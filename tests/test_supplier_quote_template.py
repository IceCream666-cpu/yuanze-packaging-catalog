"""Check the simplified picture-first supplier form exported by the builder."""
from pathlib import Path
import unittest
from zipfile import ZipFile
import xml.etree.ElementTree as ET
FILE=Path(__file__).resolve().parents[1]/'outputs/supplier-quote-simple-20261014/源泽包材库_供应商图文报价简表.xlsx'
NS={'s':'http://schemas.openxmlformats.org/spreadsheetml/2006/main'}
class SupplierQuoteTemplateTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  if not FILE.exists():raise unittest.SkipTest('Generate the simple supplier workbook first')
  with ZipFile(FILE) as z:
   cls.book=ET.fromstring(z.read('xl/workbook.xml'))
   cls.sheet=ET.fromstring(z.read('xl/worksheets/sheet1.xml'))
   shared=ET.fromstring(z.read('xl/sharedStrings.xml'))
  strings=[''.join(si.itertext()) for si in shared.findall('s:si',NS)]
  cls.cells={}
  for c in cls.sheet.findall('.//s:sheetData/s:row/s:c',NS):
   v=c.find('s:v',NS)
   if v is not None and v.text is not None:cls.cells[c.get('r')]=strings[int(v.text)] if c.get('t')=='s' else v.text
  cls.merges={m.get('ref') for m in cls.sheet.findall('.//s:mergeCell',NS)}
 def test_one_sheet_no_cross_sheet_entry(self):
  self.assertEqual(len(self.book.findall('s:sheets/s:sheet',NS)),1)
  self.assertIsNone(self.sheet.find('s:sheetProtection',NS))
 def test_every_product_has_image_and_spec_fields(self):
  for i in range(10):
   r=8+i*27
   self.assertIn(f'A{r+1}:C{r+7}',self.merges)
   self.assertEqual(self.cells[f'D{r+5}'],'规格（如250mL）')
   self.assertEqual(self.cells[f'D{r+7}'],'裸瓶价含哪些配件')
 def test_bare_and_each_process_have_moq_and_three_blank_prices(self):
  for i in range(10):
   r=8+i*27
   self.assertEqual(self.cells[f'A{r+11}'],'裸瓶')
   self.assertEqual(self.cells[f'A{r+12}'],'丝印')
   for row in range(r+11,r+20):
    for col in 'BCDE':self.assertIn(self.cells.get(f'{col}{row}'),[None,''])
   for col in 'CDE':self.assertIn(self.cells.get(f'{col}{r+10}'),[None,''])
 def test_qty_units_and_extras_are_explicit(self):
  self.assertEqual(self.cells['F19'],'元/个')
  self.assertIn('额外费用',self.cells['A28'])
  self.assertEqual(self.cells['D29'],'加工后总货期（天）')
  xml=ET.tostring(self.sheet,encoding='unicode')
  self.assertIn('元/个/色',xml)
  self.assertIn('元/批',xml)
  self.assertFalse(self.sheet.findall('.//s:c[@t="e"]',NS))
if __name__=='__main__':unittest.main()
