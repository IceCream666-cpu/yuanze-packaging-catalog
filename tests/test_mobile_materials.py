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
# Fingerprints come from the five PNGs the user approved in liaose轮播背景-v2,
# independently of the generated WebP manifest. A format conversion must not
# replace, crop or repaint any of their pixels.
BANNER_SOURCES = {
    '01-pdrn-capsule-cream': ((1983, 793),
        '3818fa904548b7791ecd376c26e1c869b7170afa617eaa4e9f7f7a4bc0d5b5c3',
        '0e0f4fcd65ead3a2e5ec8631fe39bdd36687439731e1e0ed760a9c7e4e643f5b'),
    '02-body-care-collection': ((2089, 753),
        '86d3a2c22df77a685a5156bed158f26a94b9d24f76207b3abae1e3d005c44ab1',
        '498cdb0f59ab7afc12220aa0f7d83f934642678753e579ec116605cda6e8962e'),
    '03-cherry-blossom-gift-set': ((2048, 768),
        '87f24d77d3be6bcee56110e54c32ce64a7762c67a3f701f65369dcaace166ede',
        '5b2164119407bc5b58b0d001b80b65244492570523adf4eb0def947f6d3dbfde'),
    '04-hand-care-collection': ((2048, 768),
        '6c1fdc30a0a101568a55fd8af0cbad8c3046f46a216e876711e721bf9058971a',
        '86d6af779261ec9fdc71c462ae7c354eb4a711186feb6bf60be1091a2130b792'),
    '05-daylight-still': ((1983, 793),
        'eb960f954ece99683107325c1cf50e2b8cb5558d4d4dd2dca26f31ce7313ecd8',
        '17ba5afd2e75474540c93b2a23f5084bba048a72232dbdeddec43fe49ed9b4cd'),
}
BANNER_PATHS = {f'poster-banners/{name}.webp' for name in BANNER_SOURCES}


class CompanyMaterials(unittest.TestCase):
    def test_previews_have_a_size_budget_and_verified_originals(self):
        manifest = json.loads((ASSETS / 'manifest.json').read_text())
        entries = {item['path']: item for item in manifest['files']}
        previews = [item for item in manifest['files'] if item['kind'] == 'showroom-preview']
        self.assertEqual(len(previews), 146)
        for item in previews:
            with self.subTest(path=item['path']):
                original = entries[item['source']]
                self.assertEqual(item['sourceSha256'], original['sha256'])
                self.assertLessEqual(max(item['width'], item['height']), item['maxEdge'])
                self.assertLess(item['bytes'], 45_000 if item['maxEdge'] == 512 else 170_000)
                self.assertAlmostEqual(item['width'] / item['height'],
                                       original['width'] / original['height'], delta=.01)
                with Image.open(ASSETS / item['path']) as image:
                    self.assertEqual(image.mode, 'RGB')
                    self.assertFalse(image.getexif())
                    self.assertNotIn('icc_profile', image.info)

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
                    self.assertIn(item['kind'], {'poster-lossless', 'poster-thumbnail', 'banner-lossless', 'showroom-preview'})
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

    def test_october15_batch_uses_replacement_and_preserves_pixel_identity(self):
        report = json.loads((ROOT / 'docs/产品海报素材清单.json').read_text())
        batch = [item for item in report['items'] if item['source'].get('receivedAt') == '2026-10-15']
        self.assertEqual(len(batch), 14)
        self.assertEqual(batch[0]['id'], 'poster-042')
        self.assertEqual(batch[0]['source']['filename'], 'codex-clipboard-600d61bb-5348-44c1-9a31-cb87435836c4.png')
        self.assertEqual(batch[0]['title']['en'], 'liaose Woodland body wash')
        self.assertNotIn('84dd12c393741e2a9fe27750eca17584.jpg', json.dumps(report))
        self.assertEqual([x['category'] for x in batch].count('hair'), 8)

    def test_poster_sources_deduplication_and_customer_metadata_are_traceable(self):
        report = json.loads((ROOT / 'docs/产品海报素材清单.json').read_text())
        manifest = json.loads((ASSETS / 'manifest.json').read_text())
        assignment = re.fullmatch(r'\s*(?:/\*.*?\*/\s*)*window\.YuanzeProductPosters\s*=\s*(\{.*\});\s*',
                                  (PREVIEW / 'product-posters.js').read_text(), re.DOTALL)
        self.assertIsNotNone(assignment, 'Poster data must be a standalone JSON-compatible assignment')
        catalog = json.loads(assignment[1])
        self.assertEqual((report['archiveCount'], report['directImageCount'],
                          report['inputImageCount'], report['uniqueImageCount']), (3, 39, 80, 78))
        archived_ids = {f'poster-{index:03d}' for index in range(1, 32)}
        attachment_ids = {f'poster-{index:03d}' for index in range(32, 71)}
        generated_ids = {f'poster-{index:03d}' for index in range(71, 79)}
        expected_ids = archived_ids | attachment_ids | generated_ids
        removed_ids = {f'poster-{index:03d}' for index in range(15, 32)}
        # The October source inventory ends at 078. The November release added Body Care Duo.
        active_ids = (expected_ids - removed_ids) | {'poster-079'}
        self.assertEqual((report['activeImageCount'], report['removedImageCount']), (61, 17))
        self.assertEqual(len(report['items']), 78)
        self.assertEqual({item['id'] for item in report['items']}, expected_ids)
        self.assertEqual(len(catalog['items']), 62)
        self.assertEqual({item['id'] for item in catalog['items']}, active_ids)
        customer_items = {item['id']: item for item in catalog['items']}
        self.assertEqual(len(catalog['categories']), len({category['id'] for category in catalog['categories']}))
        category_ids = {category['id'] for category in catalog['categories']}
        for category in catalog['categories']:
            self.assertTrue(category['zh'].strip())
            self.assertTrue(category['en'].strip())

        entries = {item['path']: item for item in manifest['files']}
        self.assertEqual(customer_items['poster-079'], {
            'id': 'poster-079', 'category': 'sets',
            'title': {'zh': 'liaose 圆盒身体护理双瓶套装', 'en': 'liaose Body Care Duo'},
            'src': 'assets/posters/poster-079.webp', 'thumbnail': 'assets/posters/poster-079-thumb.webp',
            'width': 1024, 'height': 1536,
        })
        duo = entries['posters/poster-079.webp']
        self.assertEqual(duo['originalSha256'], '3ba45666920db6fbed2fd7bf0a5d14bed99e5d28d5c5ddba55c9bdb37a6c6fe9')
        self.assertEqual(duo['sha256'], 'd8e838c02df715bb60536d6f18c9dbbdb09f98d20e4c1c11dc9772cdd6c6da3f')
        with Image.open(ASSETS / duo['path']) as image:
            self.assertEqual(hashlib.sha256(image.convert('RGB').tobytes()).hexdigest(),
                             'dc92aaf53d0df8d852a64c0078ee8dba9a13b596a153d9823c4c1322b06d19b0')
        expected_poster_paths = {f'posters/{poster_id}{suffix}.webp'
                                 for poster_id in active_ids for suffix in ('', '-thumb')}
        self.assertEqual({name for name,item in entries.items() if item['kind'] != 'showroom-preview'}, COMPANY_PATHS | expected_poster_paths | BANNER_PATHS)
        sources, hashes, pixel_hashes, archives = set(), set(), set(), set()
        archived_posters, attached_posters, attachments = set(), set(), set()
        for item in report['items']:
            with self.subTest(poster=item['id']):
                source = item['source']
                self.assertRegex(source['sha256'], r'^[a-f0-9]{64}$')
                self.assertRegex(source['pixelsHash'], r'^[a-f0-9]{64}$')
                self.assertNotIn(source['sha256'], hashes)
                hashes.add(source['sha256'])
                self.assertNotIn(source['pixelsHash'], pixel_hashes)
                pixel_hashes.add(source['pixelsHash'])
                self.assertGreater(source['bytes'], 0)
                self.assertGreater(source['width'], 0)
                self.assertGreater(source['height'], 0)
                if item['id'] in attachment_ids:
                    attached_posters.add(item['id'])
                    self.assertEqual(source['kind'], 'attachment')
                    self.assertEqual(source['receivedAt'], '2026-10-22' if int(item['id'].split('-')[1]) >= 56 else '2026-10-15' if int(item['id'].split('-')[1]) >= 42 else '2026-10-07')
                    self.assertTrue(source['filename'].strip())
                    self.assertEqual(Path(source['filename']).name, source['filename'])
                    self.assertNotIn('archive', source)
                    self.assertNotIn('member', source)
                    self.assertEqual(item['duplicates'], [])
                    origin = ('attachment', source['receivedAt'], source['filename'])
                    self.assertNotIn(origin, sources)
                    sources.add(origin)
                    attachments.add(origin)
                elif item['id'] in generated_ids:
                    self.assertEqual(source['kind'], 'user-approved-generated-artwork')
                    self.assertEqual(source['receivedAt'], '2026-10-24' if item['id']=='poster-071' else '2026-10-26')
                    self.assertEqual(item['duplicates'], [])
                    sources.add(('generated', source['receivedAt'], source['filename']))
                else:
                    archived_posters.add(item['id'])
                    self.assertNotIn('kind', source)
                    for occurrence in [source, *item['duplicates']]:
                        self.assertTrue(occurrence['archive'].strip())
                        self.assertTrue(occurrence['member'].strip())
                        origin = ('archive', occurrence['archive'], occurrence['member'])
                        self.assertNotIn(origin, sources)
                        sources.add(origin)
                        archives.add(occurrence['archive'])
                self.assertEqual(item['image'], f"posters/{item['id']}.webp")
                self.assertEqual(item['thumbnail'], f"posters/{item['id']}-thumb.webp")
                self.assertIn(item['category'], category_ids)
                self.assertEqual(set(item['title']), {'zh', 'en'})
                self.assertTrue(all(value.strip() for value in item['title'].values()))
                if item['id'] in removed_ids:
                    self.assertEqual(item['removedAt'], '2026-10-07')
                    self.assertEqual(item['removalReason'], '用户要求删除同系列女性模特横版海报')
                    self.assertNotIn(item['id'], customer_items)
                    for name in (item['image'], item['thumbnail']):
                        self.assertNotIn(name, entries)
                        self.assertFalse((ASSETS / name).exists())
                        self.assertFalse((ASSETS / name).is_symlink())
                    continue
                self.assertNotIn('removedAt', item)
                self.assertNotIn('removalReason', item)
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
        self.assertEqual(len(attachments), report['directImageCount'])
        self.assertEqual(archived_posters, archived_ids)
        self.assertEqual(attached_posters, attachment_ids)
        self.assertEqual(len(sources - attachments), 41)

    def test_banner_webps_preserve_the_five_approved_pngs_without_resizing_or_metadata(self):
        manifest = json.loads((ASSETS / 'manifest.json').read_text())
        report = json.loads((ROOT / 'docs/客户端轮播背景清单.json').read_text())
        entries = {item['path']: item for item in manifest['files'] if item['kind'] == 'banner-lossless'}
        self.assertEqual(set(entries), BANNER_PATHS)
        self.assertEqual(len(report['files']), 5)
        self.assertEqual({item['path']: item for item in report['files']}, entries)
        for name, (dimensions, source_hash, pixels_hash) in BANNER_SOURCES.items():
            with self.subTest(banner=name):
                entry = entries[f'poster-banners/{name}.webp']
                self.assertEqual(entry['originalName'], name + '.png')
                self.assertEqual(entry['originalSha256'], source_hash)
                self.assertEqual(entry['originalPixelsSha256'], pixels_hash)
                self.assertEqual((entry['width'], entry['height']), dimensions)
                with Image.open(ASSETS / entry['path']) as image:
                    self.assertEqual(image.format, 'WEBP')
                    self.assertEqual(image.size, dimensions)
                    self.assertFalse(getattr(image, 'is_animated', False))
                    self.assertFalse(image.getexif())
                    self.assertFalse({'exif', 'xmp', 'icc_profile'}.intersection(image.info))
                    self.assertEqual(hashlib.sha256(image.convert('RGB').tobytes()).hexdigest(), pixels_hash)


if __name__ == '__main__':
    unittest.main()
