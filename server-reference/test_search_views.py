"""Crop search associations require review evidence; fixtures never edit products."""
import copy
import json
import os
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

import search_views


def group(record_ids=None, crop=None):
    return {'recordIds': record_ids or ['R1'], 'imageMappingPending': False,
            'primaryImage': {'path': 'media/catalogue.jpg', 'role': 'product',
                             'imageScope': 'same_style_variants', 'displayCrop': crop or
                             {'x': .1, 'y': .1, 'width': .3, 'height': .7,
                              'sourceWidth': 900, 'sourceHeight': 600}},
            'review': {'basis': search_views.MANIFESTS[0][2], 'sourceImageSha256': 'a' * 64}}


class ReviewedSearchViews(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.public = Path(self.temp.name) / 'public'
        self.public.mkdir()
        self.records = [{'id': 'R1', 'kind': 'package'}, {'id': 'R2', 'kind': 'package'},
                        {'id': 'R3', 'kind': 'package', 'archived': True},
                        {'id': 'SOURCE', 'kind': 'source_page'}]
        self.write([])
        self.write([], index=1)

    def write(self, groups, index=0):
        name, export, _ = search_views.MANIFESTS[index]
        self.write_source('// Reviewed data only.\nexport const ' + export + ' = ' +
                          json.dumps(groups) + ';\n', index=index)

    def write_source(self, source, index=0):
        name = search_views.MANIFESTS[index][0]
        # Match the real release writer: create a new file before atomically
        # replacing the live path, without clearing the parser cache.
        with tempfile.NamedTemporaryFile(mode='w', encoding='utf-8', dir=self.public,
                                         prefix=name + '.', delete=False) as stream:
            stream.write(source)
            temporary = Path(stream.name)
        temporary.replace(self.public / name)

    def views(self):
        return search_views.reviewed_search_views(self.public, self.records)

    def write_provenance(self, entries, version=1):
        target = self.public.parent / search_views.PROVENANCE_FILENAME
        with tempfile.NamedTemporaryFile(mode='w', encoding='utf-8', dir=target.parent,
                                         prefix=target.name + '.', delete=False) as stream:
            json.dump({'version': version, 'entries': entries}, stream)
            temporary = Path(stream.name)
        temporary.replace(target)
        return target

    def binding(self):
        return {'path': 'media/catalogue.jpg', 'sha256': 'b' * 64,
                'native_path': 'media/catalogue.jpg', 'native_sha256': 'a' * 64}

    def test_different_physical_types_on_same_page_remain_separate(self):
        bottle = group(['R1', 'R3', 'SOURCE', 'missing', 'R1'])
        jar = group(['R2'], {'x': .5, 'y': .5, 'width': .3, 'height': .4,
                            'sourceWidth': 900, 'sourceHeight': 600})
        self.write([bottle, jar, copy.deepcopy(bottle)])
        result = self.views()
        self.assertEqual(len(result), 2)
        self.assertEqual([item['record_ids'] for item in result], [['R1'], ['R2']])
        self.assertNotEqual(result[0]['crop'], result[1]['crop'])
        self.assertEqual(result[0]['review_sha256'], 'a' * 64)
        self.assertEqual(result[0]['review_native_path'], 'media/catalogue.jpg')
        # Original source review hashes are metadata, never delivered WebP hashes.
        self.assertNotIn('sha256', result[0])

    def test_only_matching_code_owned_review_basis_and_explicit_mapping_pass(self):
        accepted = group()
        for field, value in [('imageMappingPending', True), ('imageMappingPending', 0),
                             ('imageMappingPending', None)]:
            item = copy.deepcopy(accepted); item[field] = value
            self.write([item]); self.assertEqual(self.views(), [])
        for field, value in [('basis', 'inferred-from-OCR'), ('sourceImageSha256', 'broken'),
                             ('sourceImageSha256', None)]:
            item = copy.deepcopy(accepted); item['review'][field] = value
            self.write([item]); self.assertEqual(self.views(), [])
        item = copy.deepcopy(accepted); item['review']['basis'] = search_views.MANIFESTS[1][2]
        self.write([item]); self.assertEqual(self.views(), [])
        self.write([]); self.write([item], index=1)
        self.assertEqual(self.views()[0]['record_ids'], ['R1'])

    def test_crop_rejects_invalid_coordinates_and_native_dimensions(self):
        accepted = group()
        for field, value in [('x', -.01), ('x', .8), ('x', float('nan')), ('x', 10 ** 400),
                             ('y', float('inf')), ('width', 0), ('width', True),
                             ('height', '0.7'), ('sourceWidth', True),
                             ('sourceWidth', 900.5), ('sourceHeight', 0),
                             ('sourceHeight', 10001), ('width', .001)]:
            with self.subTest(field=field, value=value):
                item = copy.deepcopy(accepted); item['primaryImage']['displayCrop'][field] = value
                self.write([item]); self.assertEqual(self.views(), [])
        item = copy.deepcopy(accepted)
        item['primaryImage']['displayCrop'].update(sourceWidth=5000, sourceHeight=5000)
        self.write([item]); self.assertEqual(self.views(), [])

    def test_serialized_crop_cache_identity_requires_six_bounded_numbers(self):
        expected = (.1, .1, .3, .7, 900, 600)
        self.assertEqual(search_views.validated_crop(expected), expected)
        self.assertEqual(search_views.validated_crop(list(expected)), expected)
        for value in [None, {}, '.1,.1,.3,.7,900,600', expected[:-1], (*expected, 1),
                      (True, .1, .3, .7, 900, 600), (.1, .1, .3, .7, 900.5, 600),
                      (.1, .1, .3, .7, 900, float('nan')), (.9, .1, .3, .7, 900, 600)]:
            with self.subTest(value=value):
                self.assertIsNone(search_views.validated_crop(value))

    def test_image_paths_and_eligibility_fail_closed(self):
        accepted = group()
        for path in ['/media/a.jpg', 'media/../a.jpg', 'media//a.jpg', 'media/./a.jpg',
                     'media\\a.jpg', 'uploads/a.jpg', 'media/a.jpg#crop',
                     'media/a.jpg?download=1', 'media/a\x00.jpg', 'media/a.jp2', None]:
            with self.subTest(path=path):
                item = copy.deepcopy(accepted); item['primaryImage']['path'] = path
                self.write([item]); self.assertEqual(self.views(), [])
        for field, value in [('role', 'other'), ('imageScope', 'source_page'),
                             ('uncertain', True), ('missing', True)]:
            item = copy.deepcopy(accepted); item['primaryImage'][field] = value
            self.write([item]); self.assertEqual(self.views(), [])
        item = copy.deepcopy(accepted); item['recordIds'] = ['SOURCE', 'R3', 'missing']
        self.write([item]); self.assertEqual(self.views(), [])

    def test_native_review_source_is_only_a_same_directory_image_basename(self):
        item = group(); item['primaryImage']['path'] = 'media/type-views/page.webp'
        item['review']['nativeSourceFile'] = 'page.jpg'
        self.write([item])
        self.assertEqual(self.views()[0]['review_native_path'], 'media/type-views/page.jpg')
        for extension in ['.jp2', '.jpf', '.jpx', '.tif', '.tiff']:
            item['review']['nativeSourceFile'] = 'page' + extension
            self.write([item])
            self.assertEqual(self.views()[0]['review_native_path'], 'media/type-views/page' + extension)
        for name in ['../page.jpg', '/page.jpg', 'sub/page.jpg', 'page\\other.jpg',
                     'page.jpg?x=1', 'page.jpg#x', 'page\x00.jpg', 'page.txt', [], '']:
            with self.subTest(name=name):
                item['review']['nativeSourceFile'] = name
                self.write([item]); self.assertEqual(self.views(), [])

    def test_record_changes_apply_without_manifest_cache_rebuild(self):
        self.write([group(['R1', 'R2'])])
        self.assertEqual(self.views()[0]['record_ids'], ['R1', 'R2'])
        self.records[0]['archived'] = True
        self.assertEqual(self.views()[0]['record_ids'], ['R2'])
        self.records[1]['kind'] = 'source_page'
        self.assertEqual(self.views(), [])

    def test_manifest_replacement_invalidates_parsed_cache_and_returns_fresh_objects(self):
        self.write([group(['R1'])])
        result = self.views(); result[0]['record_ids'].append('unauthorized')
        self.assertEqual(self.views()[0]['record_ids'], ['R1'])
        self.write([group(['R2'])])
        self.assertEqual(self.views()[0]['record_ids'], ['R2'])

    def test_same_size_same_timestamp_atomic_replacement_uses_new_file_identity(self):
        self.write([group(['R1'])])
        target = self.public / search_views.MANIFESTS[0][0]
        original_stat = Path.stat
        before = original_stat(target)

        def coarse_timestamps(path, *args, **kwargs):
            actual = original_stat(path, *args, **kwargs)
            if path != target:
                return actual
            values = {name: getattr(actual, name) for name in dir(actual) if name.startswith('st_')}
            # Emulate filesystems whose timestamps cannot distinguish two
            # rapid same-size writes; inode/device are the distinguishing data.
            values.update(st_mtime_ns=before.st_mtime_ns, st_ctime_ns=before.st_ctime_ns)
            return SimpleNamespace(**values)

        with patch.object(Path, 'stat', coarse_timestamps):
            self.assertEqual(self.views()[0]['record_ids'], ['R1'])
            self.write([group(['R2'])])
            os.utime(target, ns=(before.st_atime_ns, before.st_mtime_ns))
            after = original_stat(target)
            self.assertEqual(after.st_size, before.st_size)
            self.assertEqual(after.st_mtime_ns, before.st_mtime_ns)
            self.assertNotEqual((after.st_dev, after.st_ino), (before.st_dev, before.st_ino))
            self.assertEqual(self.views()[0]['record_ids'], ['R2'])

    def test_derivative_provenance_requires_exact_review_path_native_path_and_native_hash(self):
        self.write([group()])
        self.assertNotIn('display_sha256', self.views()[0])
        self.write_provenance([self.binding()])
        self.assertEqual(self.views()[0]['display_sha256'], 'b' * 64)
        # A valid proof for a different review never authorizes this crop.
        for field, value in [('path', 'media/other.jpg'), ('native_path', 'media/other.jp2'),
                             ('native_sha256', 'c' * 64)]:
            binding = self.binding(); binding[field] = value
            self.write_provenance([binding])
            self.assertNotIn('display_sha256', self.views()[0])

    def test_malformed_or_unsafe_derivative_provenance_never_supplies_display_hash(self):
        self.write([group()])
        for field, value in [('path', '../outside.jpg'), ('native_path', 'media/../outside.jp2'),
                             ('native_path', 'uploads/a.jpg'), ('native_path', 'media/other/a.jp2'),
                             ('sha256', 'invalid'), ('native_sha256', None), ('extra', 'unexpected')]:
            with self.subTest(field=field, value=value):
                binding = self.binding(); binding[field] = value
                self.write_provenance([binding])
                self.assertNotIn('display_sha256', self.views()[0])
        self.write_provenance([self.binding(), self.binding()])
        self.assertNotIn('display_sha256', self.views()[0])
        self.write_provenance([self.binding()], version=True)
        self.assertNotIn('display_sha256', self.views()[0])
        path = self.write_provenance([self.binding()])
        with patch.object(search_views, 'MAX_PROVENANCE_BYTES', 1):
            self.assertNotIn('display_sha256', self.views()[0])
        path.write_text('{not JSON')
        self.assertNotIn('display_sha256', self.views()[0])
        path.unlink()
        self.assertNotIn('display_sha256', self.views()[0])

    def test_derivative_provenance_replacement_and_symlink_are_handled_safely(self):
        self.write([group()])
        target = self.write_provenance([self.binding()])
        self.assertEqual(self.views()[0]['display_sha256'], 'b' * 64)
        before = target.stat()
        replacement = self.binding(); replacement['sha256'] = 'c' * 64
        self.write_provenance([replacement])
        os.utime(target, ns=(before.st_atime_ns, before.st_mtime_ns))
        self.assertEqual(target.stat().st_size, before.st_size)
        self.assertEqual(self.views()[0]['display_sha256'], 'c' * 64)
        other = target.with_name('other-provenance.json'); target.rename(other); target.symlink_to(other)
        self.assertNotIn('display_sha256', self.views()[0])

    def test_missing_malformed_oversized_or_executable_manifest_is_not_evaluated(self):
        name, export, _ = search_views.MANIFESTS[0]
        path = self.public / name
        for text in ['export const ' + export + ' = (() => [])();',
                     'export const ' + export + ' = []; alert("not executed");',
                     'export const ' + export + ' = {broken};', 'export const wrong = [];']:
            self.write_source(text)
            self.assertEqual(self.views(), [])
        self.write([group()])
        with patch.object(search_views, 'MAX_MANIFEST_BYTES', 10):
            self.assertEqual(self.views(), [])
        path.unlink(); self.assertEqual(self.views(), [])

    def test_symlink_manifests_are_not_read(self):
        name = search_views.MANIFESTS[0][0]
        path = self.public / name
        self.write([group()]); source = self.public / 'other.js'; path.rename(source)
        path.symlink_to(source)
        self.assertEqual(self.views(), [])


if __name__ == '__main__':
    unittest.main()
