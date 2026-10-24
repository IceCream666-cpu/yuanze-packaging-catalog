"""All 24 local review models must map to their own complete, self-contained GLB."""
import json,struct,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]/'docs/client-motion-demo'
class CollectionModelTests(unittest.TestCase):
 def test_complete_featured_inventory_and_independent_print_layers(self):
  featured={p['id'] for p in json.loads((ROOT/'src/featured.json').read_text())}
  collection=json.loads((ROOT/'src/structure/collection-products.json').read_text())
  self.assertEqual(set(collection)|{'poster-012','poster-071'},featured)
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
    self.assertTrue((ROOT/'model-source/collection'/id/(id+'.blend')).is_file())
 def test_preview_publication_requires_a_later_user_decision(self):
  m=json.loads((ROOT/'packaging-manifest.json').read_text())
  self.assertFalse(m['publicationApproved']);self.assertTrue(m['scope'].startswith('local-review-'))
