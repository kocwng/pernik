"""The playground's bridge between the page and Pernik, running inside Pyodide in a Web Worker.

worker.js unpacks pernik.zip next to this file, imports it and calls:

    setup()                 patch the bits a browser can't do, return {"version", "python"}
    set_demo(bytes, secs)   the demo song (bytes) and its length (measured by the page)
    put_file(path, text)    an uploaded logo at assets/logos/<name>.svg (None removes it)
    put_song(path, bytes, secs)  the user's own song for a mixtape (None removes it)
    render(payload_json)    draw one widget in both modes -> JSON {light, dark, alt, logs, ...}
    make_zip(toml, readme, user, profile)  run Pernik's real build + check on a fresh virtual repo
                            -> zip bytes; profile=True makes the "Generate my profile" zip (the
                            filled README, uploaded songs included, no demo song, no problem file)

What is replaced for the browser:
  - stack._fetch (urllib) -> a synchronous XMLHttpRequest, which a worker may make. jsDelivr
    sends CORS headers, and the browser's HTTP cache keeps the logos between visits.
  - the song length (ffprobe / afinfo don't exist here) -> the length the page measured with
    an <audio> element. Chords and video need numpy and ffmpeg, which aren't loaded, so the
    mixtape widget falls back the way it does on a computer without them.
  - git / subprocess calls fail with OSError and Pernik already handles that; the username
    is passed in explicitly (and as GITHUB_REPOSITORY_OWNER for the full build).
"""
import contextlib
import io
import json
import os
import posixpath
import re
import shutil
import sys
import time
import urllib.error
import zipfile

REPO = '/repo'                 # the virtual profile repo widgets render into
BUILD = '/build'               # a fresh repo for each "download" build
CACHE = os.path.join(REPO, '.pernik-cache')
AUDIO = ('.mp3', '.m4a', '.ogg', '.wav', '.flac', '.aac', '.opus')
LOGO_PATH = re.compile(r'assets/logos/[a-z0-9][a-z0-9._-]{0,60}\.svg')
SONG_PATH = re.compile(r'[A-Za-z0-9_][A-Za-z0-9._/-]{0,120}')
_state = {'demo': None, 'secs': 0.0, 'themes': {}, 'files': {}, 'songs': {}}


# ---------------------------------------------------------------- browser replacements

def _fetch(url):
    """urllib's job, done with a synchronous XHR (allowed in workers). Raises like urllib."""
    from js import XMLHttpRequest
    req = XMLHttpRequest.new()
    req.open('GET', url, False)
    req.responseType = 'arraybuffer'
    try:
        req.send(None)
    except Exception as e:  # network error, blocked, offline
        raise OSError(f'network error: {e}') from None
    status = int(req.status or 0)
    if not 200 <= status < 300:
        if status:
            raise urllib.error.HTTPError(url, status, str(req.statusText or 'error'), None, None)
        raise OSError('network error')
    return bytes(req.response.to_bytes())


def setup():
    import pernik
    from pernik.widgets import load_all, mixtape, stack
    load_all()
    stack._fetch = _fetch
    orig = mixtape.duration

    def duration(path, chords_file=None):
        song = _state['songs'].get(_rel(path))
        if song and song[1]:
            return song[1]
        return orig(path, chords_file) or _state['secs']
    mixtape.duration = duration
    os.makedirs(CACHE, exist_ok=True)
    return json.dumps({'version': getattr(pernik, '__version__', ''), 'python': sys.version.split()[0]})


def set_demo(data, secs):
    """The demo song: copied to wherever a mixtape's `song` points, so any path works."""
    _state['demo'] = bytes(data.to_bytes() if hasattr(data, 'to_bytes') else data)
    _state['secs'] = float(secs or 0)
    from pernik.widgets import mixtape
    mixtape._durations.clear()


def _rel(path):
    for root in (REPO, BUILD):
        if str(path).startswith(root + '/'):
            return str(path)[len(root) + 1:]
    return str(path)


def put_song(path, data, secs):
    """The user's own song for a mixtape, kept for previews and for the profile zip."""
    path = posixpath.normpath(str(path or ''))
    if not SONG_PATH.fullmatch(path) or '..' in path.split('/') or not path.lower().endswith(AUDIO):
        return False
    full = os.path.join(REPO, path)
    if os.path.exists(full):
        os.remove(full)
    if data is None:
        _state['songs'].pop(path, None)
    else:
        raw = bytes(data.to_bytes() if hasattr(data, 'to_bytes') else data)
        _state['songs'][path] = (raw, float(secs or 0))
        os.makedirs(os.path.dirname(full) or REPO, exist_ok=True)
        with open(full, 'wb') as f:
            f.write(raw)
    from pernik.widgets import mixtape
    mixtape._durations.clear()
    return True


def _ensure_song(root, song):
    p = str(song or '').strip().replace('\\', '/').removeprefix('./')
    if not p or not p.lower().endswith(AUDIO) or _state['demo'] is None:
        return
    p = posixpath.normpath(p)
    if p.startswith(('/', '..')):
        return
    path = os.path.join(root, p)
    if not os.path.exists(path):
        os.makedirs(os.path.dirname(path) or root, exist_ok=True)
        with open(path, 'wb') as f:
            f.write(_state['demo'])


def put_file(path, text):
    """Keep an uploaded logo (only under assets/logos/) and write it into the preview repo."""
    path = str(path or '')
    if not LOGO_PATH.fullmatch(path) or '..' in path:
        return False
    full = os.path.join(REPO, path)
    if text is None:
        _state['files'].pop(path, None)
        if os.path.exists(full):
            os.remove(full)
        return True
    _state['files'][path] = str(text)
    os.makedirs(os.path.dirname(full), exist_ok=True)
    with open(full, 'w', encoding='utf-8') as f:
        f.write(str(text))
    return True


def _logo_files(widgets):
    """The uploaded files that `logos` tables point at: a widget's own (stack) or one in each of
    its groups ([[widget.tree]], [[widget.line]])."""
    tables = []
    for w in widgets:
        tables.append(w.get('logos'))
        for v in w.values():
            if isinstance(v, list):
                tables += [g.get('logos') for g in v if isinstance(g, dict)]
    out = []
    for logos in tables:
        for spec in (logos.values() if isinstance(logos, dict) else ()):
            rel = spec.get('file') if isinstance(spec, dict) else spec
            if isinstance(rel, str) and rel in _state['files'] and rel not in out:
                out.append(rel)
    return out


def _theme(name):
    from pernik.theme import load_theme
    if name not in _state['themes']:
        _state['themes'][name] = load_theme(name)
    return _state['themes'][name]


# ---------------------------------------------------------------- one widget

def render(payload):
    """payload: {"user", "theme", "widget": {"id", "kind", ...options}} -> JSON result."""
    from pernik.theme import MODES
    from pernik.widgets import Context, load_all
    p = json.loads(payload)
    w = p.get('widget') or {}
    kind, wid = w.get('kind'), str(w.get('id') or w.get('kind') or 'widget')
    user = str(p.get('user') or 'octocat')
    t0 = time.perf_counter()
    out = {'id': wid, 'kind': kind}
    log = io.StringIO()
    try:
        spec = load_all().get(kind)
        if not spec:
            raise ValueError(f'unknown kind "{kind}"')
        theme = _theme(str(p.get('theme') or 'komik'))
        opts = dict(spec.defaults, **{k: v for k, v in w.items() if k not in ('id', 'kind')})
        if kind == 'mixtape':
            _ensure_song(REPO, opts.get('song'))
        results = {}
        with contextlib.redirect_stdout(log):
            for mode in MODES:
                ctx = Context(mode=mode, pal=theme.mode(mode), theme=theme, root=REPO,
                              out=os.path.join(REPO, 'pernik'), user=user, widget_id=wid)
                results[mode] = spec.fn(opts, ctx)
        light, dark = results['light'], results['dark']
        out.update(light=light.svg, dark=dark.svg, same=bool(light.same or light.svg == dark.svg),
                   alt=light.alt or wid, href=light.href, width=light.width, markdown=light.markdown,
                   bytes=[len(light.svg.encode()), len(dark.svg.encode())])
    except ImportError as e:
        name = (e.name or '').split('.')[0]
        out['error'] = (f'needs {name}, which the playground does not load (the GitHub Action does)'
                        if name in ('numpy', 'scipy', 'PIL') else f'ImportError: {e}')
    except SystemExit as e:          # load_theme says "Theme not found" this way
        out['error'] = str(e)
    except Exception as e:
        out['error'] = f'{type(e).__name__}: {e}'
    out['logs'] = _clean_logs(log.getvalue(), wid)
    out['ms'] = round((time.perf_counter() - t0) * 1000)
    return json.dumps(out)


def _clean_logs(text, wid):
    prefix = f'[{wid}]'
    lines = []
    for ln in text.splitlines():
        ln = ln.strip()
        if ln.startswith(prefix):
            ln = ln[len(prefix):].strip()
        if ln.startswith('video:') and ('not installed' in ln or 'waiting for the Action' in ln):
            continue                  # video = "auto": the page explains what happens in the Action
        if ln.startswith('chords:') and 'not installed' in ln:
            ln = 'chords: worked out from the song by the GitHub Action (the playground skips it)'
        if ln and ln not in lines:
            lines.append(ln)
    return lines[:12]


# ---------------------------------------------------------------- the whole profile

def make_zip(toml_text, readme_text, user, profile=False):
    """Run the real `pernik build` and `pernik check` on a fresh repo; zip what it made."""
    import tomllib

    from pernik.build import build
    from pernik.check import check
    shutil.rmtree(BUILD, ignore_errors=True)
    os.makedirs(BUILD)
    os.symlink(CACHE, os.path.join(BUILD, '.pernik-cache'))
    widgets = tomllib.loads(toml_text).get('widget', [])
    for w in widgets:
        if w.get('kind') != 'mixtape':
            continue
        rel = posixpath.normpath(str(w.get('song') or '').strip().removeprefix('./'))
        if rel in _state['songs']:            # the user's own song goes in as is
            full = os.path.join(BUILD, rel)
            os.makedirs(os.path.dirname(full) or BUILD, exist_ok=True)
            with open(full, 'wb') as f:
                f.write(_state['songs'][rel][0])
        elif not profile:                     # the plain SVG zip may borrow the demo song
            _ensure_song(BUILD, w.get('song'))
    logos = _logo_files(widgets)
    for rel in logos:                     # uploaded logos go in at the paths pernik.toml names
        full = os.path.join(BUILD, rel)
        os.makedirs(os.path.dirname(full), exist_ok=True)
        with open(full, 'w', encoding='utf-8') as f:
            f.write(_state['files'][rel])
    config = os.path.join(BUILD, 'pernik.toml')
    with open(config, 'w', encoding='utf-8') as f:
        f.write(toml_text)
    with open(os.path.join(BUILD, 'README.md'), 'w', encoding='utf-8') as f:
        f.write(readme_text)

    log = io.StringIO()
    saved = {k: os.environ.get(k) for k in ('GITHUB_REPOSITORY_OWNER', 'GITHUB_REPOSITORY')}
    os.environ['GITHUB_REPOSITORY_OWNER'] = user
    os.environ['GITHUB_REPOSITORY'] = f'{user}/{user}'
    try:
        with contextlib.redirect_stdout(log):
            cfg, manifest, problems = build(config, quiet=True)
            problems = list(problems) + check(cfg, manifest)
    finally:
        for k, v in saved.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, 'w', zipfile.ZIP_DEFLATED) as z:
        for folder, dirs, files in os.walk(BUILD):
            dirs[:] = sorted(d for d in dirs if not d.startswith('.'))
            for name in sorted(files):
                rel = os.path.relpath(os.path.join(folder, name), BUILD)
                if name.lower().endswith(AUDIO) and rel not in _state['songs']:
                    continue                          # the demo song stays out of your repo
                path = os.path.join(folder, name)
                z.write(path, os.path.relpath(path, BUILD))
        if problems and not profile:
            z.writestr('pernik-problems.txt', '\n'.join(problems) + '\n')
    _state['last_build'] = {'problems': problems, 'files': len(manifest), 'logos': logos,
                            'log': [ln for ln in log.getvalue().splitlines() if ln.strip()][:40]}
    return buf.getvalue()


def last_build():
    return json.dumps(_state.get('last_build') or {})
