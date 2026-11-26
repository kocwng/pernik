"""The playground site that tools/build_site.py makes:  python3 -m unittest discover -s tests"""
import importlib.util
import json
import os
import subprocess
import sys
import tempfile
import unittest
import zipfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from pernik.check import check_svg  # noqa: E402
from pernik.theme import THEMES  # noqa: E402
from pernik.widgets import load_all  # noqa: E402


def load_tool():
    spec = importlib.util.spec_from_file_location('build_site', os.path.join(ROOT, 'tools', 'build_site.py'))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class SiteTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.site, cls.size, cls.problems = load_tool().build_site(os.path.join(cls.tmp.name, 'site'))
        with open(os.path.join(cls.site, 'gallery.json'), encoding='utf-8') as f:
            cls.gallery = json.load(f)

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def test_files(self):
        for name in ('index.html', 'demo.mp3', 'pernik.zip', 'gallery.json', '.nojekyll'):
            self.assertTrue(os.path.isfile(os.path.join(self.site, name)), name)
        self.assertEqual(self.problems, [])

    def test_zip_imports(self):
        with tempfile.TemporaryDirectory() as d:
            with zipfile.ZipFile(os.path.join(self.site, 'pernik.zip')) as z:
                names = z.namelist()
                z.extractall(d)
            self.assertIn('pernik/__init__.py', names)
            self.assertFalse([n for n in names if '__pycache__' in n or n.endswith('.pyc')])
            code = ('import json, pernik\n'
                    'from pernik.widgets import load_all\n'
                    'from pernik.theme import load_theme\n'
                    'load_theme("komik")\n'
                    'print(json.dumps([pernik.__file__, sorted(load_all())]))\n')
            env = dict(os.environ, PYTHONPATH=d)
            r = subprocess.run([sys.executable, '-c', code], cwd=d, env=env,
                               capture_output=True, text=True, timeout=60)
            self.assertEqual(r.returncode, 0, r.stderr)
            where, kinds = json.loads(r.stdout)
            self.assertTrue(os.path.realpath(where).startswith(os.path.realpath(d)), where)
            self.assertEqual(kinds, sorted(load_all()))

    def test_gallery_lists_everything(self):
        g = self.gallery
        kinds = set(load_all())
        themes = {f[:-5] for f in os.listdir(THEMES) if f.endswith('.toml')}
        self.assertTrue(g['version'])
        self.assertEqual(set(g['widgets']), kinds)
        self.assertEqual({t['name'] for t in g['themes']}, themes)
        self.assertEqual(set(g['prerender']), themes)
        for t in g['themes']:
            self.assertEqual(set(t['swatch']), {'light', 'dark'})
        for kind, w in g['widgets'].items():
            self.assertIsInstance(w['defaults'], dict, kind)
            self.assertIsInstance(w['heavy'], bool, kind)
        for name in ('komik', 'stiker'):           # always drawn in full
            self.assertEqual({k.split(':')[0] for k in g['prerender'][name]}, kinds, name)
        for name, widgets in g['prerender'].items():
            self.assertTrue({'hero', 'divider'} <= set(widgets), name)

    def test_prerendered_svgs_are_safe(self):
        with tempfile.TemporaryDirectory() as d:
            for theme, widgets in self.gallery['prerender'].items():
                for kind, w in widgets.items():
                    self.assertTrue(w['alt'], f'{theme}/{kind} has no alt')
                    for mode in ('light', 'dark'):
                        path = os.path.join(d, f'{theme}-{kind}-{mode}.svg')
                        with open(path, 'w', encoding='utf-8') as f:
                            f.write(w[mode])
                        errs, _ = check_svg(path)
                        self.assertEqual(errs, [], f'{theme}/{kind}/{mode}: {errs}')


if __name__ == '__main__':
    unittest.main()
