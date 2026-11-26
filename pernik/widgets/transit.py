"""transit: the tech stack as a transit map (komik style). The drawing lives in _transit.py.

    [[widget]]
    id = "peta"
    kind = "transit"
    title = "peta stack"      # the title bar; "" hides it
    hub = ""                  # hub roundel text; "" = the GitHub username
    train = true              # the little train animation; false = still map
    [[widget.line]]
    name = "languages & frameworks"
    icons = ["go", "python"]
    logos = { echo = "assets/logos/echo.svg" }   # optional, same as stack
"""
from . import widget

DEFAULTS = {
    'title': 'peta stack',
    'hub': '',
    'train': True,
    'line': [
        {'name': 'languages', 'icons': ['python', 'go', 'typescript']},
        {'name': 'tools', 'icons': ['git', 'docker', 'linux']},
    ],
}


@widget('transit', defaults=DEFAULTS)
def transit(opts, ctx):
    """Tech stack as a transit map: one line per group of tools, all meeting at your name.

    title   the title bar above the hub; "" hides it
    hub     text on the hub roundel; "" uses your GitHub username
    train   true: a small train rides line 1 (the one animation); false: a still map
    line    1 to 6 [[widget.line]] tables, each with
              name   the line's name (shown in the key)
              icons  up to 16 tools, Simple Icons names like in stack
              logos  your own logo files for names Simple Icons lacks, e.g. { aws = "assets/aws.svg" }
    """
    from ._transit import render
    return render(opts, ctx)
