"""Render the mixtape as an MP4 "player strip" that GitHub can play right in a README.

    from pernik.audio.video import render
    render(song, 'pernik/tape.mp4', label='my tape', side='A', length='0:49', colors={...})

Ported from kocwng-profile/tools/video.py (its --style player design): a slim 1280x320 card
on the cassette's deck colour, with the cassette label ([label], side, length) and its two
reels spinning (the tape winds from left to right as the song plays), 16 equalizer bars
driven by the song's spectrum, and a thin progress line. The bottom 56 px stay calm because
GitHub's own video controls cover them.

The song is copied into the video untouched when it is AAC (m4a), otherwise encoded as AAC
160k. The video is H.264 and kept under 8 MB, so it fits GitHub's 10 MB upload limit.

GitHub only plays a video inline when it was uploaded through GitHub itself (drag the file
into the web editor of any Markdown file; GitHub turns it into a
https://github.com/user-attachments/assets/... link). A link to an MP4 in the repo only
shows as a plain link.

Needs numpy and Pillow (ImportError without them) and ffmpeg/ffprobe on PATH.
"""
import json
import math
import os
import subprocess

import numpy as np
from PIL import Image, ImageDraw, ImageFont

W, H, FPS = 1280, 320, 24
K = 4                                    # supersampling for the shapes drawn once
MAX_BYTES = 8_000_000                    # GitHub takes 10 MB; stay well under it
TARGET_BYTES = 7_400_000
THREADS = '2'                            # keep the machine responsive

DEFAULT_COLORS = {'deck': '#7B5CFF', 'cream': '#FFF6E5', 'ink': '#2B2340', 'pink': '#FF5FA2',
                  'kuning': '#FFD23F', 'mint': '#3DDC97', 'langit': '#4CC9F0', 'jeruk': '#FF8A3D'}
ROUND_FONTS = [
    '/System/Library/Fonts/Supplemental/Arial Rounded Bold.ttf',
    '/Library/Fonts/Arial Rounded Bold.ttf',
    '~/Library/Fonts/Nunito-Black.ttf', '~/Library/Fonts/Nunito-ExtraBold.ttf',
    '/usr/share/fonts/truetype/nunito/Nunito-Black.ttf',
    '/usr/share/fonts/truetype/nunito/Nunito-ExtraBold.ttf',
    '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf',
    '/usr/share/fonts/dejavu/DejaVuSans-Bold.ttf',
    '/System/Library/Fonts/Supplemental/Arial Bold.ttf',
    'C:/Windows/Fonts/arialbd.ttf',
]
SANS_FONTS = [
    '/System/Library/Fonts/Supplemental/Arial Bold.ttf',
    '/System/Library/Fonts/Supplemental/Verdana Bold.ttf',
    '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf',
    '/usr/share/fonts/dejavu/DejaVuSans-Bold.ttf',
    '/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf',
    'C:/Windows/Fonts/arialbd.ttf',
]
_fonts = {}


def rgb(c):
    c = c.lstrip('#')
    return tuple(int(c[i:i + 2], 16) for i in (0, 2, 4))


def _font_file(cands):
    for c in cands:
        p = os.path.expanduser(c)
        if os.path.exists(p):
            return p
    try:                                  # Linux without the usual paths: ask fontconfig
        p = subprocess.run(['fc-match', '-f', '%{file}', 'sans:bold'],
                           capture_output=True, text=True, timeout=10).stdout.strip()
        if p and os.path.exists(p):
            return p
    except (OSError, subprocess.SubprocessError):
        pass
    return None


def font(kind, size):
    key = (kind, round(size))
    if key not in _fonts:
        if kind not in _fonts:
            _fonts[kind] = _font_file(ROUND_FONTS if kind == 'round' else SANS_FONTS)
        path = _fonts[kind]
        _fonts[key] = (ImageFont.truetype(path, max(1, round(size))) if path
                       else ImageFont.load_default(max(1, round(size))))
    return _fonts[key]


def mix(c, over, a):
    """Colour c at opacity a over the opaque colour `over`."""
    return tuple(round(c[i] * a + over[i] * (1 - a)) for i in range(3))


def paste(frame, im, x, y):
    frame.paste(im, (round(x), round(y)), im)


class Pen:
    """RGBA canvas in 'units' (scale px per unit), drawn K times larger, then reduced.
    ImageDraw has no anti-aliasing; the reduction gives smooth edges."""

    def __init__(self, w, h, scale=1.0, ox=0.0, oy=0.0):
        self.s, self.ox, self.oy, self.w, self.h = scale * K, ox, oy, w, h
        self.im = Image.new('RGBA', (round(w * K), round(h * K)), (0, 0, 0, 0))
        self.d = ImageDraw.Draw(self.im)

    def p(self, x, y):
        return (x + self.ox) * self.s, (y + self.oy) * self.s

    def rrect(self, x0, y0, x1, y1, r, fill, stroke=None, sw=0.0):
        """Rounded rect; stroke is centred on the edge like SVG."""
        if stroke and sw:
            h = sw / 2
            self._rr(x0 - h, y0 - h, x1 + h, y1 + h, r + h, stroke)
            self._rr(x0 + h, y0 + h, x1 - h, y1 - h, max(0.0, r - h), fill)
        else:
            self._rr(x0, y0, x1, y1, r, fill)

    def _rr(self, x0, y0, x1, y1, r, fill):
        a, b = self.p(x0, y0), self.p(x1, y1)
        r = min(r * self.s, (b[0] - a[0]) / 2, (b[1] - a[1]) / 2)
        self.d.rounded_rectangle([a, b], radius=max(0, r), fill=fill)

    def circle(self, cx, cy, r, fill):
        self.d.ellipse([self.p(cx - r, cy - r), self.p(cx + r, cy + r)], fill=fill)

    def text(self, x, y, s, kind, size, fill, anchor='ls'):
        self.d.text(self.p(x, y), s, font=font(kind, size * self.s), fill=fill, anchor=anchor)

    def done(self):
        return self.im.resize((round(self.w), round(self.h)), Image.LANCZOS)


# ---------------------------------------------------------------- audio analysis

def decode(song, sr=22050):
    raw = subprocess.run(['ffmpeg', '-v', 'error', '-nostdin', '-threads', THREADS, '-i', song,
                          '-map', '0:a:0', '-ac', '1', '-ar', str(sr), '-f', 'f32le', '-'],
                         capture_output=True, check=True).stdout
    return np.frombuffer(raw, np.float32), sr


def spectrum_levels(x, sr, n_frames, n_bars=16, nfft=2048):
    """Bar levels 0..1 per video frame: log bands 60 Hz - 6 kHz, like the music page."""
    win = np.hanning(nfft).astype(np.float32)
    freqs = np.fft.rfftfreq(nfft, 1 / sr)
    edges = 60 * 100 ** (np.arange(n_bars + 1) / n_bars)
    bins = [(int(np.searchsorted(freqs, a)), max(int(np.searchsorted(freqs, a)) + 1, int(np.searchsorted(freqs, b))))
            for a, b in zip(edges, edges[1:])]
    pad = np.concatenate([np.zeros(nfft // 2, np.float32), x, np.zeros(nfft, np.float32)])
    db = np.empty((n_frames, n_bars), np.float32)
    for n in range(n_frames):
        c = int(n / FPS * sr)
        mag = np.abs(np.fft.rfft(pad[c:c + nfft] * win))
        db[n] = [20 * np.log10(mag[a:b].max() + 1e-6) for a, b in bins]
    # flatten the spectral tilt a little so the treble bars move too, then map ~42 dB to 0..1
    med = np.median(db, axis=0)
    db = db - 0.7 * (med - np.median(med))
    hi = np.percentile(db, 99.3)
    lv = np.clip((db - (hi - 42)) / 42, 0, 1) ** 1.35
    # half of each bar follows its own range, so quiet bands still move
    p5, p99 = np.percentile(lv, 5, axis=0), np.percentile(lv, 99, axis=0)
    lv = 0.5 * lv + 0.5 * np.clip((lv - p5) / np.maximum(p99 - p5, 1e-3), 0, 1)
    # smoothing: quick rise, slow fall (no flicker)
    out = np.empty_like(lv)
    y = np.zeros(n_bars, np.float32)
    for n in range(n_frames):
        y = np.where(lv[n] > y, y + 0.65 * (lv[n] - y), y + 0.22 * (lv[n] - y))
        out[n] = y
    # gentle neighbour blur so the row reads as one shape
    out[:, 1:-1] = 0.2 * out[:, :-2] + 0.6 * out[:, 1:-1] + 0.2 * out[:, 2:]
    return out


# ---------------------------------------------------------------- layers

def background(color, cream, dots=0.1):
    k = 2
    im = Image.new('RGB', (W * k, H * k), color)
    d = ImageDraw.Draw(im)
    dot = mix(cream, color, dots)
    for y in range(14, H, 28):
        for x in range(14, W, 28):
            d.ellipse([(x - 2.25) * k, (y - 2.25) * k, (x + 2.25) * k, (y + 2.25) * k], fill=dot)
    return im.resize((W, H), Image.LANCZOS)


class Deck:
    """The cream cassette label from the cassette sticker (units 22..268 x 10..94), flat,
    with the tape window and its two spinning reels."""

    def __init__(self, C, label, side, length, x0, y0, S):
        self.S = S
        self.cx, self.cy = x0 + (145 - 22) * S, y0 + (60 - 10) * S
        box = (16, 4, 278, 104)
        pen = Pen((box[2] - box[0]) * S, (box[3] - box[1]) * S, S, -box[0], -box[1])
        pen.rrect(25, 14, 271, 98, 10, C['ink'] + (90,))
        pen.rrect(22, 10, 268, 94, 10, C['cream'])
        pen.rrect(22, 58, 268, 65, 0, C['pink'])
        pen.rrect(22, 69, 268, 76, 0, C['kuning'])
        size = 20.0
        fw = lambda s, z: font('round', z * 8).getlength(s) / 8  # noqa: E731
        while fw(label, size) > 188 and size > 10:
            size -= .5
        while fw(label, size) > 188 and len(label) > 1:
            label = label[:-2].rstrip() + '…'
        pen.text(36, 27.8 + .36 * size, label, 'round', size, C['ink'])
        sideline = f'side {side} · {length}' if length else f'side {side}'
        pen.text(37, 51, sideline, 'sans', 11.5, mix(C['ink'], C['cream'], .8))
        pen.circle(246, 30, 12, C['pink'])
        bs = 15.0
        while fw(side, bs) > 19 and bs > 9:
            bs -= .5
        pen.text(246, 30, side, 'round', bs, C['cream'], anchor='mm')
        pen.rrect(72, 54, 218, 88, 17, C['ink'])
        self.tape = mix(C['langit'], C['ink'], .55)
        pen.rrect(98, 80, 192, 84, 0, self.tape)
        self.body = pen.done()
        self.x0, self.y0 = x0 + (box[0] - 22) * S, y0 + (box[1] - 10) * S
        # reel: cream wheel, ink hub, four teeth (four-fold symmetric)
        rp = Pen(26 * S, 26 * S, S, 13, 13)
        rp.circle(0, 0, 11, C['cream'])
        rp.circle(0, 0, 4, C['ink'])
        for a, b, c, d in ((-1.5, -9.5, 1.5, -4.5), (-1.5, 4.5, 1.5, 9.5), (-9.5, -1.5, -4.5, 1.5), (4.5, -1.5, 9.5, 1.5)):
            rp.rrect(a, b, c, d, 1, C['ink'])
        self.reel_big, self.reel_size = rp.im, rp.w
        self.reels, self.blobs = {}, {}

    def pos(self, ux, uy):
        return self.cx + (ux - 145) * self.S, self.cy + (uy - 60) * self.S

    def reel(self, ang):
        q = int(round(ang / 2)) * 2 % 90
        if q not in self.reels:
            im = self.reel_big.rotate(q, resample=Image.BICUBIC)
            self.reels[q] = im.resize((round(self.reel_size),) * 2, Image.LANCZOS)
        return self.reels[q]

    def blob(self, r):
        q = round(r * 4) / 4
        if q not in self.blobs:
            p = Pen((2 * q + 2) * self.S, (2 * q + 2) * self.S, self.S, q + 1, q + 1)
            p.circle(0, 0, q, self.tape)
            self.blobs[q] = p.done()
        return self.blobs[q]

    def draw(self, frame, t, prog):
        paste(frame, self.body, self.x0, self.y0)
        for ux, r, period in ((98, 15 - 3.5 * prog, 2.2), (192, 11.5 + 3.5 * prog, 1.6)):
            b = self.blob(r)
            x, y = self.pos(ux, 71)
            paste(frame, b, x - b.width / 2, y - b.height / 2)
            im = self.reel(t / period * 360)
            paste(frame, im, x - im.width / 2, y - im.height / 2)


class Equalizer:
    def __init__(self, cx, floor, colors, cream, shadow, n=16, bw=28, gap=13, hmin=24, hmax=176):
        self.n, self.bw, self.floor, self.hmin, self.hmax = n, bw, floor, hmin, hmax
        self.colors, self.cream, self.shadow = colors, cream, shadow
        self.x0 = cx - (n * bw + (n - 1) * gap) / 2
        self.step = bw + gap
        self.cache = {}

    def bar(self, i, h):
        c = i % len(self.colors)
        key = (c, h)
        if key not in self.cache:
            sw, o = 4, 6                         # cream outline, room for the shadow
            pen = Pen(self.bw + 2 * sw + o + 2, h + 2 * sw + o + 2, 1, sw + 1, sw + 1)
            r = self.bw / 2
            pen.rrect(3, 4, self.bw + 3, h + 4, r, self.shadow)
            pen.rrect(0, 0, self.bw, h, r, self.colors[c], self.cream, sw)
            self.cache[key] = pen.done()
        return self.cache[key]

    def draw(self, frame, levels):
        for i, v in enumerate(levels):
            h = int(round(self.hmin + (self.hmax - self.hmin) * float(v)))
            paste(frame, self.bar(i, h), self.x0 + i * self.step - 5, self.floor - h - 5)


class ThinLine:
    """A thin cream progress line, nothing else (GitHub's controls show the time)."""

    def __init__(self, x0, x1, cy, dur, cream, deck, hh=2.5):
        self.x0, self.x1, self.cy, self.dur, self.hh = x0, x1, cy, dur, hh
        m = 4
        track = Pen(x1 - x0 + 2 * m, 2 * hh + 2 * m, 1, m, m + hh)
        track.rrect(0, -hh, x1 - x0, hh, hh, mix(cream, deck, .28))
        self.track = track.done()
        fill = Pen(x1 - x0 + 2 * m, 2 * hh + 2 * m, 1, m, m + hh)
        fill.rrect(0, -hh, x1 - x0, hh, hh, cream)
        self.fill, self.m = fill.done(), m

    def static(self, bg):
        paste(bg, self.track, self.x0 - self.m, self.cy - self.hh - self.m)

    def draw(self, frame, t):
        p = min(1.0, max(0.0, t / self.dur)) if self.dur else 0
        w = round(p * (self.x1 - self.x0))
        if w >= 2 * self.hh:
            part = self.fill.crop((0, 0, self.m + w, self.fill.height))
            paste(frame, part, self.x0 - self.m, self.cy - self.hh - self.m)


# ---------------------------------------------------------------- komik style

KOMIK_COLORS = {'paper': '#FAF3F8', 'ink': '#1C1520', 'spot': '#E0569B', 'tint': '#F4BCD8'}
LABEL_FONTS = [
    '/System/Library/Fonts/Supplemental/Arial Black.ttf', '/Library/Fonts/Arial Black.ttf',
    '/usr/share/fonts/truetype/msttcorefonts/Arial_Black.ttf',
    '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf', '/usr/share/fonts/dejavu/DejaVuSans-Bold.ttf',
    'C:/Windows/Fonts/ariblk.ttf',
]
MONO_FONTS = [
    '/System/Library/Fonts/SFNSMono.ttf', '/System/Library/Fonts/Menlo.ttc',
    '/usr/share/fonts/truetype/dejavu/DejaVuSansMono-Bold.ttf', '/usr/share/fonts/dejavu/DejaVuSansMono-Bold.ttf',
    '/usr/share/fonts/truetype/liberation/LiberationMono-Bold.ttf', 'C:/Windows/Fonts/consolab.ttf',
]
# The README shows the 1280 px video about 900 px wide, so the design's lines (4 / 2.5 / 1.5 px)
# and halftone are drawn 1.4x here to look the same as the SVG cards next to it.
KF, KL, KH = 6, 3.5, 2                    # frame, line, hair
KR_PANEL, KR_LABEL = 8, 3                 # the 6 and 2 px radii, scaled


def kfont(kind, size):
    key = ('k' + kind, round(size))
    if key not in _fonts:
        if 'k' + kind not in _fonts:
            _fonts['k' + kind] = _font_file(LABEL_FONTS if kind == 'label' else MONO_FONTS)
        path = _fonts['k' + kind]
        if not path:
            f = ImageFont.load_default(max(1, round(size)))
        else:
            f = ImageFont.truetype(path, max(1, round(size)), index=1 if path.endswith('Menlo.ttc') else 0)
            try:
                f.set_variation_by_name('Semibold')     # a variable mono (SF Mono): weight 600, like the SVG
            except (OSError, ValueError, AttributeError):
                pass
        _fonts[key] = f
    return _fonts[key]


def dots(w, h, ox, oy, period, r):
    """Halftone alpha (L image, w x h, its top-left at (ox, oy) on the frame): round dots on a
    45-degree lattice (two square grids, the second offset by half a period), anti-aliased.
    The lattice is fixed to the frame, so neighbouring areas line up."""
    ys, xs = np.mgrid[0:h, 0:w].astype(np.float32)
    xs += ox + .5
    ys += oy + .5
    a = np.zeros((h, w), np.float32)
    for off in (0.0, period / 2):
        u = (xs - off) % period - period / 2
        v = (ys - off) % period - period / 2
        a = np.maximum(a, np.clip(r + .5 - np.sqrt(u * u + v * v), 0, 1))
    return Image.fromarray((a * 255).astype(np.uint8), 'L')


class Sketch:
    """An RGBA picture of w x h px whose top-left is (ox, oy) on the frame. Each paint() draws
    a mask K times larger in frame coordinates, reduces it (area average, so edges are smooth)
    and lays one colour through it, like one pass of a two-colour press."""

    def __init__(self, w, h, ox=0, oy=0, k=K):
        self.w, self.h, self.ox, self.oy, self.k = int(w), int(h), ox, oy, k
        self.im = Image.new('RGBA', (self.w, self.h), (0, 0, 0, 0))

    def p(self, x, y):
        return (x - self.ox) * self.k, (y - self.oy) * self.k

    def mask(self, fn):
        m = Image.new('L', (self.w * self.k, self.h * self.k), 0)
        fn(ImageDraw.Draw(m), self)
        return m.reduce(self.k)

    def paint(self, color, fn=None, mask=None, pattern=None):
        a = mask if mask is not None else self.mask(fn)
        if pattern is not None:
            a = Image.fromarray((np.asarray(a, np.float32) * np.asarray(pattern, np.float32) / 255).astype(np.uint8), 'L')
        layer = Image.new('RGBA', (self.w, self.h), color + (255,))
        layer.putalpha(a)
        self.im.alpha_composite(layer)

    def pattern(self, period, r):
        return dots(self.w, self.h, self.ox, self.oy, period, r)

    # shapes, in frame coordinates (call inside a mask function)
    def rrect(self, d, x0, y0, x1, y1, r, width=0):
        """Filled rounded rect, or (width > 0) its outline centred on the edge, like SVG."""
        h = width / 2
        box = [self.p(x0 - h, y0 - h), self.p(x1 + h, y1 + h)]
        d.rounded_rectangle(box, radius=max(0, (r + h) * self.k), fill=None if width else 255,
                            outline=255 if width else None, width=round(width * self.k) if width else 0)

    def circle(self, d, cx, cy, r, width=0):
        h = width / 2
        box = [self.p(cx - r - h, cy - r - h), self.p(cx + r + h, cy + r + h)]
        if width:
            d.ellipse(box, outline=255, width=round(width * self.k))
        else:
            d.ellipse(box, fill=255)

    def poly(self, d, pts, width=0, closed=True):
        q = [self.p(x, y) for x, y in pts]
        if not width:
            d.polygon(q, fill=255)
            return
        w = round(width * self.k)
        d.line(q + ([q[0], q[1]] if closed else []), fill=255, width=w, joint='curve')
        for x, y in (q if not closed else []):
            d.ellipse([x - w / 2, y - w / 2, x + w / 2, y + w / 2], fill=255)      # round caps

    def line(self, d, x0, y0, x1, y1, width):
        self.poly(d, [(x0, y0), (x1, y1)], width, closed=False)

    def text(self, d, x, y, s, kind, size, anchor='ls', track=0.0):
        f = kfont(kind, size * self.k)
        if not track:
            d.text(self.p(x, y), s, font=f, fill=255, anchor=anchor)
            return
        tw = sum(f.getlength(c) for c in s) + track * size * self.k * (len(s) - 1)
        px, py = self.p(x, y)
        px -= {'l': 0, 'm': tw / 2, 'r': tw}[anchor[0]]
        for c in s:
            d.text((px, py), c, font=f, fill=255, anchor='l' + anchor[1])
            px += f.getlength(c) + track * size * self.k


def kburst(cx, cy, r1, r2, points, seed=7):
    import random
    rnd = random.Random(seed)
    pts = []
    for i in range(points * 2):
        a = math.pi * i / points
        r = (r2 if i % 2 == 0 else r1) * (1 + rnd.uniform(-.06, .06))
        pts.append((cx + r * math.cos(a), cy + r * math.sin(a)))
    return pts


class KomikStrip:
    """The komik player strip: paper, an ink-framed cassette panel (halftone burst, reels that
    spin while the tape winds from left to right) and an equalizer panel (16 ink-outlined
    halftone columns on the panel floor), with a thin ink progress line in the calm bottom
    56 px that GitHub's controls cover.

      +----------------------+ +[ DEMO TAPE ]-------------------- SIDE A · 0:49 -+
      |   burst + cassette   | |   ▌▌ ▌▌▌ ▌▌▌▌ ▌▌▌ ▌▌  equalizer                    |
      +----------------------+ +--------------------------------------------------+
      ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ progress
    """
    AX, AY, AW, AH = 32, 32, 464, 216            # cassette panel
    BX, BY, BW, BH = 520, 32, 728, 216           # equalizer panel
    S = 1.3                                      # cassette units (the SVG's 224 x 136) to px
    REELS = ((80, 68), (144, 68))
    PERIOD = 10                                  # halftone lattice (neighbours 7 px apart)

    def __init__(self, colors, label, side, length, dur):
        c = dict(KOMIK_COLORS, **{k: v for k, v in (colors or {}).items() if k in KOMIK_COLORS})
        self.paper, self.ink, self.spot, self.tint = (rgb(c[k]) for k in ('paper', 'ink', 'spot', 'tint'))
        self.label, self.side, self.length, self.dur = label, side, length, dur
        self.cx0 = round(self.AX + (self.AW - 224 * self.S) / 2)
        self.cy0 = round(self.AY + (self.AH - 136 * self.S) / 2)
        self.reel_cache, self.pack_cache, self.bar_cache = {}, {}, {}
        self.lx0, self.lx1, self.ly = 48, W - 48, 288    # progress line, in the calm bottom 56 px
        self.bg = self._static()
        self._window_overlay()
        self._progress()
        # equalizer: 16 columns, pitch 40 (a multiple of the halftone period, so all share one lattice)
        self.bw, self.pitch = 30, 40
        self.n = 16
        self.ex0 = self.BX + (self.BW - (self.n - 1) * self.pitch - self.bw) / 2
        self.ex0 = round(self.ex0 / self.PERIOD) * self.PERIOD
        self.floor = self.BY + self.BH - KF // 2         # the inner edge of the panel's bottom frame
        self.hmin, self.hmax = 16, 140

    # cassette units -> frame px
    def u(self, x, y):
        return self.cx0 + x * self.S, self.cy0 + y * self.S

    def _static(self):
        sk = Sketch(W, H, k=3)
        P, I, Sp, T = self.paper, self.ink, self.spot, self.tint
        sk.paint(P, lambda d, s: s.rrect(d, 0, 0, W, H, 0))
        dots_light = sk.pattern(self.PERIOD, 1.4)        # the SVG's ht1 / ht2, scaled
        dots_mid = sk.pattern(self.PERIOD, 2.3)
        # panel A: paper, a halftone burst behind the cassette (clipped), the frame
        A = (self.AX, self.AY, self.AX + self.AW, self.AY + self.AH)
        B = (self.BX, self.BY, self.BX + self.BW, self.BY + self.BH)
        clipA = sk.mask(lambda d, s: s.rrect(d, *A, KR_PANEL))
        burst = kburst(self.AX + self.AW / 2, self.AY + self.AH / 2, 140, 236, 12)
        bm = sk.mask(lambda d, s: s.poly(d, burst))
        sk.paint(Sp, mask=_mul(bm, clipA), pattern=dots_light)
        sk.paint(I, mask=_mul(sk.mask(lambda d, s: s.poly(d, burst, KH)), clipA))
        # panel B: paper with a faint tint halftone
        clipB = sk.mask(lambda d, s: s.rrect(d, *B, KR_PANEL))
        sk.paint(T, mask=clipB, pattern=sk.pattern(8, 1.5))
        # the cassette (all but the tape packs, the window outline and the hubs, drawn per frame)
        u, S = self.u, self.S
        sk.paint(T, lambda d, s: s.rrect(d, *u(0, 0), *u(224, 136), 6 * S))
        sk.paint(I, lambda d, s: s.rrect(d, *u(0, 0), *u(224, 136), 6 * S, KL))
        for sx, sy in ((12, 12), (212, 12), (12, 124), (212, 124)):
            sk.paint(P, lambda d, s: s.circle(d, *u(sx, sy), 4 * S))
            sk.paint(I, lambda d, s: (s.circle(d, *u(sx, sy), 4 * S, KH), s.line(d, *u(sx - 2.5, sy), *u(sx + 2.5, sy), KH)))
        sk.paint(P, lambda d, s: s.rrect(d, *u(16, 12), *u(208, 100), KR_LABEL))
        sk.paint(Sp, lambda d, s: s.rrect(d, *u(16, 48), *u(208, 88), 0))
        sk.paint(I, lambda d, s: (s.rrect(d, *u(16, 12), *u(208, 100), KR_LABEL, KL),
                                  s.line(d, *u(16, 48), *u(208, 48), KH), s.line(d, *u(16, 88), *u(208, 88), KH),
                                  s.line(d, *u(56, 36), *u(192, 36), KH), s.circle(d, *u(36, 30), 11 * S)))
        sk.paint(P, lambda d, s: s.text(d, *u(36, 30.5), self.side[:1].upper(), 'label', 13 * S, anchor='mm'))
        sk.paint(P, lambda d, s: s.rrect(d, *u(48, 52), *u(176, 84), KR_PANEL))         # the window
        trap = [u(48, 136), u(60, 108), u(164, 108), u(176, 136)]
        sk.paint(T, lambda d, s: s.poly(d, trap))
        sk.paint(Sp, lambda d, s: s.poly(d, trap), pattern=dots_mid)
        sk.paint(I, lambda d, s: s.poly(d, trap, KL, closed=False))
        sk.paint(P, lambda d, s: (s.circle(d, *u(84, 124), 5 * S), s.circle(d, *u(140, 124), 5 * S),
                                  s.rrect(d, *u(104, 118), *u(120, 128), 1)))
        sk.paint(I, lambda d, s: (s.circle(d, *u(84, 124), 5 * S, KH), s.circle(d, *u(140, 124), 5 * S, KH),
                                  s.rrect(d, *u(104, 118), *u(120, 128), 1, KH)))
        # panel B header: the tape label as an ink label bar flush in the corner, side + length in mono
        size, label, room = 26.0, self.label.upper(), self.BW - 360
        fl = lambda txt, z: sum(kfont('label', z * 4).getlength(ch) for ch in txt) / 4 + .04 * z * (len(txt) - 1)  # noqa: E731
        while fl(label, size) > room and size > 18:
            size -= 1
        while fl(label, size) > room and len(label) > 1:
            label = label[:-2].rstrip() + '…'
        tw = math.ceil((fl(label, size) + 48) / 8) * 8
        th = 48
        sk.paint(I, mask=_mul(sk.mask(lambda d, s: s.rrect(d, self.BX, self.BY, self.BX + tw, self.BY + th, 0)), clipB))
        sk.paint(P, lambda d, s: s.text(d, self.BX + 24, self.BY + th / 2 + 1, label, 'label', size, anchor='lm', track=.04))
        meta = f'SIDE {self.side} · {self.length}' if self.length else f'SIDE {self.side}'
        sk.paint(I, lambda d, s: s.text(d, self.BX + self.BW - 24, self.BY + th / 2 + 1, meta, 'mono', 22, anchor='rm'))
        # frames on top: the two panels, the progress track
        sk.paint(I, lambda d, s: (s.rrect(d, *A, KR_PANEL, KF), s.rrect(d, *B, KR_PANEL, KF)))
        sk.paint(T, lambda d, s: s.line(d, self.lx0, self.ly, self.lx1, self.ly, KL))
        return sk.im.convert('RGB')

    def _progress(self):
        m = 4
        sk = Sketch(self.lx1 - self.lx0 + 2 * m, 2 * m + 4, self.lx0 - m, self.ly - m - 2)
        sk.paint(self.ink, lambda d, s: s.line(d, self.lx0, self.ly, self.lx1, self.ly, KL))
        self.prog, self.prog_xy = sk.im, (self.lx0 - m, self.ly - m - 2)

    def _window_overlay(self):
        x0, y0 = self.u(48, 52)
        x1, y1 = self.u(176, 84)
        m = 4
        self.win = (math.floor(x0) - m, math.floor(y0) - m, math.ceil(x1) + m, math.ceil(y1) + m)
        wx0, wy0, wx1, wy1 = self.win
        sk = Sketch(wx1 - wx0, wy1 - wy0, wx0, wy0)
        sk.paint(self.ink, lambda d, s: s.rrect(d, x0, y0, x1, y1, KR_PANEL, KL))
        self.win_line = sk.im
        self.win_clip = Sketch(wx1 - wx0, wy1 - wy0, wx0, wy0).mask(lambda d, s: s.rrect(d, x0, y0, x1, y1, KR_PANEL))
        self.win_dots = dots(wx1 - wx0, wy1 - wy0, wx0, wy0, 7, 1.5)

    def packs(self, p):
        """The tape on the two reels at progress p: radii trade area (26 -> 14 units and back)."""
        a, b = 26.0, 14.0
        rl = math.sqrt(max(b * b, a * a - (a * a - b * b) * p))
        rr = math.sqrt(min(a * a, b * b + (a * a - b * b) * p))
        key = (round(rl * 2) / 2, round(rr * 2) / 2)
        if key not in self.pack_cache:
            wx0, wy0, wx1, wy1 = self.win
            sk = Sketch(wx1 - wx0, wy1 - wy0, wx0, wy0)
            for (ux, uy), r in zip(self.REELS, key):
                cx, cy = self.u(ux, uy)
                sk.paint(self.ink, mask=_mul(sk.mask(lambda d, s: s.circle(d, cx, cy, r * self.S)), self.win_clip),
                         pattern=self.win_dots)
                sk.paint(self.ink, mask=_mul(sk.mask(lambda d, s: s.circle(d, cx, cy, r * self.S, KH)), self.win_clip))
            sk.im.alpha_composite(self.win_line)
            self.pack_cache[key] = sk.im
        return self.pack_cache[key]

    def reel(self, cx, cy, ang):
        """A hub at (cx, cy) turned by ang degrees: (image, x, y) to paste."""
        q = int(round(ang / 3)) * 3 % 60                 # six teeth: 60-degree symmetry
        key = (cx, cy, q)
        if key not in self.reel_cache:
            r = 10 * self.S
            box = math.ceil(r + KL) + 2
            ox, oy = math.floor(cx) - box, math.floor(cy) - box
            sk = Sketch(2 * box + 2, 2 * box + 2, ox, oy)
            sk.paint(self.paper, lambda d, s: s.circle(d, cx, cy, r))

            def ink(d, s):
                s.circle(d, cx, cy, r, KL)
                for k in range(6):
                    a = math.radians(q + 60 * k)
                    s.line(d, cx + 4 * self.S * math.sin(a), cy - 4 * self.S * math.cos(a),
                           cx + 8 * self.S * math.sin(a), cy - 8 * self.S * math.cos(a), KH)
            sk.paint(self.ink, ink)
            self.reel_cache[key] = (sk.im, ox, oy)
        return self.reel_cache[key]

    def bar(self, h):
        h = int(h)
        if h not in self.bar_cache:
            bw, sw = self.bw, KL
            box_w, box_h = bw + 12, h + 12
            ox, oy = -6, -(h + 6)                                # local: x 0..bw, y -h..0 (0 = floor)
            sk = Sketch(box_w, box_h, ox, oy)
            body = lambda d, s: s.rrect(d, 0, -h, bw, 4, KR_LABEL)  # noqa: E731  (runs under the floor line)
            sk.paint(self.tint, body)
            # the lattice is fixed to the floor and the pitch is a multiple of the period: every
            # column shows the same dots, which stay put while the column grows
            sk.paint(self.spot, body, pattern=dots(box_w, box_h, ox + self.ex0, oy + self.floor, self.PERIOD, 2.6))
            sk.paint(self.ink, lambda d, s: s.rrect(d, 0, -h, bw, 4, KR_LABEL, sw))
            im = sk.im.crop((0, 0, box_w, int(-oy)))           # nothing below the floor
            self.bar_cache[h] = (im, ox, oy)
        return self.bar_cache[h]

    def frame_fn(self, levels):
        hub = [self.u(*r) for r in self.REELS]
        floor = round(self.floor)

        def frame(k):
            t = k / FPS
            p = min(1.0, t / self.dur) if self.dur else 0.0
            fr = self.bg.copy()
            paste(fr, self.packs(p), self.win[0], self.win[1])
            for (x, y), period in zip(hub, (2.4, 1.6)):
                im, ox, oy = self.reel(x, y, -t / period * 360)
                fr.paste(im, (ox, oy), im)
            for i, v in enumerate(levels[k]):
                h = round(self.hmin + (self.hmax - self.hmin) * float(v))
                im, ox, oy = self.bar(h)
                paste(fr, im, self.ex0 + i * self.pitch + ox, floor + oy)
            w = round(p * (self.lx1 - self.lx0))
            if w > 0:
                part = self.prog.crop((0, 0, 4 + w + 2, self.prog.height))
                fr.paste(part, self.prog_xy, part)
            return fr
        return frame


def _mul(a, b):
    """Intersect two L masks."""
    return Image.fromarray((np.asarray(a, np.float32) * np.asarray(b, np.float32) / 255).astype(np.uint8), 'L')


# ---------------------------------------------------------------- encoding

def audio_info(song):
    out = subprocess.run(['ffprobe', '-v', 'error', '-select_streams', 'a:0', '-show_entries',
                          'stream=codec_name,bit_rate:format=bit_rate', '-of', 'json', song],
                         capture_output=True, text=True).stdout
    j = json.loads(out or '{}')
    st = (j.get('streams') or [{}])[0]
    br = st.get('bit_rate') or j.get('format', {}).get('bit_rate') or 192000
    return st.get('codec_name', ''), int(br)


def stamp_of(path):
    """The pernik stamp stored in an MP4's comment tag ('' if none), to skip re-rendering."""
    if not os.path.exists(path):
        return ''
    try:
        out = subprocess.run(['ffprobe', '-v', 'error', '-show_entries', 'format_tags=comment',
                              '-of', 'csv=p=0', path], capture_output=True, text=True, timeout=30).stdout
    except (OSError, subprocess.SubprocessError):
        return ''
    out = out.strip()
    return out[len('pernik:'):] if out.startswith('pernik:') else ''


def encode(frames, n, song, out, seconds, codec, crf, maxrate, stamp):
    acopy = codec == 'aac'
    cmd = ['ffmpeg', '-y', '-v', 'error', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s', f'{W}x{H}',
           '-r', str(FPS), '-i', '-', '-i', song, '-map', '0:v:0', '-map', '1:a:0',
           '-c:v', 'libx264', '-preset', 'medium', '-tune', 'animation', '-crf', str(crf),
           '-maxrate', f'{maxrate}k', '-bufsize', f'{2 * maxrate}k', '-pix_fmt', 'yuv420p',
           '-threads', THREADS, '-c:a', 'copy' if acopy else 'aac']
    if not acopy:
        cmd += ['-b:a', '160k']
    cmd += ['-t', f'{seconds:.3f}', '-metadata', f'comment=pernik:{stamp}', '-movflags', '+faststart', out]
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    try:
        for k in range(n):
            proc.stdin.write(frames(k).tobytes())
        proc.stdin.close()
    except BrokenPipeError:
        pass
    if proc.wait() != 0:
        raise RuntimeError('ffmpeg could not encode the video')


def render(song, out, label, side='A', length='', colors=None, seconds=None, stamp='', log=print, style='sticker'):
    """Write the player-strip MP4 to `out`. seconds: only the first N seconds (for tests).
    Returns a short summary string. style: 'sticker' (the deck card) or 'komik' (a comic strip:
    colors then holds the four komik colours paper/ink/spot/tint)."""
    x, sr = decode(song)
    dur = len(x) / sr
    if not dur:
        raise RuntimeError('the song decoded to no audio')
    total = min(dur, seconds) if seconds else dur
    n = int(math.ceil(total * FPS))
    levels = spectrum_levels(x, sr, n)
    # poster frame: bars resting in a gentle hump, handing over to the song within ~1 s
    rest = 0.1 + 0.16 * np.sin(np.pi * (np.arange(levels.shape[1]) + .5) / levels.shape[1])
    for k in range(min(n, FPS * 2)):
        levels[k] = np.maximum(levels[k], rest * math.exp(-k / FPS / .45))

    if style == 'komik':
        frame = KomikStrip(colors, label, side, length, dur).frame_fn(levels)
    else:
        C = {k: rgb(v) for k, v in dict(DEFAULT_COLORS, **(colors or {})).items()}
        bg = background(C['deck'], C['cream'])
        deck = Deck(C, label, side, length, 40, 48, 2.0)
        eq = Equalizer(910, 216, [C['kuning'], C['mint'], C['langit'], C['pink'], C['jeruk']],
                       C['cream'], C['ink'] + (90,))
        line = ThinLine(40, 1240, 290, dur, C['cream'], C['deck'])
        line.static(bg)

        def frame(k):
            t = k / FPS
            fr = bg.copy()
            deck.draw(fr, t, t / dur)
            eq.draw(fr, levels[k])
            line.draw(fr, t)
            return fr

    codec, abr = audio_info(song)
    audio_bits = (abr if codec == 'aac' else 160000) * total
    crf, maxrate = 20, int(max(250, min(3000, (TARGET_BYTES * 8 - audio_bits) / total / 1000 * .93)))
    os.makedirs(os.path.dirname(os.path.abspath(out)), exist_ok=True)
    for _ in range(3):
        encode(frame, n, song, out, total, codec, crf, maxrate, stamp)
        size = os.path.getsize(out)
        if size <= MAX_BYTES:
            break
        log(f'video: {size} bytes is too big, trying again smaller')
        crf, maxrate = crf + 3, int(maxrate * .75)
    return f'{os.path.getsize(out) // 1024} KB, {total:.1f} s, {n} frames'
