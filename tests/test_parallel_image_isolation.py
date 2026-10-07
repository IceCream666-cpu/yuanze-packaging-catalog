import importlib.util
from pathlib import Path
import unittest

spec = importlib.util.spec_from_file_location('isolation', Path(__file__).parents[1] / 'scripts/check_parallel_image_batch.py')
isolation = importlib.util.module_from_spec(spec)
spec.loader.exec_module(isolation)


class ParallelImageIsolationTests(unittest.TestCase):
    def record(self, identity, *paths, archived=False):
        return {'id': identity, 'kind': 'package', 'archived': archived,
                'images': [{'path': p} for p in paths]}

    def test_reviewed_source_is_reserved_even_before_upload(self):
        edit = {'sourcePath': 'media/a', 'sourceSHA256': 'sha-a'}
        other = {**edit, 'status': 'reviewed'}
        self.assertTrue(isolation.conflicts([edit], [other], [self.record('a', 'media/a')]))

    def test_identical_bytes_under_another_filename_conflict(self):
        edit = {'sourcePath': 'media/a', 'sourceSHA256': 'same'}
        other = {'sourcePath': 'media/b', 'sourceSHA256': 'same'}
        self.assertTrue(isolation.conflicts([edit], [other], [self.record('a', 'media/a')]))

    def test_new_live_association_blocks_even_when_candidate_ids_differ(self):
        edit = {'sourcePath': 'media/a', 'sourceSHA256': 'a'}
        other = {'sourcePath': 'media/b', 'sourceSHA256': 'b'}
        self.assertTrue(isolation.conflicts([edit], [other], [self.record('shared', 'media/a', 'media/b')]))

    def test_missing_or_archived_source_cannot_be_reported_as_published(self):
        edit = {'sourcePath': 'media/a', 'sourceSHA256': 'a'}
        for records in [[], [self.record('a', 'media/a', archived=True)]]:
            self.assertTrue(isolation.conflicts([edit], [], records))

    def test_disjoint_live_products_pass_and_duplicate_batch_fails(self):
        edit = {'sourcePath': 'media/a', 'sourceSHA256': 'a'}
        other = {'sourcePath': 'media/b', 'sourceSHA256': 'b'}
        records = [self.record('a', 'media/a'), self.record('b', 'media/b')]
        self.assertEqual(isolation.conflicts([edit], [other], records), [])
        self.assertTrue(isolation.conflicts([edit, edit], [other], records))

    def test_completed_receipt_reserves_product_when_original_was_removed(self):
        # A subsequent gallery edit may remove the old source. Its successful
        # publication receipt must still prevent another batch claiming it.
        edit = {'sourcePath': 'media/new', 'sourceSHA256': 'new'}
        other = {'sourcePath': 'media/old', 'sourceSHA256': 'old',
                 'status': 'published', 'publishedRecords': [{'id': 'shared'}]}
        records = [self.record('shared', 'media/new', 'uploads/optimized.jpg')]
        issues = isolation.conflicts([edit], [other], records)
        self.assertEqual(len(issues), 1)
        self.assertIn('live product shared with another batch', issues[0]['reasons'])

    def test_source_page_is_checked_even_with_different_candidate_ids(self):
        edit = {'sourcePath': 'media/new', 'sourceSHA256': 'new',
                'records': [{'id': 'stale-candidate'}]}
        other = {'sourcePath': 'media/other', 'sourceSHA256': 'other'}
        record = self.record('actual-page', 'media/new', 'media/other')
        record['kind'] = 'source_page'
        issues = isolation.conflicts([edit], [other], [record])
        self.assertEqual(len(issues), 1)
        self.assertIn('live product shared with another batch', issues[0]['reasons'])


if __name__ == '__main__':
    unittest.main()
