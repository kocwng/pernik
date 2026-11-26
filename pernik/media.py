"""Upload mixtape videos to GitHub, so they play right on your profile with no manual step.

    python -m pernik media [pernik.toml]

For every mixtape with video = "auto" whose MP4 is newer than the last upload, this runs
`gh issue comment --attach` on an issue called "Pernik media" in your repo (made once, then
closed). GitHub turns the attachment into a https://github.com/user-attachments/... link, which
is what plays as a video in a README. The link and the video's stamp go to <output>/media.json;
the next `pernik build` puts the player in your README. The previous comment is deleted.

Needs gh 2.99 or newer and a token in GH_TOKEN that can write to the repo (a fine-grained
personal access token for that one repo, with Contents and Issues: read and write). The
Action's own GITHUB_TOKEN can't upload attachments; GitHub only accepts a person's token.
"""
import json
import os
import re
import subprocess

from .config import load_config

TITLE = 'Pernik media'
ISSUE_BODY = ('Pernik keeps the videos for this profile here: GitHub only plays videos in a README when '
              'they were uploaded as attachments. The newest comment for each widget is the one in use; '
              'please leave this issue as it is. Made by https://github.com/kocwng/pernik.')
URL_RE = re.compile(r'https://github\.com/user-attachments/assets/[0-9a-fA-F-]{36}')


class MediaError(RuntimeError):
    pass


def gh(*args, check=True):
    try:
        p = subprocess.run(['gh', *args], capture_output=True, text=True, timeout=300)
    except OSError as e:
        raise MediaError(f'gh is not installed ({e})')
    if check and p.returncode != 0:
        raise MediaError((p.stderr or p.stdout).strip() or f'gh {args[0]} failed')
    return p.stdout.strip()


def gh_version():
    m = re.search(r'gh version (\d+)\.(\d+)', gh('--version', check=False))
    return (int(m.group(1)), int(m.group(2))) if m else (0, 0)


def repo_name(root):
    env = os.environ.get('GITHUB_REPOSITORY', '')
    if '/' in env:
        return env
    url = subprocess.run(['git', '-C', root, 'remote', 'get-url', 'origin'],
                         capture_output=True, text=True).stdout.strip()
    m = re.search(r'github\.com[:/]([^/]+/[^/]+?)(?:\.git)?$', url)
    if not m:
        raise MediaError('could not tell which GitHub repo this is (set GITHUB_REPOSITORY=owner/name)')
    return m.group(1)


def media_issue(repo):
    """The number of the "Pernik media" issue, made (and closed) if it doesn't exist yet."""
    found = json.loads(gh('issue', 'list', '-R', repo, '--state', 'all', '--limit', '50',
                          '--search', f'"{TITLE}" in:title', '--json', 'number,title') or '[]')
    for it in found:
        if it.get('title') == TITLE:
            return it['number']
    url = gh('issue', 'create', '-R', repo, '--title', TITLE, '--body', ISSUE_BODY)
    number = int(url.rstrip('/').rsplit('/', 1)[-1])
    gh('issue', 'close', '-R', repo, str(number), '--reason', 'not planned', check=False)
    return number


def pending(config_path):
    """[(widget id, mp4 path, stamp)] for videos that need uploading."""
    from .audio.video import stamp_of
    from .widgets.mixtape import media_path, read_media
    cfg = load_config(config_path)
    media = read_media(media_path(cfg['root'], cfg['output']))
    out = []
    for w in cfg['widgets']:
        if w['kind'] != 'mixtape' or str(w.get('video', '')).strip().lower() != 'auto':
            continue
        mp4 = os.path.join(cfg['root'], cfg['output'], f"{w['id']}.mp4")
        stamp = stamp_of(mp4)
        if stamp and media.get(w['id'], {}).get('stamp') != stamp:
            out.append((w['id'], mp4, stamp))
    return cfg, out


def upload(config_path, log=print):
    """Upload what's pending. Returns the number of videos uploaded."""
    from .widgets.mixtape import media_path, read_media
    from .widgets.mixtape import source_key, theme_name
    cfg, todo = pending(config_path)
    if not todo:
        log('media: nothing to upload')
        return 0
    if gh_version() < (2, 99):
        raise MediaError('gh 2.99 or newer is needed to upload attachments (gh --version says older)')
    repo = repo_name(cfg['root'])
    number = media_issue(repo)
    path = media_path(cfg['root'], cfg['output'])
    media = read_media(path)
    done = 0
    for wid, mp4, stamp in todo:
        size = os.path.getsize(mp4)
        if size > 10 * 1024 * 1024:
            log(f'! media: {os.path.basename(mp4)} is {size // (1024 * 1024)} MB; GitHub Free accepts up to 10 MB')
        log(f'media: uploading {os.path.relpath(mp4, cfg["root"])} ({size // 1024} KB) to {repo}#{number}')
        comment_url = gh('issue', 'comment', '-R', repo, str(number), '--attach', mp4,
                         '--body', f'Video for the `{wid}` widget (stamp `{stamp}`).')
        m = re.search(r'#issuecomment-(\d+)', comment_url)
        if not m:
            raise MediaError(f'gh did not return a comment link ({comment_url!r})')
        cid = m.group(1)
        body = gh('api', f'repos/{repo}/issues/comments/{cid}', '--jq', '.body')
        found = URL_RE.search(body)
        if not found:
            raise MediaError('the comment has no user-attachments link; GitHub may have changed how uploads work')
        old = media.get(wid, {}).get('comment')
        opts = next(w for w in cfg['widgets'] if w['id'] == wid)
        media[wid] = {'url': found.group(0), 'stamp': stamp, 'comment': cid, 'issue': number,
                      'source': source_key(opts, wid, cfg['user'], theme_name(cfg), cfg['root'])}
        if old and old != cid:
            gh('api', '-X', 'DELETE', f'repos/{repo}/issues/comments/{old}', check=False)
        done += 1
        log(f'media: {wid} -> {found.group(0)}')
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(media, f, indent=2, sort_keys=True)
        f.write('\n')
    return done
