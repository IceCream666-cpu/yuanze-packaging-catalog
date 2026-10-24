"""Inspect Golden Face Oil 056's actual empty shell, cover clearance and artwork."""
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
SOURCE = CLIENT / 'model-source/collection/poster-056'
BODY = 'Hollow rounded rectangular bottle with thick clear base'
COLLAR = 'Olive stepped pump collar'
STEM = 'Short illustrative connecting stem'
HEAD = 'Tall cylindrical press actuator'
INSET = 'Subtle actuator top inset'
COVER = 'Hollow olive cover with long rounded front skirt'
FILM = 'Transparent unprinted film carrier'
PRINT = 'Complete Golden Face Oil lettering'


class GoldenFaceOilModelTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        raw = (CLIENT / 'packaging-assets/poster-056.glb').read_bytes()
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

    def width(self):
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

    def assert_connected_axis(self, name, level):
        width = self.width()
        axis = {i for i, (x, y, z) in enumerate(self.positions(name))
                if math.hypot(x, z) < 1e-6 and abs(y / width - level) < 1e-5}
        self.assertTrue(axis, f'{name} must be sealed at {level}W')
        indices = [item[0] for item in self.accessor(self.primitive(name)['indices'])]
        self.assertGreaterEqual(sum(i in axis for i in indices), 3, 'A loose axis vertex is not a closing face.')

    def vertical_intersections(self, name, x=0, z=0):
        points = self.positions(name)
        indices = [item[0] for item in self.accessor(self.primitive(name)['indices'])]
        heights = []
        for i in range(0, len(indices), 3):
            a, b, c = [points[j] for j in indices[i:i + 3]]
            denominator = (b[2] - c[2]) * (a[0] - c[0]) + (c[0] - b[0]) * (a[2] - c[2])
            if abs(denominator) < 1e-12:
                continue
            u = ((b[2] - c[2]) * (x - c[0]) + (c[0] - b[0]) * (z - c[2])) / denominator
            v = ((c[2] - a[2]) * (x - c[0]) + (a[0] - c[0]) * (z - c[2])) / denominator
            if min(u, v, 1 - u - v) >= -1e-7:
                heights.append(u * a[1] + v * b[1] + (1 - u - v) * c[1])
        return heights

    def test_seven_independent_groups_have_only_the_reference_packaging_parts(self):
        expected = {'Body': {BODY}, 'Closure': {COLLAR}, 'PumpStem': {STEM}, 'Actuator': {HEAD, INSET},
                    'Overcap': {COVER}, 'PaperLabel': {FILM}, 'LogoPrint': {PRINT}}
        roots = self.gltf['scenes'][self.gltf.get('scene', 0)]['nodes']
        self.assertEqual({self.nodes[i]['name'] for i in roots}, set(expected))
        self.assertEqual(len(self.mesh_names()), 8, 'No formula, long nozzle, dropper or duplicate label may remain.')
        for group, names in expected.items():
            self.assertEqual({n for n in self.mesh_names() if self.ancestor(n) == group}, names)
        self.assertTrue(all('uri' not in item for item in self.gltf['images'] + self.gltf['buffers']))
        self.assertFalse(self.gltf.get('animations'))
        self.assertFalse(self.gltf.get('cameras'))
        info = json.loads((SOURCE / 'model-info.json').read_text())
        self.assertTrue(info['illustrativeDimensions'])
        self.assertFalse(info['containsFormula'])
        self.assertTrue((SOURCE / 'poster-056.blend').is_file())

    def test_deprojected_silhouette_retains_the_wide_flat_bottle_and_long_u_cover(self):
        width = self.width()
        low, high = self.bounds([p for n in self.mesh_names() for p in self.positions(n)])
        # The physical cover bevel adds a small miter envelope to the nominal display height.
        self.assertAlmostEqual(high[1] - low[1], 2.9, delta=.008)
        self.assertAlmostEqual((high[1] - low[1]) / width, 1.41, delta=.015)
        body_low, body_high = self.bounds(self.positions(BODY))
        self.assertAlmostEqual(body_high[1] / width, .92, delta=.005)
        self.assertAlmostEqual((body_high[2] - body_low[2]) / width, .34, delta=.005)
        front = [x / width for x, y, z in self.positions(BODY)
                 if abs(y / width - .838) < 1e-5 and abs(z / width - .17) < 1e-5]
        self.assertGreater(max(front) - min(front), .90, 'The broad flat face must not become an oval bottle.')
        cover_low, cover_high = self.bounds(self.positions(COVER))
        self.assertAlmostEqual((cover_high[0] - cover_low[0]) / width, .62, delta=.005)
        self.assertAlmostEqual((cover_high[2] - cover_low[2]) / width, .42, delta=.005)
        self.assertAlmostEqual(cover_low[1] / width, .50, delta=.003)
        corners = [(abs(x) / width, y / width) for x, y, z in self.positions(COVER)
                   if y / width < .60 and abs(x) / width > .22]
        self.assertGreater(len(corners), 20)
        self.assertLess(max(abs(math.hypot(x - .20, y - .61) - .11) for x, y in corners), .004,
                        'The lower front corners must keep their broad U curve.')

    def test_exported_cover_has_a_real_edge_bevel_instead_of_a_clamped_hard_corner(self):
        width = self.width()
        points = self.positions(COVER)
        indices = [item[0] for item in self.accessor(self.primitive(COVER)['indices'])]
        level = .75 * width
        section = set()
        # Slice the actual triangles through a straight part of the front skirt, below the short walls.
        for i in range(0, len(indices), 3):
            triangle = [points[j] for j in indices[i:i + 3]]
            for a, b in zip(triangle, triangle[1:] + triangle[:1]):
                if (a[1] - level) * (b[1] - level) < 0:
                    fraction = (level - a[1]) / (b[1] - a[1])
                    section.add(tuple(round((a[axis] + fraction * (b[axis] - a[axis])) / width, 8)
                                      for axis in [0, 2]))
        self.assertTrue(section)
        side = max(x for x, z in section)
        front = max(z for x, z in section)
        front_end = max(x for x, z in section if abs(z - front) < 1e-6)
        side_end = max(z for x, z in section if abs(x - side) < 1e-6)
        self.assertAlmostEqual(side - front_end, .0025, delta=.0005)
        self.assertAlmostEqual(front - side_end, .0025, delta=.0005)
        arc = [(x, z) for x, z in section if front_end + .0001 < x < side - .0001
               and side_end + .0001 < z < front - .0001]
        self.assertGreaterEqual(len(arc), 3, 'A real multi-segment bevel must remain after Boolean cleanup and export.')
        for x, z in arc:
            self.assertAlmostEqual(math.hypot(x - front_end, z - side_end), .0025, delta=.00015)

    def test_glass_is_hollow_with_an_open_round_neck_and_a_sealed_thick_floor(self):
        width = self.width()
        points = self.positions(BODY)
        mouth = [math.hypot(x, z) / width for x, y, z in points if abs(y / width - .920) < 1e-5]
        self.assertAlmostEqual(min(mouth), .091, delta=.002)
        self.assertAlmostEqual(max(mouth), .125, delta=.002)
        self.assert_connected_axis(BODY, 0)
        self.assert_connected_axis(BODY, .140)
        self.assertFalse(any(y / width > .141 and math.hypot(x, z) < 1e-6 for x, y, z in points))
        inner_front = [z / width for x, y, z in points if abs(y / width - .819) < 1e-5]
        self.assertAlmostEqual(max(inner_front), .138, delta=.002)
        heights = self.vertical_intersections(BODY)
        self.assertAlmostEqual(min(heights) / width, 0, delta=1e-5)
        self.assertAlmostEqual(max(heights) / width, .140, delta=1e-5,
                               msg='The central ray must see the inner floor, not a liquid or closed bottle mouth.')
        welded = [tuple(round(v / width, 6) for v in p) for p in points]
        indices = [item[0] for item in self.accessor(self.primitive(BODY)['indices'])]
        edges = Counter()
        for i in range(0, len(indices), 3):
            a, b, c = [welded[j] for j in indices[i:i + 3]]
            self.assertEqual(len({a, b, c}), 3)
            edges.update(tuple(sorted(pair)) for pair in [(a, b), (b, c), (c, a)])
        self.assertEqual(set(edges.values()), {2}, 'The exported inner and outer glass surfaces must have no open seam.')

    def test_cover_skirt_and_short_walls_clear_the_glass_during_the_upward_sweep(self):
        width = self.width()
        body_low, body_high = self.bounds(self.positions(BODY))
        cover = self.positions(COVER)
        skirt = [p for p in cover if p[1] < body_high[1]]
        self.assertTrue(skirt)
        self.assertGreaterEqual(min(p[2] for p in skirt) - body_high[2], .014 * width,
                                'The long front sheet must sit outside the glass, not inside it.')
        # All vertices outside that front sheet are above the shoulder; positive Y movement preserves this separation.
        short_walls = [p for p in cover if p[2] <= body_high[2] + .01 * width]
        self.assertGreater(min(p[1] for p in short_walls) - body_high[1], .038 * width)
        film_top = self.bounds(self.positions(FILM))[1][1]
        self.assertGreater(min(p[1] for p in cover) - film_top, .020 * width,
                           'The closed U skirt must not cover the artwork area.')
        for progress in [0, .01, .04, .1, .5, 1]:
            u = min(progress / .65, 1)
            lift = 4.85 * u * u * (3 - 2 * u)
            self.assertGreater(min(p[1] + lift for p in short_walls), body_high[1])

    def test_pump_clears_the_cover_roof_even_during_the_initial_smooth_acceleration(self):
        width = self.width()
        inside = [p for name in [COLLAR, STEM, HEAD, INSET] for p in self.positions(name)]
        low, high = self.bounds(inside)
        self.assertLess(max(abs(low[0]), abs(high[0])) / width, .16)
        self.assertLess(max(abs(low[2]), abs(high[2])) / width, .16)
        self.assertAlmostEqual(high[1] / width, 1.351, delta=.003)
        roof = self.vertical_intersections(COVER)
        self.assertTrue(roof, 'The clear hood must have a real closed roof over the actuator.')
        ceiling = min(roof)
        self.assertAlmostEqual(ceiling / width, 1.398, delta=.002)
        self.assertGreater(ceiling - high[1], .046 * width)
        # Use the actual roof and head bounds with the reviewed motion; endpoint checks alone miss the early minimum.
        gaps = []
        for step in range(501):
            progress = step / 500
            u = min(progress / .65, 1)
            cover_lift = 4.85 * u * u * (3 - 2 * u)
            gaps.append(ceiling + cover_lift - (high[1] + 2.6 * progress))
        self.assertGreater(min(gaps), .035, 'The pump must not penetrate the cover during smooth opening.')

    def test_clear_empty_glass_and_translucent_olive_parts_keep_distinct_materials(self):
        glass = self.material(BODY)
        pbr = glass['pbrMetallicRoughness']
        self.assertGreaterEqual(min(pbr.get('baseColorFactor', [1, 1, 1, 1])[:3]), .99)
        self.assertGreaterEqual(glass['extensions']['KHR_materials_transmission']['transmissionFactor'], .99)
        self.assertLessEqual(pbr['roughnessFactor'], .04)
        self.assertAlmostEqual(glass['extensions']['KHR_materials_ior']['ior'], 1.49, delta=.02)
        self.assertNotIn('Texture', json.dumps(glass), 'No yellow liquid or duplicate lettering may be baked into the body.')
        hood = self.material(COVER)
        hood_pbr = hood['pbrMetallicRoughness']
        red, green, blue = hood_pbr['baseColorFactor'][:3]
        self.assertTrue(0 < blue < red < green < .12, 'The hood must remain dark olive, distinct from neutral glass.')
        self.assertGreater(hood['extensions']['KHR_materials_transmission']['transmissionFactor'], .8)
        self.assertLess(hood_pbr['roughnessFactor'], .10)
        self.assertGreater(hood['extensions']['KHR_materials_clearcoat']['clearcoatFactor'], .2)
        for name in [COLLAR, STEM, HEAD, INSET]:
            material = self.material(name)
            self.assertEqual(material.get('extensions', {}).get('KHR_materials_transmission', {}).get('transmissionFactor', 0), 0,
                             'Internal parts must render in the transmission capture behind the olive cover.')
            self.assertEqual(material.get('alphaMode', 'OPAQUE'), 'OPAQUE')
        for name in self.mesh_names():
            self.assertEqual(self.material(name)['pbrMetallicRoughness'].get('metallicFactor', 1), 0)

    def test_transparent_carrier_is_blank_and_both_artwork_layers_sit_just_outside_the_flat_face(self):
        width = self.width()
        body_front = self.bounds(self.positions(BODY))[1][2]
        for name, gap in [(FILM, .0014), (PRINT, .0022)]:
            low, high = self.bounds(self.positions(name))
            self.assertAlmostEqual((high[0] - low[0]) / width, .62, delta=.002)
            self.assertAlmostEqual((high[1] - low[1]) / width, .35, delta=.002)
            self.assertAlmostEqual((high[1] + low[1]) / (2 * width), .30, delta=.002)
            self.assertAlmostEqual(low[2], high[2], places=6)
            self.assertAlmostEqual((low[2] - body_front) / width, gap, delta=1e-6)
            self.assertEqual(self.material(name)['alphaMode'], 'BLEND')
        textured = [n for n in self.mesh_names() if 'baseColorTexture' in self.material(n)['pbrMetallicRoughness']]
        self.assertEqual(set(textured), {FILM, PRINT})
        film = self.image(FILM)
        alpha = film.getchannel('A')
        self.assertEqual(alpha.getextrema()[0], 0)
        self.assertLess(alpha.getextrema()[1], 170, 'No opaque white paper may replace the clear film.')
        self.assertTrue(20 <= alpha.getpixel((film.width // 2, film.height // 2)) <= 45)
        interior = film.crop((30, 30, film.width - 30, film.height - 30))
        self.assertGreater(min(low for low, high in ImageStat.Stat(interior.convert('RGB')).extrema), 220,
                           'The unprinted carrier must not contain lettering or dark decorations.')
        self.assertFalse(any(e.tag.endswith(('}text', '}path')) for e in ET.parse(SOURCE / 'label.svg').getroot().iter()))

    def test_independent_print_contains_only_logo_and_exact_product_name_in_the_reference_layout(self):
        for name, filename in [(FILM, 'label.png'), (PRINT, 'print.png')]:
            image = self.image(name)
            with Image.open(SOURCE / filename) as source:
                self.assertEqual(image.size, source.size)
                self.assertIsNone(ImageChops.difference(image, source.convert('RGBA')).getbbox(alpha_only=False))
        printing = self.image(PRINT)
        alpha = printing.getchannel('A').point(lambda value: 255 if value > 32 else 0)
        self.assertLess(max(ImageStat.Stat(printing.convert('RGB'), alpha).mean), 55)
        rows = [bool(alpha.crop((0, y, printing.width, y + 1)).getbbox()) for y in range(printing.height)]
        starts = [i for i, filled in enumerate(rows) if filled and (i == 0 or not rows[i - 1])]
        ends = [i + 1 for i, filled in enumerate(rows) if filled and (i + 1 == len(rows) or not rows[i + 1])]
        self.assertEqual(len(starts), 2, 'Do not invent capacity, rules or extra subtitles absent from the reference.')
        low, high = self.bounds(self.positions(PRINT))
        width = self.width()
        for start, end, (target_width, target_height, center) in zip(starts, ends, [(.375, .14, .350), (.52, .029, .210)]):
            bounds = alpha.crop((0, start, printing.width, end)).getbbox()
            self.assertAlmostEqual((bounds[2] - bounds[0]) / printing.width * (high[0] - low[0]) / width, target_width, delta=.015)
            self.assertAlmostEqual((end - start) / printing.height * (high[1] - low[1]) / width, target_height, delta=.006)
            self.assertAlmostEqual((high[1] - (start + end) / 2 / printing.height * (high[1] - low[1])) / width, center, delta=.008)
        svg = ET.parse(SOURCE / 'print.svg').getroot()
        self.assertEqual([e.text for e in svg.iter() if e.tag.endswith('}text')], ['GOLDEN FACE OIL'])
        paths = [e for e in svg.iter() if e.tag.endswith('}path')]
        self.assertEqual(len(paths), 1)
        approved = ET.parse(CLIENT / 'model-source/collection/poster-039/print.svg').getroot()
        self.assertEqual(paths[0].get('d'), next(e.get('d') for e in approved.iter() if e.tag.endswith('}path')))


if __name__ == '__main__':
    unittest.main()
