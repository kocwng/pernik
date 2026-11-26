"""hero: a big wavy sticker greeting (1-2 lines) with an optional mascot on the right."""
import os

from ..mascots import draw, load_chords
from ..svg import doc
from ..text import ADV, DEFAULT_ADV, esc
from . import Out, widget
from ._kit import BOUNCE, ink_shadow, num, swatch

W, H = 900, 300
TRACK = .05
FS_MAX = 90                  # full size (the original "hello there!" title)
FS_MIN = 24
X0, INDENT = 40, 52          # line 1 starts at x=40, line 2 is indented 52 px (at full size)
MID = 139.6                  # vertical middle of the letters' cap height
WAVE = 3.0


def em(text):
    return sum(ADV.get(c, DEFAULT_ADV) + TRACK for c in text)


@widget('hero', defaults={'greeting': ['hello', 'there!'], 'mascot': 'banana', 'chords': '', 'beat': 1.17})
def hero(opts, ctx):
    """Big colourful greeting (1-2 lines, shrinks to fit) with an optional mascot.

    greeting  one or two short lines, e.g. ["hello", "there!"]
    mascot    "banana" (strums a ukulele) or "none"
    chords    optional path to a chords.json; the banana's chord card and fretting follow it
    beat      seconds per strum when there is no chords.json (default 1.17)
    """
    pal = ctx.pal
    s = swatch(pal)
    say = ctx.log if ctx.mode == 'light' else (lambda *a: None)   # warn once, not per mode

    greeting = opts.get('greeting') or ['hello!']
    if isinstance(greeting, str):
        greeting = [greeting]
    greeting = [str(g).strip() for g in greeting if str(g).strip()] or ['hello!']
    if len(greeting) > 2:
        say(f'greeting has {len(greeting)} lines; only the first two fit')
        greeting = greeting[:2]

    # ---------------------------------------------------------------- mascot (+ chords)
    try:
        beat = float(opts.get('beat') or 1.17)
    except (TypeError, ValueError):
        beat = 1.17
    beat = min(3.0, max(.3, beat))
    name = str(opts.get('mascot') or 'none').strip().lower()
    m = None
    if name not in ('none', 'off', 'false', ''):
        chords = None
        path = str(opts.get('chords') or '').strip()
        if path:
            full = path if os.path.isabs(path) else os.path.join(ctx.root, path)
            try:
                chords = load_chords(full)
                beat = chords.beat or beat
            except ValueError as e:
                say(f'no chord card ({path}: {e}); the {name} just strums')
        m = draw(name, pal, beat, chords)
    right = m.title_right if m else W - X0

    # ---------------------------------------------------------------- title
    def size_for(lines):
        fs = FS_MAX
        for i, text in enumerate(lines):
            ind = INDENT / FS_MAX if i else 0          # the indent shrinks with the letters
            fs = min(fs, int((right - X0) / (em(text) + ind)))
        return max(fs, FS_MIN)

    fs = size_for(greeting)
    if len(greeting) == 1 and fs < 56 and ' ' in greeting[0]:
        # one long line: break it at the space that gives the biggest letters
        words = greeting[0].split()
        best = max(([' '.join(words[:j]), ' '.join(words[j:])] for j in range(1, len(words))), key=size_for)
        if size_for(best) > fs:
            greeting, fs = best, size_for(best)
    k = fs / FS_MAX
    if len(greeting) == 1:
        bases = [round(MID + .36 * fs)]
    else:
        gap = 88 * k
        b1 = round(MID - (gap - .72 * fs) / 2)
        bases = [b1, b1 + round(gap)]
    starts = [X0 + (round(INDENT * k) if i else 0) for i in range(len(greeting))]
    if not m:
        # no mascot: centre the block in the whole width
        block = max(st - X0 + em(t) * fs for st, t in zip(starts, greeting))
        shift = round((W - block) / 2 - X0)
        starts = [st + shift for st in starts]
    palettes = ([s.jeruk, s.pink, s.anggur, s.langit, s.mint], [s.mint, s.jeruk, s.pink, s.anggur, s.langit, s.pink])

    def cap_i(cx, base):
        """A serifed I: in sans fonts 'I' and 'l' are twins, so names with an 'I' could read as 'l'."""
        ch, bw, sw, bh = .72 * fs, 13.5 * k, 6.5 * k, 10.5 * k
        t = base - ch
        return (f'M{num(cx - bw)} {num(t)}H{num(cx + bw)}V{num(t + bh)}H{num(cx + sw)}V{num(base - bh)}H{num(cx + bw)}V{base}'
                f'H{num(cx - bw)}V{num(base - bh)}H{num(cx - sw)}V{num(t + bh)}H{num(cx - bw)}Z')

    out, css = [], []
    add = out.append
    n = 0
    boxes = []                   # title boxes (x0, y0, x1, y1); confetti that would overlap is dropped
    add('<g class="ttl">')
    for i, text in enumerate(greeting):
        x, base, cols = starts[i], bases[i], palettes[i]
        for j, ch in enumerate(text):
            col = cols[j % len(cols)]
            w = (ADV.get(ch, DEFAULT_ADV) + TRACK) * fs
            cx = x + w / 2
            x += w
            if ch == ' ':
                continue
            tilt = (-4, 3, -2, 4, -3)[n % 5]
            rot = f'transform="rotate({tilt} {cx:.0f} {base})"'
            delay = f'animation-delay:{n * .11:.2f}s'
            if ch == 'I':
                d = cap_i(cx, base)
                sw = num(5 * k)                            # the bar's own rounding, outline on top
                sh = f'<path d="{d}" {rot} stroke-width="{num(6 + 5 * k)}" stroke-linejoin="round"/>'
                fg = (f'<path d="{d}" {rot} fill="{pal.outline}" stroke="{pal.outline}" stroke-width="{num(6 + 5 * k)}" '
                      f'stroke-linejoin="round"/>'
                      f'<path d="{d}" {rot} fill="{col}" stroke="{col}" stroke-width="{sw}" stroke-linejoin="round"/>')
                add(f'<g class="wv" style="{delay}">{ink_shadow(sh, pal)}{fg}</g>')
            else:
                glyph = f'<text x="{cx:.0f}" y="{base}" {rot}>{esc(ch)}</text>'
                add(f'<g class="wv" style="{delay}">{ink_shadow(glyph, pal)}<g fill="{col}" stroke="{pal.outline}">{glyph}</g></g>')
            n += 1
        # letter height + wave jump (13 px) above, descenders (g, y, p) below
        boxes.append((starts[i], base - .74 * fs - 14, x, base + .22 * fs))
    add('</g>')
    css.append(
        f".ttl text{{font-family:{pal.font_round};font-weight:800;font-size:{fs}px;text-anchor:middle;"
        "stroke-width:6;stroke-linejoin:round;paint-order:stroke}"
        f".wv{{animation:wave {WAVE}s {BOUNCE} infinite both;transform-box:fill-box;transform-origin:50% 85%}}"
        "@keyframes wave{0%,40%,100%{transform:translateY(0) rotate(0)}"
        "12%{transform:translateY(-13px) rotate(-6deg)}24%{transform:translateY(2px) rotate(4deg)}32%{transform:translateY(0) rotate(-1deg)}}")

    # ---------------------------------------------------------------- confetti
    defs = ['<path id="spk" d="M0-11Q2-2 11 0Q2 2 0 11Q-2 2-11 0Q-2-2 0-11Z"/>',
            '<path id="sqg" d="M-14 0q3.5-7 7 0t7 0t7 0t7 0" fill="none"/>']
    confetti = [  # (kind, x, y, colour, scale, duration, delay)
        ('spk', 22, 40, s.kuning, 1.0, 2.6, 0), ('dot', 22, 160, s.langit, 4.5, 2.6, -1.6),
        ('sqg', 338, 34, s.pink, .9, 3.6, -1.4), ('dot', 440, 64, s.pink, 6, 3.4, -1),
        ('sqg', 478, 128, s.langit, 1, 3.0, -.5), ('spk', 520, 238, s.mint, .8, 2.2, -1.2),
        ('dot', 574, 66, s.mint, 5, 3.0, -2), ('spk', 876, 34, s.anggur, .85, 2.8, -.6),
        ('dot', 882, 200, s.kuning, 6, 3.2, -.3),
    ]
    if not m:   # the right-hand side is empty: mirror a few pieces there
        confetti += [('sqg', 700, 52, s.mint, .9, 3.2, -.8), ('dot', 760, 250, s.pink, 5, 3.0, -1.3),
                     ('spk', 640, 262, s.langit, .8, 2.4, -.4)]
    reach = {'dot': lambda sc: sc + 8, 'spk': lambda sc: 13 * sc + 4, 'sqg': lambda sc: 16 * sc + 4}

    def hits(kind, x, y, sc):
        r = reach[kind](sc)
        return any(x + r > x0 and x - r < x1 and y + r > y0 and y - r < y1 for x0, y0, x1, y1 in boxes)

    edge = pal.outline
    add('<g class="cf">')
    for kind, x, y, col, sc, dur, dl in confetti:
        if hits(kind, x, y, sc):
            continue
        anim = f'animation-duration:{dur}s;animation-delay:{dl}s'
        if kind == 'dot':
            add(f'<g transform="translate({x} {y})"><g class="dr" style="{anim}">'
                f'<circle r="{sc}" fill="{col}" stroke="{edge}" stroke-width="7" paint-order="stroke"/></g></g>')
        elif kind == 'spk':
            add(f'<g transform="translate({x} {y}) scale({sc})"><g class="tw" style="{anim}">'
                f'<use href="#spk" fill="{edge}" stroke="{edge}" stroke-width="8" stroke-linejoin="round"/>'
                f'<use href="#spk" fill="{col}"/></g></g>')
        else:
            add(f'<g transform="translate({x} {y}) scale({sc})"><g class="wg" style="{anim}">'
                f'<use href="#sqg" stroke="{edge}" stroke-width="10" stroke-linecap="round"/>'
                f'<use href="#sqg" stroke="{col}" stroke-width="4.5" stroke-linecap="round"/></g></g>')
    add('</g>')
    css.append(
        ".dr{animation:dr 3s ease-in-out infinite alternate}@keyframes dr{0%{transform:translate(0,0)}100%{transform:translate(4px,-9px)}}"
        ".tw{animation:tw 2.6s ease-in-out infinite alternate}@keyframes tw{0%{transform:scale(.75) rotate(0)}100%{transform:scale(1.15) rotate(45deg)}}"
        ".wg{animation:wg 3s ease-in-out infinite alternate}@keyframes wg{0%{transform:rotate(-12deg) translateY(0)}100%{transform:rotate(10deg) translateY(-6px)}}")

    if m:
        out.append(m.svg)
        css.append(m.css)
        defs.append(m.defs)

    title = ' '.join(greeting)
    desc = f'Colourful sticker letters saying "{title}"' + (f'; {m.desc}.' if m else '.')
    svg = doc(W, H, ''.join(out), title=title, desc=desc, css=''.join(css), extra_defs=''.join(defs))
    alt = title + (f' ({m.desc.replace("on the right ", "")})' if m else '')
    if len(svg.encode()) > 25 * 1024:
        say(f'{len(svg.encode()) // 1024} KB, over the 25 KB budget (a shorter chords.json helps)')
    return Out(svg=svg, alt=alt)
