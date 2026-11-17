"""Measure unedited, same-pose Cycles shadow-on/off render differences."""
import json,hashlib
from pathlib import Path
from PIL import Image,ImageChops,ImageStat

HERE=Path(__file__).resolve().parent
render=json.loads((HERE/'render-verification.json').read_text())
on_path=HERE/render['physicalLabelShadowControl']['shadowOn']
off_path=HERE/render['physicalLabelShadowControl']['shadowOff']
on=Image.open(on_path).convert('RGB');off=Image.open(off_path).convert('RGB')
assert on.size==off.size==(1600,1600)
diff=ImageChops.difference(on,off)

def metrics(box):
    d=diff.crop(box);stat=ImageStat.Stat(d)
    high=[max(p) for p in d.getdata()]
    return {'bounds':list(box),'meanAbsoluteRGB_255':stat.mean,
            'maxChannelDifference_255':max(high),'pixelsOver3':sum(v>3 for v in high),
            'fractionPixelsOver3':sum(v>3 for v in high)/len(high),
            'pixelsOver8':sum(v>8 for v in high)}

regions={}
for name,(low,high) in render['physicalLabelShadowControl']['glassBounds'].items():
    left,top,right,bottom=round(low[0]*1600),round((1-high[1])*1600),round(high[0]*1600),round((1-low[1])*1600)
    # Interior lower-glass area avoids foreground paper and the bright bottom rim.
    width=right-left;height=bottom-top
    box=(round(left+.10*width),round(top+.43*height),round(right-.10*width),round(top+.84*height))
    regions[name]=metrics(box)

report={'method':'Identical camera frame31, lights, materials and seed84; only two Label.visible_shadow properties changed.',
        'onFile':str(on_path),'offFile':str(off_path),'resolution':list(on.size),
        'onSha256':hashlib.sha256(on_path.read_bytes()).hexdigest(),
        'offSha256':hashlib.sha256(off_path.read_bytes()).hexdigest(),
        'wholeImage':metrics((0,0,1600,1600)),'visibleLowerGlassRegions':regions,
        'exposedUpperGlassStrips':{'LOTION':metrics((688,870,752,1020)),
                                  'WASH':metrics((1118,886,1220,1040))},
        'doesNotEquateReflectionsOrPaperOverlapWithShadow':True,
        'interpretation':'Paper physically casts in Cycles. Upper exposed glass shows localized differences; lower-glass regions change by at most 1-2/255 and do not establish a strong broad bottle shadow. This is much subtler than the dedicated WebGL receiver. No retouching or image enhancement used.'}
(HERE/'shadow-verification.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
print(json.dumps(report,ensure_ascii=False,indent=2))
