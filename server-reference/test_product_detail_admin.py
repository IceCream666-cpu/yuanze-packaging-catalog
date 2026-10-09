import json
import unittest
from copy import deepcopy
from admin_store import AdminError, ConflictError, DEFAULT_PROCESS_STANDARDS
import test_admin_store as fixture

class ProductDetailAdminTests(unittest.TestCase):
    setUp = fixture.AdminStoreTests.setUp
    tearDown = fixture.AdminStoreTests.tearDown
    save = fixture.AdminStoreTests.save

    def batch(self, ids, patch=None, operation='save'):
        items=[{'id':rid,'version':self.store.read_admin('records',rid)['version']} for rid in ids]
        return self.store.mutate('records','bulk',{'items':items,'operation':operation,'patch':patch or {}},'admin')

    def test_reference_fees_start_unknown_not_demo_rates(self):
        value=self.store.read_admin('settings')
        self.assertEqual(len(value['processStandards']),8)
        self.assertTrue(all(row['price'] is None for row in value['processStandards']))
        with self.store.connection(True) as c:
            c.execute("UPDATE admin_config SET content=? WHERE resource='settings'",(json.dumps({'brandName':'preserved'}),))
        self.assertEqual(self.store.read_admin('settings')['brandName'],'preserved')
        self.assertEqual(self.store.read_admin('settings')['processStandards'],DEFAULT_PROCESS_STANDARDS)

    def test_standard_add_price_edit_delete_audited_and_conflict_checked(self):
        value=self.store.read_admin('settings');rows=deepcopy(value['processStandards'])
        rows[0]['price']=0.1234
        rows.append({'id':'new_finish','name':'新增参考工艺','englishName':'New finish','price':None,'unit':'unit','moq':'5000','leadTime':'20天'})
        saved=self.save('settings',{'version':value['version'],'value':{'processStandards':rows}})
        self.assertEqual(saved['processStandards'][0]['price'],0.1234)
        self.assertIsNone(saved['processStandards'][-1]['price'])
        with self.assertRaises(ConflictError):
            self.save('settings',{'version':value['version'],'value':{'processStandards':[]}})
        cleared=self.save('settings',{'version':saved['version'],'value':{'processStandards':[]}})
        self.assertEqual(cleared['processStandards'],[])
        self.assertTrue(any(x['resource']=='settings' for x in self.store.read_admin('audit')))

    def test_invalid_processes_do_not_write(self):
        before=self.store.read_admin('settings');row=deepcopy(DEFAULT_PROCESS_STANDARDS[0])
        for rows in ([row,row],[{**row,'price':-1}],[{**row,'price':True}],[{**row,'price':float('inf')}],[{**row,'id':'a/b'}],[{**row,'unit':'unknown'}],[{**row,'secret':'not allowed'}],[{**row,'name':''}], [row]*51):
            with self.subTest(rows=str(rows)[:80]):
                with self.assertRaises(AdminError):
                    self.save('settings',{'version':before['version'],'value':{'processStandards':rows}})
                self.assertEqual(self.store.read_admin('settings'),before)

    def test_bare_price_can_clear_without_old_quote_returning(self):
        original=self.store.read_admin('records','ORIGINAL-1')
        first=self.save('records',{'id':'ORIGINAL-1','version':original['version'],'record':{'quoteRaw':'裸瓶价格1.8元','bareBottlePrice':'2.50元','stockStatus':'yes'}})
        clear=self.batch(['ORIGINAL-1'],{'bareBottlePrice':''})['items'][0]
        self.assertEqual(clear['bareBottlePrice'],'')
        self.assertEqual(clear['quoteRaw'],'裸瓶价格1.8元')
        self.assertEqual(clear['productCode'],original['productCode'])
        self.assertEqual(clear['source'],original['source'])
        self.assertEqual(clear['images'],original['images'])
        self.assertEqual(clear['stockStatus'],'yes')

    def test_batch_changes_and_clears_core_fields_without_source_damage(self):
        original=self.store.read_admin('records','ORIGINAL-1')
        self.save('records',{'id':'SECOND','version':0,'record':{'name':'第二项','kind':'package'}})
        current=self.save('records',{'id':'ORIGINAL-1','version':original['version'],'record':{'moqRaw':'5000','productDetails':[{'label':'普通起订量','value':'5000'},{'label':'口径','value':'24mm'}]}})
        result=self.batch(['ORIGINAL-1','SECOND'],{'materials':['PET'],'materialRaw':'','moqRaw':'','leadTimeRaw':'20天'})
        self.assertEqual(result['count'],2)
        for item in result['items']:
            self.assertEqual(item['materials'],['PET']);self.assertEqual(item['moqRaw'],'')
            self.assertEqual(item['leadTimeRaw'],'20天')
        first=result['items'][0]
        self.assertEqual(first['productDetails'],[{'label':'口径','value':'24mm','sourceField':'','evidence':''}])
        for key in ('productCode','source','rawCells','images'):
            self.assertEqual(first[key],current[key])
        cleared=self.batch(['ORIGINAL-1'],{'materials':[],'materialRaw':'','uses':[],'specificationRaw':'','capacityMl':None})['items'][0]
        self.assertEqual(cleared['materials'],[]);self.assertEqual(cleared['specificationRaw'],'')

    def test_batch_conflict_rolls_back_every_record_and_audit(self):
        self.save('records',{'id':'SECOND','version':0,'record':{'name':'第二项'}})
        before=self.store.read_admin('records');audit=self.store.read_admin('audit')
        with self.assertRaises(ConflictError):
            self.store.mutate('records','bulk',{'items':[{'id':'ORIGINAL-1','version':1},{'id':'SECOND','version':0}],'operation':'save','patch':{'moqRaw':'1000'}},'admin')
        self.assertEqual(self.store.read_admin('records'),before)
        self.assertEqual(self.store.read_admin('audit'),audit)

    def test_batch_archive_restore_and_no_employee_permission(self):
        self.batch(['ORIGINAL-1'],operation='archive')
        self.assertEqual(self.store.catalog()['records'],[])
        self.batch(['ORIGINAL-1'],operation='unarchive')
        self.assertEqual(len(self.store.catalog()['records']),1)
        with self.assertRaises(AdminError):
            self.store.mutate('records','bulk',{'items':[{'id':'ORIGINAL-1','version':3}],'operation':'archive'},'yuanze')

    def test_single_record_clear_does_not_resurrect_extracted_moq(self):
        first=self.save('records',{'id':'ORIGINAL-1','version':1,'record':{'moqRaw':'5000',
                'productDetails':[{'label':'MOQ','value':'5000'},{'label':'口径','value':'24mm'}]}})
        cleared=self.save('records',{'id':'ORIGINAL-1','version':first['version'],
                'record':{'moqRaw':'','productDetails':first['productDetails']}})
        self.assertEqual(cleared['moqRaw'],'')
        self.assertEqual([row['label'] for row in cleared['productDetails']],['口径'])
        self.assertEqual(cleared['rawCells'],first['rawCells'])

    def test_invalid_batch_fields_ids_and_stock_status_rejected(self):
        before=self.store.read_admin('records','ORIGINAL-1')
        for patch in ({'supplierRaw':'blocked'},{'rawCells':{}},{'stockStatus':'maybe'},{'bareBottlePrice':{'malformed':True}}):
            with self.assertRaises(AdminError):self.batch(['ORIGINAL-1'],patch)
        with self.assertRaises(AdminError):self.batch(['ORIGINAL-1','ORIGINAL-1'],{'moqRaw':'1000'})
        self.assertEqual(self.store.read_admin('records','ORIGINAL-1'),before)
