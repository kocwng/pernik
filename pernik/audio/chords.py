"""Guess the chords (and the beat) of a song, for the mixtape's chord card.

    python -m pernik.audio.chords SONG OUT.json      # detect and write OUT.json
    python -m pernik.audio.chords --self-check       # check the ukulele shape table

Ported from kocwng-profile/tools/chords.py. How it works, in short:
  1. ffmpeg decodes the song (mp3, m4a, ogg, wav, ...) to mono 22.05 kHz samples.
  2. Every 0.1 s a long FFT window is folded into a 12-note "chroma" vector.
  3. Each vector is compared with templates for 48 chords (12 roots x maj, m, 7, m7);
     the best chord per frame is smoothed with a sliding ~0.5 s majority vote.
  4. The timeline is tidied up: quiet bits join their neighbour, blips shorter than
     ~0.6 s join the previous chord, and equal neighbours are merged.
  5. The beat comes from the autocorrelation of the spectral flux (onset strength).

chords.json schema: note, beat, shapes (ukulele GCEA), timeline [[name, start, end], ...],
source_sha1 (sha1 of the song file, so an unchanged song is never analysed twice).
Needs numpy, scipy and ffmpeg: importing this module raises ImportError without them.
"""
import json
import subprocess
import sys

import numpy as np
from scipy.ndimage import uniform_filter1d

from . import sha1

SR = 22050
HOP_S = 0.1          # chroma frame step, seconds
NFFT = 16384         # ~0.74 s window, fine enough to tell neighbouring notes apart
MIN_SEG = 0.6        # shorter chord segments are merged into the previous one
SMOOTH = 5           # majority-vote smoothing window, in frames (~0.5 s)
SILENCE_DB = -40.0   # frames this far below the loudest frame count as silent

# Display names: sharps, except Bb and Eb (that is how most ukulele charts spell them).
NOTES = ['C', 'C#', 'D', 'Eb', 'E', 'F', 'F#', 'G', 'G#', 'A', 'Bb', 'B']
QUALITIES = {'': (0, 4, 7), 'm': (0, 3, 7), '7': (0, 4, 7, 10), 'm7': (0, 3, 7, 10)}

# Ukulele, standard GCEA tuning (G4 C4 E4 A4). Fret per string in order G C E A.
# Common first-position shapes; every one is checked by self_check().
SHAPES = {
    'C': '0003',  'Cm': '0333',  'C7': '0001',  'Cm7': '3333',
    'C#': '1114', 'C#m': '1104', 'C#7': '1112', 'C#m7': '1102',
    'D': '2220',  'Dm': '2210',  'D7': '2223',  'Dm7': '2213',
    'Eb': '0331', 'Ebm': '3321', 'Eb7': '3334', 'Ebm7': '3324',
    'E': '1402',  'Em': '0432',  'E7': '1202',  'Em7': '0202',
    'F': '2010',  'Fm': '1013',  'F7': '2313',  'Fm7': '1313',
    'F#': '3121', 'F#m': '2120', 'F#7': '3424', 'F#m7': '2424',
    'G': '0232',  'Gm': '0231',  'G7': '0212',  'Gm7': '0211',
    'G#': '5343', 'G#m': '4342', 'G#7': '1323', 'G#m7': '1322',
    'A': '2100',  'Am': '2000',  'A7': '0100',  'Am7': '0000',
    'Bb': '3211', 'Bbm': '3111', 'Bb7': '1211', 'Bbm7': '1111',
    'B': '4322',  'Bm': '4222',  'B7': '2322',  'Bm7': '2222',
}
OPEN_STRINGS = (7, 0, 4, 9)  # pitch classes of G C E A


def chord_names():
    return [r + q for r in NOTES for q in QUALITIES]


def chord_tones(name):
    """Pitch classes (0 = C) of a chord name such as 'F#m7' -> (root, set of tones)."""
    root = name[:2] if name[:2] in NOTES else name[:1]
    r = NOTES.index(root)
    return r, {(r + i) % 12 for i in QUALITIES[name[len(root):]]}


def shape_pitches(shape):
    return {(o + int(f)) % 12 for o, f in zip(OPEN_STRINGS, shape) if f != 'x'}


def self_check():
    """Every shape must only sound chord tones and must contain the root and the third."""
    names = chord_names()
    assert sorted(SHAPES) == sorted(names), 'shape table must cover all 48 chords'
    for name in names:
        r, tones = chord_tones(name)
        third = (r + QUALITIES[name[len(NOTES[r]):]][1]) % 12
        got = shape_pitches(SHAPES[name])
        assert got <= tones, f'{name} {SHAPES[name]}: stray notes {got - tones}'
        assert r in got and third in got, f'{name} {SHAPES[name]}: missing root or third'
    return len(names)


# --------------------------------------------------------------------------- audio

def decode(path, sr=SR):
    """Any audio file -> mono float32 samples, via ffmpeg."""
    out = subprocess.run(['ffmpeg', '-v', 'error', '-nostdin', '-threads', '2', '-i', path, '-map', '0:a:0',
                          '-ac', '1', '-ar', str(sr), '-f', 'f32le', '-'], capture_output=True, check=True).stdout
    return np.frombuffer(out, dtype='<f4').astype(np.float32)


def frames_fft(x, nfft, hop, lo_bin=0, hi_bin=None, chunk=128):
    """Magnitude spectrogram (frames x bins), computed in chunks to keep memory small."""
    if len(x) < nfft:
        x = np.pad(x, (0, nfft - len(x)))
    view = np.lib.stride_tricks.sliding_window_view(x, nfft)[::hop]
    win = np.hanning(nfft).astype(np.float32)
    hi_bin = hi_bin or nfft // 2 + 1
    out = np.empty((len(view), hi_bin - lo_bin), dtype=np.float32)
    for i in range(0, len(view), chunk):
        out[i:i + chunk] = np.abs(np.fft.rfft(view[i:i + chunk] * win, axis=1)[:, lo_bin:hi_bin])
    return out


# --------------------------------------------------------------------------- analysis

def chromagram(x, sr=SR):
    """-> (times of frame centres, chroma 12 x frames, frame energy)."""
    hop = int(HOP_S * sr)
    f = np.fft.rfftfreq(NFFT, 1 / sr)
    band = np.nonzero((f > 120) & (f < 2000))[0]
    S = frames_fft(x, NFFT, hop, band[0], band[-1] + 1).T          # bins x frames
    f = f[band[0]:band[-1] + 1]
    pc = ((np.round(12 * np.log2(f / 440.0)) + 9) % 12).astype(int)
    P = S.astype(np.float64) ** 2
    chroma = np.sqrt(np.stack([P[pc == k].sum(axis=0) for k in range(12)]))
    chroma /= chroma.max(axis=0, keepdims=True) + 1e-12
    t = (np.arange(S.shape[1]) * hop + NFFT / 2) / sr
    return t, chroma, P.sum(axis=0)


def chord_scores(chroma):
    """Cosine similarity of each frame with each chord template (48 x frames)."""
    names, T = chord_names(), []
    for r in range(12):
        for iv in QUALITIES.values():
            v = np.zeros(12)
            v[[(r + i) % 12 for i in iv]] = 1
            v[r] += 0.5                      # the root usually rings loudest
            T.append(v / np.linalg.norm(v))
    score = np.array(T) @ (chroma / (np.linalg.norm(chroma, axis=0, keepdims=True) + 1e-12))
    score[[i for i, n in enumerate(names) if n.endswith('7')]] -= 0.03  # plain triads win ties
    return names, score


def estimate_key(chroma):
    """Krumhansl-Schmuckler key estimate -> ('G major', correlation)."""
    maj = np.array([6.35, 2.23, 3.48, 2.33, 4.38, 4.09, 2.52, 5.19, 2.39, 3.66, 2.29, 2.88])
    mnr = np.array([6.33, 2.68, 3.52, 5.38, 2.60, 3.53, 2.54, 4.75, 3.98, 2.69, 3.34, 3.17])
    tot = chroma.sum(axis=1)
    ks = [(np.corrcoef(np.roll(p, k), tot)[0, 1], f'{NOTES[k]} {mode}')
          for p, mode in ((maj, 'major'), (mnr, 'minor')) for k in range(12)]
    c, key = max(ks)
    return key, float(c)


def estimate_beat(x, sr=SR):
    """Beat length in seconds (50-200 BPM) from spectral-flux autocorrelation."""
    hop = int(0.01 * sr)
    S = np.log1p(frames_fft(x, 2048, hop))
    flux = np.maximum(0, np.diff(S, axis=0)).sum(axis=1).astype(np.float64)
    if len(flux) < 200:
        return 0.5
    flux -= flux.mean()
    n = 1 << int(np.ceil(np.log2(2 * len(flux))))
    F = np.fft.rfft(flux, n)
    ac = np.fft.irfft(F * np.conj(F), n)[:len(flux)]
    lags = np.arange(len(ac)) * hop / sr
    ok = (lags > 60 / 200) & (lags < 60 / 50)
    return float(lags[ok][ac[ok].argmax()])


def smooth_labels(labels, n, size=None):
    """Sliding majority vote over `size` frames; a frame keeps its own chord on ties."""
    onehot = np.zeros((n, len(labels)))
    onehot[labels, np.arange(len(labels))] = 1
    votes = uniform_filter1d(onehot, size or SMOOTH, axis=1, mode='nearest') + 1e-3 * onehot
    return votes.argmax(axis=0)


def tidy(segs, duration, min_len=None):
    """Merge blips into the previous chord and equal neighbours; span 0..duration exactly."""
    min_len = MIN_SEG if min_len is None else min_len
    segs = [list(s) for s in segs]
    while True:
        out = []
        for s in segs:
            if out and out[-1][0] == s[0]:
                out[-1][2] = s[2]
            else:
                out.append(s)
        segs = out
        short = [i for i, s in enumerate(segs) if s[2] - s[1] < min_len]
        if not short or len(segs) == 1:
            break
        i = min(short, key=lambda j: segs[j][2] - segs[j][1])   # shortest first
        if i == 0:
            segs[1][1] = segs[0][1]
        else:
            segs[i - 1][2] = segs[i][2]
        del segs[i]
    segs[0][1], segs[-1][2] = 0.0, duration
    return [[n, round(a, 2), round(b, 2)] for n, a, b in segs]


def detect(x, sr=SR):
    """Samples -> dict(beat, key, timeline) ; timeline = [[name, start, end], ...]."""
    duration = len(x) / sr
    t, chroma, energy = chromagram(x, sr)
    names, score = chord_scores(chroma)
    best = smooth_labels(score.argmax(axis=0), len(names))

    # quiet frames (count-in, fade-out, pauses) take the chord of their neighbour
    loud = energy > energy.max() * 10 ** (SILENCE_DB / 10) if energy.max() > 0 else np.ones(len(t), bool)
    if loud.any():
        first = int(np.argmax(loud))
        best[:first] = best[first]
        for i in range(first + 1, len(best)):
            if not loud[i]:
                best[i] = best[i - 1]

    # chord changes sit halfway between the two frame centres
    edges = np.concatenate([[0.0], (t[1:] + t[:-1]) / 2, [duration]])
    segs, start = [], 0
    for i in range(1, len(best) + 1):
        if i == len(best) or best[i] != best[start]:
            segs.append([names[best[start]], float(edges[start]), float(edges[i])])
            start = i
    key, _ = estimate_key(chroma)
    return {'beat': estimate_beat(x, sr), 'key': key, 'timeline': tidy(segs, round(duration, 2))}


# --------------------------------------------------------------------------- output

def dumps(data):
    """JSON in the same compact, hand-editable layout as docs/chords.json."""
    shapes = list(data['shapes'].items())
    shape_lines = [', '.join(f'{json.dumps(k)}: {json.dumps(v)}' for k, v in shapes[i:i + 6])
                   for i in range(0, len(shapes), 6)]
    tl = data['timeline']
    tl_lines = [', '.join(json.dumps(s) for s in tl[i:i + 4]) for i in range(0, len(tl), 4)]
    return ('{\n'
            f'  "note": {json.dumps(data["note"], ensure_ascii=False)},\n'
            f'  "beat": {json.dumps(data["beat"])},\n'
            '  "shapes": {\n    ' + ',\n    '.join(shape_lines) + '\n  },\n'
            '  "timeline": [\n    ' + ',\n    '.join(tl_lines) + '\n  ],\n'
            f'  "source_sha1": {json.dumps(data["source_sha1"])}\n'
            '}\n')


def analyse(song, rel=None):
    """Song file -> the chords.json dict (rel = the song's path as shown in the note)."""
    res = detect(decode(song))
    used = list(dict.fromkeys(name for name, _, _ in res['timeline']))
    data = {
        'note': (f'Chord timeline for {rel or song} (seconds). Auto-detected, so it may be wrong: '
                 'edit it by hand, then set chords = "keep" for this widget in pernik.toml so the '
                 'build leaves it alone. Shapes: ukulele GCEA fret per string (G C E A), x = muted.'),
        'beat': round(res['beat'], 2),
        'shapes': {n: SHAPES[n] for n in used},
        'timeline': res['timeline'],
        'source_sha1': sha1(song),
    }
    return data, res['key']


def main(argv):
    if argv[1:] == ['--self-check']:
        print(f'shape table ok ({self_check()} chords)')
        return 0
    if len(argv) != 3:
        print(__doc__.split('\n\n')[1], file=sys.stderr)
        return 2
    data, key = analyse(argv[1])
    with open(argv[2], 'w', encoding='utf-8') as f:
        f.write(dumps(data))
    print(f'{len(data["timeline"])} chords, key ~{key}, beat {data["beat"]} s -> {argv[2]}')
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv))
