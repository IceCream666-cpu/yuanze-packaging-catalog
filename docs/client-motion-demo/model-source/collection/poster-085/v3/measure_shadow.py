"""Read-only comparison of unedited Cycles shadow on/off renders."""
from pathlib import Path
import json,hashlib
import numpy as np
from PIL import Image
HERE=Path(__file__).resolve().parent
on=HERE/'previews/Daily-Hair-Blender-half.png';off=HERE/'previews/Daily-Hair-shadow-control.png'
a=np.asarray(Image.open(on).convert('RGB'),dtype=np.int16);b=np.asarray(Image.open(off).convert('RGB'),dtype=np.int16)
assert a.shape==b.shape==(1400,1400,3)
delta=np.max(np.abs(a-b),axis=2)
def metrics(box):
 x0,y0,x1,y1=box;d=delta[y0:y1,x0:x1]
 return {'roi':box,'pixelsAbove3':int((d>3).sum()),'maxChannelDifference':int(d.max()),'meanMaximumChannelDifference':float(d.mean())}
report={'method':'Same half-expanded pose/camera/lights/materials/ground/seed85; only the two physical decorative surfaces visible_shadow disabled in control. Original PNG pixels unedited.',
 'onImage':str(on),'offImage':str(off),'onSha256':hashlib.sha256(on.read_bytes()).hexdigest(),'offSha256':hashlib.sha256(off.read_bytes()).hexdigest(),
 'resolution':[1400,1400],'bareBottle':metrics([910,720,1010,1110]),'bareTube':metrics([605,850,625,1110]),
 'backgroundNegativeControl':metrics([20,100,250,500]),'wholeImageIncludesOtherSurfaces':metrics([0,0,1400,1400]),'sourceImagesUnedited':True}
assert report['bareBottle']['pixelsAbove3']>0 and report['bareTube']['pixelsAbove3']>0
(HERE/'shadow-verification.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
print(json.dumps(report,ensure_ascii=False,indent=2))
