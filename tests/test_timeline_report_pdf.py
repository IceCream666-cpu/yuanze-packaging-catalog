"""Verify complete chronological reader output, exact clocks and print geometry."""
from datetime import datetime
import json
from pathlib import Path
import re
import unittest

import pdfplumber
from pypdf import PdfReader

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / 'docs/包材库时间线汇报-20261013.json'
PDF = ROOT / 'output/pdf/源泽包材库_时间线汇报_20260922-20261013.pdf'


def compact(value):
    return re.sub(r'\s+', '', str(value))


class TimelinePdfTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = json.loads(DATA.read_text())
        cls.reader = PdfReader(PDF)
        cls.text = '\n'.join(x.extract_text() for x in cls.reader.pages)
        # LongTable repeats column headings after page splits. Remove page
        # furniture before checking uninterrupted source paragraphs.
        body = cls.text
        for item in ('YUANZE  /  广州源泽药业有限公司', '包材库时间线汇报 · 内部资料',
                     '2026-09-22 至 2026-10-13  |  北京时间  |  事件时间与截至状态分别列示',
                     '事件时间／编号', '提示目的／模块', '任务起止／共享时长',
                     '具体操作与核对依据', '截至状态与关联成果'):
            body = body.replace(item, '')
        body = re.sub(r'\n\d+ / \d+\n', '\n', body)
        cls.compact = compact(body)
        # A row split across pages yields fragments in several columns. Read
        # each column stream separately to prove complete paragraph coverage
        # without falsely treating intervening cells as missing source text.
        widths = [82, 141, 157, 212, 841.8898 - 64 - 592]
        bounds = [32]
        for width in widths:
            bounds.append(bounds[-1] + width)
        streams = [''] * len(widths)
        headings = ['事件时间／编号', '提示目的／模块', '任务起止／共享时长', '具体操作与核对依据', '截至状态与关联成果']
        with pdfplumber.open(PDF) as pdf:
            for page in pdf.pages:
                for i, (left, right) in enumerate(zip(bounds, bounds[1:])):
                    text = compact(page.crop((left, 47, right, page.height - 49)).extract_text() or '')
                    for heading in headings:
                        text = text.replace(compact(heading), '')
                    streams[i] += text
        cls.compact += ''.join(streams)

    def test_every_event_purpose_clock_status_and_evidence_present(self):
        positions = []
        for e in self.data['events']:
            with self.subTest(event=e['id']):
                for key in ('id', 'clock', 'event_type', 'purpose', 'operation', 'status', 'evidence', 'time_basis'):
                    self.assertTrue(compact(e[key]) in self.compact, f'{e["id"]}.{key} missing: {e[key]}')
                identifier = e['request_id'] or e['commit_id']
                self.assertIn(identifier, self.text)
                positions.append(compact(self.text).index(e['id']))
        self.assertEqual(positions, sorted(positions), 'Reader event order is not chronological')

    def test_every_update_purpose_operation_status_result_and_source_present(self):
        updates = [u for e in self.data['events'] for u in e['updates']]
        self.assertEqual(len(updates), 114)
        self.assertEqual(len(set(x['id'] for x in updates)), 114)
        for u in updates:
            for key in ('id', 'date', 'module', 'purpose', 'change', 'status', 'result', 'evidence'):
                with self.subTest(update=u['id'], field=key):
                    self.assertTrue(compact(u[key]) in self.compact, f'{u["id"]}.{key} missing: {u[key]}')
        self.assertIn('关联成果（截至统计截止）', self.text)
        self.assertIn('不代表在该秒已完成或已上线', self.text)

    def test_all_task_timestamps_are_fully_dated_and_activity_is_shared(self):
        for e in self.data['events']:
            t = e['task']
            if not t:
                continue
            for key in ('start', 'end'):
                expected = datetime.fromisoformat(t[key]).strftime('%Y-%m-%d %H:%M:%S')
                self.assertTrue(compact(expected) in self.compact, f'{t["id"]}.{key}: {expected}')
            self.assertIn(t['id'], self.text)
            self.assertTrue(compact(t['basis']) in self.compact, f'{t["id"]} basis missing')
            self.assertIn(compact(t['lifecycle']), self.compact)
        self.assertIn('共享时长不能逐行相加', self.text)
        self.assertIn('不是员工实际人工工时', self.text)

    def test_days_method_notes_pending_and_union_segments_complete(self):
        for d in self.data['days']:
            self.assertIn(d['date'], self.text)
        for text in self.data['method_notes'] + self.data['pending']:
            self.assertIn(compact(text), self.compact)
        for span in self.data['segments']:
            self.assertIn(span['id'], self.text)
            self.assertIn(f"{span['minutes']:.4f}", self.text)
        self.assertIn('52:08:18', self.text)
        self.assertIn('24:00:00', self.text)

    def test_image_batches_operations_and_parallel_windows_are_complete(self):
        self.assertEqual(len(self.data['image_batches']), 9)
        for row in self.data['image_batches'] + self.data['image_operations']:
            for key in ('batch_id', 'title', 'batch_kind', 'project_label', 'time_basis', 'status', 'number_basis'):
                self.assertTrue(compact(row[key]) in self.compact, f'{row["batch_id"]}.{key} missing')
            for key in ('first_started_at', 'last_finished_at', 'verification_time'):
                if row.get(key):
                    value = datetime.fromisoformat(row[key]).strftime('%Y-%m-%d %H:%M:%S')
                    self.assertTrue(compact(value) in self.compact, f'{row["batch_id"]}.{key} missing')
            for identifier in row.get('request_ids', []) + row.get('update_ids', []):
                self.assertIn(identifier, self.text)
        for text in self.data['image_method_notes']:
            self.assertTrue(compact(text) in self.compact, f'Image boundary missing: {text}')
        for window in self.data['parallel_windows']:
            self.assertTrue(compact(window['note']) in self.compact)
            for interval in window['intervals']:
                for key in ('start', 'end'):
                    value = datetime.fromisoformat(interval[key]).strftime('%Y-%m-%d %H:%M:%S')
                    self.assertTrue(compact(value) in self.compact, f'Parallel {key} missing: {value}')
        self.assertIn('用户同时打开多个Codex工程', self.text)
        self.assertTrue('526个合格版本' in self.compact)
        self.assertTrue('532个包材图片制作／编辑版本' in self.compact)
        self.assertIn('同步不是新增生成', self.text)

    def test_no_credentials_or_private_source_paths(self):
        self.assertNotRegex(self.text, r'(?i)(sk-[a-z0-9]{20,}|-----BEGIN [A-Z ]*PRIVATE KEY|ssh-ed25519 AAAA)')
        self.assertNotRegex(self.text, r'(密码|password)\s*[:：=]\s*\S+')
        for private in ('/Users/', '/var/folders/', '.secrets/', '.ssh/', 'authorized_keys'):
            self.assertNotIn(private, self.text)
        self.assertNotIn('\ufffd', self.text)

    def test_pages_numbered_landscape_and_chinese_font_embedded(self):
        self.assertGreaterEqual(len(self.reader.pages), 16)
        self.assertLessEqual(len(self.reader.pages), 120)
        embedded = False
        for i, page in enumerate(self.reader.pages, 1):
            self.assertAlmostEqual(float(page.mediabox.width), 841.8898, delta=.1)
            self.assertAlmostEqual(float(page.mediabox.height), 595.2756, delta=.1)
            text = page.extract_text()
            self.assertIn('广州源泽药业有限公司', text)
            self.assertIn(f'{i} / {len(self.reader.pages)}', text)
            self.assertGreater(len(compact(text)), 150, f'Nearly empty page {i}')
            for font in page['/Resources']['/Font'].get_object().values():
                desc = font.get_object().get('/FontDescriptor')
                if desc and desc.get_object().get('/FontFile2'):
                    embedded = True
        self.assertTrue(embedded)

    def test_all_text_inside_page_and_printable_margin(self):
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
