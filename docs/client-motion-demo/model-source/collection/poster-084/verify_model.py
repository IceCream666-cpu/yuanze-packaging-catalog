import json,struct
from pathlib import Path
p=Path(__file__).resolve().parent
raw=(p.parents[2]/'packaging-assets/poster-084-v2.glb').read_bytes()
assert raw[:4]==b'glTF' and struct.unpack_from('<I',raw,8)[0]==len(raw)
n=struct.unpack_from('<I',raw,12)[0];g=json.loads(raw[20:20+n]);nodes={x.get('name'):x for x in g['nodes']}
assert all(k in nodes for k in ['Body','Pump','Label','LogoInk','NameInk'])
assert len(nodes['Pump']['children'])>190
assert sum('dip tube' in (x.get('name','')) for x in g['nodes'])==2
assert not any('liquid' in x.get('name','').lower() for x in g['nodes'])
c=json.loads((p/'review-product.json').read_text());e=c['review']['explosion']
assert e['offsets']['print'][2]>e['offsets']['logo'][2]>e['offsets']['label'][2]
assert (p/'poster-084-v2.blend').stat().st_size>100000
print('GLB structure, two pump tubes, ink layers and Blender source verified')

for child in nodes["Body"]["children"]:
 node=g["nodes"][child]
 for prim in g["meshes"][node["mesh"]]["primitives"]:
  m=g["materials"][prim["material"]]
  assert m["extensions"]["KHR_materials_transmission"]["transmissionFactor"]==1
  assert m["pbrMetallicRoughness"].get("baseColorFactor",[1,1,1,1])==[1,1,1,1]
  assert m["pbrMetallicRoughness"]["roughnessFactor"]<.06
assert c["review"]["appearance"]["glass"] and not c["review"]["appearance"]["frosted"]
print("Both bottles are neutral clear glass; no colored contents")
