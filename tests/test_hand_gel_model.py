"""Inspect the approved Hand Gel GLB and its exact formal publication association."""
import json
from tests.test_micro_cream_model import CLIENT, ExportedModelReader


class HandGelModelTests(ExportedModelReader):
    model_id = 'poster-081-v1'
    body_name = 'Clear hollow cylinder | thick base and open neck'
    tube_name = 'Long clear hollow dip tube | angled pickup'
    source = CLIENT / 'model-source/collection/poster-081'

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.product = json.loads((cls.source / 'review-product.json').read_text())
        cls.info = json.loads((cls.source / 'model-info.json').read_text())

    def test_published_model_matches_the_approved_review(self):
        collection = json.loads((CLIENT / 'src/structure/collection-products.json').read_text())
        self.assertEqual(collection['poster-081'], self.product)
        featured = json.loads((CLIENT / 'src/featured.json').read_text())
        self.assertEqual([item['id'] for item in featured].count('poster-081'), 1)
        manifest = json.loads((CLIENT.parents[1] / 'server-reference/public/showroom/bundle-manifest.json').read_text())
        self.assertIn('assets/packaging/poster-081-v1.glb', manifest['files'])
        self.assertIn('assets/featured/poster-081.png', manifest['files'])
        for name in manifest['files']:
            self.assertNotIn('hand-gel.html', name)
            if name.startswith(('assets/packaging/', 'assets/featured/')):
                self.assertNotIn('poster-082', name)

    def test_exactly_five_groups_preserve_the_reference_proportions(self):
        roots = {self.nodes[i]['name'] for i in self.gltf['scenes'][0]['nodes']}
        self.assertEqual(roots, {'Body', 'Pump', 'Label', 'LogoInk', 'NameInk'})
        self.assertEqual(roots, {part['node'] for part in self.product['parts']})
        low, high = self.bounds([p for name in self.mesh_names() for p in self.positions(name)])
        self.assertAlmostEqual(high[1] - low[1], 2.913, delta=.005)
        self.assertAlmostEqual(self.width(), 1.564, delta=.005)
        self.assertTrue((self.source / 'poster-081-v1.blend').is_file())

    def test_long_clear_hollow_tube_belongs_to_the_complete_pump(self):
        self.assertEqual(self.ancestor(self.tube_name), 'Pump')
        for name in ['96 fine grip flutes | rounded black closure',
                     'Arched lever with recessed open pump outlet',
                     'Complete dispenser barrel and tube socket',
                     'Piston collar and actuator stem']:
            self.assertEqual(self.ancestor(name), 'Pump')
        low, high = self.bounds(self.positions(self.tube_name))
        self.assertGreater(high[1] - low[1], 2)
        self.assertAlmostEqual(high[2] - low[2], .076, delta=.002)
        floor = max(self.ray_intersections(self.body_name))
        self.assertGreater(low[1] - floor, .005)
        self.assertLess(low[1] - floor, .05)
        opening = [(x * x + z * z) ** .5 for x, y, z in self.positions(self.tube_name) if abs(y - 2.21) < 1e-5]
        self.assertAlmostEqual(min(opening), .027, delta=.001)
        self.assertAlmostEqual(max(opening), .038, delta=.001)
        material = self.material(self.tube_name)
        self.assertGreater(material['extensions']['KHR_materials_transmission']['transmissionFactor'], .8)
        self.assertLess(material['pbrMetallicRoughness']['roughnessFactor'], .15)
        body_top = self.bounds(self.positions(self.body_name))[1][1]
        lift = self.product['review']['explosion']['offsets']['pump'][1]
        self.assertGreater(low[1] + lift - body_top, .2)

    def test_clear_empty_glass_preserves_open_mouth_and_thick_base(self):
        self.assertFalse(self.info['containsFormula'])
        names = [node['name'] for node in self.nodes] + [m['name'] for m in self.gltf['materials']]
        self.assertFalse(any(word in name.lower() for name in names for word in ['liquid', 'formula', 'meniscus']))
        material = self.material(self.body_name)
        self.assertEqual(material['extensions']['KHR_materials_transmission']['transmissionFactor'], 1)
        self.assertLess(material['pbrMetallicRoughness']['roughnessFactor'], .04)
        self.assertNotIn('baseColorTexture', material['pbrMetallicRoughness'])
        hits = self.ray_intersections(self.body_name)
        self.assertAlmostEqual(min(hits), 0, delta=.001)
        self.assertAlmostEqual(max(hits), .157, delta=.002)
        self.assertTrue(self.product['review']['appearance']['referenceGlass'])
        self.assertFalse(self.product['review']['appearance']['frosted'])

    def test_flag_wordmark_stays_with_the_sleeve_and_front_print_separates(self):
        for name in ['Black woven side flag', 'Ivory woven wrap sleeve | soft rolled edges', 'liaose on black side flag']:
            self.assertEqual(self.ancestor(name), 'Label')
        self.assertEqual(self.ancestor('liaose on woven sleeve'), 'LogoInk')
        self.assertEqual(self.ancestor('EXFOLIATING HAND GEL'), 'NameInk')
        offsets = self.product['review']['explosion']['offsets']
        self.assertGreater(offsets['logo'][2] - offsets['label'][2], .8)
        self.assertGreater(offsets['print'][2] - offsets['logo'][2], .3)
        for name in ['liaose on woven sleeve', 'EXFOLIATING HAND GEL', 'liaose on black side flag']:
            self.image(name).verify()
        self.assertTrue(all('uri' not in asset for asset in self.gltf['buffers'] + self.gltf['images']))
