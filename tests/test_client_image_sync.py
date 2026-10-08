import importlib.util
from copy import deepcopy
from pathlib import Path
import unittest


SPEC = importlib.util.spec_from_file_location(
    'client_image_sync', Path(__file__).parents[1] / 'scripts/client_image_sync.py')
sync = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(sync)


class ClientImageSyncTests(unittest.TestCase):
    def setUp(self):
        self.path = 'uploads/' + 'a' * 32 + '.jpg'
        self.old = 'uploads/' + 'b' * 32 + '.jpg'
        self.other = 'uploads/' + 'c' * 32 + '.jpg'
        self.source = 'media/source.png'
        self.record = {
            'id': 'r1', 'productCode': 'YZ-BC-000001', 'version': 9,
            'kind': 'package', 'archived': False, 'name': 'Bottle',
            'quoteRaw': 'Internal supplier price', 'productDetails': {'capacity': '30mL'},
            'images': [
                {'path': self.source, 'role': 'supplier', 'imageScope': 'source_page',
                 'clientVisible': False, 'mapping': {'retained': True}},
                {'path': self.other, 'role': 'product', 'imageScope': 'single_product',
                 'clientVisible': True, 'caption': 'Another approved picture'},
                {'path': self.path, 'role': 'product', 'imageScope': 'same_style_variants',
                 'clientVisible': False, 'caption': 'Existing series label', 'missing': False},
            ]}
        self.edit = {
            'status': 'published', 'sourcePath': self.source, 'sourceSHA256': '1' * 64,
            'outputSHA256': '2' * 64, 'scope': 'same_style_variants',
            'uploaded': {'path': self.path, 'imageScope': 'single_product'},
            'qa': {key: True for key in sync.QA_FIELDS},
            'publishedRecords': [{'id': 'r1', 'code': 'YZ-BC-000001', 'version': 4}]}

    def plan(self, records=None, edits=None, approvals=None, supersessions=None):
        return sync.build_plan(
            [self.record] if records is None else records,
            [self.edit] if edits is None else edits,
            {} if approvals is None else approvals,
            [] if supersessions is None else supersessions)

    def approval(self, edit=None):
        edit = self.edit if edit is None else edit
        return {'outputSHA256': edit['outputSHA256'], 'scope': edit['scope'],
                **{key: True for key in sync.REVIEW_FIELDS}}

    def reference(self, scope='unresolved'):
        self.edit['scope'] = scope
        self.edit['qa']['clientSafe'] = False
        self.record['images'][-1].update(imageScope=scope, role='reference')

    def superseded(self):
        old = deepcopy(self.edit)
        old['uploaded']['path'] = self.old
        old['outputSHA256'] = '3' * 64
        old['qa']['clientSafe'] = False  # Not selected for approval.
        self.record['images'].insert(1, {
            'path': self.old, 'role': 'reference', 'imageScope': old['scope'],
            'clientVisible': True, 'caption': 'Previous image', 'extra': ['keep']})
        return old, {'oldPath': self.old, 'newPath': self.path}

    def test_only_selected_visibility_changes_preserving_order_metadata_and_inputs(self):
        before = deepcopy((self.record, self.edit))
        result = self.plan()
        self.assertEqual(result['excluded'], [])
        self.assertEqual(len(result['patches']), 1)
        patch = result['patches'][0]
        self.assertEqual(set(patch), {'action', 'id', 'version', 'images'})
        expected = deepcopy(self.record['images'])
        expected[-1]['clientVisible'] = True
        self.assertEqual(patch['images'], expected)
        self.assertEqual(patch['version'], 9)
        self.assertEqual((self.record, self.edit), before)
        after = {**self.record, 'images': patch['images']}
        self.assertEqual({k: v for k, v in after.items() if k != 'images'},
                         {k: v for k, v in self.record.items() if k != 'images'})
        patch['images'][0]['mapping']['retained'] = False
        self.assertTrue(self.record['images'][0]['mapping']['retained'])

    def test_current_version_is_used_and_stale_snapshot_is_rejected(self):
        self.assertEqual(self.plan()['patches'][0]['version'], 9)
        self.record['version'] = 10
        self.assertEqual(self.plan()['patches'][0]['version'], 10)
        self.record['version'] = 3
        with self.assertRaisesRegex(ValueError, 'predates'):
            self.plan()

    def test_invalid_versions_do_not_produce_unprotected_writes(self):
        for value in [None, True, 0, -1, '9']:
            with self.subTest(value=value):
                self.record['version'] = value
                with self.assertRaises(ValueError):
                    self.plan()

    def test_idempotence_after_applying_versioned_patch(self):
        patch = self.plan()['patches'][0]
        self.record.update(images=patch['images'], version=10)
        self.assertEqual(self.plan()['patches'], [])

    def test_existing_original_authorization_is_not_implicitly_revoked(self):
        self.record['images'][0]['clientVisible'] = True
        patch = self.plan()['patches'][0]
        self.assertTrue(patch['images'][0]['clientVisible'])
        self.assertTrue(patch['images'][1]['clientVisible'])

    def test_unresolved_scope_needs_explicit_approval_even_when_all_old_qa_is_true(self):
        self.edit['scope'] = 'unresolved'
        self.record['images'][-1]['imageScope'] = 'unresolved'
        with self.assertRaisesRegex(ValueError, 'explicit approval'):
            self.plan()

    def test_ordinary_qa_flags_must_be_true_not_truthy(self):
        for key in sync.QA_FIELDS:
            with self.subTest(key=key):
                edit = deepcopy(self.edit)
                edit['qa'][key] = 1
                with self.assertRaisesRegex(ValueError, 'explicit approval'):
                    self.plan(edits=[edit])

    def test_all_reference_scopes_need_explicit_bound_approval(self):
        for scope in ['unresolved', 'source_page', 'same_style_variants']:
            with self.subTest(scope=scope):
                self.reference(scope)
                with self.assertRaisesRegex(ValueError, 'explicit approval'):
                    self.plan()
                before = deepcopy(self.edit)
                result = self.plan(approvals={self.path: self.approval()})
                image = result['patches'][0]['images'][-1]
                self.assertTrue(image['clientVisible'])
                self.assertEqual(image['imageScope'], scope)
                self.assertEqual(image['role'], 'reference')
                self.assertEqual(self.edit, before)
                self.assertFalse(self.edit['qa']['clientSafe'])

    def test_reference_approval_rejects_wrong_hash_scope_or_nontrue_flags(self):
        self.reference()
        for key, value in [('outputSHA256', '9' * 64), ('scope', 'single_product'),
                           ('visualReviewed', False), ('noSensitiveText', 1),
                           ('approvedForClientDisplay', None)]:
            with self.subTest(key=key):
                approval = {**self.approval(), key: value}
                with self.assertRaises(ValueError):
                    self.plan(approvals={self.path: approval})

    def test_invalid_supplied_approval_is_not_ignored_for_ordinary_image(self):
        with self.assertRaises(ValueError):
            self.plan(approvals={self.path: {**self.approval(), 'outputSHA256': '7' * 64}})
        with self.assertRaises(ValueError):
            self.plan(approvals={self.old: self.approval()})

    def test_source_page_and_other_kinds_are_excluded_before_code_and_version(self):
        for kind in ['source_page', 'process', None]:
            with self.subTest(kind=kind):
                record = {'id': 'r1', 'kind': kind}
                self.edit['publishedRecords'][0] = {'id': 'r1'}
                result = self.plan(records=[record])
                self.assertEqual(result['patches'], [])
                self.assertEqual(result['excluded'][0]['reason'], 'not_package')

    def test_archived_package_is_reported_without_altering_or_promoting_it(self):
        self.record.update(archived=True, productCode=None, version=None)
        result = self.plan()
        self.assertEqual(result['patches'], [])
        self.assertEqual(result['excluded'][0]['reason'], 'archived')
        self.assertTrue(self.record['archived'])

    def test_missing_record_or_mismatched_product_code_is_error(self):
        with self.assertRaisesRegex(ValueError, 'missing'):
            self.plan(records=[])
        self.record['productCode'] = 'YZ-BC-000002'
        with self.assertRaisesRegex(ValueError, 'code differs'):
            self.plan()

    def test_multiple_record_ids_cannot_claim_the_same_product_code(self):
        other = deepcopy(self.record)
        other['id'] = 'r2'
        self.edit['publishedRecords'].append({'id': 'r2', 'code': other['productCode'], 'version': 4})
        with self.assertRaisesRegex(ValueError, 'multiple selected records'):
            self.plan(records=[self.record, other])

    def test_gallery_source_must_exist_and_target_must_exist_uniquely(self):
        original = deepcopy(self.record['images'])
        for images in [original[1:], original[:-1], original + [deepcopy(original[-1])]]:
            with self.subTest(paths=[i['path'] for i in images]):
                self.record['images'] = images
                with self.assertRaisesRegex(ValueError, 'gallery image'):
                    self.plan()

    def test_supplier_and_inquiry_associations_to_same_source_are_preserved(self):
        self.record['id'] = 'YZ-S01-R0025'
        self.edit['publishedRecords'][0]['id'] = self.record['id']
        self.edit['sourcePath'] = 'media/image42.png'
        self.record['images'][0].update(path='media/image42.png', missing=False,
                                        caption='Supplier source', clientVisible=True)
        inquiry = {'path': 'media/image42.png', 'role': 'inquiry',
                   'imageScope': 'source_page', 'missing': False,
                   'caption': 'Separate inquiry evidence', 'mapping': {'sourceRow': 25},
                   'clientVisible': False}
        self.record['images'].insert(2, inquiry)
        before = deepcopy(self.record)
        expected = deepcopy(self.record['images'])
        expected[-1]['clientVisible'] = True
        result = self.plan()
        self.assertEqual(result['patches'][0]['images'], expected)
        self.assertEqual(self.record, before)
        self.assertEqual([i['role'] for i in result['patches'][0]['images']
                          if i['path'] == 'media/image42.png'], ['supplier', 'inquiry'])

    def test_every_matching_source_association_is_checked_for_missing_state(self):
        duplicate = deepcopy(self.record['images'][0])
        duplicate.update(role='inquiry', missing=True)
        self.record['images'].insert(1, duplicate)
        with self.assertRaisesRegex(ValueError, 'Missing gallery image'):
            self.plan()
        duplicate['missing'] = False
        self.record['images'][0]['missing'] = True
        with self.assertRaisesRegex(ValueError, 'Missing gallery image'):
            self.plan()

    def test_invalid_target_role_scope_missing_and_permission_are_errors(self):
        original = deepcopy(self.record['images'][-1])
        for changes in [{'role': 'supplier'}, {'imageScope': 'single_product'},
                        {'missing': True}, {'clientVisible': 1}]:
            with self.subTest(changes=changes):
                self.record['images'][-1] = {**original, **changes}
                with self.assertRaises(ValueError):
                    self.plan()

    def test_manifest_path_hash_status_and_duplicate_evidence_are_rejected(self):
        for changes in [{'status': 'reviewed'}, {'sourceSHA256': 'invalid'},
                        {'outputSHA256': None}, {'sourcePath': 'media/../secret'},
                        {'sourcePath': 'media/%2e%2e/secret'},
                        {'uploaded': {'path': 'https://example.com/image.jpg'}},
                        {'uploaded': {'path': 'uploads/../outside.jpg'}},
                        {'publishedRecords': []}]:
            with self.subTest(changes=changes):
                with self.assertRaises(ValueError):
                    self.plan(edits=[{**self.edit, **changes}])
        with self.assertRaisesRegex(ValueError, 'Duplicate uploaded'):
            self.plan(edits=[self.edit, deepcopy(self.edit)])
        duplicate = {**self.edit, 'publishedRecords': self.edit['publishedRecords'] * 2}
        with self.assertRaisesRegex(ValueError, 'Duplicate published'):
            self.plan(edits=[duplicate])
        with self.assertRaisesRegex(ValueError, 'Duplicate record'):
            self.plan(records=[self.record, deepcopy(self.record)])

    def test_supersession_only_disables_old_permission_without_deleting_or_reordering(self):
        old, relation = self.superseded()
        before = deepcopy((self.record, self.edit, old))
        result = self.plan(edits=[old, self.edit], supersessions=[relation])
        expected = deepcopy(self.record['images'])
        expected[1]['clientVisible'] = False
        expected[-1]['clientVisible'] = True
        self.assertEqual(result['patches'][0]['images'], expected)
        self.assertEqual(result['excluded'][0]['reason'], 'superseded')
        self.assertEqual((self.record, self.edit, old), before)
        self.record.update(images=expected, version=10)
        self.assertEqual(self.plan(edits=[old, self.edit], supersessions=[relation])['patches'], [])

    def test_supersession_cannot_disable_old_path_on_unreferenced_product(self):
        old, relation = self.superseded()
        other = deepcopy(self.record)
        other.update(id='r2', productCode='YZ-BC-000002')
        self.edit['publishedRecords'].append({'id': 'r2', 'code': other['productCode'], 'version': 4})
        result = self.plan(records=[self.record, other], edits=[old, self.edit], supersessions=[relation])
        second = next(p for p in result['patches'] if p['id'] == 'r2')
        self.assertTrue(second['images'][1]['clientVisible'])

    def test_supersession_requires_new_coverage_for_every_active_old_product(self):
        old, relation = self.superseded()
        other = deepcopy(self.record)
        other.update(id='r2', productCode='YZ-BC-000002')
        old['publishedRecords'].append({'id': 'r2', 'code': other['productCode'], 'version': 4})
        with self.assertRaisesRegex(ValueError, 'cover every'):
            self.plan(records=[self.record, other], edits=[old, self.edit], supersessions=[relation])

    def test_supersession_source_path_or_hash_mismatch_is_rejected(self):
        old, relation = self.superseded()
        for key, value in [('sourcePath', 'media/different.png'), ('sourceSHA256', '9' * 64)]:
            with self.subTest(key=key):
                with self.assertRaisesRegex(ValueError, 'same source'):
                    self.plan(edits=[{**old, key: value}, self.edit], supersessions=[relation])

    def test_supersession_new_image_still_requires_approval(self):
        old, relation = self.superseded()
        self.edit['qa']['clientSafe'] = False
        with self.assertRaisesRegex(ValueError, 'explicit approval'):
            self.plan(edits=[old, self.edit], supersessions=[relation])

    def test_supersession_missing_edit_self_and_cycle_are_rejected(self):
        old, relation = self.superseded()
        for relations in [[{'oldPath': self.other, 'newPath': self.path}],
                          [{'oldPath': self.path, 'newPath': self.path}],
                          [relation, {'oldPath': self.path, 'newPath': self.old}],
                          [relation, relation]]:
            with self.subTest(relations=relations):
                with self.assertRaises(ValueError):
                    self.plan(edits=[old, self.edit], supersessions=relations)

    def test_two_selected_images_merge_into_one_patch(self):
        second = deepcopy(self.edit)
        second['uploaded']['path'] = self.old
        second['outputSHA256'] = '3' * 64
        self.record['images'].append({'path': self.old, 'role': 'reference',
                                      'imageScope': second['scope']})
        result = self.plan(edits=[self.edit, second])
        self.assertEqual(len(result['patches']), 1)
        self.assertTrue(result['patches'][0]['images'][-1]['clientVisible'])
        self.assertTrue(result['patches'][0]['images'][-2]['clientVisible'])

    def test_later_invalid_record_aborts_whole_plan_without_input_mutation(self):
        other = deepcopy(self.record)
        other.update(id='r2', productCode='YZ-BC-000002')
        self.edit['publishedRecords'].append({'id': 'r2', 'code': other['productCode'], 'version': 4})
        other['images'].pop()
        before = deepcopy((self.record, other, self.edit))
        with self.assertRaises(ValueError):
            self.plan(records=[self.record, other])
        self.assertEqual((self.record, other, self.edit), before)


if __name__ == '__main__':
    unittest.main()
