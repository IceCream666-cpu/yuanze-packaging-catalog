"""Reference-led checks of the actual 058–061 GLBs, artwork and material separation."""
from collections import Counter
import json
import unittest
import xml.etree.ElementTree as ET

from PIL import Image, ImageChops
from test_micro_cream_model import CLIENT, ExportedModelReader


class ReviewedPackagingChecks:
    def source(self):
        return CLIENT / 'model-source/collection' / self.model_id

    def in_group(self, group):
        return [name for name in self.mesh_names() if self.ancestor(name) == group]

    def test_independent_parts_retain_the_requested_bottle_count(self):
        roots = {self.nodes[i]['name'] for i in self.gltf['scenes'][0]['nodes']}
        self.assertEqual(roots, set(self.component_counts))
        for group, count in self.component_counts.items():
            self.assertEqual(len(self.in_group(group)), count, group)
        low, high = self.bounds([p for name in self.mesh_names() for p in self.positions(name)])
        self.assertAlmostEqual(high[1] - low[1], 2.9, delta=.003)
        self.assertFalse(self.gltf.get('animations'))
        self.assertFalse(self.gltf.get('cameras'))
        self.assertTrue(all('uri' not in entry for entry in self.gltf['images'] + self.gltf['buffers']))
        info = json.loads((self.source() / 'model-info.json').read_text())
        self.assertFalse(info['containsFormula'])
        self.assertTrue(info['illustrativeDimensions'])
        self.assertTrue((self.source() / (self.model_id + '.blend')).is_file())

    def test_complete_print_and_blank_substrate_match_the_exported_pixels(self):
        label = ET.parse(self.source() / 'label.svg').getroot()
        self.assertFalse(any(element.tag.endswith(('}text', '}path')) for element in label.iter()),
                         'The substrate must not retain a second copy of the printing.')
        for filename, expected in self.svg_copy.items():
            root = ET.parse(self.source() / filename).getroot()
            self.assertEqual([element.text for element in root.iter() if element.tag.endswith('}text')], expected)
            self.assertTrue(any(element.tag.endswith('}path') for element in root.iter()), 'The brand vector must remain.')
        info = json.loads((self.source() / 'model-info.json').read_text())
        self.assertEqual(info['printIncludes'], self.complete_copy)
        for name in self.in_group('LogoPrint') + self.in_group('PaperLabel'):
            filename = 'label.png' if self.ancestor(name) == 'PaperLabel' else self.print_file(name)
            original = Image.open(self.source() / filename).convert('RGBA')
            self.assertIsNone(ImageChops.difference(self.image(name), original).getbbox(alpha_only=False), name)
        for name in self.in_group('Body'):
            self.assertNotIn('baseColorTexture', self.material(name)['pbrMetallicRoughness'])

    def test_real_glass_floor_open_mouth_and_closed_wall_topology(self):
        for name in self.in_group('Body'):
            points = self.positions(name)
            low, high = self.bounds(points)
            width = high[0] - low[0]
            hits = self.ray_intersections(name, a=(low[0] + high[0]) / 2, b=(low[2] + high[2]) / 2)
            self.assertAlmostEqual(min(hits), 0, delta=1e-6)
            self.assertAlmostEqual(max(hits) / width, self.floor_ratio, delta=.002)
            indices = [i[0] for i in self.accessor(self.primitive(name)['indices'])]
            welded = [tuple(round(value / width, 6) for value in point) for point in points]
            edges = Counter()
            for i in range(0, len(indices), 3):
                a, b, c = [welded[j] for j in indices[i:i + 3]]
                if len({a, b, c}) < 3:
                    continue
                edges.update(tuple(sorted(edge)) for edge in [(a, b), (b, c), (c, a)])
            self.assertEqual(set(edges.values()), {2}, name)

    def test_glass_material_is_empty_and_print_is_in_front_of_its_carrier(self):
        for name in self.in_group('Body'):
            material = self.material(name)
            transmission = material['extensions']['KHR_materials_transmission']['transmissionFactor']
            pbr = material['pbrMetallicRoughness']
            if self.model_id == 'poster-061':
                self.assertAlmostEqual(transmission, .62, delta=.001)
                self.assertGreater(pbr['roughnessFactor'], .30)
                self.assertGreater(min(pbr.get('baseColorFactor', [1, 1, 1, 1])[:3]), .70)
            else:
                self.assertGreaterEqual(transmission, .99)
                self.assertLess(pbr['roughnessFactor'], .04)
                self.assertTrue(all(value > .99 for value in pbr.get('baseColorFactor', [1, 1, 1, 1])[:3]))
        labels = sorted(self.in_group('PaperLabel'))
        prints = sorted(self.in_group('LogoPrint'))
        for label, printing in zip(labels, prints):
            lp, pp = self.positions(label), self.positions(printing)
            self.assertEqual(len(lp), len(pp))
            for a, b in zip(lp, pp):
                self.assertAlmostEqual(a[0], b[0], delta=1e-6)
                self.assertAlmostEqual(a[1], b[1], delta=1e-6)
                self.assertGreater(b[2], a[2], 'Complete printing must be outside the substrate.')

    def print_file(self, name):
        return 'print.png'


class LuminousFaceOilModelTests(ReviewedPackagingChecks, ExportedModelReader):
    model_id = 'poster-058'
    body_name = 'Hollow slender flat Luminous glass bottle'
    component_counts = {'Body': 1, 'Closure': 1, 'DropperBulb': 1, 'Pipette': 1, 'PaperLabel': 1, 'LogoPrint': 1}
    floor_ratio = .124
    svg_copy = {'print.svg': ['LUMINOUS', 'FACE OIL', '50 ml']}
    complete_copy = ['liaose', 'LUMINOUS', 'FACE OIL', 'warm separator rule', '50 ml']

    def test_reference_slender_shape_silver_collar_and_lightly_wrapped_paper(self):
        width = self.width()
        self.assertAlmostEqual(2.9 / width, 3.65, delta=.01)
        low, high = self.bounds(self.positions(self.body_name))
        self.assertAlmostEqual((high[2] - low[2]) / width, .4, delta=.003)
        collar = self.material(self.in_group('Closure')[0])['pbrMetallicRoughness']
        self.assertEqual(collar.get('metallicFactor', 1), 1)
        self.assertLess(collar['roughnessFactor'], .1)
        low, high = self.bounds(self.positions(self.in_group('PaperLabel')[0]))
        self.assertAlmostEqual((high[0] - low[0]) / width, .98, delta=.003)
        self.assertAlmostEqual((high[1] - low[1]) / width, 1.415, delta=.003)
        self.assertGreater((high[2] - low[2]) / width, .018)
        self.assertLess((high[2] - low[2]) / width, .030)
        pipe = self.bounds(self.positions(self.in_group('Pipette')[0]))
        self.assertAlmostEqual(pipe[0][1] / width, 2.0, delta=.002)


class EssenceOilDuoModelTests(ReviewedPackagingChecks, ExportedModelReader):
    model_id = 'poster-059'
    body_name = 'Essence hollow rounded rectangular glass'
    component_counts = {'Body': 2, 'Closure': 2, 'DropperBulb': 2, 'Pipette': 2, 'PaperLabel': 2, 'LogoPrint': 2}
    floor_ratio = .143
    svg_copy = {'print.svg': ['ESSENCE OIL'], 'print-biphase.svg': ['BIPHASE ESSENCE OIL']}
    complete_copy = ['liaose', 'ESSENCE OIL', 'liaose', 'BIPHASE ESSENCE OIL']

    def print_file(self, name):
        return 'print-biphase.png' if name.startswith('Biphase') else 'print.png'

    def test_two_equal_bottles_have_reference_spacing_and_no_fabricated_volume_copy(self):
        width = self.width()
        self.assertAlmostEqual(2.9 / width, 2.12, delta=.01)
        boxes = [self.bounds(self.positions(name)) for name in self.in_group('Body')]
        for low, high in boxes:
            self.assertAlmostEqual((high[0] - low[0]) / width, 1, delta=.003)
            self.assertAlmostEqual((high[2] - low[2]) / width, .40, delta=.003)
        centers = sorted((low[0] + high[0]) / 2 for low, high in boxes)
        self.assertAlmostEqual((centers[1] - centers[0]) / width, 1.06, delta=.003)
        self.assertGreater(centers[1] - centers[0], width)
        self.assertTrue(all('ml' not in text.lower() for copy in self.svg_copy.values() for text in copy))


class AHABodyMistModelTests(ReviewedPackagingChecks, ExportedModelReader):
    model_id = 'poster-060'
    body_name = 'Hollow cylindrical glass with rounded shoulder and thick base'
    component_counts = {'Body': 1, 'Closure': 1, 'PumpStem': 2, 'Actuator': 2, 'PaperLabel': 1, 'LogoPrint': 1}
    floor_ratio = .18
    svg_copy = {'print.svg': ['AHA', 'BODY MIST', '160 ml']}
    complete_copy = ['liaose', 'AHA', 'BODY MIST', 'short separator rule', '160 ml']

    def test_round_bottle_silver_brushed_foil_and_real_curved_tube(self):
        width = self.width()
        self.assertAlmostEqual(2.9 / width, 3.53, delta=.01)
        low, high = self.bounds(self.positions(self.body_name))
        self.assertAlmostEqual((high[2] - low[2]) / width, 1, delta=.003)
        label = self.material(self.in_group('PaperLabel')[0])['pbrMetallicRoughness']
        self.assertEqual(label.get('metallicFactor', 1), 1)
        self.assertAlmostEqual(label['roughnessFactor'], .30, delta=.001)
        self.assertIn('baseColorTexture', label)
        low, high = self.bounds(self.positions('Curved hollow clear suction tube'))
        self.assertGreater((high[0] - low[0]) / width, .3)
        self.assertLess(low[1] / width, .22)
        self.assertGreater(low[1] / width, self.floor_ratio)


class OilInfusedBodyCreamModelTests(ReviewedPackagingChecks, ExportedModelReader):
    model_id = 'poster-061'
    body_name = 'Taller hollow frosted round-bottom bottle'
    component_counts = {'Body': 2, 'Closure': 2, 'PumpStem': 2, 'Actuator': 4, 'PaperLabel': 2, 'LogoPrint': 2}
    floor_ratio = .11
    svg_copy = {'print.svg': ['OIL-INFUSED', 'BODY CREAM']}
    complete_copy = ['liaose', 'OIL-INFUSED', 'BODY CREAM']

    def test_two_reference_heights_round_bases_and_open_right_facing_spouts(self):
        width = self.width()
        for prefix, ratio in [('Smaller', 2.20), ('Taller', 2.32)]:
            points = [p for name in self.mesh_names() if name.startswith(prefix) for p in self.positions(name)]
            low, high = self.bounds(points)
            self.assertAlmostEqual((high[1] - low[1]) / width, ratio, delta=.005)
            spout = self.bounds(self.positions(prefix + ' curved hollow oval pump spout'))
            self.assertGreater((spout[1][0] - spout[0][0]) / width, .3)
        boxes = [self.bounds(self.positions(name)) for name in self.in_group('Body')]
        centers = [((low[0] + high[0]) / 2, (low[2] + high[2]) / 2) for low, high in boxes]
        separation = ((centers[0][0] - centers[1][0])**2 + (centers[0][1] - centers[1][1])**2)**.5
        self.assertGreater(separation, width, 'The staggered cylindrical bottles must not intersect.')


if __name__ == '__main__':
    unittest.main()
