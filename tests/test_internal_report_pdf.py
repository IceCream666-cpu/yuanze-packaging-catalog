"""Reader-facing PDF coverage, sensitive-content, fonts and geometric checks."""
import json
from pathlib import Path
import re
import unittest

import pdfplumber
from pypdf import PdfReader

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / 'docs/包材库内部汇报-20261013.json'
PDF = ROOT / 'output/pdf/源泽包材库_更新微调与工作时段汇报_20260922-20261013.pdf'


def compact(text):
    return re.sub(r'\s+', '', str(text))


class InternalReportPdfTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = json.loads(DATA.read_text())
        cls.reader = PdfReader(PDF)
        cls.text = '\n'.join(page.extract_text() for page in cls.reader.pages)
        cls.compact = compact(cls.text)

    def test_every_update_purpose_operation_result_and_reference_is_present(self):
        self.assertEqual(len(self.data['updates']), self.data['totals']['update_count'])
        for row in self.data['updates']:
            for key in ('id', 'module', 'purpose', 'change', 'result', 'status', 'evidence'):
                with self.subTest(row=row['id'], field=key):
                    self.assertIn(compact(row[key]), self.compact)
            for task in row['task_ids']:
                self.assertIn(task, self.text)

    def test_every_prompt_purpose_and_shared_task_is_present(self):
        for row in self.data['requests']:
            with self.subTest(prompt=row['id']):
                self.assertIn(row['id'], self.text)
                self.assertIn(compact(row['purpose']), self.compact)
                self.assertIn(row['task_id'], self.text)
        self.assertIn('不能逐行相加', self.text)
        self.assertIn('不能跨行相加', self.text)

    def test_every_daily_union_interval_and_frozen_commit_is_present(self):
        for row in self.data['segments']:
            self.assertIn(row['id'], self.text)
            self.assertIn(f"{row['minutes']:.4f}", self.text)
        for row in self.data['daily']:
            self.assertIn(row['date'], self.text)
        for row in self.data['commits']:
            self.assertIn(row['id'], self.text)
            self.assertIn(compact(row['subject']), self.compact)
        total = self.data['totals']
        self.assertIn(f"{total['deduplicated_hours']:.2f} 小时", self.text)
        self.assertIn(f"{total['deduplicated_minutes']:.2f}", self.text)

    def test_boundaries_and_pending_items_are_explicit(self):
        for text in self.data['method_notes'] + self.data['pending']:
            self.assertIn(compact(text), self.compact)
        self.assertIn('不是员工实际人工工时', self.text)
        self.assertIn('本次报表制作', self.text)
        self.assertIn('没有重新读取当前生产数据库', self.text)
        self.assertIn('需求记录时间', self.text)
        self.assertNotIn('提示发起时间', self.text)

    def test_midnight_boundaries_remain_in_the_correct_daily_bucket(self):
        spans = [x for x in self.data['segments'] if x['end'][:10] != x['date']]
        self.assertTrue(spans, 'The historical record should retain cross-midnight splitting')
        self.assertIn('24:00:00', self.text)
        self.assertIn('次日午夜记为当日24:00', self.text)

    def test_no_credentials_and_private_source_paths_are_exported(self):
        self.assertNotRegex(self.text, r'(?i)(sk-[a-z0-9]{20,}|-----BEGIN [A-Z ]*PRIVATE KEY|ssh-ed25519 AAAA)')
        self.assertNotRegex(self.text, r'(密码|password)\s*[:：=]\s*\S+')
        for private in ('/Users/', '/var/folders/', '.secrets/', '.ssh/', 'authorized_keys'):
            self.assertNotIn(private, self.text)
        self.assertNotIn('\ufffd', self.text)

    def test_page_size_numbers_headers_and_embedded_chinese_font(self):
        self.assertGreaterEqual(len(self.reader.pages), 15)
        self.assertLessEqual(len(self.reader.pages), 70)
        embedded = False
        for i, page in enumerate(self.reader.pages, 1):
            self.assertAlmostEqual(float(page.mediabox.width), 841.8898, delta=.1)
            self.assertAlmostEqual(float(page.mediabox.height), 595.2756, delta=.1)
            text = page.extract_text()
            self.assertIn('广州源泽药业有限公司', text)
            self.assertIn(f'{i} / {len(self.reader.pages)}', text)
            self.assertGreater(len(compact(text)), 160, f'Unexpected nearly empty page {i}')
            fonts = page['/Resources']['/Font'].get_object()
            for font in fonts.values():
                desc = font.get_object().get('/FontDescriptor')
                if desc and desc.get_object().get('/FontFile2'):
                    embedded = True
        self.assertTrue(embedded, 'Chinese font is not embedded')

    def test_all_text_is_inside_page_and_printable_margin(self):
        with pdfplumber.open(PDF) as pdf:
            for page in pdf.pages:
                for char in page.chars:
                    if not char.get('text', '').strip():
                        continue
                    with self.subTest(page=page.page_number, char=char['text']):
                        self.assertGreaterEqual(char['x0'], 31)
                        self.assertLessEqual(char['x1'], page.width - 31)
                        self.assertGreaterEqual(char['top'], 10)
                        self.assertLessEqual(char['bottom'], page.height - 10)


if __name__ == '__main__':
    unittest.main()
