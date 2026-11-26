"""stack: tech-stack logos as die-cut stickers (rounded cream tiles that pop in on load).

Logos come from Simple Icons (https://simpleicons.org), downloaded once from jsDelivr at a
pinned version and cached in <repo>/.pernik-cache/simple-icons/<version>/ so later builds and
offline previews don't need the network.
"""
import json
import math
import os
import re
import urllib.error
import urllib.request

from ..svg import doc
from ..text import SLACK, esc, fit, width
from . import Out, widget
from ._kit import BOUNCE, contrast, num, swatch

# Simple Icons' SVG data is CC0, but the logos are trademarks of their owners (use them as-is).
SI_VERSION = '16.36.0'
SI_BASE = f'https://cdn.jsdelivr.net/npm/simple-icons@{SI_VERSION}'
W = 900
MARGIN = 20
TILT = (-4, 3, -2, 4, -3, 2)
ALIASES = {  # friendly names people type -> Simple Icons slugs
    'golang': 'go', 'js': 'javascript', 'ts': 'typescript', 'node': 'nodedotjs', 'nodejs': 'nodedotjs',
    'node.js': 'nodedotjs', 'postgres': 'postgresql', 'k8s': 'kubernetes', 'gcp': 'googlecloud',
    'vue': 'vuedotjs', 'next': 'nextdotjs', 'nextjs': 'nextdotjs', 'c++': 'cplusplus', 'cpp': 'cplusplus',
    'c#': 'csharp', 'html': 'html5', 'css': 'css', 'tailwind': 'tailwindcss', 'mongo': 'mongodb',
}
SAFE_D = re.compile(r'[MmLlHhVvCcSsQqTtAaZz0-9eE.,\s+-]+')
_memo = {}


def _cache_dir(root):
    d = os.path.join(root, '.pernik-cache', 'simple-icons', SI_VERSION)
    os.makedirs(d, exist_ok=True)
    return d


def _fetch(url):
    if _memo.get('offline'):
        raise OSError('offline')
    req = urllib.request.Request(url, headers={'User-Agent': 'pernik (+https://github.com)'})
    with urllib.request.urlopen(req, timeout=20) as r:
        return r.read()


def _index(root, say):
    """{slug: [title, hex]} for every icon in the pinned version (cached, trimmed)."""
    key = ('index', root)
    if key in _memo:
        return _memo[key]
    path = os.path.join(_cache_dir(root), 'index.json')
    idx = None
    if os.path.exists(path):
        try:
            with open(path, encoding='utf-8') as f:
                idx = json.load(f)
        except (OSError, ValueError):
            idx = None
    if idx is None:
        try:
            data = json.loads(_fetch(f'{SI_BASE}/data/simple-icons.json'))
            idx = {i['slug']: [i['title'], i['hex']] for i in data if i.get('slug') and i.get('hex')}
            with open(path, 'w', encoding='utf-8') as f:
                json.dump(idx, f, separators=(',', ':'))
        except (OSError, ValueError, KeyError, TypeError) as e:
            say(f'could not download the Simple Icons list ({e}); only logos already cached are drawn')
            _memo['offline'] = True
            idx = {}
    _memo[key] = idx
    return idx


def _icon_path(root, slug, say):
    """The icon's path data (24x24 box), or None."""
    key = ('icon', root, slug)
    if key in _memo:
        return _memo[key]
    path = os.path.join(_cache_dir(root), f'{slug}.svg')
    raw = None
    if os.path.exists(path):
        with open(path, encoding='utf-8') as f:
            raw = f.read()
    else:
        try:
            raw = _fetch(f'{SI_BASE}/icons/{slug}.svg').decode('utf-8')
            with open(path, 'w', encoding='utf-8') as f:
                f.write(raw)
        except urllib.error.HTTPError as e:
            if e.code != 404:
                say(f'could not download the "{slug}" logo ({e})')
        except (OSError, UnicodeDecodeError) as e:
            if not _memo.get('offline'):
                say(f'could not download the "{slug}" logo ({e})')
                _memo['offline'] = True
    d = None
    if raw:
        m = re.search(r'<path[^>]*\sd="([^"]+)"', raw)
        if m and SAFE_D.fullmatch(m.group(1)):
            d = m.group(1)
    _memo[key] = d
    return d


@widget('stack', defaults={'numbered': True, 'icons': ['python', 'git', 'docker'], 'columns': 0, 'size': 80, 'labels': True})
def stack(opts, ctx):
    """Tech-stack logos as die-cut stickers (Simple Icons slugs).

    icons    e.g. ["go", "docker", "mysql"] (slugs from simpleicons.org)
    columns  tiles per row; 0 = as many as fit
    size     tile width in px (48-140)
    labels   show the name under the logo
    """
    if ctx.pal.style == 'komik':
        from ._komik_stack import render; return render(opts, ctx)
    pal = ctx.pal
    s = swatch(pal)
    say = ctx.log if ctx.mode == 'light' else (lambda *a: None)
    icons = opts.get('icons') or []
    if isinstance(icons, str):
        icons = [i for i in re.split(r'[,\s]+', icons) if i]
    icons = [str(i).strip() for i in icons if str(i).strip()][:40]
    try:
        size = max(48, min(140, int(opts.get('size') or 80)))
    except (TypeError, ValueError):
        size = 80
    labels = opts.get('labels', True)
    labels = labels if isinstance(labels, bool) else str(labels).lower() not in ('false', 'no', '0', 'off')

    idx = _index(ctx.root, say) if icons else {}
    tiles = []   # (label, path d or None, logo colour)
    for raw in icons:
        slug = raw.lower().replace(' ', '')
        slug = ALIASES.get(slug, slug)
        info = idx.get(slug)
        d = _icon_path(ctx.root, slug, say) if (info or not idx) and re.fullmatch(r'[a-z0-9]+', slug) else None
        if d is None:
            if not _memo.get('offline'):
                say(f'unknown icon "{raw}" (see https://simpleicons.org for slugs); showing just its name')
            tiles.append((raw, None, None))
            continue
        title, hexc = info if info else (raw, '2B2340')
        col = '#' + hexc
        # brand colour, or ink when it would melt into the cream tile (pale yellows, light greens)
        if contrast(col, s.cream) < 1.8:
            col = s.ink
        tiles.append((title, d, col))

    n = len(tiles)
    gap = round(size * .32)
    pitch = size + gap
    fit_cols = max(1, (W - 2 * MARGIN + gap) // pitch)
    try:
        cols = int(opts.get('columns') or 0)
    except (TypeError, ValueError):
        cols = 0
    if cols <= 0:
        rows = max(1, math.ceil(n / fit_cols))
        cols = math.ceil(n / rows) if n else 1
    cols = max(1, min(cols, fit_cols))
    rows = max(1, math.ceil(n / cols))
    th = round(size * 1.26) if labels else size          # tile height
    row_h = th + round(gap * .8)
    pad_top = 16
    h = pad_top + rows * row_h + 4
    r = round(size * .24)
    lfs = max(9, round(size * .15))

    body = []
    ew = pal.outline_w
    for i, (label, d, col) in enumerate(tiles):
        row, c = divmod(i, cols)
        in_row = min(cols, n - row * cols)
        x0 = (W - in_row * pitch + gap) / 2
        cx = x0 + c * pitch + size / 2
        cy = pad_top + row * row_h + th / 2
        tile = f'<rect x="{num(-size / 2)}" y="{num(-th / 2)}" width="{size}" height="{th}" rx="{r}"/>'
        ring = getattr(s, ('pink', 'langit', 'jeruk', 'mint', 'anggur', 'kuning')[i % 6])
        parts = [
            f'<g transform="translate({pal.shadow_dx:g} {pal.shadow_dy:g})" fill="{pal.shadow}" stroke="{pal.shadow}" '
            f'stroke-width="{ew:g}" stroke-linejoin="round" opacity="{pal.shadow_opacity:g}">{tile}</g>',
            f'<g fill="{s.cream}" stroke="{pal.outline}" stroke-width="{ew:g}" stroke-linejoin="round">{tile}</g>',
            f'<rect x="{num(-size / 2 + 5)}" y="{num(-th / 2 + 5)}" width="{size - 10}" height="{th - 10}" rx="{max(4, r - 5)}" '
            f'fill="none" stroke="{ring}" stroke-width="2.2" stroke-dasharray="6 5" stroke-linecap="round"/>',
        ]
        if d:
            ls = size * .5
            ly = -th / 2 + (size - ls) / 2 + (size * .04 if labels else 0)
            parts.append(f'<path transform="translate({num(-ls / 2)} {num(ly)}) scale({ls / 24:.4f})" d="{d}" fill="{col}"/>')
            if labels:
                fs = fit(label, size - 18, lfs, 7)
                parts.append(f'<text class="r" x="0" y="{num(th / 2 - size * .17)}" font-size="{num(fs)}" '
                             f'text-anchor="middle" fill="{s.ink}">{esc(label)}</text>')
        else:
            # unknown icon: just its name, as big as fits (up to two words on two lines)
            words = [w for w in re.split(r'[\s_-]+', label) if w] or [label]
            lines = [' '.join(words[:len(words) // 2 or 1]), ' '.join(words[len(words) // 2 or 1:])] \
                if len(words) > 1 and width(label, lfs * 1.4) * SLACK > size - 14 else [label]
            fs = min(fit(ln, size - 14, lfs * 1.4, 7) for ln in lines)
            for k, ln in enumerate(lines):
                y = (k - (len(lines) - 1) / 2) * fs * 1.1 + fs * .35
                parts.append(f'<text class="r" x="0" y="{num(y)}" font-size="{num(fs)}" text-anchor="middle" '
                             f'fill="{s.ink}">{esc(ln)}</text>')
        body.append(f'<g transform="translate({num(cx)} {num(cy)}) rotate({TILT[i % len(TILT)]})">'
                    f'<g class="pp" style="animation-delay:{.15 + i * .09:.2f}s">{"".join(parts)}</g></g>')

    css = (f".pp{{animation:pop .7s {BOUNCE} both}}"
           "@keyframes pop{0%{transform:scale(0) rotate(-20deg)}70%{transform:scale(1.08) rotate(3deg)}"
           "100%{transform:scale(1) rotate(0)}}")
    names = [t[0] for t in tiles]
    title = 'Tech stack: ' + ', '.join(names) if names else 'Tech stack'
    svg = doc(W, h, ''.join(body), title=title,
              desc=f'{n} logo stickers in a row: ' + ', '.join(names) + '.' if names else 'No logos yet.',
              css=css, pal=pal)
    if len(svg.encode()) > 25 * 1024:
        say(f'{len(svg.encode()) // 1024} KB, over the 25 KB budget; try fewer icons')
    return Out(svg=svg, alt=title)
