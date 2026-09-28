import base64
import io
import json
from pathlib import Path
import tempfile
import unittest

from admin_imports import parse_import, template_csv
from admin_store import AdminStore, AdminError, ConflictError, TEXT_FIELDS
from test_admin_store import credentials


class ProductDetailsTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        root = Path(self.temp.name)
        self.state, self.private = root / 'state', root / 'private'
        self.state.mkdir()
        self.private.mkdir()
        (self.state / 'admin-bootstrap.json').write_text(json.dumps(credentials('admin')))
        self.base = {'records': [{'id': 'BOTTLE-1', 'kind': 'package', 'name': '样品瓶',
                                 'source': {'workbook': '原始表.xlsx', 'row': 4},
                                 'rawCells': {'A4': '原文'}, 'quoteRaw': '1000个：2元；5000个：1.8元'}]}
        self.store = AdminStore(self.state, self.private, {}, self.base)
        self.details = [
            {'label': '阶梯报价', 'value': '1000个：2元', 'sourceField': 'quoteRaw', 'evidence': '1000个：2元；5000个：1.8元'},
            {'label': '阶梯报价', 'value': '5000个：1.8元', 'sourceField': 'quoteRaw', 'evidence': '1000个：2元；5000个：1.8元'},
            {'label': '口径', 'value': '', 'sourceField': '', 'evidence': ''},
        ]

    def tearDown(self):
        self.temp.cleanup()

    def save(self, payload):
        return self.store.mutate('records', 'save', payload, 'admin')

    def test_legacy_record_and_partial_updates_are_safe(self):
        old = self.store.read_admin('records', 'BOTTLE-1')
        saved = self.save({'id': 'BOTTLE-1', 'version': 1, 'name': '新名称'})
        self.assertEqual(saved['productDetails'], [])
        self.assertEqual(saved['source'], old['source'])
        self.assertEqual(saved['rawCells'], old['rawCells'])
        self.assertEqual(saved['productCode'], old['productCode'])
        saved = self.save({'id': 'BOTTLE-1', 'version': 2, 'productDetails': self.details})
        later = self.save({'id': 'BOTTLE-1', 'version': 3, 'quoteRaw': '新原文'})
        self.assertEqual(later['productDetails'], self.details)
        self.assertEqual(later['version'], 4)
        self.assertIn('5000个：1.8元', later['searchText'])
        with self.assertRaises(ConflictError):
            self.save({'id': 'BOTTLE-1', 'version': 3, 'productDetails': []})
        self.assertEqual(self.store.read_admin('records', 'BOTTLE-1')['productDetails'], self.details)

    def test_validation_is_bounded_plain_text_and_accepts_repeat_labels(self):
        invalid = [None, {}, '[]', [None], [{}], self.details * 21,
                   [{'label': 'x', 'value': 1}], [{'label': 'x', 'extra': True}],
                   [{'label': 'x' * 81}], [{'label': 'x', 'value': 'x' * 2001}],
                   [{'label': 'x', 'evidence': 'x' * 2001}],
                   [{'label': 'x', 'sourceField': 'rawCells'}],
                   [{'label': '<script>alert(1)</script>'}],
                   [{'label': 'x', 'evidence': '<img src=x onerror=alert(1)>'}]]
        for details in invalid:
            with self.subTest(details=str(details)[:100]), self.assertRaises(AdminError):
                self.save({'id': 'BOTTLE-1', 'version': 1, 'productDetails': details})
        self.assertEqual(self.store.read_admin('records', 'BOTTLE-1')['version'], 1)
        allowed = [{'label': '  项目  ', 'value': 'MOQ <500；温度 >40℃', 'sourceField': key, 'evidence': ''}
                   for key in sorted(TEXT_FIELDS)]
        self.assertLessEqual(len(allowed), 60)
        record = self.save({'id': 'BOTTLE-1', 'version': 1, 'productDetails': allowed})
        self.assertEqual(record['productDetails'][0]['label'], '项目')
        record = self.save({'id': 'BOTTLE-1', 'version': 2, 'productDetails': self.details})
        self.assertEqual(record['productDetails'], self.details)
        empty = self.save({'id': 'BOTTLE-1', 'version': 3, 'productDetails': []})
        self.assertEqual(empty['productDetails'], [])

    def test_history_restore_original_and_both_json_exports(self):
        saved = self.save({'id': 'BOTTLE-1', 'version': 1, 'productDetails': self.details})
        revision = next(row for row in self.store.read_admin('audit') if row['after'] and row['after'].get('version') == 2)
        self.save({'id': 'BOTTLE-1', 'version': 2, 'productDetails': []})
        restored = self.store.mutate('records', 'restore', {'id': 'BOTTLE-1', 'version': 3, 'revision': revision['id']}, 'admin')
        self.assertEqual(restored['productDetails'], self.details)
        self.assertEqual(restored['productCode'], saved['productCode'])
        self.assertEqual(restored['version'], 4)
        exported = self.store.export()
        stream = io.BytesIO()
        self.store.write_export(stream)
        streamed = json.loads(stream.getvalue())
        for output in (exported, streamed):
            self.assertEqual(output['records'][0]['productDetails'], self.details)
            self.assertNotIn('productDetails', output['originalRecords']['BOTTLE-1'])
            self.assertEqual(output['originalRecords']['BOTTLE-1']['rawCells'], {'A4': '原文'})
            self.assertTrue(any(a['after'] and a['after'].get('productDetails') == self.details for a in output['audit']))

    def test_csv_omission_preserves_details_and_json_bulk_can_set_them(self):
        self.save({'id': 'BOTTLE-1', 'version': 1, 'productDetails': self.details})
        # Existing CSV templates omit the structured field; applying one must not clear it.
        text = '记录编号,版本,名称,备注\nBOTTLE-1,2,表格更新的名称,新备注\n'
        parsed = parse_import({'filename': 'update.csv', 'content': base64.b64encode(text.encode()).decode()})
        self.assertEqual(parsed['errors'], [])
        preview = self.store.bulk_preview(parsed['rows'])
        self.assertTrue(preview['valid'], preview['errors'])
        self.assertEqual(preview['rows'][0]['record']['productDetails'], self.details)
        saved = self.store.bulk_save(preview['rows'], 'admin')['records'][0]
        self.assertEqual(saved['productDetails'], self.details)
        self.assertEqual(saved['remarksRaw'], '新备注')
        self.assertIn('名称', template_csv().decode('utf-8-sig'))
        preview = self.store.bulk_preview([{'name': '新款', 'productDetails': self.details}])
        self.assertTrue(preview['valid'], preview['errors'])
        new = self.store.bulk_save(preview['rows'], 'admin')['records'][0]
        self.assertEqual(new['productDetails'], self.details)
        invalid = self.store.bulk_preview([{'name': '无效', 'productDetails': [{'label': 'x', 'sourceField': 'password'}]}])
        self.assertFalse(invalid['valid'])


if __name__ == '__main__':
    unittest.main()
