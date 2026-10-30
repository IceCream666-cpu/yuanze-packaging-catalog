"""Physical shape, cotton strands and complete label checks for Aromatic Body Lotion."""
import json,math,unittest
from collections import Counter
import xml.etree.ElementTree as ET
from test_micro_cream_model import ExportedModelReader,CLIENT

class AromaticBodyLotionTests(ExportedModelReader):
 model_id='poster-064';body_name='Hollow matte yellow stepped rectangular bottle'
 def test_reference_four_assemblies_and_stepped_bottle_proportions(self):
  self.assertEqual({self.nodes[i]['name'] for i in self.gltf['scenes'][0]['nodes']},{'PumpAssembly','BottleAssembly','PaperLabel','LogoPrint'})
  w=self.width();lo,hi=self.bounds([p for n in self.mesh_names() for p in self.positions(n)])
  self.assertAlmostEqual(hi[1]-lo[1],2.9,delta=.005);self.assertAlmostEqual((hi[1]-lo[1])/w,1.789,delta=.006)
  points=self.positions(self.body_name);foot=[abs(x)/w for x,y,z in points if abs(y/w-.175)<1e-5]
  self.assertAlmostEqual(max(foot),.445,delta=.002)
  self.assertAlmostEqual(self.bounds(points)[1][1]/w,1.325,delta=.003)
 def test_no_formula_and_real_open_neck_floor_and_clearance(self):
  w=self.width();floor=self.ray_intersections(self.body_name)
  self.assertAlmostEqual(min(floor),0,delta=1e-6);self.assertAlmostEqual(max(floor)/w,.052,delta=.001)
  collar='Smooth wide white screw collar';self.assertEqual(self.ray_intersections(collar),[])
  body=self.ray_intersections(self.body_name,0,1.315*w,0);cap=self.ray_intersections(collar,0,1.315*w,0)
  self.assertLess(max(body),min(v for v in cap if v>0))
 def test_opaque_matte_yellow_white_pump_and_cotton_are_not_glass(self):
  body=self.material(self.body_name);p=body['pbrMetallicRoughness'];r,g,b=p['baseColorFactor'][:3]
  self.assertGreater(r,g);self.assertGreater(g,b*2);self.assertGreater(p['roughnessFactor'],.4)
  for name in self.mesh_names():
   if name=='Hollow clear Aromatic dip tube':continue
   self.assertEqual(self.material(name).get('extensions',{}).get('KHR_materials_transmission',{}).get('transmissionFactor',0),0)
  self.assertNotIn('Texture',json.dumps(body))
 def test_three_wraps_have_real_twisted_plies_and_two_fringe_ends(self):
  w=self.width();cords=[n for n in self.mesh_names() if n.startswith('Cotton ')]
  self.assertTrue(all(self.ancestor(n)=='BottleAssembly' for n in cords))
  self.assertEqual(len([n for n in cords if 'neck wrap' in n and 'twisted ply' in n]),9)
  self.assertEqual(len([n for n in cords if 'Cotton fringe' in n]),60)
  for n in cords:
   if 'hanging tail' in n:
    for x,y,z in self.positions(n):
     if .24<y/w<1.02 and abs(x)/w<.50:
      self.assertGreater(z/w,.276,'The hanging cord must remain in front of the body, not penetrate it.')
  nozzle=self.positions('Flattened long left dispensing head with recessed opening');low,high=self.bounds(nozzle)
  self.assertGreater((high[0]-low[0])/self.width(),.64)
 def test_actuator_hub_connects_to_pressing_head(self):
  w=self.width();hub=self.ray_intersections('White actuator cylindrical hub');head=self.ray_intersections('Flattened long left dispensing head with recessed opening')
  self.assertEqual(len({round(v/w,5) for v in hub}),2);self.assertEqual(len({round(v/w,5) for v in head}),2)
  self.assertGreater(max(hub)-min(head),.009*w,'Pressing head must connect to its hub, not float above it.')
  self.assertLess(max(hub),max(head))
 def test_cotton_strand_normals_do_not_reverse_at_tight_bends(self):
  for name in self.mesh_names():
   primitive=self.primitive(name);points=self.accessor(primitive['attributes']['POSITION']);normals=self.accessor(primitive['attributes']['NORMAL']);indices=[v[0] for v in self.accessor(primitive['indices'])]
   for i in range(0,len(indices),3):
    a,b,c=indices[i:i+3];u=[points[b][j]-points[a][j] for j in range(3)];v=[points[c][j]-points[a][j] for j in range(3)]
    face=[u[1]*v[2]-u[2]*v[1],u[2]*v[0]-u[0]*v[2],u[0]*v[1]-u[1]*v[0]];length=math.sqrt(sum(x*x for x in face))
    self.assertGreater(length,1e-12,name+' has a degenerate triangle')
    average=[sum(normals[k][j] for k in [a,b,c]) for j in range(3)]
    self.assertGreaterEqual(sum(face[j]*average[j] for j in range(3)),0,name+' has a reversed interpolated normal')
 def test_paper_is_blank_and_brand_rules_name_capacity_all_move_together(self):
  src=CLIENT/'model-source/collection'/self.model_id
  svg=ET.parse(src/'print.svg').getroot();self.assertEqual([e.text for e in svg.iter() if e.tag.endswith('}text')],['AROMATIC','BODY LOTION','300 ml'])
  self.assertEqual(len([e for e in svg.iter() if e.tag.endswith('}path')]),3)
  self.assertFalse(any(e.tag.endswith(('}path','}text')) for e in ET.parse(src/'label.svg').getroot().iter()))
  self.assertEqual(self.ancestor('Complete Aromatic Body Lotion lettering'),'LogoPrint');self.assertEqual(self.ancestor('Blank warm cream paper label'),'PaperLabel')
  self.assertEqual(len([n for n in self.mesh_names() if 'baseColorTexture' in self.material(n)['pbrMetallicRoughness']]),2)

 def test_complete_pump_and_tied_cord_with_open_clear_tube(self):
  src=CLIENT/'model-source/collection'/self.model_id
  config=json.loads((src/'review-config.json').read_text());info=json.loads((src/'model-info.json').read_text())
  self.assertFalse(info['containsFormula']);self.assertTrue(info['illustrativeDimensions'])
  self.assertEqual(len(self.mesh_names()),139)
  for parent,children in [('PumpAssembly',{'Closure','PumpStem','Actuator'}),('BottleAssembly',{'Body','Cord'})]:
   node=self.nodes[self.named[parent]]
   self.assertEqual({self.nodes[i]['name'] for i in node['children']},children)
   self.assertEqual(node.get('translation',[0,0,0]),[0,0,0]);self.assertEqual(node.get('scale',[1,1,1]),[1,1,1])
  tube='Hollow clear Aromatic dip tube';w=self.width();points=self.positions(tube);lo,hi=self.bounds(points)
  self.assertEqual(self.ancestor(tube),'PumpAssembly');self.assertEqual(self.ray_intersections(tube),[])
  self.assertAlmostEqual(lo[1]/w,.09,delta=.001);self.assertAlmostEqual(hi[1]/w,1.635,delta=.001)
  self.assertAlmostEqual((hi[0]-lo[0])/w,.07,delta=.001)
  side=self.ray_intersections(tube,0,.5*w,0);self.assertAlmostEqual(min(v for v in side if v>0)/w,.026,delta=.001)
  floor=max(self.ray_intersections(self.body_name));self.assertAlmostEqual((lo[1]-floor)/w,.038,delta=.001)
  mouth=self.bounds(self.positions(self.body_name))[1][1];self.assertGreater(lo[1]+config['explosion']['offsets']['closure'][1]-mouth,.44)
  mat=self.material(tube);self.assertEqual(mat['extensions']['KHR_materials_transmission']['transmissionFactor'],1);self.assertLessEqual(mat['pbrMetallicRoughness']['roughnessFactor'],.061)
  indices=[i[0] for i in self.accessor(self.primitive(tube)['indices'])];welded=[tuple(round(v/w,6) for v in point) for point in points];edges=Counter()
  for i in range(0,len(indices),3):
   a,b,c=[welded[j] for j in indices[i:i+3]];self.assertEqual(len({a,b,c}),3);edges.update(tuple(sorted(e)) for e in [(a,b),(b,c),(c,a)])
  self.assertEqual(set(edges.values()),{2},'Open tube bore has a closed manifold wall')
  product=json.loads((CLIENT/'src/structure/collection-products.json').read_text())[self.model_id]
  self.assertEqual(config,{'parts':product['parts'],**product['review']})
  manifest=json.loads((CLIENT/'packaging-manifest.json').read_text());entry=next(e for e in manifest['additionalProducts'] if e['posterId']==self.model_id)
  self.assertEqual(entry['components'],[p['node'] for p in config['parts']]);self.assertNotIn('cord',config['explosion']['offsets'])
  self.assertGreater(config['explosion']['offsets']['print'][2],config['explosion']['offsets']['label'][2])

if __name__=='__main__':unittest.main()
