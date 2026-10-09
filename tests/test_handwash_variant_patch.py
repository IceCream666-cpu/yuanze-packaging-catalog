import importlib.util
from pathlib import Path
from copy import deepcopy
import unittest

module_path = Path(__file__).resolve().parents[1] / 'server-reference/deploy/handwash_variants.py'
spec = importlib.util.spec_from_file_location('handwash_variants', module_path)
patch = importlib.util.module_from_spec(spec)
spec.loader.exec_module(patch)


class HandwashVariantPatchTests(unittest.TestCase):
    def setUp(self):
        self.records = [{'id': rid, 'productCode': code, 'capacityMl': size,
                         'specificationRaw': f'{size}ml', 'quoteRaw': price[:-1],
                         'materials': [], 'version': 5,
                         'source': {'workbook': 'source.xlsx', 'row': n + 12},
                         'images': [{'path': patch.PREVIOUS_COVER, 'clientVisible': True, 'role': 'product'},
                                    {'path': 'media/image27.jpeg', 'role': 'inquiry'},
                                    {'path': 'media/image30.jpeg', 'role': 'reference', 'cell': 'E12'}]}
                        for n, (rid, code, size, price) in enumerate(patch.VARIANTS)]
        self.images = {250: {'path': 'uploads/' + 'a' * 32 + '.jpg'},
                       500: {'path': 'uploads/' + 'b' * 32 + '.jpg'}}

    def test_independent_bare_prices_and_images_retain_original_source_without_inferred_material(self):
        before = deepcopy(self.records)
        rows = patch.build_rows(self.records, self.images)
        self.assertEqual(self.records, before)
        for row, (_, _, size, price) in zip(rows, patch.VARIANTS):
            self.assertEqual(row['version'], 5)
            self.assertEqual(set(row['record']), {'bareBottlePrice', 'images'})
            self.assertEqual(row['record']['bareBottlePrice'], price)
            pictures = row['record']['images']
            self.assertEqual(pictures[0]['path'], self.images[size]['path'])
            self.assertTrue(pictures[0]['clientVisible'])
            self.assertTrue(all(not i['clientVisible'] for i in pictures[1:]))
            self.assertEqual([i['path'] for i in pictures[1:]], [i['path'] for i in before[0]['images']])
            self.assertEqual(pictures[-1]['cell'], 'E12')

    def test_missing_duplicate_and_invalid_uploads_are_rejected(self):
        for images in ({250: self.images[250]}, {250: self.images[250], 500: self.images[250]},
                       {250: {'path': 'media/source.jpg'}, 500: self.images[500]}):
            with self.subTest(images=images), self.assertRaises(ValueError):
                patch.build_rows(self.records, images)

    def test_changed_identity_quote_capacity_and_reference_require_review(self):
        for key, value in [('productCode', 'YZ-BC-000011'), ('capacityMl', 300),
                           ('specificationRaw', 'unknown'), ('quoteRaw', 'different'),
                           ('bareBottlePrice', '2.00元'), ('archived', True), ('version', 0), ('images', [])]:
            records = deepcopy(self.records)
            records[1][key] = value
            with self.subTest(key=key), self.assertRaises(ValueError):
                patch.build_rows(records, self.images)

    def test_missing_or_duplicate_records_are_rejected(self):
        for records in (self.records[:1], [self.records[0], self.records[0]]):
            with self.assertRaises(ValueError):
                patch.build_rows(records, self.images)
