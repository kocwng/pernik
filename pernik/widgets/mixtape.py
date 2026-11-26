"""mixtape: put your own song on your profile.

    [[widget]]
    id = "tape"
    kind = "mixtape"
    song = "docs/music.m4a"          # required: the song file in your repo (mp3, m4a, ogg, wav)
    label = "my tape"                # on the cassette label (default "<user> tape")
    side = "A"
    caption = ["give it", "a listen!"]
    link = ""                        # where the cassette goes; "" = the tape player page below
    page_dir = ""                    # folder of the tape player page; "" = "docs/<id>"
    pages = "docs"                   # the folder GitHub Pages publishes: "docs" or "/"
    chords = "auto"                  # "auto" | "keep" | "off"
    video = ""                       # an uploaded https://github.com/user-attachments/... video
    make_video = false               # also render <output>/<id>.mp4 to upload

What it makes:
  - the cassette sticker (one SVG for both GitHub themes) that links to `link`;
  - a tape player page in `page_dir`: index.html + tape.json (settings) + chords.json, which
    GitHub Pages serves at https://<user>.github.io/<repo>/<page_dir minus pages>/;
  - with chords = "auto", chords.json is worked out from the song whenever the song file
    changes (sha1); "keep" never touches it (use that after fixing chords by hand); "off"
    hides the chord card;
  - with make_video = true, <output>/<id>.mp4: a player-strip video to upload by hand;
  - with video set, the README shows that video player instead of the cassette.

Chords and the video need numpy, scipy, Pillow and ffmpeg (the Action installs them when a
mixtape is in pernik.toml). Without them the sticker and the page still build, and the
existing chords.json is kept.
"""
import hashlib
import json
import os
import posixpath
import re
import subprocess
from string import Template

from ..audio import duration, have_ffmpeg, length_text, sha1
from ..text import SLACK, esc, fit, width
from . import Out, widget

PAGE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'mixtape.html')
PAGE_MARK = 'made by pernik mixtape'

DEFAULTS = {
    'song': '',
    'label': '',
    'side': 'A',
    'caption': ['give it', 'a listen!'],
    'link': '',
    'page_dir': '',
    'pages': 'docs',
    'chords': 'auto',
    'video': '',
    'make_video': False,
}

TEMPLATE = Template('''\
<svg xmlns="http://www.w3.org/2000/svg" width="900" height="170" viewBox="0 0 900 170" role="img" aria-labelledby="t d">
  <title id="t">$title</title>
  <desc id="d">$desc</desc>
  <defs>
    <g id="n1">
      <ellipse cx="0" cy="0" rx="8.5" ry="6.5" transform="rotate(-22)"/>
      <rect x="4.6" y="-27" width="4.2" height="27" rx="2"/>
      <path d="M6.5 -27 C10 -20 19 -19 17 -8 C15 -13 11 -15 6.5 -16 Z"/>
    </g>
    <g id="n2">
      <ellipse cx="0" cy="0" rx="8" ry="6.2" transform="rotate(-22)"/>
      <ellipse cx="22" cy="-5" rx="8" ry="6.2" transform="rotate(-22 22 -5)"/>
      <rect x="4.4" y="-27" width="4" height="27" rx="2"/>
      <rect x="26.4" y="-32" width="4" height="27" rx="2"/>
      <path d="M4.4 -28 L30.4 -33 L30.4 -26 L4.4 -21 Z"/>
    </g>
    <path id="star" d="M0 -13 C1.6 -4 4 -1.6 13 0 C4 1.6 1.6 4 0 13 C-1.6 4 -4 1.6 -13 0 C-4 -1.6 -1.6 -4 0 -13 Z"/>
    <style>
      .t { font-family: $font_round; font-weight: 800; }
      .s { font-family: $font_body; }

      .bob { animation: bob 2.6s cubic-bezier(.5,-0.4,.5,1.4) infinite; }
      @keyframes bob {
        0%, 100% { transform: translateY(0); }
        50% { transform: translateY(-5px); }
      }

      .reel { transform-box: fill-box; transform-origin: center; animation: spin 2.2s linear infinite; }
      .reel.r2 { animation-duration: 1.6s; }
      @keyframes spin { to { transform: rotate(-360deg); } }

      .nt { opacity: 0; animation: rise 3.6s ease-out infinite; }
      .d1 { animation-delay: 0s; }
      .d2 { animation-delay: -0.9s; }
      .d3 { animation-delay: -1.8s; }
      .d4 { animation-delay: -2.7s; }
      @keyframes rise {
        0% { opacity: 1; transform: translate(0, 18px) rotate(-8deg) scale(0); }
        15% { opacity: 1; transform: translate(4px, 0) rotate(6deg) scale(1); }
        55% { opacity: 1; transform: translate(-4px, -14px) rotate(-6deg) scale(1); }
        80% { opacity: 1; transform: translate(6px, -30px) rotate(8deg) scale(0); }
        80.01%, 100% { opacity: 0; transform: translate(6px, -30px) rotate(8deg) scale(0); }
      }

      .eq { transform-box: fill-box; transform-origin: 50% 100%; animation: eq 1.6s cubic-bezier(.5,-0.4,.5,1.4) infinite; }
      .e2 { animation-duration: 1.9s; animation-delay: -0.5s; }
      .e3 { animation-duration: 1.5s; animation-delay: -1.1s; }
      .e4 { animation-duration: 2.1s; animation-delay: -0.3s; }
      .e5 { animation-duration: 1.7s; animation-delay: -0.8s; }
      @keyframes eq {
        0%, 100% { transform: scaleY(.55); }
        30% { transform: scaleY(1); }
        60% { transform: scaleY(.7); }
        80% { transform: scaleY(.85); }
      }

      .pulse { transform-box: fill-box; transform-origin: center; animation: pulse 2s cubic-bezier(.5,-0.4,.5,1.4) infinite; }
      @keyframes pulse {
        0%, 100% { transform: scale(1); }
        40% { transform: scale(1.08); }
        70% { transform: scale(.97); }
      }
      .halo { transform-box: fill-box; transform-origin: center; animation: halo 2s ease-out infinite; }
      @keyframes halo {
        0% { opacity: 1; transform: scale(1); }
        45% { opacity: .7; }
        80%, 100% { opacity: 0; transform: scale(1.3); }
      }

      .wig { transform-box: fill-box; transform-origin: center; animation: wig 3.4s cubic-bezier(.5,-0.4,.5,1.4) infinite; }
      @keyframes wig {
        0%, 100% { transform: rotate(0deg); }
        50% { transform: rotate(2.5deg) translateY(-2px); }
      }

      .tw { transform-box: fill-box; transform-origin: center; animation: tw 2.4s cubic-bezier(.5,-0.4,.5,1.4) infinite; }
      .tw2 { animation-duration: 3.1s; animation-delay: -1.2s; }
      @keyframes tw {
        0%, 100% { transform: scale(.7) rotate(0deg); }
        50% { transform: scale(1.1) rotate(20deg); }
      }

      @media (prefers-reduced-motion: reduce) {
        .bob, .reel, .eq, .pulse, .halo, .wig, .tw { animation: none; }
        .nt { animation: none; opacity: 1; }
        .halo { opacity: 0; }
      }
    </style>
  </defs>

  <g transform="translate(34 26) rotate(-3 145 60)">
    <g class="bob">
      <rect x="4" y="5" width="290" height="122" rx="18" fill="$ink" opacity=".35"/>
      <rect x="0" y="0" width="290" height="122" rx="18" fill="$anggur" stroke="$cream" stroke-width="5"/>

      <g fill="$cream" stroke="$ink" stroke-width="1.4">
        <circle cx="12" cy="12" r="4"/>
        <circle cx="278" cy="12" r="4"/>
        <circle cx="12" cy="110" r="4"/>
        <circle cx="278" cy="110" r="4"/>
      </g>

      <rect x="22" y="10" width="246" height="84" rx="10" fill="$cream"/>
      <rect x="22" y="58" width="246" height="7" fill="$pink"/>
      <rect x="22" y="69" width="246" height="7" fill="$kuning"/>
      <text x="36" y="$label_y" class="t" font-size="$label_fs" fill="$ink">$label</text>
      <text x="37" y="51" class="s" font-size="11.5" font-weight="600" fill="$ink" opacity=".8">$sideline</text>
      <circle cx="246" cy="30" r="12" fill="$pink"/>
      <text x="246" y="$badge_y" class="t" font-size="$badge_fs" fill="$cream" text-anchor="middle">$side</text>

      <rect x="72" y="54" width="146" height="34" rx="17" fill="$ink"/>
      <circle cx="98" cy="71" r="14" fill="$langit" opacity=".55"/>
      <rect x="98" y="80" width="94" height="4" fill="$langit" opacity=".55"/>
      <g class="reel">
        <circle cx="98" cy="71" r="11" fill="$cream"/>
        <circle cx="98" cy="71" r="4" fill="$ink"/>
        <g fill="$ink">
          <rect x="96.5" y="61.5" width="3" height="5" rx="1"/>
          <rect x="96.5" y="75.5" width="3" height="5" rx="1"/>
          <rect x="88.5" y="69.5" width="5" height="3" rx="1"/>
          <rect x="102.5" y="69.5" width="5" height="3" rx="1"/>
        </g>
      </g>
      <g class="reel r2">
        <circle cx="192" cy="71" r="11" fill="$cream"/>
        <circle cx="192" cy="71" r="4" fill="$ink"/>
        <g fill="$ink">
          <rect x="190.5" y="61.5" width="3" height="5" rx="1"/>
          <rect x="190.5" y="75.5" width="3" height="5" rx="1"/>
          <rect x="182.5" y="69.5" width="5" height="3" rx="1"/>
          <rect x="196.5" y="69.5" width="5" height="3" rx="1"/>
        </g>
      </g>

      <path d="M78 122 L90 100 L200 100 L212 122" fill="$jeruk" stroke="$cream" stroke-width="4" stroke-linejoin="round"/>
      <g fill="$cream" stroke="$ink" stroke-width="1.4">
        <circle cx="112" cy="112" r="4.5"/>
        <circle cx="178" cy="112" r="4.5"/>
        <rect x="139" y="106" width="12" height="10" rx="2"/>
      </g>
    </g>
  </g>

  <g transform="translate(398 118) scale(1.15) translate(-398 -118)">
  <g transform="translate(350 76)">
    <g class="nt d1">
      <use href="#n1" transform="translate(3 4)" fill="$ink" opacity=".35"/>
      <use href="#n1" fill="$cream" stroke="$cream" stroke-width="7" stroke-linejoin="round"/>
      <use href="#n1" fill="$kuning"/>
    </g>
  </g>
  <g transform="translate(404 76)">
    <g class="nt d2">
      <use href="#n2" transform="translate(3 4)" fill="$ink" opacity=".35"/>
      <use href="#n2" fill="$cream" stroke="$cream" stroke-width="7" stroke-linejoin="round"/>
      <use href="#n2" fill="$mint"/>
    </g>
  </g>
  <g transform="translate(376 70)">
    <g class="nt d3">
      <use href="#n1" transform="translate(3 4)" fill="$ink" opacity=".35"/>
      <use href="#n1" fill="$cream" stroke="$cream" stroke-width="7" stroke-linejoin="round"/>
      <use href="#n1" fill="$pink"/>
    </g>
  </g>
  <g transform="translate(448 76)">
    <g class="nt d4">
      <use href="#n1" transform="translate(3 4)" fill="$ink" opacity=".35"/>
      <use href="#n1" fill="$cream" stroke="$cream" stroke-width="7" stroke-linejoin="round"/>
      <use href="#n1" fill="$langit"/>
    </g>
  </g>

  <g class="eq"><rect x="363" y="94" width="12" height="52" rx="6" fill="$ink" opacity=".35"/><rect x="360" y="90" width="12" height="52" rx="6" fill="$pink" stroke="$cream" stroke-width="4" vector-effect="non-scaling-stroke"/></g>
  <g class="eq e2"><rect x="381" y="94" width="12" height="52" rx="6" fill="$ink" opacity=".35"/><rect x="378" y="90" width="12" height="52" rx="6" fill="$jeruk" stroke="$cream" stroke-width="4" vector-effect="non-scaling-stroke"/></g>
  <g class="eq e3"><rect x="399" y="94" width="12" height="52" rx="6" fill="$ink" opacity=".35"/><rect x="396" y="90" width="12" height="52" rx="6" fill="$kuning" stroke="$cream" stroke-width="4" vector-effect="non-scaling-stroke"/></g>
  <g class="eq e4"><rect x="417" y="94" width="12" height="52" rx="6" fill="$ink" opacity=".35"/><rect x="414" y="90" width="12" height="52" rx="6" fill="$mint" stroke="$cream" stroke-width="4" vector-effect="non-scaling-stroke"/></g>
  <g class="eq e5"><rect x="435" y="94" width="12" height="52" rx="6" fill="$ink" opacity=".35"/><rect x="432" y="90" width="12" height="52" rx="6" fill="$langit" stroke="$cream" stroke-width="4" vector-effect="non-scaling-stroke"/></g>
  <rect x="356" y="146" width="94" height="6" rx="3.5" fill="$ink" opacity=".35"/>

  </g>

  <g transform="translate(8 0)">
  <g transform="translate(528 84)">
    <circle class="halo" cx="0" cy="0" r="47" fill="none" stroke="$pink" stroke-width="6"/>
    <g class="pulse">
      <circle cx="4" cy="5" r="46" fill="$ink" opacity=".35"/>
      <circle cx="0" cy="0" r="46" fill="$pink" stroke="$cream" stroke-width="6"/>
      <path d="M-11 -17 L-11 17 L19 0 Z" fill="$ink" stroke="$ink" stroke-width="7" stroke-linejoin="round"/>
      <ellipse cx="-20" cy="-24" rx="9" ry="5" transform="rotate(-35 -20 -24)" fill="$cream" opacity=".55"/>
    </g>
  </g>

  <g class="wig">
    <g transform="rotate(-4 730 92)">
      <g class="t">
$caption      </g>
    </g>
  </g>

  <g transform="translate($star1)">
    <g class="tw">
      <use href="#star" transform="translate(2 3)" fill="$ink" opacity=".35"/>
      <use href="#star" fill="$kuning" stroke="$cream" stroke-width="4" stroke-linejoin="round" paint-order="stroke"/>
    </g>
  </g>
  <g transform="translate($star2)">
    <g class="tw tw2">
      <circle cx="1.5" cy="2" r="6" fill="$ink" opacity=".35"/>
      <circle r="6" fill="$mint" stroke="$cream" stroke-width="3.5" paint-order="stroke"/>
    </g>
  </g>
  </g>
</svg>
''')


@widget('mixtape', defaults=DEFAULTS, heavy=True)
def mixtape(opts, ctx):
    """Put your own song on your profile: a cassette sticker that opens a tape player page."""
    t = settings(opts, ctx)
    if ctx.mode == 'light':                  # extra files only once per build
        make_files(t, ctx)
    out = Out(svg=cassette_svg(t, ctx.pal), alt=sentence(' '.join(t['caption'])) + ' Play the recording.',
              href=t['link'], same=True)
    if t['video']:
        # the README shows GitHub's video player instead of the cassette picture
        out.markdown = video_markdown(t)
    return out


# ---------------------------------------------------------------- settings

def settings(opts, ctx):
    song = _repo_path(opts.get('song'), 'song')
    if not song:
        raise ValueError('mixtape needs song = "path/to/your-song.m4a" (a file in your repo)')
    song_abs = os.path.join(ctx.root, song)
    if not os.path.isfile(song_abs):
        raise FileNotFoundError(f'song not found: {song}')

    page_dir = _repo_path(opts.get('page_dir') or f'docs/{ctx.widget_id}', 'page_dir')
    if page_dir in ('', '.'):
        raise ValueError('page_dir must be a folder of its own (like "docs/tape"), not the repo root')
    pages = str(opts.get('pages', 'docs')).strip()
    pages = '' if pages in ('', '/', '.', 'root') else _repo_path(pages, 'pages')

    mode = str(opts.get('chords', 'auto')).strip().lower()
    if mode not in ('auto', 'keep', 'off'):
        raise ValueError(f'chords = "{mode}": use "auto", "keep" or "off"')
    video = str(opts.get('video') or '').strip()
    if video and not video.startswith('https://'):
        raise ValueError('video must be the https://github.com/user-attachments/... link GitHub gives you '
                         'after you upload the MP4')

    owner, repo = owner_repo(ctx.root, ctx.user)
    chords_file = posixpath.join(page_dir, 'chords.json')
    secs = _duration(song_abs, os.path.join(ctx.root, chords_file))
    caption = opts.get('caption') or DEFAULTS['caption']
    caption = [caption] if isinstance(caption, str) else caption
    caption = [str(s).strip() for s in caption if str(s).strip()][:2] or list(DEFAULTS['caption'])

    page_url = None
    if _served(page_dir, pages):
        sub = posixpath.relpath(page_dir, pages or '.')
        page_url = pages_base(owner, repo) + ('' if sub == '.' else sub + '/')
    # the page plays the song from Pages when Pages serves it, else from raw.githubusercontent
    if _served(song, pages):
        song_url, cross = posixpath.relpath(song, page_dir), False
    else:
        song_url, cross = f'https://raw.githubusercontent.com/{owner}/{repo}/HEAD/{song}', True

    return {
        'song': song, 'song_abs': song_abs, 'song_url': song_url, 'cross_origin': cross,
        'label': str(opts.get('label') or '').strip() or f'{ctx.user} tape',
        'side': (str(opts.get('side') or '').strip() or 'A')[:2],
        'caption': caption,
        'link': str(opts.get('link') or '').strip() or page_url or f'https://github.com/{owner}/{repo}',
        'page_dir': page_dir, 'pages': pages, 'page_url': page_url, 'chords': mode,
        'chords_file': chords_file, 'video': video, 'make_video': bool(opts.get('make_video')),
        'duration': secs, 'length': length_text(secs), 'owner': owner, 'repo': repo,
    }


def _repo_path(value, name):
    p = str(value or '').strip().replace('\\', '/')
    if not p:
        return ''
    p = posixpath.normpath(p.removeprefix('./')).strip('/') if not p.startswith('/') else p
    if p.startswith('/') or p == '..' or p.startswith('../'):
        raise ValueError(f'{name} = "{value}" must be a path inside your repo')
    return p


def _served(path, pages):
    """True when GitHub Pages (publishing `pages`, '' = the repo root) serves `path`.
    Jekyll leaves out files and folders that start with _ or ."""
    inside = not pages or path == pages or path.startswith(pages + '/')
    rest = path[len(pages):].lstrip('/') if pages else path
    return inside and not any(part[:1] in '_.' for part in rest.split('/') if part)


def pages_base(owner, repo):
    if repo.lower() == f'{owner}.github.io'.lower():
        return f'https://{owner}.github.io/'
    return f'https://{owner}.github.io/{repo}/'


def owner_repo(root, user):
    """(owner, repo): GITHUB_REPOSITORY in Actions, else the git remote, else (user, user),
    the profile repo every GitHub user can make."""
    gh = os.environ.get('GITHUB_REPOSITORY', '')
    if gh.count('/') == 1:
        return tuple(gh.split('/'))
    try:
        url = subprocess.run(['git', '-C', root, 'remote', 'get-url', 'origin'],
                             capture_output=True, text=True, timeout=5).stdout.strip()
        m = re.search(r'github\.com[:/]([^/]+)/([^/]+?)(?:\.git)?/?$', url)
        if m:
            return m.group(1), m.group(2)
    except (OSError, subprocess.SubprocessError):
        pass
    return user, user


_durations = {}


def _duration(path, chords_file):
    st = os.stat(path)
    key = (path, st.st_mtime_ns, st.st_size)
    if key not in _durations:
        _durations[key] = duration(path, chords_file)
    return _durations[key]


# ---------------------------------------------------------------- extra files

def make_files(t, ctx):
    index = posixpath.join(t['page_dir'], 'index.html')
    index_abs = os.path.join(ctx.root, index)
    if os.path.exists(index_abs):
        with open(index_abs, encoding='utf-8', errors='replace') as f:
            if PAGE_MARK not in f.read(600):
                raise FileExistsError(f'{index} is already there and was not made by Pernik. '
                                      'Set page_dir to a new folder so it is not overwritten.')
    if not t['page_url']:
        ctx.log(f'! {t["page_dir"]} is outside what GitHub Pages publishes ("{t["pages"] or "/"}"), so the '
                'tape player page will not be online. Pages can only publish the repo root or docs/: '
                'keep page_dir under docs/ (or set pages = "/").')
    if t['cross_origin']:
        ctx.log(f'note: GitHub Pages does not serve {t["song"]}, so the page plays it from '
                'raw.githubusercontent.com. Put the song under docs/ for faster loading.')

    update_chords(t, ctx)
    pal = ctx.pal
    page = {
        'label': t['label'], 'side': t['side'], 'song': t['song_url'], 'cross_origin': t['cross_origin'],
        'duration': round(t['duration'], 2), 'length': t['length'], 'owner': t['owner'], 'repo': t['repo'],
        'chords': t['chords'] != 'off',
        'colors': {'krem': pal.color('cream', '#FFF6E5'), 'tinta': pal.color('ink', '#2B2340'),
                   'jeruk': pal.color('jeruk'), 'pink': pal.color('pink'), 'kuning': pal.color('kuning'),
                   'mint': pal.color('mint'), 'langit': pal.color('langit'), 'anggur': pal.color('anggur'),
                   'round': pal.font_round, 'body': pal.font_body},
    }
    ctx.write(posixpath.join(t['page_dir'], 'tape.json'), json.dumps(page, indent=2, ensure_ascii=False) + '\n')
    with open(PAGE, encoding='utf-8') as f:
        ctx.write(index, f.read())
    where = t['page_url'] or t['page_dir']
    ctx.log(f'tape player page: {t["page_dir"]}/ -> {where}')
    if t['make_video']:
        make_video(t, ctx)


def update_chords(t, ctx):
    rel, mode = t['chords_file'], t['chords']
    path = os.path.join(ctx.root, rel)
    if mode == 'off':
        return
    if os.path.exists(path):
        ctx.written.append(rel)          # list it every build, so pernik.json stays the same
    if mode == 'keep':
        if not os.path.exists(path):
            ctx.log(f'chords = "keep" but there is no {rel} yet, so the page hides the chord card')
        return
    digest = sha1(t['song_abs'])
    try:
        with open(path, encoding='utf-8') as f:
            if json.load(f).get('source_sha1') == digest:
                ctx.log(f'chords: {rel} is up to date with the song')
                return
    except (OSError, ValueError, AttributeError):
        pass
    why = None if have_ffmpeg() else 'ffmpeg is not installed'
    if not why:
        try:
            from ..audio import chords as detector
        except ImportError as e:
            why = f'{e.name or e} is not installed (pip install numpy scipy)'
    if why:
        ctx.log(f'chords: {why}, so {rel} was not ' + ('updated' if os.path.exists(path) else 'made') +
                '. The GitHub Action installs what is needed; or set chords = "keep".')
        return
    ctx.log('chords: listening to the song...')
    try:
        data, key = detector.analyse(t['song_abs'], t['song'])
    except Exception as e:  # a strange file shouldn't stop the cassette and the page
        ctx.log(f'! chords: detection failed ({type(e).__name__}: {e}); keeping what was there')
        return
    ctx.write(rel, detector.dumps(data))
    ctx.log(f'chords: {len(data["timeline"])} chords, key ~{key}, beat {data["beat"]} s -> {rel}')


def make_video(t, ctx):
    outrel = os.path.relpath(ctx.out, ctx.root).replace(os.sep, '/')
    rel = posixpath.join(outrel, f'{ctx.widget_id}.mp4')
    path = os.path.join(ctx.root, rel)
    why = None if have_ffmpeg() else 'ffmpeg is not installed'
    if not why:
        try:
            from ..audio import video as vid
        except ImportError as e:
            why = f'{e.name or e} is not installed (pip install numpy pillow)'
    if why:
        ctx.log(f'video: {why}, so {rel} was not made. Turn on make_video in the GitHub Action instead.')
        return
    pal = ctx.pal
    colors = {'deck': pal.color('anggur'), 'cream': pal.color('cream', '#FFF6E5'), 'ink': pal.color('ink', '#2B2340'),
              'pink': pal.color('pink'), 'kuning': pal.color('kuning'), 'mint': pal.color('mint'),
              'langit': pal.color('langit'), 'jeruk': pal.color('jeruk')}
    seconds = float(os.environ.get('PERNIK_VIDEO_SECONDS') or 0) or None    # test hook: a short clip
    stamp = hashlib.sha1(json.dumps([sha1(t['song_abs']), t['label'], t['side'], t['length'], colors,
                                     seconds, vid.W, vid.H, 1]).encode()).hexdigest()[:16]
    if vid.stamp_of(path) == stamp:
        ctx.log(f'video: {rel} is up to date')
    else:
        ctx.log(f'video: rendering {rel} (this takes a while)...')
        try:
            info = vid.render(t['song_abs'], path, t['label'], t['side'], t['length'], colors,
                              seconds=seconds, stamp=stamp, log=ctx.log)
        except Exception as e:
            ctx.log(f'! video: could not render ({type(e).__name__}: {e})')
            return
        ctx.log(f'video: wrote {rel} ({info})')
    ctx.written.append(rel)
    ignore = posixpath.join(outrel, '.gitignore')
    if os.path.exists(os.path.join(ctx.root, ignore)):
        ctx.written.append(ignore)
    else:
        ctx.write(ignore, '# videos are uploaded through github.com by hand, not committed\n*.mp4\n')
    if not t['video']:
        ctx.log('video: to play it on your profile (GitHub only plays videos uploaded through its editor):\n'
                f'    1. On github.com open README.md, click the pencil to edit, and drag {rel} into the text.\n'
                '       (In the GitHub Action, download it first: the run page lists it under Artifacts.)\n'
                '    2. GitHub inserts a https://github.com/user-attachments/assets/... link. Copy it,\n'
                '       then cancel the edit (do not commit it there).\n'
                f'    3. In pernik.toml set video = "<that link>" (and make_video = false) for "{ctx.widget_id}".')


def video_markdown(t):
    # a bare user-attachments link on its own line, with blank lines around it, is a player
    return ('<div align="center">\n\n'
            f'{t["video"]}\n\n'
            f'<sub>Press play above, or open the <a href="{esc(t["link"], attr=True)}">tape player</a>.</sub>\n'
            '</div>')


# ---------------------------------------------------------------- the cassette sticker

def num(v):
    return f'{v:.1f}'.rstrip('0').rstrip('.')


def sentence(s):
    s = s.strip()
    s = s[:1].upper() + s[1:]
    return s if s[-1:] in '.!?…' else s + '.'


def caption_svg(lines, c):
    """Caption lines: ink shadow (+3,+4), then coloured text with a cream outline.
    40/42 px, shrinking together when a line is too long."""
    X, MAXW = 608, 264               # x=608 (inside translate(8 0)) .. right edge ~872
    STARS = 27 + 36 + 8              # star + dot after the shortest line
    if len(lines) == 1:
        spec = [(lines[0], 42, 81.9, c['jeruk'])]
    else:
        spec = [(lines[0], 40, 57.6, c['langit']), (lines[1], 42, 105.9, c['jeruk'])]
    star = min(range(len(spec)), key=lambda i: width(spec[i][0], spec[i][1]))
    s = 1.0
    for i, (text, fs, _, _) in enumerate(spec):
        room = MAXW - (STARS if i == star else 0)
        s = min(s, fit(text, room, fs, 1) / fs)
    out, ends = [], []
    for text, fs, mid, col in spec:
        size = max(14, int(fs * s * 2) / 2)
        base = round(mid + .36 * size, 1)
        tx = esc(text)
        out.append(f'        <text x="611" y="{num(base + 4)}" font-size="{num(size)}" fill="{c["ink"]}" opacity=".35" '
                   f'stroke="{c["ink"]}" stroke-width="6" stroke-linejoin="round" paint-order="stroke">{tx}</text>\n'
                   f'        <text x="608" y="{num(base)}" font-size="{num(size)}" fill="{col}" stroke="{c["cream"]}" '
                   f'stroke-width="6" stroke-linejoin="round" paint-order="stroke">{tx}</text>\n')
        ends.append((X + width(text, size), mid))
    end, mid = ends[star]
    sx = round(min(end + 27, 900 - 8 - 36 - 10))
    return ''.join(out), f'{sx} {round(mid - 13.6)}', f'{sx + 36} {round(mid + 2.4)}'


def cassette_svg(t, pal):
    # named theme colours (the same in both modes, so light and dark share one file)
    c = {k: pal.color(k, d) for k, d in (('anggur', '#7B5CFF'), ('cream', '#FFF6E5'), ('ink', '#2B2340'),
                                          ('pink', '#FF5FA2'), ('kuning', '#FFD23F'), ('langit', '#4CC9F0'),
                                          ('jeruk', '#FF8A3D'), ('mint', '#3DDC97'))}
    side, length = t['side'], t['length']
    # cassette label: room from x=36 to just before the side badge (x~228)
    label, lfs = t['label'], fit(t['label'], 192, 20, 10)
    while width(label, lfs) * SLACK > 192 and len(label) > 1:
        label = label[:-2].rstrip() + '…'
    bfs = fit(side, 19, 15, 9)                       # side letter in the round badge, r=12
    caption, star1, star2 = caption_svg(t['caption'], c)
    title = sentence(' '.join(t['caption']))
    d = int(round(t['duration']))
    if d:
        title += f' A {d}-second recording.' if d < 120 else f' A {round(d / 60)}-minute recording.'
    desc = (f'Retro cassette sticker labelled "{t["label"]}" with spinning reels, floating colourful music notes, '
            f'a small bouncing equalizer and a pulsing play button that says "{" ".join(t["caption"])}".')
    return TEMPLATE.substitute(
        title=esc(title), desc=esc(desc), font_round=esc(pal.font_round), font_body=esc(pal.font_body),
        label=esc(label), label_fs=num(lfs), label_y=num(round(27.8 + .36 * lfs, 1)),
        sideline=esc(f'side {side} · {length}' if length else f'side {side}'),
        side=esc(side), badge_fs=num(bfs), badge_y=num(round(30 + .37 * bfs, 1)),
        caption=caption, star1=star1, star2=star2, **c)
