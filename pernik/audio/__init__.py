"""Audio helpers for the mixtape widget.

This module uses only the standard library, so the cassette sticker and the music page
build anywhere. The heavy parts live next to it and are imported only when needed:

    pernik.audio.chords   chord + beat detection        (numpy, scipy, ffmpeg)
    pernik.audio.video    the player-strip MP4 video    (numpy, Pillow, ffmpeg)

Both raise ImportError when numpy/scipy/Pillow are missing; callers catch it and fall back.
"""
import hashlib
import json
import re
import shutil
import subprocess
import wave


def sha1(path):
    h = hashlib.sha1()
    with open(path, 'rb') as f:
        for block in iter(lambda: f.read(1 << 20), b''):
            h.update(block)
    return h.hexdigest()


def have_ffmpeg():
    return bool(shutil.which('ffmpeg') and shutil.which('ffprobe'))


def duration(path, chords_file=None):
    """Length of an audio file in seconds: ffprobe, then macOS afinfo, then the wave module,
    then the end of the chord timeline. 0.0 when nothing can tell."""
    for cmd in (['ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of', 'csv=p=0', path],
                ['afinfo', path]):
        if not shutil.which(cmd[0]):
            continue
        try:
            out = subprocess.run(cmd, capture_output=True, text=True, timeout=30).stdout
        except (OSError, subprocess.SubprocessError):
            continue
        m = re.search(r'estimated duration:\s*([\d.]+)', out) or re.search(r'^([\d.]+)\s*$', out.strip(), re.M)
        if m:
            return float(m.group(1))
    try:
        with wave.open(path) as w:
            return w.getnframes() / float(w.getframerate())
    except (OSError, wave.Error, EOFError):
        pass
    if chords_file:
        try:
            with open(chords_file, encoding='utf-8') as f:
                tl = json.load(f).get('timeline') or []
            return float(tl[-1][2]) if tl else 0.0
        except (OSError, ValueError, TypeError, IndexError, AttributeError):
            pass
    return 0.0


def length_text(seconds):
    d = int(round(seconds))
    return f'{d // 60}:{d % 60:02d}' if d else ''
