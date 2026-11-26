"""garden ("Kebun Pernik"): the tech stack drawn as an illustrated garden. Used by garden.py.

One Indonesian tree per group of tools, and the tools are the fruit:

    mangga (mango)      a dome of small pointed leaves; fruits on stalks with a spot leaf
    kelapa (coconut)    a leaning ringed trunk, arching fronds, coconuts clustered under the crown
    rambutan            a bumpy round crown; hairy fruits
    pisang (banana)     a pseudostem with big torn paddle leaves, a hanging bunch and its jantung

Each fruit is a paper badge with an ink outline and the logo in ink. A wooden marker planted in
the soil names each tree (two planks when the name is long). The banana mascot stands on a
bamboo ladder by one tree; with harvest on it picks fruit after fruit (up to MAX_PICKS different
ones, one CYCLE each) and drops them into the bakul it carries, while each picked fruit grows
back on the branch. The day print has a sun, the night print a moon (it shows the printing).

    from pernik.widgets._garden import render
    out = render(trees, ctx, harvest=True, mascot='banana')
    # trees = [{'name': ..., 'tree': 'mangga', 'icons': [...], 'logos': {...}}, ...]

Layout: 1-6 trees across the 900-px card. Each crown or bunch sizes itself to its fruit count
(fruits never overlap); when the trees don't fit side by side the crowns grow taller and
narrower, then the fruit shrinks a little (never below 24 px), and the card grows up to 480 px.

Rules: docs/design.md. Only paper / ink / spot / tint and their halftones; 4 / 2.5 / 1.5 lines.
Size: shapes used more than once live in <defs> and are drawn with <use>; scene coordinates are
whole pixels and logos are re-quantised to a 1/100 grid.
"""
import math
import random

from .. import komik as K
from ..mascots.banana_komik import BODY, SHADE, STEM
from . import Out
from ._komik_heading import fit_label, label_text, label_width, n
from ._komik_stack import _parse
from .stack import _index, resolve

W = 900
SIDE = 20                 # room between the card frame and the outermost tree
GAP = 10                  # least room between two trees
H_MIN, H_MAX = 360, 480
SOIL = 64                 # ground line to the bottom of the card
SKY = 16                  # least room above the tallest tree
MAX_TREES = 6
MAX_FRUIT = 18
MAX_PICKS = 4
CYCLE = 6.5               # seconds per pick
KINDS = ('mangga', 'kelapa', 'rambutan', 'pisang')
TREE_EN = {'mangga': 'mango tree', 'kelapa': 'coconut palm', 'rambutan': 'rambutan tree', 'pisang': 'banana plant'}
LOGO_FIT = 3.5            # px between the logo's corner and the badge's rim


# ---------------------------------------------------------------------------- numbers & paths
def I(v):
    return str(int(round(v)))


def P(x, y):
    return f'{I(x)} {I(y)}'


def poly(pts):
    return 'M' + 'L'.join(P(x, y) for x, y in pts) + 'Z'


def smooth(pts, closed=True, t=1 / 6):
    """Catmull-Rom through pts, as cubic Beziers (whole pixels)."""
    N = len(pts)
    get = (lambda i: pts[i % N]) if closed else (lambda i: pts[max(0, min(N - 1, i))])
    d = ['M' + P(*pts[0])]
    for i in range(N if closed else N - 1):
        p0, p1, p2, p3 = get(i - 1), get(i), get(i + 1), get(i + 2)
        c1 = (p1[0] + (p2[0] - p0[0]) * t, p1[1] + (p2[1] - p0[1]) * t)
        c2 = (p2[0] - (p3[0] - p1[0]) * t, p2[1] - (p3[1] - p1[1]) * t)
        d.append(f'C{P(*c1)} {P(*c2)} {P(*p2)}')
    return ''.join(d) + ('Z' if closed else '')


def qb(p0, c, p1, t):
    """Point and unit tangent on a quadratic Bezier."""
    u = 1 - t
    x = u * u * p0[0] + 2 * u * t * c[0] + t * t * p1[0]
    y = u * u * p0[1] + 2 * u * t * c[1] + t * t * p1[1]
    dx = 2 * u * (c[0] - p0[0]) + 2 * t * (p1[0] - c[0])
    dy = 2 * u * (c[1] - p0[1]) + 2 * t * (p1[1] - c[1])
    m = math.hypot(dx, dy) or 1
    return (x, y), (dx / m, dy / m)


def ease(t):
    t = max(0.0, min(1.0, t))
    return t * t * (3 - 2 * t)


def _walk(d):
    """Absolute points of path data, segment by segment: [(cmd, [(x, y), ...], args)]."""
    out = []
    cx = cy = sx = sy = 0.0
    for c, v in _parse(d):
        rel, C = c.islower(), c.upper()
        ox, oy = (cx, cy) if rel else (0.0, 0.0)
        if C == 'Z':
            out.append((C, [], v))
            cx, cy = sx, sy
            continue
        if C == 'H':
            pts = [(v[0] + ox, cy)]
        elif C == 'V':
            pts = [(cx, v[0] + oy)]
        elif C == 'A':
            pts = [(v[5] + ox, v[6] + oy)]
        else:
            pts = [(v[j] + ox, v[j + 1] + oy) for j in range(0, len(v), 2)]
        out.append((C, pts, v))
        cx, cy = pts[-1]
        if C == 'M':
            sx, sy = cx, cy
    return out


def quantise(d, unit):
    """Path data on an integer grid of `unit`, as short relative commands; None if unparsable."""
    try:
        segs = _walk(d)
    except ValueError:
        return None
    q = lambda v: int(round(v / unit))
    out, st = [], {'cmd': '', 'tok': ''}
    qx = qy = qsx = qsy = 0

    def emit(cmd, nums):
        if cmd != st['cmd'] or cmd in 'mMz':
            out.append(cmd)
            st['tok'] = cmd
        for v in nums:
            t = str(v)
            out.append(t if (st['tok'][-1].isalpha() or t[0] == '-') else ' ' + t)
            st['tok'] = t
        st['cmd'] = cmd

    for C, pts, v in segs:
        if C == 'Z':
            emit('z', [])
            qx, qy = qsx, qsy
            continue
        qp = [(q(x) - qx, q(y) - qy) for x, y in pts]
        if C in 'LHVCSQT' and not any(a for p in qp for a in p):
            continue                       # nothing to draw at this grid
        if C == 'H':
            emit('h', [qp[0][0]])
        elif C == 'V':
            emit('v', [qp[0][1]])
        elif C == 'A':
            emit('a', [max(1, q(v[0])), max(1, q(v[1])), int(round(v[2])), int(v[3]), int(v[4]), *qp[0]])
        else:
            emit({'M': 'm' if out else 'M'}.get(C, C.lower()), [a for p in qp for a in p])
        qx, qy = q(pts[-1][0]), q(pts[-1][1])
        if C == 'M':
            qsx, qsy = qx, qy
    return ''.join(out)


def bbox(d):
    """Rough bounds of path data (end and control points), or None."""
    try:
        pts = [p for _, ps, _ in _walk(d) for p in ps]
    except ValueError:
        return None
    if not pts:
        return None
    xs, ys = [p[0] for p in pts], [p[1] for p in pts]
    return min(xs), min(ys), max(xs), max(ys)


def _mix(a, b, t):
    """Colour a mixed toward b by t (0..1), both '#rrggbb'."""
    ca = [int(a[i:i + 2], 16) for i in (1, 3, 5)]
    cb = [int(b[i:i + 2], 16) for i in (1, 3, 5)]
    return '#' + ''.join(f'{round(x + (y - x) * t):02X}' for x, y in zip(ca, cb))


def kit_for(ctx):
    """The komik Kit. Sticker themes have no [komik] table: print them as komik in the theme's
    first accent (and give them a proper night print, so the card never glares on dark pages)."""
    k = K.Kit(ctx.theme, ctx.mode)
    if ctx.pal.style == 'komik':
        return k
    spot = next((a for a in ctx.pal.accents if isinstance(a, str) and len(a) == 7 and a.startswith('#')), '#E0569B')
    if ctx.mode == 'dark':
        k.paper, k.ink, k.spot = '#161B22', '#A9B2BD', spot
        k.tint, k.shade, k.solid, k.on_solid = _mix(spot, '#161B22', .72), '#010409', _mix(spot, '#161B22', .55), '#F2E9EF'
    else:
        k.paper, k.ink, k.spot = '#FBF8F3', '#1E1A22', spot
        k.tint = _mix(spot, '#FBF8F3', .62)
        k.shade = k.solid = k.ink
        k.on_solid = k.paper
    return k


# ---------------------------------------------------------------------------- one tree
class Tree:
    def __init__(self, i, name, kind, items):
        self.i, self.name, self.kind, self.items = i, name, kind, items
        self.x = 0.0            # anchor (trunk base) x
        self.rel = []           # fruit centres relative to the anchor and the ground
        self.pick_ids = []      # indices of fruits picked by the banana, in order


# ---------------------------------------------------------------------------- the garden
class Garden:
    def __init__(self, k, seed):
        self.k = k
        self.rnd = random.Random(seed)
        self.uid = 0
        self.defs = []
        self.R, self.z = 17, 1.0
        self.H, self.GY = 448, 384

    def css(self):
        k = self.k
        return (f'.o,.oh,.l,.L{{stroke:{k.ink};stroke-linejoin:round;stroke-linecap:round}}'
                f'.o,.L{{stroke-width:2.5px}}.oh,.l{{stroke-width:1.5px}}.l,.L,.n{{fill:none}}'
                f'.p{{fill:{k.paper}}}.t{{fill:{k.tint}}}.k{{fill:{k.spot}}}.i{{fill:{k.ink}}}'
                '.d1{fill:url(#ht1)}.d2{fill:url(#ht2)}.di{fill:url(#hti)}')

    def shared(self, d):
        self.uid += 1
        sid = f'g{self.uid}'
        self.defs.append(f'<path id="{sid}" d="{d}"/>')
        return sid

    def clip_of(self, sid):
        self.defs.append(f'<clipPath id="c{sid}"><use href="#{sid}"/></clipPath>')
        return f'url(#c{sid})'

    @staticmethod
    def use(sid, cls, extra=''):
        return f'<use href="#{sid}" class="{cls}"{extra}/>'

    @staticmethod
    def path(d, cls, extra=''):
        return f'<path d="{d}" class="{cls}"{extra}/>'

    # ------------------------------------------------------------------ fruit
    def fruit_defs(self):
        R = self.R
        r1, r2 = R - 2.2, R + 3
        a1, a2 = math.radians(-15), math.radians(110)
        p1 = (r1 * math.cos(a1), r1 * math.sin(a1))
        p2 = (r1 * math.cos(a2), r1 * math.sin(a2))
        crescent = f'M{n(p1[0])} {n(p1[1])}A{n(r1)} {n(r1)} 0 0 1 {n(p2[0])} {n(p2[1])}A{n(r2)} {n(r2)} 0 0 0 {n(p1[0])} {n(p1[1])}Z'
        hair = ''.join(f'M{n((R - 1) * math.cos(a))} {n((R - 1) * math.sin(a))}'
                       f'L{n((R + 4.5) * math.cos(a + .22))} {n((R + 4.5) * math.sin(a + .22))}'
                       for a in (2 * math.pi * j / 18 + .1 for j in range(18)))
        stalk = lambda s: (f'<path d="M0 {-R}Q0 {-R - 6} {3 * s} {-R - 11}" class="L"/>'
                           f'<path d="M{3 * s} {-R - 9}q{7 * s} -9 {15 * s} -4q{-8 * s} 6 {-15 * s} 4z" class="k oh"/>')
        self.defs.append(
            f'<g id="fb"><circle r="{R}" class="p o"/><path d="{crescent}" class="d2"/></g>'
            f'<path id="fh" d="{hair}" class="l"/>'
            f'<g id="fm0">{stalk(1)}</g><g id="fm1">{stalk(-1)}</g>'
            f'<path id="fc" d="M-7 {-R + 1}Q0 {-R - 7} 7 {-R + 1}Q0 {-R + 4} -7 {-R + 1}Z" class="k oh"/>')

    def core(self, cx, cy, item, kind):
        """What gets picked: the badge and logo, with a rambutan's hairs or a coconut's cap
        (a mango's stalk and leaf stay on the branch)."""
        R = self.R
        title, d, box, _, rule = item
        at = f' x="{I(cx)}" y="{I(cy)}"'
        g = [f'<use href="#fh"{at}/>'] if kind == 'rambutan' else []
        g.append(f'<use href="#fb"{at}/>')
        if d:
            # fit the glyph itself (not its viewBox) into the round badge: a wide logo like
            # Docker or AWS gets wider, a tall one taller, nothing pokes past the rim
            gx0, gy0, gx1, gy1 = bbox(d) or (box[0], box[1], box[0] + box[2], box[1] + box[3])
            gw, gh = max(gx1 - gx0, 1e-3), max(gy1 - gy0, 1e-3)
            sc = min(2 * (R - LOGO_FIT) / math.hypot(gw, gh), (R * 1.3) / max(gw, gh))
            unit = max(gw, gh) / 100
            qd = quantise(d, unit)
            ox, oy = round(cx) - (gx0 + gx1) / 2 * sc, round(cy) - (gy0 + gy1) / 2 * sc
            if qd is None:
                qd, unit = d, 1
            fr = f' fill-rule="{rule}"' if rule else ''
            g.append(f'<path transform="translate({n(ox)} {n(oy)}) scale({sc * unit:.4g})" d="{qd}" class="i"{fr}/>')
        else:
            letter = next((ch for ch in title if ch.isalnum()), '?').upper()
            g.append(f'<text x="{I(cx)}" y="{I(cy + R * .35)}" font-size="{I(R)}" text-anchor="middle" class="kl i">'
                     f'{K.esc(letter)}</text>')
        if kind == 'kelapa':
            g.append(f'<use href="#fc"{at}/>')
        return ''.join(g)

    def fruit(self, cx, cy, item, kind, i, pick=None):
        """One tool as a fruit. A picked fruit's core is defined once (#fp<pick>) and drawn twice:
        on the branch (class gr<pick>, it regrows) and in the banana's hand (class gf<pick>)."""
        g = [f'<use href="#fm{i % 2}" x="{I(cx)}" y="{I(cy)}"/>'] if kind == 'mangga' else []
        if pick is None:
            g.append(self.core(cx, cy, item, kind))
        else:
            self.defs.append(f'<g id="fp{pick}">{self.core(0, 0, item, kind)}</g>')
            g.append(f'<g transform="translate({I(cx)} {I(cy)})"><g class="gr{pick}"><use href="#fp{pick}"/></g></g>')
        return f'<g class="arrive a{i % 8}"><title>{K.esc(item[0])}</title>{"".join(g)}</g>'

    # ------------------------------------------------------------------ fruit placement
    @staticmethod
    def spread(count, a, b, gap, rot, narrow=False):
        """Fruit centres inside an a x b ellipse (sunflower spread, then pushed apart), growing the
        ellipse (only taller when `narrow`) until no two are closer than `gap`. Returns (points, a, b)."""
        if count <= 0:
            return [], a, b
        if count == 1:
            return [(0.0, 0.0)], a, b
        ga = math.pi * (3 - math.sqrt(5))
        for _ in range(16):
            pts = [[a * math.sqrt((i + .6) / (count + .1)) * math.cos(i * ga + rot),
                    b * math.sqrt((i + .6) / (count + .1)) * math.sin(i * ga + rot)] for i in range(count)]
            for _ in range(90):
                moved = False
                for i in range(count):
                    for j in range(i + 1, count):
                        dx, dy = pts[j][0] - pts[i][0], pts[j][1] - pts[i][1]
                        dd = math.hypot(dx, dy) or .01
                        if dd < gap:
                            push = (gap - dd) / 2 + .2
                            pts[i][0] -= dx / dd * push; pts[i][1] -= dy / dd * push
                            pts[j][0] += dx / dd * push; pts[j][1] += dy / dd * push
                            moved = True
                for p in pts:
                    m = math.hypot(p[0] / a, p[1] / b)
                    if m > 1:
                        p[0], p[1] = p[0] / m, p[1] / m
                if not moved:
                    break
            pts = [(round(x), round(y)) for x, y in pts]
            if min(math.hypot(p[0] - q[0], p[1] - q[1]) for i, p in enumerate(pts) for q in pts[i + 1:]) >= gap - 2:
                return pts, a, b
            a, b = (a, b * 1.1) if narrow else (a * 1.06, b * 1.06)
        return pts, a, b

    @staticmethod
    def cluster(count, pitch, squeeze=.9):
        """A round cluster on a hex grid (the points nearest the centre); squeeze > 1 makes it
        taller and narrower."""
        cand = []
        for r in range(-8, 9):
            for q in range(-8, 9):
                x = pitch * (q + (r % 2) * .5)
                y = pitch * .87 * r
                cand.append((math.hypot(x * squeeze, y * 1.05), x, y))
        cand.sort()
        return sorted(((round(x), round(y)) for _, x, y in cand[:count]), key=lambda p: (p[1], p[0]))

    # ------------------------------------------------------------------ planning (sizes only)
    def plan(self, t, wmax):
        """Size tree t for at most wmax px of width: sets t.left / t.right (extent around the
        anchor), t.height (above the ground) and t.rel (fruit centres from (anchor, ground))."""
        getattr(self, 'plan_' + t.kind)(t, len(t.items), wmax)

    def plan_canopy(self, t, cnt, wmax, gap, aspect, mx, my, low, trunk, tip, minr, rot):
        R = self.R
        area = max(cnt, 1) * .8 * gap * gap
        a = math.sqrt(area / (math.pi * aspect))
        b = a * aspect
        amax = wmax / 2 - mx - tip
        narrow = a > amax
        if narrow:
            a = max(amax, R)
            b = max(b, area / (math.pi * a))
        rel, a, b = self.spread(cnt, a, b, gap, rot, narrow)
        rx, ry = max(a + mx, minr[0] * self.z), max(b + my, minr[1] * self.z)
        t.crown = (rx, ry, a, b)
        t.trunk_h = trunk
        cy = -(trunk + low * ry)                    # crown centre, from the ground
        t.cy = cy
        t.rel = [(x - 2, cy - 4 + y) for x, y in rel]
        t.left = t.right = rx + tip
        t.sky = [(-rx - tip, rx + tip, cy - ry - tip)]    # skyline: (x0, x1, top) from the anchor/ground
        t.height = trunk + (1 + low) * ry + tip
        t.top_y = cy - ry - tip

    def plan_mangga(self, t, cnt, wmax):
        R = self.R
        self.plan_canopy(t, cnt, wmax, gap=2 * R + 9, aspect=.78, mx=R + 13, my=R + 19, low=.72,
                         trunk=104, tip=9, minr=(70, 60), rot=.6)

    def plan_rambutan(self, t, cnt, wmax):
        R = self.R
        self.plan_canopy(t, cnt, wmax, gap=2 * R + 12, aspect=.86, mx=2 * R, my=2 * R, low=.86,
                         trunk=84, tip=0, minr=(66, 58), rot=2.1)

    def plan_kelapa(self, t, cnt, wmax):
        R = self.R
        pitch = 2 * R + 4
        squeeze = .9
        for _ in range(8):
            pts = self.cluster(cnt, pitch, squeeze) if cnt else []
            cw = max((abs(x) for x, _ in pts), default=0) + R
            fs = min(1.5, max(.75, cw / 56)) * (.85 + .15 * self.z)
            lean = 40 * fs
            left, right = max(26, cw - lean + 6), lean + cw + 8
            if left + right <= wmax or cnt < 3:
                break
            squeeze *= 1.25
        ymin = min((y for _, y in pts), default=0)
        ymax = max((y for _, y in pts), default=0)
        crown_h = max(ymax - ymin + 11 + R + 118, 270)
        t.fs, t.lean, t.crown_h = fs, lean, crown_h
        t.rel = [(lean + 2 + x, -crown_h + 11 + (y - ymin)) for x, y in pts]
        t.left, t.right = left, right
        t.sky = [(lean - 70 * fs, lean + 70 * fs, -crown_h - 66 * fs), (lean - 150 * fs, lean + 150 * fs, -crown_h + 20 * fs)]
        t.height = crown_h + 66 * fs
        t.top_y = -t.height

    def plan_pisang(self, t, cnt, wmax):
        R = self.R
        px, py = 2 * R + 4, 2 * R + 2
        for most in ((4, 3, 2) if cnt > 12 else (3, 2)):
            rows, left_n = [], cnt
            while left_n:
                take = min(most, left_n)
                if left_n == take == most and rows and most > 1:
                    take = most - 1
                rows.append(take)
                left_n -= take
            off = (54 + (most - 3) * 19) * self.z         # bunch centre, left of the stem
            left = off + (most - 1) / 2 * px + R + 4
            right = 74 * self.z
            if left + right <= wmax:
                break
        nrows = max(1, len(rows))
        st = max(230 * (.85 + .15 * self.z), 46 + (nrows - 1) * py + 62 + 34)
        t.rows, t.off, t.stem_h = rows, off, st
        t.leaf = min(1.25, max(.85, st / 230)) * (.85 + .15 * self.z)
        t.rel = []
        y0 = -st + 46
        for r, m in enumerate(rows):
            for j in range(m):
                o = j - (m - 1) / 2
                t.rel.append((round(-4 - off + (r % 2) * 4 - 2 + o * px), round(y0 + r * py + abs(o) * 3)))
        t.left, t.right = left, right
        t.height = st + 112 * t.leaf
        t.sky = [(-100 * t.leaf, 100 * t.leaf, -t.height), (-140 * t.leaf, 130 * t.leaf, -t.height + 50 * t.leaf)]
        t.top_y = -t.height

    # ------------------------------------------------------------------ parts of trees
    def trunk(self, bx, top, w0, w1, spread, lean=0):
        """A trunk that forks into two branches at `top` (the branch ends hide in the crown)."""
        GY = self.GY
        hw, tx = w1 / 2, bx + lean
        mid = (GY + top) / 2
        d = (f'M{P(bx - w0, GY + 2)}Q{P(bx - hw - 2, GY - 4)} {P(bx - hw - 1, GY - 22)}'
             f'Q{P(tx - hw - 3, mid)} {P(tx - hw, top)}'
             f'Q{P(tx - hw - 2, top - 26)} {P(tx - spread, top - 54)}L{P(tx - spread + 13, top - 62)}'
             f'Q{P(tx - 10, top - 40)} {P(tx - 1, top - 24)}'
             f'Q{P(tx + 8, top - 46)} {P(tx + spread * .8 - 12, top - 70)}L{P(tx + spread * .8, top - 60)}'
             f'Q{P(tx + hw + 1, top - 28)} {P(tx + hw, top)}'
             f'Q{P(tx + hw + 3, mid)} {P(bx + hw + 1, GY - 22)}Q{P(bx + hw + 2, GY - 4)} {P(bx + w0, GY + 2)}Z')
        sid = self.shared(d)
        shade = (f'M{P(tx + 3, top - 80)}L{P(tx + 60, top - 80)}L{P(bx + 60, GY + 4)}'
                 f'L{P(bx + 4, GY + 4)}Q{P(bx + 1, mid)} {P(tx + 3, top - 80)}Z')
        bark = (f'M{P(bx - hw * .45, GY - 12)}Q{P(tx - hw * .6, mid)} {P(tx - hw * .3, top - 4)}'
                f'M{P(bx + hw * .15, GY - 40)}q{I(lean * .3 - 2)} -30 {I(lean * .2)} -58M{P(tx - 4, top - 22)}l-12 -18')
        return (self.use(sid, 'p') + self.path(shade, 'd1', f' clip-path="{self.clip_of(sid)}"')
                + self.path(bark, 'l') + self.use(sid, 'L'))

    def crown(self, d, shade_ellipse, details):
        """Fill in tint, a halftone underside, hair details, then the outline."""
        sid = self.shared(d)
        ex, ey, erx, ery = shade_ellipse
        return (self.use(sid, 't')
                + f'<ellipse cx="{I(ex)}" cy="{I(ey)}" rx="{I(erx)}" ry="{I(ery)}" class="d2" clip-path="{self.clip_of(sid)}"/>'
                + self.path(details, 'l') + self.use(sid, 'L'))

    @staticmethod
    def leafy_crown(cx, cy, rx, ry, segs, tip, seed):
        """Mango crown: a dome whose edge is small overlapping pointed leaves."""
        rnd = random.Random(seed)
        base = []
        for i in range(segs):
            a = 2 * math.pi * i / segs + rnd.uniform(-.03, .03) - math.pi / 2
            s = math.sin(a)
            base.append((cx + rx * math.cos(a) * rnd.uniform(.97, 1.03),
                         cy + ry * s * (.72 if s > 0 else 1) * rnd.uniform(.97, 1.03)))
        d = ['M' + P(*base[0])]
        for i in range(segs):
            A, B = base[i], base[(i + 1) % segs]
            mx, my = (A[0] + B[0]) / 2, (A[1] + B[1]) / 2
            nx, ny = (mx - cx) / rx, (my - cy) / ry
            m = math.hypot(nx, ny) or 1
            nx, ny = nx / m, ny / m
            t = tip * rnd.uniform(.8, 1.25)
            T = (mx + nx * t + (B[0] - A[0]) * .3, my + ny * t + (B[1] - A[1]) * .3 + 2)
            c1 = (A[0] + nx * t * .9, A[1] + ny * t * .9)
            d.append(f'Q{P(*c1)} {P(*T)}L{P(*B)}')
        return ''.join(d) + 'Z'

    @staticmethod
    def bumpy_crown(cx, cy, rx, ry, segs, seed):
        """Rambutan crown: a round cloud of leaf clumps."""
        rnd = random.Random(seed)
        pts = []
        for i in range(segs):
            a = 2 * math.pi * (i + rnd.uniform(-.12, .12)) / segs - math.pi / 2
            s = math.sin(a)
            pts.append((cx + rx * math.cos(a), cy + ry * s * (.86 if s > 0 else 1)))
        d = ['M' + P(*pts[0])]
        for i in range(segs):
            A, B = pts[i], pts[(i + 1) % segs]
            r = math.hypot(B[0] - A[0], B[1] - A[1]) * rnd.uniform(.56, .66)
            d.append(f'A{I(r)} {I(r)} 0 0 1 {P(*B)}')
        return ''.join(d) + 'Z'

    def frond(self, x0, y0, ang, L, droop, llen, lift):
        """A coconut frond: an arching rachis with a fringe of long narrow leaflets hanging from it."""
        a = math.radians(ang)
        tip = (x0 + L * math.cos(a), y0 + L * math.sin(a) + droop)
        c = (x0 + .5 * L * math.cos(a), y0 + .5 * L * math.sin(a) - lift)
        steps = 11
        rib, tips, notches = [(x0, y0)], [], []
        out_x = 1 if math.cos(a) >= 0 else -1
        for s in range(1, steps):
            t = s / steps
            (px, py), (tx, ty) = qb((x0, y0), c, tip, t)
            nx, ny = -ty, tx
            if ny < -.2 or (abs(ny) <= .2 and nx * out_x < 0):
                nx, ny = -nx, -ny
            dx, dy = nx * .5 + tx * .5, ny * .5 + .8 + ty * .5
            m = math.hypot(dx, dy) or 1
            dx, dy = dx / m, dy / m
            ln = llen * math.sin(math.pi * t) ** .5 * (1 - .3 * t)
            rib.append((px, py))
            tips.append((px + dx * ln, py + dy * ln))
            notches.append((px + dx * ln * .4 - tx * 4, py + dy * ln * .4 - ty * 4))
        rib.append(tip)
        edge = []
        for tp, nt in zip(tips[::-1], notches[::-1]):
            edge += [tp, nt]
        veins = ''.join(f'M{P(*r)}L{P(*tp)}' for r, tp in zip(rib[1:-1], tips))
        return (self.path(poly(rib + edge), 't o') + self.path(veins, 'l')
                + self.path(f'M{P(x0, y0)}Q{P(*c)} {P(*tip)}', 'L'))

    def banana_leaf(self, x0, y0, ang, L, wd, droop, lift, dry=False, splits=(.35, .55, .72)):
        """A banana leaf: a long blunt paddle, a strong midrib and wind-torn splits."""
        a = math.radians(ang)
        tip = (x0 + L * math.cos(a), y0 + L * math.sin(a) + droop)
        c = (x0 + .5 * L * math.cos(a), y0 + .5 * L * math.sin(a) - lift)
        t0, steps = .16, 12
        up, lo, rib = [], [], []
        for s in range(steps + 1):
            t = t0 + (1 - t0) * s / steps
            (px, py), (tx, ty) = qb((x0, y0), c, tip, t)
            u = (t - t0) / (1 - t0)
            w = wd * max(0, 1 - (2 * u - 1) ** 6) ** .5
            nx, ny = -ty, tx
            if ny > 0:
                nx, ny = -nx, -ny
            up.append((px + nx * w, py + ny * w))
            lo.append((px - nx * w * .9, py - ny * w * .9))
            rib.append(((px, py), (nx, ny), w))
        sid = self.shared(smooth(up + lo[::-1]))
        g = [self.use(sid, 'p d2') if dry else self.use(sid, 't')]
        if not dry:
            # the lower half in halftone: a plain polygon pushed past the edge, the blade clips it
            out_lo = [(px - nx * w * 1.4, py - ny * w * 1.4) for (px, py), (nx, ny), w in rib]
            g.append(self.path(poly([r[0] for r in rib] + out_lo[::-1]), 'd1', f' clip-path="{self.clip_of(sid)}"'))
        cuts = []
        for j, sp in enumerate(splits):
            i = int(sp * steps)
            (px, py), (nx, ny), w = rib[i]
            (qx, qy), _, _ = rib[min(steps, i + 1)]
            sg = 1 if j % 2 == 0 else -.9
            cuts.append(f'M{P(px + nx * w * sg, py + ny * w * sg)}L{P(qx + nx * w * .1 * sg, qy + ny * w * .1 * sg)}')
        g.append(self.path(''.join(cuts), 'l'))
        g.append(self.use(sid, 'L'))
        g.append(self.path(f'M{P(x0, y0)}Q{P(*c)} {P(*tip)}', 'L'))
        return ''.join(g)

    def ground_shadow(self, cx, rx):
        return f'<ellipse cx="{I(cx)}" cy="{self.GY}" rx="{I(rx)}" ry="7" class="di"/>'

    # ------------------------------------------------------------------ drawing the four trees
    def draw(self, t):
        """(tree art, [fruit svg]) for planned tree t at anchor t.x."""
        picks = {fi: c for c, fi in enumerate(t.pick_ids)}
        art = getattr(self, 'draw_' + t.kind)(t)
        fruits = [self.fruit(t.x + x, self.GY + y, it, t.kind, t.i * 3 + j, picks.get(j))
                  for j, ((x, y), it) in enumerate(zip(t.rel, t.items))]
        return art, fruits

    def draw_mangga(self, t):
        rx, ry, _, _ = t.crown
        cx, cy = t.x, self.GY + t.cy
        sx, sy, z = rx / 116, ry / 96, self.z
        out = [self.ground_shadow(cx, rx * .78), self.trunk(cx, cy + .85 * ry, 26 * z, 26 * z, 50 * sx, lean=-2)]
        clumps = ''.join(f'M{P(cx + x * sx - 10, cy + y * sy + 5)}Q{P(cx + x * sx - 4, cy + y * sy - 3)} {P(cx + x * sx + 4, cy + y * sy - 1)}'
                         for x, y in ((-74, -34), (-24, -66), (50, -50), (80, 2), (-90, 20)))
        segs = max(22, int(44 * (rx + ry) / 212))
        out.append(self.crown(self.leafy_crown(cx, cy, rx, ry, segs, 9, seed=7 + t.i),
                              (cx + 34 * sx, cy + 80 * sy, rx * 1.05, ry * .62), clumps))
        return ''.join(out)

    def draw_rambutan(self, t):
        rx, ry, _, _ = t.crown
        cx, cy = t.x, self.GY + t.cy
        sx, sy, z = rx / 102, ry / 88, self.z
        out = [self.ground_shadow(cx, rx * .82), self.trunk(cx, cy + .7 * ry, 22 * z, 22 * z, 44 * sx, lean=3)]
        arcs = ''.join(f'M{P(cx + x * sx - 14, cy + y * sy + 4)}A15 15 0 0 1 {P(cx + x * sx + 14, cy + y * sy + 4)}'
                       for x, y in ((-60, -42), (6, -60), (58, -20), (-32, 20), (42, 42)))
        segs = max(11, int(15 * (rx + ry) / 190))
        out.append(self.crown(self.bumpy_crown(cx, cy, rx, ry, segs, seed=11 + t.i),
                              (cx + 30 * sx, cy + 70 * sy, rx * 1.1, ry * .7), arcs))
        return ''.join(out)

    def draw_kelapa(self, t):
        GY, fs, bx = self.GY, t.fs, t.x
        top = (bx + t.lean, GY - t.crown_h)
        c = (bx - 30 * fs, GY - .47 * t.crown_h)
        out = [self.ground_shadow(bx + 6, 40 * fs)]
        left, right, rings = [], [], []
        steps = 18
        for s in range(steps + 1):
            u = s / steps
            (px, py), (tx, ty) = qb((bx, GY + 2), c, top, u)
            w = (11 - 4.5 * u + (5 * (1 - u * 6) if u < 1 / 6 else 0)) * (.8 + .2 * fs)
            nx, ny = -ty, tx
            left.append((px + nx * w, py + ny * w))
            right.append((px - nx * w, py - ny * w))
            if 0 < s < steps:
                rings.append(f'M{P(px + nx * w * .95, py + ny * w * .95)}Q{P(px + ty * 3, py - tx * 3 + 3)} {P(px - nx * w * .95, py - ny * w * .95)}')
        sid = self.shared(poly(left + right[::-1]))
        mid = [(p[0] * .45 + q[0] * .55, p[1] * .45 + q[1] * .55) for p, q in zip(left, right)]
        out.append(self.use(sid, 'p') + self.path(poly(right + mid[::-1]), 'd1') + self.path(''.join(rings), 'l') + self.use(sid, 'L'))
        x0, y0 = top
        for ang, L, droop, ll, lift in ((150, 96, 60, 24, 4), (30, 96, 60, 24, 4),
                                        (-178, 140, 72, 32, 36), (-150, 122, 36, 30, 36), (-116, 96, 16, 24, 24),
                                        (-64, 96, 16, 24, 24), (-30, 122, 36, 30, 36), (-2, 140, 72, 32, 36)):
            out.append(self.frond(x0, y0, ang, L * fs, droop * fs, ll * fs, lift * fs))
        out.append(f'<circle cx="{I(x0)}" cy="{I(y0 + 2)}" r="7" class="i"/>')
        return ''.join(out)

    def draw_pisang(self, t):
        GY, bx, lf, R = self.GY, t.x, t.leaf, self.R
        top = (bx - 4, GY - t.stem_h)
        out = [self.ground_shadow(bx, 52 * lf),
               self.banana_leaf(top[0] + 2, top[1] + 6, 30, 100 * lf, 16 * lf, 66 * lf, 10 * lf, dry=True, splits=(.4, .62)),
               self.banana_leaf(top[0], top[1], -152, 124 * lf, 21 * lf, 26 * lf, 40 * lf)]
        mid = (GY + top[1]) / 2
        sl = [(bx - 16, GY + 2), (bx - 15, GY - 40), (bx - 13, mid), (top[0] - 10, top[1] + 8)]
        sr = [(top[0] + 10, top[1] + 8), (bx + 12, mid), (bx + 14, GY - 40), (bx + 17, GY + 2)]
        sid = self.shared(smooth(sl, closed=False) + 'L' + smooth(sr, closed=False)[1:] + 'Z')
        out.append(self.use(sid, 'p')
                   + f'<rect x="{I(bx + 3)}" y="{I(top[1])}" width="20" height="{I(GY - top[1] + 4)}" class="d1" clip-path="{self.clip_of(sid)}"/>'
                   + self.path(f'M{P(bx - 5, GY - 6)}Q{P(bx - 8, mid + 20)} {P(top[0] - 4, top[1] + 30)}'
                               f'M{P(bx + 6, GY - 30)}Q{P(bx + 5, mid + 40)} {P(top[0] + 4, top[1] + 50)}', 'l')
                   + self.use(sid, 'L'))
        out.append(self.banana_leaf(top[0], top[1], -110, 118 * lf, 22 * lf, 8 * lf, 24 * lf, splits=(.3, .5, .7)))
        out.append(self.banana_leaf(top[0], top[1], -62, 120 * lf, 22 * lf, 6 * lf, 20 * lf, splits=(.38, .6)))
        out.append(self.banana_leaf(top[0], top[1] + 2, -24, 96 * lf, 19 * lf, 38 * lf, 30 * lf, splits=(.42, .66)))
        if t.items:
            # the bunch: a stalk arching out and down, hands of fruit in tiers, the jantung at the end
            bxc = top[0] - t.off
            y0 = top[1] + 46
            y_end = y0 + (len(t.rows) - 1) * (2 * R + 2)
            stalk = f'M{P(top[0] - 4, top[1] + 10)}Q{P(bxc - 4, top[1] - 6)} {P(bxc, y0 - 12)}L{P(bxc + 2, y_end + 26)}'
            out.append(f'<path d="{stalk}" class="n" stroke="{self.k.ink}" stroke-width="8" stroke-linecap="round"/>'
                       f'<path d="{stalk}" class="n" stroke="{self.k.paper}" stroke-width="3" stroke-linecap="round"/>')
            jx, jy = bxc + 2, y_end + R + 23
            out.append(self.path(f'M{P(jx, jy - 22)}C{P(jx + 16, jy - 16)} {P(jx + 13, jy + 8)} {P(jx, jy + 20)}'
                                 f'C{P(jx - 13, jy + 8)} {P(jx - 16, jy - 16)} {P(jx, jy - 22)}Z', 'k o'))
            out.append(self.path(f'M{P(jx - 10, jy - 6)}Q{P(jx, jy + 2)} {P(jx + 10, jy - 6)}M{P(jx - 7, jy + 7)}Q{P(jx, jy + 13)} {P(jx + 7, jy + 7)}', 'l'))
        return ''.join(out)

    # ------------------------------------------------------------------ marker boards
    def board(self, cx, text, tilt, wmax):
        """A wooden marker planted in the soil. A long name goes on two planks."""
        GY, k = self.GY, self.k
        words = str(text).split()
        lines = [str(text)]
        if label_width(text, 12) > min(150, wmax - 30) and len(words) > 1:      # split near the middle
            best = min(range(1, len(words)), key=lambda i: abs(len(' '.join(words[:i])) - len(' '.join(words[i:]))))
            lines = [' '.join(words[:best]), ' '.join(words[best:])]
        h, gap = 26, 4
        top = GY + 10 - len(lines) * (h + gap)
        planks, widths = [], []
        for line in lines:
            shown, size = fit_label(line, max(40, min(200, wmax - 36)), 12, 9)
            widths.append((shown, size, math.ceil((label_width(shown, size) + 30) / 4) * 4))
        wide = max(w for _, _, w in widths)
        posts = ''.join(f'<rect x="{I(px - 3)}" y="{I(top + 4)}" width="6" height="{I(GY + 26 - top)}" class="p oh"/>'
                        for px in (cx - wide / 2 + 16, cx + wide / 2 - 16))
        for j, (shown, size, w) in enumerate(widths):
            x, y = cx - w / 2 + (j * 6 - 3 if len(lines) > 1 else 0), top + j * (h + gap)
            planks.append(f'<rect x="{I(x)}" y="{I(y)}" width="{I(w)}" height="{h}" rx="{K.R_LABEL}" class="p o"/>'
                          + self.path(f'M{P(x + 5, y + 7)}h6M{P(x + w - 12, y + h - 6)}h7', 'l')
                          + ''.join(f'<circle cx="{I(px)}" cy="{I(y + h / 2)}" r="1.6" class="i"/>' for px in (x + 7, x + w - 7))
                          + label_text(x + w / 2, y + h / 2 + size * .36, shown, size, k.ink, 'middle'))
        return f'<g transform="rotate({tilt} {I(cx)} {GY})">{posts}{"".join(planks)}</g>'

    # ------------------------------------------------------------------ the banana on a ladder
    def ladder(self, foot, top):
        (fx, fy), (tx, ty) = foot, top
        L = math.hypot(tx - fx, ty - fy)
        ux, uy = (tx - fx) / L, (ty - fy) / L
        px, py = -uy * 11, ux * 11
        rails = f'M{P(fx - px, fy - py)}L{P(tx - px, ty - py)}M{P(fx + px, fy + py)}L{P(tx + px, ty + py)}'
        rungs, s = [], 16
        while s < L - 6:
            cx, cy = fx + ux * s, fy + uy * s
            rungs.append(f'M{P(cx - px, cy - py)}L{P(cx + px, cy + py)}')
            s += 20
        nodes = ''.join(f'M{P(fx + ux * s + px * sg - uy * 3.5, fy + uy * s + py * sg + ux * 3.5)}l{I(uy * 7)} {I(-ux * 7)}'
                        for s in range(34, int(L) - 10, 40) for sg in (1, -1))
        return (self.path(''.join(rungs), 'L')
                + f'<path d="{rails}" stroke="{self.k.ink}" stroke-width="7.5" stroke-linecap="round"/>'
                + f'<path d="{rails}" stroke="{self.k.paper}" stroke-width="2.5" stroke-linecap="round"/>'
                + self.path(nodes, 'l'))

    SH = (-16, -84)              # the free (left) shoulder, banana coordinates
    RIM = (80, -36)              # the basket's rim centre
    AL = 100                     # the free arm is drawn AL long and stretched with scaleX
    REST = (118.0, 64.0)         # free arm hanging: angle, length

    def banana_frame(self, x, y, s):
        """Helpers that turn banana coordinates (with a body lean) into canvas points and back."""
        def canvas(p, phi):
            c, sn = math.cos(math.radians(phi)), math.sin(math.radians(phi))
            return x + s * (p[0] * c - p[1] * sn), y + s * (p[0] * sn + p[1] * c)

        def arm_to(h, phi):
            """canvas hand point -> (angle deg, length) of the free arm"""
            lx, ly = (h[0] - x) / s, (h[1] - y) / s
            c, sn = math.cos(math.radians(-phi)), math.sin(math.radians(-phi))
            px, py = lx * c - ly * sn, lx * sn + ly * c
            vx, vy = px - self.SH[0], py - self.SH[1]
            return math.degrees(math.atan2(vy, vx)), math.hypot(vx, vy)
        return canvas, arm_to

    def banana(self, x, y, s, targets, harvest):
        """The komik banana (body, stem and face from banana_komik) on the ladder with its bakul.
        targets: fruit centres it picks in turn (the first is also its still pose). Returns (svg, css).

        Each pick is one CYCLE, all CSS transforms with linear timing over keyframes computed here,
        so the hand, the arm and the carried fruit stay locked together:
          0-10%   rest     the free arm hangs down
          10-26%  reach    the arm swings up about the shoulder, the body leans to the tree
          31%     pick     the branch fruit (gr<i>) scales to 0 as its copy (gf<i>) appears in the hand
          34-60%  carry    the fruit swings out to the right and down onto the basket, shrinking a little
          60-66%  drop     it sinks behind the basket's front wall, scaling to 0 at the rim
          64-76%  bounce   the basket squashes and springs back (gb)
          80-93%  regrow   the branch fruit grows back 0 -> 1.14 -> 1
        Reduced motion (or harvest off): the arm rests on the first fruit; nothing is duplicated."""
        k, R = self.k, self.R
        lw, hw = n(K.LINE / s), n(K.HAIR / s)
        stroke = f'stroke="{k.ink}" stroke-width="{lw}" stroke-linejoin="round" stroke-linecap="round"'
        canvas, arm_to = self.banana_frame(x, y, s)
        OFF = (-.53 * R, .76 * R)          # the hand sits at the fruit's lower left
        near = lambda a, ref: a + 360 * round((ref - a) / 360)
        F0 = targets[0]
        g_th, g_l = arm_to((F0[0] + OFF[0], F0[1] + OFF[1]), -5)
        g_th = near(g_th, self.REST[0])
        css = []
        if harvest:
            css.append(self.pick_css(canvas, arm_to, targets, OFF))
        css.append(f'.gL{{transform:rotate(-5deg)}}.gA{{transform:rotate({g_th:.0f}deg) scaleX({g_l / self.AL:.2f})}}'
                   f'.gH{{transform:rotate({g_th:.0f}deg) translateX({g_l:.0f}px)}}')
        AL = self.AL
        tube = (f'<path d="M0 0Q{AL / 2:g} -14 {AL} 0" fill="none" stroke="{k.ink}" stroke-width="{n((5 + 2 * K.LINE) / s)}" stroke-linecap="round"/>'
                f'<path d="M0 0Q{AL / 2:g} -14 {AL} 0" fill="none" stroke="{k.paper}" stroke-width="{n(5 / s)}" stroke-linecap="round"/>')
        hold = 'M46 -80Q73 -77 80 -62'
        basket = (f'<g transform="translate(80 8)"><g class="gb"><g transform="translate(-80 -8)">'
                  f'<path d="M58-34Q80-74 102-34" fill="none" {stroke}/>'
                  f'<circle cx="68" cy="-40" r="11" class="p" {stroke}/><circle cx="91" cy="-42" r="11" class="p" {stroke}/>'
                  f'<path d="M50-34H110L102 4Q80 10 58 4Z" class="t" {stroke}/>'
                  f'<path d="M54-18Q80-12 106-18M56-4Q80 2 104-4M66-32L68 6M80-32V8M94-32L92 6" fill="none" '
                  f'stroke="{k.ink}" stroke-width="{hw}"/>'
                  f'<rect x="46" y="-40" width="68" height="10" rx="4" class="k" {stroke}/></g></g></g>')
        right_arm = (f'<path d="{hold}" fill="none" stroke="{k.ink}" stroke-width="{n((5 + 2 * K.LINE) / s)}" stroke-linecap="round"/>'
                     f'<path d="{hold}" fill="none" stroke="{k.paper}" stroke-width="{n(5 / s)}" stroke-linecap="round"/>'
                     f'<circle cx="80" cy="-62" r="7" class="p" {stroke}/>')
        free_arm = (f'<g transform="translate({self.SH[0]} {self.SH[1]})"><g class="gA">{tube}</g>'
                    f'<g class="gH"><circle r="7" class="p" {stroke}/></g></g>')
        open_g = f'<g transform="translate({I(x)} {I(y)}) scale({s:.3g})"><g class="gL">'
        body = (open_g + f'<clipPath id="gbk"><path d="{BODY}"/></clipPath>'
                f'<path d="{STEM}" fill="{k.ink}" {stroke}/><path d="{BODY}" fill="{k.paper}"/>'
                f'<g clip-path="url(#gbk)"><path d="{SHADE}" class="d2"/><ellipse cx="-5" cy="0" rx="9" ry="6" class="i"/></g>'
                f'<path d="M-7-150C-12-118-14-82-10-52" fill="none" stroke="{k.ink}" stroke-width="{hw}" stroke-linecap="round"/>'
                f'<path d="{BODY}" fill="none" {stroke}/>'
                # the face looks up at the fruit
                f'<circle cx="3" cy="-122" r="5" class="i"/><circle cx="27" cy="-124" r="5" class="i"/>'
                f'<circle cx="4.5" cy="-124" r="1.8" class="p"/><circle cx="28.5" cy="-126" r="1.8" class="p"/>'
                f'<ellipse cx="-6" cy="-108" rx="6.5" ry="4" class="k"/><ellipse cx="37" cy="-110" rx="6.5" ry="4" class="k"/>'
                f'<path d="M9-110Q15-100 21-111" fill="none" {stroke}/></g></g>')
        # carried fruits sit between the body and the basket/arms: they pass in front of the
        # banana, under its hand, and sink behind the basket's front wall
        copies = ''.join(f'<g transform="translate({I(F[0])} {I(F[1])})"><g class="gf{c}"><use href="#fp{c}"/></g></g>'
                         for c, F in enumerate(targets)) if harvest else ''
        return body + copies + open_g + basket + right_arm + free_arm + '</g></g>', ''.join(css)

    def pick_css(self, canvas, arm_to, targets, OFF):
        """Keyframes for len(targets) pick cycles in one loop."""
        R, kc = self.R, len(targets)
        loop = CYCLE * kc
        near = lambda a, ref: a + 360 * round((ref - a) / 360)
        rim = canvas(self.RIM, 3)
        D = (rim[0], rim[1] - .53 * R)                  # fruit (shrunk to .7) resting on the rim
        lean = [(0, 0.), (.10, 0.), (.26, -5.), (.34, -5.), (.46, 0.), (.58, 3.), (.66, 3.), (.80, 0.), (1, 0.)]

        def phi(u):
            for (u0, v0), (u1, v1) in zip(lean, lean[1:]):
                if u0 <= u <= u1:
                    return v0 + (v1 - v0) * ease((u - u0) / (u1 - u0))
            return 0.

        US = (0, .10, .14, .18, .22, .26, .31, .32, .34, .37, .40, .43, .46, .49, .52, .55, .58, .60, .62, .64,
              .68, .72, .76, .80, .999)
        CU = (.32, .34, .37, .40, .43, .46, .49, .52, .55, .58, .60, .62, .64, .66)
        rows = {'gL': [], 'gA': [], 'gH': []}
        cps = []
        prev = self.REST[0]
        for c, F in enumerate(targets):
            rest = near(self.REST[0], prev)
            F4 = (F[0], F[1] + 4)
            Q1 = (F[0] + (D[0] - F[0]) * .6 + 8, F[1] + (D[1] - F[1]) * .25 - 2)   # out to the right,
            Q2 = (D[0] + 12, D[1] - 22)                                            # then down onto the rim
            way = [F4, F4, Q1, Q2, D, D]

            def carry(u):                           # Catmull-Rom through the waypoints
                t = ease((u - .34) / (.60 - .34)) * 3
                i = min(2, int(t))
                t -= i
                p0, p1, p2, p3 = way[i:i + 4]
                return tuple(.5 * ((2 * p1[j]) + (-p0[j] + p2[j]) * t + (2 * p0[j] - 5 * p1[j] + 4 * p2[j] - p3[j]) * t * t
                                   + (-p0[j] + 3 * p1[j] - 3 * p2[j] + p3[j]) * t ** 3) for j in (0, 1))

            def held(u):                            # where the fruit in the hand is
                if u <= .34:
                    return (F[0], F[1] + 4 * ease((u - .31) / .03))
                if u <= .60:
                    return carry(u)
                return (D[0], D[1] + 5 * ease((u - .60) / .04))

            g_th, g_l = arm_to((F[0] + OFF[0], F[1] + OFF[1]), -5)
            g_th = near(g_th, rest)
            back = None
            for u in US:
                f = phi(u)
                if u <= .10:
                    th, ln = rest, self.REST[1]
                elif u <= .26:
                    e = ease((u - .10) / .16)
                    th, ln = rest + (g_th - rest) * e, self.REST[1] + (g_l - self.REST[1]) * e
                elif u <= .31:
                    th, ln = g_th, g_l
                elif u <= .64:
                    h = held(u)
                    th, ln = arm_to((h[0] + OFF[0], h[1] + OFF[1]), f)
                    th = near(th, prev)
                else:                                # back to rest, the long way down past the belly
                    if back is None:
                        back = (prev, ln, near(self.REST[0], prev))
                    th0, ln0, goal = back
                    e = ease((u - .64) / .16)
                    th, ln = th0 + (goal - th0) * e, ln0 + (self.REST[1] - ln0) * e
                prev = th
                p = (c + u) / kc * 100
                rows['gL'].append((p, f'rotate({f:.0f}deg)'))
                rows['gA'].append((p, f'rotate({th:.0f}deg) scaleX({ln / self.AL:.2f})'))
                rows['gH'].append((p, f'rotate({th:.0f}deg) translateX({ln:.0f}px)'))
            # the copy in the hand
            cr = [(0, 'scale(0)'), ((c + .309) / kc * 100, 'scale(0)')]
            for u in (.311,) + CU:
                if u <= .60:
                    h = held(u)
                    sc = 1 - .3 * ease((u - .52) / .08)
                else:
                    e = ((u - .60) / .06) ** 2
                    h, sc = (D[0], D[1] + .8 * R * e), .7 * (1 - e)
                cr.append(((c + u) / kc * 100, f'translate({h[0] - F[0]:.0f}px,{h[1] - F[1]:.0f}px) scale({sc:.2f})'))
            cr += [((c + .661) / kc * 100, 'scale(0)'), (100, 'scale(0)')]
            cps.append(cr)

        def kf(name, rs, base=None):
            out, last = [], None
            for i, (p, v) in enumerate(rs):
                nxt = rs[i + 1][1] if i + 1 < len(rs) else None
                if v == last and v == nxt:
                    continue
                out.append(f'{p:.2f}'.rstrip('0').rstrip('.') + f'%{{transform:{v}}}')
                last = v
            b = f'transform:{base};' if base else ''
            return f'.{name}{{{b}animation:{name} {loop:g}s linear infinite}}@keyframes {name}{{{"".join(out)}}}'

        css = [kf(name, rs) for name, rs in rows.items()]
        css += [kf(f'gf{c}', cr, 'scale(0)') for c, cr in enumerate(cps)]
        for c in range(kc):
            pc = lambda u: (c + u) / kc * 100
            css.append(kf(f'gr{c}', [(0, 'none'), (pc(.309), 'none'), (pc(.311), 'scale(0)'), (pc(.80), 'scale(0)'),
                                     (pc(.88), 'scale(1.14)'), (pc(.93), 'none'), (100, 'none')]))
        gb = [(0, 'none')]
        for c in range(kc):
            gb += [((c + .63) / kc * 100, 'none'), ((c + .66) / kc * 100, 'scale(1.12,.82)'),
                   ((c + .71) / kc * 100, 'scale(.95,1.06)'), ((c + .76) / kc * 100, 'none')]
        css.append(kf('gb', gb + [(100, 'none')]))
        return ''.join(css)

    # ------------------------------------------------------------------ sky, ground, petals
    def sky(self, cx, cy):
        """Sun on the day print, moon and stars on the night print."""
        if self.k.mode == 'light':
            rays = ''.join(f'M{P(cx + 25 * math.cos(a), cy + 25 * math.sin(a))}L{P(cx + 33 * math.cos(a), cy + 33 * math.sin(a))}'
                           for a in (2 * math.pi * i / 10 + .2 for i in range(10)))
            return self.path(rays, 'L') + f'<circle cx="{I(cx)}" cy="{I(cy)}" r="19" class="d2 o"/>'
        moon = f'M{P(cx + 6, cy - 19)}A19 19 0 1 0 {P(cx + 13, cy + 14)}A15 15 0 0 1 {P(cx + 6, cy - 19)}Z'
        stars = ''.join(f'M{P(sx, sy - 5)}v10M{P(sx - 5, sy)}h10'
                        for sx, sy in ((cx + 44, cy - 6), (cx - 52, cy + 18), (cx + 22, cy + 34)))
        return self.path(moon, 'd2 o') + self.path(stars, 'l')

    def ground(self, seed):
        GY, H = self.GY, self.H
        rnd = random.Random(seed)
        for v in range(3):
            d = ''.join(f'M{j * 3} 0q{n(l * .3)} {n(-h * .6)} {n(l)} {n(-h)}'
                        for j, (l, h) in enumerate((rnd.uniform(-4, 4), rnd.uniform(6, 11)) for _ in range(3 + v % 2)))
            self.defs.append(f'<path id="gt{v}" d="{d}" class="l"/>')
        uses = ''.join(f'<use href="#gt{rnd.randrange(3)}" x="{I(x + rnd.uniform(-6, 6))}" y="{GY}"/>'
                       for x in range(20, W - 20, 30))
        return (f'<rect x="0" y="{GY}" width="{W}" height="{H - GY}" class="d1"/>'
                f'<path d="M0 {GY}H{W}" class="L"/>{uses}')

    def petals(self, spots):
        if not spots:
            return ''
        self.defs.append(f'<g id="kb">{self.k.kamboja(0, 0, 9, 0)}</g>')
        return ''.join(f'<use href="#kb" transform="translate({I(x)} {I(y)}) rotate({r}) scale({s:g})"/>'
                       for x, y, s, r in spots[:7])


# ---------------------------------------------------------------------------- layout & render
def _layout(g, trees, ladder_room):
    """Choose fruit size, crown shapes, anchors and the card height. Returns True if it fit."""
    avail = W - 2 * SIDE
    nt = len(trees)
    fit = False
    for z in (1, .94, .88, .82, .76, .71):
        g.z, g.R = z, max(12, round(17 * z))
        for t in trees:
            g.plan(t, 10 ** 6)
        lad = ladder_room * (.8 + .2 * z)
        need = sum(t.left + t.right for t in trees) + GAP * (nt - 1) + lad
        if need > avail:
            # narrow the crowns first (they grow taller); the palm and the banana plant only if needed
            flex = [t for t in trees if t.kind in ('mangga', 'rambutan')]
            for group in (flex, trees):
                if not group:
                    continue
                fixed = sum(t.left + t.right for t in trees if t not in group)
                room = avail - GAP * (nt - 1) - lad - fixed
                pref = [t.left + t.right for t in group]
                for t, p in zip(group, pref):
                    g.plan(t, max(40, p * room / sum(pref)))
                need = sum(t.left + t.right for t in trees) + GAP * (nt - 1) + lad
                if need <= avail + 1:
                    break
        tall = max(t.height for t in trees) + SOIL + SKY
        if need <= avail + 1 and tall <= H_MAX:
            fit = True
            break
    g.H = int(math.ceil(min(max(tall, H_MIN), H_MAX) / 8) * 8)
    g.GY = g.H - SOIL
    # spread the spare width evenly: between trees and at both ends
    spare = max(0, avail - need)
    step = spare / (nt + 1)
    x = SIDE + step
    for t in trees:
        x += t.left
        t.x = x
        x += t.right + GAP + step + (lad if t.harvest else 0)
    if spare == 0 and x - GAP - step > W - SIDE:      # still too wide: squeeze the gaps (trees overlap a little)
        over = (x - GAP - step) - (W - SIDE)
        for j, t in enumerate(trees):
            t.x -= over * j / max(1, nt - 1)
    return fit


def _harvest_tree(trees):
    for kind in ('mangga', 'rambutan', 'kelapa', 'pisang'):
        for t in trees:
            if t.kind == kind and t.items:
                return t
    return None


def _clear_spot(x, y, r, things):
    return all(math.hypot(x - a, y - b) > r + rr for a, b, rr in things)


def render(trees_opt, ctx, harvest=True, mascot='banana'):
    """trees_opt: [{'name', 'tree', 'icons', 'logos'}, ...] -> Out (one mode)."""
    k = kit_for(ctx)
    say = ctx.log if ctx.mode == 'light' else (lambda *a: None)
    trees_opt = list(trees_opt or [])
    if len(trees_opt) > MAX_TREES:
        say(f'{len(trees_opt)} trees; the garden has room for {MAX_TREES}, so the first {MAX_TREES} are drawn')
        trees_opt = trees_opt[:MAX_TREES]
    idx = _index(ctx.root, say) if any(o.get('icons') for o in trees_opt) else {}
    trees = []
    for i, o in enumerate(trees_opt):
        kind = str(o.get('tree') or '').strip().lower()
        if kind not in KINDS:
            if kind:
                say(f'tree {i + 1}: unknown tree "{kind}" (have: {", ".join(KINDS)}); using {KINDS[i % 4]}')
            kind = KINDS[i % 4]
        icons = o.get('icons') or []
        if isinstance(icons, str):
            icons = [s for s in icons.replace(',', ' ').split() if s]
        icons = [str(s).strip() for s in icons if str(s).strip()]
        name = str(o.get('name') or '').strip()
        if len(icons) > MAX_FRUIT:
            say(f'tree "{name or i + 1}": {len(icons)} tools; a tree holds {MAX_FRUIT}, so the first {MAX_FRUIT} are drawn '
                '(split the rest into another tree)')
            icons = icons[:MAX_FRUIT]
        logos = o.get('logos') if isinstance(o.get('logos'), dict) else {}
        trees.append(Tree(i, name, kind, [resolve(r, ctx, idx, logos, say) for r in icons]))

    g = Garden(k, ctx.seed)
    use_mascot = mascot != 'none' and any(t.items for t in trees)
    ht = _harvest_tree(trees) if use_mascot else None
    for t in trees:
        t.harvest = t is ht
    if not trees:
        g.H, g.GY = H_MIN, H_MIN - SOIL
    elif not _layout(g, trees, 66 if ht else 0):
        say('the trees are crowded; try fewer tools per tree or fewer trees')
    g.fruit_defs()
    GY = g.GY

    # the banana: on a ladder right of the harvest tree's lowest-right fruit
    mascot_svg = ladder = css_pick = ''
    targets = []
    if ht:
        order = sorted(range(len(ht.rel)), key=lambda j: -(ht.rel[j][0] + .7 * ht.rel[j][1]))
        fx, fy = ht.x + ht.rel[order[0]][0], GY + ht.rel[order[0]][1]
        s = .46 * (.85 + .15 * g.z)
        foot, top = (fx + 64, GY + 2), (fx + 12, fy + g.R + 9)
        on = lambda yy: foot[0] + (top[0] - foot[0]) * (foot[1] - yy) / (foot[1] - top[1])   # ladder x at height y
        by = min(fy + g.R + 8 + 209 * s, GY - 8)      # its stem tip just under the fruit
        bx = on(by) - 18 * s
        canvas, _ = g.banana_frame(bx, by, s)
        sh = canvas(g.SH, -5)
        ht.pick_ids = [order[0]]
        if harvest:
            for j in order[1:]:
                hx, hy = ht.x + ht.rel[j][0] - .53 * g.R, GY + ht.rel[j][1] + .76 * g.R
                dist = math.hypot(hx - sh[0], hy - sh[1])
                if 30 < dist < 130 * s / .46 and hy < sh[1] - 8 and len(ht.pick_ids) < MAX_PICKS:
                    ht.pick_ids.append(j)
        else:
            ht.pick_ids = []
        targets = [(ht.x + ht.rel[j][0], GY + ht.rel[j][1]) for j in (ht.pick_ids or [order[0]])]
        ladder = g.ladder(foot, top)
        mascot_svg, css_pick = g.banana(bx, by, s, targets, harvest)

    back, fruits, boards = [], [], []
    for t in trees:
        art, fr = g.draw(t)
        back.append(art)
        fruits.append(''.join(fr))
        if t.name:
            mx = t.x + {'kelapa': 2, 'pisang': -6}.get(t.kind, 0)
            boards.append(g.board(mx, t.name, (-2, 2, -1.5, 2.5)[t.i % 4], t.left + t.right + GAP))

    # sky: the sun (or moon) over the lowest stretch of skyline
    tops = [(t.x + a - 38, t.x + b + 38, GY + top) for t in trees for a, b, top in t.sky]
    sky_at = lambda x: min([y for a, b, y in tops if a <= x <= b] or [GY])      # skyline under the sun's reach
    best = max(range(60, W - 59, 8), key=lambda x: (min(64, sky_at(x) - 40), -abs(x - W / 2)))
    sun_y = min(64, sky_at(best) - 40)
    sun_at = (best, sun_y) if sun_y >= 46 else None
    # petals: in the air and on the soil, never on a fruit, the sun or the banana
    things = [(t.x + x, GY + y, g.R + 10) for t in trees for x, y in t.rel]
    if sun_at:
        things.append((sun_at[0], sun_at[1], 46))
    if targets:
        things.append((bx + 10, by - 50, 60))
    for t in trees:
        if t.kind == 'pisang' and t.items:                 # the jantung under the bunch
            things.append((t.x - 4 - t.off + 2, GY - t.stem_h + 46 + (len(t.rows) - 1) * (2 * g.R + 2) + g.R + 23, 34))
    crowns = [(t.x, GY + t.cy, t.crown[0], t.crown[1]) for t in trees if t.kind in ('mangga', 'rambutan')]
    rnd = random.Random(ctx.seed)
    spots = []
    for _ in range(200):
        if len(spots) >= 5:
            break
        x, y = rnd.uniform(40, W - 40), rnd.uniform(70, GY - 40)
        in_crown = any(math.hypot((x - cx) / (rx + 14), (y - cy) / (ry + 14)) < 1 for cx, cy, rx, ry in crowns)
        if not in_crown and _clear_spot(x, y, 12, things + [(a, b, 40) for a, b, _, _ in spots]):
            spots.append((x, y, round(rnd.uniform(.8, 1), 2), rnd.randrange(72)))
    for _ in range(2):
        spots.append((rnd.uniform(60, W - 60), GY + rnd.uniform(14, 24), .85, rnd.randrange(72)))

    scene = (f'<clipPath id="gin"><rect x="8" y="8" width="{W - 16}" height="{g.H - 16}" rx="4"/></clipPath>'
             f'<g clip-path="url(#gin)">{g.sky(*sun_at) if sun_at else ""}{g.ground(ctx.seed)}{"".join(back)}'
             f'{ladder}{"".join(boards)}{"".join(fruits)}{mascot_svg}{g.petals(spots)}</g>')
    H = g.H
    frame = (f'<rect x="{K.MARGIN + K.FRAME / 2:g}" y="{K.MARGIN + K.FRAME / 2:g}" width="{W - 2 * K.MARGIN - K.FRAME:g}" '
             f'height="{H - 2 * K.MARGIN - K.FRAME:g}" rx="{K.R_PANEL}" fill="none" stroke="{k.ink}" stroke-width="{K.FRAME}"/>')
    css = g.css() + k.css_arrive(delay_step=.05, count=8) + css_pick
    by_group = '; '.join(f'{t.name or "tree " + str(t.i + 1)} ({TREE_EN[t.kind]}): '
                         + (', '.join(it[0] for it in t.items) or 'no tools yet') for t in trees)
    if not trees:
        by_group = 'no trees yet'
    story = ''
    if ht:
        story = (' The banana mascot stands on a bamboo ladder by the ' + TREE_EN[ht.kind]
                 + (', picks fruit and drops it into its basket.' if harvest else ' with a basket.'))
    desc = 'An illustrated garden with one tree per group of tools; each tool is a fruit with its logo. ' + by_group + '.' + story
    body = k.card(0, 0, W, H) + f'<defs>{"".join(g.defs)}</defs>' + scene + frame
    svg = k.doc(W, H, body, title='Tech stack garden', desc=desc, css=css)
    return Out(svg=svg, alt='Tech stack garden: ' + by_group)
