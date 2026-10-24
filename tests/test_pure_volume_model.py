"""Validate the individual Pure Volume model from exported geometry and embedded artwork."""
import io
import json
import math
from pathlib import Path
import struct
import unittest
import xml.etree.ElementTree as ET

from PIL import Image, ImageChops, ImageStat

CLIENT = Path(__file__).resolve().parents[1] / 'docs/client-motion-demo'
SOURCE = CLIENT / 'model-source/collection/poster-051'
BODY = 'Hollow ivory pouch body with soft gathered folds'
FILM = 'Illustrative transparent curved label carrier'
PRINT = 'Complete Pure Volume green lettering'
LEVER = 'Left curved flattened dispensing lever'


class PureVolumeModelTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        raw = (CLIENT / 'packaging-assets/poster-051.glb').read_bytes()
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

    def mesh_names(self, group=None):
        return [n['name'] for n in self.nodes if 'mesh' in n and (group is None or self.ancestor(n['name']) == group)]

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

    def body_width(self):
        low, high = self.bounds(self.positions(BODY))
        return high[0] - low[0]

    def material(self, name):
        return self.gltf['materials'][self.primitive(name)['material']]

    def image(self, name):
        texture = self.material(name)['pbrMetallicRoughness']['baseColorTexture']['index']
        image = self.gltf['images'][self.gltf['textures'][texture]['source']]
        view = self.gltf['bufferViews'][image['bufferView']]
        offset = view.get('byteOffset', 0)
        return Image.open(io.BytesIO(self.binary[offset:offset + view['byteLength']])).convert('RGBA')

    def test_seven_independent_packaging_groups_without_formula_or_duplicate_artwork(self):
        roots = self.gltf['scenes'][self.gltf.get('scene', 0)]['nodes']
        self.assertEqual({self.nodes[i]['name'] for i in roots},
                         {'Body', 'Closure', 'PumpStem', 'Actuator', 'Cord', 'PaperLabel', 'LogoPrint'})
        self.assertEqual(self.mesh_names('Body'), [BODY])
        self.assertEqual(self.mesh_names('PaperLabel'), [FILM])
        self.assertEqual(self.mesh_names('LogoPrint'), [PRINT])
        self.assertEqual(len(self.mesh_names('Closure')), 3)
        self.assertEqual(len(self.mesh_names('PumpStem')), 1)
        self.assertEqual(len(self.mesh_names('Actuator')), 3)
        self.assertEqual(len(self.mesh_names('Cord')), 47)
        self.assertEqual(len(self.mesh_names()), 57)
        self.assertTrue(all('uri' not in item for item in self.gltf['images'] + self.gltf['buffers']))
        self.assertFalse(self.gltf.get('animations'))
        self.assertFalse(self.gltf.get('cameras'))
        info = json.loads((SOURCE / 'model-info.json').read_text())
        self.assertFalse(info['containsFormula'])
        self.assertTrue(info['illustrativeDimensions'])
        self.assertTrue((SOURCE / 'poster-051.blend').is_file())

    def test_actual_wide_body_ratio_pinched_neck_and_rounded_base(self):
        width = self.body_width()
        points = self.positions(BODY)
        low, high = self.bounds(points)
        all_low, all_high = self.bounds([p for name in self.mesh_names() for p in self.positions(name)])
        self.assertAlmostEqual((all_high[1] - all_low[1]) / width, 1.68, delta=.04,
                               msg='Photographic tilt must not become an excessively tall upright bottle.')
        self.assertAlmostEqual((high[2] - low[2]) / width, .48, delta=.025)
        self.assertAlmostEqual((high[1] - low[1]) / width, 1.188, delta=.02)
        for level, expected_width, tolerance in [(0, .79, .02), (.25, 1, .015), (.65, .72, .03),
                                                  (.92, .35, .08), (1.10, .47, .06)]:
            xs = [p[0] for p in points if abs(p[1] / width - level) < .006]
            self.assertAlmostEqual((max(xs) - min(xs)) / width, expected_width, delta=tolerance)
        # The real mesh must close both the outside foot and the interior floor at the axis.
        indices = [i for item in self.accessor(self.primitive(BODY)['indices']) for i in item]
        for floor in [0, .06]:
            axis = {i for i, (x, y, z) in enumerate(points)
                    if math.hypot(x, z) < 1e-6 and abs(y / width - floor) < 1e-6}
            self.assertTrue(axis)
            self.assertGreaterEqual(sum(i in axis for i in indices), 3)

    def test_ivory_body_and_pump_are_opaque_matte_polymer_with_only_one_gold_line(self):
        for name in self.mesh_names():
            material = self.material(name)
            self.assertEqual(material.get('extensions', {}).get('KHR_materials_transmission', {}).get('transmissionFactor', 0), 0)
        body = self.material(BODY)
        pbr = body['pbrMetallicRoughness']
        rgb = pbr['baseColorFactor'][:3]
        self.assertTrue(.4 <= pbr['roughnessFactor'] <= .65)
        self.assertTrue(rgb[0] >= rgb[1] >= rgb[2] > .65)
        self.assertEqual(pbr.get('metallicFactor', 1), 0)
        self.assertEqual(body.get('alphaMode', 'OPAQUE'), 'OPAQUE')
        self.assertNotIn('Texture', json.dumps(body), 'No product name may remain on the body when printing opens.')
        pump = self.material('Broad ivory screw closure')['pbrMetallicRoughness']
        self.assertTrue(.2 <= pump['roughnessFactor'] <= .4)
        self.assertEqual(pump.get('metallicFactor', 1), 0)
        metallic = [n for n in self.mesh_names() if self.material(n)['pbrMetallicRoughness'].get('metallicFactor', 1) > .9]
        self.assertEqual(metallic, ['Single fine gold closure line'])
        low, high = self.bounds(self.positions(metallic[0]))
        width = self.body_width()
        self.assertTrue(.003 <= (high[1] - low[1]) / width <= .012, 'The gold detail is a fine line, not a broad collar.')
        self.assertAlmostEqual((high[0] - low[0]) / width, .33, delta=.015)

    def test_pump_retains_the_broad_flat_curved_lever_and_separate_stem(self):
        width = self.body_width()
        low, high = self.bounds(self.positions('Broad ivory screw closure'))
        self.assertAlmostEqual((high[0] - low[0]) / width, .364, delta=.01)
        self.assertAlmostEqual((high[1] - low[1]) / width, .297, delta=.015)
        points = self.positions(LEVER)
        low, high = self.bounds(points)
        self.assertAlmostEqual((high[0] - low[0]) / width, .554, delta=.02)
        self.assertLess(low[0] / width, -.38)
        self.assertGreater(high[0] / width, .14)
        for x_level in [-.255, .055]:
            section = [p for p in points if abs(p[0] / width - x_level) < 1e-5]
            section_low, section_high = self.bounds(section)
            self.assertGreater((section_high[2] - section_low[2]) / (section_high[1] - section_low[1]), 1.8,
                               'The broad lever must not regress to the old cylindrical spout.')
        left_y = [p[1] for p in points if abs(p[0] - low[0]) < 1e-6]
        center_y = [p[1] for p in points if abs(p[0] / width - .055) < 1e-5]
        self.assertGreater((sum(left_y) / len(left_y) - sum(center_y) / len(center_y)) / width, .07)
        self.assertEqual(self.ancestor('Independent ivory pump stem'), 'PumpStem')
        outlet_low, outlet_high = self.bounds(self.positions('Recessed flattened outlet'))
        self.assertGreater(outlet_low[0], low[0], 'The dark outlet must be recessed inside the open nozzle.')
        self.assertLess((outlet_high[1] - outlet_low[1]) / width, .04)

    def test_braided_cord_has_two_wraps_crossing_strands_knot_and_unequal_finished_tails(self):
        width = self.body_width()
        braid_names = ['Neck cord loop 1', 'Neck cord loop 2', 'Right hand tying knot', 'Short hanging tail', 'Long hanging tail']
        for prefix in braid_names:
            core = prefix + ' inner rope core'
            self.assertEqual(self.ancestor(core), 'Cord')
            strands = [n for n in self.mesh_names('Cord') if n.startswith(prefix + ' woven')]
            self.assertEqual(len(strands), 8)
            self.assertEqual(len({tuple(self.positions(n)) for n in strands}), 8,
                             'Eight renamed copies of one curve are not a braid.')
            for strand in strands:
                self.assertGreater(len(self.positions(strand)), 100)
            for direction in [-1, 1]:
                self.assertEqual(sum(f'woven {direction} strand' in n for n in strands), 4)
        centers = []
        for suffix in [1, 2]:
            low, high = self.bounds(self.positions(f'Neck cord loop {suffix} inner rope core'))
            centers.append((low[1] + high[1]) / 2)
            self.assertAlmostEqual((high[0] - low[0]) / width, .397, delta=.015)
        self.assertTrue(.025 < (centers[1] - centers[0]) / width < .06)
        end_centers = {}
        for length in ['short', 'long']:
            low, high = self.bounds(self.positions(f'Green rounded {length} cord end'))
            for axis in range(3):
                self.assertAlmostEqual((high[axis] - low[axis]) / width, .046, delta=.005)
            center = tuple((low[i] + high[i]) / 2 for i in range(3))
            end_centers[length] = center
            core = self.positions(length.capitalize() + ' hanging tail inner rope core')
            self.assertLess(min(math.dist(center, p) for p in core) / width, .012)
        self.assertGreater((end_centers['short'][1] - end_centers['long'][1]) / width, .12)
        for name in self.mesh_names('Cord'):
            pbr = self.material(name)['pbrMetallicRoughness']
            r, g, b = pbr['baseColorFactor'][:3]
            self.assertTrue(g > b > r and g < .12)
            self.assertEqual(pbr.get('metallicFactor', 1), 0)

    def test_transparent_carrier_and_complete_green_print_have_no_white_paper_or_missing_copy(self):
        textured = [n for n in self.mesh_names() if 'baseColorTexture' in self.material(n)['pbrMetallicRoughness']]
        self.assertEqual(set(textured), {FILM, PRINT})
        film, printing = self.image(FILM), self.image(PRINT)
        for name, image, filename in [(FILM, film, 'label.png'), (PRINT, printing, 'print.png')]:
            self.assertEqual(self.material(name)['alphaMode'], 'BLEND')
            with Image.open(SOURCE / filename) as source:
                self.assertEqual(image.size, source.size)
                self.assertIsNone(ImageChops.difference(image, source.convert('RGBA')).getbbox(alpha_only=False))
        self.assertLess(film.getchannel('A').getextrema()[1], 180, 'The clear carrier must never become an opaque white paper label.')
        self.assertLess(ImageStat.Stat(film.getchannel('A')).mean[0], 60)
        visible = film.getchannel('A').point(lambda a: 255 if a > 8 else 0)
        self.assertGreater(min(low for low, high in ImageStat.Stat(film.convert('RGB'), visible).extrema), 90,
                           'The carrier must be blank, without duplicate green wording.')
        alpha = printing.getchannel('A').point(lambda a: 255 if a > 32 else 0)
        r, g, b = ImageStat.Stat(printing.convert('RGB'), alpha).mean
        self.assertTrue(g > b > r and g < 100)
        rows = [bool(alpha.crop((0, y, alpha.width, y + 1)).getbbox()) for y in range(alpha.height)]
        starts = [i for i, filled in enumerate(rows) if filled and (i == 0 or not rows[i - 1])]
        self.assertEqual(len(starts), 3, 'Logo, PURE VOLUME and SHAMPOO must all be embedded in the movable print.')
        self.assertTrue(starts[0] < alpha.height * .15 and .65 < starts[1] / alpha.height < .75
                        and .80 < starts[2] / alpha.height < .90)
        svg = ET.parse(SOURCE / 'print.svg').getroot()
        self.assertEqual([e.text for e in svg.iter() if e.tag.endswith('}text')], ['PURE VOLUME', 'SHAMPOO'])
        approved = ET.parse(CLIENT / 'model-source/collection/poster-039/print.svg').getroot()
        self.assertEqual([e.get('d') for e in svg.iter() if e.tag.endswith('}path')],
                         [e.get('d') for e in approved.iter() if e.tag.endswith('}path')])
        self.assertFalse(any(e.tag.endswith(('}text', '}path')) for e in ET.parse(SOURCE / 'label.svg').getroot().iter()))

    def test_closed_film_and_print_follow_the_actual_front_surface(self):
        width = self.body_width()
        film, printing = self.positions(FILM), self.positions(PRINT)
        self.assertEqual(len(film), len(printing))
        low, high = self.bounds(film)
        self.assertGreater((high[2] - low[2]) / width, .02, 'The artwork must follow a curved surface rather than float as a flat rectangle.')
        for a, b in zip(film, printing):
            self.assertAlmostEqual(a[0], b[0], places=6)
            self.assertAlmostEqual(a[1], b[1], places=6)
            self.assertTrue(.0002 < (b[2] - a[2]) / width < .002)
        body = self.positions(BODY)
        indices = [item[0] for item in self.accessor(self.primitive(BODY)['indices'])]
        triangles = [tuple(body[j] for j in indices[i:i + 3]) for i in range(0, len(indices), 3)]
        # Intersect the actual exported body triangles, so a matching generator formula cannot hide bad alignment.
        for x_fraction in [-.25, 0, .25]:
            for y_fraction in [.12, .32, .52]:
                point = min(film, key=lambda p: (p[0] / width - x_fraction) ** 2 + (p[1] / width - y_fraction) ** 2)
                x, y, z = point
                surfaces = []
                for a, b, c in triangles:
                    if not (min(a[0], b[0], c[0]) - 1e-7 <= x <= max(a[0], b[0], c[0]) + 1e-7
                            and min(a[1], b[1], c[1]) - 1e-7 <= y <= max(a[1], b[1], c[1]) + 1e-7):
                        continue
                    det = (b[1] - c[1]) * (a[0] - c[0]) + (c[0] - b[0]) * (a[1] - c[1])
                    if abs(det) < 1e-12:
                        continue
                    u = ((b[1] - c[1]) * (x - c[0]) + (c[0] - b[0]) * (y - c[1])) / det
                    v = ((c[1] - a[1]) * (x - c[0]) + (a[0] - c[0]) * (y - c[1])) / det
                    if min(u, v, 1 - u - v) >= -1e-5:
                        surfaces.append(u * a[2] + v * b[2] + (1 - u - v) * c[2])
                self.assertTrue(surfaces)
                gap = (z - max(surfaces)) / width
                self.assertTrue(.0003 < gap < .004, f'Carrier must lie just above the actual bottle surface: gap/D={gap}')


if __name__ == '__main__':
    unittest.main()
