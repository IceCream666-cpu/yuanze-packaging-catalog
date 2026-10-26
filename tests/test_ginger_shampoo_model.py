import unittest
from tests.tail_model_checks import TailChecks
class GingerShampooModelTests(TailChecks,unittest.TestCase):
 ID='poster-067';RATIO=2.02;GROUPS=['Body','Closure','PumpStem','Actuator','Cord','PaperLabel','LogoPrint'];TEXT=['GINGER SHAMPOO']
 def test_actual_braid_and_amber_glass_are_retained(self):
  self.load();cords=[o for i,o in enumerate(self.nodes) if 'mesh' in o and self.ancestor(i)=='Cord'];self.assertGreaterEqual(len(cords),45);body=[self.g['materials'][p['material']] for i,p in self.meshes() if self.ancestor(i)=='Body'];c=body[0]['pbrMetallicRoughness']['baseColorFactor'];self.assertGreater(c[0],c[1]);self.assertGreater(c[1],c[2]);self.assertGreater(self.info['bodyDepthToWidth'],.70)
