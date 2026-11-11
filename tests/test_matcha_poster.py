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


class MatchaPosterTests(unittest.TestCase):
    def test_approved_original_is_pixel_identical_and_all_display_sizes_match(self):
        source = CLIENT / 'model-source/collection/poster-083/matcha-shampoo-poster-v1.png'
        self.assertEqual(hashlib.sha256(source.read_bytes()).hexdigest(),
                         '53afd0b0caca47d4a6b5f9818a0179d1badb6861510775103212e606145eaafd')
        with Image.open(source) as original, Image.open(PUBLIC / 'assets/posters/poster-083.webp') as published:
            self.assertEqual(original.size, (2048, 3072))
            self.assertEqual(original.convert('RGB').tobytes(), published.convert('RGB').tobytes())
        sizes = {'assets/posters/poster-083.webp': (2048, 3072),
                 'assets/posters/poster-083-thumb.webp': (427, 640),
                 'assets/previews/posters/poster-083-512.webp': (341, 512),
                 'assets/previews/posters/poster-083-1280.webp': (853, 1280),
                 'assets/optimized/poster-083-strip.webp': (128, 192)}
        manifest = json.loads((PUBLIC / 'bundle-manifest.json').read_text())
        for path, expected in sizes.items():
            with self.subTest(path=path), Image.open(PUBLIC / path) as image:
                self.assertEqual(image.size, expected)
                self.assertEqual(hashlib.sha256((PUBLIC / path).read_bytes()).hexdigest(),
                                 manifest['files'][path]['sha256'])

    def test_poster_only_boundary(self):
        posters = json.loads((CLIENT / 'src/posters.json').read_text())
        self.assertEqual(len(posters), 66)
        match = [p for p in posters if p['id'] == 'poster-083']
        self.assertEqual(len(match), 1)
        self.assertEqual(match[0]['title']['en'], 'liaose Matcha Shampoo')
        self.assertEqual(match[0]['category'], 'hair')
        featured = json.loads((CLIENT / 'src/featured.json').read_text())
        self.assertEqual(len(featured), 29)
        self.assertNotIn('poster-083', {p['id'] for p in featured})
        models = json.loads((CLIENT / 'src/structure/collection-products.json').read_text())
        self.assertNotIn('poster-083', models)
        self.assertFalse(any('poster-084' in p['id'] for p in posters))
