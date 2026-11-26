"""stack in the komik style: one comic panel per tool, like the bottom row of a manga page.

Each panel has an ink title bar (the tool's name), its logo large in the middle in ink over a
jagged halftone burst, and a numbered badge in the corner (the order is the user's order).
Logos are Simple Icons, fetched and cached by stack.py; brand colours are not used (two-tone
rule). Unknown slugs get a big monogram letter instead of a logo. Rules: docs/design.md

density = "compact" draws chips instead: a small logo tile and the name, four to a row. Use it
for long lists, where big panels would make the tech stack the longest part of the page.
"""
import math
import random
import re

from .. import komik as K
from . import Out
from ._komik_heading import fit_label, flag, label_text, n
from .stack import _index, logo_transform, resolve

W = 900
PAD = 24           # card outer edge (4) + frame (4) + 16 inside
GUT = 16
PANEL_H = 184
BAR = 32           # title bar height
LOGO = 72          # logo box (px)
TITLE = 18
BURSTS = 3         # burst shapes per widget; each panel turns one of them its own way


def _columns(n_items, want):
    if want:
        return max(1, min(6, want, n_items))
    if n_items <= 4:
        return max(1, n_items)
    # 3 or 4 per row: fewest rows, then the fullest last row, then the wider panels
    return min((3, 4), key=lambda c: (math.ceil(n_items / c), -(n_items % c or c) / c, c))


CHIP_H = 48        # compact chips
CHIP_GAP = 12
CHIP_LOGO = 28


def render(opts, ctx):
    density = str(opts.get('density', 'panels')).strip().lower()
    if density == 'compact':
        return render_compact(opts, ctx)
    if density == 'manga':
        return render_manga(opts, ctx)
    k = K.Kit(ctx.theme, ctx.mode)
    say = ctx.log if ctx.mode == 'light' else (lambda *a: None)
    icons = opts.get('icons') or []
    if isinstance(icons, str):
        icons = [i for i in re.split(r'[,\s]+', icons) if i]
    icons = [str(i).strip() for i in icons if str(i).strip()][:24]
    numbered = flag(opts.get('numbered'), True)
    try:
        want = int(opts.get('columns') or 0)
    except (TypeError, ValueError):
        want = 0

    idx = _index(ctx.root, say) if icons else {}
    logos = opts.get('logos') or {}
    logos = logos if isinstance(logos, dict) else {}
    items = []                       # (title, path d or None, viewBox, fill rule)
    for raw in icons:
        title, d, box, _, rule = resolve(raw, ctx, idx, logos, say)
        items.append((title, d, box, rule))

    count = len(items)
    cols = _columns(count, want)
    rows = max(1, math.ceil(count / cols))
    h = 2 * PAD + rows * PANEL_H + (rows - 1) * GUT
    inner = W - 2 * PAD
    rng = random.Random(ctx.seed)
    # a few seeded burst shapes, defined once and reused (keeps the file small)
    shapes = ''.join(
        k.burst(0, 0, r2 * .72, r2, pts, seed=rng.randrange(1 << 16)).replace('<polygon ', f'<polygon id="kb{j}" ', 1)
        for j, (pts, r2) in enumerate(zip(rng.sample((12, 13, 14, 15, 16), BURSTS), (64, 60, 62))))

    panels = []
    for r in range(rows):
        row = items[r * cols:(r + 1) * cols]
        m = len(row)                 # a short last row stretches, like a manga page
        for j, (title, d, box, rule) in enumerate(row):
            i = r * cols + j
            x = PAD + round(j * (inner + GUT) / m)
            w = PAD + round((j + 1) * (inner + GUT) / m) - GUT - x
            y = PAD + r * (PANEL_H + GUT)
            panels.append(_panel(k, rng, i, x, y, w, title, d, numbered, box, rule))
    if not items:
        panels.append(f'<text x="{W / 2:g}" y="{h / 2 + 5:g}" font-size="14" text-anchor="middle" class="km" '
                      f'fill="{k.ink}">no tools listed yet</text>')

    body = k.card(0, 0, W, h) + f'<defs>{shapes}</defs>' + ''.join(panels)
    names = [t for t, *_ in items]
    title = 'Tech stack: ' + ', '.join(names) if names else 'Tech stack'
    desc = (f'{count} comic panels, one per tool' + (', numbered in order' if numbered else '') + ': '
            + ', '.join(names) + '.') if names else 'No tools listed yet.'
    svg = k.doc(W, h, body, title=title, desc=desc, css=k.css_arrive(delay_step=.07, count=max(1, count)))
    if len(svg.encode()) > 25 * 1024:
        say(f'{len(svg.encode()) // 1024} KB, over the 25 KB budget; try fewer icons')
    return Out(svg=svg, alt=title)


def _panel(k, rng, i, x, y, w, title, d, numbered, box=(0, 0, 24, 24), rule=None):
    cx = x + w / 2
    cy = y + BAR + (PANEL_H - BAR) / 2
    out = []                                                       # the card's paper shows through
    # title bar flush with the panel top (its top corners follow the panel's radius)
    r = K.R_PANEL
    out.append(f'<path d="M{x} {y + BAR}V{y + r}Q{x} {y} {x + r} {y}H{x + w - r}Q{x + w} {y} {x + w} {y + r}'
               f'V{y + BAR}Z" fill="{k.solid}"/>')
    shown, size = fit_label(title, w - 32, TITLE, 10)
    out.append(label_text(cx, y + BAR / 2 + size * .36, shown, size, k.on_solid, 'middle'))
    # the burst: seeded number of points, turn and size, so a row doesn't look stamped
    out.append(f'<use href="#kb{(i * 2 + rng.randrange(2)) % BURSTS}" '
               f'transform="translate({n(cx)} {n(cy)}) rotate({rng.randrange(0, 30)})"/>')
    halo = f'stroke="{k.paper}" stroke-linejoin="round" paint-order="stroke"'
    if d:
        tf, s = logo_transform(cx - LOGO / 2, cy - LOGO / 2, LOGO, box)
        path = compact_path(d) if box == (0, 0, 24, 24) else d
        fr = f' fill-rule="{rule}"' if rule else ''
        out.append(f'<path transform="{tf}" d="{path}" '
                   f'fill="{k.ink}"{fr} {halo} stroke-width="{2 * K.MARGIN / s:.2f}"/>')
    else:
        # no logo: a short name (AWS, GCP) is printed whole, a longer one as its first letter
        # no logo: print the name itself as big as the panel allows (AWS, GORM, BEDROCK, ANTIGRAVITY),
        # and fall back to its first letter only when even that would be too small to read
        word = re.sub(r'[^A-Za-z0-9 ]', '', title).strip().upper()
        fs = min(56.0, (w - 48) / (max(1, len(word)) * .8))
        mono = word if fs >= 18 else (word[:1] or '?')
        fs = 72 if len(mono) == 1 else max(18, int(fs))
        out.append(f'<text x="{n(cx)}" y="{n(cy + fs * .36)}" font-size="{fs}" text-anchor="middle" class="kl" '
                   f'fill="{k.ink}" {halo} stroke-width="{2 * K.MARGIN}">{K.esc(mono)}</text>')
    if numbered:
        out.append(k.badge(x + w - 24, y + PANEL_H - 24, i + 1, r=14, filled=True))
    out.append(k.panel(x, y, w, PANEL_H, fill='none'))               # the ink border on top
    return f'<g class="arrive a{i}">{"".join(out)}</g>'


# ---------------------------------------------------------------- smaller logo paths
# Simple Icons paths carry three decimals in a 24-unit box. Drawn 72 px wide, a tenth of a unit
# is 0.3 px, so we snap every point to that grid (absolute, so errors never add up) and write
# it back as short relative steps. That about halves the bytes of a detailed logo.
_CMD = re.compile(r'\s*([MmLlHhVvCcSsQqTtAaZz])')
_NUM = re.compile(r'[\s,]*([-+]?(?:\d*\.\d+|\d+\.?)(?:[eE][-+]?\d+)?)')
_FLAG = re.compile(r'[\s,]*([01])')
_ARGS = {'M': 2, 'L': 2, 'H': 1, 'V': 1, 'C': 6, 'S': 4, 'Q': 4, 'T': 2, 'A': 7, 'Z': 0}


def _parse(d):
    i, out = 0, []
    while i < len(d):
        m = _CMD.match(d, i)
        if not m:
            if d[i:].strip():
                raise ValueError(f'bad path data near {d[i:i + 12]!r}')
            break
        c, i, first = m.group(1), m.end(), True
        k = _ARGS[c.upper()]
        if not k:
            out.append((c, []))
            continue
        while True:
            vals = []
            for j in range(k):
                mm = (_FLAG if c in 'Aa' and j in (3, 4) else _NUM).match(d, i)
                if not mm:
                    break
                vals.append(float(mm.group(1)))
                i = mm.end()
            if len(vals) < k:
                if vals:
                    raise ValueError('incomplete path segment')
                break
            out.append((c if first else {'M': 'L', 'm': 'l'}.get(c, c), vals))
            first = False
    return out


def _tenths(v):
    s = '-' if v < 0 else ''
    a, b = divmod(abs(v), 10)
    return f'{s}{a}' if not b else (f'{s}.{b}' if not a else f'{s}{a}.{b}')


def compact_path(d):
    """Path data snapped to a 0.1-unit grid and rewritten as short relative commands."""
    try:
        segs = _parse(d)
    except ValueError:
        return d
    q = lambda v: round(v * 10)
    out, st = [], {'cmd': '', 'tok': ''}
    cx = cy = sx = sy = 0.0           # exact current point / subpath start
    qx = qy = qsx = qsy = 0           # the same on the grid

    def emit(cmd, nums):
        if cmd != st['cmd'] or cmd in 'mMz':
            out.append(cmd)
            st['tok'] = cmd
        for v in nums:
            t, p = (v if isinstance(v, str) else _tenths(v)), st['tok']
            out.append(t if (p[-1].isalpha() or t[0] == '-' or (t[0] == '.' and '.' in p)) else ' ' + t)
            st['tok'] = t
        st['cmd'] = cmd

    for c, v in segs:
        rel, C = c.islower(), c.upper()
        ox, oy = (cx, cy) if rel else (0.0, 0.0)
        if C == 'Z':
            emit('z', [])
            cx, cy, qx, qy = sx, sy, qsx, qsy
            continue
        if C == 'H':
            pts = [(v[0] + ox, cy)]
        elif C == 'V':
            pts = [(cx, v[0] + oy)]
        elif C == 'A':
            pts = [(v[5] + ox, v[6] + oy)]
        else:
            pts = [(v[j] + ox, v[j + 1] + oy) for j in range(0, len(v), 2)]
        qp = [(q(x) - qx, q(y) - qy) for x, y in pts]
        if C == 'H':
            emit('h', [qp[0][0]])
        elif C == 'V':
            emit('v', [qp[0][1]])
        elif C == 'A':
            emit('a', [q(v[0]), q(v[1]), f'{v[2]:g}', str(int(v[3])), str(int(v[4])), *qp[0]])
        else:
            emit({'M': 'm' if out else 'M'}.get(C, C.lower()), [a for p in qp for a in p])
        cx, cy = pts[-1]
        qx, qy = q(cx), q(cy)
        if C == 'M':
            sx, sy, qsx, qsy = cx, cy, qx, qy
    return ''.join(out)


# ---------------------------------------------------------------- density = "compact"

def render_compact(opts, ctx):
    """Chips: [logo tile | NAME], four to a row (columns = 2..6 to change it), no bursts or numbers."""
    k = K.Kit(ctx.theme, ctx.mode)
    say = ctx.log if ctx.mode == 'light' else (lambda *a: None)
    icons = opts.get('icons') or []
    if isinstance(icons, str):
        icons = [i for i in re.split(r'[,\s]+', icons) if i]
    icons = [str(i).strip() for i in icons if str(i).strip()][:48]
    try:
        cols = int(opts.get('columns') or 0)
    except (TypeError, ValueError):
        cols = 0
    cols = max(2, min(6, cols)) if cols else 4

    idx = _index(ctx.root, say) if icons else {}
    logos = opts.get('logos') or {}
    logos = logos if isinstance(logos, dict) else {}
    items = [resolve(raw, ctx, idx, logos, say) for raw in icons]

    rows = max(1, math.ceil(len(items) / cols))
    inner = W - 2 * PAD
    cw = (inner - (cols - 1) * CHIP_GAP) / cols
    h = 2 * PAD + rows * CHIP_H + (rows - 1) * CHIP_GAP
    tile = CHIP_H - 16                         # the logo tile inside the chip
    chips = []
    for i, (title, d, box, _, rule) in enumerate(items):
        r, c = divmod(i, cols)
        x = PAD + c * (cw + CHIP_GAP)
        y = PAD + r * (CHIP_H + CHIP_GAP)
        tx, ty = x + 8, y + 8
        g = [f'<rect x="{n(x)}" y="{n(y)}" width="{n(cw)}" height="{CHIP_H}" rx="{K.R_PANEL}" fill="{k.paper}" '
             f'stroke="{k.ink}" stroke-width="{K.LINE}"/>',
             f'<rect x="{n(tx)}" y="{n(ty)}" width="{tile}" height="{tile}" rx="{K.R_LABEL + 2}" fill="url(#ht1)" '
             f'stroke="{k.ink}" stroke-width="{K.HAIR}"/>']
        if d:
            off = (tile - CHIP_LOGO) / 2
            tf, sc = logo_transform(tx + off, ty + off, CHIP_LOGO, box)
            path = compact_path(d) if box == (0, 0, 24, 24) else d
            fr = f' fill-rule="{rule}"' if rule else ''
            g.append(f'<path transform="{tf}" d="{path}" fill="{k.ink}"{fr} stroke="{k.paper}" '
                     f'stroke-width="{3 / sc:.2f}" stroke-linejoin="round" paint-order="stroke"/>')
        else:
            letter = next((ch for ch in title if ch.isalnum()), '?').upper()
            g.append(f'<text x="{n(tx + tile / 2)}" y="{n(ty + tile / 2 + 7)}" font-size="20" text-anchor="middle" '
                     f'class="kl" fill="{k.ink}" stroke="{k.paper}" stroke-width="3" paint-order="stroke">'
                     f'{K.esc(letter)}</text>')
        room = cw - tile - 8 - 12 - 10
        shown, size = fit_label(title, room, 14, 9)
        g.append(label_text(tx + tile + 12, y + CHIP_H / 2 + size * .36, shown, size, k.ink))
        chips.append(f'<g class="arrive a{min(i, 7)}">{"".join(g)}</g>')
    if not items:
        chips.append(f'<text x="{W / 2:g}" y="{h / 2 + 5:g}" font-size="14" text-anchor="middle" class="km" '
                     f'fill="{k.ink}">no tools listed yet</text>')
    names = [t[0] for t in items]
    title = 'Tech stack: ' + ', '.join(names) if names else 'Tech stack'
    svg = k.doc(W, h, k.card(0, 0, W, h) + ''.join(chips), title=title,
                desc=f'{len(items)} tools as small labelled chips: ' + ', '.join(names) + '.' if names else 'No tools listed yet.',
                css=k.css_arrive(delay_step=.05, count=8))
    if len(svg.encode()) > 25 * 1024:
        say(f'{len(svg.encode()) // 1024} KB, over the 25 KB budget; try fewer icons')
    return Out(svg=svg, alt=title)


# ---------------------------------------------------------------- density = "manga"
# A manga page: every row is filled edge to edge (no empty slots), and the panels in a row are
# split by slanted gutters. Logo first, the name small underneath.

MANGA_ROW = 92     # row height
MANGA_GUT = 10     # gutter between panels (and rows)
MANGA_SLANT = 9    # how far a gutter leans (px each side of the middle)
MANGA_LOGO = 40
MANGA_MAX = 6      # panels per row at most


def _row_counts(n_items, most):
    """Split n items into the fewest rows of at most `most`, as evenly as possible (7 -> 4+3)."""
    rows = max(1, math.ceil(n_items / most))
    base, extra = divmod(n_items, rows)
    return [base + (1 if r < extra else 0) for r in range(rows)]


def render_manga(opts, ctx):
    k = K.Kit(ctx.theme, ctx.mode)
    say = ctx.log if ctx.mode == 'light' else (lambda *a: None)
    icons = opts.get('icons') or []
    if isinstance(icons, str):
        icons = [i for i in re.split(r'[,\s]+', icons) if i]
    icons = [str(i).strip() for i in icons if str(i).strip()][:48]
    try:
        most = int(opts.get('columns') or 0)
    except (TypeError, ValueError):
        most = 0
    most = max(3, min(8, most)) if most else MANGA_MAX
    idx = _index(ctx.root, say) if icons else {}
    logos = opts.get('logos') or {}
    logos = logos if isinstance(logos, dict) else {}
    items = [resolve(raw, ctx, idx, logos, say) for raw in icons]

    counts = _row_counts(len(items), most) if items else [0]
    h = 2 * PAD + len(counts) * MANGA_ROW + (len(counts) - 1) * MANGA_GUT
    left, right = PAD, W - PAD
    rng = random.Random(ctx.seed)
    out, i = [], 0
    for r, m in enumerate(counts):
        top = PAD + r * (MANGA_ROW + MANGA_GUT)
        bot = top + MANGA_ROW
        lean = MANGA_SLANT if (r + rng.randrange(2)) % 2 else -MANGA_SLANT    # rows lean different ways
        tone = rng.randrange(m) if m > 2 else -1                              # one toned panel per row
        for j in range(m):
            title, d, box, _, rule = items[i]
            x0 = left + (right - left) * j / m
            x1 = left + (right - left) * (j + 1) / m
            # inner edges lean; the card's outer edges stay straight
            lt, lb = (x0, x0) if j == 0 else (x0 + lean + MANGA_GUT / 2, x0 - lean + MANGA_GUT / 2)
            rt, rb = (x1, x1) if j == m - 1 else (x1 + lean - MANGA_GUT / 2, x1 - lean - MANGA_GUT / 2)
            pts = f'{n(lt)},{n(top)} {n(rt)},{n(top)} {n(rb)},{n(bot)} {n(lb)},{n(bot)}'
            fill = 'url(#ht1)' if j == tone else k.paper
            cx = (lt + rt + lb + rb) / 4
            g = [f'<polygon points="{pts}" fill="{fill}" stroke="{k.ink}" stroke-width="{K.LINE}" '
                 f'stroke-linejoin="round"/>']
            ly = top + 12
            if d:
                # wide logos (wordmarks) may use up to twice the height in width
                bx, by, bw, bh = box
                sc = min(MANGA_LOGO * 2 / bw, MANGA_LOGO / bh)
                ox = cx - bw * sc / 2 - bx * sc
                oy = ly + (MANGA_LOGO - bh * sc) / 2 - by * sc
                tf = f'translate({n(ox)} {n(oy)}) scale({sc:.4f})'
                path = compact_path(d) if box == (0, 0, 24, 24) else d
                fr = f' fill-rule="{rule}"' if rule else ''
                g.append(f'<path transform="{tf}" d="{path}" fill="{k.ink}"{fr} stroke="{k.paper}" '
                         f'stroke-width="{4 / sc:.2f}" stroke-linejoin="round" paint-order="stroke"/>')
            else:
                word = re.sub(r'[^A-Za-z0-9]', '', title).upper()
                mono = word if 1 < len(word) <= 4 else (word[:1] or '?')
                fs = {1: 32, 2: 26, 3: 22, 4: 18}[len(mono)]
                g.append(f'<text x="{n(cx)}" y="{n(ly + MANGA_LOGO / 2 + fs * .36)}" font-size="{fs}" '
                         f'text-anchor="middle" class="kl" fill="{k.ink}" stroke="{k.paper}" stroke-width="4" '
                         f'paint-order="stroke">{K.esc(mono)}</text>')
            room = min(rt, rb) - max(lt, lb) - 14
            shown, size = fit_label(title, room, 11, 7.5)
            # a paper halo keeps the name readable on the toned panel
            g.append(label_text(cx, bot - 13, shown, size, k.ink, 'middle').replace(
                '<text ', f'<text stroke="{k.paper}" stroke-width="3.5" stroke-linejoin="round" paint-order="stroke" ', 1))
            out.append(f'<g class="arrive a{min(i, 7)}">{"".join(g)}</g>')
            i += 1
    if not items:
        out.append(f'<text x="{W / 2:g}" y="{h / 2 + 5:g}" font-size="14" text-anchor="middle" class="km" '
                   f'fill="{k.ink}">no tools listed yet</text>')
    names = [t[0] for t in items]
    title = 'Tech stack: ' + ', '.join(names) if names else 'Tech stack'
    svg = k.doc(W, h, k.card(0, 0, W, h) + ''.join(out), title=title,
                desc=(f'{len(items)} tools as comic panels split by slanted gutters: ' + ', '.join(names) + '.')
                if names else 'No tools listed yet.',
                css=k.css_arrive(delay_step=.04, count=8))
    if len(svg.encode()) > 25 * 1024:
        say(f'{len(svg.encode()) // 1024} KB, over the 25 KB budget; try fewer icons')
    return Out(svg=svg, alt=title)
