"""footer in the komik style: the caption bar at the bottom of a manga page.

    [ NAME ]<"thanks for stopping by!"                    *>  [>>]

An ink name label, a paper speech box with the footer text in mono quotes and a small
kamboja, and a >> button only when there is somewhere to go (`link`).

Options:
    text   "thanks for stopping by!"
    name   the label; default "@" + your GitHub username
    link   optional URL; adds the >> button and makes the picture a link
"""
from .. import komik as K
from . import Out

W, H = 900, 96
X0, X1 = 24, 876
BY, BH = 24, 48               # every element in the row: y 24..72
FS = 18                       # mono caption size
LABEL_FS = 18


def render(opts, ctx):
    k = K.Kit(ctx.theme)
    text = ' '.join(str(opts.get('text') or '').split()) or 'thanks for stopping by!'
    name = ' '.join(str(opts.get('name') or '').split()) or (f'@{ctx.user}' if ctx.user else '')
    link = str(opts.get('link') or '').strip() or None

    body = [k.card(0, 0, W, H)]
    add = body.append
    x = X0
    if name:
        name = name[:24]
        fs = K.fit_label(name, 260, LABEL_FS)
        lw = int((len(name) * K.LABEL_ADV * fs * 1.04 + 32 + 7) // 8 * 8)
        add(f'<g class="arrive a0">{k.label(x, BY, lw, BH, name, size=fs)}</g>')
        x += lw + 16
    right = X1 - (BH + 16 if link else 0)

    # speech box with a tail pointing at the name
    bw = right - x
    room = bw - 32 - 32                    # text padding + the kamboja
    shown = text
    fs = FS
    while K.mono_width(f'"{shown}"', fs) > room and fs > 12:
        fs -= 1
    while K.mono_width(f'"{shown}"', fs) > room and len(shown) > 1:
        shown = shown[:-2].rstrip() + '…'
    mid = BY + BH / 2
    add('<g class="arrive a1">')
    add(k.panel(x, BY, bw, BH, weight=K.LINE))
    if name:   # the tail: a paper wedge over the box's left border, outlined on its two outer sides
        add(f'<path d="M{x + 4:g} {mid - 8:g}H{x:g}L{x - 10:g} {mid:g}L{x:g} {mid + 8:g}H{x + 4:g}Z" fill="{k.paper}"/>'
            f'<path d="M{x:g} {mid - 8:g}L{x - 10:g} {mid:g}L{x:g} {mid + 8:g}" fill="none" stroke="{k.ink}" '
            f'stroke-width="{K.LINE}" stroke-linejoin="round" stroke-linecap="round"/>')
    add(k.mono(x + 16, mid + fs * .36, f'"{shown}"', fs))
    add(k.kamboja(right - 24, mid, 9, 20))
    add('</g>')
    if link:
        add(f'<g class="arrive a2">{k.ff_button(X1 - BH, BY, BH)}</g>')

    desc = f'A comic caption bar: {name + " says " if name else ""}"{text}"' + (', with a next button' if link else '') + '.'
    svg = k.doc(W, H, ''.join(body), title=text, desc=desc, css=k.css_arrive())
    return Out(svg=svg, alt=text, href=link, same=True)
