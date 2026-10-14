"""Validate the exported supplier form, not an internal mock of its layout.

Generate it first with the bundled Node runtime and
scripts/build_supplier_quote_template.mjs. No live catalogue is modified.
"""
import os
from pathlib import Path
import unittest
from zipfile import ZipFile
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
FILE = Path(os.environ.get('SUPPLIER_QUOTE_XLSX', ROOT / 'outputs/supplier-quote-template-20261014/源泽包材库_供应商阶梯报价填写模板.xlsx'))
NS = {'s': 'http://schemas.openxmlformats.org/spreadsheetml/2006/main'}


class SupplierQuoteTemplateTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not FILE.exists():
            raise unittest.SkipTest('Generate the supplier XLSX to run artifact checks')
        with ZipFile(FILE) as z:
            cls.xml = {n: ET.fromstring(z.read(n)) for n in z.namelist() if n.endswith('.xml')}
        shared = cls.xml.get('xl/sharedStrings.xml')
        cls.strings = [] if shared is None else [''.join(x.itertext()) for x in shared.findall('s:si', NS)]
        cls.sheets = [cls.xml[f'xl/worksheets/sheet{i}.xml'] for i in range(1, 5)]

    def cells(self, index):
        result = {}
        for c in self.sheets[index].findall('.//s:sheetData/s:row/s:c', NS):
            value = c.find('s:v', NS)
            if c.get('t') == 's' and value is not None:
                result[c.get('r')] = self.strings[int(value.text)]
            elif c.get('t') == 'inlineStr':
                result[c.get('r')] = ''.join(c.find('s:is', NS).itertext())
            elif value is not None and value.text is not None:
                result[c.get('r')] = float(value.text) if c.get('t') != 'str' else value.text
        return result

    def test_real_quote_input_areas_have_no_example_or_default_prices(self):
        for index, first in [(0, 17), (1, 7), (2, 7)]:
            populated = {k: v for k, v in self.cells(index).items() if int(''.join(filter(str.isdigit, k))) >= first and v != ''}
            self.assertEqual(populated, {})

    def test_stable_product_mapping_and_configuration_fields(self):
        p = set(self.cells(0).values())
        for name in ['报价产品编号 *', '源泽产品编号（已有则填）', '供应商型号 *', '材质 *', '规格数值 *', '规格单位 *', '基础颜色 *', '价格所含配件 *', '价格不含配件']:
            self.assertIn(name, p)
        for index in [1, 2]:
            self.assertEqual(self.cells(index)['A6'], '报价产品编号 *')

    def test_moq_and_tier_boundaries_are_separate_for_both_price_types(self):
        for index, moq in [(1, '裸瓶MOQ *'), (2, '工艺MOQ *')]:
            values = set(self.cells(index).values())
            for name in [moq, 'MOQ计算口径 *', '档位起始数量 *', '档位截止数量', '数量单位 *']:
                self.assertIn(name, values)

    def test_process_conditions_and_non_unit_charges_can_be_captured(self):
        values = set(self.cells(2).values())
        for name in ['工艺方案编号 *', '报价形式 *', '加工部位 *', '材质／表面条件 *', '色数 *', '印刷面积／覆盖率', '价格计费单位 *', '最低加工收费（每批）', '一次性费用金额', '周期性质 *', '可叠加／互斥工艺']:
            self.assertIn(name, values)

    def test_bulk_tables_have_filters_frozen_ids_and_editable_cells(self):
        tables = [v for k, v in self.xml.items() if k.startswith('xl/tables/')]
        self.assertEqual({t.get('ref') for t in tables}, {'A16:L116', 'A6:N306', 'A6:X306'})
        for t in tables:
            self.assertIsNotNone(t.find('s:autoFilter', NS))
        for sheet in self.sheets[:3]:
            self.assertIsNone(sheet.find('s:sheetProtection', NS))
            pane = sheet.find('.//s:pane', NS)
            self.assertIsNotNone(pane)
            self.assertEqual(float(pane.get('xSplit', 0)), 2)
            self.assertGreater(float(pane.get('ySplit', 0)), 0)
            self.assertIsNotNone(sheet.find('s:dataValidations', NS))

    def test_samples_are_typed_and_show_independent_moq(self):
        e = self.cells(3)
        self.assertEqual(e['F27'], e['G26'] + 1)
        self.assertEqual(e['F28'], e['G27'] + 1)
        self.assertNotIn('G28', e)  # An open-ended top tier, not an invented cap.
        self.assertGreater(e['E33'], e['E26'])
        self.assertEqual(e['B33'], e['B34'])  # Same process scheme across its tiers.
        self.assertAlmostEqual(e['H33'], 0.12)
        self.assertIn('示例不是实际报价', e['A2'])

    def test_currency_terms_dates_and_no_formula_errors(self):
        vals = set(self.cells(0).values())
        for name in ['币种 *', '报价日期 *', '有效期至 *', '默认税率', '默认含税口径 *', '默认运费口径 *']:
            self.assertIn(name, vals)
        for s in self.sheets:
            self.assertFalse(s.findall('.//s:c[@t="e"]', NS))
        formats = ET.tostring(self.xml['xl/styles.xml'], encoding='unicode')
        self.assertIn('yyyy-mm-dd', formats)
        self.assertIn('0.0000', formats)


if __name__ == '__main__':
    unittest.main()
