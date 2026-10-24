"""Client 1.14 retains the approved client1.6 model and lazy chunks remain reviewed, complete and isolated."""
import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import shutil
import struct
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('packaging_showroom_builder', ROOT / 'scripts/build_customer_showroom.py')
builder = importlib.util.module_from_spec(spec)
spec.loader.exec_module(builder)


class PackagingApprovalTests(unittest.TestCase):
    def test_only_the_eight_reviewed_models_and_two_animation_scripts_are_added(self):
        files = {'unrelated.webp': b'preserved'}
        builder.packaging_files(files, builder.MOTION_CLIENT)
        self.assertEqual(files['unrelated.webp'], b'preserved')
        self.assertEqual(set(files) - {'unrelated.webp'},
                         {f'assets/packaging/{name}' for name in builder.PACKAGING_ASSETS})
        glb = files['assets/packaging/beach-magic-packaging.glb']
        self.assertEqual(struct.unpack_from('<4sII', glb), (b'glTF', 2, len(glb)))
        json_length, chunk_type = struct.unpack_from('<II', glb, 12)
        self.assertEqual(chunk_type, 0x4e4f534a)
        model = json.loads(glb[20:20 + json_length])
        roots = model['scenes'][model.get('scene', 0)]['nodes']
        self.assertEqual({model['nodes'][index]['name'] for index in roots}, {'Jar', 'OuterCap', 'InnerLid'})
        self.assertEqual(len(model['meshes']), 9)
        self.assertFalse(model.get('animations'))
        self.assertFalse(model.get('cameras'))
        self.assertNotIn('KHR_lights_punctual', model.get('extensions', {}))
        self.assertTrue(all('bufferView' in image and 'uri' not in image for image in model['images']))

    def test_pump_has_exactly_five_parts_and_beach_model_is_unchanged(self):
        files={};builder.packaging_files(files,builder.MOTION_CLIENT)
        self.assertEqual(set(builder.PACKAGING_ASSETS), {'beach-magic-packaging.glb','liaose-pump.glb','poster-039.glb','poster-049.glb','poster-042.glb','poster-051.glb','poster-044.glb','poster-047.glb','gsap.min.js','ScrollTrigger.min.js'})
        glb=files['assets/packaging/liaose-pump.glb']
        self.assertEqual(hashlib.sha256(glb).hexdigest(),'d5a1b4aa35806802b8b3022a2d5061ba2203c9a7164035d15ecfb6ef4876b936')
        length=struct.unpack_from('<I',glb,12)[0];model=json.loads(glb[20:20+length])
        roots=model['scenes'][model.get('scene',0)]['nodes']
        self.assertEqual({model['nodes'][i]['name'] for i in roots},{'BottleAssembly','Closure','PumpStem','PumpHead','LogoPrint'})
        self.assertEqual(hashlib.sha256(files['assets/packaging/beach-magic-packaging.glb']).hexdigest(),'e67f53751c841bbe90f9cb94cd4580245572d25c39f214e8f34f8378ae680e76')

    def test_approval_identity_path_hash_and_duplicate_changes_are_rejected(self):
        approved = json.loads((builder.MOTION_CLIENT / 'packaging-manifest.json').read_text())
        mutations = [
            lambda m: m.update(scope='unapproved'),
            lambda m: m.update(posterId='poster-999'),
            lambda m: m.update(containsFormula=True),
            lambda m: m['additionalProducts'].append({'posterId':'poster-062'}),
            lambda m: m['components'].append('Contents'),
            lambda m: m['files'].pop(),
            lambda m: m['files'].__setitem__(1, m['files'][0]),
            lambda m: m['files'][0].update(file='../private.glb'),
            lambda m: m['files'][0].update(productionTarget='assets/packaging/../private.glb'),
            lambda m: m['files'][0].update(sha256='0' * 64),
            lambda m: m['files'][1].update(kind='model'),
            lambda m: m['files'][2].update(bytes=1),
        ]
        original = builder.source_file
        for index, mutate in enumerate(mutations):
            with self.subTest(index=index), tempfile.TemporaryDirectory() as directory:
                manifest = copy.deepcopy(approved)
                mutate(manifest)
                path = Path(directory) / 'approval.json'
                path.write_text(json.dumps(manifest))
                with patch.object(builder, 'source_file', side_effect=lambda source, name:
                                  path if name == 'packaging-manifest.json' else original(source, name)):
                    with self.assertRaises(ValueError):
                        builder.packaging_files({}, builder.MOTION_CLIENT)

    def test_approved_model_cannot_replace_an_existing_route(self):
        with self.assertRaisesRegex(ValueError, 'cannot replace'):
            builder.packaging_files({'assets/packaging/beach-magic-packaging.glb': b'existing'}, builder.MOTION_CLIENT)

    def test_preview_preparation_copies_only_validated_assets_to_the_production_routes(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            shutil.copytree(builder.MOTION_CLIENT / 'packaging-assets', base / 'packaging-assets')
            shutil.copyfile(builder.MOTION_CLIENT / 'packaging-manifest.json', base / 'packaging-manifest.json')
            self.assertEqual(builder.prepare_packaging_assets(base), 10)
            expected = {f'assets/packaging/{name}' for name in builder.PACKAGING_ASSETS}
            self.assertEqual({path.relative_to(base / 'public').as_posix()
                              for path in (base / 'public').rglob('*') if path.is_file()}, expected)
            for name in builder.PACKAGING_ASSETS:
                self.assertEqual((base / 'public/assets/packaging' / name).read_bytes(),
                                 (base / 'packaging-assets' / name).read_bytes())
            model = base / 'packaging-assets/beach-magic-packaging.glb'
            model.write_bytes(b'tampered')
            with self.assertRaisesRegex(ValueError, 'checksum mismatch'):
                builder.prepare_packaging_assets(base)
            self.assertNotEqual((base / 'public/assets/packaging/beach-magic-packaging.glb').read_bytes(), b'tampered')

    def test_preview_preparation_rejects_symlinked_output_directories(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            shutil.copytree(builder.MOTION_CLIENT / 'packaging-assets', base / 'packaging-assets')
            shutil.copyfile(builder.MOTION_CLIENT / 'packaging-manifest.json', base / 'packaging-manifest.json')
            (base / 'public/assets').mkdir(parents=True)
            (base / 'private').mkdir()
            (base / 'public/assets/packaging').symlink_to(base / 'private', target_is_directory=True)
            with self.assertRaisesRegex(ValueError, 'symlink'):
                builder.prepare_packaging_assets(base)
            self.assertEqual(list((base / 'private').iterdir()), [])


class BuildGraphTests(unittest.TestCase):
    def fixture(self, base):
        graph = {
            'index.html': {'file': 'preview.js', 'isEntry': True, 'css': ['preview.css'],
                           'dynamicImports': ['src/structure/PackagingDetail.jsx']},
            'src/structure/PackagingDetail.jsx': {'file': 'assets/packaging/PackagingDetail-12345678.js',
                           'css': ['assets/packaging/PackagingDetail-abcdefgh.css'],
                           'dynamicImports': ['src/structure/packaging-scene.js']},
            'src/structure/packaging-scene.js': {'file': 'assets/packaging/packaging-scene-87654321.js'},
        }
        release = base / 'release'
        names = {'index.html', 'preview.js', 'preview.css',
                 'assets/packaging/PackagingDetail-12345678.js',
                 'assets/packaging/PackagingDetail-abcdefgh.css',
                 'assets/packaging/packaging-scene-87654321.js'}
        for name in names:
            path = release / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(name)
        (release / '.vite').mkdir()
        (release / '.vite/manifest.json').write_text(json.dumps(graph))
        return release, graph, names

    def test_reachable_nested_dynamic_js_and_css_are_inventoried(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            _, _, expected = self.fixture(base)
            for edition in ('client16', 'client114'):
                with self.subTest(edition=edition):
                    self.assertEqual(builder.release_file_names(base, edition), expected)
            for edition in ('client1', 'client12', 'client13', 'client14', 'client15'):
                self.assertEqual(builder.release_file_names(base, edition), set(builder.CLIENT_ENTRYPOINTS))

    def test_unreachable_missing_traversal_and_arbitrary_build_files_are_rejected(self):
        mutations = [
            lambda g: g['index.html'].update(file='../preview.js'),
            lambda g: g['src/structure/packaging-scene.js'].update(file='assets/packaging/../private.js'),
            lambda g: g['src/structure/packaging-scene.js'].update(file='assets/other/model-12345678.js'),
            lambda g: g['index.html'].update(dynamicImports=[]),
            lambda g: g['index.html'].update(imports=['missing-key']),
            lambda g: g['index.html'].update(assets=['private.json']),
            lambda g: g['index.html'].update(css=['preview.css', '../private.css']),
            lambda g: g['src/structure/packaging-scene.js'].update(isEntry=True),
        ]
        for index, mutate in enumerate(mutations):
            with self.subTest(index=index), tempfile.TemporaryDirectory() as directory:
                base = Path(directory)
                release, graph, _ = self.fixture(base)
                mutate(graph)
                (release / '.vite/manifest.json').write_text(json.dumps(graph))
                with self.assertRaises(ValueError):
                    builder.release_file_names(base, 'client114')
        for name in ('private.json', 'assets/packaging/extra-12345678.js', 'preview.js.map'):
            with self.subTest(name=name), tempfile.TemporaryDirectory() as directory:
                base = Path(directory)
                release, _, _ = self.fixture(base)
                (release / name).write_text('unreviewed')
                with self.assertRaisesRegex(ValueError, 'differs from its build graph'):
                    builder.release_file_names(base, 'client114')

    def test_symlinked_chunks_and_parent_directories_are_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            release, _, _ = self.fixture(base)
            path = release / 'assets/packaging/packaging-scene-87654321.js'
            path.unlink()
            path.symlink_to(release / 'preview.js')
            with self.assertRaisesRegex(ValueError, 'symlink'):
                builder.release_file_names(base, 'client114')
            with self.assertRaisesRegex(ValueError, 'symlink'):
                builder.source_file(release, path.relative_to(release).as_posix())
            (release / 'alias').symlink_to(release / 'assets', target_is_directory=True)
            with self.assertRaisesRegex(ValueError, 'symlink'):
                builder.source_file(release, 'alias/packaging/PackagingDetail-12345678.js')

    def test_stamped_chunk_and_graph_tampering_are_rejected_before_packaging(self):
        for tamper_graph in (False, True):
            with self.subTest(tamper_graph=tamper_graph), tempfile.TemporaryDirectory() as directory:
                base = Path(directory)
                release, graph, names = self.fixture(base)
                stamp = {'version': 'client1.14', 'sourceSha256': 'source',
                         'files': {name: hashlib.sha256((release / name).read_bytes()).hexdigest() for name in names},
                         'viteManifestSha256': hashlib.sha256((release / '.vite/manifest.json').read_bytes()).hexdigest()}
                (release / 'build.json').write_text(json.dumps(stamp))
                if tamper_graph:
                    (release / '.vite/manifest.json').write_text(json.dumps(graph, indent=2))
                else:
                    (release / 'assets/packaging/packaging-scene-87654321.js').write_text('tampered')
                with patch.object(builder, 'client_directory', return_value=base), \
                        patch.object(builder, 'client_source_hash', return_value='source'):
                    with self.assertRaisesRegex(ValueError, 'checksum mismatch'):
                        builder.client_files({}, 'client114')


class RecursiveSourceTests(unittest.TestCase):
    def test_nested_source_and_static_asset_edits_change_the_source_stamp(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            names = ['src/main.jsx', 'src/structure/vendor/three.module.js', 'src/structure/packaging-detail.css',
                     'index.html', 'vite.config.js', 'package.json', 'assets-manifest.json',
                     'featured-manifest.json', 'prepare-assets.py', 'display-derivatives.json',
                     'optimize-display-assets.py', 'packaging-manifest.json',
                     *(f'packaging-assets/{name}' for name in builder.PACKAGING_ASSETS)]
            for name in names:
                path = base / name
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(name)
            with patch.object(builder, 'client_directory', return_value=base):
                before = builder.client_source_hash('client114')
                for name in ['src/structure/vendor/three.module.js', 'src/structure/packaging-detail.css',
                             'packaging-assets/beach-magic-packaging.glb', 'packaging-manifest.json']:
                    path = base / name
                    original = path.read_bytes()
                    path.write_bytes(original + b'changed')
                    self.assertNotEqual(builder.client_source_hash('client114'), before, name)
                    path.write_bytes(original)
                (base / 'src/structure/new.js').write_text('new nested source')
                self.assertNotEqual(builder.client_source_hash('client114'), before)

    def test_original_flat_client1_source_stamp_is_still_valid(self):
        stamp = json.loads((builder.CLIENT / 'release/build.json').read_text())
        self.assertEqual(builder.client_source_hash('client1'), stamp['sourceSha256'])


class BuiltPackagingLazyLoadTests(unittest.TestCase):
    def test_initial_import_graph_excludes_three_gsap_model_and_detail_styles(self):
        client = builder.MOTION_CLIENT
        names = builder.release_file_names(client, 'client114')
        graph = json.loads((client / 'release/.vite/manifest.json').read_text())
        pending, visited, initial = ['index.html'], set(), set()
        while pending:
            key = pending.pop()
            if key in visited:
                continue
            visited.add(key)
            node = graph[key]
            initial.add(node['file'])
            initial.update(node.get('css', []))
            pending.extend(node.get('imports', []))
        initial_bytes = b'\n'.join((client / 'release' / name).read_bytes() for name in initial)
        deferred_bytes = b'\n'.join((client / 'release' / name).read_bytes() for name in names - initial)
        self.assertNotIn(b'THREE.WebGLRenderer', initial_bytes)
        self.assertIn(b'THREE.WebGLRenderer', deferred_bytes)
        # The lightweight, click-mounted loader legitimately contains the model
        # URL. The eager graph must still exclude its binary and renderer code;
        # the React integration test verifies no request occurs before opening.
        self.assertNotIn('src/structure/packaging-scene.js', visited)
        self.assertNotIn('src/structure/PackagingDetail.jsx', visited)
        self.assertTrue(all(not name.endswith('.glb') for name in initial))
        glb = (client / 'packaging-assets/beach-magic-packaging.glb').read_bytes()
        self.assertNotIn(glb, initial_bytes)
        self.assertNotIn(b'gsap.min.js', initial_bytes)
        self.assertNotIn(b'ScrollTrigger.min.js', initial_bytes)
        self.assertNotIn(b'.packaging-detail', initial_bytes)
        self.assertTrue(any(name.endswith('.css') for name in names - initial))
        html = (client / 'release/index.html').read_text()
        self.assertNotIn('beach-magic-packaging.glb', html)
        self.assertNotIn('gsap.min.js', html)
        self.assertNotIn('ScrollTrigger.min.js', html)
