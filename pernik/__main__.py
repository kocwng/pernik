"""Command line:  python -m pernik <command> [pernik.toml]

    build     render every widget and fill the README markers (default)
    preview   build, then write <output>/preview.html showing each widget on light and dark
    check     build, then check the files are safe for GitHub (size, no scripts, valid XML)
    list      show the widget kinds and their options
    init      write a starter pernik.toml and README.md in the current folder
    needs-extras  print "true" if pernik.toml uses a widget that needs numpy/scipy/pillow/ffmpeg
    media     upload mixtape videos (video = "auto") with gh, so they play on your profile
"""
import os
import sys


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    cmd = argv.pop(0) if argv and not argv[0].endswith('.toml') else 'build'
    config = argv[0] if argv else 'pernik.toml'

    if cmd == 'list':
        from .widgets import load_all
        for kind, spec in sorted(load_all().items()):
            heavy = '  (needs extras)' if spec.heavy else ''
            print(f'{kind}{heavy}\n  ' + (spec.doc.splitlines()[0] if spec.doc else ''))
            for k, v in spec.defaults.items():
                print(f'    {k} = {v!r}')
        return 0
    if cmd == 'init':
        from .starter import init
        return init(os.getcwd())
    if cmd == 'needs-extras':             # used by action.yml to skip installing what isn't needed
        from .config import load_config
        from .widgets import load_all
        reg = load_all()
        if not os.path.exists(config):
            print('false')
            return 0
        cfg = load_config(config)
        need = False
        for w in cfg['widgets']:
            spec = reg.get(w['kind'])
            if not spec or not spec.heavy:
                continue
            if w['kind'] == 'mixtape':
                from .widgets.mixtape import needs_extras
                need = need or needs_extras(w, w['id'], cfg)
            else:
                need = True
        print('true' if need else 'false')
        return 0
    if cmd == 'media':                    # the Action runs this when PERNIK_TOKEN is set
        from .media import MediaError, upload
        try:
            upload(config)
        except MediaError as e:
            print(f'! media: {e}')
            return 1
        return 0
    if cmd not in ('build', 'preview', 'check'):
        print(__doc__)
        return 2
    if not os.path.exists(config):
        print(f'No {config} here. Run "python -m pernik init" to start one.')
        return 1

    from .build import build
    cfg, manifest, problems = build(config)
    if cmd == 'preview':
        from .preview import write_preview
        path = write_preview(cfg, manifest)
        print(f'preview: {path}')
    if cmd == 'check':
        from .check import check
        problems += check(cfg, manifest)
        print('all good' if not problems else f'{len(problems)} problem(s)')
    return 1 if problems else 0


if __name__ == '__main__':
    sys.exit(main())
