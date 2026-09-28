import copy
import hashlib
import io
import json
from pathlib import Path
import tempfile
import unittest

from admin_store import AdminStore, ConflictError, dumps
from import_product_images import apply_batch


class ProductImageReview(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.root=Path(self.temp.name)
        self.private=self.root/'private';self.state=self.root/'state';(self.private/'media').mkdir(parents=True)
        self.original={'id':'old','kind':'package','name':'现有包材','quoteRaw':'7.80/套，含盖','unitPrice':7.8,
            'images':[{'path':'media/page.jpg','role':'product','mapping':'pdf-page-preview'}],
            'source':{'page':7},'rawCells':{'original':'never change'}}
        self.crop={'path':'media/crop.jpg','role':'product','mapping':'product-crop-20260928','imageScope':'single_product','sourceImage':'media/page.jpg','sourceBbox':[0,0,.3,.3]}
        manifest={'images':[self.crop],'scopes':{'media/page.jpg':'source_page','media/crop.jpg':'single_product'}}
        (self.private/'product-image-manifest.json').write_text(dumps(manifest))
        for name in ('page.jpg','crop.jpg'):(self.private/'media'/name).write_bytes(b'fixture')
        self.store=AdminStore(self.state,self.private,{}, {'records':[self.original]})
        with self.store.connection() as c:
            row=c.execute('SELECT content,version FROM admin_records WHERE id="old"').fetchone()
            self.digest=hashlib.sha256(row['content'].encode()).hexdigest()
        self.batch={'batch':'test-image-review','updates':[{'id':'old','expectedVersion':1,'expectedContentSha256':self.digest,
            'images':[self.crop,{**self.original['images'][0],'role':'reference','imageScope':'source_page'}]}],
            'newRecords':[{'id':'new-single','name':'单独盖子','kind':'package','source':{'page':7},'rawCells':{'caption':'source'},'images':[self.crop]}]}

    def tearDown(self):self.temp.cleanup()

    def test_migration_preserves_commercial_data_and_old_codes_is_idempotent(self):
        before=self.store.read_admin('records','old');result=apply_batch(self.store,self.batch)
        self.assertEqual(result['created'],1)
        after=self.store.read_admin('records','old')
        self.assertEqual(after['productCode'],before['productCode'])
        self.assertEqual(after['version'],2)
        for k in ('quoteRaw','unitPrice','source','rawCells'):self.assertEqual(after[k],before[k])
        fresh=self.store.read_admin('records','new-single')
        self.assertNotEqual(fresh['productCode'],after['productCode'])
        self.assertEqual(fresh['images'][0]['imageScope'],'single_product')
        self.assertEqual(self.store.export()['originalRecords']['old'],self.original)
        self.assertEqual(apply_batch(self.store,self.batch)['status'],'already_imported')
        self.assertEqual(self.store.read_admin('records','old')['version'],2)

    def test_conflicting_version_or_content_rolls_back_entire_batch(self):
        for key,value in [('expectedVersion',2),('expectedContentSha256','modified')]:
            broken=copy.deepcopy(self.batch);broken['updates'][0][key]=value
            with self.assertRaises(ConflictError):apply_batch(self.store,broken)
            self.assertEqual(len(self.store.catalog()['records']),1)
            self.assertEqual(self.store.read_admin('records','old')['version'],1)

    def test_invalid_new_image_rolls_back_prior_updates_and_number_sequence(self):
        broken=copy.deepcopy(self.batch);broken['newRecords'][0]['images']=[{'path':'media/not-trusted.jpg'}]
        with self.assertRaises(ValueError):apply_batch(self.store,broken)
        self.assertEqual(self.store.read_admin('records','old')['version'],1)
        apply_batch(self.store,self.batch)
        self.assertEqual(self.store.read_admin('records','new-single')['productCode'],'YZ-BC-000002')

    def test_browser_cannot_promote_full_page_or_tamper_with_crop_provenance(self):
        with self.store.connection() as c:
            images=self.store._images(c,[{'path':'media/page.jpg','role':'product','imageScope':'single_product'},
                {**self.crop,'imageScope':'unresolved','sourceImage':'fake','sourceBbox':[0,0,1,1]}])
        self.assertEqual(images[0]['imageScope'],'source_page')
        self.assertEqual(images[1]['imageScope'],'single_product')
        self.assertEqual(images[1]['sourceImage'],'media/page.jpg')
        self.assertEqual(images[1]['sourceBbox'],[0,0,.3,.3])

    def test_streamed_export_keeps_all_history_originals_and_codes(self):
        apply_batch(self.store,self.batch)
        with self.store.connection(write=True) as c:
            for n in range(1105):
                self.store._audit(c,'records','old','test','system',None,{'n':n})
        expected=self.store.export()
        class BoundedOutput(io.BytesIO):
            def write(self,chunk):
                if len(chunk)>65536:raise AssertionError('Whole export buffered in memory')
                return super().write(chunk)
        stream=BoundedOutput();self.store.write_export(stream);actual=json.loads(stream.getvalue())
        actual.pop('exportedAt');expected.pop('exportedAt')
        self.assertEqual(actual,expected)
        self.assertGreater(len(actual['audit']),1000)
        self.assertEqual(actual['records'][0]['productCode'],'YZ-BC-000002')
