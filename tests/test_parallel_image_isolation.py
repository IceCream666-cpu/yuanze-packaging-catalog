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


if __name__ == '__main__':
    unittest.main()
