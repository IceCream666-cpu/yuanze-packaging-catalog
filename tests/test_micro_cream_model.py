"""Actual GLB regressions for Micro Cream 062; reader reused by the next three models."""
from collections import Counter
import io, json, math, struct, unittest
from pathlib import Path
import xml.etree.ElementTree as ET
from PIL import Image, ImageChops, ImageStat
CLIENT=Path(__file__).resolve().parents[1]/'docs/client-motion-demo'
class ExportedModelReader(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        raw = (CLIENT / ('packaging-assets/' + cls.model_id + '.glb')).read_bytes()
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
        low, high = self.bounds(self.positions(self.body_name))
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

    @staticmethod
    def smooth(a, b, value):
        t = max(0, min((value - a) / (b - a), 1))
        return t * t * (3 - 2 * t)


class MicroCreamModelTests(ExportedModelReader):
    model_id='poster-062'
    body_name='Hollow wide rectangular glass jar'
    def test_reference_proportions_and_five_independent_roots(self):
        roots={self.nodes[i]['name'] for i in self.gltf['scenes'][0]['nodes']}
        self.assertEqual(roots,{'Body','Closure','InnerLid','PaperLabel','LogoPrint'})
        w=self.width();lo,hi=self.bounds([p for n in self.mesh_names() for p in self.positions(n)])
        self.assertAlmostEqual(hi[1]-lo[1],2.9,delta=.005)
        self.assertAlmostEqual((hi[1]-lo[1])/w,.70,delta=.006)
        blo,bhi=self.bounds(self.positions(self.body_name))
        self.assertAlmostEqual((bhi[2]-blo[2])/w,.60,delta=.005)
        self.assertAlmostEqual(bhi[1]/w,.481,delta=.003)
    def test_actual_glass_hollow_floor_and_cap_ceiling(self):
        w=self.width();hits=self.ray_intersections(self.body_name)
        self.assertAlmostEqual(min(hits),0,delta=1e-6);self.assertAlmostEqual(max(hits)/w,.10,delta=.001)
        roof=self.ray_intersections('Rounded black rectangular cap shell')
        self.assertAlmostEqual(min(roof)/w,.674,delta=.002);self.assertAlmostEqual(max(roof)/w,.70,delta=.002)
        liner=max(p[1] for n in self.mesh_names() if self.ancestor(n)=='InnerLid' for p in self.positions(n))
        self.assertLess(liner,min(roof)-.1)
        body=self.positions(self.body_name);ids=[x[0] for x in self.accessor(self.primitive(self.body_name)['indices'])];edges=Counter()
        weld=[tuple(round(x/w,6) for x in p) for p in body]
        for i in range(0,len(ids),3):
            a,b,c=[weld[j] for j in ids[i:i+3]];self.assertEqual(len({a,b,c}),3);edges.update(tuple(sorted(e)) for e in [(a,b),(b,c),(c,a)])
        self.assertEqual(set(edges.values()),{2})
    def test_clear_glass_and_black_cap_materials(self):
        g=self.material(self.body_name);self.assertEqual(g['extensions']['KHR_materials_transmission']['transmissionFactor'],1)
        self.assertNotIn('Texture',json.dumps(g))
        c=self.material('Rounded black rectangular cap shell')['pbrMetallicRoughness']
        self.assertLess(max(c['baseColorFactor'][:3]),.02);self.assertLess(c['roughnessFactor'],.15);self.assertEqual(c['metallicFactor'],0)
    def test_complete_lettering_is_separate_from_blank_film(self):
        source=CLIENT/'model-source/collection'/self.model_id
        printing='Complete Micro logo and product name';film='Blank transparent Micro carrier'
        self.assertEqual(self.ancestor(printing),'LogoPrint');self.assertEqual(self.ancestor(film),'PaperLabel')
        self.assertEqual([e.text for e in ET.parse(source/'print.svg').getroot().iter() if e.tag.endswith('}text')],['MICRO HYDRATION CREAM'])
        self.assertFalse(any(e.tag.endswith(('}path','}text')) for e in ET.parse(source/'label.svg').getroot().iter()))
        self.assertLess(self.image(film).getchannel('A').getextrema()[1],170)
        for mesh,file in [(printing,'print.png'),(film,'label.png')]:
            self.assertIsNone(ImageChops.difference(self.image(mesh),Image.open(source/file).convert('RGBA')).getbbox(alpha_only=False))
        textured=[n for n in self.mesh_names() if 'baseColorTexture' in self.material(n)['pbrMetallicRoughness']]
        self.assertEqual(set(textured),{printing,film})
        pz=self.bounds(self.positions(printing))[0][2];fz=self.bounds(self.positions(film))[0][2]
        self.assertGreater(pz,fz)

if __name__=='__main__':unittest.main()
