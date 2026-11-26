"""Drawing kit for the "komik" style (two-colour risograph comic page). Rules: docs/design.md

    from pernik import komik as K
    k = K.Kit(ctx.theme, ctx.mode)          # colours + fonts from the theme's [komik] table
    body = k.card(0, 0, 900, 240)           # paper card with ink frame and paper margin
    body += k.panel(24, 24, 400, 192, fill=k.tint)
    body += k.label(24, 24, 160, 32, 'tech stack')
    body += k.badge(400, 40, 1)
    svg = k.doc(900, 240, body, title='...', desc='...', css=k.css_arrive())

All numbers are pixels on the 8-px grid. Line weights are only k.FRAME / k.LINE / k.HAIR.
Build the kit per mode, K.Kit(ctx.theme, ctx.mode): dark mode is a night print with its own colours.
"""
import math
import random

from .text import esc, fit, width

FRAME, LINE, HAIR = 4, 2.5, 1.5
R_PANEL, R_LABEL = 6, 2
MARGIN = 4            # paper margin outside the ink frame (separates the card on dark pages)

# Average glyph widths (em) for the label font (Arial Black, uppercase) and mono.
LABEL_ADV = 0.78
MONO_ADV = 0.6


class Kit:
    def __init__(self, theme, mode='light'):
        """Colours for one of GitHub's themes. [komik] holds the light values; [komik.dark]
        overrides them for dark mode (a night print: dark paper, light lines)."""
        raw = theme.raw
        base = {k: v for k, v in raw.get('komik', {}).items() if not isinstance(v, dict)}
        c = dict(base, **raw.get('komik', {}).get(mode, {})) if mode != 'light' else base
        self.mode = mode
        self.paper = c.get('paper', '#FAF3F8')
        self.ink = c.get('ink', '#1C1520')
        self.spot = c.get('spot', '#E0569B')
        self.tint = c.get('tint', '#F4BCD8')
        self.shade = c.get('shade', self.ink)     # the print shadow behind display type
        self.solid = c.get('solid', self.ink)     # solid blocks: label bars, filled badges, tabs
        self.on_solid = c.get('on_solid', self.paper)
        f = raw.get('font', {})
        self.f_display = f.get('display', "'Arial Rounded MT Bold', 'Nunito', sans-serif")
        self.f_label = f.get('label', "'Arial Black', Arial, sans-serif")
        self.f_mono = f.get('mono', 'ui-monospace, Menlo, monospace')
        self.FRAME, self.LINE, self.HAIR = FRAME, LINE, HAIR

    # ------------------------------------------------------------------ document
    def doc(self, w, h, body, title, desc='', css=''):
        """Full SVG with halftone patterns and the three type classes (.kd display, .kl label, .km mono)."""
        style = (
            f".kd{{font-family:{self.f_display};font-weight:800}}"
            f".kl{{font-family:{self.f_label};font-weight:900;text-transform:uppercase;letter-spacing:.04em}}"
            f".km{{font-family:{self.f_mono};font-weight:600}}"
            f"{css}"
            "@media (prefers-reduced-motion: reduce){*{animation:none!important}}"
        )
        return (
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}" '
            f'role="img" aria-labelledby="t d"><title id="t">{esc(title)}</title>'
            f'<desc id="d">{esc(desc or title)}</desc><defs>{self.patterns()}<style>{style}</style></defs>'
            f'{body}</svg>\n'
        )

    def patterns(self):
        """Halftones: ht1 (fine, light), ht2 (medium), ht3 (coarse, dark) in spot; hti in ink; hatch."""
        def dots(pid, step, r, color):
            return (f'<pattern id="{pid}" width="{step}" height="{step}" patternUnits="userSpaceOnUse" '
                    f'patternTransform="rotate(45)"><circle cx="{step / 2:g}" cy="{step / 2:g}" r="{r:g}" fill="{color}"/></pattern>')
        return (dots('ht1', 6, 1.1, self.spot) + dots('ht2', 6, 1.9, self.spot) + dots('ht3', 6, 2.6, self.spot)
                + dots('hti', 5, 1.0, self.ink)
                + f'<pattern id="hatch" width="6" height="6" patternUnits="userSpaceOnUse" patternTransform="rotate(45)">'
                  f'<line x1="0" y1="0" x2="0" y2="6" stroke="{self.ink}" stroke-width="{HAIR}"/></pattern>')

    # ------------------------------------------------------------------ boxes
    def card(self, x, y, w, h, r=R_PANEL, fill=None):
        """The printed card every widget sits on: a MARGIN-wide paper edge, paper fill, ink frame.

        The card insets itself by MARGIN so the paper edge stays inside the box you give it
        (on GitHub dark that edge is what separates the ink frame from the dark page)."""
        fill = fill or self.paper
        x, y, w, h = x + MARGIN, y + MARGIN, w - 2 * MARGIN, h - 2 * MARGIN
        geo = f'x="{x + FRAME / 2:g}" y="{y + FRAME / 2:g}" width="{w - FRAME:g}" height="{h - FRAME:g}" rx="{r}"'
        return (f'<rect {geo} fill="{fill}" stroke="{self.paper}" stroke-width="{FRAME + 2 * MARGIN:g}"/>'
                f'<rect {geo} fill="none" stroke="{self.ink}" stroke-width="{FRAME}"/>')

    def panel(self, x, y, w, h, fill=None, r=R_PANEL, weight=FRAME, extra=''):
        """A comic panel: a box with an ink border. fill may be a colour or 'url(#ht2)'."""
        fill = fill or self.paper
        return (f'<rect x="{x:g}" y="{y:g}" width="{w:g}" height="{h:g}" rx="{r}" fill="{fill}" '
                f'stroke="{self.ink}" stroke-width="{weight}" stroke-linejoin="round" {extra}/>')

    def label(self, x, y, w, h, text, align='middle', size=None, inverse=False, upper=True):
        """A solid ink bar with paper text (like a panel title). inverse=True: paper bar, ink text.
        upper=False keeps the text's case (chord names like 'Em')."""
        bg, fg = (self.paper, self.ink) if inverse else (self.solid, self.on_solid)
        size = size or min(h * 0.56, fit_label(text, w - 24, h * 0.56))
        tx = {'start': x + 12, 'middle': x + w / 2, 'end': x + w - 12}[align]
        keep = '' if upper else ' style="text-transform:none"'
        return (f'<rect x="{x:g}" y="{y:g}" width="{w:g}" height="{h:g}" rx="{R_LABEL}" fill="{bg}" '
                f'stroke="{self.ink}" stroke-width="{LINE}"/>'
                f'<text x="{tx:g}" y="{y + h / 2 + size * 0.36:g}" font-size="{size:g}" text-anchor="{align}" '
                f'class="kl" fill="{fg}"{keep}>{esc(text)}</text>')

    # ------------------------------------------------------------------ type
    def display(self, x, y, text, size, anchor='start', fill=None, shadow=4):
        """The one big word: spot fill, ink outline, ink print-shadow offset (shadow, shadow)."""
        fill = fill or self.spot
        t = esc(text)
        sw = max(LINE, size * 0.06)
        base = f'x="{x:g}" y="{y:g}" font-size="{size:g}" text-anchor="{anchor}" class="kd"'
        return (f'<text {base} transform="translate({shadow} {shadow})" fill="{self.shade}" stroke="{self.shade}" '
                f'stroke-width="{sw:g}" stroke-linejoin="round">{t}</text>'
                f'<text {base} fill="{fill}" stroke="{self.ink}" stroke-width="{sw:g}" stroke-linejoin="round" '
                f'paint-order="stroke">{t}</text>')

    def mono(self, x, y, text, size=13, anchor='start', fill=None):
        return (f'<text x="{x:g}" y="{y:g}" font-size="{size:g}" text-anchor="{anchor}" class="km" '
                f'fill="{fill or self.ink}">{esc(text)}</text>')

    def circled(self, x, y, text, d=28, gap=8):
        """A tagline in circled letters (spaces become gaps), at most 12 letters. Returns (svg, total_width)."""
        out, cx, n = [], x + d / 2, 0
        for ch in text.upper():
            if ch != ' ':
                n += 1
                if n > 12:
                    break
            if ch == ' ':
                cx += d / 2
                continue
            out.append(f'<circle cx="{cx:g}" cy="{y:g}" r="{d / 2 - LINE / 2:g}" fill="{self.paper}" '
                       f'stroke="{self.ink}" stroke-width="{LINE}"/>'
                       f'<text x="{cx:g}" y="{y + d * 0.19:g}" font-size="{d * 0.52:g}" text-anchor="middle" '
                       f'class="kl" fill="{self.ink}">{esc(ch)}</text>')
            cx += d + gap
        return ''.join(out), cx - gap - d / 2 - x

    # ------------------------------------------------------------------ UI bits
    def badge(self, cx, cy, n, r=14, filled=False):
        """A numbered circle (order that means something)."""
        bg, fg = (self.solid, self.on_solid) if filled else (self.paper, self.ink)
        return (f'<circle cx="{cx:g}" cy="{cy:g}" r="{r:g}" fill="{bg}" stroke="{self.ink}" stroke-width="{LINE}"/>'
                f'<text x="{cx:g}" y="{cy + r * 0.38:g}" font-size="{r * 1.1:g}" text-anchor="middle" class="kl" '
                f'fill="{fg}">{esc(n)}</text>')

    def heart(self, cx, cy, s=12, full=True):
        p = (f'M{cx:g} {cy + s * .9:g} C{cx - s * 1.3:g} {cy:g} {cx - s * .9:g} {cy - s * .9:g} {cx:g} {cy - s * .25:g} '
             f'C{cx + s * .9:g} {cy - s * .9:g} {cx + s * 1.3:g} {cy:g} {cx:g} {cy + s * .9:g}Z')
        return f'<path d="{p}" fill="{self.spot if full else self.paper}" stroke="{self.ink}" stroke-width="{LINE}" stroke-linejoin="round"/>'

    def hearts(self, x, cy, full, total, s=12, gap=8):
        """A row of hearts, `full` of `total` filled. Only for a real value."""
        step = s * 2 + gap
        return ''.join(self.heart(x + s + i * step, cy, s, i < full) for i in range(total))

    def bar(self, x, y, w, h, frac, label='EXP', size=None):
        """A progress bar with a mono label tab: [EXP|██████░░░]. Label at least 14 px."""
        size = size or max(14, h * 0.55)
        lw = len(label) * size * MONO_ADV + 24
        frac = max(0.0, min(1.0, frac))
        inner = w - lw - 8
        return (f'<rect x="{x:g}" y="{y:g}" width="{w:g}" height="{h:g}" rx="{h / 2:g}" fill="{self.paper}" '
                f'stroke="{self.ink}" stroke-width="{LINE}"/>'
                f'<rect x="{x:g}" y="{y:g}" width="{lw:g}" height="{h:g}" rx="{h / 2:g}" fill="{self.solid}"/>'
                f'<text x="{x + lw / 2:g}" y="{y + h / 2 + size * 0.36:g}" font-size="{size:g}" text-anchor="middle" '
                f'class="km" fill="{self.on_solid}">{esc(label)}</text>'
                f'<rect x="{x + lw + 4:g}" y="{y + 4:g}" width="{max(0, inner * frac):g}" height="{h - 8:g}" '
                f'rx="{(h - 8) / 2:g}" fill="url(#ht3)"/>')

    def ff_button(self, x, y, s=40):
        """The ▶▶ 'next' button. Only where there is a next thing."""
        a = s * .22
        tri = lambda ox: f'M{x + ox:g} {y + s / 2 - a:g} L{x + ox + a * 1.2:g} {y + s / 2:g} L{x + ox:g} {y + s / 2 + a:g}Z'
        return (f'<rect x="{x:g}" y="{y:g}" width="{s:g}" height="{s:g}" rx="{R_PANEL}" fill="{self.tint}" '
                f'stroke="{self.ink}" stroke-width="{LINE}"/>'
                f'<path d="{tri(s * .2)}{tri(s * .2 + a * 1.25)}" fill="{self.ink}"/>')

    # ------------------------------------------------------------------ effects
    def burst(self, cx, cy, r1, r2, points=16, fill=None, seed=1):
        """A jagged starburst (behind the hero object of a panel)."""
        rnd = random.Random(seed)
        pts = []
        for i in range(points * 2):
            a = math.pi * i / points
            r = (r2 if i % 2 == 0 else r1) * (1 + rnd.uniform(-.06, .06))
            pts.append(f'{cx + r * math.cos(a):.1f},{cy + r * math.sin(a):.1f}')
        return (f'<polygon points="{" ".join(pts)}" fill="{fill or "url(#ht2)"}" stroke="{self.ink}" '
                f'stroke-width="{HAIR}" stroke-linejoin="round"/>')

    def speed_lines(self, cx, cy, r1, r2, n=24, seed=1, clip=None):
        """Radial manga speed lines between radii r1 and r2. One set per panel at most."""
        rnd = random.Random(seed)
        d = []
        for i in range(n):
            a = 2 * math.pi * i / n + rnd.uniform(-.08, .08)
            ra = r1 * rnd.uniform(1, 1.25)
            d.append(f'M{cx + ra * math.cos(a):.1f} {cy + ra * math.sin(a):.1f}L{cx + r2 * math.cos(a):.1f} {cy + r2 * math.sin(a):.1f}')
        cp = f' clip-path="url(#{clip})"' if clip else ''
        return f'<path d="{"".join(d)}" stroke="{self.ink}" stroke-width="{HAIR}" stroke-linecap="round" fill="none"{cp}/>'

    def kamboja(self, cx, cy, s=10, rot=0):
        """A frangipani (kamboja) flower: five overlapping petals, spot with ink line. Our falling-petal accent."""
        petals = ''.join(
            f'<ellipse cx="0" cy="{-s * .55:g}" rx="{s * .38:g}" ry="{s * .6:g}" transform="rotate({i * 72 + 18})"/>'
            for i in range(5))
        return (f'<g transform="translate({cx:g} {cy:g}) rotate({rot:g})" fill="{self.tint}" stroke="{self.ink}" '
                f'stroke-width="{HAIR}">{petals}<circle r="{s * .22:g}" fill="{self.spot}"/></g>')

    def petals(self, box, n, seed, s=9, cls='petal'):
        """Up to 7 kamboja scattered in box=(x, y, w, h), seeded. Each in a <g class> for animation."""
        rnd = random.Random(seed)
        x, y, w, h = box
        out = []
        for i in range(min(n, 7)):
            out.append(f'<g class="{cls} {cls}{i}">{self.kamboja(x + rnd.uniform(0, w), y + rnd.uniform(0, h), s * rnd.uniform(.8, 1.2), rnd.uniform(0, 72))}</g>')
        return ''.join(out)

    # ------------------------------------------------------------------ motion
    @staticmethod
    def css_arrive(selector='.arrive', delay_step=.08, count=8):
        """Things stamp in once: scale 1.04 -> 1 with a quick settle. Add class arrive a0..a7."""
        rules = ''.join(f'{selector}.a{i}{{animation-delay:{i * delay_step:.2f}s}}' for i in range(count))
        return ('@keyframes stamp{0%{transform:scale(.9)}70%{transform:scale(1.03)}100%{transform:scale(1)}}'
                f'{selector}{{transform-box:fill-box;transform-origin:center;animation:stamp .35s cubic-bezier(.3,1.4,.5,1) both}}'
                + rules)


def fit_label(text, max_w, size):
    """Font size for the label face (Arial Black uppercase is wide)."""
    w = len(text) * LABEL_ADV * size * 1.04
    return size if w <= max_w else max(8, int(size * max_w / w * 2) / 2)


def mono_width(text, size):
    return len(text) * MONO_ADV * size


__all__ = ['Kit', 'FRAME', 'LINE', 'HAIR', 'fit_label', 'mono_width', 'width', 'fit', 'esc']
