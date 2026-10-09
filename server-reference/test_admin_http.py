import base64
import json
import threading
import time
from urllib.parse import urlencode
from unittest.mock import patch
from test_http import HTTP
from test_server import server


class Administration(HTTP):
    def test_bulk_records_real_route_csrf_conflict_and_permissions(self):
        self.login()
        old=self.req('/api/admin/records')[2]['items'][0]
        request={'action':'bulk','operation':'save','items':[{'id':old['id'],'version':old['version']}],
                 'patch':{'bareBottlePrice':'1.8元','moqRaw':'5000'}}
        self.assertEqual(self.req('/api/admin/records',request,csrf=False)[0],403)
        code,_,result=self.req('/api/admin/records',request)
        self.assertEqual(code,200,result)
        self.assertEqual(result['count'],1)
        self.assertEqual(result['items'][0]['bareBottlePrice'],'1.8元')
        self.assertEqual(result['items'][0]['productCode'],old['productCode'])
        self.assertEqual(self.req('/api/admin/records',request)[0],409)
        self.employee_login()
        self.assertEqual(self.req('/api/admin/records',request)[0],403)

    def test_process_prices_real_route_and_customer_asset_boundary(self):
        self.login()
        settings=self.req('/api/admin/settings')[2]
        rows=settings['value']['processStandards'];rows[0]['price']=0.13
        code,_,saved=self.req('/api/admin/settings',{'action':'save','version':settings['version'],
             'value':{'processStandards':rows}})
        self.assertEqual(code,200,saved)
        self.assertEqual(saved['processStandards'][0]['price'],0.13)
        self.assertEqual(self.req('/product-detail.css')[0],200)
        self.assertEqual(self.req('/product-detail-facts.js')[0],200)
        server.STORE.mutate('users','save',{'id':'detail_client','version':0,'password':self.password,'role':'client'},'review_admin')
        _,headers,_=self.req('/api/login',{'username':'detail_client','password':self.password})
        self.cookie=headers['Set-Cookie'].split(';')[0]
        for route in ('/product-detail.css','/product-detail-facts.js'):
            self.assertEqual(self.req(route)[0],200)
        for route in ('/product-pricing.js','/product-detail-view.js','/admin-product-tools.js','/api/admin/settings'):
            self.assertEqual(self.req(route)[0],403)


    def test_catalog_response_gate_rejects_before_loading_and_recovers(self):
        self.login()
        cookie=self.cookie
        paths=('/api/catalog','/api/admin/records','/api/admin/export')
        with server.CATALOG_RESPONSE_GATE:
            with patch.object(server.STORE,'catalog') as catalog, \
                    patch.object(server.STORE,'read_admin') as records, \
                    patch.object(server.STORE,'write_export') as export:
                for path in paths:
                    code,headers,_=self.req(path)
                    self.assertEqual(code,429,path)
                    self.assertEqual(headers.get('Retry-After'),'2')
                self.cookie=''
                for path in paths:self.assertEqual(self.req(path)[0],401,path)
                catalog.assert_not_called()
                records.assert_not_called()
                export.assert_not_called()
        self.cookie=cookie
        for path in paths:self.assertEqual(self.req(path)[0],200,path)

    def test_product_link_survives_login_without_arbitrary_redirect(self):
        code, headers, _ = self.req('/?code=YZ-BC-000001')
        self.assertEqual(code, 303)
        self.assertEqual(headers['Location'], '/login?code=YZ-BC-000001')
        self.assertEqual(self.req('/?code=https%3A%2F%2Fexample.com')[1]['Location'], '/login')
        self.assertEqual(self.req('/?next=https%3A%2F%2Fexample.com')[1]['Location'], '/login')
        self.assertEqual(self.req('/admin?code=YZ-BC-000001')[1]['Location'], '/login')

    def employee_login(self):
        code,headers,_=self.req('/api/login',{'username':'review','password':self.password})
        self.assertEqual(code,200)
        self.cookie=headers['Set-Cookie'].split(';')[0]
        self.csrf=self.req('/api/session')[2]['csrf']

    def test_employee_cannot_access_admin_or_modify_samples(self):
        self.assertEqual(self.req('/api/admin/records')[0],401)
        self.employee_login()
        self.assertEqual(self.req('/api/session')[2]['role'],'employee')
        for path in ['/admin','/admin.html','/admin/tools','/admin.js','/api/admin/records','/api/admin/users','/api/admin/export']:
            self.assertEqual(self.req(path)[0],403,path)
        for path in ['/api/admin/records','/api/admin/users','/api/admin/uploads','/api/samples']:
            self.assertEqual(self.req(path,{'invalid':'x'*120000})[0],403,path)
        self.assertEqual(self.req('/api/catalog')[0],200)
        self.assertEqual(self.req('/api/preferences',{'favorites':[]})[0],200)

    def test_single_record_lookup_is_exact_and_independent_of_full_catalogue(self):
        self.login()
        original=server.STORE.read_admin('records',id='TEST-BOTTLE-1')
        other=server.STORE.mutate('records','save',{'id':'TEST-BOTTLE-2','version':0,
            'record':{'name':original['name'],'capacityMl':50}},'review_admin')
        path='/api/admin/records?'+urlencode({'id':original['id']})
        # Opening one product must not load or wait for a complete catalogue response.
        with server.CATALOG_RESPONSE_GATE:
            with patch.object(server.STORE,'read_admin',wraps=server.STORE.read_admin) as read:
                code,_,body=self.req(path)
                self.assertEqual((code,body),(200,{'item':original}))
                read.assert_called_once_with('records',id=original['id'])
        all_records=self.req('/api/admin/records')[2]
        self.assertEqual(set(all_records),{'items'})
        self.assertEqual({row['id'] for row in all_records['items']},{original['id'],other['id']})
        for query,status in [('id=',400),('id=%20',400),
                             ('id=TEST-BOTTLE-1&id=TEST-BOTTLE-2',400),
                             ('id=missing',404),('id=TEST-BOTTLE',404),
                             ('id=TEST-BOTTLE-1%27%20OR%201%3D1',404)]:
            with self.subTest(query=query):
                code,_,body=self.req('/api/admin/records?'+query)
                self.assertEqual(code,status)
                self.assertNotIn('items',body)
                self.assertNotIn('item',body)

    def test_single_record_edit_preserves_other_record_code_and_version_checks(self):
        self.login()
        other=server.STORE.mutate('records','save',{'id':'TEST-BOTTLE-2','version':0,
            'record':{'name':'独立规格','capacityMl':50}},'review_admin')
        path='/api/admin/records?'+urlencode({'id':'TEST-BOTTLE-1'})
        original=self.req(path)[2]['item']
        update={'action':'save','id':original['id'],'version':original['version'],
                'record':{'name':'编辑选中规格','bodyAreas':['head','body','head']}}
        self.assertEqual(self.req('/api/admin/records',update,csrf=False)[0],403)
        self.assertEqual(self.req(path)[2]['item'],original)
        code,_,saved=self.req('/api/admin/records',update)
        self.assertEqual(code,200,saved)
        self.assertEqual(saved['productCode'],original['productCode'])
        self.assertEqual(saved['id'],original['id'])
        self.assertEqual(saved['version'],original['version']+1)
        self.assertEqual(saved['bodyAreas'],['head','body'])
        self.assertEqual(self.req(path)[2],{'item':saved})
        self.assertEqual(self.req('/api/admin/records',update)[0],409)
        no_version={key:value for key,value in update.items() if key!='version'}
        self.assertEqual(self.req('/api/admin/records',no_version)[0],409)
        self.assertEqual(self.req(path)[2]['item'],saved)
        self.assertEqual(self.req('/api/admin/records?'+urlencode({'id':other['id']}))[2]['item'],other)

    def test_single_record_and_tools_keep_all_role_boundaries(self):
        path='/api/admin/records?id=TEST-BOTTLE-1'
        self.assertEqual(self.req(path)[0],401)
        self.assertEqual(self.req('/admin/tools')[0],303)
        self.employee_login()
        self.assertEqual(self.req(path)[0],403)
        self.assertEqual(self.req('/admin/tools')[0],403)
        server.STORE.mutate('users','save',{'id':'review_client','version':0,
            'password':self.password,'role':'client'},'review_admin')
        code,headers,_=self.req('/api/login',{'username':'review_client','password':self.password})
        self.assertEqual(code,200)
        self.cookie=headers['Set-Cookie'].split(';')[0]
        self.csrf=self.req('/api/session')[2]['csrf']
        for route in ('/admin','/admin.html','/admin/tools','/admin.js','/admin.css',path):
            self.assertEqual(self.req(route)[0],403,route)
        self.assertEqual(self.req('/api/admin/records',{'action':'save','id':'TEST-BOTTLE-1',
            'version':1,'record':{'name':'禁止客户编辑'}})[0],403)

    def test_product_edit_archive_restore_conflict_and_catalog_sync(self):
        self.login()
        old=self.req('/api/admin/records')[2]['items'][0]
        update={'action':'save','id':old['id'],'version':old['version'],'record':{'name':'管理员维护产品','capacityMl':75,'materials':['PETG'],'bottleType':'方瓶'}}
        self.assertEqual(self.req('/api/admin/records',update,csrf=False)[0],403)
        code,_,saved=self.req('/api/admin/records',update)
        self.assertEqual(code,200,saved)
        self.assertEqual(self.req('/api/admin/records',update)[0],409)
        online=next(x for x in self.req('/api/catalog')[2]['records'] if x['id']==old['id'])
        self.assertEqual(online['name'],'管理员维护产品')
        self.assertEqual(online['materials'],['PETG'])
        code,_,archived=self.req('/api/admin/records',{'action':'archive','id':old['id'],'version':saved['version']})
        self.assertEqual(code,200,archived)
        self.assertNotIn(old['id'],[x['id'] for x in self.req('/api/catalog')[2]['records']])
        self.assertEqual(self.req('/api/admin/records',{'action':'unarchive','id':old['id'],'version':archived['version']})[0],200)
        audit=self.req('/api/admin/audit?resource=records&id='+old['id'])[2]['items']
        self.assertGreaterEqual(len(audit),3)

    def test_site_config_and_secret_free_export(self):
        self.login()
        config=self.req('/api/admin/settings')[2]
        self.assertEqual(self.req('/api/admin/settings',{'action':'save','version':config['version'],'value':{'catalogTitle':'源泽展示厅','processReference':'由业务员按工艺和数量复核'}})[0],200)
        self.assertEqual(self.req('/api/catalog')[2]['settings']['catalogTitle'],'源泽展示厅')
        code,_,export=self.req('/api/admin/export')
        self.assertEqual(code,200)
        serialized=json.dumps(export)
        self.assertNotIn(self.password,serialized)
        self.assertNotIn('"hash"',serialized)
        self.assertNotIn('"salt"',serialized)

    def test_user_reset_invalidates_session_and_preserves_last_admin(self):
        self.login()
        admin=next(x for x in self.req('/api/admin/users')[2]['items'] if x['role']=='admin')
        self.assertEqual(self.req('/api/admin/users',{'id':admin['username'],'version':admin['version'],'role':'employee','action':'save'})[0],400)
        reset={'action':'save','id':admin['username'],'version':admin['version'],'password':'new-password-12345'}
        code,_,body=self.req('/api/admin/users',reset)
        self.assertEqual(code,200,body)
        self.assertEqual(self.req('/api/admin/users')[0],401)

    def test_import_preview_then_atomic_conflict_and_single_use(self):
        self.login()
        original=self.req('/api/admin/records')[2]['items'][0]
        content='记录编号,版本,名称,材质,容量ml\n'+original['id']+','+str(original['version'])+',更新产品,PET,50\nIMPORT-NEW,,批量新产品,玻璃,100\n'
        payload={'filename':'产品.csv','content':base64.b64encode(content.encode()).decode()}
        code,_,preview=self.req('/api/admin/import/preview',payload)
        self.assertEqual(code,200,preview)
        self.assertTrue(preview['valid'],preview)
        self.assertEqual(self.req('/api/admin/records',{'action':'save','id':original['id'],'version':original['version'],'record':{'name':'并发修改'}})[0],200)
        self.assertEqual(self.req('/api/admin/import/commit',{'token':preview['token']})[0],409)
        self.assertNotIn('IMPORT-NEW',[x['id'] for x in self.req('/api/catalog')[2]['records']])
        current=next(x for x in self.req('/api/admin/records')[2]['items'] if x['id']==original['id'])
        content='记录编号,版本,名称,材质,容量ml\n'+original['id']+','+str(current['version'])+',更新产品,PET,50\nIMPORT-NEW,,批量新产品,玻璃,100\n'
        payload={'filename':'产品.csv','content':base64.b64encode(content.encode()).decode()}
        code,_,preview=self.req('/api/admin/import/preview',payload)
        self.assertEqual(code,200)
        code,_,body=self.req('/api/admin/import/commit',{'token':preview['token']})
        self.assertEqual(code,200,body)
        self.assertEqual(self.req('/api/admin/import/commit',{'token':preview['token']})[0],400)
        self.assertIn('IMPORT-NEW',[x['id'] for x in self.req('/api/catalog')[2]['records']])

    def test_import_update_without_version_is_rejected(self):
        self.login()
        original=self.req('/api/admin/records')[2]['items'][0]
        content='记录编号,名称\n'+original['id']+',旧表覆盖\n'
        payload={'filename':'旧表.csv','content':base64.b64encode(content.encode()).decode()}
        code,_,preview=self.req('/api/admin/import/preview',payload)
        self.assertEqual(code,200,preview)
        self.assertFalse(preview['valid'])
        self.assertIsNone(preview['token'])
        self.assertIn('版本',preview['errors'][0]['error'])
        saved=next(x for x in self.req('/api/admin/records')[2]['items'] if x['id']==original['id'])
        self.assertEqual(saved['name'],original['name'])
        self.assertEqual(saved['version'],original['version'])

    def test_import_commit_does_not_block_session_checks(self):
        self.login()
        original=self.req('/api/admin/records')[2]['items'][0]
        content='记录编号,版本,名称\n'+original['id']+','+str(original['version'])+',导入期间仍可查询\n'
        payload={'filename':'更新.csv','content':base64.b64encode(content.encode()).decode()}
        _,_,preview=self.req('/api/admin/import/preview',payload)
        self.assertTrue(preview['valid'],preview)
        real=server.STORE.bulk_save
        started=threading.Event();release=threading.Event()
        def slow(rows,actor):
            started.set();release.wait(10);return real(rows,actor)
        with patch.object(server.STORE,'bulk_save',side_effect=slow):
            worker=threading.Thread(target=lambda:self.req('/api/admin/import/commit',{'token':preview['token']}))
            worker.start()
            self.assertTrue(started.wait(10))
            began=time.time();code,_,body=self.req('/api/session');elapsed=time.time()-began
            release.set();worker.join(10)
        self.assertEqual(code,200,body)
        self.assertLess(elapsed,1.0,'session checks must not wait for a running import')
        self.assertEqual(self.req('/api/admin/import/commit',{'token':preview['token']})[0],400)

    def test_login_failures_are_not_reset_by_a_valid_login(self):
        wrong=dict(username='review',password='not-the-password')
        for _ in range(5):self.assertEqual(self.req('/api/login',wrong)[0],401)
        self.employee_login()
        self.assertEqual(self.req('/api/session')[0],200)
        for _ in range(5):self.assertEqual(self.req('/api/login',wrong)[0],401)
        self.assertEqual(self.req('/api/login',wrong)[0],429)
        # A different account can still sign in from a fresh source address.
        server.ATTEMPTS.clear()
        self.login()
        self.assertEqual(self.req('/api/session')[0],200)
