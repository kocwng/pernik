"""The mixtape card in the "komik" style (docs/design.md): a two-panel comic strip.

    from ._komik_mixtape import komik_svg
    svg = komik_svg(t, ctx.theme, ctx.mode)   # t = mixtape settings(); one file per GitHub theme

    +----------------------------------------------------------------------------+
    | +-----------------------+  +[ "give it a listen!" ]-------- SIDE A · 0:49 -+ |
    | |   halftone burst      |  |                                       +----+ | |
    | |   [ cassette, reels   |  |  demo tape   (the one display word)   | >  | | |
    | |     spin = idle loop ]|  |                                       +----+ | |
    | |                       |  |  [PLAY|                        ]        0:00 | |
    | +-----------------------+  +-------------------------------------------+ |
    +----------------------------------------------------------------------------+

The picture is of a player that has not started: the tape is all on the left reel, the
PLAY bar is empty and the counter reads 0:00, next to the real length. Nothing is invented.
The leading underscore keeps load_all() from treating this module as a widget.
"""
from .. import komik as K
from ..text import esc, fit, width

W, H = 900, 216

# panel A (cassette) and panel B (player), on the 8 grid with 16 gutters
AX, AY, AW, AH = 24, 24, 352, 168
BX, BY, BW, BH = 392, 24, 484, 168
PAD = 24

# the cassette drawing, 224 x 136 (the 100 x 63 mm shell, rounded to the grid)
CW, CH = 224, 136
CX, CY = AX + (AW - CW) // 2, AY + (AH - CH) // 2          # 88, 40
REELS = ((80, 68), (144, 68))                               # hub centres, cassette units


def cassette(k, x, y, side='A'):
    """Two-tone cassette line art at (x, y): tint shell, paper label with a spot band, a
    window showing the tape (ink halftone) wound on the left reel, spinning hubs."""
    L, Hr = K.LINE, K.HAIR
    ink, paper, tint, spot = k.ink, k.paper, k.tint, k.spot
    o = [f'<g transform="translate({x} {y})" stroke-linejoin="round" stroke-linecap="round">']
    # shell
    o.append(f'<rect x="0" y="0" width="{CW}" height="{CH}" rx="{K.R_PANEL}" fill="{tint}" stroke="{ink}" stroke-width="{L}"/>')
    # screws: paper heads with a hairline slot
    for sx, sy in ((12, 12), (CW - 12, 12), (12, CH - 12), (CW - 12, CH - 12)):
        o.append(f'<circle cx="{sx}" cy="{sy}" r="4" fill="{paper}" stroke="{ink}" stroke-width="{Hr}"/>'
                 f'<path d="M{sx - 2.5} {sy}h5" stroke="{ink}" stroke-width="{Hr}"/>')
    # label: paper, writing line, side letter, spot band behind the window
    o.append(f'<rect x="16" y="12" width="192" height="88" rx="{K.R_LABEL}" fill="{paper}" stroke="{ink}" stroke-width="{L}"/>'
             f'<rect x="17.25" y="48" width="189.5" height="40" fill="{spot}"/>'
             f'<path d="M17.25 48H206.75M17.25 88H206.75" stroke="{ink}" stroke-width="{Hr}"/>'
             f'<path d="M56 36H192" stroke="{ink}" stroke-width="{Hr}"/>'
             f'<circle cx="36" cy="30" r="11" fill="{ink}"/>'
             f'<text x="36" y="34.5" font-size="13" text-anchor="middle" class="kl" fill="{paper}" '
             f'stroke="none">{esc(side[:1])}</text>')
    # window with the tape pack: at 0:00 all the tape is on the left reel
    o.append(f'<clipPath id="kwin"><rect x="48" y="52" width="128" height="32" rx="{K.R_PANEL}"/></clipPath>'
             f'<rect x="48" y="52" width="128" height="32" rx="{K.R_PANEL}" fill="{paper}"/>'
             f'<g clip-path="url(#kwin)"><circle cx="{REELS[0][0]}" cy="{REELS[0][1]}" r="26" fill="url(#hti)" '
             f'stroke="{ink}" stroke-width="{Hr}"/>'
             f'<circle cx="{REELS[1][0]}" cy="{REELS[1][1]}" r="14" fill="url(#hti)" stroke="{ink}" stroke-width="{Hr}"/></g>'
             f'<rect x="48" y="52" width="128" height="32" rx="{K.R_PANEL}" fill="none" stroke="{ink}" stroke-width="{L}"/>')
    # hubs: paper ring, six teeth; the spin is the card's one idle loop
    for i, (hx, hy) in enumerate(REELS):
        teeth = ''.join(f'<path d="M{hx} {hy - 4}V{hy - 8}" transform="rotate({a} {hx} {hy})"/>' for a in range(0, 360, 60))
        o.append(f'<g class="reel r{i}"><circle cx="{hx}" cy="{hy}" r="10" fill="{paper}" stroke="{ink}" stroke-width="{L}"/>'
                 f'<g stroke="{ink}" stroke-width="{Hr}">{teeth}</g></g>')
    # the head opening at the bottom: halftone shade, capstan holes, guide slot
    trap = 'M48 136L60 108H164L176 136'
    o.append(f'<path d="{trap}Z" fill="{tint}"/><path d="{trap}Z" fill="url(#ht2)"/>'
             f'<path d="{trap}" fill="none" stroke="{ink}" stroke-width="{L}"/>'
             f'<g fill="{paper}" stroke="{ink}" stroke-width="{Hr}"><circle cx="84" cy="124" r="5"/>'
             f'<circle cx="140" cy="124" r="5"/><rect x="104" y="118" width="16" height="10" rx="1"/></g>')
    o.append('</g>')
    return ''.join(o)


def play_button(k, x, y, s=64):
    """The ▶ button: tint square, ink border, ink triangle (optically centred)."""
    a = s * .2
    cx, cy = x + s / 2 + a * .18, y + s / 2
    tri = f'M{cx - a * .8:g} {cy - a:g}L{cx + a:g} {cy:g}L{cx - a * .8:g} {cy + a:g}Z'
    return (f'<rect x="{x}" y="{y}" width="{s}" height="{s}" rx="{K.R_PANEL}" fill="{k.tint}" '
            f'stroke="{k.ink}" stroke-width="{K.LINE}"/>'
            f'<path d="{tri}" fill="{k.ink}" stroke="{k.ink}" stroke-width="{K.LINE}" stroke-linejoin="round"/>')


def komik_svg(t, theme, mode='light'):
    k = K.Kit(theme, mode)
    side, length = t['side'], t['length']
    caption = ' '.join(t['caption'])
    body = [k.card(0, 0, W, H)]

    # ---- panel A: halftone burst behind the cassette (the hero of the panel)
    body.append(f'<g class="arrive a0"><clipPath id="kpa"><rect x="{AX}" y="{AY}" width="{AW}" height="{AH}" rx="{K.R_PANEL}"/></clipPath>'
                + k.panel(AX, AY, AW, AH)
                + f'<g clip-path="url(#kpa)">{k.burst(AX + AW / 2, AY + AH / 2, 100, 172, points=12, fill="url(#ht1)", seed=7)}</g>'
                + cassette(k, CX, CY, side)
                + k.panel(AX, AY, AW, AH, fill='none') + '</g>')

    # ---- panel B: caption box, side line, the label as the display word, play, PLAY bar
    meta = f'SIDE {side} · {length}' if length else f'SIDE {side}'
    # caption box: the quote plus 16 each side, never reaching the side line on the right
    room = BW - PAD - K.mono_width(meta, 16) - 24 - 32
    words, qs = caption, 16
    q = f'“{words}”'
    while K.mono_width(q, qs) > room and qs > 13:
        qs -= .5
    while K.mono_width(q, qs) > room and len(words) > 1:
        words = words[:-2].rstrip() + '…'
        q = f'“{words}”'
    qw = -(-int(K.mono_width(q, qs) + 32) // 8) * 8
    b = [f'<clipPath id="kpb"><rect x="{BX}" y="{BY}" width="{BW}" height="{BH}" rx="{K.R_PANEL}"/></clipPath>',
         k.panel(BX, BY, BW, BH),
         f'<g clip-path="url(#kpb)"><rect x="{BX}" y="{BY}" width="{qw}" height="32" fill="{k.tint}" '
         f'stroke="{k.ink}" stroke-width="{K.LINE}"/></g>',
         k.mono(BX + 16, BY + 22, q, qs),
         k.mono(BX + BW - PAD, BY + 22, meta, 16, anchor='end'),
         k.panel(BX, BY, BW, BH, fill='none')]

    # display word: the tape label, fitted to the column left of the button
    room = BW - 2 * PAD - 64 - 24 - 4                      # minus button, gap and print shadow
    label, size = t['label'], fit(t['label'], room, 56, 28)
    while width(label, size) * 1.06 > room and len(label) > 1:
        label = label[:-2].rstrip() + '…'
    base = 112 if size >= 44 else 108
    b.append(k.display(BX + PAD, base, label, size))
    b.append(play_button(k, BX + BW - PAD - 64, 64))      # the README wraps the card in Out.href

    # the PLAY bar is empty and the counter reads 0:00: a picture of a player before you press play
    bar_w = BW - 2 * PAD - 64 - 24
    b.append(k.bar(BX + PAD, 144, bar_w, 24, 0, label='PLAY'))
    b.append(k.mono(BX + BW - PAD, 161, '0:00', 16, anchor='end'))
    body.append('<g class="arrive a1">' + ''.join(b) + '</g>')

    css = (K.Kit.css_arrive()
           + '.reel{transform-box:fill-box;transform-origin:center;animation:spin 2.4s linear infinite}'
           + '.reel.r1{animation-duration:1.6s}'
           + '@keyframes spin{to{transform:rotate(-360deg)}}')

    d = int(round(t['duration']))
    title = caption[:1].upper() + caption[1:]
    title = title if title[-1:] in '.!?…' else title + '.'
    if d:
        title += f' A {d}-second recording.' if d < 120 else f' A {round(d / 60)}-minute recording.'
    desc = (f'Comic-strip card: a cassette labelled side {side} with spinning reels on a halftone burst, '
            f'the title "{t["label"]}", a play button, an empty PLAY bar at 0:00 of {length or "the song"}, '
            f'and the caption "{caption}".')
    return k.doc(W, H, ''.join(body), title=title, desc=desc, css=css)
