"""The poster-only release must reuse the authenticated, approved asset surface."""
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('showroom_builder', ROOT / 'scripts/build_customer_showroom.py')
builder = importlib.util.module_from_spec(spec)
spec.loader.exec_module(builder)


class ClientReleaseTests(unittest.TestCase):
    def test_only_three_entrypoints_change_from_approved_showroom(self):
        previous = builder.expected_files()
        current = builder.expected_files(edition='client1')
        self.assertEqual(set(previous), set(current))
        changed = {name for name in current if previous[name] != current[name]}
        self.assertEqual(changed, {'index.html', 'preview.css', 'preview.js', 'bundle-manifest.json'})
        self.assertIn(b'client1.0', current['index.html'])
        self.assertIn(b'/showroom/preview.js', current['index.html'])
        self.assertIn(b'/api/session', current['preview.js'])
        self.assertIn(b'/api/logout', current['preview.js'])
        self.assertNotIn('找相似包材'.encode(), current['preview.js'])
        self.assertNotIn('选型意向'.encode(), current['preview.js'])
        manifest = json.loads(current['bundle-manifest.json'])
        self.assertEqual(manifest['version'], 'client1.0')
        self.assertTrue(all(not name.startswith('assets/') or builder.ASSET_PATH.fullmatch(name)
                            for name in manifest['files']))

    def test_rebuild_is_exact_and_detects_tampering(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / 'showroom'
            builder.build(destination=output, edition='client1')
            self.assertEqual(builder.check(destination=output, edition='client1'), [])
            (output / 'preview.js').write_text('stale')
            self.assertIn('preview.js', builder.check(destination=output, edition='client1'))
