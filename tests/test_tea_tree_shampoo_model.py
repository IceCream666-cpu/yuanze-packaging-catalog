"""Inspect the actual empty Tea Tree bottle and refill pouch, including both sets of lettering."""
from collections import Counter
import json,math,unittest
import xml.etree.ElementTree as ET
from PIL import Image,ImageChops
from test_micro_cream_model import ExportedModelReader,CLIENT

class TeaTreeShampooTests(ExportedModelReader):
 model_id='poster-065';body_name='Hollow round shampoo bottle with sloping shoulder'
 def test_five_groups_keep_complete_pump_bottle_and_refill_as_packaging(self):
  self.assertEqual({self.nodes[i]['name'] for i in self.gltf['scenes'][0]['nodes']},{'Body','PumpAssembly','RefillPouch','PaperLabel','LogoPrint'})
  self.assertEqual(len(self.mesh_names()),19)
  w=self.width();lo,hi=self.bounds([p for n in self.mesh_names() for p in self.positions(n)])
  self.assertAlmostEqual(hi[1]-lo[1],2.9,delta=.005)
  baglo,baghi=self.bounds([p for n in self.mesh_names() if self.ancestor(n)=='RefillPouch' for p in self.positions(n)])
  self.assertAlmostEqual((baghi[1]-baglo[1])/w,2.76,delta=.01)
  self.assertAlmostEqual((baghi[0]-baglo[0])/w,1.88,delta=.01)
  bodylo,bodyhi=self.bounds(self.positions(self.body_name));self.assertGreater(baglo[0],bodyhi[0]+.035)
 def test_bottle_floor_cap_bores_and_dip_tube_are_physically_clear(self):
  w=self.width();floor=self.ray_intersections(self.body_name)
  self.assertAlmostEqual(min(floor),0,delta=1e-6);self.assertAlmostEqual(max(floor)/w,.07,delta=.001)
  self.assertEqual(self.ray_intersections('Navy smooth pump screw collar'),[])
  self.assertEqual(self.ray_intersections('Navy raised collar step'),[])
  tube=self.positions('Open hollow dip tube');lo,hi=self.bounds(tube)
  self.assertAlmostEqual(lo[1]/w,.09,delta=.001);self.assertGreater(lo[1]-max(floor),.019*w)
  # A tilted hollow tube retains separate inner and outer annular openings.
  for level,inner,outer in [(.09,.026,.035),(1.34,.026,.035),(1.39,.018,.024),(1.48,.018,.024)]:
   centre=.13*max(0,1-level/1.39)
   radii=[math.hypot(x/w-centre,z/w) for x,y,z in tube if abs(y/w-level)<1e-5]
   self.assertAlmostEqual(min(radii),inner,delta=.001);self.assertAlmostEqual(max(radii),outer,delta=.001)
  mouth=max(p[1] for p in self.positions(self.body_name))
  self.assertGreater(lo[1]+2.45-mouth,.42)
  self.assertLess(max(math.hypot(x/w,z/w) for x,y,z in tube if y/w>=1.39-1e-5),.026,'Tapered tip must fit the existing pump chamber without wall intersection.')
 def test_refill_front_and_rear_are_sealed_thin_skins_with_an_empty_gap(self):
  w=self.width()
  for name in ['Front thin refill pouch skin','Rear thin refill pouch skin']:
   points=self.positions(name);ids=[x[0] for x in self.accessor(self.primitive(name)['indices'])]
   welded=[tuple(round(v/w,6) for v in p) for p in points];edges=Counter()
   for i in range(0,len(ids),3):
    a,b,c=[welded[j] for j in ids[i:i+3]];self.assertEqual(len({a,b,c}),3);edges.update(tuple(sorted(e)) for e in [(a,b),(b,c),(c,a)])
   self.assertEqual(set(edges.values()),{2})
   self.assertNotIn('Texture',json.dumps(self.material(name)))
  front=self.positions('Front thin refill pouch skin');back=self.positions('Rear thin refill pouch skin')
  # Check the actual central films, rather than an opaque solid pouch block.
  centre=[p for p in front if abs(p[0]/w-1.48)<1e-5 and abs(p[1]/w-1.415)<.02]
  rear=[p for p in back if abs(p[0]/w-1.48)<1e-5 and abs(p[1]/w-1.415)<.02]
  self.assertTrue(centre and rear);self.assertGreater(min(p[2] for p in centre)-max(p[2] for p in rear),.20*w)
 def test_clear_bottle_navy_pump_and_warm_tinted_empty_film_materials(self):
  glass=self.material(self.body_name);self.assertEqual(glass['extensions']['KHR_materials_transmission']['transmissionFactor'],1);self.assertNotIn('Texture',json.dumps(glass))
  blue=self.material('Navy smooth pump screw collar')['pbrMetallicRoughness'];r,g,b=blue['baseColorFactor'][:3];self.assertTrue(r<g<b<.08);self.assertEqual(blue.get('metallicFactor',1),0)
  for name in ['Front thin refill pouch skin','Rear thin refill pouch skin']:
   film=self.material(name);self.assertGreater(film['extensions']['KHR_materials_transmission']['transmissionFactor'],.1);self.assertLess(film['extensions']['KHR_materials_transmission']['transmissionFactor'],.3)
   r,g,b=film['pbrMetallicRoughness']['baseColorFactor'][:3];self.assertGreater(r,g);self.assertGreater(g,b);self.assertGreater(r-b,.25)
   self.assertGreater(film['pbrMetallicRoughness']['roughnessFactor'],.18);self.assertLess(film['pbrMetallicRoughness']['roughnessFactor'],.35)
  self.assertLess(self.material('Wide top heat seal')['extensions']['KHR_materials_transmission']['transmissionFactor'],.15)
 def test_actuator_hub_connects_to_pressing_head(self):
  w=self.width();hub=self.ray_intersections('Navy actuator hub');head=self.ray_intersections('Long curved navy dispensing head')
  self.assertEqual(len({round(v/w,5) for v in hub}),2);self.assertEqual(len({round(v/w,5) for v in head}),2)
  self.assertGreater(max(hub)-min(head),.009*w,'Pressing head must connect to its hub, not float above it.')
  self.assertLess(max(hub),max(head))
 def test_complete_pump_and_hollow_clear_tube_survive_export(self):
  source=CLIENT/'model-source/collection'/self.model_id
  config=json.loads((source/'review-config.json').read_text());info=json.loads((source/'model-info.json').read_text())
  self.assertEqual(info['assemblyChildren'],{'PumpAssembly':['Closure','PumpStem','Actuator']})
  for name in ['Navy smooth pump screw collar','Visible navy connecting pump stem','Ivory internal pump chamber','Navy actuator hub','Long curved navy dispensing head','Open hollow dip tube']:
   self.assertEqual(self.ancestor(name),'PumpAssembly')
  self.assertEqual(config['explosion']['offsets']['closure'],[0,2.45,0])
  self.assertNotIn('head',config['explosion']['offsets']);self.assertNotIn('stem',config['explosion']['offsets'])
  self.assertGreater(config['explosion']['offsets']['print'][2],config['explosion']['offsets']['label'][2])
  self.assertFalse(info['containsFormula'])
  name='Open hollow dip tube';material=self.material(name)
  self.assertEqual(material['extensions']['KHR_materials_transmission']['transmissionFactor'],1)
  self.assertAlmostEqual(material['pbrMetallicRoughness']['roughnessFactor'],.06,places=5)
  points=[tuple(round(v/self.width(),6) for v in p) for p in self.positions(name)];indices=[x[0] for x in self.accessor(self.primitive(name)['indices'])];edges=Counter()
  for i in range(0,len(indices),3):
   a,b,c=[points[j] for j in indices[i:i+3]];self.assertEqual(len({a,b,c}),3);edges.update(tuple(sorted(e)) for e in [(a,b),(b,c),(c,a)])
  self.assertEqual(set(edges.values()),{2},'Tube walls form a closed shell around the open bore.')
 def test_reference_letter_sizes_survive_texture_export(self):
  # Ratios use the bottle diameter as the common reference, including the larger pouch label.
  for name,svg_width,bands in [
   ('Complete Tea Tree bottle lettering',680,[(400,500,.34,.38),(500,600,.34,.39),(700,850,.18,.20)]),
   ('Complete Tea Tree refill lettering',910,[(500,630,.40,.44),(630,730,.40,.44),(850,1000,.22,.25)])]:
   alpha=self.image(name).getchannel('A');scale=alpha.width/svg_width
   for lower,upper,minimum,maximum in bands:
    bbox=alpha.crop((0,int(lower*scale),alpha.width,int(upper*scale))).getbbox();self.assertIsNotNone(bbox)
    ratio=(bbox[2]-bbox[0])/scale/1000
    self.assertGreaterEqual(ratio,minimum);self.assertLessEqual(ratio,maximum)
 def test_both_blank_labels_and_all_brand_names_capacities_are_independent(self):
  source=CLIENT/'model-source/collection'/self.model_id
  pairs=[('Blank navy bottle paper label','label','Complete Tea Tree bottle lettering','print',['TEA TREE','SHAMPOO','750 mL']),('Blank navy refill pouch label','refill-label','Complete Tea Tree refill lettering','refill-print',['TEA TREE','SHAMPOO','REFILL'])]
  for paper,paperfile,ink,inkfile,words in pairs:
   self.assertEqual(self.ancestor(paper),'PaperLabel');self.assertEqual(self.ancestor(ink),'LogoPrint')
   svg=ET.parse(source/(inkfile+'.svg')).getroot();self.assertEqual([e.text for e in svg.iter() if e.tag.endswith('}text')],words);self.assertEqual(len([e for e in svg.iter() if e.tag.endswith('}path')]),2)
   self.assertFalse(any(e.tag.endswith(('}path','}text')) for e in ET.parse(source/(paperfile+'.svg')).getroot().iter()))
   for name,file in [(paper,paperfile),(ink,inkfile)]:self.assertIsNone(ImageChops.difference(self.image(name),Image.open(source/(file+'.png')).convert('RGBA')).getbbox(alpha_only=False))
   self.assertGreater(self.bounds(self.positions(ink))[0][2],self.bounds(self.positions(paper))[0][2])
  textured=[n for n in self.mesh_names() if 'baseColorTexture' in self.material(n)['pbrMetallicRoughness']];self.assertEqual(len(textured),4)

if __name__=='__main__':unittest.main()
