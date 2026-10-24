"""Actual GLB geometry and artwork checks for independently rebuilt tail products."""
import io,json,math,struct,unittest
from pathlib import Path
from collections import Counter
from PIL import Image
ROOT=Path(__file__).resolve().parents[1];CLIENT=ROOT/'docs/client-motion-demo'
class TailChecks:
 def load(self):
  raw=(CLIENT/'packaging-assets'/f'{self.ID}.glb').read_bytes();self.assertEqual(struct.unpack_from('<4sII',raw),(b'glTF',2,len(raw)));n,kind=struct.unpack_from('<I4s',raw,12);self.assertEqual(kind,b'JSON');g=json.loads(raw[20:20+n]);self.binary=raw[28+n:];self.g=g;self.nodes=g['nodes'];self.parents={c:i for i,o in enumerate(self.nodes) for c in o.get('children',[])};self.named={o['name']:i for i,o in enumerate(self.nodes)};self.source=CLIENT/'model-source/collection'/self.ID;self.info=json.loads((self.source/'model-info.json').read_text());self.config=json.loads((self.source/'review-config.json').read_text())
 def ancestor(self,index):
  while index in self.parents:index=self.parents[index]
  return self.nodes[index]['name']
 def accessor(self,index):
  a=self.g['accessors'][index];v=self.g['bufferViews'][a['bufferView']];fmt='<'+{5121:'B',5123:'H',5125:'I',5126:'f'}[a['componentType']]*{'SCALAR':1,'VEC2':2,'VEC3':3}[a['type']];offset=v.get('byteOffset',0)+a.get('byteOffset',0);stride=v.get('byteStride',struct.calcsize(fmt));return [struct.unpack_from(fmt,self.binary,offset+i*stride) for i in range(a['count'])]
 def points(self,i,p):
  points=self.accessor(p['attributes']['POSITION'])
  while True:
   o=self.nodes[i];self.assertNotIn('matrix',o);self.assertEqual(o.get('rotation',[0,0,0,1]),[0,0,0,1]);s=o.get('scale',[1,1,1]);t=o.get('translation',[0,0,0]);points=[tuple(v[j]*s[j]+t[j] for j in range(3)) for v in points]
   if i not in self.parents:return points
   i=self.parents[i]
 def meshes(self):
  for i,o in enumerate(self.nodes):
   if 'mesh' in o:
    for p in self.g['meshes'][o['mesh']]['primitives']:yield i,p
 def test_reference_proportions_and_exact_independent_groups(self):
  self.load();self.assertEqual({o['name'] for i,o in enumerate(self.nodes) if i not in self.parents},set(self.GROUPS));allpts=[p for i,prim in self.meshes() for p in self.points(i,prim)];body=[p for i,prim in self.meshes() if self.ancestor(i)=='Body' for p in self.points(i,prim)];h=max(p[1] for p in allpts)-min(p[1] for p in allpts);w=max(p[0] for p in body)-min(p[0] for p in body);self.assertAlmostEqual(h,2.9,delta=.015);self.assertAlmostEqual(h/w,self.RATIO,delta=.025);self.assertFalse(self.info['containsFormula']);self.assertTrue(all(not any(word in o['name'].lower() for word in ['liquid','formula','carton','flower vase']) for o in self.nodes))
 def test_glass_is_a_closed_hollow_surface_and_body_has_no_artwork(self):
  self.load()
  for i,p in self.meshes():
   if self.ancestor(i)!='Body':continue
   m=self.g['materials'][p['material']];self.assertNotIn('baseColorTexture',m['pbrMetallicRoughness']);self.assertGreater(m.get('extensions',{}).get('KHR_materials_transmission',{}).get('transmissionFactor',0),.7)
   pts=self.accessor(p['attributes']['POSITION']);ids=[tuple(round(x,6) for x in v) for v in pts];inds=[v[0] for v in self.accessor(p['indices'])];edges=Counter()
   for j in range(0,len(inds),3):
    tri=[ids[inds[j+k]] for k in range(3)]
    if len(set(tri))<3:continue
    for a,b in [(tri[0],tri[1]),(tri[1],tri[2]),(tri[2],tri[0])]:edges[tuple(sorted((a,b)))]+=1
   self.assertTrue(edges);self.assertEqual(set(edges.values()),{2},self.nodes[i]['name'])
 def test_unprinted_carrier_and_complete_original_wording(self):
  self.load();paper=(self.source/'label.svg').read_text();self.assertNotIn('<text',paper);printing=(self.source/'print.svg').read_text()
  for text in self.TEXT:self.assertIn(text,printing)
  self.assertAlmostEqual(self.config['explosion']['offsets']['print'][2]-self.config['explosion']['offsets']['label'][2],1)
  self.assertEqual(self.config['explosion']['scales']['print'],1.95)
  for i,p in self.meshes():
   if self.ancestor(i) not in ('PaperLabel','LogoPrint'):continue
   m=self.g['materials'][p['material']];self.assertIn('baseColorTexture',m['pbrMetallicRoughness']);t=self.g['textures'][m['pbrMetallicRoughness']['baseColorTexture']['index']];im=self.g['images'][t['source']];v=self.g['bufferViews'][im['bufferView']];off=v.get('byteOffset',0)
   with Image.open(io.BytesIO(self.binary[off:off+v['byteLength']])) as bitmap:bitmap.verify()
 def test_large_explosion_and_clear_cap_intervals(self):
  self.load();offs=self.config['explosion']['offsets'];b=self.info['componentBoundsBlenderXYZ'];lookup={p['key']:p['node'] for p in self.config['parts']};self.assertLessEqual(offs['print'][0],-3.1);self.assertGreaterEqual(offs.get('closure',[0,0,0])[1],.75)
  chain=[k for k in ['closure','stem','head','overcap'] if k in lookup]
  for low,high in zip(chain,chain[1:]):self.assertGreater(b[lookup[high]]['min'][2]+offs[high][1]-(b[lookup[low]]['max'][2]+offs[low][1]),.07,(low,high))

 def test_review_controls_have_real_bilingual_details(self):
  self.load()
  for part in self.config['parts']:
   self.assertIn(len(part['short'][0]),(2,3));self.assertNotEqual(part['detail'][0],part['detail'][1]);self.assertTrue(part['detail'][1].isascii());self.assertGreater(len(part['detail'][1]),15)
