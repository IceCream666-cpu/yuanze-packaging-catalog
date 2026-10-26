"""The 26 published models and five archived review models must map to their own complete, self-contained GLB."""
import json,struct,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]/'docs/client-motion-demo'
class CollectionModelTests(unittest.TestCase):
 def test_pdrn_reference_geometry_clear_glass_and_separate_wordmark(self):
  raw=(ROOT/'packaging-assets/poster-039.glb').read_bytes()
  json_length=struct.unpack_from('<I',raw,12)[0]
  gltf=json.loads(raw[20:20+json_length])
  binary_start=20+json_length
  binary_length,binary_type=struct.unpack_from('<I4s',raw,binary_start)
  self.assertEqual(binary_type,b'BIN\0')
  binary=raw[binary_start+8:binary_start+8+binary_length]
  nodes=gltf['nodes']; named={node['name']:i for i,node in enumerate(nodes)}
  parents={child:i for i,node in enumerate(nodes) for child in node.get('children',[])}
  roots=gltf['scenes'][gltf.get('scene',0)]['nodes']
  self.assertEqual({nodes[i]['name'] for i in roots},{'Body','Closure','InnerLid','LogoPrint'})

  def positions(name):
   index=named[name]; node=nodes[index]
   primitive,=gltf['meshes'][node['mesh']]['primitives']
   accessor=gltf['accessors'][primitive['attributes']['POSITION']]
   self.assertEqual((accessor['type'],accessor['componentType']),('VEC3',5126))
   self.assertNotIn('sparse',accessor)
   view=gltf['bufferViews'][accessor['bufferView']]
   offset=view.get('byteOffset',0)+accessor.get('byteOffset',0)
   stride=view.get('byteStride',12)
   points=[struct.unpack_from('<3f',binary,offset+i*stride) for i in range(accessor['count'])]
   # This export bakes rotations into the vertices; include every remaining parent transform.
   while True:
    node=nodes[index]
    self.assertNotIn('matrix',node)
    self.assertEqual(node.get('rotation',[0,0,0,1]),[0,0,0,1])
    scale=node.get('scale',[1,1,1]); translation=node.get('translation',[0,0,0])
    points=[tuple(p[j]*scale[j]+translation[j] for j in range(3)) for p in points]
    if index not in parents: return points
    index=parents[index]

  def bounds(points):
   return [min(p[j] for p in points) for j in range(3)],[max(p[j] for p in points) for j in range(3)]

  body_low,body_high=bounds(positions('Clear thick-bottom jar'))
  lid_points=positions('Polished silver lid shell'); lid_low,lid_high=bounds(lid_points)
  diameter=lid_high[0]-lid_low[0]; height=lid_high[1]-body_low[1]
  self.assertAlmostEqual(height,2.9,places=5)
  self.assertTrue(.79<height/diameter<.81,'Reference jar must remain broad and low, not cylindrical.')
  self.assertTrue(.23<(lid_high[1]-lid_low[1])/diameter<.25)
  self.assertAlmostEqual(body_high[0]-body_low[0],body_high[2]-body_low[2],places=5)
  self.assertTrue(any(abs(x)<1e-6 and abs(z)<1e-6 and abs(y-lid_high[1])<1e-6 for x,y,z in lid_points),
                  'The silver lid must close at its top centre without a pinhole.')

  def mesh_material(name):
   primitive,=gltf['meshes'][nodes[named[name]]['mesh']]['primitives']
   return gltf['materials'][primitive['material']]

  glass=mesh_material('Clear thick-bottom jar'); glass_pbr=glass['pbrMetallicRoughness']
  self.assertEqual(glass_pbr.get('baseColorFactor',[1,1,1,1]),[1,1,1,1])
  self.assertEqual(glass_pbr.get('metallicFactor',1),0)
  self.assertEqual(glass['extensions']['KHR_materials_transmission']['transmissionFactor'],1)
  self.assertLessEqual(glass_pbr['roughnessFactor'],.04)
  self.assertAlmostEqual(glass['extensions']['KHR_materials_ior']['ior'],1.48,places=5)
  silver=mesh_material('Polished silver lid shell')['pbrMetallicRoughness']
  self.assertGreaterEqual(silver.get('metallicFactor',1),.98)
  self.assertLessEqual(silver['roughnessFactor'],.10)
  silver_rgb=silver.get('baseColorFactor',[1,1,1,1])[:3]
  self.assertLess(max(silver_rgb)-min(silver_rgb),.005)

  # The empty jar has no contents or duplicate text; all front printing moves together.
  self.assertEqual({nodes[i]['name'] for i in nodes[named['Body']]['children']},
                   {'Clear thick-bottom jar','Glass neck bead','Visible glass screw thread'})
  print_names={'Serif copy and underline','Liaose separate print'}
  self.assertEqual({nodes[i]['name'] for i in nodes[named['LogoPrint']]['children']},print_names)
  for name in print_names:
   self.assertEqual(sum(node['name']==name for node in nodes),1)
   self.assertEqual([i for i,node in enumerate(nodes) if named[name] in node.get('children',[])],[named['LogoPrint']])
  self.assertNotIn(named['LogoPrint'],parents)
  copy=mesh_material('Serif copy and underline')
  wordmark=mesh_material('Liaose separate print')
  copy_texture=copy['pbrMetallicRoughness']['baseColorTexture']['index']
  wordmark_texture=wordmark['pbrMetallicRoughness']['baseColorTexture']['index']
  self.assertNotEqual(copy_texture,wordmark_texture)
  self.assertNotEqual(gltf['textures'][copy_texture]['source'],gltf['textures'][wordmark_texture]['source'])
  self.assertIn(copy.get('alphaMode'),{'BLEND','MASK'})
  self.assertIn(wordmark.get('alphaMode'),{'BLEND','MASK'})
  # Reparenting the product name must not shift its original closed-state artwork plate.
  copy_bounds=bounds(positions('Serif copy and underline'))
  wordmark_bounds=bounds(positions('Liaose separate print'))
  for copy_edge,wordmark_edge in zip(copy_bounds,wordmark_bounds):
   for axis in (0,1): self.assertAlmostEqual(copy_edge[axis],wordmark_edge[axis],places=5)
  self.assertAlmostEqual(copy_bounds[0][1],.21*2.9/1.632,places=5)
  self.assertAlmostEqual(copy_bounds[1][1],1.09*2.9/1.632,places=5)
  meta=json.loads((ROOT/'model-source/collection/poster-039/model-info.json').read_text())
  self.assertFalse(meta['containsFormula'])

 def test_complete_featured_inventory_and_independent_print_layers(self):
  featured={p['id'] for p in json.loads((ROOT/'src/featured.json').read_text())}
  collection=json.loads((ROOT/'src/structure/collection-products.json').read_text())
  self.assertEqual(set(collection)|{'poster-012','poster-071'},featured|{'poster-072','poster-073'})
  self.assertFalse({f'poster-{n:03}' for n in range(72,79)} & featured)
  self.assertEqual(len(collection),24)
  self.assertEqual(len(featured),24)
  for id,p in collection.items():
   with self.subTest(id=id):
    self.assertEqual(p['file'],id+'.glb')
    raw=(ROOT/'packaging-assets'/p['file']).read_bytes();self.assertEqual(struct.unpack_from('<4sII',raw),(b'glTF',2,len(raw)))
    n=struct.unpack_from('<I',raw,12)[0];g=json.loads(raw[20:20+n]);nodes=g['nodes'];roots=g['scenes'][g.get('scene',0)]['nodes']
    self.assertEqual({nodes[i]['name'] for i in roots},{part['node'] for part in p['parts']})
    self.assertEqual(sum(n['name']=='LogoPrint' for n in nodes),1)
    self.assertTrue(next(n for n in nodes if n['name']=='LogoPrint')['children'])
    self.assertTrue(all('uri' not in i for i in g.get('images',[])+g.get('buffers',[])))
    self.assertFalse(g.get('animations'));self.assertFalse(g.get('cameras'))
    for view in g['bufferViews']:self.assertLessEqual(view.get('byteOffset',0)+view['byteLength'],g['buffers'][0]['byteLength'])
    source_id={'poster-072':'daily-emulsion','poster-073':'body-oil-collection'}.get(id,id)
    source=ROOT/'model-source/collection'/source_id
    self.assertTrue((source/(source_id+'.blend')).is_file())
 def test_collection_publication_matches_explicit_user_approval(self):
  m=json.loads((ROOT/'packaging-manifest.json').read_text())
  self.assertTrue(m['publicationApproved']);self.assertEqual(m['scope'],'approved-client1.23-collection-packaging')

 def test_five_withdrawn_liaose_models_remain_archived_and_inactive(self):
  collection=json.loads((ROOT/'src/structure/collection-products.json').read_text())
  expected={74:{'jar','closure','stem','head','overcap','liner','print'},75:{'jar','closure','stem','head','print'},76:{'jar','closure','overcap','label','print'},77:{'jar','closure','liner','head','ball','print'},78:{'jar','closure','label','print'}}
  for number,keys in expected.items():
   pid=f'poster-{number:03}';source=ROOT/'model-source/collection'/pid
   with self.subTest(id=pid):
    self.assertNotIn(pid,collection)
    review=json.loads((source/'review-config.json').read_text());cfg={'parts':review['parts'],'review':review,'file':pid+'.glb'};meta=json.loads((source/'model-info.json').read_text())
    self.assertEqual({p['key'] for p in cfg['parts']},keys)
    self.assertFalse(meta['containsFormula']);self.assertTrue(meta['illustrativeDimensions'])
    self.assertLess((ROOT/'packaging-assets'/cfg['file']).stat().st_size,750_000)
    self.assertEqual(json.loads((source/'review-config.json').read_text())['explosion'],cfg['review']['explosion'])
    self.assertEqual(set(cfg['review']['explosion']['offsets']),keys-{'jar'})
  for file,value in [('print-01.svg','01'),('print.svg','02'),('print-03.svg','03')]:
   self.assertIn('>'+value+'</text>',(ROOT/'model-source/collection/poster-073'/file).read_text())
  self.assertIn('studio',json.loads((ROOT/'model-source/collection/poster-075/review-config.json').read_text())['appearance'])
