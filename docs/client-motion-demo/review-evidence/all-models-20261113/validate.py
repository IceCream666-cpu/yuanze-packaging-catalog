"""Check audit coverage and links without changing model or release assets."""
from pathlib import Path
from html.parser import HTMLParser
from collections import Counter
import hashlib,json,math,struct
HERE=Path(__file__).resolve().parent
CLIENT=HERE.parents[1]
rows=json.loads((HERE/'findings.json').read_text())
assert len(rows)==32 and len({p['id'] for p in rows})==32
assert Counter(p['priority'] for p in rows)=={'优先':5,'第二轮':19,'保留主体':8}
for row in rows:
    blob=(CLIENT/'packaging-assets'/row['file']).read_bytes()
    assert hashlib.sha256(blob).hexdigest()==row['sha256'],row['id']
    states=json.loads((HERE/'screenshots'/(row['id']+'-states.json')).read_text())
    assert [s['name']for s in states]==['closed','half','expanded','rotated']
    for state,progress in zip(states,[0,.5,1,1]):
        assert abs(state['renderedProgress']-progress)<.001,row['id']
        assert state['triangles']>0
        png=HERE/'screenshots'/(row['id']+'-'+state['name']+'.png')
        assert png.read_bytes()[:8]==b'\x89PNG\r\n\x1a\n'
    assert abs(states[-1]['yaw']-math.pi/2)<.001
class Links(HTMLParser):
    def handle_starttag(self,tag,attrs):
        for k,v in attrs:
            if k in ('src','href') and v and not v.startswith('#'):
                if v!='validation.json':assert (HERE/v).is_file(),v
Links().feed((HERE/'index.html').read_text())
result={'reportDate':'2026-11-17','captureDate':'2026-11-13','modelCount':32,'mainScreenshots':128,'all32LocalHashesUnchanged':True,'priorities':dict(Counter(p['priority']for p in rows)),'productionFilesModified':False,'liveRecheckOnReportDate':False,'browserVariantsNotVisuallyChecked':['poster-080/after','poster-080/baby'],'limitations':['No physical measurements','No mobile-device or performance testing','No all-source Blender re-render','Unified audit viewport is not complete product-page QA']}
(HERE/'validation.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
print(json.dumps(result,ensure_ascii=False))
