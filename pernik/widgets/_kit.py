"""Small shared bits for the sticker widgets (hero, footer, stack, heading) and the mascots.

    from pernik.widgets._kit import swatch, ink_shadow, num, contrast, BOUNCE

The leading underscore keeps load_all() from treating this module as a widget.
"""
from types import SimpleNamespace

# the springy easing every bouncing thing uses
BOUNCE = 'cubic-bezier(.5,-0.4,.5,1.4)'


def swatch(pal):
    """The named sticker colours, with sensible fallbacks for themes that don't name them.

    Accents are assumed in the default order (orange, pink, yellow, mint, sky, grape)."""
    c = pal.color
    return SimpleNamespace(
        jeruk=c('jeruk', pal.accent(0)), pink=c('pink', pal.accent(1)), kuning=c('kuning', pal.accent(2)),
        mint=c('mint', pal.accent(3)), langit=c('langit', pal.accent(4)), anggur=c('anggur', pal.accent(5)),
        cream=c('cream', pal.outline), ink=c('ink', '#2B2340'),
    )


def ink_shadow(inner, pal):
    """Shadow copy of `inner` that keeps the stroke widths it sets (unlike svg.shadow)."""
    return (f'<g transform="translate({pal.shadow_dx:g} {pal.shadow_dy:g})" fill="{pal.shadow}" '
            f'stroke="{pal.shadow}" opacity="{pal.shadow_opacity:g}">{inner}</g>')


def num(v):
    """Short number: 128.0 -> '128', 117.25 -> '117.2'."""
    return f'{v:.1f}'.rstrip('0').rstrip('.')


def _lum(hexcol):
    h = hexcol.lstrip('#')
    if len(h) == 3:
        h = ''.join(ch * 2 for ch in h)
    out = []
    for i in (0, 2, 4):
        v = int(h[i:i + 2], 16) / 255
        out.append(v / 12.92 if v <= .03928 else ((v + .055) / 1.055) ** 2.4)
    r, g, b = out
    return .2126 * r + .7152 * g + .0722 * b


def contrast(a, b):
    """WCAG contrast ratio between two '#rrggbb' colours (1..21)."""
    la, lb = sorted((_lum(a), _lum(b)), reverse=True)
    return (la + .05) / (lb + .05)


def wide_chars(text):
    """How many characters are probably emoji/CJK (drawn ~1.25 em, not the table's .62)."""
    return sum(1 for ch in text if ord(ch) >= 0x2190 and ch not in '…’·')
