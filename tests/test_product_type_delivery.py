import hashlib
import importlib.util
from pathlib import Path
import tempfile
import unittest
from PIL import Image

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('type_delivery',ROOT/'scripts/build_product_type_views.py')
module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)

class TypeDelivery(unittest.TestCase):
    def test_native_bytes_and_lossless_browser_conversion(self):
        with tempfile.TemporaryDirectory() as tmp:
            base=Path(tmp);native=base/'native.png';display=base/'display.webp';preview=base/'preview.webp'
            Image.effect_noise((2400,1200),15).convert('RGB').save(native)
            raw=native.read_bytes();sha=hashlib.sha256(raw).hexdigest()
            self.assertEqual(module.deliver_photo(native,sha,display,preview),(2400,1200))
            self.assertEqual(native.read_bytes(),raw)
            with Image.open(native) as original,Image.open(display) as browser,Image.open(preview) as small:
                self.assertEqual(original.convert('RGB').tobytes(),browser.convert('RGB').tobytes())
                self.assertEqual(small.size,(1536,768));self.assertLess(preview.stat().st_size,native.stat().st_size)
                self.assertEqual(small.getexif(),{});self.assertEqual(browser.getexif(),{})
    def test_changed_source_does_not_publish_new_assets(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp);native=p/'original.png';Image.new('RGB',(40,30),'red').save(native)
            with self.assertRaises(ValueError):module.deliver_photo(native,'0'*64,p/'display.webp',p/'preview.webp')
            self.assertFalse((p/'display.webp').exists());self.assertFalse((p/'preview.webp').exists())
    def test_source_bytes_not_reencoded_when_web_supported(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp);native=p/'original.jpg';Image.new('RGB',(300,200),'blue').save(native)
            raw=native.read_bytes();module.deliver_photo(native,module.digest(raw),native,p/'preview.webp')
            self.assertEqual(native.read_bytes(),raw)
    def test_identical_photos_deliver_all_source_specific_filenames(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp);Image.new('RGB',(80,60),'blue').save(p/'source-a.jpg')
            raw=(p/'source-a.jpg').read_bytes();(p/'source-b.jpg').write_bytes(raw)
            groups=[]
            for source in ('a','b'):
                groups.append({'review':{'catalogue':f'{source}.pdf','page':1,
                    'nativeSourceFile':f'source-{source}.jpg','sourceImageSha256':module.digest(raw)},
                    'primaryImage':{'path':f'media/type-views/source-{source}.jpg',
                    'previewPath':f'media/type-views/source-{source}-preview.webp',
                    'displayCrop':{'sourceWidth':80,'sourceHeight':60}}})
            self.assertEqual(module.rebuild(p,p,groups+groups),2)
            for source in ('a','b'):
                self.assertEqual((p/f'source-{source}.jpg').read_bytes(),raw)
                self.assertTrue((p/f'source-{source}-preview.webp').is_file())

if __name__=='__main__':unittest.main()
