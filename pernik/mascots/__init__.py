"""Mascots that can stand next to the hero greeting.

A mascot is a function registered under a name:

    from pernik.mascots import mascot, Drawn

    @mascot('banana')
    def banana(pal, beat, chords=None):
        ...
        return Drawn(svg=..., css=..., defs=..., title_right=540, desc='a banana strums a ukulele')

It draws in the hero's own coordinates (a 900 x 300 canvas) in the right-hand part, and says
how far right the greeting may reach (`title_right`). `beat` is seconds per strum or bounce;
`chords` is a Chords (or None) for mascots that play along with a song.

    draw('banana', pal, beat=1.17, chords=load_chords('docs/chords.json'))
"""
import importlib
import json
import pkgutil
import re
from dataclasses import dataclass, field

REGISTRY = {}
MAX_LOOP = 40.0          # a chord card repeats about the first 40 seconds of the song
MAX_CHORDS = 12          # distinct chord names drawn on the card (keeps the SVG small)


@dataclass
class Drawn:
    svg: str
    css: str = ''
    defs: str = ''
    title_right: float = 860
    desc: str = ''


@dataclass
class Chords:
    """A chord timeline: seconds per beat, ukulele shapes ('GCEA' frets) and (name, start, end) rows."""
    beat: float
    shapes: dict
    seq: list = field(default_factory=list)


def mascot(name):
    def deco(fn):
        REGISTRY[name] = fn
        return fn
    return deco


def names():
    for m in pkgutil.iter_modules(__path__):
        if not m.name.startswith('_'):
            importlib.import_module(f'{__name__}.{m.name}')
    return sorted(REGISTRY)


def draw(name, pal, beat=1.17, chords=None):
    if name not in REGISTRY and re.fullmatch(r'[a-z0-9_]+', name or ''):
        try:
            importlib.import_module(f'{__name__}.{name}')
        except ImportError:
            pass
    if name not in REGISTRY:
        raise ValueError(f'unknown mascot "{name}" (have: {", ".join(names())}, or "none")')
    return REGISTRY[name](pal, beat, chords)


def load_chords(path):
    """Read a chords.json -> Chords, or raise ValueError saying what is wrong with it.

    Format: {"beat": 1.17, "shapes": {"C": "0003", ...}, "timeline": [["C", 0.0, 4.17], ...]}"""
    try:
        with open(path, encoding='utf-8') as f:
            cj = json.load(f)
    except FileNotFoundError:
        raise ValueError('not found')
    except (OSError, ValueError) as e:
        raise ValueError(str(e).splitlines()[0][:80])
    if not isinstance(cj, dict):
        raise ValueError('not a JSON object')
    try:
        beat = float(cj.get('beat') or 0)
    except (TypeError, ValueError):
        beat = 0
    beat = round(beat, 3) if .3 <= beat <= 3 else 0
    shapes = cj.get('shapes') if isinstance(cj.get('shapes'), dict) else {}
    shapes = {str(k): str(v) for k, v in shapes.items() if len(str(v)) == 4}   # GCEA, 4 strings
    tl = []
    for row in cj.get('timeline') or []:
        try:
            c, s, e = row[:3]
            c, s, e = str(c).strip(), float(s), float(e)
        except (TypeError, ValueError):
            continue
        if c and e > s:
            tl.append((c[:12], s, e))
    if not tl:
        raise ValueError('the timeline is empty')
    t0 = tl[0][1]
    seq = [r for r in tl if r[2] <= t0 + MAX_LOOP] or tl[:1]
    keep = list(dict.fromkeys(c for c, _, _ in seq))[:MAX_CHORDS]
    seq = [r for r in seq if r[0] in keep]
    return Chords(beat=beat, shapes=shapes, seq=seq)
