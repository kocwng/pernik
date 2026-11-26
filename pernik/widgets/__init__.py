"""Widget registry and the contract every widget follows.

A widget is a function registered under a `kind` name:

    from pernik.widgets import widget, Out

    @widget('divider', defaults={'style': 'wave', 'height': 60})
    def divider(opts, ctx):
        pal = ctx.pal                       # Palette for ctx.mode ('light' or 'dark')
        ...
        return Out(svg=..., alt='A wavy divider')

It is called once per mode (light, then dark) with the same `opts` (the widget's table from
pernik.toml merged over `defaults`). It returns an Out:

    svg    the SVG text for this mode (required)
    alt    text for screen readers, used in the README <img alt>
    href   optional link the picture should open when clicked
    width  the <img width> in the README (default "100%")
    same   True when the light and dark SVG are identical (then only one file is written)
    markdown  optional README text to show instead of the picture (the SVG is still written)

Widgets that make extra files (a music page, a video) call ctx.write(relpath, data) and
ctx.log(...). ctx.root is the user's repo folder, ctx.out the output folder, ctx.user the
GitHub username, ctx.widget_id this widget's id, ctx.seed a stable integer from user+id.
Widgets must only use the Python standard library unless they are marked heavy=True
(then the Action installs numpy/scipy/pillow/ffmpeg for them).
"""
import hashlib
import importlib
import os
import pkgutil
from dataclasses import dataclass, field

REGISTRY = {}


@dataclass
class Out:
    svg: str
    alt: str = ''
    href: str = None
    width: str = '100%'
    same: bool = False
    markdown: str = None   # replaces the <picture> in the README (e.g. a video link)


@dataclass
class Spec:
    kind: str
    fn: object
    defaults: dict = field(default_factory=dict)
    heavy: bool = False
    doc: str = ''


def widget(kind, defaults=None, heavy=False):
    def deco(fn):
        REGISTRY[kind] = Spec(kind, fn, dict(defaults or {}), heavy, (fn.__doc__ or '').strip())
        return fn
    return deco


@dataclass
class Context:
    mode: str
    pal: object
    theme: object
    root: str
    out: str
    user: str
    widget_id: str
    written: list = field(default_factory=list)

    @property
    def seed(self):
        return int(hashlib.sha1(f'{self.user}/{self.widget_id}'.encode()).hexdigest()[:8], 16)

    def write(self, relpath, data):
        """Write an extra file relative to the repo root (bytes or str). Returns the path."""
        path = os.path.join(self.root, relpath)
        os.makedirs(os.path.dirname(path) or '.', exist_ok=True)
        with open(path, 'wb' if isinstance(data, bytes) else 'w') as f:
            f.write(data)
        self.written.append(relpath)
        return path

    def log(self, *a):
        print(f'  [{self.widget_id}]', *a)


def load_all():
    """Import every module in this package so their @widget decorators run."""
    for m in pkgutil.iter_modules(__path__):
        if not m.name.startswith('_'):
            importlib.import_module(f'{__name__}.{m.name}')
    return REGISTRY
