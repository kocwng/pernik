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


def render(song, out, label, side='A', length='', colors=None, seconds=None, stamp='', log=print):
    """Write the player-strip MP4 to `out`. seconds: only the first N seconds (for tests).
    Returns a short summary string."""
    C = {k: rgb(v) for k, v in dict(DEFAULT_COLORS, **(colors or {})).items()}
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
