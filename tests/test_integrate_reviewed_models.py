"""Exercise local model integration without touching the active preview or manifest."""
import contextlib
import hashlib
import io
import json
from pathlib import Path
import runpy
import tempfile
import unittest
from unittest.mock import patch


class ReviewedModelIntegrationTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.base = Path(temporary.name)
        for directory in ['src/structure', 'packaging-assets', 'public/assets/packaging', 'model-source/collection']:
            (self.base / directory).mkdir(parents=True)
        self.config_path = self.base / 'src/structure/collection-products.json'
        self.manifest_path = self.base / 'packaging-manifest.json'
        self.identifiers = ['poster-013', 'poster-039']
        self.config = {identifier: {'file': identifier + '.glb', 'parts': [], 'preserve': identifier} for identifier in self.identifiers}
        self.manifest = {
            'files': [{'name': identifier + '.glb', 'bytes': 3, 'sha256': 'original-' + identifier} for identifier in self.identifiers],
            'additionalProducts': [{'posterId': identifier, 'components': ['Original']} for identifier in self.identifiers],
            'preserve': 'unrelated manifest metadata',
        }
        self.config_path.write_text(json.dumps(self.config))
        self.manifest_path.write_text(json.dumps(self.manifest))
        self.payload = b'glTF reviewed fixture bytes'
        for identifier in self.identifiers:
            source = self.base / 'model-source/collection' / identifier
            source.mkdir()
            parts = [{'node': name, 'short': [label, label]} for name, label in [('Body', '瓶身'), ('PaperLabel', '标贴'), ('LogoPrint', '文字')]]
            (source / 'review-config.json').write_text(json.dumps({'parts': parts, 'explosion': {'offsets': {'label': [-1, 0, .65], 'print': [-3, 0, 1.65]}}}))
            (source / 'model-info.json').write_text(json.dumps({'components': [part['node'] for part in parts], 'containsFormula': False}))
            (self.base / 'packaging-assets' / f'{identifier}.glb').write_bytes(self.payload)
            (self.base / 'public/assets/packaging' / f'{identifier}.glb').write_bytes(b'old preview')
        namespace = runpy.run_path(str(Path(__file__).resolve().parents[1] / 'scripts/integrate_reviewed_models.py'))
        self.integrate = namespace['integrate']
        self.integrate.__globals__.update(BASE=self.base, SOURCE=self.base / 'model-source/collection')

    def test_any_symlink_is_rejected_before_config_manifest_or_other_preview_is_written(self):
        before = {path: path.read_bytes() for path in [self.config_path, self.manifest_path]}
        first = self.base / 'public/assets/packaging/poster-013.glb'
        destination = self.base / 'public/assets/packaging/poster-039.glb'
        outside = self.base / 'protected.glb'
        outside.write_bytes(b'protected target')
        destination.unlink()
        destination.symlink_to(outside)
        with self.assertRaises(AssertionError):
            self.integrate(self.identifiers)
        for path, content in before.items():
            self.assertEqual(path.read_bytes(), content)
        self.assertEqual(first.read_bytes(), b'old preview')
        self.assertEqual(outside.read_bytes(), b'protected target')
        self.assertTrue(destination.is_symlink())

    def test_copy_uses_hashed_bytes_and_preserves_every_unselected_entry(self):
        source = self.base / 'packaging-assets/poster-013.glb'
        original_read = Path.read_bytes

        def read_then_reexport(path):
            content = original_read(path)
            if path == source:
                path.write_bytes(b'a later export replaced the source')
            return content

        with patch.object(Path, 'read_bytes', read_then_reexport), contextlib.redirect_stdout(io.StringIO()):
            self.integrate(['poster-013'])
        config = json.loads(self.config_path.read_text())
        manifest = json.loads(self.manifest_path.read_text())
        copied = (self.base / 'public/assets/packaging/poster-013.glb').read_bytes()
        entry = next(item for item in manifest['files'] if item['name'] == 'poster-013.glb')
        self.assertEqual(copied, self.payload)
        self.assertNotEqual(source.read_bytes(), copied)
        self.assertEqual(entry['sha256'], hashlib.sha256(copied).hexdigest())
        self.assertEqual(entry['bytes'], len(copied))
        self.assertEqual(config['poster-013']['preserve'], 'poster-013')
        self.assertEqual(config['poster-039'], self.config['poster-039'])
        self.assertEqual(manifest['files'][1], self.manifest['files'][1])
        self.assertEqual(manifest['additionalProducts'][1], self.manifest['additionalProducts'][1])
        self.assertEqual(manifest['preserve'], self.manifest['preserve'])
        self.assertEqual((self.base / 'public/assets/packaging/poster-039.glb').read_bytes(), b'old preview')


if __name__ == '__main__':
    unittest.main()
