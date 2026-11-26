"""garden widget tests (standard library only):  python3 -m unittest tests.test_garden

Logos are faked (a plain square) so the tests never touch the network or the icon cache.
"""
import math
import os
import re
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pernik.check import check_svg  # noqa: E402
from pernik.theme import load_theme  # noqa: E402
from pernik.widgets import Context, load_all  # noqa: E402
from pernik.widgets import _garden as G  # noqa: E402

SQUARE = 'M3 3h18v18H3z'

# the profile this widget was designed for (logos omitted)
USER_TREES = [
    {'name': 'languages & frameworks', 'icons': ['go', 'python', 'rust', 'nodejs', 'typescript', 'echo', 'gin',
                                                 'fiber', 'fastapi', 'flask', 'nextdotjs', 'react']},
    {'name': 'data', 'icons': ['mysql', 'postgresql', 'mongodb', 'redis', 'kafka', 'vertica', 'dbeaver']},
    {'name': 'infra & tools', 'icons': ['docker', 'kubernetes', 'linux', 'aws', 'googlecloud', 'cloudflare', 'grafana',
                                        'uptimerobot', 'git', 'postman', 'swagger', 'termius']},
    {'name': 'ai & editors', 'icons': ['claude', 'codex', 'grok', 'deepseek', 'aws bedrock', 'ibm watson', 'vscode',
                                       'antigravity', 'kiro']},
]


def fake_resolve(raw, ctx, idx, logos, say):
    return raw.title(), SQUARE, (0, 0, 24, 24), None, None


class GardenTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls._saved = G._index, G.resolve
        G._index = lambda root, say: {}
        G.resolve = fake_resolve
        cls.spec = load_all()['garden']
        cls.tmp = tempfile.TemporaryDirectory()

    @classmethod
    def tearDownClass(cls):
        G._index, G.resolve = cls._saved
        cls.tmp.cleanup()

    def build(self, theme='komik', **opts):
        """{mode: Out} plus the messages the widget logged."""
        th = load_theme(theme)
        logs, outs = [], {}
        for mode in ('light', 'dark'):
            ctx = Context(mode=mode, pal=th.mode(mode), theme=th, root=self.tmp.name,
                          out=self.tmp.name, user='octocat', widget_id='kebun')
            ctx.log = lambda *a: logs.append(' '.join(map(str, a)))
            outs[mode] = self.spec.fn(dict(self.spec.defaults, **opts), ctx)
        for mode, out in outs.items():
            path = os.path.join(self.tmp.name, f'kebun-{mode}.svg')
            with open(path, 'w') as f:
                f.write(out.svg)
            errs, _ = check_svg(path)
            self.assertEqual(errs, [], f'{mode}: {errs}')
        self.assertNotEqual(outs['light'].svg, outs['dark'].svg)
        self.assertFalse(outs['light'].same)
        return outs, logs

    @staticmethod
    def fruits(svg):
        """Fruit centres on the trees (plain fruits and the regrowing picked ones) and the radius."""
        r = int(re.search(r'<g id="fb"><circle r="(\d+)"', svg).group(1))
        pts = [(int(x), int(y)) for x, y in re.findall(r'<use href="#fb" x="(-?\d+)" y="(-?\d+)"/>', svg)
               if (x, y) != ('0', '0')]
        pts += [(int(x), int(y)) for x, y in re.findall(r'translate\((-?\d+) (-?\d+)\)"><g class="gr\d', svg)]
        return pts, r

    def assertGardenSound(self, svg, count):
        pts, r = self.fruits(svg)
        self.assertEqual(len(pts), count)
        self.assertGreaterEqual(r, 12, 'fruit too small for a legible logo')
        for i, p in enumerate(pts):
            for q in pts[i + 1:]:
                self.assertGreaterEqual(math.hypot(p[0] - q[0], p[1] - q[1]), 2 * r, f'fruits overlap at {p} {q}')
        w, h = (int(v) for v in re.search(r'width="(\d+)" height="(\d+)"', svg).groups())
        self.assertEqual(w, 900)
        self.assertLessEqual(h, 480)
        for x, y in pts:
            self.assertTrue(r <= x <= w - r and r <= y <= h - r, f'fruit off the card at {x},{y}')

    # ------------------------------------------------------------------ cases
    def test_defaults(self):
        outs, logs = self.build()
        n = sum(len(t['icons']) for t in self.spec.defaults['tree'])
        self.assertGardenSound(outs['light'].svg, n)
        self.assertIn('languages (mango tree): Python', outs['light'].alt)
        self.assertIn('@keyframes gA', outs['light'].svg)
        self.assertIn('prefers-reduced-motion', outs['light'].svg)

    def test_user_scene(self):
        outs, logs = self.build(tree=USER_TREES)
        svg = outs['light'].svg
        self.assertGardenSound(svg, 40)
        for kind in ('mango tree', 'coconut palm', 'rambutan tree', 'banana plant'):
            self.assertIn(kind, outs['light'].alt)
        self.assertIn('Kafka', outs['light'].alt)
        picks = set(re.findall(r'class="gf(\d)"', svg))
        self.assertTrue(1 <= len(picks) <= G.MAX_PICKS)
        loop = float(re.search(r'animation:gA ([\d.]+)s', svg).group(1))
        self.assertAlmostEqual(loop, G.CYCLE * len(picks))
        # the still frame hides every copy in the hand
        for c in picks:
            self.assertRegex(svg, r'\.gf%s\{transform:scale\(0\);animation' % c)
        self.assertEqual(logs, [])

    def test_one_tree(self):
        outs, _ = self.build(tree=[{'name': 'tools', 'icons': ['git', 'docker']}])
        self.assertGardenSound(outs['light'].svg, 2)

    def test_six_trees(self):
        trees = [{'name': f'group {i}', 'icons': [f'tool{i}{j}' for j in range(10)]} for i in range(6)]
        outs, logs = self.build(tree=trees)
        self.assertGardenSound(outs['light'].svg, 60)
        self.assertEqual(logs, [])

    def test_too_many_trees(self):
        trees = [{'name': f'g{i}', 'icons': ['a', 'b']} for i in range(8)]
        outs, logs = self.build(tree=trees)
        self.assertGardenSound(outs['light'].svg, 12)
        self.assertTrue(any('room for 6' in m for m in logs))

    def test_too_many_fruits(self):
        outs, logs = self.build(tree=[{'name': 'lots', 'tree': 'rambutan', 'icons': [f't{i}' for i in range(25)]}])
        self.assertGardenSound(outs['light'].svg, G.MAX_FRUIT)
        self.assertTrue(any('first 18' in m for m in logs))

    def test_every_tree_type_full(self):
        for kind in G.KINDS:
            with self.subTest(kind=kind):
                outs, _ = self.build(tree=[{'name': kind, 'tree': kind, 'icons': [f't{i}' for i in range(18)]}] * 2)
                self.assertGardenSound(outs['light'].svg, 36)

    def test_harvest_off(self):
        outs, _ = self.build(harvest=False)
        svg = outs['light'].svg
        self.assertIn('gbk', svg)                       # the banana is there...
        self.assertNotIn('@keyframes gA', svg)          # ...but still
        self.assertNotIn('class="gf', svg)
        self.assertGardenSound(svg, 8)

    def test_no_mascot(self):
        outs, _ = self.build(mascot='none')
        svg = outs['light'].svg
        self.assertNotIn('gbk', svg)
        self.assertNotIn('@keyframes', svg.replace('@keyframes stamp', ''))
        self.assertNotIn('picks fruit', outs['light'].svg)

    def test_unknown_tree_type(self):
        outs, logs = self.build(tree=[{'name': 'x', 'tree': 'durian', 'icons': ['a', 'b', 'c']}])
        self.assertTrue(any('unknown tree "durian"' in m for m in logs))
        self.assertIn('(mango tree)', outs['light'].alt)    # first tree falls back to mangga

    def test_bad_options(self):
        outs, logs = self.build(tree='nope', mascot='cat', harvest='no')
        self.assertTrue(any('mascot' in m for m in logs))
        self.assertTrue(any('list' in m for m in logs))
        self.assertGardenSound(outs['light'].svg, 0)
        outs, _ = self.build(tree=[{'name': 'empty'}, {'icons': 'go, rust'}])
        self.assertGardenSound(outs['light'].svg, 2)

    def test_sticker_theme(self):
        outs, _ = self.build(theme='stiker')
        self.assertIn('#161B22', outs['dark'].svg)          # a night print, not a bright card
        self.assertGardenSound(outs['dark'].svg, 8)


if __name__ == '__main__':
    unittest.main()
