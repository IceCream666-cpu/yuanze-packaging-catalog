import unittest,json
from collections import Counter
from tests.tail_model_checks import TailChecks
class RoseHairOilModelTests(TailChecks,unittest.TestCase):
 ID='poster-066';RATIO=1.77;GROUPS=['Body','PumpAssembly','Overcap','PaperLabel','LogoPrint'];TEXT=['ROSE HAIR OIL','120 ml']
 def test_original_rose_artwork_is_retained_without_old_black_letters(self):
  self.load()
  from PIL import Image
  im=Image.open(self.source/'floral.png').convert('RGBA');colors=list(im.get_flattened_data());self.assertGreater(sum(a>128 and r>g*1.18 for r,g,b,a in colors),1000);self.assertLess(sum(a>128 and max(r,g,b)<100 for r,g,b,a in colors),15)
 def test_complete_pump_clear_hollow_tube_reaches_near_floor_and_clears_mouth(self):
  self.load();assembly=self.nodes[self.named['PumpAssembly']]
  self.assertEqual({self.nodes[i]['name'] for i in assembly['children']},{'Closure','PumpStem','Actuator'})
  self.assertEqual(assembly.get('translation',[0,0,0]),[0,0,0]);self.assertEqual(assembly.get('scale',[1,1,1]),[1,1,1])
  i,p=next((i,p) for i,p in self.meshes() if self.nodes[i]['name']=='Hollow clear Rose dip tube')
  self.assertEqual(self.ancestor(i),'PumpAssembly');self.assertEqual(len(list(self.meshes())),9)
  points=self.points(i,p);w=self.info['width'];low=min(v[1] for v in points);high=max(v[1] for v in points)
  self.assertAlmostEqual(low/w,.12,delta=.0001);self.assertAlmostEqual(high/w,1.5,delta=.0001)
  radii=[(x*x+z*z)**.5/w for x,y,z in points]
  self.assertAlmostEqual(min(radii),.026,delta=.0001);self.assertAlmostEqual(max(radii),.035,delta=.0001)
  self.assertAlmostEqual(low/w-.095,.025,delta=.0001)
  self.assertGreater(low+self.config['explosion']['offsets']['closure'][1]-1.082*w,.52)
  self.assertLess(max(radii),.041,'The inserted tube must fit the original connector bore.')
  material=self.g['materials'][p['material']];self.assertEqual(material['extensions']['KHR_materials_transmission']['transmissionFactor'],1)
  self.assertLessEqual(material['pbrMetallicRoughness']['roughnessFactor'],.061)
  coords=[tuple(round(v/w,6) for v in point) for point in points];indices=[v[0] for v in self.accessor(p['indices'])];edges=Counter()
  for k in range(0,len(indices),3):
   a,b,c=[coords[j] for j in indices[k:k+3]];self.assertEqual(len({a,b,c}),3);edges.update(tuple(sorted(e)) for e in [(a,b),(b,c),(c,a)])
  self.assertEqual(set(edges.values()),{2},'The open bore has a closed manifold tube wall.')
  product=json.loads((self.source.parents[2]/'src/structure/collection-products.json').read_text())[self.ID]
  self.assertEqual(self.config,{'parts':product['parts'],**product['review']})
 def test_pump_straight_walls_and_recessed_short_nozzle_are_real_geometry(self):
  self.load();by_name={self.nodes[i]['name']:(i,p) for i,p in self.meshes()}
  i,p=by_name['Gold base ring and tapered pump housing'];points=self.points(i,p);normals=self.accessor(p['attributes']['NORMAL']);w=self.info['width']
  for level,radius in [(1.075,.240),(1.132,.190),(1.342,.190)]:
   wall=[normal for point,normal in zip(points,normals) if abs(point[1]/w-level)<1e-5 and abs((point[0]**2+point[2]**2)**.5/w-radius)<1e-5]
   self.assertGreater(len(wall),100);self.assertLess(max(abs(n[1]) for n in wall),.015)
  gold=self.g['materials'][p['material']]['pbrMetallicRoughness'];self.assertAlmostEqual(gold['roughnessFactor'],.30,places=5)
  i,p=by_name['Short white left dispensing lip'];points=[tuple(v/w for v in point) for point in self.points(i,p)]
  front=[v for v in points if abs(v[0]+.180)<1e-5]
  self.assertGreater(len(front),50)
  # At the outlet face no vertex fills the hole; the closed recess ends behind it.
  self.assertGreater(min(((v[1]-1.6335)**2+v[2]**2)**.5 for v in front),.007)
  self.assertTrue(any(abs(x+.145)<1e-5 and abs(y-1.6335)<1e-5 and abs(z)<1e-5 for x,y,z in points))
  self.assertGreaterEqual(min(x for x,y,z in points),-.18001);self.assertLessEqual(max(x for x,y,z in points),-.08499)
