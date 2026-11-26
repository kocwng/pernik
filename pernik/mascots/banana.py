"""The banana mascot: a smiling banana strumming a ukulele, with music notes floating up.

With a Chords timeline its fretting hand slides along the neck and a speech-bubble card
shows the chord being played (about the first 40 seconds, looping, real durations).
Without one it just strums at `beat` seconds per strum.
"""
import math

from ..text import esc, fit
from ..widgets._kit import ink_shadow, num, swatch
from . import Drawn, mascot

BX, BY, SC = 724, 246, 1.06  # banana's foot (hidden by the ukulele body) and scale
UX, UY, UR = 33, -27, 20     # ukulele waist in banana coordinates, angle (neck up to the left)
NUT, HEAD = -160, -194
FRETS = [-145, -131, -118, -106, -95, -85, -76, -68, -61]
FRET_X = [NUT] + FRETS
REST = '0003'                # hand position with no chords (or an unknown shape)
UC, US = math.cos(math.radians(UR)), math.sin(math.radians(UR))
ROUND = "'Arial Rounded MT Bold','Nunito','Varela Round','Trebuchet MS','Segoe UI',sans-serif"


def u2b(x, y):
    """ukulele-local point -> banana coordinates"""
    return UX + x * UC - y * US, UY + x * US + y * UC


def fret_pos(shape):
    fr = [int(c) for c in shape if c.isdigit() and c != '0']
    p = sum(fr) / len(fr) if fr else 1
    i = max(1, min(int(p), 8))
    return FRET_X[i - 1] + (FRET_X[i] - FRET_X[i - 1]) * (p - i + .5)


def string_pos(shape):
    """mean index of the fretted strings (0=G .. 3=A), for a small shift across the neck"""
    ix = [k for k, c in enumerate(shape) if c.isdigit() and c != '0']
    return sum(ix) / len(ix) if ix else 1.5


@mascot('banana')
def banana(pal, beat, chords=None):
    s = swatch(pal)
    edge = pal.outline
    seq = chords.seq if chords else []
    shapes = chords.shapes if chords else {}
    has = bool(seq)
    if has:
        t0, loop = seq[0][1], seq[-1][2] - seq[0][1]

        def pct(t):
            return f'{(t - t0) / loop * 100:.3f}'.rstrip('0').rstrip('.') + '%'

    css, defs, out = [], [], []
    add = out.append

    # ------------------------------------------------------------ body
    body = 'M0 0C58-26 66-128 14-176Q2-186-10-176C-17-128-26-50-14-8Q-8 2 0 0Z'
    defs.append(f'<path id="bd" d="{body}"/>')
    defs.append('<clipPath id="bdc"><use href="#bd"/></clipPath>')
    stem = 'M3-178Q2-196-10-206'
    add(f'<g transform="translate({BX} {BY}) scale({SC})"><g class="sq">')
    add(ink_shadow(f'<use href="#bd" stroke-width="10"/><path d="{stem}" fill="none" stroke-width="20" '
                   'stroke-linecap="round"/>', pal))
    add(f'<path d="{stem}" fill="none" stroke="{edge}" stroke-width="20" stroke-linecap="round"/>')
    add(f'<use href="#bd" fill="{s.kuning}" stroke="{edge}" stroke-width="10" paint-order="stroke"/>')
    # mint stem with a cream glint (a dark stem reads as a stray music note on the dark theme)
    add(f'<path d="{stem}" fill="none" stroke="{s.mint}" stroke-width="10" stroke-linecap="round"/>'
        f'<path d="M1-184Q0-194-7-201" fill="none" stroke="{s.cream}" stroke-opacity=".6" stroke-width="2.6" '
        'stroke-linecap="round"/>')
    add(f'<g clip-path="url(#bdc)">'
        f'<path d="M14-6C56-36 58-128 20-170" fill="none" stroke="{s.jeruk}" stroke-opacity=".35" stroke-width="12"/>'
        f'<ellipse cx="-4" cy="-2" rx="12" ry="9" fill="{s.ink}" fill-opacity=".7"/>'
        f'<ellipse cx="6" cy="-180" rx="12" ry="7" fill="{s.mint}" fill-opacity=".75"/></g>')
    add(f'<path d="M-8-150C-13-118-15-82-11-52" fill="none" stroke="{s.cream}" stroke-opacity=".8" stroke-width="5" '
        'stroke-linecap="round"/>')
    add(f'<g class="eye"><circle cx="4" cy="-118" r="4.6" fill="{s.ink}"/><circle cx="30" cy="-118" r="4.6" fill="{s.ink}"/>'
        f'<circle cx="5.6" cy="-119.6" r="1.6" fill="{s.cream}"/><circle cx="31.6" cy="-119.6" r="1.6" fill="{s.cream}"/></g>'
        f'<ellipse cx="-5" cy="-106" rx="6.5" ry="4" fill="{s.pink}" opacity=".85"/>'
        f'<ellipse cx="39" cy="-106" rx="6.5" ry="4" fill="{s.pink}" opacity=".85"/>'
        f'<path d="M11-109Q17-101 23-109" fill="none" stroke="{s.ink}" stroke-width="2.8" stroke-linecap="round"/>')

    # ------------------------------------------------------------ ukulele (local x axis, waist at 0,0)
    uke_body = ('M-10-24C-2-24 6-40 22-40A40 40 0 0 1 22 40C6 40-2 24-10 24'
                'C-18 24-22 31-30 31A31 31 0 0 1-30-31C-22-31-18-24-10-24Z')
    pegs = ''.join(f'<circle cx="{x}" cy="{y}" r="4.6"/>' for x in (-170, -185) for y in (-14, 14))
    uke_parts = (f'<path d="{uke_body}"/><rect x="{NUT - 2}" y="-8" width="{-50 - (NUT - 2)}" height="16" rx="4"/>'
                 f'<rect x="{HEAD}" y="-11" width="{NUT - HEAD + 4}" height="22" rx="8"/>{pegs}')
    add(f'<g transform="translate({UX} {UY}) rotate({UR})">')
    add(ink_shadow(f'<g stroke-width="10" stroke-linejoin="round">{uke_parts}</g>', pal))
    add(f'<g fill="{edge}" stroke="{edge}" stroke-width="10" stroke-linejoin="round">{uke_parts}</g>')
    add(f'<g fill="{s.jeruk}">{uke_parts}</g><g fill="{s.kuning}">{pegs}</g>')
    add(f'<path d="M30-33A33 33 0 0 1 52 2" fill="none" stroke="{s.cream}" stroke-opacity=".7" stroke-width="4" stroke-linecap="round"/>'
        f'<path d="M-50-14A22 22 0 0 1-36-25" fill="none" stroke="{s.cream}" stroke-opacity=".7" stroke-width="3.5" stroke-linecap="round"/>'
        f'<rect x="{NUT}" y="-6.5" width="{NUT * -1 - 44}" height="13" rx="2" fill="{s.ink}" fill-opacity=".8"/>'
        f'<path d="{"".join(f"M{x} -6.5v13" for x in FRETS)}" stroke="{s.cream}" stroke-opacity=".55" stroke-width="1.3"/>'
        f'<circle cx="-100" cy="0" r="1.8" fill="{s.cream}" fill-opacity=".8"/>'
        f'<rect x="{NUT - 2}" y="-7" width="4" height="14" rx="1.5" fill="{s.cream}"/>'
        f'<circle cx="-30" cy="0" r="13.5" fill="{s.kuning}"/><circle cx="-30" cy="0" r="10.5" fill="{s.ink}" fill-opacity=".85"/>'
        f'<rect x="24" y="-15" width="10" height="30" rx="4" fill="{s.ink}" fill-opacity=".75"/>'
        f'<path d="M29-11v22" stroke="{s.cream}" stroke-width="2" stroke-linecap="round"/>'
        f'<path d="M{HEAD + 8} 0h{NUT - HEAD - 12}" stroke="{s.ink}" stroke-opacity=".35" stroke-width="4" stroke-linecap="round"/>')
    strings = ''.join(f'M{NUT} {y}H29' for y in (-4.5, -1.5, 1.5, 4.5))
    add(f'<path class="str" d="{strings}" stroke="{s.cream}" stroke-width="1.3"/>')
    add('</g>')

    def arm(sx, sy, d, hx, hy, cls, extra=''):
        """soft banana arm: path d (relative to the shoulder) ending in a round hand at (hx, hy)"""
        return (f'<g transform="translate({sx} {sy})"><g class="{cls}">'
                f'<path d="{d}" fill="none" stroke="{edge}" stroke-width="20" stroke-linecap="round" stroke-linejoin="round"/>{extra}'
                f'<path d="{d}" fill="none" stroke="{s.kuning}" stroke-width="10" stroke-linecap="round" stroke-linejoin="round"/>'
                f'<circle cx="{hx:.1f}" cy="{hy:.1f}" r="7.5" fill="{s.kuning}" stroke="{edge}" stroke-width="10" paint-order="stroke"/>'
                f'</g></g>')

    shape0 = shapes.get(seq[0][0], REST) if has else REST
    base, sbase = fret_pos(shape0), string_pos(shape0)
    lsx, lsy, rsx, rsy = -19, -86, 49, -86
    # left arm (holds the chord): a soft curve that sags a little
    fx, fy = u2b(base, -5)
    fx, fy = fx - lsx, fy - lsy
    add(arm(lsx, lsy, f'M0 0C{fx * .3:.1f} 15 {fx * .72:.1f} {fy + 15:.1f} {fx:.1f} {fy:.1f}', fx, fy, 'fh'))
    # right arm strums at the end of the fretboard, holding a pick
    px, py = u2b(-40, 6)
    pick = (f'<path d="M{px - rsx:.1f} {py - rsy:.1f}l-4-8h9z" fill="{s.pink}" stroke="{edge}" '
            'stroke-width="5" stroke-linejoin="round" paint-order="stroke"/>')
    hx, hy = u2b(-40, -1)
    hx, hy = hx - rsx, hy - rsy
    ex, ey = 9, hy * .9                                  # elbow
    add(arm(rsx, rsy, f'M0 0C14 8 {ex + 12:.1f} {ey - 14:.1f} {ex:.1f} {ey:.1f}'
                      f'S{hx * .55:.1f} {hy + 4:.1f} {hx:.1f} {hy:.1f}', hx, hy, 'st', pick))
    add('</g></g>')

    if has:
        kf = []
        for c, t, e in seq:
            shape = shapes.get(c, shape0)
            off = (fret_pos(shape) - base) * .75
            cross = (string_pos(shape) - sbase) * 2.5
            v = f'translate({off * UC - cross * US:.1f}px,{off * US + cross * UC:.1f}px)'
            kf.append(f'{pct(t)}{{transform:{v}}}')
            kf.append(f'{pct(max(t, e - .25))}{{transform:{v}}}')
        kf.append('100%{transform:none}')
        css.append(f".fh{{animation:fh {loop:.2f}s ease-in-out infinite}}@keyframes fh{{{''.join(kf)}}}")
    css.append(
        f".sq{{animation:sq {beat:g}s ease-out infinite}}"
        "@keyframes sq{0%,100%{transform:none}15%{transform:translateY(2px) scale(1.035,.96)}"
        "36%{transform:translateY(-2px) scale(.985,1.025)}57%{transform:translateY(1px) scale(1.015,.98)}78%{transform:none}}"
        ".eye{animation:blink 3.2s infinite;transform-box:fill-box;transform-origin:50% 50%}"
        "@keyframes blink{0%,46%,50%,100%{transform:scaleY(1)}48%{transform:scaleY(.1)}}"
        f".st{{animation:st {beat:g}s infinite}}"
        "@keyframes st{0%,6%{transform:rotate(11deg);animation-timing-function:ease-in}24%,48%{transform:rotate(-12deg);"
        "animation-timing-function:ease-in}66%,100%{transform:rotate(11deg)}}"
        f".str{{animation:vb {beat:g}s linear infinite}}"
        "@keyframes vb{0%,14%,56%{stroke-width:1.3;stroke-opacity:1}17%,59%{stroke-width:2.6;stroke-opacity:.7}"
        "21%,63%{stroke-width:1.1;stroke-opacity:1}25%,67%{stroke-width:2;stroke-opacity:.8}32%,74%,100%{stroke-width:1.3;stroke-opacity:1}}")

    # ------------------------------------------------------------ chord card (speech bubble)
    if has:
        cx, cy, cw, cht = 646, 14, 92, 106
        sx = [-19.5, -6.5, 6.5, 19.5]     # strings G C E A
        ny, fs = 56, 11                    # nut line + fret spacing
        card = (f'<rect x="{-cw / 2}" y="0" width="{cw}" height="{cht}" rx="16"/>'
                f'<path d="M{cw / 2 - 6} 58L{cw / 2 + 20} 80L{cw / 2 - 6} 78Z"/>')
        add(f'<g transform="translate({cx} {cy}) rotate(-4 0 {cht / 2})"><g class="cd">')
        add(ink_shadow(f'<g stroke-width="12" stroke-linejoin="round">{card}</g>', pal))
        add(f'<g fill="{edge}" stroke="{edge}" stroke-width="16" stroke-linejoin="round">{card}</g>'
            f'<g fill="{s.cream}" stroke="{s.anggur}" stroke-width="5" stroke-linejoin="round">{card}</g>'
            f'<g fill="{s.cream}">{card}</g>')
        grid = (''.join(f'M{x} {ny}v{4 * fs}' for x in sx)
                + ''.join(f'M{sx[0]} {ny + k * fs}H{sx[-1]}' for k in range(1, 5)))
        add(f'<path d="{grid}" stroke="{s.ink}" stroke-opacity=".55" stroke-width="1.5" stroke-linecap="round"/>'
            f'<path d="M{sx[0] - 1} {ny}H{sx[-1] + 1}" stroke="{s.ink}" stroke-width="4" stroke-linecap="round"/>')
        names = list(dict.fromkeys(c for c, _, _ in seq))
        for gi, c in enumerate(names):
            # unknown shape, or above fret 4 (off the diagram): just the chord name
            shape = shapes.get(c, '')
            if not all(f_ in '01234x' for f_ in shape):
                shape = ''
            dots = ''.join(f'<circle cx="{sx[k]}" cy="{ny + (int(f_) - .5) * fs}" r="4.6"/>'
                           for k, f_ in enumerate(shape) if f_.isdigit() and f_ != '0')
            opens = ''.join(f'<circle cx="{sx[k]}" cy="{ny - 7}" r="2.8"/>' for k, f_ in enumerate(shape) if f_ == '0')
            muted = ''.join(f'<path d="M{sx[k] - 3} {ny - 10}l6 6m0-6l-6 6"/>' for k, f_ in enumerate(shape) if f_ == 'x')
            cfs = fit(c, cw - 12, 31, 12)               # long names (e.g. "F#m7b5") shrink
            size = f' font-size="{num(cfs)}"' if cfs < 31 else ''
            add(f'<g class="ch c{gi}"><text x="0" y="40"{size}>{esc(c)}</text>'
                f'<g fill="{s.anggur}">{dots}</g><g fill="none" stroke="{s.ink}" stroke-width="1.6">{opens}{muted}</g></g>')
            # switch on/off in a single step (not a fade)
            kf, vis = [], None
            for c2, t, _ in seq:
                v = 1 if c2 == c else 0
                if v != vis:
                    kf.append(f'{pct(t)}{{opacity:{v}}}')
                    vis = v
            kf.append(f'100%{{opacity:{vis}}}')
            css.append(f".c{gi}{{animation:c{gi} {loop:.2f}s step-end infinite}}@keyframes c{gi}{{{''.join(kf)}}}")
        add('</g></g>')
        css.append(
            ".ch{opacity:0}.c0{opacity:1}"
            f".ch text{{font-family:{ROUND};font-weight:800;font-size:31px;text-anchor:middle;fill:{s.ink}}}"
            f".cd{{animation:cd {beat * 2:.2f}s ease-in-out infinite alternate}}"
            "@keyframes cd{0%{transform:translateY(0) rotate(0)}100%{transform:translateY(-4px) rotate(1.5deg)}}")

    # ------------------------------------------------------------ music notes, one per strum
    defs.append('<g id="n1"><ellipse cx="0" cy="0" rx="7.5" ry="5.8" transform="rotate(-22)"/>'
                '<rect x="4.2" y="-27" width="3.6" height="27" rx="1.5"/>'
                '<path d="M4.2-27q12 3 11 16q-3-8-11-9z"/></g>')
    defs.append('<g id="n2"><ellipse cx="0" cy="0" rx="7" ry="5.4" transform="rotate(-22)"/>'
                '<ellipse cx="20" cy="-5" rx="7" ry="5.4" transform="rotate(-22 20 -5)"/>'
                '<rect x="3.8" y="-25" width="3.4" height="25" rx="1.5"/><rect x="23.8" y="-30" width="3.4" height="25" rx="1.5"/>'
                '<path d="M3.8-25L27.2-30v6L3.8-19z"/></g>')
    notes = [('n1', 810, 192, s.anggur, -2), ('n2', 836, 214, s.pink, 22),
             ('n1', 822, 178, s.langit, 46), ('n1', 846, 200, s.mint, 2)]
    for i, (nid, x, y, col, dx) in enumerate(notes):
        add(f'<g transform="translate({x} {y})"><g class="nt nt{i}" style="animation-delay:{beat * (.15 + .5 * i):.3f}s">'
            f'<use href="#{nid}" fill="{edge}" stroke="{edge}" stroke-width="7" stroke-linejoin="round"/>'
            f'<use href="#{nid}" fill="{col}"/></g></g>')
        # notes vanish by shrinking, not fading: half-transparent notes look muddy on the dark theme
        css.append(f"@keyframes nt{i}{{0%{{transform:translate(0,0) scale(0) rotate(0);opacity:1}}"
                   f"12%{{transform:translate({dx * .1:.1f}px,-14px) scale(.85) rotate(1deg)}}"
                   f"72%{{transform:translate({dx * .78:.1f}px,-92px) scale(1.1) rotate({6 + 2 * i}deg);opacity:1}}"
                   f"100%{{transform:translate({dx}px,-118px) scale(0) rotate({8 + 3 * i}deg);opacity:1}}}}"
                   f".nt{i}{{animation:nt{i} {beat * 2:.2f}s ease-out infinite both}}")
    css.append(".nt{opacity:0}")   # with reduced motion the notes simply stay hidden

    desc = 'on the right a banana mascot strums a ukulele'
    desc += (', a chord card shows the chord being played' if has else '') + ' while music notes float up'
    return Drawn(svg=''.join(out), css=''.join(css), defs=''.join(defs), title_right=540, desc=desc)

