"""Verify that portable company preview files remain intact and self-contained."""
import hashlib
import json
from pathlib import Path
import re
import unittest

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
PREVIEW = ROOT / 'docs/mobile-client-preview'
ASSETS = PREVIEW / 'assets'
COMPANY_PATHS = {'reception.png', 'showroom.png', 'yuanze-mark.svg'} | {
    f'certificates/{certificate}.{extension}'
    for certificate in ('gmpc-en', 'gmpc-zh', 'iso22716-en', 'iso22716-zh')
    for extension in ('pdf', 'png')
}


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
                elif item['kind'] == 'faithful-pdf-render':
                    self.assertTrue((ASSETS / item['sourcePdf']).is_file())
                else:
                    self.assertIn(item['kind'], {'poster-lossless', 'poster-thumbnail'})
                if path.suffix in {'.png', '.webp'}:
                    with Image.open(path) as image:
                        self.assertEqual(image.size, (item['width'], item['height']))
                        image.verify()
                if path.suffix == '.pdf':
                    self.assertTrue(data.startswith(b'%PDF-'))
        self.assertEqual({path.name for path in (ASSETS / 'certificates').glob('*.pdf')},
                         {'gmpc-en.pdf', 'gmpc-zh.pdf', 'iso22716-en.pdf', 'iso22716-zh.pdf'})
        self.assertEqual({p.relative_to(ASSETS).as_posix() for p in ASSETS.rglob('*')
                          if p.is_file() and p.name != 'manifest.json'}, paths)
        self.assertEqual({item['path'] for item in manifest['files']
                          if item['kind'] in {'unchanged-original', 'faithful-pdf-render'}}, COMPANY_PATHS)

    def test_poster_sources_deduplication_and_customer_metadata_are_traceable(self):
        report = json.loads((ROOT / 'docs/产品海报素材清单.json').read_text())
        manifest = json.loads((ASSETS / 'manifest.json').read_text())
        assignment = re.fullmatch(r'\s*(?:/\*.*?\*/\s*)*window\.YuanzeProductPosters\s*=\s*(\{.*\});\s*',
                                  (PREVIEW / 'product-posters.js').read_text(), re.DOTALL)
        self.assertIsNotNone(assignment, 'Poster data must be a standalone JSON-compatible assignment')
        catalog = json.loads(assignment[1])
        self.assertEqual((report['archiveCount'], report['inputImageCount'], report['uniqueImageCount']), (3, 33, 31))
        expected_ids = {f'poster-{index:03d}' for index in range(1, 32)}
        self.assertEqual(len(report['items']), 31)
        self.assertEqual({item['id'] for item in report['items']}, expected_ids)
        self.assertEqual(len(catalog['items']), 31)
        self.assertEqual({item['id'] for item in catalog['items']}, expected_ids)
        customer_items = {item['id']: item for item in catalog['items']}
        self.assertEqual(len(catalog['categories']), len({category['id'] for category in catalog['categories']}))
        category_ids = {category['id'] for category in catalog['categories']}
        for category in catalog['categories']:
            self.assertTrue(category['zh'].strip())
            self.assertTrue(category['en'].strip())

        entries = {item['path']: item for item in manifest['files']}
        expected_poster_paths = {f'posters/{poster_id}{suffix}.webp'
                                 for poster_id in expected_ids for suffix in ('', '-thumb')}
        self.assertEqual(set(entries), COMPANY_PATHS | expected_poster_paths)
        sources, hashes, archives = set(), set(), set()
        for item in report['items']:
            with self.subTest(poster=item['id']):
                source = item['source']
                self.assertRegex(source['sha256'], r'^[a-f0-9]{64}$')
                self.assertRegex(source['pixelsHash'], r'^[a-f0-9]{64}$')
                self.assertNotIn(source['sha256'], hashes)
                hashes.add(source['sha256'])
                self.assertGreater(source['bytes'], 0)
                self.assertGreater(source['width'], 0)
                self.assertGreater(source['height'], 0)
                for occurrence in [source, *item['duplicates']]:
                    origin = (occurrence['archive'], occurrence['member'])
                    self.assertNotIn(origin, sources)
                    sources.add(origin)
                    archives.add(occurrence['archive'])
                self.assertEqual(item['image'], f"posters/{item['id']}.webp")
                self.assertEqual(item['thumbnail'], f"posters/{item['id']}-thumb.webp")
                customer = customer_items[item['id']]
                self.assertEqual(set(customer), {'id', 'category', 'title', 'src', 'thumbnail', 'width', 'height'})
                self.assertIn(customer['category'], category_ids)
                self.assertEqual(customer['category'], item['category'])
                self.assertEqual(customer['title'], item['title'])
                self.assertEqual(set(customer['title']), {'zh', 'en'})
                self.assertTrue(all(value.strip() for value in customer['title'].values()))
                self.assertEqual(customer['src'], 'assets/' + item['image'])
                self.assertEqual(customer['thumbnail'], 'assets/' + item['thumbnail'])
                self.assertEqual((customer['width'], customer['height']), (source['width'], source['height']))

                full, thumb = entries[item['image']], entries[item['thumbnail']]
                for entry, kind in [(full, 'poster-lossless'), (thumb, 'poster-thumbnail')]:
                    self.assertEqual(entry['kind'], kind)
                    self.assertEqual(entry['posterId'], item['id'])
                    self.assertEqual(entry['originalSha256'], source['sha256'])
                    with Image.open(ASSETS / entry['path']) as image:
                        self.assertEqual(image.format, 'WEBP')
                        self.assertEqual(image.size, (entry['width'], entry['height']))
                        self.assertFalse(getattr(image, 'is_animated', False))
                        self.assertFalse(image.getexif())
                        self.assertFalse({'exif', 'xmp', 'icc_profile'}.intersection(image.info))
                        if kind == 'poster-lossless':
                            self.assertEqual(image.size, (source['width'], source['height']))
                            self.assertEqual(entry['originalPixelsSha256'], source['pixelsHash'])
                            self.assertEqual(hashlib.sha256(image.convert('RGB').tobytes()).hexdigest(), source['pixelsHash'])
                        else:
                            self.assertLessEqual(max(image.size), 640)
                            self.assertLessEqual(image.width, source['width'])
                            self.assertLessEqual(image.height, source['height'])
                            # Resizing may round either dimension by one pixel.
                            self.assertLessEqual(abs(image.width * source['height'] - image.height * source['width']),
                                                 max(source['width'], source['height']))
                self.assertEqual(thumb['sourceImage'], item['image'])
        self.assertEqual(len(sources), report['inputImageCount'])
        self.assertEqual(len(archives), report['archiveCount'])


if __name__ == '__main__':
    unittest.main()
