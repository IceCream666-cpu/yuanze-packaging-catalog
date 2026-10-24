"""Read the final Rich Moisture Cream GLB rather than trusting the generator metadata."""
import json,unittest,math
import xml.etree.ElementTree as ET
from test_micro_cream_model import ExportedModelReader,CLIENT

class RichMoistureCreamTests(ExportedModelReader):
 model_id='poster-063';body_name='Hollow frosted circular cream jar'
 def test_five_groups_and_reference_round_proportions(self):
  self.assertEqual({self.nodes[i]['name'] for i in self.gltf['scenes'][0]['nodes']},{'Body','Closure','InnerLid','PaperLabel','LogoPrint'})
  w=self.width();lo,hi=self.bounds([p for n in self.mesh_names() for p in self.positions(n)])
  self.assertAlmostEqual(hi[1]-lo[1],2.9,delta=.005);self.assertAlmostEqual((hi[1]-lo[1])/w,.68,delta=.005)
  b0,b1=self.bounds(self.positions(self.body_name));self.assertAlmostEqual((b1[2]-b0[2])/w,1,delta=.001)
 def test_empty_glass_floor_and_real_closed_cap_roof(self):
  w=self.width();floor=self.ray_intersections(self.body_name);self.assertAlmostEqual(max(floor)/w,.09,delta=.001);self.assertAlmostEqual(min(floor),0,delta=1e-6)
  roof=self.ray_intersections('Champagne lid with closed top and hollow skirt');self.assertAlmostEqual(min(roof)/w,.653,delta=.001)
  liner=max(p[1] for n in self.mesh_names() if self.ancestor(n)=='InnerLid' for p in self.positions(n));self.assertLess(liner,min(roof))
  # The lid skirt begins above the broad shoulder and clears the glass neck.
  glass=self.ray_intersections(self.body_name,0,.451*w,0);lid=self.ray_intersections('Champagne lid with closed top and hollow skirt',0,.451*w,0)
  self.assertGreater(min(r for r in lid if r>0)-max(glass),.005*w)
 def test_frosted_glass_and_metal_label_remain_distinct(self):
  g=self.material(self.body_name);self.assertEqual(g['extensions']['KHR_materials_transmission']['transmissionFactor'],1);self.assertGreater(g['pbrMetallicRoughness']['roughnessFactor'],.25)
  metal=self.material('Champagne lid with closed top and hollow skirt')['pbrMetallicRoughness'];self.assertEqual(metal.get('metallicFactor',1),1);self.assertAlmostEqual(metal['roughnessFactor'],.27,delta=.01)
  foil=self.material('Blank copper foil curved label')['pbrMetallicRoughness'];self.assertGreater(foil['metallicFactor'],.7)
  self.assertNotIn('Texture',json.dumps(g))
 def test_curved_blank_foil_and_complete_black_text_are_independent(self):
  source=CLIENT/'model-source/collection'/self.model_id
  self.assertEqual([e.text for e in ET.parse(source/'print.svg').getroot().iter() if e.tag.endswith('}text')],['RICH MOISTURE CREAM'])
  self.assertFalse(any(e.tag.endswith(('}path','}text')) for e in ET.parse(source/'label.svg').getroot().iter()))
  for name,group in [('Blank copper foil curved label','PaperLabel'),('Complete Rich Moisture cream black lettering','LogoPrint')]:
   self.assertEqual(self.ancestor(name),group);lo,hi=self.bounds(self.positions(name));self.assertGreater((hi[2]-lo[2])/self.width(),.15)
  textured=[n for n in self.mesh_names() if 'baseColorTexture' in self.material(n)['pbrMetallicRoughness']];self.assertEqual(len(textured),2)

if __name__=='__main__':unittest.main()
