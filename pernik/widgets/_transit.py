"""transit: the tech stack drawn as a transit map, in the komik style. Rules: docs/design.md

Every group of tools is a line; every tool is a station (its logo in a small paper roundel on
the line, its name in mono at 45 degrees). All lines meet at one hub roundel that carries the
user's name ("you are here"). The four-line map looks like this:

    1 ●─go─py─rust─node─ts─╮               ╭─echo─gin─fiber─...─react─● 1
                            ╲   PETA STACK ╱
    2 ●─mysql─pg─...─kafka──[  KOCWNG  ]──claude─codex─...─kiro─● 4
                            ╱             ╲
    3 ●─docker─k8s─...─gcp─╯ you are here  ╰─grafana─...─termius─● 3

Layout (only 45 and 90 degree track, round bends):
- Lines are placed in slots around the hub. "top"/"bot" run through the hub as a V above it /
  a Λ below it, "west"/"east" are arms on the hub's own row, "mid" is one straight line through
  the hub, and "z"/"z2" run along the very top row, drop straight through the hub and carry on
  along the very bottom row (two of them cross inside the hub, where the roundel hides it).
- For each number of lines there are a few slot sets; longer lines go to roomier slots, and the
  set with the widest station spacing wins (a little bonus for fewer rows, to stay compact).
- Two-armed lines are split so both arms get about the same spacing; the hub slides sideways so
  the west and east arms do too. Diagonals carry no stations, so the middle stays quiet for the
  title (above the hub) and "you are here" (below it).
- Names always lean away from the hub (left half to the upper left, right half to the upper
  right), so they never cross a line; each row is as far below the last as its tallest name needs.
- When stations get crowded the roundels and names shrink a little, never overlap.

Lines are told apart by how they are printed (two colours only), every band with the same ink
edge so they look like one set:
    1 spot   2 solid (ink by day, deep spot at night)   3 spot halftone   4 hollow
    5 spot dashes   6 ink dashes
A dashed zone of fine halftone sits behind the hub: the one burst, making the person the hero.

Motion: lines draw in once, stations stamp in, and (train = true) one small train rides line 1:
the one idle loop. With reduced motion it waits on the line; the still frame is a finished map.
"""
import math
import re

from .. import komik as K
from ..theme import load_theme
from . import Out
from ._komik_heading import fit_label, flag, label_text, label_width, n
from ._komik_stack import _parse
from .stack import _index, logo_transform, resolve

W = 900
END_L, END_R = 48, 852             # terminus bullets (x)
EDGE_L, EDGE_R = 28, 872           # names must stay inside these
TOP_PAD = 24                       # card edge (8) + 16
BAND, CORE = 12, 7                 # line band: an ink edge 2.5 each side around a 7 px core
CORNER = 28                        # radius of the curves at the bends
BADGE = 15                         # station roundel radius (shrinks when crowded, down to 11)
NAME = 13                          # station name size, mono (shrinks when crowded, down to 10)
NAME_MAX = 14                      # longer names are cut with "…"
MONO_ADV = .6
MIN_GAP = 88                       # rows are at least this far apart
RING = 34                          # hub ring radius (centre of its band)
BAR_H = 28                         # hub name bar
CLEAR = 28                         # first station this far past the hub bar / a bend
CLEAR_Z = 64                       # ... and this far from the straight drop of a z line
ZONE = 64                          # radius of the halftone zone around the hub
JOG = 10                           # two z lines drop 2*JOG apart and swap sides inside the hub
MAX_LINES, MAX_STOPS = 6, 16
STYLES = ('spot', 'ink', 'dots', 'hollow', 'sdash', 'idash')
TITLE_ROOM = 80                    # title bar + caption above the top row
GRID = 56                          # logo path grid: the longer side of its box is GRID steps
SPECK = 3                          # sub-paths at most this many steps across are left out
FLAT = .8                          # curves whose handles stray less than this (steps) become lines

ROOM = {'mid': 4, 'z': 3, 'z2': 3, 'top': 2, 'bot': 2, 'west': 1, 'east': 1}
LAYOUTS = {
    1: [('mid',)],
    2: [('west', 'east'), ('top', 'bot'), ('mid', 'z')],
    3: [('top', 'west', 'east'), ('top', 'bot', 'mid'), ('z', 'west', 'east')],
    4: [('top', 'bot', 'west', 'east'), ('z', 'top', 'west', 'east')],
    5: [('z', 'top', 'bot', 'west', 'east')],
    6: [('z', 'z2', 'top', 'bot', 'west', 'east')],
}
PAIRS = (('top', 'bot'), ('west', 'east'), ('z', 'z2'))


# ---------------------------------------------------------------------------- small helpers
def _name(title):
    """Station name: lower case, no foundation's name in front ("Apache Kafka" -> kafka), short."""
    t = re.sub(r'^(apache|the)\s+', '', str(title).strip(), flags=re.I).lower()
    return t if len(t) <= NAME_MAX else t[:NAME_MAX - 1].rstrip() + '…'


def _reach(name, size=NAME, badge=BADGE):
    """How far (in x and in y) a 45-degree name reaches from its station's centre."""
    return ((badge + 6) + len(name) * size * MONO_ADV) * .7071 + 2


def _up8(v):
    return int(math.ceil(v / 8) * 8)


def _clean(pts):
    """Drop repeated points and points in the middle of a straight run."""
    out = []
    for p in pts:
        if out and abs(p[0] - out[-1][0]) < .01 and abs(p[1] - out[-1][1]) < .01:
            continue
        if len(out) >= 2:
            (ax, ay), (bx, by) = out[-2], out[-1]
            if abs((bx - ax) * (p[1] - by) - (by - ay) * (p[0] - bx)) < .01:
                out[-1] = p
                continue
        out.append(p)
    return out


def _corners(pts, r=CORNER):
    """(a, corner, b, radius) for each bend of a polyline: the curve runs from a to b."""
    out = []
    for i in range(1, len(pts) - 1):
        (x0, y0), (x1, y1), (x2, y2) = pts[i - 1], pts[i], pts[i + 1]
        l1, l2 = math.hypot(x1 - x0, y1 - y0), math.hypot(x2 - x1, y2 - y1)
        rr = min(r, l1 / 2, l2 / 2)
        a = (x1 - (x1 - x0) / l1 * rr, y1 - (y1 - y0) / l1 * rr)
        b = (x1 + (x2 - x1) / l2 * rr, y1 + (y2 - y1) / l2 * rr)
        out.append((a, (x1, y1), b, rr))
    return out


def _rounded(pts):
    """Path data for a polyline with round corners (quadratic curves)."""
    d = [f'M{n(pts[0][0])} {n(pts[0][1])}']
    for a, c, b, _ in _corners(pts):
        d.append(f'L{n(a[0])} {n(a[1])}Q{n(c[0])} {n(c[1])} {n(b[0])} {n(b[1])}')
    d.append(f'L{n(pts[-1][0])} {n(pts[-1][1])}')
    return ''.join(d)


def _quad_len(a, c, b, steps=12):
    pts = [((1 - t) ** 2 * a[0] + 2 * (1 - t) * t * c[0] + t * t * b[0],
            (1 - t) ** 2 * a[1] + 2 * (1 - t) * t * c[1] + t * t * b[1]) for t in (i / steps for i in range(steps + 1))]
    return sum(math.hypot(q[0] - p[0], q[1] - p[1]) for p, q in zip(pts, pts[1:]))


def _along(pts, p):
    """Distance along the polyline to point p (which lies on it), or None."""
    run = 0.0
    for a, b in zip(pts, pts[1:]):
        seg = math.hypot(b[0] - a[0], b[1] - a[1])
        t = ((p[0] - a[0]) * (b[0] - a[0]) + (p[1] - a[1]) * (b[1] - a[1])) / (seg * seg or 1)
        q = (a[0] + t * (b[0] - a[0]), a[1] + t * (b[1] - a[1]))
        if -.001 <= t <= 1.001 and math.hypot(q[0] - p[0], q[1] - p[1]) < 1:
            return run + t * seg
        run += seg
    return None


# ---------------------------------------------------------------------------- logos
def grid_path(d, box, grid=GRID):
    """Path data moved into a 0..grid box and snapped to whole steps, as short relative commands.

    At logo size a step is about 0.3 px, finer than a screen pixel, and whole numbers need no
    decimals. Then it is made shorter without changing what you see: steps that snap to nothing
    are left out, curves flatter than a step become lines, straight lines become h/v, and smooth
    joins use the s/t shorthand. A logo ends up at roughly half its 0.1-unit size."""
    bx, by, bw, bh = box
    sc = grid / max(bw, bh)
    try:
        segs = _parse(d)
    except ValueError:
        return None
    # 1. absolute float geometry, with S/T written out and H/V as lines
    ops, cx, cy, sx, sy, prev = [], 0.0, 0.0, 0.0, 0.0, None     # prev = (kind, last control)
    for c, v in segs:
        C, rel = c.upper(), c.islower()
        ox, oy = (cx, cy) if rel else (0.0, 0.0)
        if C == 'Z':
            ops.append(('Z', []))
            cx, cy, prev = sx, sy, None
            continue
        if C == 'H':
            pts, C = [(v[0] + ox, cy)], 'L'
        elif C == 'V':
            pts, C = [(cx, v[0] + oy)], 'L'
        elif C == 'A':
            pts = [(v[5] + ox, v[6] + oy)]
        else:
            pts = [(v[j] + ox, v[j + 1] + oy) for j in range(0, len(v), 2)]
        if C in 'ST':
            k = 'C' if C == 'S' else 'Q'
            ref = (2 * cx - prev[1][0], 2 * cy - prev[1][1]) if prev and prev[0] == k else (cx, cy)
            pts, C = [ref] + pts, k
        if C == 'A':
            ops.append(('A', pts, v[:5]))
        else:
            ops.append((C, pts))
        prev = (C, pts[-2]) if C in 'CQ' else None
        cx, cy = pts[-1]
        if C == 'M':
            sx, sy = cx, cy
    # 2. snap to the grid, flatten what is flat, then write short relative commands
    q = lambda p: (round((p[0] - bx) * sc), round((p[1] - by) * sc))
    out, last = [], ['']
    cur = start = (0, 0)
    pc = None                                     # (kind, previous control) on the grid

    def emit(cmd, nums):
        new = cmd != last[0] or cmd in 'mz'
        if new:
            out.append(cmd)
        for v in nums:
            t = str(v)
            out.append(t if (new or t[0] == '-') else ' ' + t)
            new = False
        last[0] = cmd

    def flat(a, ctrl, b):
        dx, dy = b[0] - a[0], b[1] - a[1]
        ln = math.hypot(dx, dy)
        for p in ctrl:
            dist = abs(dx * (p[1] - a[1]) - dy * (p[0] - a[0])) / ln if ln else math.hypot(p[0] - a[0], p[1] - a[1])
            if dist > FLAT:
                return False
        return True

    # sub-paths smaller than a pixel or so (specks in a detailed logo) are not drawn at all
    keep, sub, box_ = [], [], None
    for op in ops + [('M', [(0, 0)])]:
        if op[0] == 'M' and sub:
            if box_ and max(box_[2] - box_[0], box_[3] - box_[1]) > SPECK:
                keep += sub
            sub, box_ = [], None
        sub.append(op)
        for p in op[1]:
            x, y = q(p)
            box_ = (min(box_[0], x), min(box_[1], y), max(box_[2], x), max(box_[3], y)) if box_ else (x, y, x, y)
    ops = keep
    for i, op in enumerate(ops):
        C, pts = op[0], [q(p) for p in op[1]]
        nxt = ops[i + 1][0] if i + 1 < len(ops) else ''
        if C == 'Z':
            emit('z', [])
            cur, pc = start, None
            continue
        end_ = pts[-1]
        rel = [(x - cur[0], y - cur[1]) for x, y in pts]
        if C == 'M':
            emit('M' if not out else 'm', list(rel[0]))
            cur = start = end_
            pc = None
            continue
        if C == 'A':
            a = op[2]
            emit('a', [max(1, round(a[0] * sc)), max(1, round(a[1] * sc)), f'{a[2]:g}', int(a[3]), int(a[4]), *rel[0]])
            cur, pc = end_, None
            continue
        if C in 'CQ' and nxt not in ('C', 'Q') and flat(cur, pts[:-1], end_):
            C = 'L'                               # flatter than a grid step (and nothing smooths off it)
        if C == 'L':
            if end_ == cur:
                continue                          # snapped to nothing
            if rel[-1][1] == 0:
                emit('h', [rel[-1][0]])
            elif rel[-1][0] == 0:
                emit('v', [rel[-1][1]])
            else:
                emit('l', list(rel[-1]))
            cur, pc = end_, None
            continue
        if end_ == cur and all(p == cur for p in pts):
            continue
        ref = (2 * cur[0] - pc[1][0], 2 * cur[1] - pc[1][1]) if pc and pc[0] == C else None
        if C == 'C':
            if ref == pts[0]:
                emit('s', [a for p in rel[1:] for a in p])
            else:
                emit('c', [a for p in rel for a in p])
        else:
            if ref == pts[0]:
                emit('t', list(rel[-1]))
            else:
                emit('q', [a for p in rel for a in p])
        cur, pc = end_, (C, pts[-2])
    return ''.join(out)


def _logo(k, cx, cy, item, size):
    title, d, box, _, rule = item
    bx, by, bw, bh = box
    gd = grid_path(d, box) if d and bw / bh <= 2.5 else None   # a wide wordmark would be a sliver
    if gd:
        m = max(bw, bh)
        tf, _ = logo_transform(cx - size / 2, cy - size / 2, size, (0, 0, bw * GRID / m, bh * GRID / m))
        fr = f' fill-rule="{rule}"' if rule else ''
        return f'<path class="lg" transform="{tf}" d="{gd}"{fr}/>'
    letter = next((ch for ch in str(title) if ch.isalnum()), '?').upper()
    return (f'<text x="{n(cx)}" y="{n(cy + size * .3)}" font-size="{n(size * .85)}" text-anchor="middle" '
            f'class="kl" fill="{k.ink}">{K.esc(letter)}</text>')


# ---------------------------------------------------------------------------- printing
def _band(k, d, style, draw=True):
    """One line: its ink edge and its core. Returns (edge, core) so every edge sits under every core."""
    pl = ' pathLength="1"' if draw else ''
    cls = ' draw' if draw else ''
    edge = f'<path class="e{cls}" d="{d}"{pl}/>'
    if style in ('sdash', 'idash'):
        ink = k.spot if style == 'sdash' else k.ink
        core = (f'<path class="c{cls}" d="{d}" stroke="{k.paper}"{pl}/>'
                f'<path class="c{" fade" if draw else ""}" d="{d}" stroke="{ink}" stroke-dasharray="9 6" '
                f'stroke-linecap="butt"/>')
    elif style == 'dots':      # paper under the dots, so the band reads as a printed tone
        core = f'<path class="c{cls}" d="{d}" stroke="{k.paper}"{pl}/><path class="c{cls}" d="{d}" stroke="url(#tdot)"{pl}/>'
    else:
        col = {'spot': k.spot, 'ink': k.solid, 'hollow': k.paper}[style]
        core = f'<path class="c{cls}" d="{d}" stroke="{col}"{pl}/>'
    return edge, core


def _bullet(k, cx, cy, num, style, r=12):
    """A line's number in a roundel printed like the line (the map's line bullet)."""
    fill, fg = {'spot': (k.spot, k.ink if k.mode == 'light' else k.paper), 'ink': (k.solid, k.on_solid),
                'dots': ('url(#tdot)', k.ink), 'hollow': (k.paper, k.ink), 'sdash': (k.tint, k.ink),
                'idash': ('url(#hatch)', k.ink)}[style]
    patterned = fill.startswith('url(')
    under = f'<circle cx="{n(cx)}" cy="{n(cy)}" r="{r}" fill="{k.paper}"/>' if patterned else ''
    halo = (f' stroke="{k.paper}" stroke-width="3" paint-order="stroke" stroke-linejoin="round"'
            if patterned else '')
    return (under + f'<circle cx="{n(cx)}" cy="{n(cy)}" r="{r}" fill="{fill}" stroke="{k.ink}" stroke-width="{K.LINE}"/>'
            f'<text x="{n(cx)}" y="{n(cy + r * .42)}" font-size="{n(r * 1.15)}" text-anchor="middle" class="kl" '
            f'fill="{fg}"{halo}>{num}</text>')


def _station(k, cx, cy, item, i, g):
    """The roundel with the logo (it stamps in)."""
    return (f'<g class="arrive a{i % 8}"><circle class="sb" cx="{n(cx)}" cy="{n(cy)}" r="{n(g["badge"])}"/>'
            f'{_logo(k, cx, cy, item, g["logo"])}</g>')


def _names(spots, g):
    """Station names at 45 degrees, leaning away from the hub. All names on one side share one
    turned group, so each name only needs its position (in the group's turned coordinates)."""
    c = .7071
    o = (g['badge'] + 6) * c
    base = g['name'] * .34
    left, right = [], []
    for x, y, side, item in spots:
        t = K.esc(_name(item[0]))
        if side > 0:      # right of the hub: reads up and to the right; group is rotate(-45)
            gx, gy = x + o, y - o
            right.append(f'<text x="{n(c * gx - c * gy)}" y="{n(c * gx + c * gy + base)}">{t}</text>')
        else:             # left of the hub: reads down towards the station; group is rotate(45)
            gx, gy = x - o, y - o
            left.append(f'<text x="{n(c * gx + c * gy)}" y="{n(-c * gx + c * gy + base)}">{t}</text>')
    out = ''
    if left:
        out += f'<g class="km sn fade" transform="rotate(45)" text-anchor="end">{"".join(left)}</g>'
    if right:
        out += f'<g class="km sn fade" transform="rotate(-45)">{"".join(right)}</g>'
    return out


def _kit(ctx):
    """The komik kit; themes without a [komik] table (the sticker themes) borrow komik's colours."""
    theme = ctx.theme
    if not isinstance(getattr(theme, 'raw', None), dict) or 'komik' not in theme.raw:
        theme = load_theme('komik')
    return K.Kit(theme, ctx.mode)


# ---------------------------------------------------------------------------- layout
def _assign(lines, slots):
    """{slot: line}: the longest lines get the roomiest slots; a pair keeps the user's order."""
    by_size = sorted(lines, key=lambda l: (-len(l['items']), l['num']))
    order = sorted(slots, key=lambda s: -ROOM[s])
    got = dict(zip(order, by_size))
    for a, b in PAIRS:
        if a in got and b in got and got[a]['num'] > got[b]['num']:
            got[a], got[b] = got[b], got[a]
    return got


def _first_x(items):
    return max(END_L + 40, EDGE_L + _reach(_name(items[0][0]))) if items else END_L + 40


def _last_x(items):
    return min(END_R - 40, EDGE_R - _reach(_name(items[-1][0]))) if items else END_R - 40


def _arm_xs(side, inner, items):
    """Station x positions (left to right) for one arm; side -1 runs out to the left."""
    if not items:
        return []
    if len(items) == 1:
        return [inner]
    a, b = (_first_x(items), inner) if side < 0 else (inner, _last_x(items))
    if b < a:
        a = b = inner
    return [a + (b - a) * i / (len(items) - 1) for i in range(len(items))]


def _pitch(xs):
    return min((b - a for a, b in zip(xs, xs[1:])), default=1e9)


def _split(items, arm1, arm2):
    """Split items over two arms (each (side, inner)) so the tighter arm is as roomy as it can be."""
    if len(items) <= 1:
        return [(arm1, items), (arm2, [])]
    best = None
    for k in range(1, len(items)):
        a, b = items[:k], items[k:]
        p = min(_pitch(_arm_xs(*arm1, a)), _pitch(_arm_xs(*arm2, b)))
        if best is None or p > best[0] + .01:
            best = (p, k)
    k = best[1]
    return [(arm1, items[:k]), (arm2, items[k:])]


def _plan(lines, slots, hub_w):
    """Rows, hub position, paths and stations for one slot set. Returns a dict (with 'score')."""
    got = _assign(lines, slots)
    has = set(got)
    z = 'z' in has
    rows = (['A'] if z else []) + (['B'] if 'top' in has else []) + ['M'] + \
           (['C'] if 'bot' in has else []) + (['D'] if z else [])
    row_items = {r: [] for r in rows}            # names per row (for the row gaps)
    for s, l in got.items():
        it = l['items']
        if s in ('top',):
            row_items['B'] += it
        elif s == 'bot':
            row_items['C'] += it
        elif s in ('mid', 'west', 'east'):
            row_items['M'] += it
        else:
            row_items['A'] += it
            row_items['D'] += it

    def need(r):
        names = [_name(t[0]) for t in row_items[r]] or ['']
        return max(MIN_GAP, _up8(BADGE + 10 + max(_reach(nm) for nm in names)))

    # gaps between rows: each row sits as far below the one above as its own names need,
    # mirrored around the hub's row so the V and the Λ have the same diagonals
    mi = rows.index('M')
    above = [need(rows[i + 1]) for i in range(mi - 1, -1, -1)]      # gap just above M first
    below = [need(rows[i]) for i in range(mi + 1, len(rows))]
    for i in range(min(len(above), len(below))):
        above[i] = below[i] = max(above[i], below[i])
    gaps = list(reversed(above)) + below
    return got, rows, gaps


def _layout(lines, slots, hub_w, title_on):
    got, rows, gaps = _plan(lines, slots, hub_w)
    top_names = [_name(t[0]) for s, l in got.items() for t in l['items']
                 if (rows[0] == 'A' and s in ('z', 'z2')) or (rows[0] == 'B' and s == 'top')
                 or (rows[0] == 'M' and s in ('mid', 'west', 'east'))]
    band = max(_reach(nm) for nm in top_names) + 8 if top_names else 24
    room = (TITLE_ROOM + (RING + 16 if rows[0] == 'M' else 0)) if title_on else 0
    y0 = _up8(TOP_PAD + max(band, room))
    ys, y = {}, y0
    for r, g in zip(rows, [0] + gaps):
        y += g
        ys[r] = y
    M = ys['M']

    cbar = hub_w / 2 + CLEAR
    hx = W / 2
    if 'west' in got and 'east' in got:
        a, b = max(1, len(got['west']['items']) - 1), max(1, len(got['east']['items']) - 1)
        xl, xr = _first_x(got['west']['items']), _last_x(got['east']['items'])
        hx = ((xr - cbar) * a + (xl + cbar) * b) / (a + b)
    hx = round(min(W / 2 + 64, max(W / 2 - 64, hx)) / 8) * 8
    dz = JOG if 'z2' in got else 0

    placed = []          # (line, path points, [(x, y, side, item)])
    for s, l in got.items():
        it = l['items']
        if s == 'mid':
            pts = [(END_L, M), (END_R, M)]
            arms = _split(it, (-1, hx - cbar), (1, hx + cbar))
            ys_ = (M, M)
        elif s == 'west':
            pts, arms, ys_ = [(END_L, M), (hx, M)], [((-1, hx - cbar), it)], (M,)
        elif s == 'east':
            pts, arms, ys_ = [(hx, M), (END_R, M)], [((1, hx + cbar), it)], (M,)
        elif s in ('top', 'bot'):
            ty = ys['B' if s == 'top' else 'C']
            run = abs(M - ty)
            pts = [(END_L, ty), (hx - run, ty), (hx, M), (hx + run, ty), (END_R, ty)]
            arms = _split(it, (-1, hx - run - CLEAR), (1, hx + run + CLEAR))
            ys_ = (ty, ty)
        elif s == 'z':           # top row, left half -> down through the hub -> bottom row, right half
            A, D = ys['A'], ys['D']
            pts = [(END_L, A), (hx - dz, A), (hx - dz, M - dz), (hx + dz, M + dz), (hx + dz, D), (END_R, D)]
            arms = _split(it, (-1, hx - CLEAR_Z), (1, hx + CLEAR_Z))
            ys_ = (A, D)
        else:                    # z2: bottom row, left half -> up through the hub -> top row, right half
            A, D = ys['A'], ys['D']
            pts = [(END_L, D), (hx - dz, D), (hx - dz, M + dz), (hx + dz, M - dz), (hx + dz, A), (END_R, A)]
            arms = _split(it, (-1, hx - CLEAR_Z), (1, hx + CLEAR_Z))
            ys_ = (D, A)
        spots = []
        for ((side, inner), part), yy in zip(arms, ys_):
            spots += [(x, yy, side, item) for x, item in zip(_arm_xs(side, inner, part), part)]
        placed.append((l, _clean(pts), spots))

    pitches = []
    for _, _, spots in placed:
        for a, b in zip(spots, spots[1:]):
            if a[1] == b[1] and a[2] == b[2]:
                pitches.append(abs(b[0] - a[0]))
    p = min(pitches, default=60)
    score = min(p, 44) - 2 * len(rows)
    return {'got': got, 'rows': rows, 'ys': ys, 'M': M, 'hx': hx, 'placed': placed, 'pitch': p,
            'score': score, 'z': 'z' in got, 'bottom': ys[rows[-1]]}


# ---------------------------------------------------------------------------- the widget
def _lines_from(opts, say):
    raw = opts.get('line') or []
    if isinstance(raw, dict):
        raw = [raw]
    if not isinstance(raw, list):
        say('line should be a list of [[widget.line]] tables; drawing an empty map')
        raw = []
    raw = [r for r in raw if isinstance(r, dict)]
    if len(raw) > MAX_LINES:
        say(f'{len(raw)} lines; a map holds {MAX_LINES}, so only the first {MAX_LINES} are drawn')
        raw = raw[:MAX_LINES]
    out = []
    for i, r in enumerate(raw, 1):
        icons = r.get('icons') or []
        if isinstance(icons, str):
            icons = [x for x in re.split(r'[,\n]+', icons) if x.strip()]
        icons = [str(x).strip() for x in icons if str(x).strip()]
        name = str(r.get('name') or '').strip() or f'line {i}'
        if len(icons) > MAX_STOPS:
            say(f'line "{name}" has {len(icons)} stops; a line holds {MAX_STOPS}, so only the first {MAX_STOPS} are drawn')
            icons = icons[:MAX_STOPS]
        logos = r.get('logos') or {}
        out.append((name, icons, logos if isinstance(logos, dict) else {}))
    return out


def render(opts, ctx):
    """Out for the transit widget (opts: title, hub, train, line = [{name, icons, logos}])."""
    k = _kit(ctx)
    say = ctx.log if ctx.mode == 'light' else (lambda *a: None)
    groups = _lines_from(opts, say)
    title = str(opts.get('title') if opts.get('title') is not None else 'peta stack').strip()
    who = str(opts.get('hub') or '').strip() or str(ctx.user or 'me')
    train_on = flag(opts.get('train'), True)

    idx = _index(ctx.root, say) if any(g[1] for g in groups) else {}
    lines = []
    for num, (gname, icons, logos) in enumerate(groups, 1):
        items = [resolve(raw, ctx, idx, logos, say) for raw in icons]
        lines.append({'num': num, 'name': gname, 'items': items, 'style': STYLES[num - 1]})

    # hub bar: as wide as the name needs (within reason)
    hub_text, hub_size = fit_label(who.upper(), 176 - 24, 15, 10)
    hub_w = max(112, _up8(label_width(hub_text, hub_size) + 28))

    if lines:
        plans = [_layout(lines, s, hub_w, bool(title)) for s in LAYOUTS[len(lines)]]
        lay = max(plans, key=lambda p: p['score'])         # first one wins a tie
    else:
        m = _up8(TOP_PAD + (TITLE_ROOM if title else 0) + RING + 16)
        lay = {'got': {}, 'rows': ['M'], 'ys': {'M': m}, 'M': m, 'hx': 448, 'placed': [], 'pitch': 60,
               'z': True, 'bottom': m + RING + 40}
    M, hx = lay['M'], lay['hx']

    # crowded stations: smaller roundels and names, never overlapping
    p = lay['pitch']
    badge = max(11.0, min(BADGE, (p - 6) / 2))
    g = {'badge': badge, 'logo': round(badge * 1.2, 1), 'name': max(10.0, min(NAME, p * .7071 - 4))}

    stations, edges, cores, bullets, every = [], [], [], [], []
    order, train = 0, None
    for l, pts, spots in lay['placed']:
        d = _rounded(pts)
        e, c = _band(k, d, l['style'])
        edges.append(e)
        cores.append(c)
        for x, y, side, item in spots:
            stations.append(_station(k, x, y, item, order, g))
            order += 1
        every += spots
        for ex, ey in (pts[0], pts[-1]):
            if ex in (END_L, END_R):
                bullets.append(_bullet(k, ex, ey, l['num'], l['style']))
        if l['num'] == 1:
            train = (d, pts, [(x, y) for x, y, *_ in spots])

    # the hub: a spot ring with the name on a bar across it, on a halftone zone
    zone = (f'<circle cx="{n(hx)}" cy="{M}" r="{ZONE}" fill="url(#ht1)" stroke="{k.ink}" stroke-width="{K.HAIR}" '
            f'stroke-dasharray="2 5" stroke-linecap="round"/>')
    hub = (f'<circle cx="{n(hx)}" cy="{M}" r="{RING}" fill="{k.paper}" stroke="{k.ink}" stroke-width="15"/>'
           f'<circle cx="{n(hx)}" cy="{M}" r="{RING}" fill="none" stroke="{k.spot}" stroke-width="10"/>'
           f'<rect x="{n(hx - hub_w / 2)}" y="{M - BAR_H / 2}" width="{hub_w}" height="{BAR_H}" rx="{K.R_LABEL}" '
           f'fill="{k.solid}" stroke="{k.ink}" stroke-width="{K.LINE}"/>'
           + label_text(hx, M + hub_size * .36, hub_text, hub_size, k.on_solid, 'middle'))
    bottom = lay['bottom'] + badge
    here = ''
    if not lay['z']:          # "you are here" in the quiet space under the hub
        py = M + ZONE + 6
        here = (f'<path d="M{n(hx)} {py}l6 9h-12z" fill="{k.spot}" stroke="{k.ink}" stroke-width="{K.HAIR}" '
                f'stroke-linejoin="round"/>' + k.mono(hx, py + 25, 'you are here', 12, 'middle'))
        bottom = max(bottom, py + 30)
    if not lines:
        here = k.mono(hx, M + RING + 30, 'no lines yet', 13, 'middle')

    # the title, in the quiet space above the hub
    count = sum(len(l['items']) for l in lines)
    head = ''
    if title:
        y0 = lay['ys'][lay['rows'][0]]
        if lay['rows'][0] == 'M':          # nothing above the hub's row: sit above the ring
            y0 = M - RING - 16
        tw = min(176, max(128, _up8(label_width(title, 15) + 32)))
        shown, size = fit_label(title, tw - 24, 15, 10)
        cap = f'{len(lines)} line{"s" * (len(lines) != 1)} · {count} stop{"s" * (count != 1)}'
        head = (k.label(hx - tw / 2, y0 - 72, tw, 28, shown, size=size)
                + k.mono(hx, y0 - 22, cap, 12, 'middle'))

    # the key: bullet, a stretch of the line, its name (one row, or rows of three)
    rule_y = _up8(bottom + 12)
    keys, avail = [], W - 2 * 40
    entries = []
    for l in lines:
        nm, sz = fit_label(l['name'], 240, 11, 9)
        entries.append([l, nm, sz, 74 + label_width(nm, sz)])
    one_row = len(lines) <= 4 and sum(e[3] for e in entries) + 24 * (len(lines) - 1) <= avail
    cols = len(lines) if one_row else max(1, math.ceil(len(lines) / 2))
    if not one_row:
        for e in entries:
            e[1], e[2] = fit_label(e[0]['name'], avail / cols - 74 - 16, 11, 8.5)
            e[3] = 74 + label_width(e[1], e[2])
    rows_n = math.ceil(len(entries) / cols) if entries else 0
    for r in range(rows_n):
        row = entries[r * cols:(r + 1) * cols]
        ky = rule_y + 24 + r * 28
        if one_row:
            gap = (avail - sum(e[3] for e in row)) / max(1, len(row) - 1) if len(row) > 1 else 0
            x = 40 if len(row) > 1 else (W - row[0][3]) / 2
        for j, (l, nm, sz, w) in enumerate(row):
            if not one_row:
                x = 40 + j * avail / cols
            e, c = _band(k, f'M{n(x + 28)} {ky}h28', l['style'], draw=False)
            keys.append(e + c + _bullet(k, x + 12, ky, l['num'], l['style'], r=11)
                        + label_text(x + 74, ky + sz * .36, nm, sz, k.ink))
            if one_row:
                x += w + gap
    if rows_n:
        keys.insert(0, f'<path d="M24 {rule_y}H{W - 24}" stroke="{k.ink}" stroke-width="{K.HAIR}" '
                       f'stroke-dasharray="2 5" stroke-linecap="round"/>')
        H = _up8(rule_y + 24 + (rows_n - 1) * 28 + 28)
    else:
        H = _up8(bottom + 32)

    # one small train on line 1 (the idle loop); it waits in the longest empty stretch of track
    ride, css_train = '', ''
    if train and train_on:
        d, pts, stops = train
        corners = _corners(pts)
        save = [(_along(pts, c), 2 * rr - _quad_len(a, c, b)) for a, c, b, rr in corners]
        total = sum(math.hypot(b[0] - a[0], b[1] - a[1]) for a, b in zip(pts, pts[1:]))
        marks = sorted({0.0, total, *(m for m in (_along(pts, s) for s in stops) if m is not None)})
        hub_at = _along(pts, (hx, M))
        hub_r = max(RING, hub_w / 2) + 12
        free = []                               # stretches of track with nothing on them
        for a, b in zip(marks, marks[1:]):
            a2 = a + (24 if a == 0 else badge + 10)
            b2 = b - (24 if b == total else badge + 10)
            if hub_at is not None and a2 < hub_at + hub_r and b2 > hub_at - hub_r:
                free += [(a2, hub_at - hub_r), (hub_at + hub_r, b2)]
            else:
                free.append((a2, b2))
        best = max(((b - a, (a + b) / 2) for a, b in free if b > a), default=None)
        mid = best[1] if best else total / 2
        real = total - sum(s for _, s in save)
        park = (mid - sum(s for at, s in save if at is not None and at < mid)) / real * 100
        ride = (f'<g class="train"><rect x="-11" y="-4.5" width="22" height="9" rx="4.5" fill="{k.ink}" '
                f'stroke="{k.paper}" stroke-width="{K.HAIR}"/>'
                f'<path d="M-5 -1.5h3M1 -1.5h3" stroke="{k.paper}" stroke-width="{K.HAIR}" stroke-linecap="round"/></g>')
        secs = max(12, round(real / 40))
        css_train = (f".train{{offset-path:path('{d}');offset-rotate:auto;offset-distance:{park:.1f}%;"
                     f"animation:ride {secs}s linear 1.2s infinite}}"
                     "@keyframes ride{0%{offset-distance:0%}50%{offset-distance:100%}100%{offset-distance:0%}}")

    css = (k.css_arrive(delay_step=.05, count=8)
           + f'.e{{fill:none;stroke:{k.ink};stroke-width:{BAND}px;stroke-linecap:round;stroke-linejoin:round}}'
           f'.c{{fill:none;stroke-width:{CORE}px;stroke-linecap:round;stroke-linejoin:round}}'
           f'.sb{{fill:{k.paper};stroke:{k.ink};stroke-width:{K.LINE}px}}.lg{{fill:{k.ink}}}'
           f'.sn{{font-size:{n(g["name"])}px;fill:{k.ink}}}'
           '.draw{animation:draw 1.1s cubic-bezier(.5,0,.3,1) both}'
           '@keyframes draw{0%{stroke-dasharray:1;stroke-dashoffset:1}100%{stroke-dasharray:1;stroke-dashoffset:0}}'
           '.fade{animation:fade .4s .9s both}@keyframes fade{0%{opacity:0}100%{opacity:1}}'
           + css_train)
    defs = (f'<defs><pattern id="tdot" width="5" height="5" patternUnits="userSpaceOnUse" patternTransform="rotate(45)">'
            f'<circle cx="2.5" cy="2.5" r="1.6" fill="{k.spot}"/></pattern></defs>')
    body = (k.card(0, 0, W, H) + defs + (zone if lines else '') + head + ''.join(edges) + ''.join(cores) + ride
            + ''.join(stations) + _names(every, g) + ''.join(bullets) + hub + here + ''.join(keys))

    parts = [f"line {l['num']} {l['name']}: " + (', '.join(_name(t[0]) for t in l['items']) or 'no stops')
             for l in lines]
    alt = (f'Tech stack as a transit map, {len(lines)} line{"s" * (len(lines) != 1)} meeting at {who}'
           + (': ' + '; '.join(parts) + '.' if parts else '.'))
    svg = k.doc(W, H, body, title='Tech stack as a transit map', desc=alt, css=css)
    if len(svg.encode()) > 60 * 1024:
        say(f'{len(svg.encode()) // 1024} KB; a map this full loads slowly, try fewer stops')
    return Out(svg=svg, alt=alt)
