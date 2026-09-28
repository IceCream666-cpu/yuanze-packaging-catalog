import hashlib
import json
from pathlib import Path
import tempfile
import unittest

from admin_store import AdminStore, ConflictError
from import_brand_refresh import apply_batch


class BrandRefreshTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        root = Path(self.tmp.name)
        self.private = root/'private'
        (self.private/'media').mkdir(parents=True)
        (self.private/'media/product.jpg').write_bytes(b'test-image')
        self.store = AdminStore(root/'state', self.private, {}, {'records': [
            {'id':'no-image', 'name':'无图', 'kind':'package', 'images':[], 'quoteRaw':'原始价格条件'},
            {'id':'product', 'name':'瓶子', 'kind':'package', 'materials':[], 'capacityMl':None,
             'specificationRaw':'100ml\n实灌105ml', 'images':[{'path':'media/product.jpg', 'role':'product',
              'imageScope':'single_product'}]},
        ]})

    def patch(self, rid, changes=None, archived=None):
        with self.store.connection() as c:
            row = c.execute('SELECT * FROM admin_records WHERE id=?',(rid,)).fetchone()
        p = {'id':rid, 'expectedVersion':row['version'], 'expectedArchived':bool(row['archived']),
             'expectedContentSha256':hashlib.sha256(row['content'].encode()).hexdigest(), 'set':changes or {}}
        if archived is not None:p['archived']=archived
        return p

    def batch(self, *patches):
        return {'batch':'brand-test','updates':list(patches),'newRecords':[]}

    def test_archive_and_enrich_keep_originals_codes_and_raw_evidence(self):
        with self.store.connection() as c:
            original = dict(c.execute('SELECT id,original FROM admin_records'))
            codes = dict(c.execute('SELECT record_id,product_code FROM admin_product_codes'))
        batch = self.batch(self.patch('no-image',archived=True), self.patch('product',{'capacityMl':100,
             'productDetails':[{'label':'实灌容量','value':'105mL','sourceField':'specificationRaw','evidence':'实灌105ml'}]}))
        result=apply_batch(self.store,batch)
        self.assertEqual((result['archived'],result['enriched']),(1,1))
        self.assertEqual([r['id'] for r in self.store.catalog()['records']],['product'])
        with self.store.connection() as c:
            self.assertEqual(dict(c.execute('SELECT id,original FROM admin_records')),original)
            self.assertEqual(dict(c.execute('SELECT record_id,product_code FROM admin_product_codes')),codes)
            content=json.loads(c.execute("SELECT content FROM admin_records WHERE id='product'").fetchone()[0])
        self.assertEqual(content['specificationRaw'],'100ml\n实灌105ml')
        self.assertEqual(apply_batch(self.store,batch)['status'],'already_imported')

    def test_stale_preflight_prevents_partial_archive(self):
        bad=self.patch('product',{'capacityMl':100});bad['expectedVersion']+=1
        with self.assertRaises(ConflictError):apply_batch(self.store,self.batch(self.patch('no-image',archived=True),bad))
        self.assertEqual(len(self.store.catalog()['records']),2)

    def test_image_product_cannot_be_archived_and_transaction_rolls_back(self):
        with self.assertRaises(ValueError):
            apply_batch(self.store,self.batch(self.patch('no-image',archived=True),self.patch('product',archived=True)))
        self.assertEqual(len(self.store.catalog()['records']),2)

    def test_pending_category_and_uncertain_source_page_are_preserved(self):
        with self.store.connection(write=True) as c:
            row=c.execute("SELECT content FROM admin_records WHERE id='product'").fetchone()
            record=json.loads(row[0]);record['category']='待细分'
            record['images']=[{'path':'media/product.jpg','role':'reference',
                               'imageScope':'source_page','uncertain':True}]
            c.execute("UPDATE admin_records SET content=? WHERE id='product'",(json.dumps(record),))
        with self.assertRaises(ValueError):
            apply_batch(self.store,self.batch(self.patch('no-image',archived=True),self.patch('product',archived=True)))
        self.assertEqual(len(self.store.catalog()['records']),2)

    def test_filled_value_cannot_be_replaced(self):
        with self.store.connection(write=True) as c:
            row=c.execute("SELECT content FROM admin_records WHERE id='product'").fetchone()
            record=json.loads(row[0]);record['capacityMl']=120
            c.execute("UPDATE admin_records SET content=? WHERE id='product'",(json.dumps(record),))
        with self.assertRaises(ValueError):apply_batch(self.store,self.batch(self.patch('product',{'capacityMl':100})))


if __name__=='__main__':unittest.main()
