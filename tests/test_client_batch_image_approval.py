from copy import deepcopy
import importlib.util
from pathlib import Path
import unittest


SPEC = importlib.util.spec_from_file_location(
    'client_batch_image_approval',
    Path(__file__).parents[1] / 'scripts/client_batch_image_approval.py')
approval = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(approval)


class ClientBatchImageApprovalTests(unittest.TestCase):
    def setUp(self):
        self.path = 'uploads/' + 'a' * 32 + '.jpg'
        self.source = 'media/product-crops/source.jpg'
        self.record = {
            'id': 'r1', 'productCode': 'YZ-BC-000001', 'version': 9,
            'kind': 'package', 'archived': False, 'quoteRaw': 'private',
            'images': [
                {'path': self.source, 'role': 'reference', 'imageScope': 'same_style_variants',
                 'clientVisible': False, 'sourceBbox': [0, 0, 1, 1]},
                {'path': 'media/unrelated.jpg', 'role': 'supplier', 'caption': 'private'},
                {'path': self.path, 'role': 'product', 'imageScope': 'same_style_variants',
                 'clientVisible': False, 'caption': 'reviewed', 'missing': False},
                {'path': 'uploads/' + 'b' * 32 + '.jpg', 'clientVisible': True,
                 'imageScope': 'single_product', 'role': 'product'},
            ]}
        self.edit = {
            'status': 'published', 'sourcePath': self.source, 'scope': 'same_style_variants',
            'qa': {key: True for key in ('identity', 'count', 'watermarks', 'clientSafe')},
            'uploaded': {'path': self.path},
            'publishedRecords': [{'id': 'r1', 'code': 'YZ-BC-000001', 'version': 2}]}

    def test_only_selected_upload_changes_and_preserves_order_fields_and_inputs(self):
        records, edits = [deepcopy(self.record)], [deepcopy(self.edit)]
        before = deepcopy((records, edits))
        plan = approval.build_plan(records, edits)
        expected = deepcopy(self.record['images'])
        expected[2]['clientVisible'] = True
        self.assertEqual(plan, [{'action': 'images', 'id': 'r1', 'version': 9, 'images': expected}])
        self.assertEqual((records, edits), before)
        plan[0]['images'][0]['sourceBbox'][0] = 0.2
        self.assertEqual((records, edits), before)

    def test_idempotent_duplicate_edits_and_multiple_uploads_make_one_patch(self):
        other = deepcopy(self.edit)
        other['uploaded']['path'] = 'uploads/' + 'c' * 32 + '.jpg'
        self.record['images'].append({**self.record['images'][2], 'path': other['uploaded']['path']})
        edits = [self.edit, deepcopy(self.edit), other]
        plan = approval.build_plan([self.record], edits)
        self.assertEqual(len(plan), 1)
        self.assertTrue(plan[0]['images'][2]['clientVisible'])
        self.assertTrue(plan[0]['images'][4]['clientVisible'])
        self.record['images'] = plan[0]['images']
        self.assertEqual(approval.build_plan([self.record], edits), [])

    def test_unsafe_unpublished_and_incomplete_batches_fail_without_mutation(self):
        invalid = []
        for status in ('reviewed', 'pending', 'rejected', None):
            invalid.append({**deepcopy(self.edit), 'status': status})
        for field in self.edit['qa']:
            for value in (False, 1, 'true', None):
                edit = deepcopy(self.edit)
                edit['qa'][field] = value
                invalid.append(edit)
        invalid.extend({**deepcopy(self.edit), 'scope': scope}
                       for scope in ('source_page', 'unresolved', None, 'unknown'))
        invalid.append({**deepcopy(self.edit), 'qa': {}})
        for edit in invalid:
            with self.subTest(edit=edit):
                records = [deepcopy(self.record)]
                before = deepcopy(records)
                with self.assertRaises(ValueError):
                    approval.build_plan(records, [self.edit, edit])
                self.assertEqual(records, before)

    def test_missing_provenance_code_mismatch_record_and_archive_are_rejected(self):
        for refs in (None, [], [{}], [{'id': 'missing', 'code': 'YZ-BC-000001'}],
                     [{'id': 'r1', 'code': 'YZ-BC-000002'}], [{'id': 'r1'}]):
            with self.subTest(refs=refs), self.assertRaises(ValueError):
                approval.build_plan([self.record], [{**self.edit, 'publishedRecords': refs}])
        for changes in ({'archived': True}, {'kind': 'source_page'}, {'kind': 'uncertain'},
                        {'version': None}, {'version': True}):
            with self.subTest(changes=changes), self.assertRaises(ValueError):
                approval.build_plan([{**self.record, **changes}], [self.edit])
        with self.assertRaises(ValueError):
            approval.build_plan([self.record, deepcopy(self.record)], [self.edit])

    def test_unknown_upload_and_noncanonical_source_paths_are_rejected(self):
        for path in (self.source, 'uploads/unknown.jpg', 'uploads/' + 'c' * 32 + '.jpg',
                     'uploads/' + 'a' * 32 + '.png', '../' + self.path,
                     self.path + '?raw=1', 'https://example.com/' + self.path):
            with self.subTest(path=path), self.assertRaises(ValueError):
                approval.build_plan([self.record], [{**self.edit, 'uploaded': {'path': path}}])
        for path in (None, 'media/missing.jpg', 'media/../source.jpg',
                     'media//source.jpg', 'media/%2e%2e/source.jpg', '/media/source.jpg'):
            with self.subTest(source=path), self.assertRaises(ValueError):
                approval.build_plan([self.record], [{**self.edit, 'sourcePath': path}])

    def test_original_and_target_must_remain_present_and_have_valid_evidence(self):
        for index in (0, 2):
            record = deepcopy(self.record)
            record['images'].pop(index)
            with self.subTest(missing_index=index), self.assertRaises(ValueError):
                approval.build_plan([record], [self.edit])
            for changes in ({'missing': True}, {'uncertain': True}, {'role': 'uncertain'},
                            {'role': 'invalid'}, {'imageScope': 'invalid'},
                            {'role': []}, {'imageScope': []},
                            {'clientVisible': 'true'}):
                record = deepcopy(self.record)
                record['images'][index].update(changes)
                with self.subTest(index=index, changes=changes), self.assertRaises(ValueError):
                    approval.build_plan([record], [self.edit])
        for changes in ({'role': 'reference'}, {'imageScope': 'unresolved'},
                        {'imageScope': 'single_product'}):
            record = deepcopy(self.record)
            record['images'][2].update(changes)
            with self.subTest(target=changes), self.assertRaises(ValueError):
                approval.build_plan([record], [self.edit])
        self.record['images'].append(deepcopy(self.record['images'][2]))
        with self.assertRaises(ValueError):
            approval.build_plan([self.record], [self.edit])

    def test_already_visible_target_still_requires_valid_batch(self):
        self.record['images'][2]['clientVisible'] = True
        self.edit['qa']['clientSafe'] = False
        with self.assertRaises(ValueError):
            approval.build_plan([self.record], [self.edit])

    def test_shared_image_supports_212_explicit_products_but_not_unlisted_products(self):
        records, refs = [], []
        for number in range(213):
            record = deepcopy(self.record)
            record.update(id=f'r{number}', productCode=f'YZ-BC-{number:06}', version=number + 1)
            records.append(record)
            if number < 212:
                refs.append({'id': record['id'], 'code': record['productCode']})
        plan = approval.build_plan(records, [{**self.edit, 'publishedRecords': list(reversed(refs))}])
        self.assertEqual([patch['id'] for patch in plan], [record['id'] for record in records[:212]])
        self.assertTrue(all(patch['images'][2]['clientVisible'] is True for patch in plan))
        self.assertTrue(all(patch['images'][0]['clientVisible'] is False for patch in plan))
        self.assertFalse(records[212]['images'][2]['clientVisible'])

    def test_single_product_scope_and_empty_batch(self):
        self.edit['scope'] = self.record['images'][2]['imageScope'] = 'single_product'
        self.assertEqual(len(approval.build_plan([self.record], [self.edit])), 1)
        self.assertEqual(approval.build_plan([self.record], []), [])

    def test_unlisted_archived_record_with_no_gallery_is_untouched(self):
        unrelated = {'id': 'old', 'archived': True, 'kind': 'uncertain', 'images': None}
        plan = approval.build_plan([unrelated, self.record], [self.edit])
        self.assertEqual([patch['id'] for patch in plan], ['r1'])

    def test_conflicting_upload_provenance_is_rejected(self):
        other = deepcopy(self.edit)
        other['sourcePath'] = 'media/another.jpg'
        self.record['images'].append({**self.record['images'][0], 'path': other['sourcePath']})
        with self.assertRaises(ValueError):
            approval.build_plan([self.record], [self.edit, other])


if __name__ == '__main__':
    unittest.main()
