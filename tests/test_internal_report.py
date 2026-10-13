"""Evidence reconciliation for the frozen 2026-10-13 internal report."""
from datetime import datetime
import importlib.util
import json
from pathlib import Path
import re
import unittest
import xml.etree.ElementTree as ET
import zipfile

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / 'docs/包材库内部汇报-20261013.json'
XLSX = ROOT / 'outputs/internal-report-20261013/源泽包材库_更新微调与工作时段汇报_20260922-20261013.xlsx'
NS = {'m':'http://schemas.openxmlformats.org/spreadsheetml/2006/main'}


class InternalReportEvidenceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data=json.loads(DATA.read_text())

    def test_all_curated_update_and_prompt_purposes_are_present(self):
        d=self.data
        self.assertEqual(len(d['updates']),114)
        self.assertEqual(len(d['requests']),183)
        self.assertEqual([x['id'] for x in d['updates']],[f'U{i:03d}' for i in range(1,115)])
        self.assertEqual([x['id'] for x in d['requests']],[f'P{i:03d}' for i in range(13,196)])
        for row in d['updates']:
            for key in ('purpose','change','result','status','evidence','time_note'):
                self.assertTrue(row[key],(row['id'],key))
        task_ids={x['id'] for x in d['tasks']}
        self.assertEqual(len(task_ids),len(d['tasks']))
        self.assertTrue(all(x['task_id'] in task_ids for x in d['requests']))
        self.assertTrue(all(set(x['task_ids']) <= task_ids for x in d['updates']))
        self.assertEqual(d['totals']['request_count'],len(d['requests']))

    def test_all_legacy_packaging_updates_preserved_without_erp_scope(self):
        legacy=json.loads((ROOT/'docs/建设更新日志-20261007.json').read_text())
        expected=[r[1] for pi,p in enumerate(legacy['phases']) for ri,r in enumerate(p['rows']) if not(pi==0 and ri<2)]
        self.assertEqual([x['module'] for x in self.data['updates'][:69]],expected)
        self.assertEqual(self.data['excluded']['legacy_erp_update_count'],2)
        self.assertTrue(self.data['excluded']['report_generation_excluded'])
        self.assertTrue(all(x['time'] >= '2026-09-22T20:30:56' for x in self.data['requests']))

    def test_deduplicated_intervals_reconcile_without_midnight_or_overlap_errors(self):
        segments=self.data['segments']; total=0; previous=None
        for x in segments:
            a,b=map(datetime.fromisoformat,(x['start'],x['end']))
            self.assertLess(a,b)
            self.assertEqual(a.utcoffset().total_seconds(),28800)
            self.assertEqual(a.date().isoformat(),x['date'])
            self.assertTrue(a.date()==b.date() or b.hour==b.minute==b.second==0)
            if previous:self.assertLessEqual(previous,a,'Parallel activity double-counted')
            previous=b
            seconds=(b-a).total_seconds(); total+=seconds
            self.assertAlmostEqual(x['minutes'],seconds/60,places=5)
        self.assertAlmostEqual(self.data['totals']['deduplicated_minutes'],total/60,places=5)
        self.assertAlmostEqual(self.data['totals']['deduplicated_hours'],total/3600,places=5)
        self.assertEqual(len(segments),self.data['totals']['segment_count'])
        self.assertAlmostEqual(sum(x['minutes'] for x in self.data['daily']),total/60,places=4)
        self.assertEqual(self.data['as_of'],segments[-1]['end'])
        self.assertLess(datetime.fromisoformat(self.data['as_of']),datetime.fromisoformat('2026-10-13T02:00:00+08:00'))

    def test_shared_task_links_do_not_claim_independent_labour_hours(self):
        rows={x['id']:x for x in self.data['updates']}
        self.assertEqual(rows['U111']['task_ids'],rows['U114']['task_ids'])
        self.assertIn('共享',rows['U111']['time_note'])
        self.assertIn('不能跨事项相加',rows['U114']['time_note'])
        self.assertIn('不是员工实际人工工时',''.join(self.data['method_notes']))
        self.assertIn('不用Git时间差',''.join(self.data['method_notes']))

    def test_historical_results_and_pending_work_are_not_reported_as_current_complete(self):
        rows={x['id']:x for x in self.data['updates']}
        self.assertNotIn('截至本报告仍未解决',rows['U034']['result'])
        self.assertIn('10-13',rows['U034']['result'])
        self.assertIn('待用户补充',rows['U097']['status'])
        self.assertIn('方案',rows['U102']['status'])
        pending='；'.join(self.data['pending'])
        for word in ['业务员专属','真实询盘','全库图片','15张','公司首页']:
            self.assertIn(word,pending)
        self.assertIn('历史快照',self.data['historical_snapshot']['label'])
        self.assertNotIn('10-07建设日志',rows['U111']['evidence'])

    def test_reader_data_has_no_credentials_raw_chat_or_private_user_paths(self):
        text=json.dumps(self.data,ensure_ascii=False)
        self.assertNotRegex(text,r'(?i)(sk-[a-z0-9]{20,}|-----BEGIN [A-Z ]*PRIVATE KEY|ssh-ed25519 AAAA)')
        self.assertNotRegex(text,r'(?:密码|password|API KEY)\s*[:：=]\s*\S+')
        self.assertNotIn('/Users/',text)
        self.assertNotIn('<send_user_message_question_reply>',text)
        self.assertNotIn('<in-app-browser-context',text)
        # No opaque alphanumeric credential values in prompt summaries, even if
        # the original user message had no password label.
        for p in self.data['requests']:
            self.assertNotRegex(p['purpose'],r'(?i)\b[a-z]{3,}\d{3,}\b')

    def test_merge_function_handles_nested_parallel_turns_and_idle_gaps(self):
        spec=importlib.util.spec_from_file_location('report_prepare',ROOT/'scripts/prepare_internal_report.py')
        m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
        self.assertEqual(m.merge_intervals([(0,60),(10,50),(50,100),(200,230),(210,240),(9,9)]),[[0,100],[200,240]])
        self.assertAlmostEqual(m.minutes([(0,60),(20,80),(200,260)]),140/60)


class InternalReportWorkbookTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not XLSX.exists():
            raise unittest.SkipTest('Editable XLSX is a local generated deliverable; run workbook builder to inspect it')
        cls.archive=zipfile.ZipFile(XLSX)
        cls.data=json.loads(DATA.read_text())
        strings=ET.fromstring(cls.archive.read('xl/sharedStrings.xml'))
        cls.strings=[''.join(s.itertext()) for s in strings]
        for name in cls.archive.namelist():
            if name.startswith('xl/worksheets/') and name.endswith('.xml'):
                cls.strings.extend(''.join(s.itertext()) for s in ET.fromstring(cls.archive.read(name)).findall('.//m:is',NS))
                cls.strings.extend(s.findtext('m:v',default='',namespaces=NS) for s in ET.fromstring(cls.archive.read(name)).findall('.//m:c[@t="str"]',NS))
        cls.book=ET.fromstring(cls.archive.read('xl/workbook.xml'))

    @classmethod
    def tearDownClass(cls):
        if hasattr(cls,'archive'):cls.archive.close()

    def _sheet(self,n):
        return ET.fromstring(self.archive.read(f'xl/worksheets/sheet{n}.xml'))

    def test_exported_tabs_tables_filters_freeze_and_all_purpose_rows(self):
        names=[s.attrib['name'] for s in self.book.find('m:sheets',NS)]
        self.assertEqual(names,['汇报总览','更新与微调','提示词目的','任务时段','去重时段'])
        joined='\n'.join(self.strings)
        for kind in ('updates','requests'):
            for row in self.data[kind]:
                self.assertIn(row['id'],joined)
                self.assertIn(row['purpose'],joined)
        for n in range(2,6):
            sh=self._sheet(n)
            self.assertIsNotNone(sh.find('m:sheetViews/m:sheetView/m:pane',NS))
            self.assertIsNotNone(sh.find('m:tableParts',NS))
        for f in self.archive.namelist():
            if re.match(r'xl/tables/table\d+\.xml$',f):
                self.assertIsNotNone(ET.fromstring(self.archive.read(f)).find('m:autoFilter',NS))

    def test_cached_calculations_no_excel_errors_and_correct_local_dates(self):
        for name in self.archive.namelist():
            if name.startswith('xl/worksheets/') and name.endswith('.xml'):
                xml=ET.fromstring(self.archive.read(name))
                self.assertFalse(xml.findall('.//m:c[@t="e"]',NS),name)
        summary=self._sheet(1)
        vals={c.attrib['r']:c.findtext('m:v',namespaces=NS) for c in summary.findall('.//m:c',NS)}
        self.assertAlmostEqual(float(vals['C11']),self.data['totals']['deduplicated_minutes'],delta=.001)
        self.assertAlmostEqual(float(vals['C12']),self.data['totals']['deduplicated_hours'],delta=.001)
        first=self._sheet(5).find('.//m:c[@r="C6"]',NS)
        expected=datetime.fromisoformat(self.data['segments'][0]['start']).replace(tzinfo=None)
        value=first.findtext('m:v',namespaces=NS)
        if first.attrib.get('t')=='d':
            actual=datetime.fromisoformat(value.replace('Z','+00:00')).replace(tzinfo=None)
            self.assertAlmostEqual((actual-expected).total_seconds(),0,places=3,msg='Date was shifted by the host timezone')
        else:
            actual_days=(expected-datetime(1899,12,30)).total_seconds()/86400
            self.assertAlmostEqual(float(value),actual_days,places=6,msg='Date was shifted by the host timezone')


if __name__=='__main__':unittest.main()
