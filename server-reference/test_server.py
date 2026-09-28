import importlib.util, json, tempfile, unittest
from pathlib import Path
from unittest.mock import patch
spec=importlib.util.spec_from_file_location('server',Path(__file__).with_name('server.py'))
server=importlib.util.module_from_spec(spec);spec.loader.exec_module(server)

def isolated_catalog(test, root):
 """Keep test runs independent of private local or production catalogues."""
 private=Path(root)/'test-private';private.mkdir()
 catalog={'meta':{},'records':[{'id':'TEST-BOTTLE-1','name':'虚构测试瓶','kind':'package','capacityMl':100,'materials':['PET'],'images':[]}]}
 (private/'catalog.json').write_text(json.dumps(catalog),encoding='utf-8')
 replacement=patch.multiple(server,PRIVATE=private,CATALOG=catalog)
 replacement.start();test.addCleanup(replacement.stop)

class Samples(unittest.TestCase):
 def setUp(self):
  self.temp=tempfile.TemporaryDirectory();isolated_catalog(self,self.temp.name);server.STATE=Path(self.temp.name);server.LOCAL=True;server.initialize()
  with server.db() as c:c.execute('INSERT INTO samples VALUES(?,?,?,?,?,?,?,?)',('S1','R1','A-1','available','','','完好',server.now()))
 def tearDown(self):self.temp.cleanup()
 def get(self):
  with server.db() as c:return dict(c.execute('SELECT * FROM samples WHERE id=?',('S1',)).fetchone())
 def test_borrow_return(self):
  server.change_sample('S1','lend',{'borrower':'测试借用人','due':'2026-10-01'},'test')
  self.assertEqual(self.get()['status'],'lent')
  server.change_sample('S1','return',{'location':'B-2','condition':'完好'},'test')
  self.assertEqual(self.get()['location'],'B-2');self.assertEqual(self.get()['status'],'available')
 def test_double_borrow_rejected(self):
  server.change_sample('S1','lend',{'borrower':'甲','due':'2026-10-01'},'test')
  with self.assertRaises(ValueError):server.change_sample('S1','lend',{'borrower':'乙','due':'2026-10-02'},'test')
  self.assertEqual(self.get()['borrower'],'甲')
 def test_missing_return_location_preserves_record(self):
  server.change_sample('S1','lend',{'borrower':'甲','due':'2026-10-01'},'test');before=self.get()
  with self.assertRaises(ValueError):server.change_sample('S1','return',{'location':'','condition':'完好'},'test')
  self.assertEqual(self.get(),before)
 def test_sent_not_returnable(self):
  server.change_sample('S1','sent',{'note':'寄客户试装'},'test')
  with self.assertRaises(ValueError):server.change_sample('S1','return',{'location':'A-1','condition':'完好'},'test')
  self.assertEqual(self.get()['status'],'sent')
 def test_flow_events_persist(self):
  server.change_sample('S1','consumed',{'note':'测试耗用'},'test')
  server.initialize()
  self.assertEqual(self.get()['status'],'consumed')
  with server.db() as c:self.assertEqual(c.execute('SELECT COUNT(*) FROM movements').fetchone()[0],1)
 def test_db_helper_closes_its_connection(self):
  import sqlite3
  with server.db() as c:self.assertEqual(c.execute('SELECT COUNT(*) FROM samples').fetchone()[0],1)
  with self.assertRaises(sqlite3.ProgrammingError):c.execute('SELECT 1')
if __name__=='__main__':unittest.main()
