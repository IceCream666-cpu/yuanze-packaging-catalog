"""Measure original same-pose Cycles frames; change no raster pixels."""
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
    region=diff.crop(box);values=list(region.getdata());high=[max(p) for p in values]
    return {'bounds':list(box),'meanAbsoluteRGB_255':ImageStat.Stat(region).mean,
            'maxChannelDifference_255':max(high),'pixelsOver3':sum(v>3 for v in high),
            'fractionPixelsOver3':sum(v>3 for v in high)/len(high),'pixelsOver8':sum(v>8 for v in high)}
report={'method':'Identical final frame31, camera, light, ground, material and seed82; only the thin opaque blue stripe object visible_shadow flag changed.',
        'onFile':str(on_path),'offFile':str(off_path),'resolution':list(on.size),
        'onSha256':hashlib.sha256(on_path.read_bytes()).hexdigest(),
        'offSha256':hashlib.sha256(off_path.read_bytes()).hexdigest(),
        'wholeImage':metrics((0,0,1600,1600)),
        'unprintedTubeUpperROI':metrics((665,425,875,720)),
        'unprintedTubeLowerROI':metrics((650,900,680,1160)),
        'bottleNegativeControlROI':metrics((1100,760,1390,1290)),
        'doesNotEquateVisibleBlueStripesOrGroundShadowWithBodyShadow':True,
        'physicalCaster':'Pale blue pinstripes | thin solid direct-print decoration',
        'noPaperLabelOrOpaqueTransparentCarrier':True,
        'interpretation':'This comparison isolates thin direct-print decoration shadowing. The two unprinted tube regions exclude blue stripes and floating typography; the undecorated right bottle is a negative control. Web shadow-map differences are evaluated independently.'}
(HERE/'shadow-verification.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
print(json.dumps(report,ensure_ascii=False,indent=2))
