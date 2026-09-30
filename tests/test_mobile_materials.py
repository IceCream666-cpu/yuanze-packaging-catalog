"""Verify that portable company preview files remain intact and self-contained."""
import hashlib
import json
from pathlib import Path
import unittest

from PIL import Image

ASSETS = Path(__file__).resolve().parents[1] / 'docs/mobile-client-preview/assets'


class CompanyMaterials(unittest.TestCase):
    def test_originals_and_pdf_renders_match_recorded_materials(self):
        manifest = json.loads((ASSETS / 'manifest.json').read_text())
        paths = set()
        for item in manifest['files']:
            with self.subTest(path=item['path']):
                path = (ASSETS / item['path']).resolve()
                self.assertTrue(path.is_relative_to(ASSETS.resolve()))
                self.assertNotIn(item['path'], paths)
                paths.add(item['path'])
                data = path.read_bytes()
                self.assertEqual(hashlib.sha256(data).hexdigest(), item['sha256'])
                self.assertEqual(len(data), item['bytes'])
                if item['kind'] == 'unchanged-original':
                    self.assertEqual(item['originalSha256'], item['sha256'])
                else:
                    self.assertEqual(item['kind'], 'faithful-pdf-render')
                    self.assertTrue((ASSETS / item['sourcePdf']).is_file())
                if path.suffix == '.png':
                    with Image.open(path) as image:
                        self.assertEqual(image.size, (item['width'], item['height']))
                        image.verify()
                if path.suffix == '.pdf':
                    self.assertTrue(data.startswith(b'%PDF-'))
        self.assertEqual({path.name for path in (ASSETS / 'certificates').glob('*.pdf')},
                         {'gmpc-en.pdf', 'gmpc-zh.pdf', 'iso22716-en.pdf', 'iso22716-zh.pdf'})
        self.assertEqual({p.relative_to(ASSETS).as_posix() for p in ASSETS.rglob('*')
                          if p.is_file() and p.name != 'manifest.json'}, paths)


if __name__ == '__main__':
    unittest.main()
