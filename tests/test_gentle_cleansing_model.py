"""Inspect Gentle Cleansing 044's actual GLB geometry and artwork against the original poster."""
import io
import json
import math
from collections import Counter
from pathlib import Path
import struct
import unittest
import xml.etree.ElementTree as ET

from PIL import Image, ImageChops, ImageStat

CLIENT = Path(__file__).resolve().parents[1] / 'docs/client-motion-demo'
SOURCE = CLIENT / 'model-source/collection/poster-044'
BODY = 'Hollow straight clear bottle with rounded thick base'
COVER = 'Hollow clear protective overcap with top dimple'
CLOSURE = 'Wide smooth white screw closure'
OVAL = 'Translucent frosted white oval decoration'
PRINT = 'Complete Gentle Cleansing lettering'
TUBE = 'Hollow clear Gentle pump dip tube'


class GentleCleansingModelTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        raw = (CLIENT / 'packaging-assets/poster-044.glb').read_bytes()
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
        def belongs(name):
            index = self.named[name]
            while True:
                if self.nodes[index]['name'] == group:
                    return True
                if index not in self.parents:
                    return False
                index = self.parents[index]
        return [n['name'] for n in self.nodes if 'mesh' in n and (group is None or belongs(n['name']))]

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

    def diameter(self):
        low, high = self.bounds(self.positions(BODY))
        return high[0] - low[0]

    def radii_at(self, name, level):
        diameter = self.diameter()
        radii = [math.hypot(x, z) / diameter for x, y, z in self.positions(name)
                 if abs(y / diameter - level) < 1e-5]
        self.assertTrue(radii, f'{name} must include the expected ring at {level}D')
        return radii

    def material(self, name):
        return self.gltf['materials'][self.primitive(name)['material']]

    def image(self, name):
        texture = self.material(name)['pbrMetallicRoughness']['baseColorTexture']['index']
        image = self.gltf['images'][self.gltf['textures'][texture]['source']]
        view = self.gltf['bufferViews'][image['bufferView']]
        offset = view.get('byteOffset', 0)
        return Image.open(io.BytesIO(self.binary[offset:offset + view['byteLength']])).convert('RGBA')

    def assert_connected_axis(self, name, level):
        diameter = self.diameter()
        axis = {i for i, (x, y, z) in enumerate(self.positions(name))
                if math.hypot(x, z) < 1e-6 and abs(y / diameter - level) < 1e-5}
        self.assertTrue(axis, f'{name} must have a solid axis at {level}D')
        indices = [item[0] for item in self.accessor(self.primitive(name)['indices'])]
        self.assertGreaterEqual(sum(i in axis for i in indices), 3, 'A loose axis vertex is not a sealing face.')

    def test_five_groups_keep_the_complete_pump_and_only_empty_packaging(self):
        roots = self.gltf['scenes'][self.gltf.get('scene', 0)]['nodes']
        counts = {'Body': 2, 'PumpAssembly': 10, 'Overcap': 2, 'PaperLabel': 1, 'LogoPrint': 1}
        self.assertEqual({self.nodes[i]['name'] for i in roots}, set(counts))
        self.assertEqual(len(self.mesh_names()), 16, 'Only the new hollow tube is added to the original packaging.')
        for group, count in counts.items():
            self.assertEqual(len(self.mesh_names(group)), count)
        pump = self.nodes[self.named['PumpAssembly']]
        self.assertEqual({self.nodes[i]['name'] for i in pump['children']}, {'Closure', 'PumpStem', 'Actuator'})
        self.assertNotIn('matrix', pump)
        self.assertEqual(pump.get('translation', [0, 0, 0]), [0, 0, 0])
        self.assertEqual(pump.get('rotation', [0, 0, 0, 1]), [0, 0, 0, 1])
        self.assertEqual(pump.get('scale', [1, 1, 1]), [1, 1, 1])
        for group, count in {'Closure': 4, 'PumpStem': 2, 'Actuator': 4}.items():
            self.assertEqual(len(self.mesh_names(group)), count)
        self.assertEqual(self.mesh_names('PaperLabel'), [OVAL])
        self.assertEqual(self.mesh_names('LogoPrint'), [PRINT])
        self.assertTrue(all('uri' not in item for item in self.gltf['images'] + self.gltf['buffers']))
        self.assertFalse(self.gltf.get('animations'))
        self.assertFalse(self.gltf.get('cameras'))
        info = json.loads((SOURCE / 'model-info.json').read_text())
        self.assertTrue(info['illustrativeDimensions'])
        self.assertFalse(info['containsFormula'])
        self.assertFalse(info['containsFoam'])
        self.assertTrue((SOURCE / 'poster-044.blend').is_file())

    def test_clear_hollow_dip_tube_is_fitted_to_pump_and_clears_the_bottle(self):
        self.assertEqual(self.ancestor(TUBE), 'PumpAssembly')
        self.assertEqual(self.nodes[self.parents[self.named[TUBE]]]['name'], 'Closure')
        diameter = self.diameter()
        points = self.positions(TUBE)
        low, high = self.bounds(points)
        radii = [math.hypot(x, z) / diameter for x, y, z in points]
        self.assertAlmostEqual(min(radii), .026, delta=.0002)
        self.assertAlmostEqual(max(radii), .035, delta=.0002)
        self.assertGreater(sum(abs(r-.026) < 1e-5 for r in radii), 100)
        self.assertGreater(sum(abs(r-.035) < 1e-5 for r in radii), 100)
        self.assertAlmostEqual(low[1] / diameter, .16, delta=.001)
        self.assertAlmostEqual(high[1] / diameter, 2.69, delta=.001)
        body = self.positions(BODY)
        inner_floor = max(y for x, y, z in body if math.hypot(x, z) < 1e-6)
        self.assertTrue(.06 < (low[1]-inner_floor)/diameter < .09)
        self.assertGreater(low[1]+2.15-self.bounds(body)[1][1], .35, 'The inlet fully clears the bottle when the complete pump opens.')
        cap_low = min(p[1] for name in self.mesh_names('Overcap') for p in self.positions(name))
        head_high = max(p[1] for name in self.mesh_names('Actuator') for p in self.positions(name))
        self.assertGreater(cap_low+3.15-head_high-2.15, .3, 'The protective cover must fully separate from the pump head.')
        indices = [row[0] for row in self.accessor(self.primitive(TUBE)['indices'])]
        edges, volume = Counter(), 0
        for offset in range(0, len(indices), 3):
            triangle = [points[i] for i in indices[offset:offset+3]]
            a, b, c = triangle
            volume += (a[0]*(b[1]*c[2]-b[2]*c[1]) - a[1]*(b[0]*c[2]-b[2]*c[0]) + a[2]*(b[0]*c[1]-b[1]*c[0]))/6
            welded = [tuple(round(v, 7) for v in p) for p in triangle]
            self.assertEqual(len(set(welded)), 3)
            for i in range(3):
                edges[tuple(sorted((welded[i], welded[(i+1)%3])))] += 1
            determinant = (b[2]-c[2])*(a[0]-c[0]) + (c[0]-b[0])*(a[2]-c[2])
            if abs(determinant) > 1e-12:
                u = ((b[2]-c[2])*(-c[0]) + (c[0]-b[0])*(-c[2]))/determinant
                v = ((c[2]-a[2])*(-c[0]) + (a[0]-c[0])*(-c[2]))/determinant
                self.assertLess(min(u, v, 1-u-v), -1e-6, 'Both tube mouths must remain open along the central bore.')
        self.assertEqual(set(edges.values()), {2})
        self.assertGreater(volume, 0)
        material = self.material(TUBE)
        pbr = material['pbrMetallicRoughness']
        self.assertEqual(pbr.get('metallicFactor', 1), 0)
        self.assertEqual(pbr.get('baseColorFactor', [1, 1, 1, 1]), [1, 1, 1, 1])
        self.assertTrue(.03 <= pbr['roughnessFactor'] <= .1)
        self.assertGreaterEqual(material['extensions']['KHR_materials_transmission']['transmissionFactor'], .95)
        self.assertAlmostEqual(material['extensions']['KHR_materials_ior']['ior'], 1.46, delta=.02)
        self.assertFalse(material.get('doubleSided', False))

    def test_original_poster_height_round_body_wide_closure_and_short_right_nozzle(self):
        diameter = self.diameter()
        low, high = self.bounds([p for name in self.mesh_names() for p in self.positions(name)])
        self.assertAlmostEqual((high[1] - low[1]) / diameter, 3.44, delta=.025)
        body_low, body_high = self.bounds(self.positions(BODY))
        self.assertAlmostEqual((body_high[2] - body_low[2]) / diameter, 1, places=5)
        for level in [.12, 2.110]:
            radii = self.radii_at(BODY, level)
            self.assertLess(max(abs(r - .5) for r in radii), 1e-5, 'The main wall must remain circular and straight.')
        closure_low, closure_high = self.bounds(self.positions(CLOSURE))
        self.assertAlmostEqual(closure_low[1] / diameter, 2.17, delta=.005)
        self.assertAlmostEqual((closure_high[1] - closure_low[1]) / diameter, .35, delta=.005)
        self.assertAlmostEqual((closure_high[0] - closure_low[0]) / diameter, .982, delta=.005)
        head = [p for name in self.mesh_names('Actuator') for p in self.positions(name)]
        head_low, head_high = self.bounds(head)
        self.assertAlmostEqual((head_high[0] - head_low[0]) / diameter, .642, delta=.015)
        self.assertLess(max(math.hypot(x, z) for x, y, z in head) / diameter, .425,
                        'The short foamer head must fit inside the protective cover.')
        self.assertLess(head_high[1] / diameter, 3.40)
        spout = self.positions('Short curved right dispensing spout')
        spout_low, spout_high = self.bounds(spout)
        self.assertGreater(spout_low[0], 0)
        self.assertAlmostEqual(spout_high[0] / diameter, .382, delta=.005)
        self.assertLess((spout_high[0] - spout_low[0]) / diameter, .28,
                        'Do not reuse the long lotion-pump lever.')
        outlet_low, outlet_high = self.bounds(self.positions('Recessed foamer outlet'))
        self.assertLess(outlet_high[0], spout_high[0])

    def test_thin_hollow_bottle_wall_and_rounded_sealed_thick_base(self):
        top = self.radii_at(BODY, 2.286)
        self.assertAlmostEqual(min(top), .393, delta=.002)
        self.assertAlmostEqual(max(top), .418, delta=.002)
        self.assertGreater(min(top), .38, 'The neck is open, not filled with formula or a top disc.')
        inner_radius = self.radii_at(BODY, .132)
        self.assertTrue(all(.02 < .5 - r < .04 for r in inner_radius), 'The cavity must leave a thin clear sidewall.')
        self.assertAlmostEqual(max(self.radii_at(BODY, .025)), .443, delta=.002)
        self.assert_connected_axis(BODY, 0)
        self.assert_connected_axis(BODY, .087)

    def test_clear_cover_is_thin_open_below_and_solid_through_its_top_dimple(self):
        diameter = self.diameter()
        low, high = self.bounds([p for name in self.mesh_names('Overcap') for p in self.positions(name)])
        self.assertAlmostEqual((high[1] - low[1]) / diameter, .90, delta=.005)
        self.assertAlmostEqual((high[0] - low[0]) / diameter, .91, delta=.005)
        lower = self.radii_at(COVER, 2.540)
        self.assertAlmostEqual(min(lower), .430, delta=.002)
        self.assertAlmostEqual(max(lower), .447, delta=.002)
        self.assertTrue(.01 < max(lower) - min(lower) < .03)
        self.assertGreater(min(lower), .42, 'The dust cover must stay open underneath.')
        self.assert_connected_axis(COVER, 3.425)
        self.assert_connected_axis(COVER, 3.410)
        self.assertLess(3.425 * diameter, high[1], 'The top molding dimple is recessed but not a through-hole.')

    def test_neutral_transparent_walls_white_pump_and_frosted_oval_materials(self):
        for name in [BODY, COVER]:
            material = self.material(name)
            pbr = material['pbrMetallicRoughness']
            rgb = pbr.get('baseColorFactor', [1, 1, 1, 1])[:3]
            self.assertGreater(min(rgb), .93)
            self.assertLess(max(rgb) - min(rgb), .08, 'The liquid tint must not become yellow packaging.')
            self.assertGreaterEqual(material['extensions']['KHR_materials_transmission']['transmissionFactor'], .98)
            self.assertLessEqual(pbr['roughnessFactor'], .06)
            self.assertEqual(pbr.get('metallicFactor', 1), 0)
        for name in [CLOSURE, 'Tall rounded foamer actuator']:
            material = self.material(name)
            pbr = material['pbrMetallicRoughness']
            self.assertGreater(min(pbr['baseColorFactor'][:3]), .85)
            self.assertTrue(.18 < pbr['roughnessFactor'] < .35)
            self.assertEqual(material.get('extensions', {}).get('KHR_materials_transmission', {}).get('transmissionFactor', 0), 0)
        self.assertTrue(all(self.material(n)['pbrMetallicRoughness'].get('metallicFactor', 1) == 0 for n in self.mesh_names()),
                        'No metal ring is present in the original reference.')
        self.assertGreater(self.material(OVAL)['pbrMetallicRoughness']['roughnessFactor'], .70)

    def test_oval_is_separate_correctly_sized_and_both_artwork_layers_follow_the_body(self):
        diameter = self.diameter()
        low, high = self.bounds(self.positions(OVAL))
        self.assertAlmostEqual((high[0] - low[0]) / diameter, .72, delta=.005)
        self.assertAlmostEqual((high[1] - low[1]) / diameter, .91, delta=.005)
        self.assertAlmostEqual((high[1] + low[1]) / (2 * diameter), 1.06, delta=.005)
        self.assertAlmostEqual(low[1] / diameter, .605, delta=.005)
        textured = [n for n in self.mesh_names() if 'baseColorTexture' in self.material(n)['pbrMetallicRoughness']]
        self.assertEqual(set(textured), {OVAL, PRINT})
        for name in self.mesh_names('Body'):
            self.assertNotIn('Texture', json.dumps(self.material(name)), 'The body must not retain duplicate wording or the oval.')
        # The actual body rings above establish radius D/2; all exported artwork vertices must follow it.
        for name, offset in [(OVAL, .0015), (PRINT, .0022)]:
            points = self.positions(name)
            low, high = self.bounds(points)
            self.assertGreater((high[2] - low[2]) / diameter, .1, 'The label must wrap the cylinder, not float as a flat plate.')
            for x, y, z in points:
                self.assertAlmostEqual((z - math.sqrt((diameter / 2) ** 2 - x ** 2)) / diameter, offset, delta=1e-6)
            self.assertEqual(self.material(name)['alphaMode'], 'BLEND')

    def test_embedded_oval_has_no_ink_and_complete_black_120ml_print_matches_reference_layout(self):
        oval, printing = self.image(OVAL), self.image(PRINT)
        for image, filename in [(oval, 'label.png'), (printing, 'print.png')]:
            with Image.open(SOURCE / filename) as source:
                self.assertEqual(image.size, source.size)
                self.assertIsNone(ImageChops.difference(image, source.convert('RGBA')).getbbox(alpha_only=False))
        alpha = oval.getchannel('A')
        self.assertEqual(alpha.getextrema()[0], 0)
        self.assertTrue(100 < alpha.getextrema()[1] < 200)
        visible = alpha.point(lambda a: 255 if a > 32 else 0)
        self.assertGreater(min(low for low, high in ImageStat.Stat(oval.convert('RGB'), visible).extrema), 200,
                           'The frosted oval must contain no black speck, text or baked-in pump shadow.')
        for x, y in [(0, 0), (oval.width - 1, 0), (0, oval.height - 1), (oval.width - 1, oval.height - 1)]:
            self.assertEqual(alpha.getpixel((x, y)), 0, 'No rectangular white label background may remain.')
        for y_fraction in [.10, .25, .50, .75, .90]:
            row = visible.crop((0, int(y_fraction * oval.height), oval.width, int(y_fraction * oval.height) + 1)).getbbox()
            self.assertIsNotNone(row)
            expected = math.sqrt(1 - (2 * y_fraction - 1) ** 2)
            self.assertAlmostEqual((row[2] - row[0]) / oval.width, expected, delta=.015)
        print_alpha = printing.getchannel('A').point(lambda a: 255 if a > 32 else 0)
        self.assertLess(max(ImageStat.Stat(printing.convert('RGB'), print_alpha).mean), 35)
        rows = [bool(print_alpha.crop((0, y, printing.width, y + 1)).getbbox()) for y in range(printing.height)]
        starts = [i for i, filled in enumerate(rows) if filled and (i == 0 or not rows[i - 1])]
        ends = [i + 1 for i, filled in enumerate(rows) if filled and (i + 1 == len(rows) or not rows[i + 1])]
        self.assertEqual(len(starts), 5, 'All four copy items and the separator must be present, without extra marks.')
        low, high = self.bounds(self.positions(PRINT))
        diameter = self.diameter()
        targets = [(.598, .238, 1.685), (.257, .037, .646), (.626, .037, .561), (.131, .004, .444), (.196, .047, .313)]
        for start, end, (width, height, center) in zip(starts, ends, targets):
            bounds = print_alpha.crop((0, start, printing.width, end)).getbbox()
            self.assertAlmostEqual((bounds[2] - bounds[0]) / printing.width * (high[0] - low[0]) / diameter, width, delta=.015)
            self.assertAlmostEqual((end - start) / printing.height * (high[1] - low[1]) / diameter, height, delta=.008)
            self.assertAlmostEqual((high[1] - (start + end) / 2 / printing.height * (high[1] - low[1])) / diameter, center, delta=.01)
        svg = ET.parse(SOURCE / 'print.svg').getroot()
        self.assertEqual([e.text for e in svg.iter() if e.tag.endswith('}text')], ['GENTLE', 'CLEANSING FOAM', '120 ml'])
        paths = [e for e in svg.iter() if e.tag.endswith('}path')]
        self.assertEqual(len(paths), 2)
        approved = ET.parse(CLIENT / 'model-source/collection/poster-039/print.svg').getroot()
        self.assertEqual(paths[0].get('d'), next(e.get('d') for e in approved.iter() if e.tag.endswith('}path')))
        self.assertEqual(paths[1].get('fill'), 'none')
        self.assertIn('stroke', paths[1].attrib)
        self.assertFalse(any(e.tag.endswith(('}text', '}path')) for e in ET.parse(SOURCE / 'label.svg').getroot().iter()))


if __name__ == '__main__':
    unittest.main()
