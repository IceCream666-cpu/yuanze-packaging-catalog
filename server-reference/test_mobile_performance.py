"""HTTP regression: list media, revalidation, server pages and permission isolation."""
import hashlib,http.client,io,json,unittest
from unittest.mock import patch
from PIL import Image
import test_client_access as fixtures
from test_server import server

class MobilePerformance(unittest.TestCase):
    setUp=fixtures.ClientAccess.setUp
    tearDown=fixtures.ClientAccess.tearDown
    req=fixtures.ClientAccess.req
    login=fixtures.ClientAccess.login
    catalog=fixtures.ClientAccess.catalog
    def conditional(self,path,etag):
        c=http.client.HTTPConnection(self.host);c.request('GET',path,headers={'Cookie':self.cookie,'If-None-Match':etag})
        r=c.getresponse();result=r.status,dict(r.getheaders()),r.read();c.close();return result
    def test_thumbnail_and_revoke(self):
        source=server.PRIVATE/'media/supplier-secret.png';Image.effect_noise((1600,1200),25).convert('RGB').save(source)
        original=hashlib.sha256(source.read_bytes()).hexdigest();self.login();url=self.catalog()['items'][0]['images'][0]['url']
        status,h,body=self.req(url+'?thumb=1');self.assertEqual(status,200)
        with Image.open(io.BytesIO(body)) as image:
            self.assertLessEqual(max(image.size),512);self.assertEqual(image.getexif(),{});self.assertNotIn('supplier',image.info)
        self.assertEqual(h['Cache-Control'],'private, no-cache');self.assertLess(len(body),len(self.req(url)[2])//2)
        self.assertEqual(self.conditional(url+'?thumb=1',h['ETag'])[::2],(304,b''))
        record=server.STORE.read_admin('records',id='INTERNAL-1');record['images'][0]['clientVisible']=False
        server.STORE.mutate('records','save',{'id':record['id'],'version':record['version'],'record':record},'admin')
        self.assertEqual(self.conditional(url+'?thumb=1',h['ETag'])[0],404);self.assertEqual(self.catalog()['total'],0)
        self.req('/api/logout',{});self.cookie='';self.assertEqual(self.conditional(url+'?thumb=1',h['ETag'])[0],401)
        self.login('employee');status,h,raw=self.req('/media/supplier-secret.png?download=original.png')
        self.assertEqual(status,200);self.assertIn('attachment',h['Content-Disposition']);self.assertEqual(hashlib.sha256(raw).hexdigest(),original)
        status,h,thumb=self.req('/media/supplier-secret.png?thumb=1');self.assertEqual(status,200);self.assertLess(len(thumb),len(raw))
        self.assertEqual(self.conditional('/media/supplier-secret.png?thumb=1',h['ETag'])[0],304)
        self.req('/api/logout',{});self.cookie='';self.assertEqual(self.conditional('/media/supplier-secret.png?thumb=1',h['ETag'])[0],401)
    def test_persistent_get_and_post_rejection_framing(self):
        self.login('employee')
        connection=http.client.HTTPConnection(self.host)
        for path in ['/api/session','/media/supplier-secret.png?thumb=1','/api/session']:
            connection.request('GET',path,headers={'Cookie':self.cookie})
            response=connection.getresponse();self.assertEqual(response.status,200);response.read()
            self.assertFalse(response.will_close)
            if path=='/api/session':self.assertEqual(json.loads(self.req(path)[2])['role'],'employee')
            self.assertIsNotNone(connection.sock)
        connection.close()
        connection=http.client.HTTPConnection(self.host)
        connection.request('POST','/api/preferences',body='unread-private-body',headers={'Cookie':self.cookie,'Origin':'https://'+self.host,'X-CSRF-Token':'invalid'})
        response=connection.getresponse();self.assertEqual(response.status,403);response.read()
        self.assertTrue(response.will_close);self.assertEqual(response.getheader('Connection'),'close');connection.close()
        self.assertEqual(self.req('/api/session')[0],200)
    def test_worker_restart_and_export_formula_protection(self):
        from catalog_pages import internal_csv
        self.login('employee');self.assertEqual(self.req('/api/catalog/page')[0],200)
        server.CATALOG_PAGES.process.kill();server.CATALOG_PAGES.process.wait()
        self.assertEqual(self.req('/api/catalog/page')[0],200)
        result=internal_csv([{'id':'test','name':'=SUM(A1)','quoteRaw':'  +1','sourceNote':'source'}]).decode()
        self.assertIn("'=SUM(A1)",result);self.assertIn("'  +1",result)
        with patch('catalog_pages.shutil.which',return_value=None),patch.dict('os.environ',{'NODE_BIN':''}):
            from catalog_pages import CatalogPages
            self.assertFalse(CatalogPages(server.STORE,server.ROOT).enabled)
    def test_server_pages_and_favorites(self):
        for i in range(45):server.STORE.mutate('records','save',{'version':0,'record':{'kind':'package','name':f'精华玻璃瓶{i}','capacityMl':30,'materials':['玻璃'],'uses':['精华液'],'quoteRaw':'synthetic price','images':[]}},'admin')
        self.login('employee');status,_,body=self.req('/api/catalog/page?kind=package&pageSize=20&page=2')
        self.assertEqual(status,200,body);data=json.loads(body);self.assertEqual((data['page'],data['total'],len(data['pageRecordIds'])),(2,47,20));self.assertLess(len(body),100_000)
        code=data['records'][0]['productCode'];searched=json.loads(self.req('/api/catalog/page?q='+code)[2]);self.assertEqual(searched['total'],1)
        rid=searched['records'][0]['id'];self.req('/api/preferences',{'favorites':[rid]});self.assertEqual(json.loads(self.req('/api/catalog/page?favorites=1')[2])['pageRecordIds'],[rid])
        self.assertEqual(self.req('/api/catalog/page?page=0')[0],400);self.assertEqual(self.req('/api/catalog/records')[0],400)
        status,h,body=self.req('/api/catalog/export?use=%E7%B2%BE%E5%8D%8E%E6%B6%B2');self.assertEqual(status,200);self.assertIn('attachment',h['Content-Disposition']);self.assertEqual(body.decode().count('synthetic price'),45)
        edited=server.STORE.read_admin('records',id=rid);edited['name']='updated red bottle';server.STORE.mutate('records','save',{'id':rid,'version':edited['version'],'record':edited},'admin')
        self.assertEqual(json.loads(self.req('/api/catalog/records?id='+rid)[2])['records'][0]['name'],'updated red bottle')
        self.req('/api/logout',{});self.login()
        for path in ['/api/catalog/page','/api/catalog/records?id='+rid,'/api/catalog/export']:self.assertEqual(self.req(path)[0],403)

if __name__=='__main__':unittest.main()
