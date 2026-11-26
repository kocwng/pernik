"""Themes: one TOML file holds the palette, fonts and sticker style for every widget.

    from pernik.theme import load_theme
    th = load_theme('komik')           # a name from pernik/themes/ or a path to a .toml file
    pal = th.mode('dark')               # Palette for one of GitHub's two themes
    pal.accents[0], pal.color('pink'), pal.outline, pal.shadow, pal.shadow_opacity, pal.text
"""
import os
import tomllib
from dataclasses import dataclass, field

PKG = os.path.dirname(os.path.abspath(__file__))
THEMES = os.path.join(PKG, 'themes')
MODES = ('light', 'dark')


@dataclass
class Palette:
    mode: str
    accents: list
    colors: dict
    font_round: str
    font_body: str
    outline_w: float
    shadow_dx: float
    shadow_dy: float
    page: str
    outline: str
    shadow: str
    shadow_opacity: float
    text: str
    muted: str
    style: str = 'sticker'   # 'sticker' or 'komik': which drawing style widgets use
    extra: dict = field(default_factory=dict)

    def color(self, name, default=None):
        """A named colour ('pink', 'cream', 'ink'...) or a literal '#rrggbb'."""
        if isinstance(name, str) and name.startswith('#'):
            return name
        return self.colors.get(name, default if default is not None else self.accents[0])

    def accent(self, i):
        return self.accents[i % len(self.accents)]


@dataclass
class Theme:
    name: str
    path: str
    raw: dict

    def mode(self, mode):
        r = self.raw
        m = r.get(mode, {})
        st = r.get('sticker', {})
        fn = r.get('font', {})
        return Palette(
            mode=mode,
            accents=list(r.get('accents', [])) or ['#FF8A3D'],
            colors=dict(r.get('colors', {})),
            font_round=fn.get('round', 'sans-serif'),
            font_body=fn.get('body', 'sans-serif'),
            outline_w=float(st.get('outline', 6)),
            shadow_dx=float(st.get('shadow_dx', 4)),
            shadow_dy=float(st.get('shadow_dy', 5)),
            page=m.get('page', '#ffffff' if mode == 'light' else '#0d1117'),
            outline=m.get('outline', '#FFF6E5'),
            shadow=m.get('shadow', '#2B2340'),
            shadow_opacity=float(m.get('shadow_opacity', .35)),
            text=m.get('text', '#2B2340' if mode == 'light' else '#FFF6E5'),
            muted=m.get('muted', '#57606a'),
            style=r.get('style', 'sticker'),
            extra={k: v for k, v in m.items() if k not in
                   ('page', 'outline', 'shadow', 'shadow_opacity', 'text', 'muted')},
        )


def theme_path(name_or_path, base=None):
    if name_or_path.endswith('.toml'):
        p = name_or_path if os.path.isabs(name_or_path) else os.path.join(base or os.getcwd(), name_or_path)
        return p
    return os.path.join(THEMES, f'{name_or_path}.toml')


def load_theme(name_or_path='komik', base=None):
    path = theme_path(name_or_path, base)
    if not os.path.exists(path):
        have = sorted(f[:-5] for f in os.listdir(THEMES) if f.endswith('.toml'))
        raise SystemExit(f"Theme not found: {name_or_path}. Built-in themes: {', '.join(have)}")
    with open(path, 'rb') as f:
        raw = tomllib.load(f)
    # a theme may start from another one and change a few values
    if 'extends' in raw:
        parent = load_theme(raw['extends'], os.path.dirname(path)).raw
        raw = _merge(parent, raw)
    return Theme(name=raw.get('name', os.path.basename(path)[:-5]), path=path, raw=raw)


def _merge(a, b):
    out = dict(a)
    for k, v in b.items():
        out[k] = _merge(a[k], v) if isinstance(v, dict) and isinstance(a.get(k), dict) else v
    return out
