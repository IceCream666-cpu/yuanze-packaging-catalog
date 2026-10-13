"""Chronology, concurrency and image production reconciliation for the report."""
from collections import Counter
from datetime import datetime
import hashlib
import json
from pathlib import Path
import re
import unittest
import xml.etree.ElementTree as ET
import zipfile

ROOT=Path(__file__).resolve().parents[1]
DATA=ROOT/'docs/包材库时间线汇报-20261013.json'
BASE=ROOT/'docs/包材库内部汇报-20261013.json'
XLSX=ROOT/'outputs/timeline-report-20261013/源泽包材库_时间线汇报_20260922-20261013.xlsx'
NS={'m':'http://schemas.openxmlformats.org/spreadsheetml/2006/main'}


class TimelineEvidenceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data=json.loads(DATA.read_text());cls.base=json.loads(BASE.read_text())

    def test_all_events_use_exact_source_clocks_and_sort_chronologically(self):
        d=self.data; by_request={p['id']:p for p in self.base['requests']};by_commit={c['id']:c for c in self.base['commits']}
        self.assertEqual(len(d['events']),248)
        times=[datetime.fromisoformat(e['time']).timestamp() for e in d['events']]
        self.assertEqual(times,sorted(times))
        self.assertEqual([e['id'] for e in d['events']],[f'E{i:03d}' for i in range(1,249)])
        for e in d['events']:
            with self.subTest(event=e['id']):
                original=by_request[e['request_id']] if e['request_id'] else by_commit[e['commit_id']]
                self.assertEqual(e['time'],original['time'])
                dt=datetime.fromisoformat(e['time']);self.assertEqual(e['date'],dt.strftime('%Y-%m-%d'));self.assertEqual(e['clock'],dt.strftime('%H:%M:%S'))
        self.assertEqual(len([e for e in d['events'] if e['request_id']]),183)
        self.assertEqual(len([e for e in d['events'] if e['commit_id']]),65)

    def test_every_update_has_one_timeline_owner_without_faked_completion_time(self):
        ids=[u['id'] for e in self.data['events'] for u in e['updates']]
        self.assertEqual(Counter(ids),Counter(u['id'] for u in self.base['updates']))
        self.assertTrue(all(n==1 for n in Counter(ids).values()))
        self.assertIn('不表示该功能已在左列需求时刻完成',''.join(self.data['method_notes']))
        self.assertEqual(self.data['base_data_sha256'],hashlib.sha256(BASE.read_bytes()).hexdigest())
        self.assertEqual(self.data['totals']['deduplicated_seconds'],187698.067)

    def test_activity_only_date_and_parallel_projects_remain_visible(self):
        d=self.data;self.assertEqual(len(d['days']),16)
        continuation=next(x for x in d['days'] if x['date']=='2026-09-25')
        self.assertEqual(continuation['event_ids'],[]);self.assertGreater(continuation['activity_summary']['minutes'],0)
        projects={e['project_session_short'] for e in d['events'] if e['request_id']}
        self.assertEqual(projects,{'01a0c869','01a1147a','01a11546','01a11550','01a1156d','01a0e639'})
        p119=next(e for e in d['events'] if e['request_id']=='P119')
        self.assertIn('尾批图片',p119['project_label'])

    def test_image_quantities_distinguish_versions_sources_operations_and_snapshots(self):
        d=self.data;s=d['image_summary'];b={x['batch_id']:x for x in d['image_batches']}
        self.assertEqual([x['produced_versions'] for x in d['image_batches']],[17,3,4,200,200,50,50,6,2])
        self.assertEqual(sum(x['produced_versions'] for x in d['image_batches']),532)
        self.assertEqual(sum(x['produced_versions'] for x in d['image_batches'] if x['batch_kind']!='规格标注编辑'),526)
        self.assertEqual(s['through_20261008_batch_style_versions'],524)
        self.assertEqual(s['through_20261008_batch_style_unique_source_sha256'],523)
        self.assertEqual(s['eight_batches_total_versions'],530);self.assertEqual(s['eight_batches_unique_sources'],528)
        self.assertEqual(s['through_20261013_verified_product_edit_unique_sources_including_annotations'],529)
        self.assertEqual(b['I04']['new_unique_sources'],199);self.assertEqual(b['I04']['reprocessed_sources'],1)
        self.assertEqual(b['I04']['product_associations'],253);self.assertEqual(b['I04']['unique_product_record_count'],217)
        self.assertEqual(b['I09']['produced_versions'],2);self.assertEqual(b['I09']['unique_sources_in_batch'],1)
        self.assertEqual(b['I08']['generation_tool'],'built-in imagegen')
        self.assertEqual(len(d['image_operations']),5)

    def test_parallel_windows_show_cross_project_overlap_without_invented_output(self):
        d=self.data;self.assertEqual(len(d['parallel_windows']),8)
        pair=next(x for x in d['parallel_windows'] if x['batch_ids']==['I04','I05'])
        self.assertEqual(pair['intervals'][0]['start'],'2026-10-07T11:55:47+08:00')
        self.assertEqual(pair['intervals'][0]['end'],'2026-10-07T14:21:47+08:00')
        for p in d['parallel_windows']:
            self.assertIsNone(p['count_during_overlap'])
            self.assertIn('未逐张统计',p['note'])
            for x in p['intervals']:self.assertLess(datetime.fromisoformat(x['start']),datetime.fromisoformat(x['end']))
        for b in d['image_batches'][:3]:self.assertIn('共用T070',b['time_basis'])

    def test_public_timeline_has_no_credentials_or_private_user_paths(self):
        text=json.dumps(self.data,ensure_ascii=False)
        self.assertNotRegex(text,r'(?i)(sk-[a-z0-9]{20,}|-----BEGIN [A-Z ]*PRIVATE KEY|ssh-ed25519 AAAA)')
        self.assertFalse('/Users/' in text,'Private user path leaked');self.assertFalse('/var/folders/' in text,'Private temp path leaked')
        self.assertNotRegex(text,r'(密码|password)\s*[:：=]\s*\S+')


class TimelineWorkbookTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not XLSX.exists():raise unittest.SkipTest('Local generated editable workbook not present')
        cls.z=zipfile.ZipFile(XLSX);cls.data=json.loads(DATA.read_text())
    @classmethod
    def tearDownClass(cls):
        if hasattr(cls,'z'):cls.z.close()
    def sheet(self,n):return ET.fromstring(self.z.read(f'xl/worksheets/sheet{n}.xml'))
    def value(self,n,cell):return self.sheet(n).find(f'.//m:c[@r="{cell}"]',NS).findtext('m:v',namespaces=NS)
    def test_rows_and_dates_and_counts_are_exported(self):
        book=ET.fromstring(self.z.read('xl/workbook.xml'))
        self.assertEqual([x.attrib['name'] for x in book.find('m:sheets',NS)],['时间线汇报','图片批次与并行','每日与时段'])
        alltext='\n'.join(self.z.read(n).decode() for n in self.z.namelist() if n.startswith('xl/worksheets/') and n.endswith('.xml'))
        for e in self.data['events']:
            self.assertIn(e['id'],alltext);self.assertIn(e['purpose'],alltext)
            for u in e['updates']:self.assertIn(u['id'],alltext)
        for b in self.data['image_batches']:self.assertIn(b['batch_id'],alltext)
        self.assertEqual(datetime.fromisoformat(self.value(1,'C8').replace('Z','+00:00')).strftime('%Y-%m-%d %H:%M:%S'),'2026-09-22 20:30:56')
        self.assertEqual(float(self.value(2,'C4')),526);self.assertEqual(float(self.value(2,'G4')),6);self.assertEqual(float(self.value(2,'K4')),532)
        self.assertAlmostEqual(float(self.value(3,'E4')),self.data['totals']['deduplicated_minutes'],delta=.001)
        for n in range(1,4):self.assertIsNotNone(self.sheet(n).find('m:sheetViews/m:sheetView/m:pane',NS))
    def test_no_excel_formula_errors(self):
        for n in range(1,4):self.assertFalse(self.sheet(n).findall('.//m:c[@t="e"]',NS))
        for name in self.z.namelist():
            if name.startswith('xl/tables/table') and name.endswith('.xml'):
                columns=[x.attrib['name'] for x in ET.fromstring(self.z.read(name)).find('m:tableColumns',NS)]
                self.assertEqual(len(columns),len(set(columns)),'Duplicate table headers can cause Excel repair')


if __name__=='__main__':unittest.main()
