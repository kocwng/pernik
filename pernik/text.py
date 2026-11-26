"""Rough text widths for the SVG generators (no font files needed at build time).

    from pernik.text import ADV, width, fit, esc

ADV is the advance width of each character in em for 'Arial Rounded MT Bold' (the first
font in our title stack), read from the macOS font once and rounded. A few letters keep
the slightly wider hand-tuned values the hero title was laid out with. Characters not
in the table count as DEFAULT_ADV.
"""
import sys
from xml.sax.saxutils import escape

ADV = {
    # lower case
    'a': .58, 'b': .63, 'c': .59, 'd': .62, 'e': .58, 'f': .33, 'g': .63, 'h': .62, 'i': .28,
    'j': .27, 'k': .58, 'l': .30, 'm': .92, 'n': .60, 'o': .62, 'p': .63, 'q': .63, 'r': .42,
    's': .54, 't': .40, 'u': .62, 'v': .54, 'w': .81, 'x': .52, 'y': .54, 'z': .52,
    # upper case
    'A': .72, 'B': .72, 'C': .74, 'D': .74, 'E': .67, 'F': .60, 'G': .79, 'H': .76, 'I': .37,
    'J': .57, 'K': .74, 'L': .60, 'M': .83, 'N': .76, 'O': .79, 'P': .67, 'Q': .79, 'R': .72,
    'S': .67, 'T': .63, 'U': .76, 'V': .69, 'W': .94, 'X': .60, 'Y': .63, 'Z': .65,
    # digits
    **{d: .59 for d in '0123456789'},
    # space and punctuation
    ' ': .22, '!': .36, '?': .57, '.': .31, ',': .30, "'": .24, '’': .31, '-': .33,
    '&': .76, ':': .31, ';': .31, '"': .48, '(': .35, ')': .35, '/': .28, '+': .58,
    '#': .55, '@': .98, '*': .44, '_': .50, '~': .58, '·': .31, '…': 1.0,
}
DEFAULT_ADV = .62
# Fallback fonts (Segoe UI Black, Trebuchet, Nunito) run a little wider: leave some room.
SLACK = 1.06


def width(text, size, track=0.0):
    """Estimated width in px of `text` at font-size `size` (track = extra em per char)."""
    return sum(ADV.get(c, DEFAULT_ADV) + track for c in text) * size


def fit(text, max_w, size, min_size=1.0, track=0.0):
    """Largest font size <= size (rounded down to .5 px) that keeps `text` within max_w."""
    w = width(text, size, track) * SLACK
    if w <= max_w:
        return size
    return max(min_size, int(size * max_w / w * 2) / 2)


def esc(s, attr=False):
    """Escape for XML text (attr=True: also for a double-quoted attribute)."""
    return escape(str(s), {'"': '&quot;'} if attr else {})


