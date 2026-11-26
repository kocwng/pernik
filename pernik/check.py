"""Checks that generated files will show up properly on GitHub.

GitHub shows README pictures through its image proxy, inside <img>. In that mode an SVG
can't run scripts or load anything from outside, and very large files load slowly.
"""
import os
import re
import xml.dom.minidom

MAX_BYTES = 25 * 1024          # per SVG; bigger files are allowed but warned about
HARD_MAX = 1024 * 1024         # GitHub's proxy struggles past this

BANNED = [
    (r'<script\b', 'contains <script> (GitHub strips it; nothing will run)'),
    (r'<foreignObject\b', 'uses <foreignObject> (not shown inside <img>)'),
    (r'\son[a-z]+\s*=', 'has an on...= event handler (never runs in a README)'),
    (r'(?:href|src)\s*=\s*"(?:https?:)?//', 'links to an outside file (blocked inside <img>)'),
    (r'@import\b', 'uses CSS @import (blocked inside <img>)'),
    (r'@font-face\b[^}]*url\(\s*["\']?(?:https?:)?//', 'loads a web font from outside (blocked)'),
]


def check_svg(path):
    problems, warnings = [], []
    with open(path, 'rb') as f:
        data = f.read()
    try:
        xml.dom.minidom.parseString(data)
    except Exception as e:
        problems.append(f'not valid XML ({e})')
    text = data.decode('utf-8', 'replace')
    for pat, msg in BANNED:
        if re.search(pat, text, re.I):
            problems.append(msg)
    if len(data) > HARD_MAX:
        problems.append(f'{len(data) // 1024} KB is too big for GitHub to show reliably')
    elif len(data) > MAX_BYTES:
        warnings.append(f'{len(data) // 1024} KB (aim for under {MAX_BYTES // 1024} KB so it loads fast)')
    if '<title' not in text:
        warnings.append('has no <title> (screen readers need it)')
    return problems, warnings


def check(cfg, manifest):
    problems = []
    for w in manifest:
        for rel in w['files'].values():
            p, warn = check_svg(os.path.join(cfg['root'], rel))
            for m in p:
                problems.append(f'{rel}: {m}')
                print(f'✗ {rel}: {m}')
            for m in warn:
                print(f'~ {rel}: {m}')
            if not p and not warn:
                print(f'✓ {rel}')
        if not w.get('alt'):
            print(f"~ {w['id']}: no alt text")
    return problems
