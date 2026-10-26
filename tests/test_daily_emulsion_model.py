"""Inspect the exported Daily Emulsion single-bottle model and its local review config."""
from collections import Counter
import hashlib
import json
import math
import unittest
import xml.etree.ElementTree as ET

from PIL import Image, ImageChops
from test_micro_cream_model import CLIENT, ExportedModelReader


class DailyEmulsionModelTests(ExportedModelReader):
    model_id = '../public/review/daily-emulsion/daily-emulsion'
    body_name = 'Daily hollow flat rounded glass bottle'
    cover_name = 'Daily hollow clear overcap with soft top and mould dimple'
    head_name = 'Daily sloped press head with short right nozzle'
    source = CLIENT / 'model-source/collection/daily-emulsion'
    expected_roots = {'Body', 'PumpAssembly', 'Overcap',
                      'PaperLabel', 'LogoPrint', 'ProductPrint'}

    def group(self, name):
        def belongs(mesh):
            index = self.named[mesh]
            while True:
                if self.nodes[index]['name'] == name:
                    return True
                if index not in self.parents:
                    return False
                index = self.parents[index]
        return [n for n in self.mesh_names() if belongs(n)]

    def config(self):
        return json.loads((CLIENT / 'review-source/daily-emulsion/review-config.json').read_text())

    def test_single_bottle_six_roots_keep_three_pump_pieces_in_one_assembly(self):
        self.assertEqual({self.nodes[i]['name'] for i in self.gltf['scenes'][0]['nodes']},
                         self.expected_roots)
        self.assertEqual(len(self.mesh_names()), 8)
        for name in self.expected_roots:
            self.assertEqual(len(self.group(name)), 3 if name == 'PumpAssembly' else 1)
        assembly = self.named['PumpAssembly']
        self.assertEqual({self.nodes[i]['name'] for i in self.nodes[assembly]['children']},
                         {'Closure', 'PumpStem', 'Actuator'})
        for name in ('Closure', 'PumpStem', 'Actuator'):
            self.assertEqual(self.parents[self.named[name]], assembly)
            self.assertEqual(len(self.group(name)), 1)
        self.assertTrue(all('uri' not in item for item in self.gltf['buffers'] + self.gltf['images']))

    def test_reference_proportions_and_normalized_height(self):
        width = self.width()
        low, high = self.bounds([p for n in self.mesh_names() for p in self.positions(n)])
        self.assertAlmostEqual(high[1] - low[1], 2.9, delta=.001)
        self.assertAlmostEqual((high[1] - low[1]) / width, 2.80, delta=.002)
        low, high = self.bounds(self.positions(self.body_name))
        self.assertAlmostEqual(high[1] / width, 1.972, delta=.002)
        self.assertAlmostEqual((high[2] - low[2]) / width, .58, delta=.002)
        low, high = self.bounds(self.positions(self.cover_name))
        self.assertAlmostEqual((high[0] - low[0]) / width, .628, delta=.002)
        self.assertAlmostEqual((high[1] - low[1]) / width, .684, delta=.002)
        low, high = self.bounds(self.positions(self.group('Closure')[0]))
        self.assertAlmostEqual((high[0] - low[0]) / width, .69, delta=.002)

    def test_colourless_frosted_body_clear_cover_opaque_white_pump_and_no_formula(self):
        for name in (self.body_name, self.cover_name):
            material = self.material(name)
            pbr = material['pbrMetallicRoughness']
            self.assertTrue(all(c > .99 for c in pbr.get('baseColorFactor', [1] * 4)[:3]))
            self.assertNotIn('baseColorTexture', pbr)
            self.assertEqual(material['extensions']['KHR_materials_transmission']['transmissionFactor'], 1)
        self.assertGreaterEqual(self.material(self.body_name)['pbrMetallicRoughness']['roughnessFactor'], .24)
        self.assertLess(self.material(self.cover_name)['pbrMetallicRoughness']['roughnessFactor'], .06)
        for group in ('Actuator', 'Closure', 'PumpStem'):
            material = self.material(self.group(group)[0])
            self.assertNotIn('KHR_materials_transmission', material.get('extensions', {}))
            self.assertGreater(min(material['pbrMetallicRoughness']['baseColorFactor'][:3]), .75)
        self.assertFalse(any('liquid' in n.get('name', '').lower() or 'meniscus' in n.get('name', '').lower()
                             for n in self.nodes + self.gltf['materials']))
        appearance = self.config()['product']['review']['appearance']
        self.assertIs(appearance['frosted'], True)
        self.assertIs(appearance['clearOvercap'], True)
        self.assertNotIn('liquid', appearance)

    def test_actual_hollow_floor_watertight_solids_and_outward_normals(self):
        width = self.width()
        hits = self.ray_intersections(self.body_name)
        self.assertAlmostEqual(min(hits), 0, delta=1e-6)
        self.assertAlmostEqual(max(hits) / width, .14, delta=.002)
        for group in ('Body', 'Closure', 'PumpStem', 'Actuator', 'Overcap'):
            name = self.group(group)[0]
            primitive = self.primitive(name)
            positions = self.accessor(primitive['attributes']['POSITION'])
            normals = self.accessor(primitive['attributes']['NORMAL'])
            ids = [v[0] for v in self.accessor(primitive['indices'])]
            welded = [tuple(round(x / width, 6) for x in p) for p in self.positions(name)]
            edges = Counter()
            for i in range(0, len(ids), 3):
                tri = ids[i:i + 3]
                a, b, c = [welded[j] for j in tri]
                self.assertEqual(len({a, b, c}), 3, name)
                edges.update(tuple(sorted(e)) for e in ((a, b), (b, c), (c, a)))
                a, b, c = [positions[j] for j in tri]
                u, v = [[p[k] - a[k] for k in range(3)] for p in (b, c)]
                cross = [u[1]*v[2] - u[2]*v[1], u[2]*v[0] - u[0]*v[2], u[0]*v[1] - u[1]*v[0]]
                average = [sum(normals[j][k] for j in tri) / 3 for k in range(3)]
                self.assertGreaterEqual(sum(cross[k] * average[k] for k in range(3)), -1e-10, name)
            self.assertEqual(set(edges.values()), {2}, name)

    def test_clear_cover_roof_clears_actuator_through_the_whole_opening_motion(self):
        roof = min(self.ray_intersections(self.cover_name))
        head_top = self.bounds(self.positions(self.head_name))[1][1]
        explosion = self.config()['product']['review']['explosion']
        cover_lift = explosion['offsets']['overcap'][1]
        pump_lift = explosion['offsets']['pump'][1]
        self.assertEqual(explosion['offsets']['pump'], [0, 1.05, 0])
        self.assertEqual(explosion['offsets']['overcap'], [0, 2.35, 0])
        for settings in ('offsets', 'scales', 'timing', 'rotations'):
            self.assertFalse({'head', 'stem', 'closure'} & set(explosion.get(settings, {})))
        self.assertEqual(explosion.get('scales', {}).get('pump', 1), 1)
        self.assertEqual(explosion.get('rotations', {}).get('pump', [0, 0, 0]), [0, 0, 0])
        interval = explosion.get('timing', {}).get('overcap')
        cover_amount = lambda progress: self.smooth(*interval, progress) if interval else progress
        clearances = [roof + cover_lift * cover_amount(p / 1000)
                      - head_top - pump_lift * p / 1000 for p in range(1001)]
        self.assertGreater(min(clearances), .02)
        # Project the real cover vertices at the neutral desktop camera's 1.05/10 tilt.
        # This catches the early cover lift that previously escaped the compact half-open frame.
        camera = explosion['camera']
        tilt = math.atan2(1.05, 10)
        for step in range(101):
            progress = step / 100
            lerp = lambda pair: pair[0] + (pair[1] - pair[0]) * progress
            height = max(lerp(camera['height']), lerp(camera['width']) / (1200 / 800))
            top = max((p[1] + cover_lift * cover_amount(progress) - lerp(camera['centerY'])) * math.cos(tilt)
                      - p[2] * math.sin(tilt) for p in self.positions(self.cover_name))
            self.assertGreater(height / 2 - top, .1, f'cover headroom at {progress:.2f}')
        parts = [('Overcap', 'overcap'), ('PumpAssembly', 'pump'), ('Body', 'body')]
        for (upper, upper_key), (lower, lower_key) in zip(parts, parts[1:]):
            upper_min = min(p[1] for n in self.group(upper) for p in self.positions(n))
            lower_max = max(p[1] for n in self.group(lower) for p in self.positions(n))
            self.assertGreater(upper_min + explosion['offsets'].get(upper_key, [0, 0, 0])[1]
                               - lower_max - explosion['offsets'].get(lower_key, [0, 0, 0])[1], .1)

    def test_all_reference_copy_and_blank_carrier_are_separate_embedded_artwork(self):
        film = ET.parse(self.source / 'label.svg').getroot()
        self.assertFalse(any(e.tag.endswith(('}path', '}text')) for e in film.iter()))
        brand = ET.parse(self.source / 'print.svg').getroot()
        self.assertTrue(any(e.tag.endswith('}path') for e in brand.iter()))
        self.assertFalse(any(e.tag.endswith('}text') for e in brand.iter()))
        names = ET.parse(self.source / 'name.svg').getroot()
        self.assertEqual([e.text for e in names.iter() if e.tag.endswith('}text')], ['DAILY EMULSION', 'FACE CARE'])
        self.assertTrue(any(e.tag.endswith('}path') for e in names.iter()))
        for group, file in [('PaperLabel', 'label.png'), ('LogoPrint', 'print.png'), ('ProductPrint', 'name.png')]:
            mesh = self.group(group)[0]
            self.assertIsNone(ImageChops.difference(self.image(mesh), Image.open(self.source / file).convert('RGBA')).getbbox(alpha_only=False))
        self.assertLess(self.image(self.group('PaperLabel')[0]).getchannel('A').getextrema()[1], 170)
        # Compare visible ink width, not SVG textLength (some rasterizers ignore it).
        ink = self.image(self.group('ProductPrint')[0]).getchannel('A')
        for top, bottom, minimum, maximum in [(.68, .78, .53, .565), (.83, .92, .28, .31)]:
            box = ink.crop((0, int(top * ink.height), ink.width, int(bottom * ink.height))).getbbox()
            self.assertIsNotNone(box)
            width_to_bottle = (box[2] - box[0]) / ink.width * .66
            self.assertGreater(width_to_bottle, minimum)
            self.assertLess(width_to_bottle, maximum)

    def test_closed_artwork_stays_on_flat_front_and_text_moves_farther_out(self):
        front = self.bounds(self.positions(self.body_name))[1][2]
        depths = []
        for group in ('PaperLabel', 'LogoPrint', 'ProductPrint'):
            low, high = self.bounds(self.positions(self.group(group)[0]))
            self.assertAlmostEqual(high[0] - low[0], self.width() * .66, delta=.001)
            self.assertAlmostEqual(high[2], low[2], delta=1e-7)
            self.assertGreater(low[2], front)
            self.assertLess(low[2] - front, .004)
            depths.append(low[2])
        self.assertEqual(depths, sorted(depths))
        explosion = self.config()['product']['review']['explosion']
        for key in ('print', 'name'):
            self.assertGreater(explosion['offsets'][key][2] - explosion['offsets']['label'][2], 1)
            self.assertGreater(explosion['scales'][key], explosion['scales']['label'])
        self.assertNotEqual(explosion['offsets']['print'][1], explosion['offsets']['name'][1])

    def test_local_review_config_and_source_metadata_match_delivered_model(self):
        product = self.config()['product']
        self.assertEqual(product['kind'], 'collection')
        self.assertEqual(product['file'], 'daily-emulsion.glb')
        self.assertEqual({p['node'] for p in product['parts']}, self.expected_roots)
        info = json.loads((self.source / 'model-info.json').read_text())
        self.assertEqual(info['state'], 'local-review')
        self.assertEqual(info['bottleCount'], 1)
        self.assertIs(info['containsFormula'], False)
        self.assertEqual(info['printIncludes'], ['liaose', 'horizontal rule', 'DAILY EMULSION', 'FACE CARE'])
        model = (CLIENT / 'public/review/daily-emulsion/daily-emulsion.glb').read_bytes()
        self.assertEqual(hashlib.sha256(model).hexdigest(), info['glbSha256'])
        self.assertEqual(len(model), info['glbBytes'])
        self.assertTrue((self.source / 'daily-emulsion.blend').is_file())
        self.assertEqual((self.source / 'reference.png').read_bytes(),
                         (CLIENT / 'public/review/daily-emulsion/reference.png').read_bytes())


if __name__ == '__main__':
    unittest.main()
