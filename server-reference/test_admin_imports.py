import base64
import unittest
from admin_imports import parse_import,template_csv

class Imports(unittest.TestCase):
    def parse(self,content):
        return parse_import({'filename':'products.csv','content':base64.b64encode(content.encode()).decode()})
    def test_zero_empty_and_raw_price_meaning(self):
        result=self.parse('名称,单价,容量ml,材质,MOQ\n空值产品,,,,\n零价产品,0,50,"PET、PP",5000\n')
        self.assertEqual(result['errors'],[])
        self.assertEqual(result['rows'][0]['capacityMl'],None)
        self.assertEqual(result['rows'][0]['quoteRaw'],'')
        self.assertEqual(result['rows'][1]['quoteRaw'],'0')
        self.assertEqual(result['rows'][1]['materials'],['PET','PP'])
    def test_unknown_columns_and_invalid_capacity(self):
        with self.assertRaises(ValueError):self.parse('名称,隐藏字段\na,b\n')
        self.assertTrue(self.parse('名称,容量ml\nb,nan\n')['errors'])
    def test_template_is_header_only_and_no_product_is_invented(self):
        self.assertEqual(len(template_csv().decode('utf-8-sig').splitlines()),1)
    def test_reference_uses_import_blank_reset_disable_and_multiple_values(self):
        result=self.parse('名称,参考用途\n保留原值,\n恢复自动,自动\n关闭参考,[]\n多个用途,洁面、护手霜\nJSON数组,"[""面霜"",""身体乳""]"\n')
        self.assertEqual(result['errors'],[])
        self.assertNotIn('referenceUses',result['rows'][0])
        self.assertIsNone(result['rows'][1]['referenceUses'])
        self.assertEqual(result['rows'][2]['referenceUses'],[])
        self.assertEqual(result['rows'][3]['referenceUses'],['洁面','护手霜'])
        self.assertEqual(result['rows'][4]['referenceUses'],['面霜','身体乳'])
        for value in ('[1]','[null]','[{}]','["""""" ]','[broken'):
            self.assertTrue(self.parse('名称,参考用途\n坏值,"'+value.replace('"','""')+'"\n')['errors'])
    def test_source_rows_survive_blank_and_invalid_rows(self):
        result=self.parse('名称,容量ml\n\n第一条,30\n非法容量,nan\n\n第二条,50\n')
        self.assertEqual(result['sourceRows'],[3,6])
        self.assertEqual([row['name'] for row in result['rows']],['第一条','第二条'])
        self.assertEqual(result['errors'][0]['row'],4)
    def test_xlsx_source_rows_use_actual_sheet_rows(self):
        import io
        from openpyxl import Workbook
        workbook=Workbook();sheet=workbook.active
        sheet.append(['名称','容量ml']);sheet.append([None,None])
        sheet.append(['第一条',30]);sheet.append(['非法容量','nan'])
        sheet.append([None,None]);sheet.append(['第二条',50])
        stream=io.BytesIO();workbook.save(stream);workbook.close()
        result=parse_import({'filename':'source-rows.xlsx','content':base64.b64encode(stream.getvalue()).decode()})
        self.assertEqual(result['sourceRows'],[3,6])
        self.assertEqual(result['errors'][0]['row'],4)
