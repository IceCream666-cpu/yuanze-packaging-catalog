"""Reopen actual source and check surfaces, real openings, UV/PBR and assembled motion."""
import bpy,bmesh,json,struct,hashlib,math
from pathlib import Path
from mathutils import Vector
from mathutils.kdtree import KDTree
HERE=Path(__file__).resolve().parent;OLD=HERE.parent;CLIENT=HERE.parents[3]
def points(o):return [o.matrix_world@v.co for v in o.data.vertices]
protected=['Empty tall cylinder | ivory rounded heel and hollow threaded neck',
 'Long clear hollow dip tube | near-bottom angled intake','Tube cap | lower hinged lid','Tube cap | rear hinge']
bpy.ops.wm.open_mainfile(filepath=str(OLD/'poster-085-v2.blend'))
bpy.context.scene.frame_set(1);bpy.context.view_layer.update()
original={n:points(bpy.data.objects[n]) for n in protected}
old_seal=[p for o in bpy.context.scene.objects if o.name=='Tube integrated flattened heat seal' or o.name.startswith('Tube seal ridge') for p in points(o)]
bpy.ops.wm.open_mainfile(filepath=str(HERE/'poster-085-v3.blend'))
scene=bpy.context.scene;scene.frame_set(1);bpy.context.view_layer.update()
cfg=json.loads((HERE/'review-product.json').read_text());roots={p['node']:bpy.data.objects[p['node']] for p in cfg['parts']}
assert {n:len(o.children) for n,o in roots.items()}=={'Body':3,'Pump':6,'TubeCap':3,'Label':2,'LogoInk':2,'NameInk':2}
meshes=[o for root in roots.values() for o in root.children_recursive if o.type=='MESH'];assert len(meshes)==18
assert all(not o.hide_render and len(o.data.materials)==1 and o.data.materials[0] for o in meshes)
errors={}
for n,ps in original.items():
 current=points(bpy.data.objects[n]);assert len(ps)==len(current)
 errors[n]=max((a-b).length for a,b in zip(ps,current));assert errors[n]==0
seal=bpy.data.objects['Tube heat seal | original 72 fine ridges merged']
seal_points=points(seal);assert len(old_seal)==len(seal_points)
tree=KDTree(len(seal_points))
for i,p in enumerate(seal_points):tree.insert(p,i)
tree.balance();matches=[tree.find(p) for p in old_seal]
seal_error=max(item[2] for item in matches)
assert seal_error<1e-6,('Original embossed ridge vertices changed',seal_error)
assert len({item[1] for item in matches})==len(seal_points),'Merged seal lost unique original vertices'
solids={};transparent=[]
for o in meshes:
 if o.parent.name in {'LogoInk','NameInk'}:
  assert not o.visible_shadow and o.data.uv_layers.active;transparent.append(o.name);continue
 bm=bmesh.new();bm.from_mesh(o.data);assert all(e.is_manifold for e in bm.edges),o.name
 vol=bm.calc_volume(signed=True);assert vol>0,(o.name,vol)
 remaining=set(bm.verts);components=0
 while remaining:
  components+=1;stack=[remaining.pop()]
  while stack:
   v=stack.pop()
   for edge in v.link_edges:
    q=edge.other_vert(v)
    if q in remaining:remaining.remove(q);stack.append(q)
 if o==seal:assert components==73,components
 solids[o.name]={'manifold':True,'positiveVolume':vol,'connectedComponents':components};bm.free()
assert len(solids)==14 and len(transparent)==4
for o in roots['Label'].children:
 assert o.visible_shadow and o.data.uv_layers.active and abs(o['nominalThickness']-.0009)<1e-8

def cast(o,p,d,distance):
 inv=o.matrix_world.inverted();hit,q,n,i=o.ray_cast(inv@Vector(p),(inv.to_3x3()@Vector(d)).normalized(),distance=distance)
 return hit,o.matrix_world@q if hit else None
tube=bpy.data.objects['Empty flexible tube | sealed tail and open dispensing nozzle']
bottle=bpy.data.objects['Empty tall cylinder | ivory rounded heel and hollow threaded neck']
dip=bpy.data.objects['Long clear hollow dip tube | near-bottom angled intake']
collar=bpy.data.objects['Pump | broad ivory shoulder collar'];stem=bpy.data.objects['Pump | actuator barrel and stem']
connector=bpy.data.objects['Pump | internal connector'];beak=bpy.data.objects['Pump | wide flattened beak actuator']
upper=bpy.data.objects['Tube cap | closure sleeve'];lower=bpy.data.objects['Tube cap | lower hinged lid']
assert not cast(tube,(-.72,0,.17),(0,0,1),2.02)[0],'Tube dispensing neck blocked'
assert cast(seal,(-.72,0,2.20),(0,0,1),.10)[0],'Heat seal fails to close tube end'
wall=[]
for z in [.45,.75,1.1,1.5,1.9]:
 hit,inner=cast(tube,(-.72,0,z),(0,-1,0),.25);assert hit
 hit,outer=cast(tube,inner+Vector((0,-.00001,0)),(0,-1,0),.025);assert hit
 thickness=(outer-inner).length;assert .010<thickness<.015,(z,thickness);wall.append({'z':z,'thickness':thickness})
assert not cast(collar,(.64,0,2.59),(0,0,1),.22)[0]
assert not cast(collar,(.64+.175,0,2.665),(0,0,1),.10)[0]
assert not cast(stem,(.64,0,2.74),(0,0,1),.46)[0]
assert not cast(stem,(.64+.175,0,2.76),(0,0,1),.035)[0]
assert not cast(connector,(.64,0,2.50),(0,0,1),.24)[0]
assert not cast(upper,(-.72,0,.10),(0,0,1),.25)[0]
assert cast(lower,(-.72,0,-.01),(0,0,1),.20)[0]
assert not cast(beak,(.04,0,3.18),(0,0,1),.06)[0],'Underside mouth is not recessed'
assert cast(beak,(.04,0,3.18),(0,0,1),.10)[0],'Mouth recess lacks back wall'
assert not cast(bottle,(.64,0,2.80),(0,0,-1),2.65)[0]
def center(t):return Vector((.64+.145*t*t,0,2.61-(2.61-.135)*t))
for i in range(19):
 a=center(.025+i*.05);b=center(.025+(i+1)*.05);assert not cast(dip,a,b-a,(b-a).length)[0]
assert not cast(dip,(.785,0,.09),(0,0,1),.08)[0]
intake_gap=min(p.z for p in points(dip))-.10;assert intake_gap>.016
print_gaps={}
for name in ['Tube liaose','Tube HAIR TREATMENT']:
 ds=[]
 for p in points(bpy.data.objects[name]):
  hit,q=cast(tube,p,(0,1,0),.025);assert hit;ds.append((q-p).length)
 assert min(ds)>.003 and max(ds)<.009,(name,min(ds),max(ds));print_gaps[name]=[min(ds),max(ds)]
for name in ['logo','shampoo','treatment']:
 for suffix in ['svg','png']:assert (HERE/f'{name}.{suffix}').read_bytes()==(OLD/f'{name}.{suffix}').read_bytes()

rest={n:o.location.copy() for n,o in roots.items()};local={o.name:o.matrix_local.copy() for o in meshes};poses=[]
for frame,t in [(1,0),(31,.5),(61,1)]:
 scene.frame_set(frame);bpy.context.view_layer.update()
 for part in cfg['parts']:
  key=part['key'];root=roots[part['node']];x,y,z=cfg['review']['explosion']['offsets'][key]
  assert (root.location-rest[root.name]-Vector((x,-z,y))*t).length<1e-6
  s=1+(cfg['review']['explosion']['scales'].get(key,1)-1)*t
  assert max(abs(v-s) for v in root.scale)<1e-6
  for o in root.children:assert max(abs(o.matrix_local[i][j]-local[o.name][i][j]) for i in range(4) for j in range(4))<1e-6
 ground=bpy.data.objects.get('Daily Hair physical studio ground')
 if ground:assert ground.location.z<min(p.z for o in meshes for p in points(o))-.004
 poses.append({'frame':frame,'progress':t})
exit_gap=min(p.z for p in points(dip))-max(p.z for p in points(bottle));assert exit_gap>.27
cap_gap=min(p.z for p in points(tube))-max(p.z for o in roots['TubeCap'].children for p in points(o));assert cap_gap>.36
scene.frame_set(1);bpy.context.view_layer.update()

blob=(CLIENT/'packaging-assets/poster-085-v3.glb').read_bytes();assert struct.unpack_from('<4sII',blob)==(b'glTF',2,len(blob))
length,kind=struct.unpack_from('<II',blob,12);assert kind==0x4e4f534a;g=json.loads(blob[20:20+length])
assert not g.get('animations') and len(g['meshes'])==18 and sum('mesh'in n for n in g['nodes'])==18
assert sum(len(m['primitives']) for m in g['meshes'])==18
assert {g['nodes'][i]['name'] for i in g['scenes'][0]['nodes']}==set(roots)
assert all('bufferView'in im and 'uri'not in im for im in g['images'])
main={'Warm ivory satin molded polymer','Satin copper bronze decorative finish','Muted rose bronze tube decoration'}
pbr={}
for m in g['materials']:
 if m['name'] in main:
  assert 'normalTexture'in m and 'metallicRoughnessTexture'in m['pbrMetallicRoughness']
  assert abs(m['normalTexture'].get('scale',1)-.22)<1e-6
  assert m.get('alphaMode','OPAQUE')=='OPAQUE'
  pbr[m['name']]={'normal':m['normalTexture'],'metallicRoughness':m['pbrMetallicRoughness']}
 if m['name'].startswith('White '):assert m['alphaMode']=='BLEND'
assert 'baseColorTexture'in next(m for m in g['materials'] if m['name']=='Muted rose bronze tube decoration')['pbrMetallicRoughness']
for o in meshes:
 if o.data.materials[0].name in main:assert o.data.uv_layers.active
source=HERE/'poster-085-v3.blend'
report={'passed':True,'product':'poster-085','version':'v3','meshObjects':18,'primitives':18,'pumpMeshes':6,'capMeshes':3,
 'solidGeometry':solids,'preservedWorldVertexErrors':errors,'original72SealRidgesPreserved':True,'maximumSealJoinWorldVertexError':seal_error,'actualTubeWallSamples':wall,
 'pumpNeckSocketAndStemBoresOpen':True,'realUndersideOutletRecess':True,'flipCapApertureOpenWithClosedLowerLid':True,
 'continuousDipTubeBoreOpen':True,'intakeToInnerFloorGap':intake_gap,'fullyExpandedTubeExitGap':exit_gap,'fullyExpandedCapGap':cap_gap,
 'wholePumpAndCapLocalTransformsPreserved':True,'tubePrintingGap':print_gaps,'allOriginalSvgPngBytesPreserved':True,
 'fourTransparentInkPlanesShadowDisabled':True,'twoPhysicalDecorativeSurfacesCastShadow':True,'sourceFrames':poses,
 'pbrTextureChain':pbr,'glbAnimations':0,'glbImages':len(g['images']),'glbBytes':len(blob),
 'glbSha256':hashlib.sha256(blob).hexdigest(),'configSha256':hashlib.sha256((HERE/'review-product.json').read_bytes()).hexdigest(),
 'sourceBytes':source.stat().st_size,'sourceSha256':hashlib.sha256(source.read_bytes()).hexdigest(),
 'visualReviewPending':True,'productionRegistered':False}
(HERE/'source-verification.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
print('085_SOURCE_VERIFIED',json.dumps({k:report[k] for k in ['passed','meshObjects','glbBytes','fullyExpandedTubeExitGap','fullyExpandedCapGap']}))
