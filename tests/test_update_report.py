"""Content and artifact checks for the internal build-history report."""
import importlib.util
import json
from pathlib import Path
import re
import unittest

from pypdf import PdfReader

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / 'docs/建设更新日志-20261007.json'
PDF = ROOT / 'output/pdf/源泽包材库_建设与更新日志_20260922-20261007.pdf'


class UpdateReportTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = json.loads(DATA.read_text())
        cls.reader = PdfReader(PDF)
        cls.text = '\n'.join(page.extract_text() for page in cls.reader.pages)

    def test_all_milestones_and_evidence_are_present(self):
        sources = {row[0] for row in self.data['sources']}
        steps = [row for phase in self.data['phases'] for row in phase['rows']]
        self.assertEqual(len(steps), 71)
        compact = re.sub(r'\s+', '', self.text)
        for row in steps:
            self.assertIn(re.sub(r'\s+', '', row[1]), compact)
            self.assertTrue(set(row[4].split('/')) <= sources)
        for source in sources:
            self.assertIn(source, self.text)

    def test_entire_frozen_commit_history_is_included(self):
        spec = importlib.util.spec_from_file_location('history_builder', ROOT / 'scripts/build_update_report.py')
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        commits = module.commits_at_source(self.data['sourceHead'])
        self.assertEqual(len(commits), 37)
        for sha, _ in commits:
            self.assertIn(sha, self.text)

    def test_current_counts_and_remaining_work_are_reconciled(self):
        s = self.data['snapshot']
        self.assertEqual(s['activeRecords'] + s['archivedRecords'], s['totalRecords'])
        self.assertEqual(s['activePackageRecords'] + s['sourcePageRecords'] + s['processRuleRecords'] + s['otherRecords'], s['activeRecords'])
        self.assertEqual(s['activePackageRecords'] + s['archivedRecords'], s['productCodes'])
        self.assertEqual(s['imageQueuePublished'] + s['imageQueuePending'], s['imageQueueSources'])
        self.assertEqual(s['groupSourceRecords'] - s['sameStyleGroups'], s['reducedCards'])
        for word in ['5,286', '229', '公网域名', '方案阶段', '未实现', '待核对', '未备案']:
            self.assertIn(word, self.text)

    def test_no_credentials_or_private_keys_in_deliverable(self):
        serialized = json.dumps(self.data, ensure_ascii=False) + self.text
        self.assertNotRegex(serialized, r'(?i)(sk-[a-z0-9]{20,}|-----BEGIN [A-Z ]*PRIVATE KEY|ssh-ed25519 AAAA)')
        self.assertNotRegex(serialized, r'(密码|password)\s*[:：=]\s*\S+')

    def test_pdf_font_embedding_and_layout_bounds(self):
        self.assertGreaterEqual(len(self.reader.pages), 10)
        self.assertLessEqual(len(self.reader.pages), 30)
        for page in self.reader.pages:
            self.assertAlmostEqual(float(page.mediabox.width), 841.8898, delta=0.1)
            self.assertAlmostEqual(float(page.mediabox.height), 595.2756, delta=0.1)
            text = page.extract_text()
            self.assertGreater(len(re.sub(r'\s+', '', text)), 300, 'Unexpected mostly empty page')
            self.assertIn('广州源泽药业有限公司', text)
            self.assertNotIn('\ufffd', text)
            self.assertRegex(text, rf'\d+ / {len(self.reader.pages)}')
            self.assertTrue(page['/Resources']['/Font'])
        fonts = self.reader.pages[0]['/Resources']['/Font'].get_object()
        embedded = [v.get_object().get('/FontDescriptor') for v in fonts.values()]
        self.assertTrue(any(d and d.get_object().get('/FontFile2') for d in embedded))


if __name__ == '__main__':
    unittest.main()
