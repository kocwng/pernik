"""hero in the komik style: a manga chapter title card.

Left: a mono header ("No.01 ----- @user"), the greeting as the one display line (1-2 lines),
an optional tagline in circled letters, and optional real stats (hearts, EXP bar).
Right: a framed panel where the banana strums a ukulele in front of a halftone burst, with a
few kamboja petals; with a chords.json an ink tag pinned to the panel shows the chord.

Options (on top of the sticker hero's greeting / mascot / chords / beat):
    tagline    ""        short line; up to 12 characters as circled letters, longer as a mono caption
    hp         unset     [full, total] hearts, e.g. [4, 6]
    exp        unset     0..1 (or 0..100) fill of the EXP bar
    exp_label  "EXP"     text on the bar's tab, e.g. "GO"
    issue      1         the "No.01" in the header (0 hides it)
"""
import os

from .. import komik as K
from ..mascots import load_chords
from ..mascots.banana_komik import draw_banana
from ..text import SLACK, width
from . import Out

W, H = 900, 320
LX = 40                       # left column start
PX, PY, PW = 552, 24, 324     # the mascot panel (right edge 876)
PH = H - 2 * PY
GUT = 40                      # left column end = PX - GUT


def _int(v, lo, hi):
    try:
        return max(lo, min(hi, int(v)))
    except (TypeError, ValueError):
        return None


def _stats(opts, say):
    hp = opts.get('hp')
    hearts = None
    if hp not in (None, '', False):
        try:
            if isinstance(hp, str):
                hp = hp.replace('/', ' ').split()
            full, total = int(hp[0]), int(hp[1])
            total = max(1, min(10, total))
            hearts = (max(0, min(total, full)), total)
        except (TypeError, ValueError, IndexError):
            say(f'hp should look like [4, 6] (full, total); got {hp!r}')
    exp = opts.get('exp')
    frac = None
    if exp not in (None, '', False):
        try:
            frac = float(exp)
            frac = frac / 100 if frac > 1 else frac
            frac = max(0.0, min(1.0, frac))
        except (TypeError, ValueError):
            say(f'exp should be a number from 0 to 1; got {exp!r}')
    label = str(opts.get('exp_label') or 'EXP').strip().upper()[:6] or 'EXP'
    return hearts, frac, label


def _fit(greeting, maxw, room):
    """(lines, size): the biggest display size that fits maxw x room.

    Tries the lines as given, every two-line split of one long line, and two short lines
    joined into one, and keeps whichever prints biggest (ties go to the lines as given)."""
    def size_for(lines):
        f = min([104 if len(lines) == 1 else 88] + [int(maxw / (width(t, 1) * SLACK)) for t in lines])
        while _block_h(len(lines), f) > room and f > 28:
            f -= 2
        return max(f, 28)

    cands = [greeting]
    if len(greeting) == 1 and ' ' in greeting[0]:
        words = greeting[0].split()
        cands += [[' '.join(words[:j]), ' '.join(words[j:])] for j in range(1, len(words))]
    elif len(greeting) == 2:
        cands.append([' '.join(greeting)])
    best = max(cands, key=size_for)          # max() keeps the first of equals
    return best, size_for(best)


def _block_h(n, f):
    """Height of n display lines at size f: cap height, line steps, descenders."""
    return round(f * .74) + round(f * 1.02) * (n - 1) + round(f * .2)


def render(opts, ctx):
    k = K.Kit(ctx.theme, ctx.mode)
    say = ctx.log if ctx.mode == 'light' else (lambda *a: None)

    greeting = opts.get('greeting') or ['hello!']
    if isinstance(greeting, str):
        greeting = [greeting]
    greeting = [str(g).strip() for g in greeting if str(g).strip()] or ['hello!']
    if len(greeting) > 2:
        say(f'greeting has {len(greeting)} lines; only the first two fit')
        greeting = greeting[:2]
    tagline = ' '.join(str(opts.get('tagline') or '').split())
    hearts, frac, exp_label = _stats(opts, say)
    issue = _int(opts.get('issue', 1), 0, 999)

    # ---------------------------------------------------------------- mascot + chords
    try:
        beat = min(3.0, max(.3, float(opts.get('beat') or 1.17)))
    except (TypeError, ValueError):
        beat = 1.17
    name = str(opts.get('mascot') or 'none').strip().lower()
    has_m = name not in ('none', 'off', 'false', '')
    if has_m and name != 'banana':
        say(f'mascot "{name}" has no komik drawing yet; showing none')
        has_m = False
    chords = None
    path = str(opts.get('chords') or '').strip()
    if has_m and path:
        full = path if os.path.isabs(path) else os.path.join(ctx.root, path)
        try:
            chords = load_chords(full)
            beat = chords.beat or beat
        except ValueError as e:
            say(f'no chord tag ({path}: {e}); the banana just strums')

    right = PX - GUT if has_m else W - LX
    colw = right - LX
    body, css = [], [k.css_arrive()]
    add = body.append
    add(k.card(0, 0, W, H))

    # ---------------------------------------------------------------- header: No.01 ------ @user
    hy = 48
    head_l = f'No.{issue:02d}' if issue else ''
    head_r = f'@{ctx.user}' if ctx.user else ''
    x0 = LX
    if head_l:
        add(k.mono(LX, hy, head_l, 13))
        x0 = LX + K.mono_width(head_l, 13) + 12
    x1 = right
    if head_r:
        add(k.mono(right, hy, head_r, 13, anchor='end'))
        x1 = right - K.mono_width(head_r, 13) - 12
    if x1 - x0 > 24:
        add(f'<path d="M{x0:g} {hy - 4.5:g}H{x1:g}" stroke="{k.ink}" stroke-width="{K.HAIR}" stroke-linecap="round"/>')

    # ---------------------------------------------------------------- stats row (bottom), only real values
    # with the mascot everything is set flush left; without it the title card is centred
    mid = None if has_m else W / 2
    stats_h = 0
    if hearts or frac is not None:
        sy = H - 56                          # row centre
        stats_h = 56
        hw = 32 + hearts[1] * 28 - 8 if hearts else 0
        bw = min(256, colw - (hw + 24 if hearts else 0)) if frac is not None else 0
        if frac is not None and bw < 120:
            say('no room for the EXP bar next to that many hearts')
            bw = 0
        total = hw + bw + (24 if hw and bw else 0)
        x = LX if mid is None else round(mid - total / 2)
        if hearts:
            add(k.mono(x, sy + 4.5, 'HP', 13))
            add(k.hearts(x + 32, sy, hearts[0], hearts[1], s=10, gap=8))
            x += hw + 24
        if bw:
            add(k.bar(x, sy - 12, bw, 24, frac, label=exp_label))

    # ---------------------------------------------------------------- greeting + tagline, centred in what is left
    top, bottom = 72, H - 32 - stats_h
    tag_h = (32 if len(tagline) <= 12 else 18) if tagline else 0
    room = bottom - top - (tag_h + 24 if tag_h else 0)
    lines, fs = _fit(greeting, colw - 8, room)
    lh = round(fs * 1.02)
    bh = _block_h(len(lines), fs) +(tag_h + 24 if tag_h else 0)
    base = round(top + (bottom - top - bh) / 2 + fs * .74)
    add('<g class="arrive a1">')
    for i, t in enumerate(lines):
        add(k.display(LX if mid is None else mid, base + i * lh, t, fs, anchor='start' if mid is None else 'middle'))
    add('</g>')
    if tag_h:
        ty = base + (len(lines) - 1) * lh + round(fs * .2) + 24
        if tag_h == 32:
            _, tw = k.circled(0, 0, tagline, d=32, gap=6)
            svg, _ = k.circled(LX if mid is None else round(mid - tw / 2), ty + 16, tagline, d=32, gap=6)
            add(f'<g class="arrive a2">{svg}</g>')
        else:
            add(k.mono(LX if mid is None else mid, ty + 13, f'"{tagline}"', 16, anchor='start' if mid is None else 'middle'))

    # ---------------------------------------------------------------- the panel
    desc = []
    if has_m:
        add(f'<clipPath id="pc"><rect x="{PX}" y="{PY}" width="{PW}" height="{PH}" rx="6"/></clipPath>')
        add(f'<g class="arrive a0">{k.panel(PX, PY, PW, PH)}')
        bx, by = PX + PW / 2 + 28, PY + PH - 36
        add(f'<g clip-path="url(#pc)">{k.burst(bx - 16, by - 112, 64, 112, points=14, fill="url(#ht1)", seed=ctx.seed % 97)}</g>')
        add(k.panel(PX, PY, PW, PH, fill='none'))
        add('</g>')
        # petals: still (the banana's strum is this widget's one loop); one drifts over the frame
        for px, py, s, rot in ((PX + PW - 40, PY + 40, 11, 10), (PX + 40, PY + 96, 9, 40),
                               (PX + PW - 24, PY + 160, 9, 64), (PX + 32, PY + 224, 10, 30),
                               (PX - 4, PY + 152, 10, 52)):
            add(k.kamboja(px, py, s, rot))
        svg, mcss = draw_banana(k, bx, by, beat=beat, chords=chords)
        add(svg)
        css.append(mcss)
        desc.append('on the right a banana strums a ukulele in a comic panel')
        if chords and chords.seq:
            add(_chord_tag(k, chords, css))
            desc.append('an ink tag shows the chord being played')

    title = ' '.join(greeting)
    if tagline:
        desc.insert(0, f'tagline "{tagline}"')
    if hearts:
        desc.append(f'{hearts[0]} of {hearts[1]} hearts')
    if frac is not None:
        desc.append(f'{exp_label} bar {round(frac * 100)}% full')
    d = f'A comic title card saying "{title}"' + (': ' + '; '.join(desc) if desc else '') + '.'
    svg = k.doc(W, H, ''.join(body), title=title, desc=d, css=''.join(css))
    if len(svg.encode()) > 25 * 1024:
        say(f'{len(svg.encode()) // 1024} KB, over the 25 KB budget (a shorter chords.json helps)')
    return Out(svg=svg, alt=title + (' (a banana strums a ukulele)' if has_m else ''))


def _chord_tag(k, chords, css):
    """A small ink label pinned to the panel's top-left corner; the chord name switches on the timeline."""
    seq = chords.seq
    t0, loop = seq[0][1], seq[-1][2] - seq[0][1]
    names = list(dict.fromkeys(c for c, _, _ in seq))
    size = 20
    tw = max(len(c) * K.LABEL_ADV * size * 1.04 for c in names)
    w = max(48, int((tw + 24 + 7) // 8 * 8))
    x, y, h = PX + 16, PY + 16, 32
    out = [f'<g class="arrive a3"><rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{K.R_LABEL}" fill="{k.solid}" '
           f'stroke="{k.ink}" stroke-width="{K.LINE}"/>']
    for gi, c in enumerate(names):
        fs = K.fit_label(c, w - 16, size)
        out.append(f'<text class="kl kc kc{gi}" x="{x + w / 2:g}" y="{y + h / 2 + fs * .36:g}" font-size="{fs:g}" '
                   f'text-anchor="middle" fill="{k.on_solid}">{K.esc(c)}</text>')
        kf, vis = [], None
        for c2, t, _ in seq:
            v = 1 if c2 == c else 0
            if v != vis:
                kf.append(f'{(t - t0) / loop * 100:.2f}%{{opacity:{v}}}')
                vis = v
        kf.append(f'100%{{opacity:{vis}}}')
        css.append(f'.kc{gi}{{animation:kc{gi} {loop:.2f}s step-end infinite}}@keyframes kc{gi}{{{"".join(kf)}}}')
    css.append('.kc{opacity:0;text-transform:none}.kc0{opacity:1}')   # Em is not EM
    out.append('</g>')
    return ''.join(out)
