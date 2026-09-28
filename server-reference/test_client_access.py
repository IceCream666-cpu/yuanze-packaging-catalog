"""Customer access regressions, using synthetic accounts and images only."""
from contextlib import redirect_stdout
import http.client, io, json, secrets, tempfile, threading, time, unittest
from pathlib import Path
from unittest.mock import patch
from PIL import Image, PngImagePlugin
from client_catalog import safe_capacity
from test_admin_store import credentials, PASSWORD
from test_server import server

class ClientAccess(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        state=Path(self.temp.name)/'state'; private=Path(self.temp.name)/'private'
        state.mkdir(); (private/'media').mkdir(parents=True)
        meta=PngImagePlugin.PngInfo(); meta.add_text('supplier','PRIVATE-SUPPLIER-SECRET')
        Image.new('RGB',(100,150),'#164b47').save(private/'media/supplier-secret.png',pnginfo=meta)
        Image.new('RGB',(50,50),'white').save(private/'media/unapproved.png')
        image={'path':'media/supplier-secret.png','role':'product','missing':False,'clientVisible':True}
        records=[{'id':'INTERNAL-1','name':'PRIVATE-NAME','kind':'package','capacityMl':100,
            'supplierRaw':'PRIVATE-SUPPLIER','unitPrice':9.99,'quoteRaw':'PRIVATE-QUOTE','images':[image,{'path':'media/unapproved.png','role':'product'}]},
            {'id':'INTERNAL-2','name':'hidden','kind':'package','images':[{'path':'media/unapproved.png'}]},
            {'id':'INTERNAL-3','name':'source','kind':'source_page','images':[image]}]
        (private/'catalog.json').write_text(json.dumps({'meta':{},'records':records}))
        (state/'auth.json').write_text(json.dumps(credentials('employee')))
        (state/'admin-bootstrap.json').write_text(json.dumps(credentials('admin')))
        patches=patch.multiple(server,STATE=state,PRIVATE=private,LOCAL=False); patches.start();self.addCleanup(patches.stop)
        server.ATTEMPTS.clear();server.initialize()
        server.STORE.mutate('users','save',{'id':'client-test','version':0,'password':PASSWORD,'role':'client'},'admin')
        self.srv=server.ThreadingHTTPServer(('127.0.0.1',0),server.Handler)
        self.thread=threading.Thread(target=self.srv.serve_forever,daemon=True);self.thread.start()
        self.host='127.0.0.1:'+str(self.srv.server_port);self.cookie='';self.csrf=''
    def tearDown(self):
        self.srv.shutdown();self.srv.server_close();self.thread.join()
    def req(self,path,data=None,method=None):
        c=http.client.HTTPConnection(self.host)
        c.request(method or ('GET' if data is None else 'POST'),path,body=None if data is None else json.dumps(data),
            headers={'Origin':'https://'+self.host,'Cookie':self.cookie,'X-CSRF-Token':self.csrf})
        r=c.getresponse(); result=r.status,dict(r.getheaders()),r.read();c.close();return result
    def login(self,username='client-test'):
        code,headers,raw=self.req('/api/login',{'username':username,'password':PASSWORD});self.assertEqual(code,200,raw)
        self.cookie=headers['Set-Cookie'].split(';')[0];session=json.loads(self.req('/api/session')[2]);self.csrf=session['csrf'];return session
    def catalog(self):
        code,_,raw=self.req('/api/client/catalog');self.assertEqual(code,200,raw);return json.loads(raw)
    def test_projection_opaque_ids_and_pagination(self):
        self.assertEqual(self.req('/api/client/catalog')[0],401);self.assertEqual(self.login()['role'],'client')
        catalog=self.catalog();self.assertEqual(set(catalog),{'items','page','pages','total'});self.assertEqual(catalog['total'],1)
        item=catalog['items'][0];self.assertEqual(set(item),{'id','capacity','images'});self.assertEqual(item['capacity'],'100 mL')
        self.assertEqual(len(item['images']),1);self.assertEqual(set(item['images'][0]),{'url'})
        self.assertRegex(item['images'][0]['url'],r'^/client-media/[a-f0-9]{64}\.jpg$')
        for secret in ['INTERNAL','supplier','PRIVATE','price','quote','raw','source','9.99']:
            self.assertNotIn(secret,json.dumps(catalog))
        for query in ['page=-1','page=bad','pageSize=0']:self.assertEqual(self.req('/api/client/catalog?'+query)[0],400)
        self.assertEqual(json.loads(self.req('/api/client/catalog?page=999&pageSize=999')[2])['page'],1)
    def test_get_head_post_alt_verbs_fail_closed(self):
        self.login()
        paths=['/api/catalog','/api/admin/records','/api/admin/users','/api/admin/export','/api/image-search/status',
            '/api/preferences','/api/plans','/api/samples','/api/samples/S1/history','/media/supplier-secret.png',
            '/uploads/abcdef0123456789.jpg','/media/%2e%2e/catalog.json','/client-media/../media/supplier-secret.png',
            '/client-media/%2e%2e%2fkey','/%2e%2e/private/catalog.json','/client.js/../app.js','/app.js','/admin','/admin.js','/business/index.html']
        for path in paths:
            for method in ['GET','HEAD']:
                with self.subTest(path=path,method=method):self.assertIn(self.req(path,method=method)[0],[403,404])
        with patch.object(server.STORE,'catalog') as loader,patch.object(server.IMAGE_SEARCH,'search_request') as search:
            for path in ['/api/catalog','/api/preferences','/api/plans','/api/samples','/api/admin/records','/api/image-search','/api/client/catalog']:
                self.assertEqual(self.req(path,{'unused':'x'})[0],403,path)
            loader.assert_not_called();search.assert_not_called()
        for verb in ['PUT','PATCH','DELETE','OPTIONS','TRACE','CONNECT']:
            self.assertEqual(self.req('/api/admin/users',{},method=verb)[0],403)
    def test_redirects_logout_admin_preview_and_employee_unchanged(self):
        self.login()
        for path in ['/','/index.html','/catalog','/?code=YZ-BC-000001','/login?code=YZ-BC-000001','/login.html']:
            code,headers,_=self.req(path);self.assertEqual(code,303,path);self.assertEqual(headers['Location'],'/client')
        self.assertEqual(self.req('/api/logout',{})[0],200);self.assertEqual(self.req('/api/client/catalog')[0],401)
        self.login('admin');self.assertEqual(self.catalog()['total'],1);self.assertEqual(self.req('/api/catalog')[0],200)
        self.login('employee');self.assertEqual(self.req('/api/catalog')[0],200);self.assertEqual(self.req('/api/admin/users')[0],403)
    def test_reencoding_and_immediate_cached_image_revocation(self):
        self.login();url=self.catalog()['items'][0]['images'][0]['url']
        code,headers,raw=self.req(url);self.assertEqual(code,200);self.assertEqual(headers['Content-Type'],'image/jpeg')
        self.assertNotIn(b'PRIVATE-SUPPLIER',raw);self.assertNotIn('Content-Disposition',headers)
        with Image.open(io.BytesIO(raw)) as im:self.assertEqual(im.size,(100,150));self.assertFalse(im.getexif())
        self.assertEqual(self.req(url,method='HEAD')[0],200)
        record=server.STORE.read_admin('records',id='INTERNAL-1');record['images'][0]['clientVisible']=False
        saved=server.STORE.mutate('records','save',{'id':record['id'],'version':record['version'],'record':{'images':record['images']}},'admin')
        self.assertEqual(self.req(url)[0],404);self.assertEqual(self.catalog()['total'],0)
        saved['images'][0]['clientVisible']=True
        saved=server.STORE.mutate('records','save',{'id':saved['id'],'version':saved['version'],'record':{'images':saved['images']}},'admin')
        self.assertEqual(self.req(url)[0],200)
        server.STORE.mutate('records','archive',{'id':saved['id'],'version':saved['version']},'admin')
        self.assertEqual(self.req(url)[0],404)
    def test_media_bounded_and_unknown_handles_denied(self):
        self.login();url=self.catalog()['items'][0]['images'][0]['url']
        server.CLIENT_CATALOG.waiters=threading.BoundedSemaphore(1)
        with server.CLIENT_CATALOG.waiters:
            code,headers,_=self.req(url);self.assertEqual(code,429);self.assertEqual(headers['Retry-After'],'2')
        self.assertEqual(self.req('/client-media/'+'a'*64+'.jpg')[0],404)
    def test_admin_account_role_approval_validation_password_policy(self):
        self.login('admin')
        code,_,raw=self.req('/api/admin/users',{'action':'save','id':'customer-two','version':0,'password':PASSWORD,'role':'client'})
        self.assertEqual(code,200,raw);self.assertEqual(json.loads(raw)['role'],'client')
        self.assertEqual(self.req('/api/admin/users',{'action':'save','id':'customer-short','version':0,'password':'eight123','role':'client'})[0],400)
        record=server.STORE.read_admin('records',id='INTERNAL-1');record['images'][0]['clientVisible']='true'
        self.assertEqual(self.req('/api/admin/records',{'action':'save','id':record['id'],'version':record['version'],'record':{'images':record['images']}})[0],400)
    def test_unknown_roles_denied_and_sessions_persist(self):
        self.login();server.initialize();self.assertEqual(self.req('/api/session')[0],200)
        with server.STORE.connection(True) as conn:conn.execute("UPDATE admin_users SET role='unknown' WHERE username='client-test'")
        self.assertEqual(self.req('/api/session')[0],401);self.assertIsNone(server.STORE.authenticate('client-test',PASSWORD))
        self.assertEqual(self.req('/api/login',{'username':'client-test','password':PASSWORD})[0],401)
        with self.assertRaises(ValueError):server.SESSION_STORE.create(secrets.token_urlsafe(32),{'username':'x','role':'unknown','csrf':'x','expires':time.time()+60,'auth_version':1})
    def test_capacity_does_not_leak_unstructured_data(self):
        for value in [True,float('nan'),'100ml supplier']:
            self.assertEqual(safe_capacity({'capacityMl':value}),'')
        self.assertEqual(safe_capacity({'productDetails':[{'label':'净含量','value':'50克'}]}),'50 g')
        self.assertEqual(safe_capacity({'productDetails':[{'label':'净含量','value':'50g ￥3'}]}),'')
        self.assertEqual(safe_capacity({'specificationRaw':'100ml price3'}),'')

if __name__=='__main__':
    with redirect_stdout(io.StringIO()):unittest.main()
