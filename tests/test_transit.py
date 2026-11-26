"""transit widget tests (offline: a fake Simple Icons cache and fake logo files in a temp folder).

    python3 -m unittest tests.test_transit
"""
import json
import math
import os
import re
import sys
import tempfile
import unittest
import xml.dom.minidom

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pernik.check import check_svg  # noqa: E402
from pernik.theme import load_theme  # noqa: E402
from pernik.widgets import Context, load_all  # noqa: E402
from pernik.widgets.stack import SI_VERSION  # noqa: E402

# the four groups of the user's profile (profile-pernik.toml)
USER_LINES = [
    {'name': 'languages & frameworks',
     'icons': ['go', 'python', 'rust', 'nodejs', 'typescript', 'echo', 'gin', 'fiber', 'fastapi', 'flask',
               'nextdotjs', 'react'],
     'logos': {'echo': 'assets/logos/echo.svg', 'fiber': 'assets/logos/fiber.svg'}},
    {'name': 'data',
     'icons': ['mysql', 'postgresql', 'mongodb', 'redis', 'kafka', 'vertica', 'dbeaver'],
     'logos': {'vertica': 'assets/logos/vertica.svg'}},
    {'name': 'infra & tools',
     'icons': ['docker', 'kubernetes', 'linux', 'aws', 'googlecloud', 'cloudflare', 'grafana', 'uptimerobot',
               'git', 'postman', 'swagger', 'termius'],
     'logos': {'aws': 'assets/logos/aws.svg', 'uptimerobot': 'assets/logos/uptimerobot.svg'}},
    {'name': 'ai & editors',
     'icons': ['claude', 'codex', 'grok', 'deepseek', 'aws bedrock', 'ibm watson', 'vscode', 'antigravity', 'kiro'],
     'logos': {'codex': 'assets/logos/codex.svg', 'grok': 'assets/logos/grok.svg',
               'aws bedrock': 'assets/logos/aws-bedrock.svg', 'ibm watson': 'assets/logos/ibm-watson.svg',
               'vscode': 'assets/logos/vscode.svg', 'antigravity': 'assets/logos/antigravity.svg',
               'kiro': 'assets/logos/kiro.svg'}},
]
SLUGS = {'go': 'Go', 'python': 'Python', 'rust': 'Rust', 'nodedotjs': 'Node.js', 'typescript': 'TypeScript',
         'gin': 'Gin', 'fastapi': 'FastAPI', 'flask': 'Flask', 'nextdotjs': 'Next.js', 'react': 'React',
         'mysql': 'MySQL', 'postgresql': 'PostgreSQL', 'mongodb': 'MongoDB', 'redis': 'Redis',
         'apachekafka': 'Apache Kafka', 'dbeaver': 'DBeaver', 'docker': 'Docker', 'kubernetes': 'Kubernetes',
         'linux': 'Linux', 'googlecloud': 'Google Cloud', 'cloudflare': 'Cloudflare', 'grafana': 'Grafana',
         'git': 'Git', 'postman': 'Postman', 'swagger': 'Swagger', 'termius': 'Termius', 'claude': 'Claude',
         'deepseek': 'DeepSeek'}
# a little logo with curves, a hole and a speck, so the path rewriting gets exercised
ICON = ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24"><path d="M12 0C5.373 0 0 5.373 0 12s5.373 12 '
        '12 12 12-5.373 12-12S18.627 0 12 0zm0 4.5a7.5 7.5 0 1 1 0 15 7.5 7.5 0 0 1 0-15zM11.9 11.9h.1v.1h-.1z'
        'M6 11h12v2H6z"/></svg>')


class TransitTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        root = cls.root = cls.tmp.name
        cache = os.path.join(root, '.pernik-cache', 'simple-icons', SI_VERSION)
        os.makedirs(cache)
        with open(os.path.join(cache, 'index.json'), 'w') as f:
            json.dump({s: [t, '336699'] for s, t in SLUGS.items()}, f)
        for s in SLUGS:
            with open(os.path.join(cache, f'{s}.svg'), 'w') as f:
                f.write(ICON)
        os.makedirs(os.path.join(root, 'assets', 'logos'))
        for line in USER_LINES:
            for rel in line['logos'].values():
                box = '0 0 438 89' if 'vertica' in rel else '0 0 128 128'     # vertica is a wide wordmark
                with open(os.path.join(root, rel), 'w') as f:
                    f.write(f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="{box}"><path d="M8 8h40v40H8z"/></svg>')
        cls.spec = load_all()['transit']

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def run_widget(self, theme='komik', **opts):
        """{mode: (Out, svg path, log lines)} for both prints."""
        th = load_theme(theme)
        res = {}
        for mode in ('light', 'dark'):
            ctx = Context(mode=mode, pal=th.mode(mode), theme=th, root=self.root, out=self.root,
                          user='kocwng', widget_id='peta')
            logs = []
            ctx.log = lambda *a, logs=logs: logs.append(' '.join(map(str, a)))
            out = self.spec.fn(dict(self.spec.defaults, **opts), ctx)
            path = os.path.join(self.root, f'peta-{theme}-{mode}.svg')
            with open(path, 'w') as f:
                f.write(out.svg)
            res[mode] = (out, path, logs)
        return res

    def assertClean(self, res):
        for mode, (out, path, _) in res.items():
            errs, _ = check_svg(path)
            self.assertEqual(errs, [], f'{mode}: {errs}')
            xml.dom.minidom.parseString(out.svg)
            self.assertNotIn('http://', out.svg.replace('http://www.w3.org/2000/svg', ''))
            self.assertIn('prefers-reduced-motion', out.svg)

    def stations(self, svg):
        return [(float(x), float(y), float(r)) for x, y, r in
                re.findall(r'<circle class="sb" cx="([\d.]+)" cy="([\d.]+)" r="([\d.]+)"', svg)]

    def assertNoOverlap(self, svg):
        pts = self.stations(svg)
        for i, a in enumerate(pts):
            for b in pts[i + 1:]:
                self.assertGreater(math.hypot(a[0] - b[0], a[1] - b[1]), a[2] + b[2], f'{a} overlaps {b}')
        w, h = (int(v) for v in re.search(r'width="(\d+)" height="(\d+)"', svg).groups())
        for x, y, r in pts:
            self.assertTrue(8 + r <= x <= w - 8 - r and 8 + r <= y <= h - 8 - r, (x, y))
        self.assertEqual(h % 8, 0)

    # ---------------------------------------------------------------- the tests
    def test_defaults(self):
        res = self.run_widget()
        self.assertClean(res)
        out = res['light'][0]
        self.assertIn('languages', out.alt)
        self.assertIn('python', out.alt)
        self.assertIn('PETA STACK', out.svg.upper())
        self.assertIn('offset-path', out.svg)              # the train
        self.assertEqual(len(self.stations(out.svg)), 6)
        self.assertNotEqual(res['light'][0].svg, res['dark'][0].svg)
        self.assertIn('#161B22', res['dark'][0].svg)       # night paper

    def test_user_map(self):
        res = self.run_widget(line=USER_LINES)
        self.assertClean(res)
        svg, alt = res['light'][0].svg, res['light'][0].alt
        self.assertEqual(len(self.stations(svg)), 40)
        self.assertNoOverlap(svg)
        for name in ('line 1 languages & frameworks', 'go', 'kafka', 'google cloud', 'aws bedrock', 'kiro'):
            self.assertIn(name, alt)
        self.assertIn('KOCWNG', svg)                        # the hub carries the username
        self.assertIn('4 lines · 40 stops', svg)
        self.assertEqual(res['light'][2], [])               # nothing to complain about
        self.assertLess(len(svg.encode()), 50 * 1024)

    def test_one_line(self):
        res = self.run_widget(line=[USER_LINES[0]], hub='me!')
        self.assertClean(res)
        svg = res['light'][0].svg
        self.assertEqual(len(self.stations(svg)), 12)
        self.assertNoOverlap(svg)
        self.assertIn('ME!', svg)
        self.assertIn('1 line · 12 stops', svg)

    def test_two_to_six_lines(self):
        pool = [i for line in USER_LINES for i in line['icons']]
        logos = {k: v for line in USER_LINES for k, v in line['logos'].items()}
        for count in (2, 3, 5, 6):
            with self.subTest(lines=count):
                lines = [{'name': f'line {i}', 'icons': pool[i * 6:i * 6 + 4 + i], 'logos': logos} for i in range(count)]
                res = self.run_widget(line=lines)
                self.assertClean(res)
                svg = res['light'][0].svg
                self.assertEqual(len(self.stations(svg)), sum(len(l['icons']) for l in lines))
                self.assertNoOverlap(svg)
                if count >= 5:
                    self.assertIn('stroke-dasharray="9 6"', svg)   # lines 5 and 6 are dashed

    def test_seven_lines_keeps_six(self):
        lines = [{'name': f'l{i}', 'icons': ['go', 'git']} for i in range(7)]
        res = self.run_widget(line=lines)
        self.assertClean(res)
        self.assertEqual(len(self.stations(res['light'][0].svg)), 12)
        self.assertTrue(any('only the first 6' in m for m in res['light'][2]))

    def test_too_many_stops(self):
        icons = list(SLUGS)[:20]
        res = self.run_widget(line=[{'name': 'everything', 'icons': icons}, {'name': 'two', 'icons': ['go']}])
        self.assertClean(res)
        svg = res['light'][0].svg
        self.assertEqual(len(self.stations(svg)), 17)
        self.assertNoOverlap(svg)
        self.assertTrue(any('only the first 16' in m for m in res['light'][2]))
        self.assertEqual(res['dark'][2], [])               # messages only once (light pass)

    def test_train_off(self):
        res = self.run_widget(train=False)
        self.assertClean(res)
        self.assertNotIn('offset-path', res['light'][0].svg)
        self.assertNotIn('class="train"', res['light'][0].svg)

    def test_empty_title(self):
        with_title = self.run_widget()['light'][0].svg
        res = self.run_widget(title='')
        self.assertClean(res)
        svg = res['light'][0].svg
        self.assertNotIn('PETA STACK', svg.upper())
        self.assertNotIn(' stops<', svg)
        h = lambda s: int(re.search(r'height="(\d+)"', s).group(1))
        self.assertLessEqual(h(svg), h(with_title))

    def test_no_lines_and_odd_input(self):
        for line in ([], None, 'nonsense', [{'name': '', 'icons': 'go, git'}, {'icons': []}, 'x']):
            with self.subTest(line=line):
                res = self.run_widget(line=line)
                self.assertClean(res)

    def test_other_themes(self):
        for theme in ('komik-laut', 'stiker', 'pastel', 'sogan'):
            with self.subTest(theme=theme):
                res = self.run_widget(theme=theme, line=USER_LINES[:2])
                self.assertClean(res)
                self.assertNoOverlap(res['light'][0].svg)

    def test_grid_path_keeps_shapes(self):
        from pernik.widgets._transit import grid_path
        d = grid_path('M12 0C5.373 0 0 5.373 0 12s5.373 12 12 12 12-5.373 12-12S18.627 0 12 0z'
                      'M11.9 11.9h.1v.1h-.1z', (0, 0, 24, 24))
        self.assertTrue(d.startswith('M'))
        self.assertNotIn('.', d)                            # whole steps only
        self.assertEqual(d.count('z'), 1)                   # the speck is gone, the circle stays
        self.assertFalse(grid_path('M0 0 L', (0, 0, 24, 24)))     # nothing to draw: a monogram instead


if __name__ == '__main__':
    unittest.main()
