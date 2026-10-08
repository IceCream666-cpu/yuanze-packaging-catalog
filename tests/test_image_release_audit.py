import copy
import sys
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from audit_packaging_image_release import audit_release


class ImageReleaseAuditTests(unittest.TestCase):
    def setUp(self):
        self.before = [{'id': 'p1', 'price': 1.25, 'productCode': 'YZ-BC-1',
                        'images': [{'path': 'media/a.jpg', 'clientVisible': False}], 'version': 1}]
        self.edit = {'sourcePath': 'media/a.jpg', 'sourceSHA256': 'sourcehash',
                     'status': 'published', 'scope': 'single_product', 'qa': {'clientSafe': True},
                     'uploaded': {'path': 'uploads/edited.jpg'}, 'publishedRecords': [{'id': 'p1'}]}
        self.after = copy.deepcopy(self.before)
        self.after[0]['images'].insert(0, {'path': 'uploads/edited.jpg', 'clientVisible': False,
                                         'imageScope': 'single_product', 'role': 'product'})
        self.after[0]['version'] = 2

    def check(self, edits=None):
        return audit_release(edits or [self.edit], self.before, self.after, expected_count=len(edits or [self.edit]))

    def test_valid_image_only_publication(self):
        self.assertEqual(self.check()['originalAssociationsKept'], 1)

    def test_rejects_price_change(self):
        self.after[0]['price'] = 99
        with self.assertRaisesRegex(ValueError, 'Non-image'): self.check()

    def test_rejects_missing_original(self):
        self.after[0]['images'].pop()
        with self.assertRaisesRegex(ValueError, 'gallery'): self.check()

    def test_rejects_customer_permission_expansion(self):
        self.after[0]['images'][0]['clientVisible'] = True
        with self.assertRaisesRegex(ValueError, 'authorization'): self.check()

    def test_preserves_existing_customer_approval(self):
        self.before[0]['images'][0]['clientVisible'] = True
        self.after[0]['images'][0]['clientVisible'] = True
        self.assertTrue(self.check()['customerPermissionsPreserved'])

    def test_rejects_duplicate_source(self):
        with self.assertRaisesRegex(ValueError, 'Repeated original'): self.check([self.edit, self.edit])

    def test_rejects_wrong_scope(self):
        self.after[0]['images'][0]['imageScope'] = 'source_page'
        with self.assertRaisesRegex(ValueError, 'scope'): self.check()

    def test_rejects_unfinished_batch(self):
        with self.assertRaisesRegex(ValueError, 'count'):
            audit_release([self.edit], self.before, self.after, expected_count=50)


if __name__ == '__main__': unittest.main()
