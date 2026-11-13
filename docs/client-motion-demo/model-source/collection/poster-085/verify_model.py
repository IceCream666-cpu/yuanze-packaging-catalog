"""Check actual exported geometry, embedded resources and separation clearance."""
import hashlib, json, math, struct
from pathlib import Path

HERE = Path(__file__).resolve().parent
cfg = json.loads((HERE / 'review-product.json').read_text())
info = json.loads((HERE / 'model-info.json').read_text())
blob = (HERE.parents[2] / 'packaging-assets' / cfg['file']).read_bytes()
assert struct.unpack_from('<4sII', blob) == (b'glTF', 2, len(blob))
length, kind = struct.unpack_from('<I4s', blob, 12)
assert kind == b'JSON'
doc = json.loads(blob[20:20 + length])
bin_length, kind = struct.unpack_from('<I4s', blob, 20 + length)
binary = blob[28 + length:]
assert kind == b'BIN\0' and len(binary) == bin_length
nodes = doc['nodes']
groups = {n['name']: n for n in nodes if 'partKey' in n.get('extras', {})}
assert set(groups) == {'Body', 'Pump', 'TubeCap', 'Label', 'LogoInk', 'NameInk'}
assert {p['node'] for p in cfg['parts']} == set(groups)
children = {k: [nodes[i]['name'] for i in n['children']] for k, n in groups.items()}
assert len(children['Pump']) == 6 and len(children['TubeCap']) == 3
assert len(children['Label']) == len(children['LogoInk']) == len(children['NameInk']) == 2
assert not info['containsFormula'] and not info['paperLabel']
assert all('liquid' not in n.get('name', '').lower() for n in nodes)
assert .67 < info['tubeHeight'] / info['bottleWithPumpHeight'] < .71
pipe = next(n for n in nodes if n['name'].startswith('Long clear hollow dip tube'))
assert nodes.index(pipe) in groups['Pump']['children']
accessor = doc['accessors'][doc['meshes'][pipe['mesh']]['primitives'][0]['attributes']['POSITION']]
pipe_y = [accessor[k][1] + pipe.get('translation', [0, 0, 0])[1] + groups['Pump']['translation'][1] for k in ['min', 'max']]
assert .11 < pipe_y[0] < .15 and math.isclose(pipe_y[1], 2.61, abs_tol=1e-4)
assert 0 < pipe_y[0] - info['suctionTube']['containerInnerFloorZ'] < .03
offsets = cfg['review']['explosion']['offsets']
clearance = pipe_y[0] + offsets['pump'][1] - info['componentBoundsBlenderXYZ']['Body']['max'][2]
assert clearance > .2, 'Fully expanded suction pipe must clear the bottle neck'
assert offsets['print'][2] > offsets['logo'][2] > offsets['label'][2] > 0
assert len(doc['images']) == 3
for im in doc['images']:
    assert 'uri' not in im and im['mimeType'] == 'image/png'
    view = doc['bufferViews'][im['bufferView']]
    start = view.get('byteOffset', 0)
    assert binary[start:start + 8] == b'\x89PNG\r\n\x1a\n'
assert all('uri' not in b for b in doc['buffers'])
ivory = next(m for m in doc['materials'] if m['name'] == 'Warm ivory satin molded polymer')
assert ivory['pbrMetallicRoughness']['baseColorFactor'][3] == 1
pipe_mat = next(m for m in doc['materials'] if m['name'] == 'Transparent hollow polyethylene suction tube')
assert pipe_mat['alphaMode'] == 'BLEND'
blend = HERE / 'poster-085-v1.blend'
report = {'glbSha256': hashlib.sha256(blob).hexdigest(), 'blendSha256': hashlib.sha256(blend.read_bytes()).hexdigest(),
          'glbBytes': len(blob), 'blendBytes': blend.stat().st_size, 'meshes': len(doc['meshes']),
          'triangles': sum(doc['accessors'][p['indices']]['count'] // 3 for m in doc['meshes'] for p in m['primitives']),
          'groups': children, 'pipeBoundsY': pipe_y, 'expandedPipeClearance': clearance,
          'noFormula': True, 'embeddedImages': len(doc['images']), 'scope': 'Actual exported local model; not manufacturing validation'}
(HERE / 'model-verification.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
print(json.dumps({k: v for k, v in report.items() if k != 'groups'}, indent=2))
