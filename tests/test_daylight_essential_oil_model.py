"""Actual Daylight geometry, artwork and complete-cap regressions."""
import io
import math
import unittest

from PIL import Image, ImageChops
from tests.tail_model_checks import TailChecks


class DaylightEssentialOilModelTests(TailChecks, unittest.TestCase):
    ID = 'poster-070'
    RATIO = 1.39
    GROUPS = ['Body', 'Closure', 'PaperLabel', 'LogoPrint']
    TEXT = ['DAYLIGHT', 'ESSENTIAL OIL']
    CAP_MESHES = {
        'Champagne cylindrical metal screw cap',
        'Hidden cap seal',
        'Embossed sleeve around the cap',
        'Original loose embossed wrap extension at right',
    }

    def embedded_image(self, texture_index):
        texture = self.g['textures'][texture_index]
        image = self.g['images'][texture['source']]
        view = self.g['bufferViews'][image['bufferView']]
        start = view.get('byteOffset', 0)
        return Image.open(io.BytesIO(self.binary[start:start + view['byteLength']])).convert('RGBA')

    def test_frosted_cone_and_complete_cap_preserve_wrap_texture_and_seal(self):
        self.load()
        self.assertTrue(self.config['appearance']['frosted'])
        closure = [(i, p) for i, p in self.meshes() if self.ancestor(i) == 'Closure']
        self.assertEqual({self.nodes[i]['name'] for i, _ in closure}, self.CAP_MESHES)
        self.assertEqual(len(closure), 4)
        for i, p in self.meshes():
            material = self.g['materials'][p['material']]
            if self.ancestor(i) == 'Body':
                self.assertTrue(.2 <= material['pbrMetallicRoughness']['roughnessFactor'] <= .3)
        wraps = [(i, p) for i, p in closure if 'embossed' in self.nodes[i]['name'].lower()]
        self.assertEqual(len(wraps), 2)
        for _, primitive in wraps:
            material = self.g['materials'][primitive['material']]
            self.assertGreater(material['pbrMetallicRoughness']['roughnessFactor'], .7)
            self.assertIn('normalTexture', material)
            for texture_index, file in [
                (material['pbrMetallicRoughness']['baseColorTexture']['index'], 'embossed-wrap.png'),
                (material['normalTexture']['index'], 'embossed-wrap-normal.png'),
            ]:
                expected = Image.open(self.source / file).convert('RGBA')
                self.assertIsNone(ImageChops.difference(self.embedded_image(texture_index), expected).getbbox(alpha_only=False))
        self.assertEqual({part['node'] for part in self.config['parts']}, set(self.GROUPS))
        self.assertEqual(self.config['explosion']['offsets']['closure'], [0, 1.35, 0])
        for settings in ('offsets', 'scales', 'timing', 'rotations'):
            self.assertNotIn('wrap', self.config['explosion'].get(settings, {}))
        self.assertEqual(self.config['explosion'].get('scales', {}).get('closure', 1), 1)
        self.assertNotIn('closure', self.config['explosion'].get('timing', {}))

    def test_complete_cap_clears_bottle_and_all_layers_fit_closed_half_and_open_frames(self):
        self.load()
        meshes = [(i, primitive, self.points(i, primitive)) for i, primitive in self.meshes()]
        cap = [point for i, _, points in meshes if self.ancestor(i) == 'Closure' for point in points]
        body = [point for i, _, points in meshes if self.ancestor(i) == 'Body' for point in points]
        self.assertGreater(min(p[1] for p in cap) + 1.35 - max(p[1] for p in body), 1.2)
        explosion = self.config['explosion']
        camera = explosion['camera']
        keys = {part['node']: part['key'] for part in self.config['parts']}
        tilt = math.atan2(1.05, 10)
        aspect = 1200 / 800
        for progress in (0, .5, 1):
            lerp = lambda pair: pair[0] + (pair[1] - pair[0]) * progress
            height = max(lerp(camera['height']), lerp(camera['width']) / aspect)
            posed = []
            for i, _, points in meshes:
                root = self.ancestor(i)
                key = keys[root]
                pivot = self.nodes[self.named[root]].get('translation', [0, 0, 0])
                offset = explosion['offsets'].get(key, [0, 0, 0])
                scale = 1 + (explosion['scales'].get(key, 1) - 1) * progress
                posed.extend(tuple((p[j] - pivot[j]) * scale + pivot[j] + offset[j] * progress for j in range(3)) for p in points)
            for x, y, z in posed:
                screen_y = (y - lerp(camera['centerY'])) * math.cos(tilt) - z * math.sin(tilt)
                screen_x = x - lerp(camera['centerX'])
                self.assertLess(abs(screen_y), height / 2 - .1, f'vertical frame at {progress}')
                self.assertLess(abs(screen_x), height * aspect / 2 - .1, f'horizontal frame at {progress}')


if __name__ == '__main__':
    unittest.main()
