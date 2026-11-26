"""divider in the komik style: a framed strip printed in ink + one spot colour. Rules: docs/design.md

Batik styles (kawung, truntum, mega-mendung, sekar-jagad) are drawn as two-colour cap-batik
stamps: spot or tint fills with ink lines on paper, inside a thin inner rule like the border
of a cloth. The stamps press in once, left to right (a cap is a stamp). Komik-native styles:

    film    a film strip / manga gutter: sprocket holes and frames whose halftone pulses
    hearts  a garland of hearts (pure decoration: every heart is full, nothing is counted)
    dots    a halftone band fading from dense (left) to paper (right)
    wave    an ink wave with tint below; the line draws in once

No idle loop. parang / lereng and other court-restricted motifs stay left out (see
docs/motifs.md). Shape helpers are shared with the sticker divider.
"""
import math
import random

from .. import komik as K
from . import Out
from ._komik_heading import n
from .divider import NOT_OFFERED, _blossom, _cloud, _ellipse, _patterns, _wave_d

W = 900
STYLES = ('wave', 'kawung', 'truntum', 'mega-mendung', 'sekar-jagad', 'film', 'hearts', 'dots')
AUTO_H = {'wave': 56, 'dots': 48, 'hearts': 56, 'film': 88,
          'kawung': 80, 'truntum': 80, 'mega-mendung': 88, 'sekar-jagad': 80}
LOW = {'wave': 40, 'dots': 40, 'hearts': 48, 'film': 80}          # batik needs 64 for its motif
NAMES = {'wave': 'ink wave', 'dots': 'halftone fade', 'hearts': 'row of hearts', 'film': 'film strip',
         'kawung': 'kawung batik', 'truntum': 'truntum batik', 'mega-mendung': 'mega mendung batik',
         'sekar-jagad': 'sekar jagad batik'}
ALIAS = {'megamendung': 'mega-mendung', 'mega': 'mega-mendung', 'sekarjagad': 'sekar-jagad',
         'sekar': 'sekar-jagad', 'dot': 'dots', 'heart': 'hearts', 'halftone': 'dots',
         'filmstrip': 'film', 'film-strip': 'film', 'gutter': 'film'}


class Print:
    """One render: the kit, the strip box, the seed and the arrive/draw timing."""

    def __init__(self, k, h, rng, animate):
        self.k, self.h, self.rng, self.anim = k, h, rng, animate
        self.delays = set()
        # inner edge of the card's ink frame
        self.ix0, self.iy0, self.ix1, self.iy1 = 8, 8, W - 8, h - 8
        # the thin inner rule of a batik strip (4 px of paper inside the frame)
        self.x0, self.y0, self.x1, self.y1 = 12, 12, W - 12, h - 12

    def when(self, x, extra=0.0):
        """Start time for something at x: the press moves left to right in about a second."""
        return .15 + .95 * max(0.0, min(1.0, (x - self.x0) / (self.x1 - self.x0))) + extra

    def cls(self, kind, x, extra=0.0):
        if not self.anim:
            return ''
        d = round(self.when(x, extra) * 10)
        self.delays.add(d)
        return f' class="{kind} d{d}"'

    def css(self):
        if not self.anim:
            return ''
        return ('.st{transform-box:fill-box;transform-origin:center;animation:st .45s cubic-bezier(.3,1.3,.5,1) both}'
                '@keyframes st{0%{opacity:0;transform:scale(1.25)}55%{opacity:1;transform:scale(.96)}'
                '100%{transform:scale(1)}}'
                '.dr{stroke-dasharray:1 1;animation:dr 1.1s cubic-bezier(.45,0,.3,1) both}'
                '@keyframes dr{from{stroke-dashoffset:1}to{stroke-dashoffset:0}}'
                + ''.join(f'.d{d}{{animation-delay:{d / 10:g}s}}' for d in sorted(self.delays)))

    def clip(self, cid, inner_rule):
        if inner_rule:
            return (f'<clipPath id="{cid}"><rect x="{self.x0}" y="{self.y0}" width="{self.x1 - self.x0}" '
                    f'height="{self.y1 - self.y0}" rx="{K.R_LABEL}"/></clipPath>')
        return (f'<clipPath id="{cid}"><rect x="{self.ix0}" y="{self.iy0}" width="{self.ix1 - self.ix0}" '
                f'height="{self.iy1 - self.iy0}" rx="4"/></clipPath>')

    def frame(self, motif, defs, inner_rule=True):
        """Card + clipped motif (+ the cloth's thin inner rule) + the ink frame on top."""
        k, h = self.k, self.h
        rule = (f'<rect x="{self.x0}" y="{self.y0}" width="{self.x1 - self.x0}" height="{self.y1 - self.y0}" '
                f'rx="{K.R_LABEL}" fill="none" stroke="{k.ink}" stroke-width="{K.HAIR}"/>' if inner_rule else '')
        return (k.card(0, 0, W, h) + f'<defs>{self.clip("dc", inner_rule)}{defs}</defs>'
                + f'<g clip-path="url(#dc)">{motif}</g>' + rule
                + f'<rect x="6" y="6" width="{W - 12}" height="{h - 12}" rx="{K.R_PANEL}" fill="none" '
                  f'stroke="{k.ink}" stroke-width="{K.FRAME}"/>')


def render(opts, ctx):
    style = str(opts.get('style') or 'wave').strip().lower().replace('_', '-').replace(' ', '-')
    style = ALIAS.get(style, style)
    if style in NOT_OFFERED or style.startswith('parang'):
        raise ValueError(f'style "{style}" is not offered: parang/lereng and other court-restricted '
                         f'("larangan") motifs are left out on purpose. Try: {", ".join(STYLES)}')
    if style not in STYLES:
        raise ValueError(f'unknown style "{style}". Try: {", ".join(STYLES)}')
    seed = opts.get('seed')
    rng = random.Random(ctx.seed if seed in (None, '') else int(seed))
    h = opts.get('height')
    if h in (None, '', 'auto', 0):
        h = AUTO_H[style]
    else:
        h = max(LOW.get(style, 64), min(96, int(h)))
        h -= h % 8                                              # heights sit on the 8 grid
    anim = opts.get('animate', True)
    anim = anim if isinstance(anim, bool) else str(anim).lower() not in ('false', 'no', '0', 'off')
    p = Print(K.Kit(ctx.theme, ctx.mode), h, rng, anim)
    body = {'wave': _wave, 'dots': _dots, 'hearts': _hearts, 'film': _film, 'kawung': _kawung,
            'truntum': _truntum, 'mega-mendung': _mega, 'sekar-jagad': _sekar}[style](p)
    title = f'{NAMES[style]} divider'
    svg = p.k.doc(W, h, body, title=title, desc=f'A decorative {NAMES[style]} section divider, printed in two colours.',
                  css=p.css())
    return Out(svg=svg, alt=title[0].upper() + title[1:])


# ---------------------------------------------------------------- komik-native

def _wave(p):
    k, rng, h = p.k, p.rng, p.h
    cy = h / 2 - 2
    amp = min(8, (h - 32) / 2.5)
    period = (W - 16) / rng.choice((4, 4.5, 5, 5.5, 6))
    d = _wave_d(p.ix0 - 8, p.ix1 + 8, cy, amp, period, rng.choice((0, .5)))
    fill = f'<path d="{d}V{h}H0Z" fill="{k.tint}"/>'
    # a hairline echo underneath gives the tint a printed edge, like a second pass of the press
    echo = (f'<path d="{d}" transform="translate(0 {n(min(12, h / 4))})" fill="none" stroke="{k.ink}" '
            f'stroke-width="{K.HAIR}" stroke-linecap="round" pathLength="1"{p.cls("dr", p.x0, .25)}/>')
    line = (f'<path d="{d}" fill="none" stroke="{k.ink}" stroke-width="{K.LINE}" stroke-linecap="round" '
            f'stroke-linejoin="round" pathLength="1"{p.cls("dr", p.x0)}/>')
    return p.frame(fill + echo + line, '', inner_rule=False)


def _dots(p):
    """Halftone fade: one dot grid whose dot size steps down left to right, in many small steps."""
    k = p.k
    steps = 18
    r_hi, r_lo = 2.7, .25
    span = p.ix1 - p.ix0
    defs, bands = '', ''
    for i in range(steps):
        t = i / (steps - 1)
        r = r_hi + (r_lo - r_hi) * t ** .8
        defs += (f'<pattern id="hf{i}" width="6" height="6" patternUnits="userSpaceOnUse" patternTransform="rotate(45)">'
                 f'<circle cx="3" cy="3" r="{r:.2f}" fill="{k.spot}"/></pattern>')
        x = p.ix0 + span * i / steps
        bands += f'<rect x="{n(x)}" y="0" width="{n(span / steps + .5)}" height="{p.h}" fill="url(#hf{i})"/>'
    # the band presses in from the dense end
    motif = f'<g{p.cls("st", p.x0)}>{bands}</g>' if p.anim else bands
    return p.frame(motif, defs, inner_rule=False)


def _hearts(p):
    k, h = p.k, p.h
    cy = h / 2 + 1
    big, small = (12, 8) if h >= 56 else (10, 6)
    pitch = 48
    count = int((p.ix1 - p.ix0 - 48) / pitch) | 1                # odd, so a big heart sits in the middle
    x0 = W / 2 - (count - 1) / 2 * pitch
    # a hairline string ties the garland together and leads the eye across
    out = [f'<path d="M{p.ix0 + 16} {n(cy)}H{p.ix1 - 16}" stroke="{k.ink}" stroke-width="{K.HAIR}" '
           f'stroke-linecap="round" pathLength="1"{p.cls("dr", p.x0, -.1)}/>']
    for i in range(count):
        x = x0 + i * pitch
        if i % 2 == 0:
            hrt = k.heart(x, cy, big, True)
        else:
            hrt = k.heart(x, cy, small, True).replace(f'fill="{k.spot}"', f'fill="{k.tint}"', 1)
        out.append(f'<g{p.cls("st", x, .1)}>{hrt}</g>' if p.anim else hrt)
    return p.frame(''.join(out), '', inner_rule=False)


def _film(p):
    """A strip of film: ink base, sprocket holes top and bottom, frames whose halftone pulses."""
    k, h = p.k, p.h
    ink_y0, ink_y1 = p.y0, p.y1                              # 4 px of paper above and below
    hole_w, hole_h, hole_pitch = 8, 6, 16
    m = 4                                                    # film edge to hole
    top_y, bot_y = ink_y0 + m, ink_y1 - m - hole_h
    fy0, fy1 = top_y + hole_h + m, bot_y - m
    fh = fy1 - fy0
    fw = round(fh * 1.5 / 8) * 8                              # frames on the 8 grid, about 3:2
    gap = 8
    pitch = fw + gap
    count = int((p.ix1 - p.ix0 - gap) / pitch)
    fx0 = W / 2 - (count * pitch - gap) / 2
    hx0 = p.ix0 + 4
    holes = ''.join(f'M{hx0 + i * hole_pitch} {y}h{hole_w}v{hole_h}h-{hole_w}Z'
                    for i in range(int((p.ix1 - hx0) / hole_pitch) + 1) for y in (top_y, bot_y))
    tones = ('url(#ht1)', 'url(#ht2)', 'url(#ht3)', 'url(#ht2)')
    off = p.rng.randrange(len(tones))
    frames = []
    for i in range(count):
        x = fx0 + i * pitch
        tone = tones[(i + off) % len(tones)]
        f = (f'<rect x="{n(x)}" y="{fy0}" width="{fw}" height="{fh}" rx="{K.R_LABEL}" fill="{k.paper}"/>'
             f'<rect x="{n(x)}" y="{fy0}" width="{fw}" height="{fh}" rx="{K.R_LABEL}" fill="{tone}"/>')
        frames.append(f'<g{p.cls("st", x)}>{f}</g>' if p.anim else f)
    motif = (f'<rect x="0" y="{ink_y0}" width="{W}" height="{ink_y1 - ink_y0}" fill="{k.solid}"/>'
             f'<path d="{holes}" fill="{k.paper}"/>' + ''.join(frames))
    return p.frame(motif, '', inner_rule=False)


# ---------------------------------------------------------------- cap batik

def _kawung(p):
    """Four ovals round a centre in a diagonal lattice; the middle row in spot, the cut rows in tint."""
    k, rng = p.k, p.rng
    ih = p.y1 - p.y0
    s = max(ih, 52) * rng.choice((1.0, 1.08, 1.16))     # thin strips crop the flowers, not shrink them
    c, a = .25 * s, .21 * s
    b = a * rng.uniform(.6, .7)
    four = ''.join(f'<use href="#ko" transform="rotate({r})"/>' for r in (45, 135, 225, 315))
    veins = ''.join(f'<use href="#kv" transform="rotate({r})"/>' for r in (45, 135, 225, 315))
    defs = (f'<path id="ko" d="{_ellipse(c, 0, a, b)}"/>'
            f'<path id="kv" d="M{n(c - a * .5)} 0Q{n(c)} {n(-b * .55)} {n(c + a * .5)} 0Q{n(c)} {n(b * .55)} '
            f'{n(c - a * .5)} 0Z"/>'
            + ''.join(f'<g id="k{t}"><g fill="{col}" stroke="{k.ink}" stroke-width="{K.LINE}">{four}</g>'
                      f'<g fill="none" stroke="{k.ink}" stroke-width="{K.HAIR}">{veins}</g>'
                      f'<circle r="{n(s * .045)}" fill="{k.ink}"/></g>'
                      for t, col in (('a', k.spot), ('b', k.tint)))
            + f'<path id="ks" d="M0 -{n(s * .07)}Q0 0 {n(s * .07)} 0Q0 0 0 {n(s * .07)}Q0 0 -{n(s * .07)} 0Q0 0 0 '
              f'-{n(s * .07)}Z" fill="{k.ink}"/>')
    cy = (p.y0 + p.y1) / 2
    off = rng.uniform(0, s)
    out, stars = [], []
    i = 0
    x = p.x0 - s + off
    while x < p.x1 + s / 2:
        # a diagonal lattice: even columns hold a middle-row flower, odd ones the cut rows above and below
        flowers, gaps = ((0,), (-s / 2, s / 2)) if i % 2 == 0 else ((-s / 2, s / 2), (0,))
        for dy in flowers:
            t = 'a' if dy == 0 else 'b'
            out.append(f'<use href="#k{t}" x="{n(x)}" y="{n(cy + dy)}"{p.cls("st", x)}/>')
        stars += [f'<use href="#ks" x="{n(x)}" y="{n(cy + dy)}"/>' for dy in gaps]
        x += s / 2
        i += 1
    return p.frame(''.join(out) + ''.join(stars), defs)


def _truntum(p):
    """Small star blossoms scattered in two staggered rows, with ink cecek dots between."""
    k, rng = p.k, p.rng
    ih = p.y1 - p.y0
    R = ih * .25
    defs = (f'<path id="t8" d="{_blossom(8, R, R * .38)}"/>'
            f'<path id="t6" d="{_blossom(6, R * .84, R * .36, .7)}"/>'
            f'<g id="tc"><circle r="{n(R * .3)}" fill="{k.paper}" stroke="{k.ink}" stroke-width="{K.HAIR}"/>'
            f'<circle r="{n(R * .1)}" fill="{k.ink}"/></g>'
            f'<path id="t4" d="M0 -{n(R * .42)}Q{n(R * .08)} -{n(R * .08)} {n(R * .42)} 0Q{n(R * .08)} {n(R * .08)} '
            f'0 {n(R * .42)}Q-{n(R * .08)} {n(R * .08)} -{n(R * .42)} 0Q-{n(R * .08)} -{n(R * .08)} 0 -{n(R * .42)}Z" '
            f'fill="{k.ink}"/>'
            f'<g id="td" fill="{k.ink}"><circle cy="-{n(R * .26)}" r="{n(R * .1)}"/>'
            f'<circle cx="{n(R * .23)}" cy="{n(R * .13)}" r="{n(R * .1)}"/>'
            f'<circle cx="-{n(R * .23)}" cy="{n(R * .13)}" r="{n(R * .1)}"/></g>')
    cy = (p.y0 + p.y1) / 2
    gx = ih * rng.uniform(.6, .68)
    dy = ih * .23
    x = p.x0 + rng.uniform(0, gx) - gx
    out, i = [], 0
    while x < p.x1 + gx:
        up = i % 2 == 0
        y = cy + (-dy if up else dy) + rng.uniform(-1.5, 1.5)
        kind = 't8' if rng.random() < .65 else 't6'
        fill = k.spot if i % 3 != 1 else k.tint
        blossom = (f'<use href="#{kind}" fill="{fill}" stroke="{k.ink}" stroke-width="{K.HAIR}" '
                   f'stroke-linejoin="round"/><use href="#tc"/>')
        out.append(f'<g transform="translate({n(x)} {n(y)}) rotate({rng.randrange(45)})">'
                   f'<g{p.cls("st", x)}>{blossom}</g></g>')
        # between two blossoms: a tiny ink star or a three-dot cecek
        fx = x + gx / 2
        filler = 't4' if rng.random() < .55 else 'td'
        out.append(f'<use href="#{filler}" transform="translate({n(fx)} {n(cy + rng.uniform(-2, 2))}) '
                   f'rotate({rng.randrange(90)})"/>')
        out.append(f'<use href="#td" transform="translate({n(x)} {n(cy + (dy if up else -dy) * 1.05)}) scale(.8)"/>')
        x += gx
        i += 1
    return p.frame(''.join(out), defs)


def _mega(p):
    """Mega mendung clouds as a two-colour print: ink outline, spot rim, ink hairline, tint core."""
    k, rng = p.k, p.rng
    ih = p.y1 - p.y0
    ch = max(28, ih * .52)
    band = ch * .13
    defs = ''
    variants = 3
    for v in range(variants):
        cw = ch * rng.uniform(1.75, 2.15)
        defs += (f'<path id="m{v}" d="{_cloud(rng, cw, ch)}"/>'
                 f'<clipPath id="mc{v}"><use href="#m{v}"/></clipPath>'
                 f'<g id="g{v}"><g clip-path="url(#mc{v})" fill="none">'
                 f'<use href="#m{v}" fill="{k.tint}"/>'
                 f'<use href="#m{v}" stroke="{k.ink}" stroke-width="{n(2 * band + K.HAIR)}"/>'
                 f'<use href="#m{v}" stroke="{k.spot}" stroke-width="{n(2 * band - K.HAIR)}"/></g>'
                 f'<use href="#m{v}" fill="none" stroke="{k.ink}" stroke-width="{K.LINE}" stroke-linejoin="round"/></g>')
    cy = (p.y0 + p.y1) / 2
    step = ch * 2.1
    x = p.x0 + rng.uniform(-step * .4, 0)
    out, i = [], 0
    vs = list(range(variants))
    rng.shuffle(vs)
    while x < p.x1 + step * .5:
        # the lobes rise above the cloud's box, so the cloud sits a little low to look centred
        y = cy + ch * .24 + (ih * .06 if i % 2 else -ih * .06) + rng.uniform(-1.5, 1.5)
        flip = -1 if (i + (rng.random() < .3)) % 2 else 1
        out.append(f'<g transform="translate({n(x)} {n(y)}) scale({flip} 1)">'
                   f'<use href="#g{vs[i % variants]}"{p.cls("st", x)}/></g>')
        x += step * rng.uniform(.85, 1.05)
        i += 1
    return p.frame(''.join(out), defs)


def _hair_patterns(ink):
    """Two line fills drawn with the hair weight (the shared ones are fills only)."""
    def tile(pid, w, h, body):
        return f'<pattern id="{pid}" width="{w}" height="{h}" patternUnits="userSpaceOnUse">{body}</pattern>'
    return {
        'sisik': lambda pid, c: tile(pid, 14, 12, f'<path d="M0 12A7 7 0 0 1 14 12M-7 6A7 7 0 0 1 7 6M7 6A7 7 0 0 1 21 6" '
                                                  f'fill="none" stroke="{c}" stroke-width="{K.HAIR}"/>'),
        'ombak': lambda pid, c: tile(pid, 16, 8, f'<path d="M0 4Q4 0 8 4T16 4" fill="none" stroke="{c}" '
                                                 f'stroke-width="{K.HAIR}"/>'),
    }


def _sekar(p):
    """Sekar jagad: a map of islands, each filled with its own small motif, outlined in a double line."""
    k, rng = p.k, p.rng
    top, bot = p.y0 - 4, p.y1 + 4
    cy = (p.y0 + p.y1) / 2
    xs = [p.x0 - 30]
    while xs[-1] < p.x1 + 10:
        xs.append(xs[-1] + rng.uniform(64, 104))
    bounds = []
    for i, x in enumerate(xs):
        wob = 0 if i in (0, len(xs) - 1) else 11
        bounds.append(((x + rng.uniform(-wob, wob), top), (x + rng.uniform(-wob, wob), cy + rng.uniform(-6, 6)),
                       (x + rng.uniform(-wob, wob), bot)))

    def seg(a, b):        # S-curve with vertical tangents
        my = (b[1] - a[1]) / 2
        return f'C{n(a[0])} {n(a[1] + my)} {n(b[0])} {n(b[1] - my)} {n(b[0])} {n(b[1])}'

    def hseg(a, b, w):    # left-right curve with horizontal tangents
        dx = (b[0] - a[0]) / 3
        return f'C{n(a[0] + dx)} {n(a[1] + w)} {n(b[0] - dx)} {n(b[1] - w)} {n(b[0])} {n(b[1])}'

    fills_only = _patterns(None)
    pats = {name: fills_only[name] for name in ('cecek', 'kawung', 'kembang')}
    pats.update(_hair_patterns(k.ink))
    names = list(pats)
    rng.shuffle(names)
    colours = (k.paper, k.tint, k.spot)
    used, defs, cells, lines = set(), '', [], []
    last_col, last_pat, ci = None, None, rng.randrange(3)
    for i in range(len(bounds) - 1):
        L, R = bounds[i], bounds[i + 1]
        if i:
            lines.append((f'M{n(L[0][0])} {n(L[0][1])}' + seg(L[0], L[1]) + seg(L[1], L[2]), L[1][0]))
        if rng.random() < .55 and (R[1][0] - L[1][0]) > 56:
            w = rng.uniform(-6, 6)
            parts = [f'M{n(L[0][0])} {n(L[0][1])}L{n(R[0][0])} {n(R[0][1])}' + seg(R[0], R[1])
                     + hseg(R[1], L[1], -w) + seg(L[1], L[0]) + 'Z',
                     f'M{n(L[1][0])} {n(L[1][1])}' + hseg(L[1], R[1], w) + seg(R[1], R[2])
                     + f'L{n(L[2][0])} {n(L[2][1])}' + seg(L[2], L[1]) + 'Z']
            lines.append((f'M{n(L[1][0])} {n(L[1][1])}' + hseg(L[1], R[1], w), L[1][0]))
        else:
            parts = [f'M{n(L[0][0])} {n(L[0][1])}L{n(R[0][0])} {n(R[0][1])}' + seg(R[0], R[1]) + seg(R[1], R[2])
                     + f'L{n(L[2][0])} {n(L[2][1])}' + seg(L[2], L[1]) + seg(L[1], L[0]) + 'Z']
        cx = (L[1][0] + R[1][0]) / 2
        for d in parts:
            col = colours[ci % 3]
            if col == last_col:
                ci += 1
                col = colours[ci % 3]
            ci += 1 + (rng.random() < .3)
            last_col = col
            pn = rng.choice([q for q in names if q != last_pat])
            last_pat = pn
            tone = 'p' if col == k.spot else 'i'
            pid = f's{names.index(pn)}{tone}'
            if pid not in used:
                used.add(pid)
                defs += pats[pn](pid, k.paper if tone == 'p' else k.ink)
            cells.append(f'<g{p.cls("st", cx)}><path d="{d}" fill="{col}"/><path d="{d}" fill="url(#{pid})"/></g>')
    # boundaries: two ink hairlines with paper between, like the outlined islands of the cloth
    lpath = ''.join(f'<path d="{d}" pathLength="1"{p.cls("dr", x, .15)}/>' for d, x in lines)
    out = (''.join(cells)
           + f'<g fill="none" stroke="{k.ink}" stroke-width="{2 * K.HAIR + 3}">{lpath}</g>'
           + f'<g fill="none" stroke="{k.paper}" stroke-width="3">{lpath}</g>')
    return p.frame(out, defs)
