"""pernik.toml: the one file a user edits.

    schema = 1
    theme = "pernik"          # built-in theme name, or a path like "my-theme.toml"
    output = "pernik"         # folder (in your repo) the pictures are written to
    # user = "octocat"        # GitHub username; found automatically in Actions and from git

    [[widget]]
    id = "hello"              # used for file names and the README marker <!-- pernik:hello -->
    kind = "hero"             # which widget (python -m pernik list)
    greeting = ["hello", "there!"]
"""
import os
import re
import subprocess
import tomllib

SCHEMA = 1


def find_user(root):
    gh = os.environ.get('GITHUB_REPOSITORY_OWNER') or os.environ.get('GITHUB_REPOSITORY', '').split('/')[0]
    if gh:
        return gh
    try:
        url = subprocess.run(['git', '-C', root, 'remote', 'get-url', 'origin'],
                             capture_output=True, text=True, timeout=5).stdout
        m = re.search(r'github\.com[:/]([^/]+)/', url)
        if m:
            return m.group(1)
    except (OSError, subprocess.SubprocessError):
        pass
    return os.path.basename(os.path.abspath(root))


def load_config(path):
    root = os.path.dirname(os.path.abspath(path))
    with open(path, 'rb') as f:
        raw = tomllib.load(f)
    schema = raw.get('schema', SCHEMA)
    if schema > SCHEMA:
        raise SystemExit(f'{path} uses schema {schema}; this Pernik understands up to {SCHEMA}. Update Pernik.')
    widgets, seen = [], set()
    for i, w in enumerate(raw.get('widget', [])):
        if 'kind' not in w:
            raise SystemExit(f'widget #{i + 1} in {path} has no kind = "..."')
        wid = str(w.get('id') or f"{w['kind']}-{i + 1}")
        if not re.fullmatch(r'[A-Za-z0-9_-]+', wid):
            raise SystemExit(f'widget id "{wid}" may only use letters, digits, - and _')
        if wid in seen:
            raise SystemExit(f'two widgets share the id "{wid}"')
        seen.add(wid)
        widgets.append(dict(w, id=wid))
    return {
        'root': root,
        'path': path,
        'theme': raw.get('theme', 'pernik'),
        'output': raw.get('output', 'pernik').strip('/') or 'pernik',
        'user': raw.get('user') or find_user(root),
        'readme': raw.get('readme', 'README.md'),
        'widgets': widgets,
    }
