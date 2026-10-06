import importlib.util
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock, patch

SPEC = importlib.util.spec_from_file_location('packaging_batch', Path(__file__).parents[1] / 'scripts/packaging_image_batch.py')
batch = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(batch)


class PackagingImageBatchTests(unittest.TestCase):
    def setUp(self):
        self.record = {'id': 'r', 'productCode': 'YZ-BC-000001', 'version': 2, 'kind': 'package',
                       'quoteRaw': 'supplier price 0.5', 'productDetails': None,
                       'images': [{'path': 'media/source.png', 'role': 'supplier', 'clientVisible': True}]}
        self.edit = {'sourcePath': 'media/source.png', 'scope': 'single_product', 'qa': {'clientSafe': True}}
        self.upload = {'path': 'uploads/' + 'a' * 32 + '.jpg'}

    def test_patch_preserves_original_and_only_changes_images(self):
        patch = batch.image_patch(self.record, self.edit, self.upload)
        self.assertEqual(set(patch), {'id', 'version', 'action', 'images'})
        self.assertTrue(patch['images'][0]['clientVisible'])
        self.assertEqual(patch['images'][1]['path'], 'media/source.png')
        self.assertFalse(patch['images'][1]['clientVisible'])
        self.assertTrue(self.record['images'][0]['clientVisible'])
        self.assertEqual(patch['version'], 2)

    def test_reference_scope_and_client_permission_are_not_promoted(self):
        for scope in ['source_page', 'unresolved']:
            self.edit['scope'] = scope
            patch = batch.image_patch(self.record, self.edit, self.upload)
            self.assertEqual(patch['images'][0]['imageScope'], scope)
            self.assertFalse(patch['images'][0]['clientVisible'])
        self.edit['scope'] = 'single_product'
        self.record['images'][0]['clientVisible'] = False
        self.assertFalse(batch.image_patch(self.record, self.edit, self.upload)['images'][0]['clientVisible'])

    def test_repeat_missing_source_and_gallery_overflow_do_not_duplicate_or_drop(self):
        self.record['images'].append(self.upload)
        self.assertIsNone(batch.image_patch(self.record, self.edit, self.upload))
        self.record['images'] = []
        self.assertIsNone(batch.image_patch(self.record, self.edit, self.upload))
        self.record['images'] = [{'path': 'media/source.png'}] * 30
        with self.assertRaises(ValueError):
            batch.image_patch(self.record, self.edit, self.upload)

    def test_product_integrity_checks_all_non_image_fields(self):
        after = {**self.record, 'version': 3, 'updated': 'now', 'images': []}
        self.assertTrue(batch.unchanged_product(self.record, after))
        self.assertFalse(batch.unchanged_product(self.record, {**after, 'quoteRaw': 'changed'}))
        self.assertFalse(batch.unchanged_product(self.record, {**after, 'productDetails': []}))

    def test_plan_includes_unresolved_and_shares_image_without_merging_records(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'media').mkdir()
            (root / 'media/source.png').write_bytes(b'fixture')
            a = {**self.record, 'images': [{'path': 'media/source.png', 'imageScope': 'unresolved'}]}
            b = {**self.record, 'id': 'other', 'images': [{'path': 'media/source.png', 'imageScope': 'source_page'}]}
            jobs = batch.plan([a, b, {**a, 'id': 'archived', 'archived': True}], root)
            self.assertEqual(len(jobs), 1)
            self.assertEqual(len(jobs[0]['records']), 2)
            self.assertEqual(set(jobs[0]['scopes']), {'unresolved', 'source_page'})
            self.assertFalse(jobs[0]['clientApproved'])

    def test_review_and_checksums_are_required_before_upload(self):
        with self.assertRaises(ValueError):
            batch.validate_edit({'status': 'generated', 'qa': {}})

    def test_upload_waits_for_index_without_bypassing_limits(self):
        gate = Mock()
        gate.expect_status.side_effect = [(None, b'{"building":true}'), (None, b'{"building":false}')]
        with patch.object(batch.time, 'sleep') as sleep:
            batch.wait_for_index_idle(object(), gate)
        self.assertEqual(gate.expect_status.call_count, 2)
        sleep.assert_called_once_with(2)
        gate.expect_status.side_effect = None
        gate.expect_status.return_value = (None, b'{"building":true}')
        with patch.object(batch.time, 'monotonic', side_effect=[0, 181]):
            with self.assertRaises(TimeoutError):
                batch.wait_for_index_idle(object(), gate)


if __name__ == '__main__':
    unittest.main()
