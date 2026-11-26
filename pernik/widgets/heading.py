"""heading: a small section title, a coloured pill sticker with outlined text."""
from ..svg import doc
from ..text import SLACK, esc, fit, width
from . import Out, widget
from ._kit import BOUNCE, contrast, num, swatch, wide_chars

W, H = 900, 76
FS = 28
PAD_X = 30                 # text-to-pill-edge room
MARGIN = 26                # pill-to-canvas edge room (outline, shadow, star)
STAR = 'M0-11Q2-2 11 0Q2 2 0 11Q-2 2-11 0Q-2-2 0-11Z'


@widget('heading', defaults={'number': 0, 'note': '', 'text': 'tech stack', 'color': 'pink', 'align': 'left'})
def heading(opts, ctx):
    """Section title on a coloured pill sticker.

    text   the title, e.g. "tech stack"
    color  a theme colour name (pink, mint, langit, ...) or "#rrggbb"
    align  "left", "center" or "right"
    """
    if ctx.pal.style == 'komik':
        from ._komik_heading import render; return render(opts, ctx)
    pal = ctx.pal
    s = swatch(pal)
    text = str(opts.get('text') or '').strip() or 'hello'
    fill = pal.color(str(opts.get('color') or 'pink'))
    align = str(opts.get('align') or 'left').lower()
    if align not in ('left', 'center', 'centre', 'right'):
        if ctx.mode == 'light':
            ctx.log(f'align "{align}" is not left/center/right; using left')
        align = 'left'

    def tw(t, size):
        return (width(t, size) + wide_chars(t) * .63 * size) * SLACK

    room = W - 2 * MARGIN - 2 * PAD_X - 30
    fs = fit(text, room, FS, 14)
    while tw(text, fs) > room and fs > 14:
        fs -= .5
    shown = text
    while tw(shown, fs) > room and len(shown) > 1:
        shown = shown[:-2].rstrip() + '…'
    pw = round(tw(shown, fs) + 2 * PAD_X)
    ph = 50
    if align == 'left':
        x0 = MARGIN
    elif align == 'right':
        x0 = W - MARGIN - pw - 8
    else:
        x0 = round((W - pw) / 2)
    cx, cy = x0 + pw / 2, H / 2 - 2

    # ink text with a cream edge on light pills; cream text on dark ones
    ink_on = contrast(fill, s.ink) >= contrast(fill, s.cream)
    tfill = s.ink if ink_on else s.cream
    tedge = (f' stroke="{pal.outline}" stroke-width="5" stroke-linejoin="round" paint-order="stroke"'
             if ink_on else '')

    pill = f'<rect x="{num(-pw / 2)}" y="{-ph / 2:g}" width="{pw}" height="{ph}" rx="{ph / 2:g}"/>'
    body = (
        f'<g transform="translate({num(cx)} {num(cy)}) rotate(-1.5)"><g class="hd">'
        f'<g transform="translate({pal.shadow_dx:g} {pal.shadow_dy:g})" fill="{pal.shadow}" stroke="{pal.shadow}" '
        f'stroke-width="{pal.outline_w:g}" opacity="{pal.shadow_opacity:g}">{pill}</g>'
        f'<g fill="{fill}" stroke="{pal.outline}" stroke-width="{pal.outline_w:g}">{pill}</g>'
        # a little shine along the top
        f'<path d="M{num(-pw / 2 + 18)} -16H{num(-pw / 2 + 40)}" stroke="{s.cream}" stroke-opacity=".6" stroke-width="4" '
        'stroke-linecap="round"/>'
        f'<text class="r" x="1.5" y="{num(.35 * fs + 2)}" font-size="{num(fs)}" text-anchor="middle" fill="{s.ink}" '
        f'opacity=".3"{tedge.replace(pal.outline, s.ink)}>{esc(shown)}</text>'
        f'<text class="r" x="0" y="{num(.35 * fs)}" font-size="{num(fs)}" text-anchor="middle" fill="{tfill}"{tedge}>'
        f'{esc(shown)}</text></g></g>'
        # a twinkling star sticker on the pill's corner
        f'<g transform="translate({num(x0 + pw - 4)} {num(cy - ph / 2 + 4)})"><g class="tw">'
        f'<path d="{STAR}" fill="{pal.outline}" stroke="{pal.outline}" stroke-width="8" stroke-linejoin="round"/>'
        f'<path d="{STAR}" fill="{s.kuning if fill != s.kuning else s.pink}"/></g></g>'
    )
    css = (f".hd{{animation:hd 2.8s {BOUNCE} infinite}}"
           "@keyframes hd{0%,100%{transform:translateY(0) rotate(0)}50%{transform:translateY(-2px) rotate(1deg)}}"
           ".tw{animation:tw 2.4s ease-in-out infinite alternate}"
           "@keyframes tw{0%{transform:scale(.7) rotate(0)}100%{transform:scale(1.1) rotate(40deg)}}")
    svg = doc(W, H, body, title=text, desc=f'Section heading "{text}" on a coloured sticker pill.', css=css, pal=pal)
    return Out(svg=svg, alt=text)
