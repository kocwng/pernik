#!/usr/bin/env python3
"""Build the static playground site (what GitHub Pages serves).

    python3 tools/build_site.py [OUT]        # OUT defaults to "site"

    OUT/<everything in playground/>   the page itself, copied as is
    OUT/pernik.zip                    the pernik package, for the browser to unpack and import
    OUT/gallery.json                  themes, widget options and every widget drawn with its
                                      defaults in every built-in theme, made by Pernik's own build
    OUT/demo.mp3                      the example song, for the mixtape widget
    OUT/.nojekyll

Standard library only. The stack widget's logos come from <repo>/.pernik-cache (downloaded
once and kept); without a network the logos that aren't cached yet are left out.
"""
import contextlib
import io
import json
import os
import shutil
import subprocess
import sys
import tempfile
import zipfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

import pernik  # noqa: E402
from pernik.build import build  # noqa: E402
from pernik.komik import Kit  # noqa: E402
from pernik.theme import MODES, THEMES, load_theme  # noqa: E402
from pernik.widgets import load_all  # noqa: E402

PLAYGROUND = os.path.join(ROOT, 'playground')
PACKAGE = os.path.join(ROOT, 'pernik')
SONG = os.path.join(ROOT, 'examples', 'profile', 'docs', 'music', 'demo.mp3')
CHORDS = os.path.join(ROOT, 'examples', 'profile', 'docs', 'tape', 'chords.json')
CACHE = os.path.join(ROOT, '.pernik-cache')
USER = 'octocat'
MAX_GALLERY = 1_500_000                  # bytes; past this only some themes keep every widget
FULL_THEMES = ('komik', 'stiker')
SMALL_KINDS = ('hero', 'divider')
ZIP_TIME = (2020, 1, 1, 0, 0, 0)         # fixed, so the same code makes the same zip

PLACEHOLDER = '''<!doctype html>
<html lang="en">
<head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>Pernik playground</title></head>
<body style="font-family: system-ui, sans-serif; max-width: 40rem; margin: 3rem auto; padding: 0 1rem">
<h1>Pernik playground</h1>
<p>The playground isn't built yet. Meanwhile, see <a href="https://github.com/kocwng/pernik">Pernik on GitHub</a>.</p>
</body>
</html>
'''


def theme_names():
    return sorted(f[:-5] for f in os.listdir(THEMES) if f.endswith('.toml'))


def swatch(theme):
    """The few colours that show what a theme looks like, per mode."""
    out = {}
    for mode in MODES:
        pal = theme.mode(mode)
        if pal.style == 'komik':
            k = Kit(theme, mode)
            out[mode] = {'paper': k.paper, 'ink': k.ink, 'spot': k.spot, 'tint': k.tint}
        else:
            out[mode] = {'accents': pal.accents, 'outline': pal.outline, 'text': pal.text}
    return out


def git_commit():
    try:
        r = subprocess.run(['git', '-C', ROOT, 'rev-parse', '--short', 'HEAD'],
                           capture_output=True, text=True, timeout=10)
        return r.stdout.strip() if r.returncode == 0 else ''
    except (OSError, subprocess.SubprocessError):
        return ''


def zip_package(dest):
    with zipfile.ZipFile(dest, 'w', zipfile.ZIP_DEFLATED) as z:
        for folder, dirs, files in os.walk(PACKAGE):
            dirs[:] = sorted(d for d in dirs if d != '__pycache__' and not d.startswith('.'))
            for name in sorted(files):
                if name.endswith(('.pyc', '.pyo')) or name.startswith('.'):
                    continue
                path = os.path.join(folder, name)
                info = zipfile.ZipInfo(os.path.relpath(path, ROOT).replace(os.sep, '/'), ZIP_TIME)
                info.compress_type = zipfile.ZIP_DEFLATED
                info.external_attr = 0o644 << 16
                with open(path, 'rb') as f:
                    z.writestr(info, f.read())


def _link_cache(repo):
    """Share <ROOT>/.pernik-cache with the temp repo, so logos are downloaded only once."""
    os.makedirs(CACHE, exist_ok=True)
    try:
        os.symlink(CACHE, os.path.join(repo, '.pernik-cache'), target_is_directory=True)
    except OSError:                       # no symlinks (Windows without rights): copy instead
        shutil.copytree(CACHE, os.path.join(repo, '.pernik-cache'))


@contextlib.contextmanager
def _quiet_build_env():
    """Prerender as a plain octocat profile, even inside GitHub Actions."""
    saved = {k: os.environ.pop(k) for k in ('GITHUB_REPOSITORY', 'GITHUB_REPOSITORY_OWNER') if k in os.environ}
    try:
        yield
    finally:
        os.environ.update(saved)


VARIANTS = [('divider', 'kawung')]   # extra prerenders, so the playground's first paint matches


def prerender(themes, kinds):
    """{theme: {kind: {light, dark, alt}}}, each widget drawn with its defaults."""
    out, problems = {}, []
    with tempfile.TemporaryDirectory(prefix='pernik-site-') as repo:
        os.makedirs(os.path.join(repo, 'docs', 'music'))
        shutil.copyfile(SONG, os.path.join(repo, 'docs', 'music', 'demo.mp3'))
        if os.path.exists(CHORDS):        # matches the song, so no chord detection runs
            os.makedirs(os.path.join(repo, 'docs', 'mixtape'))
            shutil.copyfile(CHORDS, os.path.join(repo, 'docs', 'mixtape', 'chords.json'))
        _link_cache(repo)
        for name in themes:
            lines = ['schema = 1', f'user = "{USER}"', f'theme = "{name}"', 'output = "pernik"']
            for kind in kinds:
                lines += ['', '[[widget]]', f'id = "{kind}"', f'kind = "{kind}"']
                if kind == 'mixtape':
                    lines.append('song = "docs/music/demo.mp3"')
            # style variants the playground's starting profile uses, keyed "kind:style"
            for kind, style in VARIANTS:
                if kind in kinds:
                    lines += ['', '[[widget]]', f'id = "{kind}-{style}"', f'kind = "{kind}"', f'style = "{style}"']
            config = os.path.join(repo, 'pernik.toml')
            with open(config, 'w') as f:
                f.write('\n'.join(lines) + '\n')
            log = io.StringIO()
            with _quiet_build_env(), contextlib.redirect_stdout(log):
                _, manifest, bad = build(config, quiet=True)
            problems += [f'{name}: {p}' for p in bad]
            out[name] = {}
            for w in manifest:
                svg = {}
                for key, rel in w['files'].items():
                    with open(os.path.join(repo, rel), encoding='utf-8') as f:
                        svg[key] = f.read()
                light = svg.get('light', svg.get('both'))
                dark = svg.get('dark', svg.get('both'))
                variant = next((f'{k}:{st}' for k, st in VARIANTS if w['id'] == f'{k}-{st}'), None)
                out[name][variant or w['kind']] = {'light': light, 'dark': dark, 'alt': w.get('alt') or ''}
    return out, problems


def gallery():
    reg = load_all()
    kinds = sorted(reg)
    themes = theme_names()
    pre, problems = prerender(themes, kinds)
    data = {
        'version': pernik.__version__,
        'commit': git_commit(),
        'themes': [{'name': n, 'style': load_theme(n).mode('light').style, 'swatch': swatch(load_theme(n))}
                   for n in themes],
        'widgets': {k: {'defaults': reg[k].defaults, 'doc': reg[k].doc, 'heavy': reg[k].heavy} for k in kinds},
        'prerender': pre,
    }
    text = _dumps(data)
    if len(text.encode()) > MAX_GALLERY:
        for name in themes:
            if name not in FULL_THEMES:
                pre[name] = {k: v for k, v in pre[name].items() if k in SMALL_KINDS}
        text = _dumps(data)
    return text, problems


def _dumps(data):
    return json.dumps(data, ensure_ascii=False, separators=(',', ':')) + '\n'


def build_site(out):
    out = os.path.abspath(out)
    if out == ROOT or ROOT.startswith(out + os.sep):
        raise SystemExit(f'{out} holds the repo; pick another folder for the site')
    if os.path.isdir(out) and os.listdir(out):
        if not os.path.exists(os.path.join(out, 'gallery.json')):
            raise SystemExit(f'{out} is not empty and was not made by this script; pick another folder')
        shutil.rmtree(out)
    os.makedirs(out, exist_ok=True)

    if os.path.isdir(PLAYGROUND):
        shutil.copytree(PLAYGROUND, out, dirs_exist_ok=True,
                        ignore=shutil.ignore_patterns('__pycache__', '*.pyc', '.DS_Store'))
    if not os.path.exists(os.path.join(out, 'index.html')):
        with open(os.path.join(out, 'index.html'), 'w', encoding='utf-8') as f:
            f.write(PLACEHOLDER)
    zip_package(os.path.join(out, 'pernik.zip'))
    shutil.copyfile(SONG, os.path.join(out, 'demo.mp3'))
    open(os.path.join(out, '.nojekyll'), 'w').close()

    text, problems = gallery()
    with open(os.path.join(out, 'gallery.json'), 'w', encoding='utf-8') as f:
        f.write(text)
    return out, len(text.encode()), problems


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    out, size, problems = build_site(argv[0] if argv else 'site')
    for p in problems:
        print('! ' + p)
    zsize = os.path.getsize(os.path.join(out, 'pernik.zip'))
    print(f'site: {out}  (gallery.json {size / 1024:.0f} KB, pernik.zip {zsize / 1024:.0f} KB)')
    return 1 if problems else 0


if __name__ == '__main__':
    sys.exit(main())
