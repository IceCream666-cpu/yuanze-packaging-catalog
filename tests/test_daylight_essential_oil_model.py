import unittest
from tests.tail_model_checks import TailChecks
class DaylightEssentialOilModelTests(TailChecks,unittest.TestCase):
 ID='poster-070';RATIO=1.39;GROUPS=['Body','Closure','CapWrap','PaperLabel','LogoPrint'];TEXT=['DAYLIGHT','ESSENTIAL OIL']
 def test_frosted_cone_and_separate_embossed_wrap(self):
  self.load();self.assertTrue(self.config['appearance']['frosted']);body=[self.g['materials'][p['material']] for i,p in self.meshes() if self.ancestor(i)=='Body'];self.assertTrue(all(.2<=m['pbrMetallicRoughness']['roughnessFactor']<=.3 for m in body));wrap=[self.g['materials'][p['material']] for i,p in self.meshes() if self.ancestor(i)=='CapWrap'];self.assertEqual(len(wrap),2);self.assertTrue(all('normalTexture' in m for m in wrap));self.assertNotIn('ml',(self.source/'print.svg').read_text().split('</svg>',1)[-1])
