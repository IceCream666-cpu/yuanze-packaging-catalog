"""Split the existing vector artwork into a fixed label and movable print.
Run against the approved pre-split GLB; mesh accessors and other materials stay unchanged.
"""
import copy,json,struct,sys
from pathlib import Path
source,target=map(Path,sys.argv[1:3]);base=Path(__file__).resolve().parent
raw=source.read_bytes();length=struct.unpack_from('<I',raw,12)[0];g=json.loads(raw[20:20+length]);binary=bytearray(raw[28+length:])
assert len(g['nodes'])==12 and g['nodes'][3]['mesh']==3
# Remove the old artwork and relocate subsequent views without changing their bytes.
old=g['bufferViews'][g['images'][0]['bufferView']];assert old['byteOffset']+old['byteLength']<=len(binary)
size=(old['byteLength']+3)//4*4
binary=binary[:old['byteOffset']]+binary[old['byteOffset']+size:]
for view in g['bufferViews']:
 if view['byteOffset']>old['byteOffset']:view['byteOffset']-=size
old['byteOffset']=0;old['byteLength']=4
g['images']=[];g['textures']=[]
for name in ('label-without-logo','logo-only'):
 data=(base/(name+'.webp')).read_bytes();binary.extend(b'\0'*(-len(binary)%4));view=len(g['bufferViews'])
 g['bufferViews'].append({'buffer':0,'byteOffset':len(binary),'byteLength':len(data)});binary.extend(data)
 g['images'].append({'bufferView':view,'mimeType':'image/webp','name':name})
 g['textures'].append({'sampler':0,'extensions':{'EXT_texture_webp':{'source':len(g['images'])-1}}})
m=copy.deepcopy(g['materials'][1]);m['name']='LogoPrintInk';m['doubleSided']=True;m['pbrMetallicRoughness']['baseColorTexture']['index']=1;g['materials'].append(m)
mesh=copy.deepcopy(g['meshes'][3]);mesh['name']='Independent logo print';mesh['primitives'][0]['material']=len(g['materials'])-1;g['meshes'].append(mesh)
node=copy.deepcopy(g['nodes'][3]);node.update(name='LogoPrint',mesh=len(g['meshes'])-1,translation=[0,0,.000025]);g['nodes'].append(node)
# Jar root has no transform: the print can be a sibling with the same local UV surface.
assert not ({'translation','rotation','scale','matrix'} & set(g['nodes'][4]))
g['scenes'][g.get('scene',0)]['nodes'].append(len(g['nodes'])-1)
g['buffers'][0]['byteLength']=len(binary);binary.extend(b'\0'*(-len(binary)%4))
j=json.dumps(g,separators=(',',':')).encode();j+=b' '*(-len(j)%4)
out=struct.pack('<4sII',b'glTF',2,28+len(j)+len(binary))+struct.pack('<II',len(j),0x4e4f534a)+j+struct.pack('<II',len(binary),0x004e4942)+binary
target.write_bytes(out);print('Written',target,len(out))
