"""client1.3 preserves reviewed cutouts in the authenticated showroom bundle."""
import copy
import base64
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import xml.etree.ElementTree as ET

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('motion_showroom_builder', ROOT / 'scripts/build_customer_showroom.py')
builder = importlib.util.module_from_spec(spec)
spec.loader.exec_module(builder)


class EditionSelectionTests(unittest.TestCase):
    def test_default_and_explicit_historical_editions_reach_matching_build(self):
        for args, edition in [([], 'client13'), (['--edition', 'client13'], 'client13'),
                              (['--edition', 'client12'], 'client12'),
                              (['--edition', 'client1'], 'client1'), (['--edition', 'legacy'], 'legacy')]:
            with self.subTest(edition=edition, args=args), \
                    patch.object(builder.sys, 'argv', ['build_customer_showroom.py', '--check', *args]), \
                    patch.object(builder, 'check', return_value=[]) as check:
                self.assertEqual(builder.main(), 0)
                self.assertEqual(check.call_args.kwargs['edition'], edition)

    def test_release_cannot_be_relabeled_as_another_edition(self):
        for edition, other_version in [('client13', 'client1.2'), ('client12', 'client1.3')]:
            with self.subTest(edition=edition), tempfile.TemporaryDirectory() as directory:
                stamp = Path(directory) / 'build.json'
                stamp.write_text(json.dumps({'version': other_version, 'sourceSha256': '0' * 64,
                                             'files': {name: '0' * 64 for name in builder.CLIENT_ENTRYPOINTS}}))
                with patch.object(builder, 'source_file', return_value=stamp):
                    with self.assertRaisesRegex(ValueError, 'invalid version'):
                        builder.client_files({}, edition)


class MotionReleaseTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.previous = builder.expected_files(edition='client1')
        cls.current = builder.expected_files(edition='client13')
        cls.featured = json.loads((builder.MOTION_CLIENT / 'featured-manifest.json').read_text())
        cls.display = json.loads((builder.MOTION_CLIENT / 'display-derivatives.json').read_text())

    def test_release_changes_only_entrypoints_and_adds_reviewed_display_derivatives(self):
        added = {item['productionTarget'] for item in self.featured['files']}
        self.assertEqual(len(added), 8)
        added |= {f"assets/featured/{entry['posterId']}-{size}.webp" for entry in self.featured['files'] for size in (640, 1024)}
        self.assertEqual(len(added), 24)
        added |= {entry['productionTarget'] for entry in self.display['files']}
        self.assertEqual(len(added), 63)
        self.assertEqual(set(self.current) - set(self.previous), added)
        self.assertEqual(set(self.previous) - set(self.current), set())
        changed = {name for name in self.previous if self.previous[name] != self.current[name]}
        self.assertEqual(changed, {'index.html', 'preview.js', 'preview.css', 'bundle-manifest.json'})
        self.assertIn(b'client1.3', self.current['index.html'])
        self.assertNotIn('动效预览'.encode(), self.current['index.html'])
        self.assertIn(b'/showroom/preview.js', self.current['index.html'])
        self.assertIn(b'/showroom/preview.css', self.current['index.html'])
        self.assertIn(b'/api/session', self.current['preview.js'])
        self.assertIn(b'/api/logout', self.current['preview.js'])
        self.assertIn(b'assets/featured/', self.current['preview.js'])
        self.assertNotIn(b'/src/main.jsx', self.current['index.html'])
        manifest = json.loads(self.current['bundle-manifest.json'])
        self.assertEqual(manifest['version'], 'client1.3')
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
                builder.client_files(self.previous, 'client13')
        with tempfile.TemporaryDirectory() as directory:
            altered = Path(directory) / 'preview.js'
            altered.write_bytes(b'tampered')
            original = builder.source_file
            def source_file(source, name):
                return altered if Path(source) == builder.MOTION_CLIENT / 'release' and name == 'preview.js' else original(source, name)
            with patch.object(builder, 'source_file', side_effect=source_file):
                with self.assertRaisesRegex(ValueError, 'release checksum mismatch'):
                    builder.client_files(self.previous, 'client13')

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
            builder.build(destination=output, edition='client13')
            self.assertEqual(builder.check(destination=output, edition='client13'), [])
            name = self.featured['files'][0]['productionTarget']
            (output / name).write_bytes(b'changed')
            (output / 'private.json').write_text('not approved')
            self.assertEqual(builder.check(destination=output, edition='client13'), [name, 'private.json'])

    def test_cli_defaults_to_client13_and_keeps_historical_editions_explicit(self):
        with patch.object(builder.sys, 'argv', ['build_customer_showroom.py', '--check']), \
                patch.object(builder, 'check', return_value=[]) as check:
            self.assertEqual(builder.main(), 0)
            self.assertEqual(check.call_args.kwargs['edition'], 'client13')
        with self.assertRaisesRegex(ValueError, 'Unsupported showroom edition'):
            builder.expected_files(edition='unknown')

    def test_optimized_derivatives_reject_modified_hash_and_path(self):
        for field, value in [('file', '../private.png'), ('sha256', '0' * 64)]:
            with self.subTest(field=field), tempfile.TemporaryDirectory() as directory:
                manifest = json.loads((builder.MOTION_CLIENT / 'src/featured-media.json').read_text())
                manifest['poster-012']['files']['640'][field] = value
                altered = Path(directory) / 'featured-media.json'
                altered.write_text(json.dumps(manifest))
                original = builder.source_file
                with patch.object(builder, 'source_file', side_effect=lambda source, name: altered if name == 'src/featured-media.json' else original(source, name)):
                    with self.assertRaises(ValueError):
                        builder.featured_files(dict(self.previous), builder.MOTION_CLIENT)


class DisplayDerivativeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.previous = builder.expected_files(edition='client1')
        cls.manifest = json.loads((builder.MOTION_CLIENT / 'display-derivatives.json').read_text())

    def test_adds_only_39_small_derivatives_and_keeps_all_original_bytes(self):
        files = dict(self.previous)
        builder.optimized_display_files(files, builder.MOTION_CLIENT)
        added = set(files) - set(self.previous)
        self.assertEqual(len(added), 39)
        self.assertEqual(added, {entry['productionTarget'] for entry in self.manifest['files']})
        for name, data in self.previous.items():
            self.assertEqual(files[name], data, name)
        for entry in self.manifest['files']:
            with Image.open(io.BytesIO(files[entry['productionTarget']])) as image:
                self.assertEqual(image.format, 'WEBP')
                self.assertEqual(image.size, (entry['width'], entry['height']))
                if entry['kind'] == 'filmstrip':
                    self.assertEqual(max(image.size), 192)

    def test_compact_logo_has_the_exact_original_visible_pixels(self):
        svg = ET.fromstring(self.previous['assets/yuanze-mark.svg'])
        embedded = svg.find('{http://www.w3.org/2000/svg}image').get('href').split(',', 1)[1]
        x, y, width, height = [int(value) for value in svg.get('viewBox').split()]
        with Image.open(io.BytesIO(base64.b64decode(embedded))) as original, \
                Image.open(builder.MOTION_CLIENT / 'optimized-assets/yuanze-mark-compact.webp') as compact:
            expected = original.crop((x, y, x + width, y + height)).convert('RGBA')
            self.assertEqual(compact.convert('RGBA').tobytes(), expected.tobytes())
            self.assertLess((builder.MOTION_CLIENT / 'optimized-assets/yuanze-mark-compact.webp').stat().st_size, 10_000)

    def test_rejects_modified_approval_identity_paths_hashes_and_dimensions(self):
        mutations = [
            lambda m: m.update(scope='unapproved'),
            lambda m: m['files'].pop(),
            lambda m: m['files'].append(copy.deepcopy(m['files'][0])),
            lambda m: m['files'][0].update(productionTarget='assets/yuanze-mark.svg'),
            lambda m: m['files'][0].update(file='../private.json'),
            lambda m: m['files'][0].update(approvedSource='private.json'),
            lambda m: m['files'][0].update(approvedSourceSha256='0' * 64),
            lambda m: m['files'][0].update(sha256='0' * 64),
            lambda m: m['files'][0].update(crop=[0, 0, 152, 171]),
            lambda m: m['files'][1].update(posterId='poster-999'),
            lambda m: m['files'][1].update(width=193),
        ]
        for index, mutate in enumerate(mutations):
            with self.subTest(index=index), tempfile.TemporaryDirectory() as directory:
                manifest = copy.deepcopy(self.manifest)
                mutate(manifest)
                altered = Path(directory) / 'display-derivatives.json'
                altered.write_text(json.dumps(manifest))
                original = builder.source_file
                with patch.object(builder, 'source_file', side_effect=lambda source, name:
                                  altered if name == 'display-derivatives.json' else original(source, name)):
                    with self.assertRaises(ValueError):
                        builder.optimized_display_files(dict(self.previous), builder.MOTION_CLIENT)

    def test_derivatives_cannot_overwrite_any_existing_route(self):
        files = dict(self.previous)
        files[self.manifest['files'][0]['productionTarget']] = b'existing'
        with self.assertRaisesRegex(ValueError, 'cannot replace'):
            builder.optimized_display_files(files, builder.MOTION_CLIENT)

    def test_responsive_metadata_and_routes_match_real_assets(self):
        posters = json.loads((builder.MOTION_CLIENT / 'src/posters.json').read_text())
        paths = json.loads((builder.MOTION_CLIENT / 'src/asset-paths.json').read_text())
        files = dict(self.previous)
        builder.optimized_display_files(files, builder.MOTION_CLIENT)
        for poster in posters:
            for field, width_field, height_field in [('image', 'imageWidth', 'imageHeight'),
                    ('smallImage', 'smallWidth', 'smallHeight'), ('stripThumb', 'stripWidth', 'stripHeight')]:
                route = paths[poster[field]].removeprefix('/showroom/')
                with Image.open(io.BytesIO(files[route])) as image:
                    self.assertEqual(image.size, (poster[width_field], poster[height_field]))
                if field == 'smallImage':
                    self.assertTrue(route.endswith('-512.webp'))
                if field == 'stripThumb':
                    self.assertEqual(route, f"assets/optimized/{poster['id']}-strip.webp")
