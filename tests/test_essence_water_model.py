import unittest
from tests.tail_model_checks import TailChecks
class EssenceWaterModelTests(TailChecks,unittest.TestCase):
 ID='poster-068';RATIO=2.36;GROUPS=['Body','Closure','NeckInsert','PaperLabel','LogoPrint'];TEXT=['ESSENCE WATER','200 ml']
 def test_lavender_cap_is_sculpted_not_a_plain_cylinder(self):
  self.load();self.assertIn('Lavender cap with original U folded front',self.named);idx=self.named['Lavender cap with original U folded front'];prim=self.g['meshes'][self.nodes[idx]['mesh']]['primitives'][0];p=self.points(idx,prim);near=[v for v in p if abs(v[0])<.002 and v[2]>.2];self.assertGreater(len(near),30);self.assertGreater(max(v[2] for v in near)-min(v[2] for v in near),.035);self.assertIn('NeckInsert',self.info['components'])
