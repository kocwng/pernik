"""Core tests (standard library only):  python3 -m unittest discover -s tests"""
import os
import sys
import tempfile
import textwrap
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pernik.build import build, fill_readme  # noqa: E402
from pernik.check import check_svg  # noqa: E402
from pernik.config import load_config  # noqa: E402
from pernik.theme import load_theme  # noqa: E402
from pernik.widgets import load_all  # noqa: E402


def write(folder, name, text):
    path = os.path.join(folder, name)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'w') as f:
        f.write(textwrap.dedent(text))
    return path


class ThemeTests(unittest.TestCase):
    def test_default_theme_has_both_modes(self):
        th = load_theme('stiker')
        light, dark = th.mode('light'), th.mode('dark')
        self.assertEqual(light.page, '#ffffff')
        self.assertEqual(dark.page, '#0d1117')
        self.assertTrue(light.accents)
        self.assertEqual(light.color('pink'), '#FF5FA2')
        self.assertEqual(light.color('#123456'), '#123456')

    def test_extends(self):
        with tempfile.TemporaryDirectory() as d:
            p = write(d, 'mine.toml', '''
                extends = "stiker"
                name = "mine"
                accents = ["#000000"]
                [dark]
                text = "#ff0000"
            ''')
            th = load_theme(p)
            self.assertEqual(th.name, 'mine')
            self.assertEqual(th.mode('dark').text, '#ff0000')
            self.assertEqual(th.mode('dark').page, '#0d1117')   # inherited
            self.assertEqual(th.mode('light').accents, ['#000000'])


class ConfigTests(unittest.TestCase):
    def test_ids_and_errors(self):
        with tempfile.TemporaryDirectory() as d:
            p = write(d, 'pernik.toml', '''
                user = "octocat"
                [[widget]]
                kind = "divider"
                [[widget]]
                id = "x"
                kind = "footer"
            ''')
            cfg = load_config(p)
            self.assertEqual([w['id'] for w in cfg['widgets']], ['divider-1', 'x'])
            self.assertEqual(cfg['user'], 'octocat')
            write(d, 'pernik.toml', '[[widget]]\nid = "a"\nkind = "footer"\n[[widget]]\nid = "a"\nkind = "footer"\n')
            with self.assertRaises(SystemExit):
                load_config(p)


class ReadmeTests(unittest.TestCase):
    def test_fill_only_between_markers(self):
        text = 'top\n<!-- pernik:a -->\nold\n<!-- /pernik:a -->\nbottom\n'
        new, found = fill_readme(text, 'a', 'NEW')
        self.assertTrue(found)
        self.assertEqual(new, 'top\n<!-- pernik:a -->\nNEW\n<!-- /pernik:a -->\nbottom\n')
        same, found = fill_readme(text, 'b', 'NEW')
        self.assertFalse(found)
        self.assertEqual(same, text)


class IconNameTests(unittest.TestCase):
    IDX = {'apachekafka': ['Apache Kafka', '231F20'], 'apachespark': ['Apache Spark', 'E25A1C'],
           'sparkar': ['Spark AR', 'FF5C83'], 'nodedotjs': ['Node.js', '5FA04E'], 'go': ['Go', '00ADD8'],
           'springboot': ['Spring Boot', '6DB33F']}

    def test_names_people_type(self):
        from pernik.widgets.stack import find_icon
        self.assertEqual(find_icon('kafka', self.IDX), ('apachekafka', ''))
        self.assertEqual(find_icon('Apache Kafka', self.IDX), ('apachekafka', ''))
        self.assertEqual(find_icon('Node.js', self.IDX), ('nodedotjs', ''))
        self.assertEqual(find_icon('golang', self.IDX), ('go', ''))
        self.assertEqual(find_icon('Spring Boot', self.IDX), ('springboot', ''))
        slug, hint = find_icon('spark', self.IDX)
        self.assertIsNone(slug)
        self.assertIn('apachespark', hint)
        self.assertEqual(find_icon('aws', self.IDX), (None, ''))

    def test_custom_logo_file(self):
        from pernik.widgets.stack import custom_logo
        with tempfile.TemporaryDirectory() as d:
            write(d, 'assets/x.svg', '<svg viewBox="0 0 100 50"><path d="M0 0h100v50z"/></svg>')
            dpath, box, color = custom_logo(d, {'file': 'assets/x.svg', 'color': '#FF9900'}, print)
            self.assertEqual(box, (0, 0, 100, 50))
            self.assertEqual(color, '#FF9900')
            self.assertIsNone(custom_logo(d, '../outside.svg', lambda *a: None))


class CheckTests(unittest.TestCase):
    def test_flags_unsafe_svg(self):
        with tempfile.TemporaryDirectory() as d:
            bad = write(d, 'bad.svg', '<svg xmlns="http://www.w3.org/2000/svg"><script>x()</script>'
                                      '<image href="https://example.com/a.png"/></svg>')
            problems, _ = check_svg(bad)
            self.assertTrue(any('script' in p for p in problems))
            self.assertTrue(any('outside' in p for p in problems))
            good = write(d, 'good.svg', '<svg xmlns="http://www.w3.org/2000/svg"><title>ok</title></svg>')
            self.assertEqual(check_svg(good), ([], []))


class WidgetTests(unittest.TestCase):
    """Every registered widget builds with its defaults (plus required options) in both modes."""
    REQUIRED = {'mixtape': None}   # needs a song file; covered by its own test

    def test_all_widgets_build(self):
        for theme in ('komik', 'komik-laut', 'stiker', 'sogan'):
            with self.subTest(theme=theme):
                self._build_all(theme)

    def _build_all(self, theme):
        reg = load_all()
        with tempfile.TemporaryDirectory() as d:
            lines = ['user = "octocat"', f'theme = "{theme}"']
            for kind in sorted(reg):
                if kind in self.REQUIRED or kind.startswith('_'):
                    continue
                lines += ['[[widget]]', f'id = "w-{kind}"', f'kind = "{kind}"']
                if kind == 'stack':
                    lines.append('icons = []')
            p = write(d, 'pernik.toml', '\n'.join(lines) + '\n')
            cfg, manifest, problems = build(p, quiet=True)
            self.assertEqual(problems, [])
            for w in manifest:
                for rel in w['files'].values():
                    errs, _ = check_svg(os.path.join(d, rel))
                    self.assertEqual(errs, [], f'{rel}: {errs}')


if __name__ == '__main__':
    unittest.main()
