import importlib.util
import unittest
import sys
import io
import tempfile
from unittest.mock import Mock,patch
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('brochure',ROOT/'scripts/prepare_hongsheng_catalog.py')
brochure=importlib.util.module_from_spec(spec);spec.loader.exec_module(brochure)
sys.path.insert(0,str(ROOT/'scripts'))
from publish_brochure_manifest import check_existing,upload_image,upload_bytes,create_record

def page(n,*lines): return {'page':n,'lines':[{'text':v} for v in lines]}

class BrochureTests(unittest.TestCase):
    def test_reversed_layout_82(self):
        rows=brochure.extract(page(82,'HS0216','HS0215','材质/Material:PE/PP','容量/Capacity:100ml/150ml','瓶身规格:16牙15克/24牙19克'))
        self.assertEqual([(r['model'],r['material'],r['specification']) for r in rows],[('HS0215','PE','100mL'),('HS0216','PP','150mL')])
    def test_grams_not_label_volume(self):
        row=brochure.extract(page(9,'350ml','材质:PET','容量:200g','瓶身规格:88牙34克'))[0]
        self.assertEqual(row['specification'],'200g');self.assertIsNone(row['capacityMl']);self.assertEqual(row['category'],'罐')
    def test_continuation_and_shared_material(self):
        rows=brochure.extract(page(4,'HS0111','HS0112','材质:HDPE','容量:450ml','300ml','瓶身规格:28牙','02'))
        self.assertEqual([r['specification'] for r in rows],['450mL','300mL'])
    def test_adjacent_model_page(self):
        rows=brochure.extract(page(120,'材质:HDPE','容量:750m//750ml/750ml','瓶身规格:32牙76克/32牙75克/32牙75克'),page(121,'HS0266','HS0267','HS0268'))
        self.assertEqual(len(rows),3);self.assertEqual(rows[0]['pages'],[120,121]);self.assertEqual(rows[0]['capacityMl'],750)
    def test_different_container_types_same_page(self):
        rows=brochure.extract(page(76,'HS0207','HS0212','材质:PET','容量:180ml/240ml','瓶身规格:24牙29克/88牙43克'))
        self.assertEqual([r['category'] for r in rows],['瓶','罐'])
    def test_missing_weight_not_guessed(self):
        rows=brochure.extract(page(122,'HS0261','HS0262','HS0263','HS0264','材质:PET','容量:500ml/450ml/300ml/200ml','瓶身规格:42牙65克/65克/44克'))
        self.assertTrue(all(not r['neckWeight'] for r in rows))
    def test_ambiguous_capacity_fails(self):
        with self.assertRaises(ValueError): brochure.extract(page(5,'HS0115','材质:PET','容量:300ml/500ml','瓶身规格:24牙'))
    def test_x_models(self):
        rows=brochure.extract(page(177,'材质:PET','容量:700ml/400ml','瓶身规格:32牙65克/28牙48克'))
        self.assertEqual([r['model'] for r in rows],['HSX001','HSX002'])
    def test_resume_refuses_other_source_or_changed_product(self):
        entry={'record':{'model':'HS0113','specificationRaw':'500mL','materials':['HDPE'],'category':'瓶'}}
        current={**entry['record'],'sourceNote':'sha256:abc','images':[{'clientVisible':False}]}
        check_existing(current,entry,'abc')
        with self.assertRaises(ValueError): check_existing(current,entry,'different')
        with self.assertRaises(ValueError): check_existing({**current,'materials':['PET']},entry,'abc')
    def test_resume_does_not_approve_customer_images(self):
        entry={'record':{'model':'HS0113','specificationRaw':'500mL','materials':['HDPE'],'category':'瓶'}}
        for images in ([],[{'clientVisible':True}]):
            with self.assertRaises(ValueError): check_existing({**entry['record'],'sourceNote':'abc','images':images},entry,'abc')
    def test_upload_retries_only_explicit_busy(self):
        client=Mock();client.request.side_effect=[(429,{'Retry-After':'2'},b''),(201,{},b'{"image":{"path":"uploads/test.jpg"}}')]
        with patch('publish_brochure_manifest.time.sleep') as sleep:
            self.assertEqual(upload_image(client,'data'),{'path':'uploads/test.jpg'})
            sleep.assert_called_once_with(2)
        client=Mock();client.request.return_value=(500,{},b'')
        with self.assertRaises(RuntimeError):upload_image(client,'data')
        self.assertEqual(client.request.call_count,1)
    def test_transport_resize_preserves_original(self):
        from PIL import Image
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'source.jpg';Image.new('RGB',(2000,1000),'white').save(path)
            original=path.read_bytes();encoded=upload_bytes(path)
            self.assertEqual(path.read_bytes(),original)
            with Image.open(io.BytesIO(encoded)) as image:self.assertEqual(image.size,(1600,800))
    def test_create_is_version_zero_and_private_reference(self):
        parent=Mock(origin='https://example.com',jar=[],csrf='test')
        worker=Mock();worker.request.return_value=(200,{},b'{"id":"HS2608-HS0113-500mL","version":1}')
        entry={'id':'HS2608-HS0113-500mL','pages':[3],'record':{'name':'fixture','model':'HS0113'}}
        with patch('publish_brochure_manifest.gate.Client',return_value=worker):
            create_record(parent,entry,{'3':{'path':'uploads/example.jpg'}})
        payload=worker.request.call_args.args[1]
        self.assertEqual(payload['version'],0)
        self.assertFalse(payload['record']['images'][0]['clientVisible'])
        self.assertEqual(payload['record']['images'][0]['imageScope'],'source_page')
        self.assertNotIn('images',entry['record'])

if __name__=='__main__':unittest.main()
