import base64
import json
import threading
import time
from unittest.mock import patch
from test_http import HTTP
from test_server import server


class Administration(HTTP):
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
        for path in ['/admin','/admin.html','/admin.js','/api/admin/records','/api/admin/users','/api/admin/export']:
            self.assertEqual(self.req(path)[0],403,path)
        for path in ['/api/admin/records','/api/admin/users','/api/admin/uploads','/api/samples']:
            self.assertEqual(self.req(path,{'invalid':'x'*120000})[0],403,path)
        self.assertEqual(self.req('/api/catalog')[0],200)
        self.assertEqual(self.req('/api/preferences',{'favorites':[]})[0],200)

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
