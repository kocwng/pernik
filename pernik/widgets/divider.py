"""A full-width section divider: a wavy ribbon, a row of dots, or a batik band.

    [[widget]]
    id = "garis"
    kind = "divider"
    style = "kawung"        # wave | kawung | truntum | mega-mendung | sekar-jagad | dots
    colors = ["pink", "kuning", "#4CC9F0"]   # accent names or hex; default: theme accents
    # ground = "anggur"     # batik styles: the band's base colour (default: a dark accent)
    # height = 72           # px, default depends on the style
    # animate = true        # draw-in once ("canting"), then a tiny idle glint
    # seed = 7              # default: from your username + widget id

The batik bands are procedural designs *inspired by* the motifs (see docs/motifs.md), not
copies of any cloth. Court-restricted ("larangan") motifs such as parang and lereng are
deliberately not offered.
"""
import math
import random

from ..svg import doc, sticker
from . import Out, widget

W = 900
STYLES = ('wave', 'kawung', 'truntum', 'mega-mendung', 'sekar-jagad', 'dots')
AUTO_H = {'wave': 60, 'dots': 60, 'kawung': 76, 'truntum': 72, 'mega-mendung': 86, 'sekar-jagad': 80}
NAMES = {'wave': 'wavy ribbon', 'dots': 'row of dots', 'kawung': 'kawung batik',
         'truntum': 'truntum batik', 'mega-mendung': 'mega mendung batik',
         'sekar-jagad': 'sekar jagad batik'}
NOT_OFFERED = ('parang', 'lereng', 'parang-rusak', 'parang-barong', 'udan-liris', 'semen-rama')


@widget('divider', defaults={'style': 'wave', 'colors': [], 'ground': None, 'height': 'auto',
                             'animate': True, 'seed': None})
def divider(opts, ctx):
    """A section divider: wavy ribbon, dots, or a batik band (kawung, truntum, mega-mendung, sekar-jagad)."""
    if ctx.pal.style == 'komik':
        from ._komik_divider import render; return render(opts, ctx)
    pal = ctx.pal
    style = str(opts.get('style') or 'wave').strip().lower().replace('_', '-').replace(' ', '-')
    style = {'megamendung': 'mega-mendung', 'mega': 'mega-mendung', 'sekarjagad': 'sekar-jagad',
             'sekar': 'sekar-jagad', 'dot': 'dots'}.get(style, style)
    if style in NOT_OFFERED or style.startswith('parang'):
        raise ValueError(f'style "{style}" is not offered: parang/lereng and other court-restricted '
                         f'("larangan") motifs are left out on purpose. Try: {", ".join(STYLES)}')
    if style not in STYLES:
        raise ValueError(f'unknown style "{style}". Try: {", ".join(STYLES)}')
    seed = opts.get('seed')
    rng = random.Random(ctx.seed if seed in (None, '') else int(seed))
    h = opts.get('height')
    low = 40 if style in ('wave', 'dots') else 60  # batik needs room for its motif
    h = AUTO_H[style] if h in (None, '', 'auto', 0) else max(low, min(140, int(h)))
    cols = [pal.color(c) for c in (opts.get('colors') or [])] or list(pal.accents)
    k = Kit(pal, h, bool(opts.get('animate', True)), rng)

    if style == 'wave':
        body, css, defs = _wave(k, cols)
    elif style == 'dots':
        body, css, defs = _dots(k, cols)
    else:
        ground, fills = _split(cols, opts.get('ground'), pal, rng)
        motif, mdefs = {'kawung': _kawung, 'truntum': _truntum, 'mega-mendung': _mega,
                        'sekar-jagad': _sekar}[style](k, ground, fills)
        body, css, defs = k.band(ground, motif, mdefs)

    title = f'{NAMES[style]} divider'
    return Out(svg=doc(W, h, body, title=title, desc=f'A decorative {NAMES[style]} section divider.',
                       css=css, extra_defs=defs),
               alt=title[0].upper() + title[1:])


# ---------------------------------------------------------------- small helpers

def n(v):
    """Short number for SVG text."""
    s = f'{v:.1f}'
    if s.endswith('.0'):
        s = s[:-2]
    return '0' if s == '-0' else s


def _rgb(c):
    c = c.lstrip('#')
    if len(c) == 3:
        c = ''.join(ch * 2 for ch in c)
    return tuple(int(c[i:i + 2], 16) for i in (0, 2, 4))


def lum(c):
    def ch(v):
        v /= 255
        return v / 12.92 if v <= .04045 else ((v + .055) / 1.055) ** 2.4
    r, g, b = _rgb(c)
    return .2126 * ch(r) + .7152 * ch(g) + .0722 * ch(b)


def mix(a, b, t):
    ra, rb = _rgb(a), _rgb(b)
    return '#' + ''.join(f'{round(x + (y - x) * t):02X}' for x, y in zip(ra, rb))


def _split(cols, ground, pal, rng):
    """Pick the band's base colour (a darker one, so cream lines read on it) and the fills."""
    cols = list(dict.fromkeys(c.upper() for c in cols))
    if ground:
        g = pal.color(ground).upper()
    else:
        dark = sorted(cols, key=lum)
        pool = [c for c in dark if lum(c) < .36] or dark[:1]
        g = rng.choice(pool[:2])
    fills = [c for c in cols if c != g] or [mix(g, pal.color('cream', '#FFF6E5'), .55)]
    rng.shuffle(fills)
    return g, fills


class Kit:
    """Shared geometry, colours and animation attributes for one render."""

    def __init__(self, pal, h, animate, rng):
        self.pal, self.h, self.anim, self.rng = pal, h, animate, rng
        self.delays = {}
        self.cream = pal.color('cream', '#FFF6E5')
        self.ink = pal.color('ink', '#2B2340')
        self.bx, self.by = 12, 8
        self.bw, self.bh = W - 28, h - 22

    # animation attributes -------------------------------------------------------
    def t(self, x):
        """Draw-in start time for something at x: the canting moves left to right."""
        return .3 + 1.15 * max(0, min(1, (x - self.bx) / self.bw))

    def _at(self, cls, when):
        """class="dr d7": delays are shared classes in steps of 0.1 s, which keeps the file small."""
        if not self.anim:
            return ''
        key = round(when * 10)
        self.delays[key] = 1
        return f' class="{cls} d{key}"'

    def draw(self, x, extra=0):
        return self._at('dr', self.t(x) + extra)

    def pop(self, x, extra=.3):
        return self._at('pp', self.t(x) + extra)

    def css(self, idle=''):
        if not self.anim:
            return ''
        return (
            '.un{transform-origin:%spx 0;animation:un .6s cubic-bezier(.3,1.25,.5,1) both}'
            '@keyframes un{from{transform:scaleX(0)}}'
            '.dr{stroke-dasharray:1 1;animation:dr .9s cubic-bezier(.45,0,.55,1) both}'
            '@keyframes dr{from{stroke-dashoffset:1}to{stroke-dashoffset:0}}'
            '.pp{animation:pp .5s cubic-bezier(.5,-0.4,.5,1.4) both}'
            '@keyframes pp{from{transform:scale(0)}}' % self.bx) + idle + ''.join(
            f'.d{k}{{animation-delay:{k / 10:g}s}}' for k in sorted(self.delays))

    # the batik band ---------------------------------------------------------------
    def band(self, ground, motif, defs):
        bx, by, bw, bh, cream = self.bx, self.by, self.bw, self.bh, self.cream
        r = min(16, bh / 2)
        rect = f'<rect x="{bx}" y="{by}" width="{bw}" height="{n(bh)}" rx="{n(r)}" fill="{ground}"/>'
        i = 4.5
        inner = (f'<rect x="{n(bx + i)}" y="{n(by + i)}" width="{n(bw - 2 * i)}" height="{n(bh - 2 * i)}" '
                 f'rx="{n(r - i)}" fill="none" stroke="{cream}" stroke-width="1.5"/>')
        defs += (f'<clipPath id="bc"><rect x="{n(bx + i)}" y="{n(by + i)}" width="{n(bw - 2 * i)}" '
                 f'height="{n(bh - 2 * i)}" rx="{n(r - i)}"/></clipPath>')
        glints, idle = self.glints()
        body = (f'<g class="un">{sticker(rect, self.pal)}<g clip-path="url(#bc)">{motif}</g>{inner}</g>'
                f'{glints}')
        return body, self.css(idle), defs

    def glints(self, count=3):
        """A very quiet idle shimmer: a few cream sparkles that pop now and then."""
        if not self.anim:
            return '', ''
        rng, out = self.rng, []
        star = 'M0 -6Q1 -1 6 0Q1 1 0 6Q-1 1 -6 0Q-1 -1 0 -6Z'
        slots = rng.sample(range(count * 3), count)
        for j, s in enumerate(sorted(slots)):
            x = self.bx + 30 + (self.bw - 60) * (s + rng.uniform(.2, .8)) / (count * 3)
            y = self.by + rng.choice((2, self.bh - 2))
            out.append(f'<g transform="translate({n(x)} {n(y)})"><path class="tw" '
                       f'style="animation-delay:{2.6 + j * 2.1 + rng.uniform(0, .8):.2f}s" d="{star}" '
                       f'fill="{self.cream}" stroke="{self.ink}" stroke-width="1"/></g>')
        idle = ('.tw{transform:scale(0);animation:tw 6.3s ease-in-out infinite}'
                '@keyframes tw{0%,84%,100%{transform:scale(0)}90%{transform:scale(1) rotate(45deg)}}')
        return ''.join(out), idle


# ---------------------------------------------------------------- wave

def _wave_d(x0, x1, y, amp, period, phase):
    """y + amp*sin(...) from x0 to x1 as cubic Béziers, one per quarter wave (Hermite fit)."""
    steps = max(8, int((x1 - x0) / (period / 4)))
    q = (x1 - x0) / steps
    def f(t):
        return y + amp * math.sin(2 * math.pi * (t - x0) / period + phase * 2 * math.pi)
    def df(t):
        return amp * 2 * math.pi / period * math.cos(2 * math.pi * (t - x0) / period + phase * 2 * math.pi)
    d = f'M{n(x0)} {n(f(x0))}'
    for i in range(steps):
        a, b = x0 + i * q, x0 + (i + 1) * q
        c1 = (a + q / 3, f(a) + df(a) * q / 3)
        c2 = (b - q / 3, f(b) - df(b) * q / 3)
        d += f'C{n(c1[0])} {n(c1[1])} {n(c2[0])} {n(c2[1])} {n(b)} {n(f(b))}'
    return d


def _wave(k, cols):
    rng, pal, h = k.rng, k.pal, k.h
    cols = list(dict.fromkeys(c.upper() for c in cols))
    rng.shuffle(cols)
    ns = max(1, min(4, len(cols)))
    stripes = cols[:ns]
    sp = min(5.0, (h - 28) / (ns + 1.6))
    cream_w = ns * sp + 7
    amp = min(9, (h - cream_w - 14) / 2)
    period = (W - 80) / rng.choice((5, 5.5, 6, 6.5, 7))
    phase = rng.choice((0, .5))
    y = h / 2 - 2
    d = _wave_d(40, W - 40, y, amp, period, phase)
    defs = f'<path id="wv" d="{d}" pathLength="1" fill="none" stroke-linecap="round" stroke-linejoin="round"/>'
    cls = ' class="dr"' if k.anim else ''
    sh = (f'<use href="#wv" transform="translate({n(pal.shadow_dx)} {n(pal.shadow_dy)})" stroke="{pal.shadow}" '
          f'stroke-width="{n(cream_w)}" opacity="{n(pal.shadow_opacity)}"{cls}/>')
    body = sh + f'<use href="#wv" stroke="{k.cream}" stroke-width="{n(cream_w)}"{cls}/>'
    for i, c in enumerate(stripes):
        off = (i - (ns - 1) / 2) * sp
        body += (f'<use href="#wv" transform="translate(0 {n(off)})" stroke="{c}" '
                 f'stroke-width="{n(sp + .2)}"{cls}/>')
    body = f'<g class="bob">{body}</g>'
    css = ''
    if k.anim:
        css = ('.dr{stroke-dasharray:1 1;animation:dr 1.8s cubic-bezier(.45,0,.4,1) both}'
               '@keyframes dr{from{stroke-dashoffset:1}to{stroke-dashoffset:0}}'
               '.bob{animation:bob 5s ease-in-out 1.8s infinite}'
               '@keyframes bob{0%,100%{transform:translateY(0)}50%{transform:translateY(-1.5px)}}')
    return body, css, defs


# ---------------------------------------------------------------- dots

def _dots(k, cols):
    rng, pal, h = k.rng, k.pal, k.h
    cols = list(dict.fromkeys(c.upper() for c in cols))
    rng.shuffle(cols)
    big = min(11.5, (h - 24) / 2.6)
    small = big * .52
    gap = max(26, big * 3.1)
    count = int((W - 60) / gap)
    x0 = (W - (count - 1) * gap) / 2
    y = h / 2 - 2
    amp = min(5, (h - 2 * big - 20) / 2)
    phase = rng.uniform(0, 2 * math.pi)
    breathe = set(rng.sample(range(count), min(4, count)))
    out = []
    for i in range(count):
        x = x0 + i * gap
        yy = y + amp * math.sin(i * .9 + phase)
        r = big if i % 2 == 0 else small
        c = cols[i % len(cols)]
        dot = f'<circle r="{n(r)}" fill="{c}"/>'
        hl = (f'<circle cx="{n(-r * .35)}" cy="{n(-r * .35)}" r="{n(r * .22)}" fill="{k.cream}"/>'
              if r == big else '')
        inner = sticker(dot, pal) + hl
        if k.anim:
            d = .15 + 1.4 * i / max(1, count - 1)
            inner = f'<g class="pp" style="animation-delay:{d:.2f}s">{inner}</g>'
            if i in breathe:
                inner = f'<g class="br" style="animation-delay:{2.4 + rng.uniform(0, 3):.2f}s">{inner}</g>'
        out.append(f'<g transform="translate({n(x)} {n(yy)})">{inner}</g>')
    css = ''
    if k.anim:
        css = ('.pp{animation:pp .5s cubic-bezier(.5,-0.4,.5,1.4) both}@keyframes pp{from{transform:scale(0)}}'
               '.br{animation:br 4.2s ease-in-out infinite}'
               '@keyframes br{0%,70%,100%{transform:scale(1)}80%{transform:scale(1.14)}}')
    return ''.join(out), css, ''


# ---------------------------------------------------------------- kawung

def _ellipse(cx, cy, a, b):
    return (f'M{n(cx - a)} {n(cy)}A{n(a)} {n(b)} 0 1 1 {n(cx + a)} {n(cy)}'
            f'A{n(a)} {n(b)} 0 1 1 {n(cx - a)} {n(cy)}Z')


def _kawung(k, ground, fills):
    rng, cream, ink = k.rng, k.cream, k.ink
    ih = k.bh - 9
    # lattice size (seeded): the middle row always fits, rows above and below are cut by the frame
    s = max(46, ih * rng.choice((.96, 1.04, 1.12, 1.2)))
    fat = rng.uniform(.64, .74)
    c, a = .25 * s, .222 * s
    b = a * fat
    rot = ''.join(f'<use href="#{{0}}" transform="rotate({r})"/>' for r in (0, 90, 180, 270))
    defs = (f'<path id="kp" d="{_ellipse(c, 0, a, b)}" pathLength="1"/>'
            f'<path id="ki" d="M{n(c - a * .55)} 0Q{n(c)} {n(-b * .6)} {n(c + a * .55)} 0Q{n(c)} {n(b * .6)} '
            f'{n(c - a * .55)} 0Z" pathLength="1"/>'
            f'<g id="kf">{rot.format("kp")}</g>'
            f'<g id="kl" fill="none" stroke="{cream}" stroke-width="2.4" stroke-linejoin="round" '
            f'stroke-linecap="round">{rot.format("kp")}<g stroke-width="1.3">{rot.format("ki")}</g></g>'
            f'<g id="kc"><circle r="{n(s * .06)}" fill="{cream}"/><circle r="{n(s * .025)}" fill="{ink}"/></g>'
            f'<path id="ks" d="M0 -{n(s * .075)}Q0 0 {n(s * .075)} 0Q0 0 0 {n(s * .075)}Q0 0 -{n(s * .075)} 0'
            f'Q0 0 0 -{n(s * .075)}Z" fill="{cream}"/>')
    cy = k.by + k.bh / 2
    off = rng.uniform(0, s / 2)
    rows = int(k.bh / s) + 2
    # colours: the middle row walks through the fills, the others share a softer tint
    scheme = rng.choice(('walk', 'pair'))
    tint = mix(ground, cream, rng.choice((.35, .5)))
    out, stars = [], []
    i, j = -1, 0
    reach = (k.bh - 9) / 2 + c + a  # rows further out than this are hidden by the frame
    while k.bx + off + i * s / 2 < k.bx + k.bw + s / 2:
        x = k.bx + off + i * s / 2
        fl, ln = '', ''
        for m in range(-rows, rows + 1):
            for dy, kind in ((m * s + (i % 2) * s / 2, 'f'), (m * s + ((i + 1) % 2) * s / 2, 's')):
                if abs(dy) > reach:
                    continue
                if kind == 's':
                    stars.append(f'<use href="#ks" x="{n(x)}" y="{n(cy + dy)}"/>')
                    continue
                if abs(dy) < 1:
                    col = fills[j % len(fills)] if scheme == 'walk' else fills[j % min(2, len(fills))]
                    j += 1
                else:
                    col = tint if scheme == 'walk' or len(fills) < 3 else fills[2]
                yy = f' y="{n(dy)}"' if dy else ''
                fl += f'<use href="#kf"{yy} fill="{col}"/><use href="#kc"{yy}/>'
                ln += f'<use href="#kl"{yy}/>'
        # one column at a time: its lines draw, then its ovals are "dyed" in
        out.append(f'<g transform="translate({n(x)} {n(cy)})"><g{k.pop(x, .45)}>{fl}</g><g{k.draw(x)}>{ln}</g></g>')
        i += 1
    return ''.join(out) + ''.join(stars), defs


# ---------------------------------------------------------------- truntum

def _blossom(petals, R, r_in, spread=.62):
    """One closed outline of a small star flower: a single subpath so it draws in one stroke."""
    step = 2 * math.pi / petals
    d = ''
    for i in range(petals):
        th = i * step - math.pi / 2
        v0 = (r_in * math.cos(th - step / 2), r_in * math.sin(th - step / 2))
        v1 = (r_in * math.cos(th + step / 2), r_in * math.sin(th + step / 2))
        sp = step / 2 * spread
        c1 = (R * 1.22 * math.cos(th - sp), R * 1.22 * math.sin(th - sp))
        c2 = (R * 1.22 * math.cos(th + sp), R * 1.22 * math.sin(th + sp))
        if i == 0:
            d += f'M{n(v0[0])} {n(v0[1])}'
        d += f'C{n(c1[0])} {n(c1[1])} {n(c2[0])} {n(c2[1])} {n(v1[0])} {n(v1[1])}'
    return d + 'Z'


def _truntum(k, ground, fills):
    rng, cream, ink = k.rng, k.cream, k.ink
    bh = k.bh
    units = max(1, round((bh - 9) / 52))  # tall bands get more rows of the same two-row unit
    ih = (bh - 9) / units
    R = ih * .23
    defs = (f'<path id="t8" d="{_blossom(8, R, R * .38)}" pathLength="1"/>'
            f'<path id="t6" d="{_blossom(6, R * .82, R * .36, .7)}" pathLength="1"/>'
            + ''.join(f'<use id="t{p}l" href="#t{p}" fill="none" stroke="{cream}" stroke-width="2" '
                      f'stroke-linejoin="round"/>' for p in (6, 8)) +
            f'<path id="t4" d="M0 -{n(R * .5)}Q{n(R * .1)} -{n(R * .1)} {n(R * .5)} 0Q{n(R * .1)} {n(R * .1)} 0 '
            f'{n(R * .5)}Q-{n(R * .1)} {n(R * .1)} -{n(R * .5)} 0Q-{n(R * .1)} -{n(R * .1)} 0 -{n(R * .5)}Z" '
            f'fill="{cream}"/>'
            f'<g id="tc"><circle r="{n(R * .3)}" fill="{cream}"/><circle r="{n(R * .13)}" fill="{ink}"/></g>'
            f'<g id="td" fill="{cream}"><circle cx="0" cy="-{n(R * .3)}" r="{n(R * .1)}"/>'
            f'<circle cx="{n(R * .26)}" cy="{n(R * .15)}" r="{n(R * .1)}"/>'
            f'<circle cx="-{n(R * .26)}" cy="{n(R * .15)}" r="{n(R * .1)}"/></g>'
            f'<use id="te" href="#td" transform="scale(.75)"/>')
    gx = max(25, ih * rng.uniform(.56, .64))
    dy = ih * .25
    out, j = [], 0
    for u in range(units):
        cy = k.by + 4.5 + ih * (u + .5)
        off = rng.uniform(0, gx)
        x = k.bx + off - gx
        i = 0
        while x < k.bx + k.bw + gx:
            up = i % 2 == 0
            y = cy + (-dy if up else dy) + rng.uniform(-1.5, 1.5)
            xx = x + rng.uniform(-2.5, 2.5)
            sc = rng.uniform(.9, 1.06)
            rot = rng.uniform(0, 45)
            kind = 't8' if rng.random() < .65 else 't6'
            col = fills[j % len(fills)]
            j += 1
            out.append(f'<g transform="translate({n(xx)} {n(y)}) rotate({n(rot)}) scale({sc:.2f})">'
                       f'<g{k.pop(xx, .4)}><use href="#{kind}" fill="{col}"/><use href="#tc"/></g>'
                       f'<use href="#{kind}l"{k.draw(xx)}/></g>')
            # between two blossoms: a tiny star or a three-dot "cecek"; at the free edge spot, dots
            fx = x + gx / 2 + rng.uniform(-2, 2)
            filler = 't4' if rng.random() < .6 else 'td'
            out.append(f'<g transform="translate({n(fx)} {n(cy + rng.uniform(-2, 2))}) rotate({rng.randint(0, 90)})">'
                       f'<use href="#{filler}"{k.pop(fx, .7)}/></g>')
            ey = cy + (dy if up else -dy) * 1.12
            out.append(f'<use href="#te" x="{n(x)}" y="{n(ey)}"/>')
            x += gx
            i += 1
    return ''.join(out), defs


# ---------------------------------------------------------------- mega mendung

def _cloud(rng, w, h):
    """A lobed cloud outline: big lobes on top, small ones underneath, cusps between."""
    a, b = w / 2, h / 2
    top = rng.choice((3, 4))
    bot = top + rng.choice((1, 2))
    angs = []
    # screen coords: angle pi..2pi is the upper half; go clockwise starting at the left
    for i in range(top):
        angs.append(math.pi + math.pi * (i + rng.uniform(-.12, .12) * (0 < i)) / top)
    for i in range(bot):
        angs.append(2 * math.pi + math.pi * (i + rng.uniform(-.12, .12) * (0 < i)) / bot)
    pts = []
    for t in angs:
        rr = 1 + rng.uniform(-.05, .05)
        ry = b * (1 if math.sin(t) < 0 else .78)
        pts.append((a * rr * math.cos(t), ry * rr * math.sin(t) + (0 if math.sin(t) < 0 else -b * .05)))
    d = f'M{n(pts[0][0])} {n(pts[0][1])}'
    for i in range(len(pts)):
        p, q = pts[i], pts[(i + 1) % len(pts)]
        chord = math.dist(p, q)
        # upper lobes are near half circles, so the cusps between them dip in sharply
        r = chord * (rng.uniform(.5, .54) if i < top else rng.uniform(.6, .7))
        d += f'A{n(r)} {n(r)} 0 0 1 {n(q[0])} {n(q[1])}'
    return d + 'Z'


def _mega(k, ground, fills):
    rng, cream, ink = k.rng, k.cream, k.ink
    bh = k.bh
    N = rng.randint(3, 7)
    ch = max(34, (bh - 9) * .66)
    # cloud colour families: traditional mega mendung is blue or red; pale yellows go muddy
    fam = ([c for c in fills if lum(c) < .6] or fills)[:2]
    defs = ''
    variants = 3
    for v in range(variants):
        cw = ch * rng.uniform(1.75, 2.2)
        defs += (f'<path id="m{v}" d="{_cloud(rng, cw, ch)}" pathLength="1"/>'
                 f'<clipPath id="c{v}"><use href="#m{v}"/></clipPath>')
    # band width so the lightest core keeps some room
    dd = min(4.2, ch * .36 / N)
    for f, base in enumerate(fam):
        dark = mix(base, ink, .3 if lum(base) < .45 else .2)
        light = mix(base, cream, .88)
        steps = [mix(dark, light, j / (N - 1)) for j in range(N)]
        for v in range(variants):
            g = f'<use href="#m{v}" fill="{steps[-1]}"/>'
            for j in range(N - 2, -1, -1):
                g += (f'<use href="#m{v}" fill="none" stroke="{steps[j]}" '
                      f'stroke-width="{n(2 * (j + 1) * dd)}"/>')
            defs += f'<g id="g{v}{f}"><g clip-path="url(#c{v})">{g}</g></g>'
    cy = k.by + bh / 2
    step = ch * 1.45
    x = k.bx + rng.uniform(-step * .4, 0)
    out, i = [], 0
    vs = list(range(variants))
    rng.shuffle(vs)
    while x < k.bx + k.bw + step * .5:
        v = vs[i % variants]
        f = (i // 2) % len(fam) if len(fam) > 1 else 0
        y = cy + (bh * .1 if i % 2 else -bh * .07) + rng.uniform(-1.5, 1.5)
        flip = -1 if (i + (rng.random() < .3)) % 2 else 1
        out.append(f'<g transform="translate({n(x)} {n(y)}) scale({flip} 1)">'
                   f'<use href="#g{v}{f}"{k.pop(x, .4)}/>'
                   f'<use href="#m{v}" fill="none" stroke="{cream}" stroke-width="2.6" '
                   f'stroke-linejoin="round"{k.draw(x)}/></g>')
        x += step * rng.uniform(.85, 1.05)
        i += 1
    return ''.join(out), defs


# ---------------------------------------------------------------- sekar jagad

def _patterns(k):
    """Small fill patterns, one mini-motif each, drawn in a given colour."""
    def tile(pid, w, h, body):
        return (f'<pattern id="{pid}" width="{w}" height="{h}" patternUnits="userSpaceOnUse">'
                f'{body}</pattern>')
    return {
        'cecek': lambda pid, c: tile(pid, 10, 10, f'<g fill="{c}"><circle cx="2.5" cy="2.5" r="1.5"/>'
                                                  f'<circle cx="7.5" cy="7.5" r="1.5"/></g>'),
        'sisik': lambda pid, c: tile(pid, 12, 10, f'<path d="M0 10A6 6 0 0 1 12 10M-6 5A6 6 0 0 1 6 5M6 5A6 6 0 0 1 18 5" '
                                                  f'fill="none" stroke="{c}" stroke-width="1.3"/>'),
        'kawung': lambda pid, c: tile(pid, 14, 14, f'<g fill="{c}" transform="rotate(45 7 7)">'
                                                   f'<ellipse cx="4" cy="7" rx="2.4" ry="1.5"/>'
                                                   f'<ellipse cx="10" cy="7" rx="2.4" ry="1.5"/>'
                                                   f'<ellipse cx="7" cy="4" rx="1.5" ry="2.4"/>'
                                                   f'<ellipse cx="7" cy="10" rx="1.5" ry="2.4"/></g>'),
        'kembang': lambda pid, c: tile(pid, 14, 14, f'<g fill="{c}"><circle cx="5" cy="7" r="1.7"/>'
                                                    f'<circle cx="9" cy="7" r="1.7"/><circle cx="7" cy="5" r="1.7"/>'
                                                    f'<circle cx="7" cy="9" r="1.7"/></g>'),
        'gringsing': lambda pid, c: tile(pid, 10, 17, f'<g fill="none" stroke="{c}" stroke-width="1.1">'
                                                      f'<circle cx="5" cy="4.25" r="3.4"/><circle cx="0" cy="12.75" r="3.4"/>'
                                                      f'<circle cx="10" cy="12.75" r="3.4"/></g><g fill="{c}">'
                                                      f'<circle cx="5" cy="4.25" r="1"/><circle cx="0" cy="12.75" r="1"/>'
                                                      f'<circle cx="10" cy="12.75" r="1"/></g>'),
        'ukel': lambda pid, c: tile(pid, 14, 12, f'<path d="M3 8.5a3.2 3.2 0 1 1 3.2 -3.2a1.6 1.6 0 1 1 -1.6 -1.6" '
                                                 f'fill="none" stroke="{c}" stroke-width="1.2" stroke-linecap="round"/>'),
        'ombak': lambda pid, c: tile(pid, 16, 7, f'<path d="M0 3.5Q4 0 8 3.5T16 3.5" fill="none" stroke="{c}" '
                                                 f'stroke-width="1.3"/>'),
    }


def _sekar(k, ground, fills):
    rng, cream, ink = k.rng, k.cream, k.ink
    top, bot = k.by - 4, k.by + k.bh + 4
    cy = k.by + k.bh / 2
    # vertical boundaries: three points each (top, middle, bottom), joined by S-curves
    xs = [k.bx - 30]
    while xs[-1] < k.bx + k.bw + 10:
        xs.append(xs[-1] + rng.uniform(58, 96))
    bounds = []
    for i, x in enumerate(xs):
        wob = 0 if i in (0, len(xs) - 1) else 11
        bounds.append(((x + rng.uniform(-wob, wob), top), (x + rng.uniform(-wob, wob), cy + rng.uniform(-6, 6)),
                       (x + rng.uniform(-wob, wob), bot)))

    def seg(p, q):  # S-curve between p and q with vertical tangents
        my = (q[1] - p[1]) / 2
        return f'C{n(p[0])} {n(p[1] + my)} {n(q[0])} {n(q[1] - my)} {n(q[0])} {n(q[1])}'

    def hseg(p, q, w):  # left-right curve with horizontal tangents
        dx = (q[0] - p[0]) / 3
        return f'C{n(p[0] + dx)} {n(p[1] + w)} {n(q[0] - dx)} {n(q[1] - w)} {n(q[0])} {n(q[1])}'

    pats = _patterns(k)
    names = list(pats)
    rng.shuffle(names)
    used, defs = {}, ''
    cells, lines = [], []
    last_name, last_col, ci = None, None, 0
    for i in range(len(bounds) - 1):
        L, R = bounds[i], bounds[i + 1]
        lines.append((L, i))
        split = rng.random() < .55 and (R[1][0] - L[1][0]) > 50
        if split:
            w = rng.uniform(-6, 6)
            d_up = (f'M{n(L[0][0])} {n(L[0][1])}L{n(R[0][0])} {n(R[0][1])}' + seg(R[0], R[1])
                    + hseg(R[1], L[1], -w) + seg(L[1], L[0]) + 'Z')
            d_dn = (f'M{n(L[1][0])} {n(L[1][1])}' + hseg(L[1], R[1], w) + seg(R[1], R[2])
                    + f'L{n(L[2][0])} {n(L[2][1])}' + seg(L[2], L[1]) + 'Z')
            parts = [(d_up, (L[0][1] + L[1][1]) / 2 - 2), (d_dn, (L[1][1] + L[2][1]) / 2 + 2)]
            lines.append(('h', L[1], R[1], w))
        else:
            d = (f'M{n(L[0][0])} {n(L[0][1])}L{n(R[0][0])} {n(R[0][1])}' + seg(R[0], R[1]) + seg(R[1], R[2])
                 + f'L{n(L[2][0])} {n(L[2][1])}' + seg(L[2], L[1]) + seg(L[1], L[0]) + 'Z')
            parts = [(d, cy)]
        cx = (L[1][0] + R[1][0]) / 2
        for d, ccy in parts:
            choices = [c for c in fills if c != last_col] or fills
            col = choices[ci % len(choices)]
            ci += 1
            last_col = col
            pn = [p for p in names if p != last_name][rng.randrange(len(names) - 1)]
            last_name = pn
            tone = 'i' if lum(col) > .42 else 'c'
            pid = f'p{names.index(pn)}{tone}'
            if pid not in used:
                used[pid] = 1
                defs += pats[pn](pid, ink if tone == 'i' else cream)
            cells.append(f'<g transform="translate({n(cx)} {n(ccy)})"><g{k.pop(cx, .35)}>'
                         f'<g transform="translate({n(-cx)} {n(-ccy)})"><path d="{d}" fill="{col}"/>'
                         f'<path d="{d}" fill="url(#{pid})"/></g></g></g>')
    # boundaries drawn last: a cream double line like the outlined "islands" of the cloth
    lpaths = []
    for item in lines:
        if item[0] == 'h':
            _, p, q, w = item
            d = f'M{n(p[0])} {n(p[1])}' + hseg(p, q, w)
            x = p[0]
        else:
            b, i = item
            if i == 0:
                continue
            d = f'M{n(b[0][0])} {n(b[0][1])}' + seg(b[0], b[1]) + seg(b[1], b[2])
            x = b[1][0]
        lpaths.append((d, x))
    lines_svg = ''.join(f'<path d="{d}" pathLength="1"{k.draw(x, .1)}/>' for d, x in lpaths)
    out = (''.join(cells)
           + f'<g fill="none" stroke="{cream}" stroke-width="6.5" stroke-linecap="round">{lines_svg}</g>'
           + f'<g fill="none" stroke="{ground}" stroke-width="2" stroke-linecap="round">{lines_svg}</g>')
    return out, defs
