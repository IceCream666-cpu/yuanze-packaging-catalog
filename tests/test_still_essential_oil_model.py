import unittest
from tests.tail_model_checks import TailChecks
class StillEssentialOilModelTests(TailChecks,unittest.TestCase):
 ID='poster-069';RATIO=3.9;GROUPS=['Body','Closure','NeckSeal','PaperLabel','LogoPrint'];TEXT=['STILL','ESSENTIAL OIL','30 ml']
 def test_heavy_base_cork_texture_and_original_neck_seal(self):
  self.load();self.assertAlmostEqual(self.info['solidBaseHeightToWidth'],.495);self.assertIn('NeckSeal',self.info['components']);mats=[self.g['materials'][p['material']] for i,p in self.meshes() if self.ancestor(i)=='Closure'];self.assertTrue(all('normalTexture' in m for m in mats));self.assertTrue(all(m['pbrMetallicRoughness']['roughnessFactor']>.75 for m in mats))

 def test_cork_texture_is_mid_brown_and_seal_faces_the_front(self):
  self.load()
  import io
  from statistics import median
  from PIL import Image
  for i,p in self.meshes():
   if self.ancestor(i)=='Closure':
    mat=self.g['materials'][p['material']];pbr=mat['pbrMetallicRoughness'];self.assertEqual(pbr.get('baseColorFactor',[1,1,1,1]),[1,1,1,1]);tex=self.g['textures'][pbr['baseColorTexture']['index']];im=self.g['images'][tex['source']];view=self.g['bufferViews'][im['bufferView']];start=view.get('byteOffset',0);bitmap=Image.open(io.BytesIO(self.binary[start:start+view['byteLength']])).convert('RGB');pixels=list(bitmap.get_flattened_data());med=[median(v[j] for v in pixels) for j in range(3)];self.assertGreater(med[0],100);self.assertGreater(med[1],50);self.assertGreater(med[0],med[1]);self.assertGreater(med[1],med[2])
   if self.ancestor(i)=='NeckSeal':
    points=self.points(i,p);bottom=min(v[1] for v in points);front_width=[v[0] for v in points if v[1]<bottom+.008];self.assertGreater(max(front_width)-min(front_width),.23)
