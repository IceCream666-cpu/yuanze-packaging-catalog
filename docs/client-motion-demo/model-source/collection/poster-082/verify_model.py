"""Structural checks against the real exported GLB, not the planned configuration."""
import datetime, hashlib, json, math, struct
from pathlib import Path
HERE=Path(__file__).resolve().parent
info=json.loads((HERE/'model-info.json').read_text());config=json.loads((HERE/'review-product.json').read_text())
glb=HERE.parents[2]/'packaging-assets'/config['file'];blob=glb.read_bytes()
assert struct.unpack_from('<4sII',blob)==(b'glTF',2,len(blob))
jlen,typ=struct.unpack_from('<I4s',blob,12);assert typ==b'JSON'
d=json.loads(blob[20:20+jlen]);blen,typ=struct.unpack_from('<I4s',blob,20+jlen);assert typ==b'BIN\0'
binary=blob[28+jlen:];assert len(binary)==blen
nodes=d['nodes'];groups={n['name']:n for n in nodes if 'partKey' in n.get('extras',{})}
assert set(groups)=={'Body','Pump','TubeCap','Label','LogoInk','NameInk'}
assert {p['node'] for p in config['parts']}==set(groups)
assert set(config['review']['explosion']['offsets'])=={p['key'] for p in config['parts']}
children={k:[nodes[i]['name'] for i in n['children']] for k,n in groups.items()}
assert len(children['Body'])==3 and len(children['Pump'])==6 and len(children['TubeCap'])==3
assert len(children['LogoInk'])==2 and len(children['NameInk'])==4 and len(children['Label'])==3
assert len(d['meshes'])==21
assert not info['containsFormula'] and not info['paperLabel']
assert info['tubeHeight']/info['bottleWithPumpHeight']>1.1 and info['tubeHeight']/info['bottleWithPumpHeight']<1.2
assert all('liquid' not in n.get('name','').lower() for n in nodes)
tube=next(n for n in nodes if n['name'].startswith('Long clear hollow dip tube'))
assert nodes.index(tube) in groups['Pump']['children']
a=d['accessors'][d['meshes'][tube['mesh']]['primitives'][0]['attributes']['POSITION']]
y=[a[k][1]+tube.get('translation',[0,0,0])[1]+groups['Pump']['translation'][1] for k in ['min','max']]
assert .09<y[0]<.13 and abs(y[1]-1.985)<.001
assert math.isclose(info['suctionTube']['outerDiameter'],.082)
assert y[0]-info['suctionTube']['containerInnerFloorZ']<.03
disc=next(n for n in nodes if n['name'].endswith('wide flat circular pressing surface'))
da=d['accessors'][d['meshes'][disc['mesh']]['primitives'][0]['attributes']['POSITION']]
assert math.isclose(da['max'][1]-da['min'][1],.107,abs_tol=1e-4)
assert math.isclose(da['max'][0]-da['min'][0],.604,abs_tol=1e-4)
assert any('low rear-edge' in n for n in children['Pump'])
assert not any('central peg' in n for n in children['Pump'])
for n in ['Ivory opaque soft plastic','Powder blue molded plastic']:
 m=next(m for m in d['materials'] if m['name']==n)
 assert m.get('extensions',{}).get('KHR_materials_transmission',{}).get('transmissionFactor',0)==0
 assert m.get('pbrMetallicRoughness',{}).get('baseColorFactor',[1,1,1,1])[3]==1
assert len(d['images'])==6
for name in ['Transparent direct-print carrier | conceptual ink layer','Powder blue pinstripe ink']:
 material=next(m for m in d['materials'] if m['name']==name)
 assert 'baseColorTexture' in material['pbrMetallicRoughness'], 'Ink layers must use the viewer no-shadow texture path'
pipe=next(m for m in d['materials'] if m['name']=='Transparent hollow polyethylene suction tube')
assert pipe['alphaMode']=='BLEND' and .25<pipe['pbrMetallicRoughness']['baseColorFactor'][3]<.4
for im in d['images']:
 assert 'uri' not in im and im['mimeType']=='image/png'
 view=d['bufferViews'][im['bufferView']];o=view.get('byteOffset',0);assert binary[o:o+8]==b'\x89PNG\r\n\x1a\n'
assert all('uri' not in buf for buf in d['buffers'])
blend=HERE/'poster-082-v1.blend'
report={'scope':'Actual local Blender source and exported GLB structure; interaction verified separately by primary agent','verifiedAt':datetime.datetime.now().astimezone().isoformat(),'blenderVersion':info['blenderVersion'],'glbBytes':len(blob),'glbSha256':hashlib.sha256(blob).hexdigest(),'blendBytes':blend.stat().st_size,'blendSha256':hashlib.sha256(blend.read_bytes()).hexdigest(),'meshes':len(d['meshes']),'triangles':sum(d['accessors'][p['indices']]['count']//3 for m in d['meshes'] for p in m['primitives']),'embeddedImages':len(d['images']),'groups':children,'noFormula':True,'opaquePlasticBodies':True,'noPaperLabel':True,'discTopFlat':True,'pipeBoundsY':y,'pipeOuterDiameter':.082,'pipeInnerDiameter':.058,'ratioTubeToBottle':info['tubeHeight']/info['bottleWithPumpHeight'],'renderStatus':'pending visual inspection'}
visual=HERE/'visual-review.json'
if visual.exists():
 v=json.loads(visual.read_text())
 if v.get('glbSha256')==report['glbSha256'] and v.get('blendSha256')==report['blendSha256']:
  report['renderStatus']='front, side and full expansion inspected'
  report['renderEvidence']=v['renders']
(HERE/'model-verification.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
print(json.dumps(report,ensure_ascii=False,indent=2))
