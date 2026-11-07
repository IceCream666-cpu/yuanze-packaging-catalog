"""Approved poster source fidelity and approved model and homepage replacement boundaries."""
import hashlib
import json
from pathlib import Path
import unittest
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
CLIENT = ROOT / 'docs/client-motion-demo'
MOBILE = ROOT / 'docs/mobile-client-preview'
PUBLIC = ROOT / 'server-reference/public/showroom'


class SoapCleanDuoPosterTests(unittest.TestCase):
    def test_approved_original_is_pixel_identical_and_all_display_sizes_match(self):
        source = CLIENT / 'model-source/collection/poster-082/soap-clean-duo-v2.png'
        self.assertEqual(hashlib.sha256(source.read_bytes()).hexdigest(),
                         '616ab8db3a22d0c764e0ee47a4c31ef8d57cb575d5d75f24f33ff89a5672eb94')
        with Image.open(source) as original, Image.open(PUBLIC / 'assets/posters/poster-082.webp') as published:
            self.assertEqual(original.size, (1024, 1536))
            self.assertEqual(original.convert('RGB').tobytes(), published.convert('RGB').tobytes())
        sizes = {'assets/posters/poster-082.webp': (1024, 1536),
                 'assets/posters/poster-082-thumb.webp': (427, 640),
                 'assets/previews/posters/poster-082-512.webp': (341, 512),
                 'assets/previews/posters/poster-082-1280.webp': (853, 1280),
                 'assets/optimized/poster-082-strip.webp': (128, 192)}
        manifest = json.loads((PUBLIC / 'bundle-manifest.json').read_text())
        for path, expected in sizes.items():
            with self.subTest(path=path), Image.open(PUBLIC / path) as image:
                self.assertEqual(image.size, expected)
                self.assertEqual(hashlib.sha256((PUBLIC / path).read_bytes()).hexdigest(),
                                 manifest['files'][path]['sha256'])

    def test_duo_replaces_home_entry_while_preserving_the_single_bottle(self):
        posters = json.loads((CLIENT / 'src/posters.json').read_text())
        self.assertEqual(len(posters), 65)
        poster = [p for p in posters if p['id'] == 'poster-082']
        self.assertEqual(len(poster), 1)
        self.assertEqual(poster[0]['category'], 'sets')
        self.assertEqual(poster[0]['title']['en'], 'liaose Soap Clean Duo')
        featured = json.loads((CLIENT / 'src/featured.json').read_text())
        self.assertEqual(len(featured), 29)
        self.assertEqual(featured[27]['id'], 'poster-082')
        self.assertNotIn('poster-080', {p['id'] for p in featured})
        collection = json.loads((CLIENT / 'src/structure/collection-products.json').read_text())
        self.assertIn('poster-082', collection)
        self.assertIn('poster-080', collection)
        manifest = json.loads((PUBLIC / 'bundle-manifest.json').read_text())
        self.assertEqual(manifest['version'], 'client1.47')
        self.assertEqual(sum(n.endswith('.glb') for n in manifest['files']), 30)
        self.assertFalse(any('soap-duo' in n or 'review-product' in n for n in manifest['files']))
        self.assertIn('assets/packaging/poster-082-v1.glb', manifest['files'])
        self.assertIn('assets/featured/poster-082.png', manifest['files'])
        self.assertIn('assets/packaging/poster-080-v2.glb', manifest['files'])
        self.assertIn('assets/posters/poster-080.webp', manifest['files'])


if __name__ == '__main__':
    unittest.main()
