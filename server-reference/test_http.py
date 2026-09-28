import hashlib,http.client,json,secrets,tempfile,threading,unittest
from pathlib import Path
from test_server import server, isolated_catalog
class HTTP(unittest.TestCase):
 def setUp(self):
  self.temp=tempfile.TemporaryDirectory();server.STATE=Path(self.temp.name);server.LOCAL=False
  isolated_catalog(self,self.temp.name)
  self.password=secrets.token_urlsafe(20);salt=secrets.token_hex(16)
  server.STATE.joinpath('auth.json').write_text(json.dumps(dict(username='review',salt=salt,iterations=100000,hash=hashlib.pbkdf2_hmac('sha256',self.password.encode(),bytes.fromhex(salt),100000).hex())))
  bootstrap=json.loads(server.STATE.joinpath('auth.json').read_text());bootstrap['username']='review_admin'
  server.STATE.joinpath('admin-bootstrap.json').write_text(json.dumps(bootstrap))
  server.ATTEMPTS.clear();server.initialize()
  self.srv=server.ThreadingHTTPServer(('127.0.0.1',0),server.Handler);self.thread=threading.Thread(target=self.srv.serve_forever,daemon=True);self.thread.start()
  self.host='127.0.0.1:'+str(self.srv.server_port);self.cookie='';self.csrf=''
 def tearDown(self):self.srv.shutdown();self.srv.server_close();self.thread.join();self.temp.cleanup()
 def req(self,path,data=None,csrf=True):
  c=http.client.HTTPConnection(self.host);headers={'Origin':'https://'+self.host,'Cookie':self.cookie}
  if csrf:headers['X-CSRF-Token']=self.csrf
  c.request('GET' if data is None else 'POST',path,body=None if data is None else json.dumps(data),headers=headers)
  r=c.getresponse();status=r.status;h=dict(r.getheaders());raw=r.read();c.close()
  try:body=json.loads(raw)
  except ValueError:body=raw
  return status,h,body
 def login(self):
  code,h,_=self.req('/api/login',dict(username='review_admin',password=self.password));self.assertEqual(code,200)
  self.assertIn('Secure',h['Set-Cookie']);self.assertIn('HttpOnly',h['Set-Cookie']);self.cookie=h['Set-Cookie'].split(';')[0]
  self.csrf=self.req('/api/session')[2]['csrf']
 def test_private_routes_and_csrf(self):
  for path in ['/api/catalog','/media/image15.png','/api/samples']:self.assertEqual(self.req(path)[0],401)
  self.assertEqual(self.req('/business/index.html')[0],303)
  self.assertEqual(self.req('/api/login',dict(username='review',password='wrong'))[0],401)
  self.login();self.assertEqual(self.req('/api/catalog')[0],200)
  self.assertEqual(self.req('/api/preferences',{'favorites':[]},csrf=False)[0],403)
  self.assertEqual(self.req('/api/preferences',{'favorites':[]})[0],200)
  for path in ['/../private/catalog.json','/%2e%2e/private/catalog.json','/media/../catalog.json']:self.assertEqual(self.req(path)[0],404)
  self.assertEqual(self.req('/api/logout',{})[0],200);self.assertEqual(self.req('/api/catalog')[0],401)
 def test_history_is_per_sample_and_complete(self):
  with server.db() as c:
   for sid in ['OLD','NEW']:c.execute('INSERT INTO samples VALUES(?,?,?,?,?,?,?,?)',(sid,'R1','A','available','','','完好',server.now()))
   for sid,n in [('OLD',2),('NEW',305)]:
    for _ in range(n):c.execute('INSERT INTO movements(sample_id,action,actor,details,created) VALUES(?,?,?,?,?)',(sid,'register','test','{}',server.now()))
  self.login();code,_,rows=self.req('/api/samples/OLD/history');self.assertEqual(code,200);self.assertEqual(len(rows),2)
  self.assertEqual(len(self.req('/api/samples/NEW/history')[2]),305)
  self.assertEqual(self.req('/api/samples/ABSENT/history')[0],404)
 def test_saved_plan_and_sample_flow_survive_reinitialize(self):
  self.login();rid=server.CATALOG['records'][0]['id']
  self.assertEqual(self.req('/api/preferences',{'favorites':[rid]})[0],200)
  self.assertEqual(self.req('/api/plans',{'ids':[rid],'title':'验收方案','note':'测试数据'})[0],201)
  sample={'id':'验收/001','record_id':rid,'location':'A-1','condition':'完好'}
  self.assertEqual(self.req('/api/samples',sample)[0],201)
  path='/api/samples/%E9%AA%8C%E6%94%B6%2F001'
  self.assertEqual(self.req(path+'/lend',{'borrower':'验收员','due':'2026-10-01'})[0],200)
  self.assertEqual(self.req(path+'/return',{'location':'B-1','condition':'完好'})[0],200)
  server.initialize()
  self.assertEqual(self.req('/api/preferences')[2]['favorites'],[rid])
  self.assertEqual(self.req('/api/plans')[2][0]['snapshot'][0]['id'],rid)
  self.assertEqual(self.req('/api/samples')[2]['samples'][0]['location'],'B-1')
  self.assertEqual(len(self.req(path+'/history')[2]),3)
if __name__=='__main__':unittest.main()
