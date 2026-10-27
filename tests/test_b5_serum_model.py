"""Inspect B5 Serum 057's exported geometry, empty packaging and separate artwork."""
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
SOURCE = CLIENT / 'model-source/collection/poster-057'
BODY = 'Hollow rounded flat B5 glass bottle'
BASE = 'Hollow matte white base cup with sealed floor'
COLLAR = 'Smooth white open screw collar'
BULB = 'Hollow white elastomer dropper bulb'
TUBE = 'Hollow clear pipette with open tapered tip'
FILM = 'Transparent unprinted B5 label film'
PRINT = 'Complete white B5 bottle printing'
RELIEF = 'Raised liaose base lettering'


class B5SerumModelTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        raw = (CLIENT / 'packaging-assets/poster-057.glb').read_bytes()
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
        low, high = self.bounds(self.positions(BASE))
        return high[0] - low[0]

    def material(self, name):
        return self.gltf['materials'][self.primitive(name)['material']]

    def image(self, name):
        texture = self.material(name)['pbrMetallicRoughness']['baseColorTexture']['index']
        image = self.gltf['images'][self.gltf['textures'][texture]['source']]
        view = self.gltf['bufferViews'][image['bufferView']]
        offset = view.get('byteOffset', 0)
        return Image.open(io.BytesIO(self.binary[offset:offset + view['byteLength']])).convert('RGBA')

    def ray_intersections(self, name, direction=1, a=0, b=0):
        """Intersect actual triangles with an axis ray; a/b are the other two coordinates."""
        points = self.positions(name)
        indices = [item[0] for item in self.accessor(self.primitive(name)['indices'])]
        u, v = [axis for axis in range(3) if axis != direction]
        hits = []
        for i in range(0, len(indices), 3):
            p, q, r = [points[j] for j in indices[i:i + 3]]
            denominator = (q[v] - r[v]) * (p[u] - r[u]) + (r[u] - q[u]) * (p[v] - r[v])
            if abs(denominator) < 1e-12:
                continue
            s = ((q[v] - r[v]) * (a - r[u]) + (r[u] - q[u]) * (b - r[v])) / denominator
            t = ((r[v] - p[v]) * (a - r[u]) + (p[u] - r[u]) * (b - r[v])) / denominator
            if min(s, t, 1 - s - t) >= -1e-7:
                hits.append(s * p[direction] + t * q[direction] + (1 - s - t) * r[direction])
        return hits

    def test_four_groups_keep_the_dropper_complete_and_base_attached_without_duplicate_lettering(self):
        expected = {'BottleAssembly': {BODY, BASE}, 'DropperAssembly': {COLLAR, BULB, TUBE},
                    'PaperLabel': {FILM}, 'LogoPrint': {PRINT, RELIEF}}
        roots = self.gltf['scenes'][self.gltf.get('scene', 0)]['nodes']
        self.assertEqual({self.nodes[i]['name'] for i in roots}, set(expected))
        self.assertEqual(len(self.mesh_names()), 8, 'No pink formula, duplicate print or old draft geometry may remain.')
        for group, names in expected.items():
            self.assertEqual({n for n in self.mesh_names() if self.ancestor(n) == group}, names)
        for group, children in [('DropperAssembly', {'Closure', 'DropperBulb', 'Pipette'}),
                                ('BottleAssembly', {'Body', 'Base'})]:
            node = self.nodes[self.named[group]]
            self.assertEqual({self.nodes[i]['name'] for i in node['children']}, children)
            self.assertEqual(node.get('translation', [0, 0, 0]), [0, 0, 0])
            self.assertEqual(node.get('rotation', [0, 0, 0, 1]), [0, 0, 0, 1])
            self.assertEqual(node.get('scale', [1, 1, 1]), [1, 1, 1])
        self.assertTrue(all('uri' not in item for item in self.gltf['images'] + self.gltf['buffers']))
        self.assertFalse(self.gltf.get('animations'))
        self.assertFalse(self.gltf.get('cameras'))
        info = json.loads((SOURCE / 'model-info.json').read_text())
        self.assertTrue(info['illustrativeDimensions'])
        self.assertFalse(info['containsFormula'])
        self.assertTrue((SOURCE / 'poster-057.blend').is_file())

    def test_world_space_proportions_follow_the_full_poster_including_its_tall_base(self):
        width = self.width()
        low, high = self.bounds([p for n in self.mesh_names() for p in self.positions(n)])
        self.assertAlmostEqual(high[1] - low[1], 2.9, delta=.006)
        self.assertAlmostEqual((high[1] - low[1]) / width, 2.14, delta=.02)
        glass_low, glass_high = self.bounds(self.positions(BODY))
        self.assertAlmostEqual((glass_high[0] - glass_low[0]) / width, .98, delta=.006)
        self.assertAlmostEqual((glass_high[2] - glass_low[2]) / width, .40, delta=.006)
        self.assertAlmostEqual(glass_high[1] / width, 1.36, delta=.005)
        base_low, base_high = self.bounds(self.positions(BASE))
        self.assertAlmostEqual(base_high[1] / width, .50, delta=.005)
        self.assertAlmostEqual((base_high[2] - base_low[2]) / width, .42, delta=.005)
        collar_low, collar_high = self.bounds(self.positions(COLLAR))
        self.assertAlmostEqual((collar_high[0] - collar_low[0]) / width, .45, delta=.005)
        self.assertAlmostEqual((collar_high[1] - collar_low[1]) / width, .40, delta=.005)
        bulb_low, bulb_high = self.bounds(self.positions(BULB))
        self.assertAlmostEqual((bulb_high[1] - collar_high[1]) / width, .39, delta=.006)
        self.assertAlmostEqual((bulb_high[0] - bulb_low[0]) / width, .28, delta=.005)
        upper = [math.hypot(x, z) / width for x, y, z in self.positions(BULB) if abs(y / width - 2.03) < 1e-5]
        self.assertAlmostEqual(max(upper), .11, delta=.002)

    def test_bottle_and_base_are_connected_hollow_shells_with_sealed_floors(self):
        width = self.width()
        for name, floor, underside in [(BODY, .11, .055), (BASE, .045, 0)]:
            hits = self.ray_intersections(name)
            self.assertTrue(hits)
            self.assertAlmostEqual(min(hits) / width, underside, delta=1e-5)
            self.assertAlmostEqual(max(hits) / width, floor, delta=1e-5,
                                   msg='The central ray must see an inner floor, not a closed mouth or formula.')
            points = self.positions(name)
            welded = [tuple(round(v / width, 6) for v in p) for p in points]
            indices = [item[0] for item in self.accessor(self.primitive(name)['indices'])]
            edges = Counter()
            for i in range(0, len(indices), 3):
                a, b, c = [welded[j] for j in indices[i:i + 3]]
                self.assertEqual(len({a, b, c}), 3)
                edges.update(tuple(sorted(pair)) for pair in [(a, b), (b, c), (c, a)])
            self.assertEqual(set(edges.values()), {2}, 'No open seam may remain in the actual exported shell.')
        mouth = [math.hypot(x, z) / width for x, y, z in self.positions(BODY) if abs(y / width - 1.36) < 1e-5]
        self.assertAlmostEqual(min(mouth), .089, delta=.002)
        self.assertAlmostEqual(max(mouth), .125, delta=.002)

    def test_base_cup_keeps_its_fitted_clearance_inside_the_stationary_bottle_assembly(self):
        width = self.width()
        glass_low, _ = self.bounds(self.positions(BODY))
        # Horizontal rays across both axes and near each rounded corner catch a solid block or tight cup.
        minimum = float('inf')
        for level in [.071, .151, .301, .449, .479, .489, .499]:
            for cross in [0, .08, .12, .15]:
                glass = self.ray_intersections(BODY, 0, level * width, cross * width)
                cup = self.ray_intersections(BASE, 0, level * width, cross * width)
                if glass and cup:
                    clearance = min(v for v in cup if v > 0) - max(glass)
                    minimum = min(minimum, clearance / width)
            glass = self.ray_intersections(BODY, 2, 0, level * width)
            cup = self.ray_intersections(BASE, 2, 0, level * width)
            minimum = min(minimum, (min(v for v in cup if v > 0) - max(glass)) / width)
        self.assertGreater(minimum, .0015, 'The white base must not penetrate the transparent bottle heel or lip.')
        self.assertGreater(glass_low[1] - .045 * width, .009 * width)
        self.assertEqual(self.ancestor(BASE), 'BottleAssembly')
        self.assertEqual(self.ancestor(BODY), 'BottleAssembly')

    def test_dropper_is_a_hollow_domed_bulb_and_open_tapered_tube_with_clear_air_path(self):
        width = self.width()
        low, high = self.bounds(self.positions(TUBE))
        self.assertAlmostEqual(low[1] / width, .17, delta=.003)
        self.assertAlmostEqual(high[1] / width, 1.82, delta=.003)
        self.assertAlmostEqual((high[0] - low[0]) / width, .058, delta=.002)
        self.assertEqual(self.ray_intersections(TUBE), [], 'Both pipette ends must be open, not capped by flat disks.')
        self.assertEqual(self.ray_intersections(COLLAR), [], 'The collar must retain the central bore.')
        for level, inner, outer in [(.17, .010, .014), (1.82, .021, .027)]:
            radii = [math.hypot(x, z) / width for x, y, z in self.positions(TUBE) if abs(y / width - level) < 1e-5]
            self.assertAlmostEqual(min(radii), inner, delta=.001)
            self.assertAlmostEqual(max(radii), outer, delta=.001)
        roof = self.ray_intersections(BULB)
        self.assertAlmostEqual(min(roof) / width, 2.121, delta=.002)
        self.assertAlmostEqual(max(roof) / width, 2.14, delta=.002)
        self.assertGreater(low[1] - max(self.ray_intersections(BODY)), .059 * width)
        self.assertGreater(.089 * width - max(math.hypot(x, z) for x, y, z in self.positions(TUBE)), .059 * width)
        self.assertGreater(min(roof) - high[1], .29 * width,
                           'The fitted pipette must retain its internal air space below the bulb roof.')
        self.assertEqual(self.ancestor(TUBE), self.ancestor(COLLAR))
        self.assertEqual(self.ancestor(TUBE), self.ancestor(BULB))

    def test_clear_empty_glass_and_opaque_white_components_keep_their_material_identity(self):
        for name in [BODY, TUBE]:
            material = self.material(name)
            pbr = material['pbrMetallicRoughness']
            self.assertGreaterEqual(min(pbr.get('baseColorFactor', [1, 1, 1, 1])[:3]), .99)
            self.assertGreaterEqual(material['extensions']['KHR_materials_transmission']['transmissionFactor'], .99)
            self.assertLessEqual(pbr['roughnessFactor'], .04)
            self.assertAlmostEqual(material['extensions']['KHR_materials_ior']['ior'], 1.49, delta=.02)
            self.assertNotIn('Texture', json.dumps(material))
        for name, roughness in [(BASE, .55), (COLLAR, .30), (BULB, .42), (RELIEF, .36)]:
            material = self.material(name)
            pbr = material['pbrMetallicRoughness']
            # The reviewed relief uses pale warm gray to remain visible against the matte white cup.
            self.assertGreater(min(pbr['baseColorFactor'][:3]), .45 if name == RELIEF else .70)
            self.assertLess(max(pbr['baseColorFactor'][:3]) - min(pbr['baseColorFactor'][:3]), .17 if name == RELIEF else .15)
            self.assertAlmostEqual(pbr['roughnessFactor'], roughness, delta=.04)
            self.assertEqual(material.get('extensions', {}).get('KHR_materials_transmission', {}).get('transmissionFactor', 0), 0)
            self.assertEqual(material.get('alphaMode', 'OPAQUE'), 'OPAQUE')
            self.assertNotIn('Texture', json.dumps(material), 'The body/base must have no baked duplicate wordmark.')
        for name in self.mesh_names():
            self.assertEqual(self.material(name)['pbrMetallicRoughness'].get('metallicFactor', 1), 0)

    def test_transparent_unprinted_film_and_white_artwork_rest_just_outside_the_glass(self):
        width = self.width()
        for name, front in [(FILM, .2014), (PRINT, .2022)]:
            low, high = self.bounds(self.positions(name))
            self.assertAlmostEqual((high[0] - low[0]) / width, .72, delta=.002)
            self.assertAlmostEqual((high[1] - low[1]) / width, .66, delta=.002)
            self.assertAlmostEqual((high[1] + low[1]) / (2 * width), .875, delta=.002)
            self.assertAlmostEqual(low[2] / width, front, delta=1e-6)
            self.assertAlmostEqual(low[2], high[2], places=6)
            self.assertEqual(self.material(name)['alphaMode'], 'BLEND')
        textured = [n for n in self.mesh_names() if 'baseColorTexture' in self.material(n)['pbrMetallicRoughness']]
        self.assertEqual(set(textured), {FILM, PRINT})
        film = self.image(FILM)
        alpha = film.getchannel('A')
        self.assertEqual(alpha.getextrema()[0], 0)
        self.assertLess(alpha.getextrema()[1], 170)
        self.assertTrue(20 <= alpha.getpixel((film.width // 2, film.height // 2)) <= 45)
        interior = film.crop((30, 30, film.width - 30, film.height - 30))
        self.assertGreater(min(low for low, high in ImageStat.Stat(interior.convert('RGB')).extrema), 220)
        self.assertFalse(any(e.tag.endswith(('}text', '}path')) for e in ET.parse(SOURCE / 'label.svg').getroot().iter()))

    def test_complete_white_type_and_real_base_relief_are_owned_only_by_the_print_group(self):
        for name, filename in [(FILM, 'label.png'), (PRINT, 'print.png')]:
            embedded = self.image(name)
            with Image.open(SOURCE / filename) as source:
                self.assertEqual(embedded.size, source.size)
                self.assertIsNone(ImageChops.difference(embedded, source.convert('RGBA')).getbbox(alpha_only=False))
        printing = self.image(PRINT)
        alpha = printing.getchannel('A').point(lambda value: 255 if value > 32 else 0)
        self.assertGreater(min(ImageStat.Stat(printing.convert('RGB'), alpha).mean), 240)
        rows = [bool(alpha.crop((0, y, printing.width, y + 1)).getbbox()) for y in range(printing.height)]
        starts = [i for i, filled in enumerate(rows) if filled and (i == 0 or not rows[i - 1])]
        ends = [i + 1 for i, filled in enumerate(rows) if filled and (i + 1 == len(rows) or not rows[i + 1])]
        self.assertEqual(len(starts), 3, 'The glass must keep the logo, B5 SERUM and 30 ml as three complete lines.')
        low, high = self.bounds(self.positions(PRINT))
        width = self.width()
        for start, end, (target_width, target_height, center) in zip(starts, ends, [(.51, .185, .97), (.325, .045, .765), (.14, .04, .64)]):
            bounds = alpha.crop((0, start, printing.width, end)).getbbox()
            self.assertAlmostEqual((bounds[2] - bounds[0]) / printing.width * (high[0] - low[0]) / width, target_width, delta=.018)
            self.assertAlmostEqual((end - start) / printing.height * (high[1] - low[1]) / width, target_height, delta=.008)
            self.assertAlmostEqual((high[1] - (start + end) / 2 / printing.height * (high[1] - low[1])) / width, center, delta=.015)
        svg = ET.parse(SOURCE / 'print.svg').getroot()
        self.assertEqual([e.text for e in svg.iter() if e.tag.endswith('}text')], ['B5 SERUM', '30 ml'])
        paths = [e for e in svg.iter() if e.tag.endswith('}path')]
        self.assertEqual(len(paths), 1)
        base_svg = ET.parse(SOURCE / 'base-logo.svg').getroot()
        self.assertEqual([e.get('d') for e in base_svg.iter() if e.tag.endswith('}path')], [paths[0].get('d')])
        low, high = self.bounds(self.positions(RELIEF))
        self.assertAlmostEqual((high[0] - low[0]) / width, .55, delta=.003)
        self.assertAlmostEqual((high[1] - low[1]) / width, .21, delta=.003)
        self.assertAlmostEqual((high[1] + low[1]) / (2 * width), .23, delta=.003)
        self.assertAlmostEqual((high[2] - low[2]) / width, .003, delta=.0003,
                               msg='The base wordmark must retain actual shallow relief, not a flat rectangle.')
        self.assertGreater(low[2], self.bounds(self.positions(BASE))[1][2])
        self.assertGreater(len(self.positions(RELIEF)), 100, 'The exported logo must retain its curved letter geometry.')
        # Narrow letter corners previously interpolated normals into the back face and produced dark flecks.
        points = self.positions(RELIEF)
        primitive = self.primitive(RELIEF)
        normals = self.accessor(primitive['attributes']['NORMAL'])
        indices = [item[0] for item in self.accessor(primitive['indices'])]
        for i in range(0, len(indices), 3):
            ids = indices[i:i + 3]
            a, b, c = [points[j] for j in ids]
            ab, ac = [b[k] - a[k] for k in range(3)], [c[k] - a[k] for k in range(3)]
            cross = [ab[1] * ac[2] - ab[2] * ac[1], ab[2] * ac[0] - ab[0] * ac[2],
                     ab[0] * ac[1] - ab[1] * ac[0]]
            length = math.sqrt(sum(value * value for value in cross))
            if length < 1e-14:
                continue
            average = [sum(normals[j][k] for j in ids) / 3 for k in range(3)]
            self.assertGreaterEqual(sum(average[k] * cross[k] for k in range(3)) / length, 0,
                                    'The actual relief triangle must not shade with a backwards average normal.')


if __name__ == '__main__':
    unittest.main()
