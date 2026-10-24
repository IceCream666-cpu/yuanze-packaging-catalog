"""Check Coastal 047's exported surfaces and artwork against its original poster."""
from collections import Counter
import io
import json
import math
from pathlib import Path
import struct
import unittest
import xml.etree.ElementTree as ET

from PIL import Image, ImageChops, ImageStat

CLIENT = Path(__file__).resolve().parents[1] / 'docs/client-motion-demo'
SOURCE = CLIENT / 'model-source/collection/poster-047'
BODY = 'Hollow short cylindrical bottle with heavy glass base'
CORK = 'Two-step tapered cork with integrated stopper foot'
PAPER = 'Warm white textured paper label'
PRINT = 'Complete Coastal perfume lettering'


class CoastalModelTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        raw = (CLIENT / 'packaging-assets/poster-047.glb').read_bytes()
        if struct.unpack_from('<4sII', raw) != (b'glTF', 2, len(raw)):
            raise ValueError('Expected a complete GLB 2.0 model')
        length, kind = struct.unpack_from('<I4s', raw, 12)
        if kind != b'JSON':
            raise ValueError('Expected a GLB JSON chunk')
        cls.gltf = json.loads(raw[20:20 + length])
        size, kind = struct.unpack_from('<I4s', raw, 20 + length)
        if kind != b'BIN\0':
            raise ValueError('Expected embedded model data')
        cls.binary = raw[28 + length:28 + length + size]
        cls.nodes = cls.gltf['nodes']
        cls.named = {node['name']: i for i, node in enumerate(cls.nodes)}
        cls.parents = {child: i for i, node in enumerate(cls.nodes) for child in node.get('children', [])}
        cls.world_points = {}

    def ancestor(self, name):
        index = self.named[name]
        while index in self.parents:
            index = self.parents[index]
        return self.nodes[index]['name']

    def mesh_names(self):
        return [node['name'] for node in self.nodes if 'mesh' in node]

    def primitive(self, name):
        primitive, = self.gltf['meshes'][self.nodes[self.named[name]]['mesh']]['primitives']
        return primitive

    def accessor(self, index):
        accessor = self.gltf['accessors'][index]
        self.assertNotIn('sparse', accessor)
        view = self.gltf['bufferViews'][accessor['bufferView']]
        fmt = '<' + {5121: 'B', 5123: 'H', 5125: 'I', 5126: 'f'}[accessor['componentType']] * {'SCALAR': 1, 'VEC2': 2, 'VEC3': 3}[accessor['type']]
        offset = view.get('byteOffset', 0) + accessor.get('byteOffset', 0)
        stride = view.get('byteStride', struct.calcsize(fmt))
        return [struct.unpack_from(fmt, self.binary, offset + i * stride) for i in range(accessor['count'])]

    def positions(self, name):
        if name not in self.world_points:
            points = self.accessor(self.primitive(name)['attributes']['POSITION'])
            index = self.named[name]
            # Measure the closed assembly after the complete parent/pivot transform chain.
            while True:
                node = self.nodes[index]
                self.assertNotIn('matrix', node)
                self.assertEqual(node.get('rotation', [0, 0, 0, 1]), [0, 0, 0, 1])
                scale, translation = node.get('scale', [1, 1, 1]), node.get('translation', [0, 0, 0])
                points = [tuple(p[j] * scale[j] + translation[j] for j in range(3)) for p in points]
                if index not in self.parents:
                    break
                index = self.parents[index]
            self.world_points[name] = points
        return self.world_points[name]

    @staticmethod
    def bounds(points):
        return ([min(p[j] for p in points) for j in range(3)],
                [max(p[j] for p in points) for j in range(3)])

    def diameter(self):
        low, high = self.bounds(self.positions(BODY))
        return high[0] - low[0]

    def radii_at(self, name, level):
        diameter = self.diameter()
        radii = [math.hypot(x, z) / diameter for x, y, z in self.positions(name)
                 if abs(y / diameter - level) < 1e-5]
        self.assertTrue(radii, f'{name} must retain its profile at {level}D')
        return radii

    def material(self, name):
        return self.gltf['materials'][self.primitive(name)['material']]

    def image(self, name, normal=False):
        material = self.material(name)
        texture = (material['normalTexture'] if normal else material['pbrMetallicRoughness']['baseColorTexture'])['index']
        image = self.gltf['images'][self.gltf['textures'][texture]['source']]
        view = self.gltf['bufferViews'][image['bufferView']]
        offset = view.get('byteOffset', 0)
        return Image.open(io.BytesIO(self.binary[offset:offset + view['byteLength']])).convert('RGBA')

    def assert_connected_axis(self, name, level):
        diameter = self.diameter()
        axis = {i for i, (x, y, z) in enumerate(self.positions(name))
                if math.hypot(x, z) < 1e-6 and abs(y / diameter - level) < 1e-5}
        self.assertTrue(axis, f'{name} must be sealed at {level}D')
        indices = [item[0] for item in self.accessor(self.primitive(name)['indices'])]
        self.assertGreaterEqual(sum(i in axis for i in indices), 3, 'A loose axis vertex is not a closing face.')

    def test_four_independent_groups_contain_only_empty_packaging(self):
        expected = {'Body': BODY, 'Closure': CORK, 'PaperLabel': PAPER, 'LogoPrint': PRINT}
        roots = self.gltf['scenes'][self.gltf.get('scene', 0)]['nodes']
        self.assertEqual({self.nodes[i]['name'] for i in roots}, set(expected))
        self.assertEqual(set(self.mesh_names()), set(expected.values()),
                         'No liquid, spray pump, duplicate lettering or old bottle mesh may remain.')
        for group, name in expected.items():
            self.assertEqual(self.ancestor(name), group)
        self.assertTrue(all('uri' not in item for item in self.gltf['images'] + self.gltf['buffers']))
        self.assertFalse(self.gltf.get('animations'))
        self.assertFalse(self.gltf.get('cameras'))
        info = json.loads((SOURCE / 'model-info.json').read_text())
        self.assertFalse(info['containsFormula'])
        self.assertTrue(info['illustrativeDimensions'])
        self.assertTrue((SOURCE / 'poster-047.blend').is_file())

    def test_short_round_body_and_two_step_cork_match_reference_proportions(self):
        diameter = self.diameter()
        low, high = self.bounds([p for name in self.mesh_names() for p in self.positions(name)])
        self.assertAlmostEqual(high[1] - low[1], 2.9, delta=.005)
        self.assertAlmostEqual((high[1] - low[1]) / diameter, 1.89, delta=.02)
        body_low, body_high = self.bounds(self.positions(BODY))
        self.assertAlmostEqual((body_high[2] - body_low[2]) / diameter, 1, places=5)
        self.assertAlmostEqual(body_high[1] / diameter, 1.329, delta=.01)
        for level in [.064, 1.185]:
            self.assertLess(max(abs(r - .5) for r in self.radii_at(BODY, level)), 1e-6)
        self.assertAlmostEqual(max(self.radii_at(BODY, .020)), .476, delta=.002)
        self.assertAlmostEqual(max(self.radii_at(BODY, 1.280)), .326, delta=.002)
        cork_low, cork_high = self.bounds(self.positions(CORK))
        self.assertAlmostEqual((cork_high[1] - body_high[1]) / diameter, .57, delta=.015)
        self.assertAlmostEqual((cork_high[0] - cork_low[0]) / diameter, .674, delta=.006)
        lower = self.radii_at(CORK, 1.442)
        self.assertAlmostEqual(sum(lower) / len(lower), .255, delta=.001)
        upper = self.radii_at(CORK, 1.874)
        self.assertAlmostEqual(sum(upper) / len(upper), .337, delta=.001)
        self.assertGreater(min(upper) - max(lower), .07, 'The cap must retain its wide tapered upper section.')
        self.assertAlmostEqual(max(self.radii_at(CORK, 1.459)), .285, delta=.003)
        self.assertGreater(max(upper) - min(upper), .002, 'Retain subtle physical cork-chip relief.')
        self.assert_connected_axis(CORK, 1.175)
        self.assert_connected_axis(CORK, 1.890)

    def test_glass_has_open_mouth_hollow_walls_and_a_connected_heavy_base(self):
        mouth = self.radii_at(BODY, 1.329)
        self.assertAlmostEqual(min(mouth), .203, delta=.002)
        self.assertAlmostEqual(max(mouth), .243, delta=.002)
        self.assertAlmostEqual(min(self.radii_at(BODY, 1.198)), .462, delta=.002)
        self.assert_connected_axis(BODY, 0)
        self.assert_connected_axis(BODY, .210)
        diameter = self.diameter()
        points = self.positions(BODY)
        self.assertFalse(any(y / diameter > .211 and math.hypot(x, z) < 1e-6 for x, y, z in points),
                         'No face may fill the bottle cavity above the thick bottom.')
        # Weld exporter normal splits, then verify the inner wall and outer wall form a closed solid shell.
        welded = [tuple(round(v / diameter, 6) for v in p) for p in points]
        indices = [item[0] for item in self.accessor(self.primitive(BODY)['indices'])]
        edges = Counter()
        for i in range(0, len(indices), 3):
            a, b, c = [welded[j] for j in indices[i:i + 3]]
            self.assertEqual(len({a, b, c}), 3, 'Degenerate triangles cannot seal the glass base.')
            edges.update(tuple(sorted(pair)) for pair in [(a, b), (b, c), (c, a)])
        self.assertEqual(set(edges.values()), {2}, 'The glass wall must not contain open seams or holes.')

    def test_glass_is_neutral_clear_and_cork_and_paper_remain_matte_nonmetal(self):
        glass = self.material(BODY)
        pbr = glass['pbrMetallicRoughness']
        self.assertGreaterEqual(min(pbr.get('baseColorFactor', [1, 1, 1, 1])[:3]), .99,
                                'The photographed liquid must not tint the empty glass yellow-green.')
        self.assertGreaterEqual(glass['extensions']['KHR_materials_transmission']['transmissionFactor'], .99)
        self.assertAlmostEqual(glass['extensions']['KHR_materials_ior']['ior'], 1.49, delta=.02)
        self.assertLessEqual(pbr['roughnessFactor'], .04)
        self.assertNotIn('Texture', json.dumps(glass), 'No wording or formula image may stay on the bottle.')
        for name in self.mesh_names():
            self.assertEqual(self.material(name)['pbrMetallicRoughness'].get('metallicFactor', 1), 0)
        self.assertGreater(self.material(CORK)['pbrMetallicRoughness']['roughnessFactor'], .75)
        self.assertGreater(self.material(PAPER)['pbrMetallicRoughness']['roughnessFactor'], .70)
        self.assertAlmostEqual(self.material(CORK)['normalTexture']['scale'], .70, delta=.01)

    def test_separate_paper_and_print_fit_the_same_cylinder_without_changing_closed_layout(self):
        diameter = self.diameter()
        low, high = self.bounds(self.positions(PAPER))
        self.assertAlmostEqual((high[0] - low[0]) / diameter, .85, delta=.005)
        self.assertAlmostEqual((high[1] - low[1]) / diameter, .72, delta=.005)
        self.assertAlmostEqual(low[1] / diameter, .32, delta=.005)
        self.assertAlmostEqual((low[1] + high[1]) / (2 * diameter), .68, delta=.005)
        for name, offset in [(PAPER, .0015), (PRINT, .0022)]:
            points = self.positions(name)
            bounds = self.bounds(points)
            for axis in [0, 1]:
                self.assertAlmostEqual(bounds[0][axis], low[axis], places=6)
                self.assertAlmostEqual(bounds[1][axis], high[axis], places=6)
            self.assertGreater((bounds[1][2] - bounds[0][2]) / diameter, .20,
                               'The broad label must curve around the cylindrical glass.')
            for x, y, z in points:
                self.assertAlmostEqual((z - math.sqrt((diameter / 2) ** 2 - x ** 2)) / diameter, offset, delta=1e-6)
            uv = self.accessor(self.primitive(name)['attributes']['TEXCOORD_0'])
            self.assertEqual(min(u for u, v in uv), 0)
            self.assertEqual(max(u for u, v in uv), 1)
            self.assertEqual(min(v for u, v in uv), 0)
            self.assertEqual(max(v for u, v in uv), 1)
            self.assertEqual(self.material(name)['alphaMode'], 'BLEND')
        self.assertNotEqual(self.primitive(PAPER)['material'], self.primitive(PRINT)['material'])

    def test_embedded_cork_and_blank_fibre_paper_match_the_editable_textures(self):
        images = [(self.image(CORK), 'cork-color.jpg'), (self.image(CORK, normal=True), 'cork-normal.png'),
                  (self.image(PAPER), 'label.png'), (self.image(PRINT), 'print.png')]
        for image, filename in images:
            with Image.open(SOURCE / filename) as source:
                self.assertEqual(image.size, source.size)
                self.assertIsNone(ImageChops.difference(image, source.convert('RGBA')).getbbox(alpha_only=False))
        cork, normal, paper = [item[0] for item in images[:3]]
        # The embedded JPEG must match the approved JPEG exactly, while retaining the PNG master's colour and pores.
        with Image.open(SOURCE / 'cork.png') as master:
            self.assertEqual(cork.size, master.size)
            error = ImageStat.Stat(ImageChops.difference(cork, master.convert('RGBA')))
            self.assertLess(max(error.mean[:3]), 3)
            self.assertLess(max(high for low, high in error.extrema[:3]), 32)
        self.assertEqual(cork.getchannel('A').getextrema(), (255, 255))
        cork_stats = ImageStat.Stat(cork)
        self.assertTrue(cork_stats.mean[0] > cork_stats.mean[1] > cork_stats.mean[2])
        self.assertGreater(min(cork_stats.stddev[:3]), 12, 'Retain coarse cork chips rather than a flat tan cap.')
        normal_stats = ImageStat.Stat(normal)
        self.assertGreater(min(normal_stats.stddev[:2]), 10)
        self.assertGreater(normal_stats.mean[2], 240)
        flat = normal.getchannel('B').point(lambda value: 255 if value >= 254 else 0)
        flat_stats = ImageStat.Stat(normal, flat)
        for channel in [0, 1]:
            self.assertIn(flat_stats.median[channel], [127, 128])
            self.assertAlmostEqual(flat_stats.mean[channel], 127.5, delta=1,
                                   msg='Normal maps must not gamma-shift their neutral channels toward 188.')
        alpha = paper.getchannel('A')
        visible = alpha.point(lambda value: 255 if value > 32 else 0)
        stats = ImageStat.Stat(paper.convert('RGB'), visible)
        self.assertGreater(min(low for low, high in stats.extrema), 210,
                           'Blank paper must not retain any dark text, rules or baked-in shadows.')
        self.assertTrue(.7 < stats.stddev[0] < 5, 'Keep the restrained paper fibre texture.')
        self.assertEqual(alpha.getpixel((0, 0)), 0)
        self.assertEqual(alpha.getpixel((paper.width // 2, paper.height // 2)), 255)
        self.assertFalse(any(e.tag.endswith(('}text', '}path')) for e in ET.parse(SOURCE / 'label.svg').getroot().iter()))

    def test_all_five_print_bands_and_exact_copy_are_on_the_independent_print_layer(self):
        printing = self.image(PRINT)
        alpha = printing.getchannel('A').point(lambda value: 255 if value > 32 else 0)
        self.assertLess(max(ImageStat.Stat(printing.convert('RGB'), alpha).mean), 45)
        rows = [bool(alpha.crop((0, y, printing.width, y + 1)).getbbox()) for y in range(printing.height)]
        starts = [i for i, filled in enumerate(rows) if filled and (i == 0 or not rows[i - 1])]
        ends = [i + 1 for i, filled in enumerate(rows) if filled and (i + 1 == len(rows) or not rows[i + 1])]
        self.assertEqual(len(starts), 5, 'Logo, COASTAL, rule, PERFUME and 50 ml must all move together.')
        low, high = self.bounds(self.positions(PRINT))
        diameter = self.diameter()
        targets = [(.50, .21, .86), (.34, .038, .660), (.102, .002, .580), (.24, .027, .502), (.133, .044, .394)]
        for start, end, (width, height, center) in zip(starts, ends, targets):
            bounds = alpha.crop((0, start, printing.width, end)).getbbox()
            self.assertAlmostEqual((bounds[2] - bounds[0]) / printing.width * (high[0] - low[0]) / diameter, width, delta=.025)
            self.assertAlmostEqual((end - start) / printing.height * (high[1] - low[1]) / diameter, height, delta=.008)
            self.assertAlmostEqual((high[1] - (start + end) / 2 / printing.height * (high[1] - low[1])) / diameter, center, delta=.01)
        svg = ET.parse(SOURCE / 'print.svg').getroot()
        self.assertEqual([e.text for e in svg.iter() if e.tag.endswith('}text')], ['COASTAL', 'PERFUME', '50 ml'])
        paths = [e for e in svg.iter() if e.tag.endswith('}path')]
        self.assertEqual(len(paths), 2)
        approved = ET.parse(CLIENT / 'model-source/collection/poster-039/print.svg').getroot()
        self.assertEqual(paths[0].get('d'), next(e.get('d') for e in approved.iter() if e.tag.endswith('}path')))
        self.assertEqual(paths[1].get('fill'), 'none')
        self.assertIn('stroke', paths[1].attrib)


if __name__ == '__main__':
    unittest.main()
