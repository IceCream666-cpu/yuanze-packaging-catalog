"""Inspect Woodland 042's exported geometry and artwork, not generator metadata alone."""
import io
import json
import math
from pathlib import Path
import struct
import unittest
import xml.etree.ElementTree as ET

from PIL import Image, ImageChops, ImageStat

CLIENT = Path(__file__).resolve().parents[1] / 'docs/client-motion-demo'
SOURCE = CLIENT / 'model-source/collection/poster-042'
BODY = 'Hollow amber bevelled square bottle'
MOUTH = 'Clear thick flared mouth ring'
CAP = 'Hollow glossy black spherical closure'
PAPER = 'Black woodgrain label substrate'
PRINT = 'Complete Woodland lettering'


class WoodlandModelTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        raw = (CLIENT / 'packaging-assets/poster-042.glb').read_bytes()
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

    def ancestor(self, index):
        while index in self.parents:
            index = self.parents[index]
        return self.nodes[index]['name']

    def primitive(self, name):
        primitive, = self.gltf['meshes'][self.nodes[self.named[name]]['mesh']]['primitives']
        return primitive

    def accessor(self, index):
        accessor = self.gltf['accessors'][index]
        self.assertNotIn('sparse', accessor)
        view = self.gltf['bufferViews'][accessor['bufferView']]
        fmt = {5121: 'B', 5123: 'H', 5125: 'I', 5126: 'f'}[accessor['componentType']]
        count = {'SCALAR': 1, 'VEC2': 2, 'VEC3': 3}[accessor['type']]
        fmt = '<' + fmt * count
        offset = view.get('byteOffset', 0) + accessor.get('byteOffset', 0)
        stride = view.get('byteStride', struct.calcsize(fmt))
        return [struct.unpack_from(fmt, self.binary, offset + i * stride) for i in range(accessor['count'])]

    def positions(self, name):
        points = self.accessor(self.primitive(name)['attributes']['POSITION'])
        index = self.named[name]
        # Include every parent transform so pivot changes cannot silently alter the closed silhouette.
        while True:
            node = self.nodes[index]
            self.assertNotIn('matrix', node)
            self.assertEqual(node.get('rotation', [0, 0, 0, 1]), [0, 0, 0, 1])
            scale = node.get('scale', [1, 1, 1])
            translation = node.get('translation', [0, 0, 0])
            points = [tuple(p[j] * scale[j] + translation[j] for j in range(3)) for p in points]
            if index not in self.parents:
                return points
            index = self.parents[index]

    @staticmethod
    def bounds(points):
        return ([min(p[j] for p in points) for j in range(3)],
                [max(p[j] for p in points) for j in range(3)])

    def material(self, name):
        return self.gltf['materials'][self.primitive(name)['material']]

    def image(self, name):
        texture = self.material(name)['pbrMetallicRoughness']['baseColorTexture']['index']
        image = self.gltf['images'][self.gltf['textures'][texture]['source']]
        view = self.gltf['bufferViews'][image['bufferView']]
        offset = view.get('byteOffset', 0)
        return Image.open(io.BytesIO(self.binary[offset:offset + view['byteLength']])).convert('RGBA')

    def body_width(self):
        low, high = self.bounds(self.positions(BODY))
        return high[0] - low[0]

    def test_five_independent_groups_with_only_the_eight_packaging_meshes(self):
        expected = {
            'Body': {BODY, MOUTH},
            'Closure': {CAP, 'Black closure seating rim'},
            'StopperInsert': {'Illustrative removable sealing sleeve', 'Illustrative stopper seating ribs'},
            'PaperLabel': {PAPER},
            'LogoPrint': {PRINT},
        }
        roots = self.gltf['scenes'][self.gltf.get('scene', 0)]['nodes']
        self.assertEqual({self.nodes[i]['name'] for i in roots}, set(expected))
        meshes = [i for i, node in enumerate(self.nodes) if 'mesh' in node]
        self.assertEqual(len(meshes), 8, 'No extra formula, duplicated artwork or old bottle mesh may remain.')
        for group, names in expected.items():
            self.assertEqual({self.nodes[i]['name'] for i in meshes if self.ancestor(i) == group}, names)
        self.assertTrue(all('uri' not in item for item in self.gltf['images'] + self.gltf['buffers']))
        self.assertFalse(self.gltf.get('animations'))
        self.assertFalse(self.gltf.get('cameras'))
        self.assertTrue((SOURCE / 'poster-042.blend').is_file())
        info = json.loads((SOURCE / 'model-info.json').read_text())
        self.assertFalse(info['containsFormula'])
        self.assertTrue(info['illustrativeDimensions'])
        self.assertIn('illustrative', info['hiddenStructure'])

    def test_reference_silhouette_has_a_bevelled_rectangular_body(self):
        points = self.positions(BODY)
        low, high = self.bounds(points)
        width = self.body_width()
        self.assertAlmostEqual((high[2] - low[2]) / width, .70, delta=.01)
        all_points = [p for node in self.nodes if 'mesh' in node for p in self.positions(node['name'])]
        all_low, all_high = self.bounds(all_points)
        self.assertAlmostEqual((all_high[1] - all_low[1]) / width, 2.27, delta=.025)
        # Front corners joined by a broad flat face distinguish the bottle from an oval cylinder.
        for level in [.13, 1.37]:
            front = [p[0] for p in points if abs(p[1] / width - level) < 1e-5
                     and abs(p[2] / width - .35) < 1e-5]
            self.assertGreaterEqual(len(front), 2)
            self.assertGreater((max(front) - min(front)) / width, .88)
        lower = [p[0] for p in points if abs(p[1] / width - .008) < 1e-5]
        self.assertAlmostEqual((max(lower) - min(lower)) / width, .82, delta=.01,
                               msg='The bottom must round inward rather than end as a sharp box.')

    def test_hollow_body_has_an_open_neck_and_connected_inner_and_outer_floors(self):
        width = self.body_width()
        points = self.positions(BODY)
        top = max(p[1] for p in points)
        mouth = [math.hypot(x, z) / width for x, y, z in points if abs(y - top) < 1e-6]
        self.assertAlmostEqual(min(mouth), .155, delta=.002)
        self.assertAlmostEqual(max(mouth), .231, delta=.002)
        indices = [i for item in self.accessor(self.primitive(BODY)['indices']) for i in item]
        for floor in [0, .098]:
            axis = {i for i, (x, y, z) in enumerate(points)
                    if math.hypot(x, z) < 1e-6 and abs(y / width - floor) < 1e-6}
            self.assertTrue(axis, 'Both the bottom and cavity floor must be sealed at their axes.')
            self.assertGreaterEqual(sum(i in axis for i in indices), 3,
                                    'A loose axis vertex is not a closing face.')

    def test_cap_is_a_truncated_sphere_above_a_wider_open_clear_lip(self):
        width = self.body_width()
        points = self.positions(CAP)
        low, high = self.bounds(points)
        self.assertAlmostEqual((high[0] - low[0]) / width, .51, delta=.005)
        self.assertAlmostEqual((high[1] - low[1]) / width, .42, delta=.005)
        base = [math.hypot(x, z) / width for x, y, z in points if abs(y - low[1]) < 1e-6]
        self.assertAlmostEqual(max(base), math.sqrt(.255 ** 2 - .165 ** 2), delta=.002)
        self.assertGreater(min(base), .14, 'The underside must retain its hollow seating aperture.')
        outer_top = [math.sqrt((x / width) ** 2 + (y / width - 2.015) ** 2 + (z / width) ** 2)
                     for x, y, z in points if y / width >= 2.015]
        shell = [radius for radius in outer_top if radius > .24]
        self.assertGreater(len(shell), 64)
        self.assertLess(max(abs(radius - .255) for radius in shell), .0001,
                        'A cap with matching bounds must still retain the spherical surface.')
        mouth = self.positions(MOUTH)
        rim_low, rim_high = self.bounds(mouth)
        self.assertAlmostEqual((rim_high[0] - rim_low[0]) / width, .564, delta=.005)
        self.assertGreater(rim_high[0] - rim_low[0], high[0] - low[0])
        self.assertAlmostEqual(min(math.hypot(x, z) for x, y, z in mouth) / width, .15, delta=.002)
        self.assertTrue(rim_low[1] < low[1] < rim_high[1], 'The spherical cap must seat into the clear lip.')

    def test_amber_glass_clear_lip_and_polished_nonmetal_black_cap(self):
        for name in [BODY, MOUTH]:
            material = self.material(name)
            pbr = material['pbrMetallicRoughness']
            extensions = material['extensions']
            self.assertEqual(pbr.get('metallicFactor', 1), 0)
            self.assertGreaterEqual(extensions['KHR_materials_transmission']['transmissionFactor'], .98)
            self.assertLessEqual(pbr['roughnessFactor'], .05)
            self.assertAlmostEqual(extensions['KHR_materials_ior']['ior'], 1.49, delta=.02)
        amber = self.material(BODY)['pbrMetallicRoughness']['baseColorFactor']
        self.assertTrue(amber[0] > .8 and .25 < amber[1] < .45 and .02 < amber[2] < .10)
        clear = self.material(MOUTH)['pbrMetallicRoughness'].get('baseColorFactor', [1, 1, 1, 1])
        self.assertGreaterEqual(min(clear[:3]), .98)
        cap = self.material(CAP)
        pbr = cap['pbrMetallicRoughness']
        self.assertEqual(pbr.get('metallicFactor', 1), 0)
        self.assertLess(max(pbr['baseColorFactor'][:3]), .01)
        self.assertTrue(.04 <= pbr['roughnessFactor'] <= .10)
        self.assertGreaterEqual(cap['extensions']['KHR_materials_clearcoat']['clearcoatFactor'], .2)

    def test_paper_and_complete_print_share_the_closed_layout_without_body_textures(self):
        textured = []
        for node in self.nodes:
            if 'mesh' not in node:
                continue
            material = self.material(node['name'])
            if 'baseColorTexture' in material['pbrMetallicRoughness']:
                textured.append(node['name'])
            if self.ancestor(self.named[node['name']]) == 'Body':
                self.assertNotIn('Texture', json.dumps(material), 'No printing may stay on the bottle after unfolding.')
        self.assertEqual(set(textured), {PAPER, PRINT})
        width = self.body_width()
        paper_low, paper_high = self.bounds(self.positions(PAPER))
        print_low, print_high = self.bounds(self.positions(PRINT))
        for axis in [0, 1]:
            self.assertAlmostEqual(paper_low[axis], print_low[axis], places=6)
            self.assertAlmostEqual(paper_high[axis], print_high[axis], places=6)
        self.assertAlmostEqual((paper_high[0] - paper_low[0]) / width, .61, delta=.01)
        self.assertAlmostEqual((paper_high[1] - paper_low[1]) / width, 1.21, delta=.01)
        self.assertAlmostEqual(paper_low[1] / width, .14, delta=.005)
        self.assertTrue(0 < (print_low[2] - paper_low[2]) / width < .002,
                        'Closed printing must sit just in front of its separate paper, without z-fighting.')
        self.assertGreater(paper_low[2], self.bounds(self.positions(BODY))[1][2])
        for name in [PAPER, PRINT]:
            self.assertEqual(self.material(name)['alphaMode'], 'BLEND')
            uv = self.accessor(self.primitive(name)['attributes']['TEXCOORD_0'])
            self.assertEqual(set(uv), {(0, 0), (1, 0), (1, 1), (0, 1)})

    def test_embedded_artwork_has_a_text_free_wood_label_and_four_print_bands(self):
        paper, printing = self.image(PAPER), self.image(PRINT)
        for image, filename in [(paper, 'label.png'), (printing, 'print.png')]:
            with Image.open(SOURCE / filename) as source:
                self.assertEqual(image.size, source.size)
                self.assertIsNone(ImageChops.difference(image, source.convert('RGBA')).getbbox(alpha_only=False),
                                  'Exported artwork must match the editable source raster.')
        paper_mask = paper.getchannel('A').point(lambda value: 255 if value > 32 else 0)
        self.assertLess(max(high for low, high in ImageStat.Stat(paper.convert('RGB'), paper_mask).extrema), 100,
                        'The wood background must not carry duplicate ivory lettering.')
        self.assertGreater(ImageStat.Stat(paper.convert('L')).stddev[0], 3, 'Retain visible wood grain.')
        alpha = printing.getchannel('A').point(lambda value: 255 if value > 32 else 0)
        rows = [bool(alpha.crop((0, y, alpha.width, y + 1)).getbbox()) for y in range(alpha.height)]
        starts = [i for i, filled in enumerate(rows) if filled and (i == 0 or not rows[i - 1])]
        ends = [i + 1 for i, filled in enumerate(rows) if filled and (i + 1 == len(rows) or not rows[i + 1])]
        self.assertEqual(len(starts), 4, 'The logo and all three copy lines must be present in the moving print.')
        for start, end, expected in zip(starts, ends, [(.20, .33), (.73, .79), (.81, .86), (.89, .94)]):
            self.assertTrue(expected[0] <= start / alpha.height < end / alpha.height <= expected[1])
        self.assertEqual(printing.getchannel('A').getextrema(), (0, 255))
        self.assertGreater(min(ImageStat.Stat(printing.convert('RGB'), alpha).mean), 210)
        svg = ET.parse(SOURCE / 'print.svg').getroot()
        self.assertEqual([element.text for element in svg.iter() if element.tag.endswith('}text')],
                         ['WOODLAND', 'BODY WASH', '350 ml'])
        approved = ET.parse(CLIENT / 'model-source/collection/poster-039/print.svg').getroot()
        self.assertEqual([e.get('d') for e in svg.iter() if e.tag.endswith('}path')],
                         [e.get('d') for e in approved.iter() if e.tag.endswith('}path')],
                         'The moving wordmark must retain the approved liaose logo.')
        label = ET.parse(SOURCE / 'label.svg').getroot()
        self.assertFalse(any(e.tag.endswith(('}text', '}path')) for e in label.iter()))


if __name__ == '__main__':
    unittest.main()
