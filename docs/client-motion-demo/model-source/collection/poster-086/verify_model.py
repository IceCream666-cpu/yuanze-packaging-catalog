"""Inspect the actual embedded GLB, part hierarchy, proportions and release isolation."""
from pathlib import Path
import json,struct,hashlib,math
HERE=Path(__file__).resolve().parent
CLIENT=HERE.parents[2]
cfg=json.loads((HERE/'review-product.json').read_text());info=json.loads((HERE/'model-info.json').read_text())
blob=(CLIENT/'packaging-assets'/cfg['file']).read_bytes()
assert struct.unpack_from('<4sII',blob)==(b'glTF',2,len(blob))
length,kind=struct.unpack_from('<I4s',blob,12);assert kind==b'JSON'
doc=json.loads(blob[20:20+length]);binary=blob[28+length:]
assert struct.unpack_from('<I4s',blob,20+length)==(len(binary),b'BIN\0')
nodes=doc['nodes'];groups={n['name']:n for n in nodes if 'partKey' in n.get('extras',{})}
assert set(groups)=={'Body','Cap','Label','LogoInk','NameInk'}=={p['node'] for p in cfg['parts']}
assert len(groups['Cap']['children'])==2
assert len(groups['Label']['children'])==len(groups['LogoInk']['children'])==len(groups['NameInk']['children'])==1
bounds={}
for key,g in groups.items():
 positions=[]
 for child in g['children']:
  n=nodes[child];a=doc['accessors'][doc['meshes'][n['mesh']]['primitives'][0]['attributes']['POSITION']]
  for side in ['min','max']:positions.append([a[side][j]+n.get('translation',[0,0,0])[j]+g.get('translation',[0,0,0])[j] for j in range(3)])
 bounds[key]={'min':[min(p[j] for p in positions) for j in range(3)],'max':[max(p[j] for p in positions) for j in range(3)]}
assert math.isclose(bounds['Cap']['max'][1],4.4,abs_tol=1e-5)
assert math.isclose(bounds['Body']['max'][0]-bounds['Body']['min'][0],1,abs_tol=1e-5)
off=cfg['review']['explosion']['offsets']
assert bounds['Cap']['min'][1]+off['cap'][1]-bounds['Body']['max'][1]>1.2
assert off['print'][2]>off['logo'][2]>off['label'][2]>0
assert cfg['review']['appearance']['labelShadows'] is True
assert not info['containsFormula'] and info['illustrativeDimensions']
assert len(doc['images'])==2
for im in doc['images']:
 assert 'uri' not in im and im['mimeType']=='image/png';v=doc['bufferViews'][im['bufferView']];start=v.get('byteOffset',0);assert binary[start:start+8]==b'\x89PNG\r\n\x1a\n'
assert all('uri' not in b for b in doc['buffers'])
label=next(m for m in doc['materials'] if m['name'].startswith('Copper brown'))
assert label.get('alphaMode','OPAQUE')=='OPAQUE' and label['pbrMetallicRoughness']['metallicFactor']>.5
for n in ['logo printed ink','name printed ink']:
 m=next(m for m in doc['materials'] if m['name']==n);assert m['alphaMode']=='BLEND'
registered=json.loads((CLIENT/'src/structure/collection-products.json').read_text());assert 'poster-086' not in registered
assert all(x['id']!='poster-086' for x in json.loads((CLIENT/'src/featured.json').read_text()))
assert 'assets/packaging/poster-086-v1.glb' not in json.loads((CLIENT.parents[1]/'server-reference/public/showroom/bundle-manifest.json').read_text())['files']
blend=HERE/'poster-086-v1.blend'
report=dict(glbSha256=hashlib.sha256(blob).hexdigest(),blendSha256=hashlib.sha256(blend.read_bytes()).hexdigest(),glbBytes=len(blob),blendBytes=blend.stat().st_size,groups=list(groups),bounds=bounds,meshes=len(doc['meshes']),embeddedImages=2,layerOrderVerified=True,completeCap=True,localOnlyModel=True)
(HERE/'model-verification.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
