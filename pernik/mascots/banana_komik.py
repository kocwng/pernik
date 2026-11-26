"""The banana in the komik style: two-tone line art (ink lines, spot/tint fills, halftone shade).

    from pernik.mascots.banana_komik import draw_banana
    svg, css = draw_banana(k, x=716, y=264, beat=1.17, chords=chords)

(x, y) is the banana's foot; the drawing reaches about 160 px left (the ukulele head), 70 px
right, 212 px up and 24 px down at scale 1. Line weights stay 2.5 / 1.5 at any scale. One
loop: the strumming arm swings on the beat and the body bobs with it; with a chord timeline
the fretting hand slides to each chord. This is not a registered mascot (the sticker
'banana' is): the komik hero calls it directly.
"""
import math

from ..komik import HAIR, LINE

UX, UY, UR = 33, -27, 20      # ukulele waist in banana coordinates, angle (neck up to the left)
NUT, HEAD = -156, -186
REST = '0003'
UC, US = math.cos(math.radians(UR)), math.sin(math.radians(UR))
FRETS = [NUT] + [-141, -128, -116, -105, -95, -86, -78, -71, -65]

BODY = 'M0 0C58-26 66-128 14-176Q2-186-10-176C-17-128-26-50-14-8Q-8 2 0 0Z'
SHADE = 'M0 0C58-26 66-128 14-176C38-132 40-46 0 0Z'           # the outer (right) side
STEM = 'M-1-176Q-2-192-13-201Q-17-205-13-209Q-9-212-5-208Q8-195 8-177Z'
UKE = ('M-10-24C-2-24 6-40 22-40A40 40 0 0 1 22 40C6 40-2 24-10 24'
       'C-18 24-22 31-30 31A31 31 0 0 1-30-31C-22-31-18-24-10-24Z')


def _n(v):
    return f'{v:.1f}'.rstrip('0').rstrip('.')


def u2b(x, y):
    """ukulele-local point -> banana coordinates"""
    return UX + x * UC - y * US, UY + x * US + y * UC


def fret_pos(shape):
    fr = [int(c) for c in shape if c.isdigit() and c != '0']
    p = sum(fr) / len(fr) if fr else 1
    i = max(1, min(int(p), 8))
    return FRETS[i - 1] + (FRETS[i] - FRETS[i - 1]) * (p - i + .5)


def string_pos(shape):
    ix = [j for j, c in enumerate(shape) if c.isdigit() and c != '0']
    return sum(ix) / len(ix) if ix else 1.5


def draw_banana(k, x, y, scale=1.0, beat=1.17, chords=None, pid='bk'):
    """Return (svg_group, css). `pid` prefixes ids and classes (two bananas in one file stay apart)."""
    ink, spot, paper, tint = k.ink, k.spot, k.paper, k.tint
    lw, hw = _n(LINE / scale), _n(HAIR / scale)     # keep the printed line weights at any scale
    seq = chords.seq if chords else []
    shapes = chords.shapes if chords else {}
    out, css = [], []
    add = out.append
    stroke = f'stroke="{ink}" stroke-width="{lw}" stroke-linejoin="round" stroke-linecap="round"'

    add(f'<g transform="translate({_n(x)} {_n(y)}) scale({_n(scale)})"><g class="{pid}b">')
    # ---------------------------------------------------------------- body
    add(f'<clipPath id="{pid}c"><path d="{BODY}"/></clipPath>')
    add(f'<path d="{STEM}" fill="{ink}" {stroke}/>')
    add(f'<path d="{BODY}" fill="{paper}"/>')
    add(f'<g clip-path="url(#{pid}c)"><path d="{SHADE}" fill="url(#ht2)"/>'
        f'<ellipse cx="-5" cy="0" rx="9" ry="6" fill="{ink}"/></g>')
    add(f'<path d="M-7-150C-12-118-14-82-10-52" fill="none" stroke="{ink}" stroke-width="{hw}" stroke-linecap="round"/>')
    add(f'<path d="{BODY}" fill="none" {stroke}/>')
    # face: ink eyes with a paper glint, spot cheeks, a small smile
    add(f'<circle cx="5" cy="-118" r="5" fill="{ink}"/><circle cx="31" cy="-118" r="5" fill="{ink}"/>'
        f'<circle cx="6.8" cy="-120" r="1.8" fill="{paper}"/><circle cx="32.8" cy="-120" r="1.8" fill="{paper}"/>'
        f'<ellipse cx="-4" cy="-105" rx="6.5" ry="4" fill="{spot}"/><ellipse cx="40" cy="-105" rx="6.5" ry="4" fill="{spot}"/>'
        f'<path d="M12-108Q18-101 24-108" fill="none" {stroke}/>')

    # ---------------------------------------------------------------- ukulele (local x axis, waist at 0,0)
    strings = ''.join(f'M{NUT} {s}H29' for s in (-5.5, -2, 2, 5.5))
    add(f'<g transform="translate({UX} {UY}) rotate({UR})">'
        f'<path d="{UKE}" fill="{spot}" {stroke}/>'
        f'<path d="M30-30A32 32 0 0 1 50 6" fill="none" stroke="{paper}" stroke-width="{lw}" stroke-linecap="round"/>'
        f'<rect x="{NUT}" y="-8" width="{-48 - NUT}" height="16" rx="2" fill="{ink}" {stroke}/>'
        f'<rect x="{HEAD}" y="-11" width="{NUT - HEAD + 2}" height="22" rx="6" fill="{tint}" {stroke}/>'
        + ''.join(f'<circle cx="{px}" cy="{py}" r="3.5" fill="{paper}" {stroke}/>' for px in (-164, -178) for py in (-14, 14))
        + f'<circle cx="-30" cy="0" r="11" fill="{ink}"/>'
        f'<rect x="23" y="-14" width="10" height="28" rx="2" fill="{ink}"/>'
        f'<path class="{pid}s" d="{strings}" stroke="{paper}" stroke-width="{hw}"/>'
        f'<path d="{"".join(f"M{fx} -8v16" for fx in FRETS[1:6])}" stroke="{spot}" stroke-width="{hw}"/>'
        '</g>')

    # ---------------------------------------------------------------- arms (an ink tube: 10 ink under 5 paper)
    def arm(sx, sy, d, hx, hy, cls, extra=''):
        return (f'<g transform="translate({sx} {sy})"><g class="{cls}">'
                f'<path d="{d}" fill="none" stroke="{ink}" stroke-width="{_n((5 + 2 * LINE) / scale)}" stroke-linecap="round"/>'
                f'<path d="{d}" fill="none" stroke="{paper}" stroke-width="{_n(5 / scale)}" stroke-linecap="round"/>'
                f'{extra}<circle cx="{hx:.1f}" cy="{hy:.1f}" r="6" fill="{paper}" {stroke}/></g></g>')

    shape0 = shapes.get(seq[0][0], REST) if seq else REST
    base, sbase = fret_pos(shape0), string_pos(shape0)
    lsx, lsy, rsx, rsy = -18, -84, 48, -84
    fx, fy = u2b(base, -6)
    fx, fy = fx - lsx, fy - lsy
    add(arm(lsx, lsy, f'M0 0C{fx * .3:.1f} 14 {fx * .72:.1f} {fy + 14:.1f} {fx:.1f} {fy:.1f}', fx, fy, f'{pid}f'))
    px, py = u2b(-40, 6)
    pick = f'<path d="M{px - rsx:.1f} {py - rsy:.1f}l-5-9h10z" fill="{spot}" {stroke}/>'
    hx, hy = u2b(-40, -1)
    hx, hy = hx - rsx, hy - rsy
    ex, ey = 10, hy * .9
    add(arm(rsx, rsy, f'M0 0C14 8 {ex + 12:.1f} {ey - 14:.1f} {ex:.1f} {ey:.1f}S{hx * .55:.1f} {hy + 4:.1f} {hx:.1f} {hy:.1f}',
            hx, hy, f'{pid}m', pick))
    add('</g></g>')

    # ---------------------------------------------------------------- motion: one loop, the strum
    css.append(
        f".{pid}b{{animation:{pid}b {beat:g}s ease-out infinite}}"
        f"@keyframes {pid}b{{0%,100%{{transform:none}}18%{{transform:translateY(2px)}}45%{{transform:translateY(-1px)}}}}"
        f".{pid}m{{animation:{pid}m {beat:g}s infinite}}"
        f"@keyframes {pid}m{{0%,6%{{transform:rotate(10deg);animation-timing-function:ease-in}}"
        f"24%,48%{{transform:rotate(-11deg);animation-timing-function:ease-in}}66%,100%{{transform:rotate(10deg)}}}}")
    if seq:
        t0, loop = seq[0][1], seq[-1][2] - seq[0][1]
        kf = []
        for c, t, e in seq:
            shape = shapes.get(c, shape0)
            off = (fret_pos(shape) - base) * .75
            cross = (string_pos(shape) - sbase) * 2.5
            v = f'translate({off * UC - cross * US:.1f}px,{off * US + cross * UC:.1f}px)'
            for tt in (t, max(t, e - .25)):
                kf.append(f'{(tt - t0) / loop * 100:.2f}%{{transform:{v}}}')
        kf.append('100%{transform:none}')
        css.append(f".{pid}f{{animation:{pid}f {loop:.2f}s ease-in-out infinite}}@keyframes {pid}f{{{''.join(kf)}}}")
    return ''.join(out), ''.join(css)
