"""preview.html: every widget on GitHub's light page next to its dark page.

Open it in a browser before pushing. Images are loaded with <img>, the same way GitHub
shows them, so anything that breaks in a README (scripts, web fonts) also breaks here.
"""
import os

from .text import esc
from .theme import load_theme


def write_preview(cfg, manifest):
    theme = load_theme(cfg['theme'], cfg['root'])
    light, dark = theme.mode('light'), theme.mode('dark')
    out = os.path.join(cfg['root'], cfg['output'])
    rows = []
    for w in manifest:
        f = w['files']
        src_l = os.path.relpath(os.path.join(cfg['root'], f.get('light') or f['both']), out)
        src_d = os.path.relpath(os.path.join(cfg['root'], f.get('dark') or f['both']), out)
        size = ' + '.join(f'{v // 1024 or 1} KB' for v in w['bytes'].values())
        rows.append(
            f'<section><h2>{esc(w["id"])} <small>{esc(w["kind"])} · {size}</small></h2>'
            f'<div class="pair">'
            f'<figure class="light"><img src="{esc(src_l, True)}" alt="{esc(w["alt"], True)}">'
            f'<figcaption>GitHub light</figcaption></figure>'
            f'<figure class="dark"><img src="{esc(src_d, True)}" alt="{esc(w["alt"], True)}">'
            f'<figcaption>GitHub dark</figcaption></figure>'
            f'</div></section>')
    html = f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Pernik preview · {esc(cfg['user'])}</title>
<style>
  body {{ margin: 0; padding: 24px 16px; font: 15px/1.5 -apple-system, 'Segoe UI', sans-serif; background: #f6f8fa; color: #1f2328; }}
  h1 {{ font-size: 20px; margin: 0 0 4px; }} p.note {{ margin: 0 0 24px; color: #57606a; }}
  section {{ margin: 0 0 28px; }} h2 {{ font-size: 15px; margin: 0 0 8px; }} small {{ color: #57606a; font-weight: 400; }}
  .pair {{ display: grid; grid-template-columns: 1fr 1fr; gap: 12px; }}
  @media (max-width: 900px) {{ .pair {{ grid-template-columns: 1fr; }} }}
  figure {{ margin: 0; padding: 16px; border-radius: 6px; border: 1px solid #d0d7de; }}
  figure.light {{ background: {light.page}; }} figure.dark {{ background: {dark.page}; border-color: #30363d; }}
  figure img {{ display: block; max-width: 100%; margin: 0 auto; }}
  figcaption {{ font-size: 12px; margin-top: 8px; color: #57606a; }} .dark figcaption {{ color: #8b949e; }}
</style></head><body>
<h1>Pernik preview</h1>
<p class="note">{len(manifest)} widget(s), theme “{esc(theme.name)}”. Each one is shown the way GitHub shows it in light and dark mode.</p>
{''.join(rows)}
</body></html>
"""
    path = os.path.join(out, 'preview.html')
    with open(path, 'w') as f:
        f.write(html)
    return path
