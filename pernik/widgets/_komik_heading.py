"""heading in the komik style: a chapter strip. Rules: docs/design.md

    ┌──────────────────────────────────────────────────────────────────┐
    │█ ② TECH STACK ◤ ──────────────────────────────────── since 2019 │
    └──────────────────────────────────────────────────────────────────┘

A solid ink label block (label font, uppercase) with an optional numbered badge (the
chapter number), then a hairline rule that leads the eye to an optional mono caption.
The rule draws in once; nothing loops. Also holds two small helpers the other komik
widgets share (label_width, n).
"""
from .. import komik as K
from ..text import esc
from . import Out

W, H = 900, 56
TEXT = 20          # label size; long titles shrink to MIN_TEXT, then get cut with "…"
MIN_TEXT = 14
NOTE = 14          # mono caption size (7 px on a phone: the smallest we allow)
SLANT = 12         # the block's cut end leans this far, like a manga chapter tab

# Advance widths (em) of Arial Black capitals, the first face in the label stack. Using
# them with textLength keeps a title exactly as wide as we planned in any fallback font.
_ADV = {**dict.fromkeys('ABCDKRVXY', .778), **dict.fromkeys('EPSTZ', .722), **dict.fromkeys('FJL', .667),
        **dict.fromkeys('GHNOQU', .833), 'I': .389, 'M': .944, 'W': 1.0, ' ': .333,
        **dict.fromkeys('0123456789', .667), '.': .333, ',': .333, '-': .333, '+': .66, '#': .66,
        '&': .889, '/': .278, ':': .333, '!': .333, '?': .611, "'": .278, '(': .389, ')': .389}
TRACK = .04        # the .kl class adds this much letter spacing


def label_width(text, size):
    """Width in px of `text` set in the label face (uppercase, tracked)."""
    return sum(_ADV.get(c, .8) + TRACK for c in str(text).upper()) * size


def fit_label(text, max_w, size, low):
    """(text, size) that fits max_w: shrink to `low`, then cut the end with an ellipsis."""
    text = str(text)
    while label_width(text, size) > max_w and size > low:
        size -= .5
    while label_width(text, size) > max_w and len(text) > 1:
        text = text[:-2].rstrip() + '…'
    return text, size


def label_text(x, y, text, size, fill, anchor='start'):
    """Label-face text pinned to the width we laid out (textLength), so fallbacks can't overflow."""
    tl = label_width(text, size) - TRACK * size     # the last letter's tracking is outside the ink
    return (f'<text x="{n(x)}" y="{n(y)}" font-size="{n(size)}" text-anchor="{anchor}" class="kl" '
            f'fill="{fill}" textLength="{n(tl)}" lengthAdjust="spacing">{esc(str(text).upper())}</text>')


def n(v):
    """Short number for SVG: 12.0 -> '12', 12.25 -> '12.2'."""
    s = f'{v:.1f}'
    s = s[:-2] if s.endswith('.0') else s
    return '0' if s == '-0' else s


def flag(v, default=True):
    if isinstance(v, bool):
        return v
    if v in (None, ''):
        return default
    return str(v).strip().lower() not in ('false', 'no', '0', 'off')


def render(opts, ctx):
    k = K.Kit(ctx.theme)
    say = ctx.log if ctx.mode == 'light' else (lambda *a: None)
    text = str(opts.get('text') or '').strip() or 'hello'
    note = str(opts.get('note') or '').strip()
    align = str(opts.get('align') or 'left').strip().lower()
    align = {'centre': 'center', 'middle': 'center', 'start': 'left', 'end': 'right'}.get(align, align)
    if align not in ('left', 'center', 'right'):
        say(f'align "{align}" is not left/center/right; using left')
        align = 'left'
    num = opts.get('number')
    try:
        num = int(num) if num not in (None, '', False) else None
    except (TypeError, ValueError):
        say(f'number "{num}" is not a whole number; leaving the badge out')
        num = None
    if num is not None and not 0 <= num <= 99:
        say(f'number {num} is outside 0-99; leaving the badge out')
        num = None

    # geometry: paper margin 0..4, ink frame 4..8, so the inside starts at 8 (ends at 892 / 48)
    x0, x1, cy = 8, 892, H / 2
    badge_r = 12
    pad = 16
    lead = (badge_r * 2 + 10) if num is not None else 0      # badge + gap before the title
    note_w = K.mono_width(note, NOTE) if note else 0
    # the block may take at most ~60% of the strip (less when a caption needs room)
    max_text = (x1 - x0) * .62 - 2 * pad - lead - SLANT - (note_w if align == 'center' else 0)
    shown, size = fit_label(text, max_text, TEXT, MIN_TEXT)
    if shown != text:
        say(f'title "{text}" is too long for one strip; it is cut to "{shown}"')
    tw = label_width(shown, size) - TRACK * size
    bw = round(pad + lead + tw + pad + SLANT)                 # block width incl. the slanted end

    # block position and its slanted edge(s)
    if align == 'left':
        bx = x0
        block = f'M0 0H{n(bx + bw)}L{n(bx + bw - SLANT)} {H}H0Z'
        content_x = bx + pad
    elif align == 'right':
        bx = x1 - bw
        block = f'M{n(bx + SLANT)} 0H{W}V{H}H{n(bx)}Z'
        content_x = bx + SLANT + pad
    else:
        bw += SLANT
        bx = round((W - bw) / 2)
        block = f'M{n(bx + SLANT)} 0H{n(bx + bw)}L{n(bx + bw - SLANT)} {H}H{n(bx)}Z'
        content_x = bx + SLANT + pad
    # the print shadow of the block: a spot sliver 4 px behind its cut end(s)
    sliver = ''
    if align in ('left', 'center'):
        e = bx + bw
        sliver += f'M{n(e)} 0h6L{n(e - SLANT + 6)} {H}h-6Z'
    if align in ('right', 'center'):
        sliver += f'M{n(bx + SLANT)} 0h-6L{n(bx - 6)} {H}h6Z'

    parts = []
    tx = content_x
    if num is not None:
        bcx = content_x + badge_r
        parts.append(f'<circle cx="{n(bcx)}" cy="{n(cy)}" r="{badge_r}" fill="{k.spot}"/>'
                     f'<text x="{n(bcx)}" y="{n(cy + 5)}" font-size="{14 if num < 10 else 12}" '
                     f'text-anchor="middle" class="kl" fill="{k.ink}">{num}</text>')
        tx = content_x + lead
    parts.append(label_text(tx, cy + size * .36, shown, size, k.paper))
    title = ''.join(parts)

    # rule(s) and caption, kept 16 px clear of the block and the frame
    gap = 16
    rules, cap = [], ''
    if align == 'left':
        r0, r1 = bx + bw + gap, x1 - pad
        if note:
            cap = k.mono(x1 - pad, cy + NOTE * .34, note, NOTE, 'end')
            r1 -= note_w + gap
        rules.append((r0, r1))
    elif align == 'right':
        r0, r1 = x0 + pad, bx - gap
        if note:
            cap = k.mono(x0 + pad, cy + NOTE * .34, note, NOTE, 'start')
            r0 += note_w + gap
        rules.append((r1, r0))            # draws away from the block, like the others
    else:
        rules.append((bx - gap, x0 + pad))
        r1 = x1 - pad
        if note:
            cap = k.mono(x1 - pad, cy + NOTE * .34, note, NOTE, 'end')
            r1 -= note_w + gap
        rules.append((bx + bw + gap, r1))
    rule_svg = ''.join(
        f'<path class="dr" d="M{n(a)} {n(cy)}H{n(b)}" pathLength="1"/>' for a, b in rules if abs(b - a) >= 24)

    clip = (f'<defs><clipPath id="hc"><rect x="6" y="6" width="888" height="{H - 12}" rx="{K.R_PANEL}"/>'
            '</clipPath></defs>')
    body = (k.card(0, 0, W, H) + clip
            + f'<g clip-path="url(#hc)"><path d="{sliver}" fill="{k.spot}"/><path d="{block}" fill="{k.ink}"/></g>'
            + f'<g class="arrive">{title}</g>'
            + f'<g fill="none" stroke="{k.ink}" stroke-width="{K.HAIR}" stroke-linecap="round">{rule_svg}</g>'
            + cap
            # the frame again on top, so the block meets it cleanly
            + f'<rect x="6" y="6" width="888" height="{H - 12}" rx="{K.R_PANEL}" fill="none" '
              f'stroke="{k.ink}" stroke-width="{K.FRAME}"/>')
    css = (k.css_arrive(count=1)
           + '.dr{stroke-dasharray:1 1;animation:dr .7s cubic-bezier(.45,0,.3,1) .25s both}'
             '@keyframes dr{from{stroke-dashoffset:1}to{stroke-dashoffset:0}}')
    chapter = f'chapter {num}: ' if num is not None else ''
    desc = f'Section heading: {chapter}{text}' + (f' ({note})' if note else '') + '.'
    svg = k.doc(W, H, body, title=f'{chapter}{text}', desc=desc, css=css)
    return Out(svg=svg, alt=f'{chapter}{text}', same=True)
