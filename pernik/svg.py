"""Small helpers every widget uses to write README-safe SVG.

The rules (GitHub shows README images through its camo proxy, inside <img>):
  - no scripts, no foreignObject, no external images or fonts: everything inline
  - animate with CSS @keyframes or SMIL only
  - things appear and disappear by scaling, not by fading opacity (fades look muddy on dark)

    from pernik.svg import doc, sticker, text_sticker, esc
    body = sticker('<rect x="10" y="10" width="200" height="60" rx="30" fill="#FF5FA2"/>', pal)
    svg = doc(900, 200, body, title='...', desc='...', css='...')
"""
from .text import esc, fit, width  # noqa: F401  (re-exported for widgets)


def doc(w, h, body, title, desc='', css='', pal=None, extra_defs=''):
    """A complete <svg> document with an accessible title/description and reduced-motion support."""
    font = f".r {{ font-family: {pal.font_round}; font-weight: 800; }} .b {{ font-family: {pal.font_body}; }}" if pal else ''
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}" '
        f'role="img" aria-labelledby="t d">'
        f'<title id="t">{esc(title)}</title><desc id="d">{esc(desc or title)}</desc>'
        f'<defs>{extra_defs}<style>{font} {css} '
        '@media (prefers-reduced-motion: reduce) { * { animation: none !important; } }'
        f'</style></defs>{body}</svg>\n'
    )


def shadow(markup, pal):
    """The ink shadow copy of a shape: same geometry, shifted, ink-coloured, see-through."""
    return (f'<g transform="translate({pal.shadow_dx:g} {pal.shadow_dy:g})" fill="{pal.shadow}" '
            f'stroke="{pal.shadow}" stroke-width="{pal.outline_w:g}" stroke-linejoin="round" '
            f'opacity="{pal.shadow_opacity:g}" class="shadow">{_strip_paint(markup)}</g>')


def sticker(markup, pal, outline=True):
    """Wrap shapes as a sticker: soft shadow underneath, then the shapes with a cream edge.

    Paint on the shapes (fill=...) is kept; the outline is added as a stroke on a group, so
    shapes that set their own stroke keep it."""
    edge = (f' stroke="{pal.outline}" stroke-width="{pal.outline_w:g}" stroke-linejoin="round" '
            'paint-order="stroke"') if outline else ''
    return f'{shadow(markup, pal)}<g{edge}>{markup}</g>'


def text_sticker(x, y, text, size, fill, pal, anchor='start', cls='r', extra=''):
    """Text with a cream outline and ink shadow, readable on both light and dark pages."""
    t = esc(text)
    base = f'x="{x:g}" y="{y:g}" font-size="{size:g}" text-anchor="{anchor}" class="{cls}" {extra}'
    return (
        f'<text {base} transform="translate({pal.shadow_dx:g} {pal.shadow_dy:g})" fill="{pal.shadow}" '
        f'stroke="{pal.shadow}" stroke-width="{pal.outline_w:g}" stroke-linejoin="round" '
        f'opacity="{pal.shadow_opacity:g}">{t}</text>'
        f'<text {base} fill="{fill}" stroke="{pal.outline}" stroke-width="{pal.outline_w:g}" '
        f'stroke-linejoin="round" paint-order="stroke">{t}</text>'
    )


def _strip_paint(markup):
    """Remove fill/stroke attributes so the shadow group's ink colour applies to everything."""
    import re
    return re.sub(r'\s(fill|stroke|stroke-width|paint-order)="[^"]*"', '', markup)
