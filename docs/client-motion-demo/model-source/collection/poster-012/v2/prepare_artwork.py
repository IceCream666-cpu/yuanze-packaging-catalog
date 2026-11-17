"""Split the existing vector artwork without redrawing any printed path."""
from pathlib import Path
import copy
import hashlib
import json
import xml.etree.ElementTree as ET

HERE = Path(__file__).resolve().parent
SOURCE = HERE.parents[2] / 'beach-magic/front.svg'
ET.register_namespace('', 'http://www.w3.org/2000/svg')
original = SOURCE.read_bytes()
(HERE / 'front-original.svg').write_bytes(original)
root = ET.fromstring(original)
children = list(root)
assert len(children) == 10
assert children[6].attrib['aria-label'] == 'BEACH MAGIC'
assert children[7].attrib['aria-label'] == 'SUGAR SCRUB'
assert children[9].attrib['aria-label'] == 'YELLOW + PINK BODY POLISH'
assert children[3].attrib['rx'] == '130'
selections = {'paper': [0, 1, 2, 3, 4], 'logo': [0, 1, 2, 5], 'product': [0, 1, 2, 6, 7, 8, 9]}
for name, indices in selections.items():
    plate = ET.Element(root.tag, root.attrib)
    for i in indices:
        plate.append(copy.deepcopy(children[i]))
    ET.ElementTree(plate).write(HERE / (name + '.svg'), encoding='utf-8', xml_declaration=True)
    # Compare full vector subtrees, including every path, fill, and transform.
    reread = ET.parse(HERE / (name + '.svg')).getroot()
    assert [ET.tostring(e) for e in reread] == [ET.tostring(children[i]) for i in indices]
manifest = {
    'source': str(SOURCE), 'sourceSha256': hashlib.sha256(original).hexdigest(),
    'viewBox': root.attrib['viewBox'], 'rasterSize': [2048, 1280],
    'layers': {name: {'sourceChildIndices': ids, 'pathCount': sum(1 for i in ids for e in children[i].iter() if e.tag.endswith('}path'))} for name, ids in selections.items()},
    'allSelectedVectorSubtreesUnchanged': True,
}
(HERE / 'artwork-verification.json').write_text(json.dumps(manifest, indent=2) + '\n')
