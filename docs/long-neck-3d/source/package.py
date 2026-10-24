"""Assemble and validate the offline viewer after Vite and Blender builds."""
from pathlib import Path
import base64, json, struct, hashlib
BASE=Path(__file__).resolve().parents[1]
raw=(BASE/'assets/liaose-pump.glb').read_bytes()
magic,version,size=struct.unpack_from('<4sII',raw);assert(magic,version,size)==(b'glTF',2,len(raw))
length,kind=struct.unpack_from('<II',raw,12);assert kind==0x4e4f534a
gltf=json.loads(raw[20:20+length]);names={n['name'] for n in gltf['nodes']}
assert {'Bottle','Curved dispensing spout','Front liaose print','Press pad'}<=names
assert {'BottleAssembly','Closure','PumpStem','PumpHead','LogoPrint'}<=names
logo_group=next(n for n in gltf['nodes'] if n['name']=='LogoPrint')
assert len(logo_group['children'])==1 and gltf['nodes'][logo_group['children'][0]]['name']=='Front liaose print'
assert sum(n['name']=='Front liaose print' for n in gltf['nodes'])==1, 'The logo must move, not duplicate'
assert len(gltf['scenes'][gltf.get('scene',0)]['nodes'])==5, 'Five independent layers required'
assert all('uri' not in item for item in gltf.get('images',[])+gltf.get('buffers',[])), 'Model must be self-contained'
assert len(gltf['meshes'])>70 and len(gltf['materials'])>=4
html=(BASE/'source/template.html').read_text()
for key,path in [('__LOGO__','assets/liaose.svg'),('__MODEL__','assets/liaose-pump.glb')]:html=html.replace(key,base64.b64encode((BASE/path).read_bytes()).decode())
html=html.replace('__SCRIPT__',(BASE/'build/viewer.js').read_text().replace('</script','<\\/script'))
assert '__MODEL__' not in html and '<script src=' not in html and '<link' not in html
html='\n'.join(line.rstrip() for line in html.splitlines())+'\n'
(BASE/'index.html').write_text(html)
report={'modelSha256':hashlib.sha256(raw).hexdigest(),'bytes':len(raw),'meshes':len(gltf['meshes']),'materials':len(gltf['materials']),'embeddedTextures':len(gltf.get('images',[])),'offlineHTMLBytes':len(html.encode()),'externalModelResources':False,'geometryValidation':'passed','productionDimensions':False}
(BASE/'verification.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report))
