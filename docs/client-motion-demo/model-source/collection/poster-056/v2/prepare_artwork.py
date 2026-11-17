"""Keep the approved 056 lettering intact while separating its two print layers."""
from pathlib import Path
import copy
import hashlib
import json
import xml.etree.ElementTree as ET

HERE=Path(__file__).resolve().parent
ET.register_namespace('', 'http://www.w3.org/2000/svg')
original=(HERE.parent/'print.svg').read_bytes()
(HERE/'print-original.svg').write_bytes(original)
(HERE/'label-original.svg').write_bytes((HERE.parent/'label.svg').read_bytes())
root=ET.fromstring(original)
children=list(root)
assert len(children)==2 and children[0].tag.endswith('}svg') and children[1].text=='GOLDEN FACE OIL'
for name,index in [('logo',0),('product',1)]:
    out=ET.Element(root.tag,root.attrib)
    out.append(copy.deepcopy(children[index]))
    ET.ElementTree(out).write(HERE/(name+'.svg'),encoding='utf-8',xml_declaration=True)
    assert ET.tostring(list(ET.parse(HERE/(name+'.svg')).getroot())[0])==ET.tostring(children[index])
(HERE/'artwork-verification.json').write_text(json.dumps({'sourceSha256':hashlib.sha256(original).hexdigest(),'originalVectorSubtreesPreserved':True,'originalViewBox':root.attrib['viewBox'],'logoColor':'#29301b','productCopy':'GOLDEN FACE OIL','productTypeface':children[1].attrib['font-family'],'rasterSize':[2048,1156],'surfaceInterpretation':'Reference is directly printed; transparent physical carrier is an exploded-layer illustration, not a paper label.'},indent=2)+'\n')
