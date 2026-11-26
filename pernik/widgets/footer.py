"""footer: a wavy rainbow ribbon with a cream pill of text in the middle."""
from ..svg import doc
from ..text import SLACK, esc, fit, width
from . import Out, widget
from ._kit import BOUNCE, num, swatch

W, H = 900, 100
FS, PAD = 20, 46          # text size; text-to-pill-edge room (half the pill height + 23)
HW_MIN, HW_MAX = 60, 360  # half pill width: keeps rainbow (40..860) showing left and right + room for stars
X_A, X_B, MID, AMP = 40, 860, 50, 9
STEP = 41                 # a quarter wavelength
STAR = 'M0-1Q.2-.2 1 0Q.2 .2 0 1Q-.2 .2-1 0Q-.2-.2 0-1Z'


def wave(phase):
    """The ribbon's centre line as smooth cubic segments; phase 0..3 shifts it a quarter wave."""
    ys = [MID, MID + AMP, MID, MID - AMP]
    nodes = [(X_A + i * STEP, ys[(i - phase) % 4]) for i in range((X_B - X_A) // STEP + 1)]
    h = STEP / 3

    def slope(i):   # tangent height over h at a node: 0 at a crest, +-AMP/2 at a crossing
        y = nodes[i][1]
        if y != MID:
            return 0
        prev = nodes[i - 1][1] if i else MID * 2 - nodes[i + 1][1]
        nxt = nodes[i + 1][1] if i + 1 < len(nodes) else MID * 2 - prev
        return (AMP * .52) if nxt > prev else -(AMP * .52)

    d = f'M{nodes[0][0]} {nodes[0][1]}'
    for i in range(1, len(nodes)):
        (x0, y0), (x1, y1) = nodes[i - 1], nodes[i]
        d += f'C{num(x0 + h)} {num(y0 + slope(i - 1))} {num(x1 - h)} {num(y1 - slope(i))} {x1} {y1}'
    return d


@widget('footer', defaults={'text': 'thanks for stopping by!'})
def footer(opts, ctx):
    """Wavy rainbow ribbon with a cream pill of text (text = "thanks for stopping by!")."""
    if ctx.pal.style == 'komik':
        from ._komik_footer import render; return render(opts, ctx)
    pal = ctx.pal
    s = swatch(pal)
    text = str(opts.get('text') or '').strip() or 'thanks for stopping by!'

    room = 2 * (HW_MAX - PAD)
    fs = fit(text, room, FS, 12)
    shown = text
    while width(shown, fs) * SLACK > room and len(shown) > 1:
        shown = shown[:-2].rstrip() + '…'
    hw = max(HW_MIN, min(HW_MAX, round(width(shown, fs) * SLACK / 2 + PAD)))

    frames = [wave(p) for p in (0, 1, 2, 3, 0)]
    path = (f'<path id="w" d="{frames[0]}" fill="none" stroke-linecap="round">'
            f'<animate attributeName="d" dur="4s" repeatCount="indefinite" values="{";".join(frames)}"/></path>')
    stripes = [s.pink, s.jeruk, s.kuning, s.mint, s.langit]
    sw = 7.1
    body = [f'<use href="#w" transform="translate({pal.shadow_dx:g} {pal.shadow_dy:g})" stroke="{pal.shadow}" '
            f'stroke-width="42.5" opacity="{pal.shadow_opacity:g}"/>',
            f'<use href="#w" stroke="{pal.outline}" stroke-width="42.5"/>']
    for i, col in enumerate(stripes):
        body.append(f'<use href="#w" transform="translate(0 {num((i - 2) * 6.5)})" stroke="{col}" stroke-width="{sw}"/>')

    # the pill
    body.append(
        f'<g transform="translate({W // 2} {MID})"><g class="bob">'
        f'<rect x="-{hw}" y="-23" width="{2 * hw}" height="46" rx="23" transform="translate({pal.shadow_dx:g} {pal.shadow_dy:g})" '
        f'fill="{pal.shadow}" stroke="{pal.shadow}" stroke-width="6" opacity="{pal.shadow_opacity:g}"/>'
        f'<rect x="-{hw}" y="-23" width="{2 * hw}" height="46" rx="23" fill="{s.cream}" stroke="{pal.outline}" stroke-width="6"/>'
        f'<rect x="-{hw - 5}" y="-18" width="{2 * hw - 10}" height="36" rx="18" fill="none" stroke="{s.pink}" '
        'stroke-width="2.5" stroke-dasharray="7 6" stroke-linecap="round"/>'
        f'<text class="t" x="0" y="{num(round(.35 * fs, 1))}" font-size="{num(fs)}" fill="{s.ink}" '
        f'text-anchor="middle">{esc(shown)}</text></g></g>')

    # little stars either side of the pill
    stars = [(W // 2 - hw - 29, 20, 13, s.kuning, 0), (W // 2 + hw + 31, 80, 11, s.kuning, .7),
             (W // 2 + hw + 19, 18, 8, s.pink, 1.2), (W // 2 - hw - 15, 84, 8, s.langit, .4)]
    for x, y, sc, col, dl in stars:
        w = num(3 / sc)
        body.append(
            f'<g transform="translate({x} {y})"><g class="sp" style="animation-delay:{dl:g}s">'
            f'<path d="{STAR}" transform="translate(2.5 3) scale({sc})" fill="{pal.shadow}" stroke="{pal.shadow}" '
            f'stroke-width="{w}" stroke-linejoin="round" opacity="{pal.shadow_opacity:g}"/>'
            f'<path d="{STAR}" transform="scale({sc})" fill="{col}" stroke="{pal.outline}" stroke-width="{w}" '
            'stroke-linejoin="round"/></g></g>')

    css = (f".t{{font-family:{pal.font_round};font-weight:800}}"
           f".bob{{animation:bob 2.6s {BOUNCE} infinite}}"
           "@keyframes bob{0%,100%{transform:translateY(0) rotate(-1.5deg)}50%{transform:translateY(-3px) rotate(1.5deg)}}"
           f".sp{{transform-origin:0 0;animation:sp 1.8s {BOUNCE} infinite}}"
           "@keyframes sp{0%,100%{transform:translateY(4px) scale(.75) rotate(0)}50%{transform:translateY(-6px) scale(1.1) rotate(25deg)}}")
    svg = doc(W, H, ''.join(body), title=text, desc=f'A wavy rainbow ribbon with a cream label saying "{text}".',
              css=css, extra_defs=path)
    return Out(svg=svg, alt=text)
