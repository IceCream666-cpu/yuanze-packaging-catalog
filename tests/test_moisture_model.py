"""Check the individual Moisture 049 reconstruction against its reference ratios."""
import io
import json
import math
from pathlib import Path
import struct
import unittest
from PIL import Image

CLIENT = Path(__file__).resolve().parents[1] / 'docs/client-motion-demo'


class MoistureModelTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        raw = (CLIENT / 'packaging-assets/poster-049.glb').read_bytes()
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

    def positions(self, index):
        node = self.nodes[index]
        points = []
        for primitive in self.gltf['meshes'][node['mesh']]['primitives']:
            accessor = self.gltf['accessors'][primitive['attributes']['POSITION']]
            self.assertEqual((accessor['type'], accessor['componentType']), ('VEC3', 5126))
            self.assertNotIn('sparse', accessor)
            view = self.gltf['bufferViews'][accessor['bufferView']]
            offset = view.get('byteOffset', 0) + accessor.get('byteOffset', 0)
            points.extend(struct.unpack_from('<3f', self.binary, offset + i * view.get('byteStride', 12))
                          for i in range(accessor['count']))
        # Blender exports these revolved meshes with rotations baked into the vertices.
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

    def materials(self, index):
        return [self.gltf['materials'][p['material']]
                for p in self.gltf['meshes'][self.nodes[index]['mesh']]['primitives']]

    def mesh_indices(self, root=None):
        return [i for i, node in enumerate(self.nodes)
                if 'mesh' in node and (root is None or self.ancestor(i) == root)]

    @staticmethod
    def bounds(points):
        return ([min(p[j] for p in points) for j in range(3)],
                [max(p[j] for p in points) for j in range(3)])

    def test_six_independent_groups_and_embedded_editable_assets(self):
        roots = self.gltf['scenes'][self.gltf.get('scene', 0)]['nodes']
        self.assertEqual({self.nodes[i]['name'] for i in roots},
                         {'Body', 'Closure', 'PumpStem', 'Actuator', 'PaperLabel', 'LogoPrint'})
        self.assertTrue(all(self.nodes[i].get('children') for i in roots))
        self.assertTrue(all('uri' not in item for item in self.gltf.get('images', []) + self.gltf.get('buffers', [])))
        self.assertFalse(self.gltf.get('animations'))
        self.assertFalse(self.gltf.get('cameras'))
        source = CLIENT / 'model-source/collection/poster-049'
        self.assertTrue((source / 'poster-049.blend').is_file())
        info = json.loads((source / 'model-info.json').read_text())
        self.assertFalse(info['containsFormula'])
        self.assertTrue(info['illustrativeDimensions'])

    def test_round_bottle_and_reference_height_and_closure_ratios(self):
        glass = [i for i in self.mesh_indices('Body') if any(
            m.get('extensions', {}).get('KHR_materials_transmission', {}).get('transmissionFactor', 0) > .5
            for m in self.materials(i))]
        self.assertTrue(glass, 'The bottle body must include transparent glass.')
        body = max(glass, key=lambda i: self.bounds(self.positions(i))[1][0] - self.bounds(self.positions(i))[0][0])
        points = self.positions(body)
        low, high = self.bounds(points)
        diameter = high[0] - low[0]
        self.assertAlmostEqual(diameter, high[2] - low[2], places=5, msg='The bottle must remain round, not flattened.')
        center_x, center_z = (low[0] + high[0]) / 2, (low[2] + high[2]) / 2
        widest = max(points, key=lambda p: p[0])
        ring = [p for p in points if abs(p[1] - widest[1]) < 1e-6]
        outer = [math.hypot(p[0] - center_x, p[2] - center_z) for p in ring
                 if math.hypot(p[0] - center_x, p[2] - center_z) > diameter * .48]
        self.assertGreaterEqual(len(outer), 64)
        self.assertLess(max(outer) - min(outer), diameter * .005, 'The widest bottle ring must be circular.')
        all_low, all_high = self.bounds([p for i in self.mesh_indices() for p in self.positions(i)])
        self.assertTrue(2.40 <= (all_high[1] - all_low[1]) / diameter <= 2.50,
                        'The full bottle must match the reference height-to-width ratio.')
        cap_low, cap_high = self.bounds([p for i in self.mesh_indices('Closure') for p in self.positions(i)])
        self.assertTrue(.86 <= (cap_high[0] - cap_low[0]) / diameter <= .92,
                        'The silver closure must retain the reference diameter relative to the body.')

    def test_clear_neutral_glass_and_polished_silver_materials(self):
        glass = [m for m in self.gltf['materials']
                 if m.get('extensions', {}).get('KHR_materials_transmission', {}).get('transmissionFactor', 0) > .5]
        silver = [m for m in self.gltf['materials'] if m['pbrMetallicRoughness'].get('metallicFactor', 1) > .9]
        self.assertTrue(glass)
        self.assertTrue(silver)
        for material in glass:
            pbr = material['pbrMetallicRoughness']
            rgb = pbr.get('baseColorFactor', [1, 1, 1, 1])[:3]
            self.assertLess(max(rgb) - min(rgb), .005, 'Clear glass must not inherit the old yellow tint.')
            self.assertGreaterEqual(min(rgb), .95)
            self.assertEqual(pbr.get('metallicFactor', 1), 0)
            self.assertGreaterEqual(material['extensions']['KHR_materials_transmission']['transmissionFactor'], .98)
            self.assertLessEqual(pbr['roughnessFactor'], .06)
        for material in silver:
            pbr = material['pbrMetallicRoughness']
            rgb = pbr.get('baseColorFactor', [1, 1, 1, 1])[:3]
            self.assertLess(max(rgb) - min(rgb), .005)
            self.assertTrue(.12 <= pbr['roughnessFactor'] <= .20,
                            'The Moisture silver finish must retain its softer sheen rather than a mirror finish.')

    def test_paper_and_printing_are_separate_without_a_duplicate_label_on_the_body(self):
        textured = [i for i in self.mesh_indices() if any(
            'baseColorTexture' in m['pbrMetallicRoughness'] for m in self.materials(i))]
        self.assertTrue(textured, 'The model must retain the product artwork.')
        paper = self.named['Ivory paper label']
        self.assertEqual(self.ancestor(paper), 'PaperLabel')
        self.assertEqual({self.nodes[i]['name'] for i in self.mesh_indices('PaperLabel')}, {'Ivory paper label'})
        self.assertEqual({self.nodes[i]['name'] for i in self.mesh_indices('LogoPrint')}, {'Complete shampoo print'})
        self.assertEqual({self.nodes[i]['name'] for i in self.mesh_indices('Body')},
                         {'Clear wide-mouth bottle', 'Glass neck bead', 'Visible bottle thread'})
        for name in ['Ivory paper label', 'Complete shampoo print']:
            self.assertEqual(sum(node['name'] == name for node in self.nodes), 1)
        for index in textured:
            self.assertEqual(self.ancestor(index), 'PaperLabel' if index == paper else 'LogoPrint', self.nodes[index]['name'])
        for index in self.mesh_indices('Body'):
            for material in self.materials(index):
                for fields in [material, material['pbrMetallicRoughness']]:
                    self.assertFalse(any(key.endswith('Texture') for key in fields),
                                     'The bottle body must not retain a label texture after the whole label opens.')
        for material in self.materials(paper):
            texture = material['pbrMetallicRoughness'].get('baseColorTexture')
            if not texture:
                continue
            image = self.gltf['images'][self.gltf['textures'][texture['index']]['source']]
            view = self.gltf['bufferViews'][image['bufferView']]
            offset = view.get('byteOffset', 0)
            with Image.open(io.BytesIO(self.binary[offset:offset + view['byteLength']])) as decoded:
                rgba = decoded.convert('RGBA')
                mask = rgba.getchannel('A').point(lambda alpha: 255 if alpha > 32 else 0)
                self.assertIsNotNone(mask.getbbox())
                visible = Image.composite(rgba.convert('RGB'), Image.new('RGB', rgba.size, 'white'), mask)
                self.assertGreater(min(low for low, high in visible.getextrema()), 180,
                                   'The moving paper contains only its ivory background, never duplicate dark printing.')

    def test_bottle_bottom_and_actuator_top_are_sealed_without_rejecting_designed_openings(self):
        # The collar's central pump aperture and the dispensing outlet are intentional.
        for name, top in [('Clear wide-mouth bottle', False), ('Silver actuator shaft', True)]:
            with self.subTest(mesh=name):
                index = self.named[name]
                points = self.positions(index)
                low, high = self.bounds(points)
                center_x, center_z = (low[0] + high[0]) / 2, (low[2] + high[2]) / 2
                level = high[1] if top else low[1]
                axis = {i for i, (x, y, z) in enumerate(points)
                        if abs(x-center_x) < 1e-6 and abs(z-center_z) < 1e-6 and abs(y-level) < 1e-6}
                self.assertTrue(axis, f'{name} must be sealed at the axis, without an accidental pinhole.')
                primitive, = self.gltf['meshes'][self.nodes[index]['mesh']]['primitives']
                accessor = self.gltf['accessors'][primitive['indices']]
                view = self.gltf['bufferViews'][accessor['bufferView']]
                fmt = {5121: 'B', 5123: 'H', 5125: 'I'}[accessor['componentType']]
                offset = view.get('byteOffset', 0) + accessor.get('byteOffset', 0)
                indices = struct.unpack_from('<' + fmt * accessor['count'], self.binary, offset)
                self.assertGreaterEqual(sum(vertex in axis for vertex in indices), 3,
                                        'The axis vertex must belong to the closing faces.')
