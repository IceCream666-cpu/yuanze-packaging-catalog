"""client1.2 may only add reviewed cutouts to the authenticated showroom bundle."""
import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('motion_showroom_builder', ROOT / 'scripts/build_customer_showroom.py')
builder = importlib.util.module_from_spec(spec)
spec.loader.exec_module(builder)


class MotionReleaseTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.previous = builder.expected_files(edition='client1')
        cls.current = builder.expected_files(edition='client12')
        cls.featured = json.loads((builder.MOTION_CLIENT / 'featured-manifest.json').read_text())

    def test_release_changes_only_entrypoints_and_adds_eight_approved_derivatives(self):
        added = {item['productionTarget'] for item in self.featured['files']}
        self.assertEqual(len(added), 8)
        self.assertEqual(set(self.current) - set(self.previous), added)
        self.assertEqual(set(self.previous) - set(self.current), set())
        changed = {name for name in self.previous if self.previous[name] != self.current[name]}
        self.assertEqual(changed, {'index.html', 'preview.js', 'preview.css', 'bundle-manifest.json'})
        self.assertIn(b'client1.2', self.current['index.html'])
        self.assertNotIn('动效预览'.encode(), self.current['index.html'])
        self.assertIn(b'/showroom/preview.js', self.current['index.html'])
        self.assertIn(b'/showroom/preview.css', self.current['index.html'])
        self.assertIn(b'/api/session', self.current['preview.js'])
        self.assertIn(b'/api/logout', self.current['preview.js'])
        self.assertIn(b'assets/featured/', self.current['preview.js'])
        self.assertNotIn(b'/src/main.jsx', self.current['index.html'])
        manifest = json.loads(self.current['bundle-manifest.json'])
        self.assertEqual(manifest['version'], 'client1.2')
        self.assertEqual(manifest['source'], 'docs/client-motion-demo')
        self.assertEqual(set(manifest['files']), set(self.current) - {'bundle-manifest.json'})
        for name, entry in manifest['files'].items():
            self.assertEqual(hashlib.sha256(self.current[name]).hexdigest(), entry['sha256'])
            self.assertEqual(len(self.current[name]), entry['bytes'])
        for entry in self.featured['files']:
            self.assertEqual(hashlib.sha256(self.current[entry['productionTarget']]).hexdigest(), entry['sha256'])

    def test_source_changes_and_release_tampering_are_rejected(self):
        with patch.object(builder, 'client_source_hash', return_value='0' * 64):
            with self.assertRaisesRegex(ValueError, 'source changed'):
                builder.client_files(self.previous, 'client12')
        with tempfile.TemporaryDirectory() as directory:
            altered = Path(directory) / 'preview.js'
            altered.write_bytes(b'tampered')
            original = builder.source_file
            def source_file(source, name):
                return altered if Path(source) == builder.MOTION_CLIENT / 'release' and name == 'preview.js' else original(source, name)
            with patch.object(builder, 'source_file', side_effect=source_file):
                with self.assertRaisesRegex(ValueError, 'release checksum mismatch'):
                    builder.client_files(self.previous, 'client12')

    def test_derivative_approval_identity_paths_and_original_hash_are_checked(self):
        cases = [
            ('approval', lambda m: m.update(scope='local-preview-derived-assets-not-production-approved')),
            ('identity', lambda m: m['files'].append(copy.deepcopy(m['files'][0]))),
            ('route', lambda m: m['files'][0].update(productionTarget='assets/../private.png')),
            ('source route', lambda m: m['files'][0].update(approvedPoster='server-reference/private/secret.png')),
            ('source hash', lambda m: m['files'][0].update(approvedPosterSha256='0' * 64)),
            ('derivative hash', lambda m: m['files'][0].update(sha256='0' * 64)),
        ]
        for label, mutate in cases:
            with self.subTest(label=label), tempfile.TemporaryDirectory() as directory:
                manifest = copy.deepcopy(self.featured)
                mutate(manifest)
                altered = Path(directory) / 'featured-manifest.json'
                altered.write_text(json.dumps(manifest))
                original = builder.source_file
                def source_file(source, name):
                    return altered if name == 'featured-manifest.json' else original(source, name)
                with patch.object(builder, 'source_file', side_effect=source_file):
                    with self.assertRaises(ValueError):
                        builder.featured_files(dict(self.previous), builder.MOTION_CLIENT)

    def test_derivatives_cannot_replace_existing_showroom_files(self):
        files = dict(self.previous)
        files[self.featured['files'][0]['productionTarget']] = b'existing file'
        with self.assertRaisesRegex(ValueError, 'cannot replace'):
            builder.featured_files(files, builder.MOTION_CLIENT)

    def test_only_stamped_entrypoints_are_packaged_and_output_tampering_is_detected(self):
        self.assertEqual({p.name for p in (builder.MOTION_CLIENT / 'release').iterdir()},
                         {'index.html', 'preview.js', 'preview.css', 'build.json'})
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / 'showroom'
            builder.build(destination=output, edition='client12')
            self.assertEqual(builder.check(destination=output, edition='client12'), [])
            name = self.featured['files'][0]['productionTarget']
            (output / name).write_bytes(b'changed')
            (output / 'private.json').write_text('not approved')
            self.assertEqual(builder.check(destination=output, edition='client12'), [name, 'private.json'])

    def test_cli_defaults_to_client12_and_keeps_historical_editions_explicit(self):
        with patch.object(builder.sys, 'argv', ['build_customer_showroom.py', '--check']), \
                patch.object(builder, 'check', return_value=[]) as check:
            self.assertEqual(builder.main(), 0)
            self.assertEqual(check.call_args.kwargs['edition'], 'client12')
        with self.assertRaisesRegex(ValueError, 'Unsupported showroom edition'):
            builder.expected_files(edition='unknown')
