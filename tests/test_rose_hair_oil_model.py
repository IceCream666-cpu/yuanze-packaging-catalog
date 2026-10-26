import unittest
from tests.tail_model_checks import TailChecks
class RoseHairOilModelTests(TailChecks,unittest.TestCase):
 ID='poster-066';RATIO=1.77;GROUPS=['Body','Closure','PumpStem','Actuator','Overcap','PaperLabel','LogoPrint'];TEXT=['ROSE HAIR OIL','120 ml']
 def test_original_rose_artwork_is_retained_without_old_black_letters(self):
  self.load()
  from PIL import Image
  im=Image.open(self.source/'floral.png').convert('RGBA');colors=list(im.get_flattened_data());self.assertGreater(sum(a>128 and r>g*1.18 for r,g,b,a in colors),1000);self.assertLess(sum(a>128 and max(r,g,b)<100 for r,g,b,a in colors),15)
