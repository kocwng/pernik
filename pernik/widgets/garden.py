"""garden ("Kebun Pernik"): the tech stack as an illustrated garden, one tree per group of tools.

    [[widget]]
    id = "kebun"
    kind = "garden"
    harvest = true            # the banana picks fruit (animation); false = still scene
    mascot = "banana"         # or "none"
    [[widget.tree]]
    name = "languages & frameworks"
    tree = "mangga"           # mangga | kelapa | rambutan | pisang  (default: cycles in this order)
    icons = ["go", "python"]
    logos = { echo = "assets/logos/echo.svg" }   # optional, same as stack

Drawn in the komik style (docs/design.md) with every theme; the drawing is in _garden.py.
"""
from . import widget
from ._komik_heading import flag

DEFAULT_TREES = [
    {'name': 'languages', 'tree': 'mangga', 'icons': ['python', 'go', 'typescript', 'rust', 'react']},
    {'name': 'tools', 'tree': 'kelapa', 'icons': ['git', 'docker', 'linux']},
]


@widget('garden', defaults={'harvest': True, 'mascot': 'banana', 'tree': DEFAULT_TREES})
def garden(opts, ctx):
    """Tech stack as an illustrated garden: one tree per group, the tools are its fruit.

    tree     a list of [[widget.tree]] tables: name, tree (mangga, kelapa, rambutan or pisang;
             default cycles in that order), icons (Simple Icons names, up to 18 per tree),
             logos (your own logo files, as in stack). Up to 6 trees.
    harvest  true: the banana picks fruit and drops it in its basket (one CSS loop); false: still
    mascot   "banana" (on a ladder by the first mango tree) or "none"
    """
    from ._garden import render
    say = ctx.log if ctx.mode == 'light' else (lambda *a: None)
    trees = opts.get('tree')
    if isinstance(trees, dict):
        trees = [trees]
    if not isinstance(trees, list):
        say('tree should be a list of [[widget.tree]] tables; drawing an empty garden')
        trees = []
    good = [t for t in trees if isinstance(t, dict)]
    if len(good) != len(trees):
        say('some [[widget.tree]] entries are not tables and were skipped')
    mascot = str(opts.get('mascot') or 'banana').strip().lower()
    if mascot not in ('banana', 'none'):
        say(f'mascot "{mascot}" is not one of: banana, none; using banana')
        mascot = 'banana'
    return render(good, ctx, harvest=flag(opts.get('harvest'), True), mascot=mascot)
