"""Render every widget in pernik.toml and fill the README markers.

For each [[widget]] it writes <output>/<id>-light.svg and <output>/<id>-dark.svg (or a single
<id>.svg when both are the same), then replaces whatever sits between

    <!-- pernik:<id> -->
    <!-- /pernik:<id> -->

in README.md with a <picture> that shows the right file for GitHub's light or dark theme.
Everything outside the markers is left alone.
"""
import json
import os
import re

from .config import load_config
from .text import esc
from .theme import MODES, load_theme
from .widgets import Context, load_all


def snippet(wid, files, out):
    """The README HTML for one widget. A widget may set out.markdown to put its own README
    block there instead of the picture (mixtape does, to show an uploaded video player)."""
    if getattr(out, 'markdown', None):
        return out.markdown.strip('\n')
    alt = esc(out.alt or wid, attr=True)
    if 'both' in files:
        img = f'<img src="./{files["both"]}" width="{out.width}" alt="{alt}" />'
    else:
        img = ('<picture>\n'
               f'  <source media="(prefers-color-scheme: dark)" srcset="./{files["dark"]}" />\n'
               f'  <img src="./{files["light"]}" width="{out.width}" alt="{alt}" />\n'
               '</picture>')
    if out.href:
        img = f'<a href="{esc(out.href, attr=True)}">\n{img}\n</a>'
    return img


def fill_readme(text, wid, html):
    pat = re.compile(r'(<!-- pernik:' + re.escape(wid) + r' -->\n).*?(<!-- /pernik:' + re.escape(wid) + r' -->)', re.S)
    if not pat.search(text):
        return text, False
    return pat.sub(lambda m: m.group(1) + html + '\n' + m.group(2), text, count=1), True


def build(config_path, only=None, quiet=False):
    cfg = load_config(config_path)
    reg = load_all()
    theme = load_theme(cfg['theme'], cfg['root'])
    outdir = os.path.join(cfg['root'], cfg['output'])
    os.makedirs(outdir, exist_ok=True)
    manifest, snippets, problems = [], {}, []

    # widgets that make data files (e.g. mixtape writes chords.json) run first, so widgets
    # that read those files (the hero's chord card) see them on the very first build
    order = sorted(cfg['widgets'], key=lambda w: 0 if getattr(reg.get(w['kind']), 'heavy', False) else 1)
    for w in order:
        wid, kind = w['id'], w['kind']
        if only and wid not in only:
            continue
        spec = reg.get(kind)
        if not spec:
            problems.append(f'{wid}: unknown kind "{kind}" (have: {", ".join(sorted(reg))})')
            continue
        opts = dict(spec.defaults, **{k: v for k, v in w.items() if k not in ('id', 'kind')})
        results, written = {}, []
        try:
            for mode in MODES:
                ctx = Context(mode=mode, pal=theme.mode(mode), theme=theme, root=cfg['root'],
                              out=outdir, user=cfg['user'], widget_id=wid)
                results[mode] = spec.fn(opts, ctx)
                written += ctx.written
        except ImportError as e:
            if (e.name or '').split('.')[0] in ('numpy', 'scipy', 'PIL'):
                problems.append(f'{wid}: needs an extra package ({e.name}). Install pernik[{kind}] or see the docs.')
            else:
                problems.append(f'{wid}: ImportError: {e}')
            continue
        except Exception as e:  # one broken widget shouldn't stop the others
            problems.append(f'{wid}: {type(e).__name__}: {e}')
            continue

        light, dark = results['light'], results['dark']
        files = {}
        if light.same or light.svg == dark.svg:
            files['both'] = f"{cfg['output']}/{wid}.svg"
            _write(cfg['root'], files['both'], light.svg)
            _remove(cfg['root'], f"{cfg['output']}/{wid}-light.svg", f"{cfg['output']}/{wid}-dark.svg")
        else:
            files['light'] = f"{cfg['output']}/{wid}-light.svg"
            files['dark'] = f"{cfg['output']}/{wid}-dark.svg"
            _write(cfg['root'], files['light'], light.svg)
            _write(cfg['root'], files['dark'], dark.svg)
            _remove(cfg['root'], f"{cfg['output']}/{wid}.svg")
        snippets[wid] = snippet(wid, files, light)
        sizes = {k: len(_read(cfg['root'], v).encode()) for k, v in files.items()}
        manifest.append({'id': wid, 'kind': kind, 'files': files, 'bytes': sizes,
                         'alt': light.alt, 'href': light.href, 'width': light.width,
                         'extra': sorted(set(written))})
        if not quiet:
            print(f'{wid:<16} {kind:<10} ' + ', '.join(f'{v} ({sizes[k] // 1024 or 1} KB)' for k, v in files.items()))

    pos = {w['id']: i for i, w in enumerate(cfg['widgets'])}
    manifest.sort(key=lambda m: pos[m['id']])

    # README markers
    readme = os.path.join(cfg['root'], cfg['readme'])
    missing = []
    if os.path.exists(readme):
        with open(readme) as f:
            text = f.read()
        new = text
        for wid, html in snippets.items():
            new, found = fill_readme(new, wid, html)
            if not found:
                missing.append(wid)
        if new != text:
            with open(readme, 'w') as f:
                f.write(new)
            if not quiet:
                print(f"updated {cfg['readme']}")
    else:
        missing = list(snippets)

    with open(os.path.join(outdir, 'pernik.json'), 'w') as f:
        json.dump({'user': cfg['user'], 'theme': theme.name, 'widgets': manifest}, f, indent=2)
        f.write('\n')

    if missing and not quiet:
        print('\nNot in the README yet. Paste these where you want them:')
        for wid in missing:
            print(f'\n<!-- pernik:{wid} -->\n<!-- /pernik:{wid} -->')
    for p in problems:
        print('! ' + p)
    return cfg, manifest, problems


def _write(root, rel, text):
    path = os.path.join(root, rel)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'w') as f:
        f.write(text)


def _read(root, rel):
    with open(os.path.join(root, rel)) as f:
        return f.read()


def _remove(root, *rels):
    for r in rels:
        p = os.path.join(root, r)
        if os.path.exists(p):
            os.remove(p)
