"""Inspect the delivered GLB rather than just its generator or screenshot."""
from collections import Counter
import hashlib, json, math, unittest
import xml.etree.ElementTree as ET
from PIL import Image, ImageChops
from test_micro_cream_model import CLIENT, ExportedModelReader


class BodyOilCollectionTests(ExportedModelReader):
    model_id='poster-073'
    body_name='Body Oil 02 hollow long-shoulder glass bottle'
    source=CLIENT/'model-source/collection/body-oil-collection'

    def group(self,name):
        def belongs(mesh):
            index=self.named[mesh]
            while True:
                if self.nodes[index]['name']==name:return True
                if index not in self.parents:return False
                index=self.parents[index]
        return [n for n in self.mesh_names() if belongs(n)]

    def test_one_bottle_five_layers_with_nested_seal_and_embedded_assets(self):
        expected={'Body','Closure','PaperLabel','LogoPrint','ProductPrint'}
        self.assertEqual({self.nodes[i]['name'] for i in self.gltf['scenes'][0]['nodes']},expected)
        for name in expected:self.assertEqual(len(self.group(name)),2 if name=='Closure' else 1)
        self.assertEqual(self.parents[self.named['InnerSeal']],self.named['Closure'])
        self.assertEqual(len(self.group('InnerSeal')),1)
        self.assertEqual(len(self.mesh_names()),6)
        self.assertTrue(all(name.startswith('Body Oil 02 ') for name in self.mesh_names()))
        lo,hi=self.bounds(self.positions(self.body_name));width=hi[0]-lo[0]
        self.assertAlmostEqual((hi[1]-lo[1])/width,1.84,delta=.002)
        self.assertAlmostEqual((hi[2]-lo[2])/width,1,delta=.002)
        lo,hi=self.bounds([p for n in self.mesh_names() for p in self.positions(n)])
        self.assertAlmostEqual(hi[1]-lo[1],2.9,delta=.001)
        self.assertTrue(all('uri' not in x for x in self.gltf['buffers']+self.gltf['images']))

    def test_single_bottle_preserves_reference_cap_and_closed_height_proportions(self):
        d=self.width()
        lo,hi=self.bounds(self.positions(self.body_name))
        cl,ch=self.bounds(self.positions('Body Oil 02 hollow satin ivory cap'))
        self.assertAlmostEqual((ch[0]-cl[0])/d,.514,delta=.002)
        self.assertAlmostEqual((ch[1]-cl[1])/d,.347,delta=.002)
        self.assertAlmostEqual((ch[1]-lo[1])/d,2.182,delta=.002)
        self.assertAlmostEqual((cl[0]+ch[0])/2,(lo[0]+hi[0])/2,delta=1e-6)
        cap=self.material('Body Oil 02 hollow satin ivory cap')['pbrMetallicRoughness']
        self.assertEqual(cap['metallicFactor'],0)
        self.assertAlmostEqual(cap['roughnessFactor'],.30,delta=.001)

    def test_complete_cap_has_neck_clearance_and_stays_inside_the_compact_frame(self):
        product=json.loads((CLIENT/'src/structure/collection-products.json').read_text())['poster-073']
        explosion=product['review']['explosion'];camera=explosion['camera']
        cap=self.positions('Body Oil 02 hollow satin ivory cap')
        seal=self.positions(self.group('InnerSeal')[0]);body=self.positions(self.body_name)
        cap_bottom=min(p[1] for p in cap);body_top=max(p[1] for p in body)
        self.assertGreater(min(p[1] for p in seal)-body_top,.005)
        self.assertGreater(min(self.ray_intersections('Body Oil 02 hollow satin ivory cap'))-max(p[1] for p in seal),.35)
        cap_inner_radius=min(math.hypot(p[0],p[2]) for p in cap if p[1]<=body_top+.01)
        neck_radius=max(math.hypot(p[0],p[2]) for p in body if p[1]>=body_top-1e-6)
        self.assertGreater(cap_inner_radius-neck_radius,.05,'cap skirt clears the glass neck when closed')
        lift=explosion['offsets']['closure'][1]
        self.assertGreater(cap_bottom+lift-body_top,1.35)
        tilt=math.atan2(1.05,10)
        for step in range(101):
            progress=step/100;lerp=lambda pair:pair[0]+(pair[1]-pair[0])*progress
            height=max(lerp(camera['height']),lerp(camera['width'])/(1200/800))
            top=max((p[1]+lift*progress-lerp(camera['centerY']))*math.cos(tilt)-p[2]*math.sin(tilt) for p in cap+seal)
            self.assertGreater(height/2-top,.1,f'cap headroom at {progress:.2f}')

    def test_glass_is_colourless_and_contains_no_liquid_geometry_or_material(self):
        self.assertEqual(self.group('Liquid'),[])
        self.assertFalse(any(n.get('name')=='Liquid' for n in self.nodes))
        self.assertFalse(any('liquid' in m.get('name','').lower() or 'meniscus' in m.get('name','').lower()
                             for m in self.gltf.get('materials',[])))
        for n in self.group('Body'):
            mat=self.material(n);pbr=mat['pbrMetallicRoughness']
            self.assertEqual(mat['extensions']['KHR_materials_transmission']['transmissionFactor'],1)
            self.assertTrue(all(c>.99 for c in pbr.get('baseColorFactor',[1]*4)[:3]))
            self.assertNotIn('baseColorTexture',pbr)

    def test_open_glass_mouth_thick_base_and_watertight_shell(self):
        d=self.width()
        for name in self.group('Body'):
            points=self.positions(name);lo,hi=self.bounds(points)
            hits=self.ray_intersections(name,a=(lo[0]+hi[0])/2,b=(lo[2]+hi[2])/2)
            self.assertAlmostEqual(min(hits),lo[1],delta=1e-6)
            self.assertAlmostEqual((max(hits)-lo[1])/d,.139,delta=.002)
            ids=[i[0] for i in self.accessor(self.primitive(name)['indices'])]
            welded=[tuple(round(v/d,6) for v in p) for p in points];edges=Counter()
            for i in range(0,len(ids),3):
                a,b,c=[welded[j] for j in ids[i:i+3]]
                self.assertEqual(len({a,b,c}),3)
                edges.update(tuple(sorted(e)) for e in [(a,b),(b,c),(c,a)])
            self.assertEqual(set(edges.values()),{2})

    def test_brand_product_copy_and_blank_carrier_are_three_distinct_layers(self):
        film=ET.parse(self.source/'label.svg').getroot()
        self.assertFalse(any(e.tag.endswith(('}path','}text')) for e in film.iter()))
        brand=ET.parse(self.source/'print.svg').getroot()
        self.assertTrue(any(e.tag.endswith('}path') for e in brand.iter()))
        self.assertFalse(any(e.tag.endswith('}text') for e in brand.iter()))
        for num in ['02']:
            name=ET.parse(self.source/f'name-{num}.svg').getroot()
            self.assertEqual([e.text for e in name.iter() if e.tag.endswith('}text')],['BODY OIL',num])
            for group,mesh,file in [('PaperLabel',f'Body Oil {num} blank curved transparent carrier','label.png'),('LogoPrint',f'Body Oil {num} liaose only','print.png'),('ProductPrint',f'Body Oil {num} BODY OIL and {num}',f'name-{num}.png')]:
                self.assertEqual(self.ancestor(mesh),group)
                self.assertIsNone(ImageChops.difference(self.image(mesh),Image.open(self.source/file).convert('RGBA')).getbbox(alpha_only=False))

    def test_published_config_matches_roots_and_substantial_independent_explosion(self):
        p=json.loads((CLIENT/'src/structure/collection-products.json').read_text())['poster-073'];self.assertEqual({n['node'] for n in p['parts']},{self.nodes[i]['name'] for i in self.gltf['scenes'][0]['nodes']})
        self.assertEqual(len(p['parts']),5)
        self.assertNotIn('liquid',p['review']['appearance'])
        ex=p['review']['explosion'];self.assertEqual(ex['offsets']['closure'],[0,1.4,0])
        for settings in ('offsets','scales','timing','rotations'):
            self.assertNotIn('liner',ex.get(settings,{}))
        self.assertNotIn('closure',ex.get('timing',{}))
        self.assertEqual(ex.get('scales',{}).get('closure',1),1)
        self.assertEqual(ex.get('rotations',{}).get('closure',[0,0,0]),[0,0,0])
        for key in ['print','name']:
            self.assertGreater(ex['offsets'][key][2]-ex['offsets']['label'][2],1)
            self.assertGreater(ex['scales'][key],ex['scales']['label'])
        self.assertNotEqual(ex['offsets']['name'][1],ex['offsets']['print'][1])
        info=json.loads((self.source/'model-info.json').read_text())
        self.assertEqual(info['state'],'local-review');self.assertEqual(info['bottleCount'],1)
        self.assertIs(info['containsFormula'],False)
        self.assertEqual(info['printIncludes'],['liaose','BODY OIL','02'])
        raw=(CLIENT/'packaging-assets/poster-073.glb').read_bytes()
        self.assertEqual(hashlib.sha256(raw).hexdigest(),info['glbSha256'])
        self.assertEqual(hashlib.sha256(raw).hexdigest(),'169b4090346106299dbac1b9479baf3aa59da36f6c27b6655c7c08ada1ee204e')
        self.assertTrue((self.source/'body-oil-collection.blend').is_file())


if __name__=='__main__':unittest.main()
