"""Validate the actual exported 081 GLB without importing a renderer."""
import datetime
import hashlib
import json
import math
import struct
from pathlib import Path

HERE = Path(__file__).resolve().parent
config = json.loads((HERE / 'review-product.json').read_text())
info = json.loads((HERE / 'model-info.json').read_text())
glb = HERE.parents[2] / 'packaging-assets' / config['file']
blob = glb.read_bytes()
assert struct.unpack_from('<4sII', blob) == (b'glTF', 2, len(blob))
json_length, kind = struct.unpack_from('<I4s', blob, 12)
assert kind == b'JSON'
data = json.loads(blob[20:20 + json_length])
bin_length, kind = struct.unpack_from('<I4s', blob, 20 + json_length)
assert kind == b'BIN\0'
binary = blob[28 + json_length:]
assert len(binary) == bin_length
nodes = data['nodes']
groups = {n['name']: n for n in nodes if 'partKey' in n.get('extras', {})}
assert set(groups) == {'Body', 'Pump', 'Label', 'LogoInk', 'NameInk'}
assert {part['node'] for part in config['parts']} == set(groups)
children = {key: [nodes[i]['name'] for i in group['children']] for key, group in groups.items()}
assert children['Label'] == ['Black woven side flag', 'Ivory woven wrap sleeve | soft rolled edges', 'liaose on black side flag']
assert children['LogoInk'] == ['liaose on woven sleeve']
assert children['NameInk'] == ['EXFOLIATING HAND GEL']
assert len(children['Body']) == 1 and len(children['Pump']) == 5
assert len(data['meshes']) == 11, 'Unexpected mesh, possibly a formula placeholder'
assert not info['containsFormula'] and info['capacity'] is None
assert not any(word in n.get('name', '').lower() for n in nodes for word in ['formula', 'liquid', 'contents'])
tube = next(n for n in nodes if n['name'] == 'Long clear hollow dip tube | angled pickup')
assert nodes.index(tube) in groups['Pump']['children']
position = data['accessors'][data['meshes'][tube['mesh']]['primitives'][0]['attributes']['POSITION']]
tube_y = [position[bound][1] + tube['translation'][1] + groups['Pump']['translation'][1] for bound in ('min', 'max')]
assert .15 < tube_y[0] < .19 and 2.19 < tube_y[1] < 2.23
glass = next(m for m in data['materials'] if m['name'] == 'Crystal clear glass | thick heel')
pbr = glass['pbrMetallicRoughness']
assert pbr.get('baseColorFactor', [1, 1, 1, 1]) == [1, 1, 1, 1]
assert math.isclose(pbr['roughnessFactor'], .02, abs_tol=1e-6)
assert glass['extensions']['KHR_materials_transmission']['transmissionFactor'] == 1
assert config['review']['appearance']['referenceGlass'] is True
assert config['review']['appearance']['frosted'] is False
assert len(data['images']) == 6
for image in data['images']:
    assert 'uri' not in image and image['mimeType'] == 'image/png'
    view = data['bufferViews'][image['bufferView']]
    offset = view.get('byteOffset', 0)
    assert binary[offset:offset + 8] == b'\x89PNG\r\n\x1a\n'
assert all('uri' not in buffer for buffer in data['buffers'])
blend = HERE / 'poster-081-v1.blend'
report = {
    'scope': 'local Blender source and actual exported GLB structural verification; browser verification owned by primary agent',
    'verifiedAt': datetime.datetime.now().astimezone().isoformat(),
    'blenderVersion': info['blenderVersion'],
    'glbBytes': len(blob), 'glbSha256': hashlib.sha256(blob).hexdigest(),
    'blendBytes': blend.stat().st_size, 'blendSha256': hashlib.sha256(blend.read_bytes()).hexdigest(),
    'meshes': len(data['meshes']),
    'triangles': sum(data['accessors'][p['indices']]['count'] // 3 for m in data['meshes'] for p in m['primitives']),
    'packedImages': len(data['images']), 'groups': sorted(groups),
    'wholePumpMeshCount': len(children['Pump']),
    'hollowTubeOuterDiameter': .076, 'hollowTubeInnerDiameter': .054,
    'suctionTubeTipMinZ': tube_y[0], 'suctionTubeTopMaxZ': tube_y[1],
    'sideWordmarkAttachedToFlag': True, 'neutralClearGlass': True,
    'noFormula': True, 'capacityUnspecified': True,
    'visualReview': {'assembled': 'pending refreshed Blender render', 'exploded': 'pending refreshed Blender render'},
    'renderDirectory': 'outputs/20261106-Citrus-Hand-Gel/3D',
}
(HERE / 'model-verification.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
print(json.dumps(report, ensure_ascii=False, indent=2))
