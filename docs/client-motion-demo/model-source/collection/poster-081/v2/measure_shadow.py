"""Measure unedited, identical-pose Cycles textile-shadow control renders."""
import hashlib,json
from pathlib import Path
from PIL import Image,ImageChops,ImageStat

HERE=Path(__file__).resolve().parent
render=json.loads((HERE/'render-verification.json').read_text())
control=render['physicalLabelShadowControl']
on_path=HERE/control['shadowOn'];off_path=HERE/control['shadowOff']
on=Image.open(on_path).convert('RGB');off=Image.open(off_path).convert('RGB')
assert on.size==off.size==(1600,1600)
diff=ImageChops.difference(on,off)
def metrics(box):
    region=diff.crop(box);stat=ImageStat.Stat(region);high=[max(p) for p in region.getdata()]
    return {'bounds':list(box),'meanAbsoluteRGB_255':stat.mean,'maxChannelDifference_255':max(high),
            'pixelsOver3':sum(v>3 for v in high),'fractionPixelsOver3':sum(v>3 for v in high)/len(high),
            'pixelsOver8':sum(v>8 for v in high)}

# Fixed review rectangles selected on the final 1600-pixel frame31.
# Foreground fabric occupies x475..1039,y870..1264 and is excluded here.
regions={'rightExposedGlass':metrics((1060,920,1190,1290)),
         'lowerExposedGlass':metrics((800,1275,1180,1335)),
         'upperExposedGlass':metrics((840,839,1170,865))}
report={'method':'Identical camera frame31, light, material and seed81; only two physical textile visible_shadow flags changed.',
        'onFile':str(on_path),'offFile':str(off_path),'resolution':list(on.size),
        'onSha256':hashlib.sha256(on_path.read_bytes()).hexdigest(),
        'offSha256':hashlib.sha256(off_path.read_bytes()).hexdigest(),
        'wholeImage':metrics((0,0,1600,1600)),'exposedGlassRegions':regions,
        'doesNotEquateClothOverlapOrReflectionsWithShadow':True,
        'motionLimitation':'Frame31 is a layered comparison pose with a rigid circular sleeve, not a collision-free physical removal path. Fully expanded pose has independently measured positive radial clearance.',
        'interpretation':'The pair isolates the physical textile shadow flag. Read the exposed-glass region differences separately from cloth self-shadow and ground shadow; the WebGL receiver is evaluated independently.'}
(HERE/'shadow-verification.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
print(json.dumps(report,ensure_ascii=False,indent=2))
