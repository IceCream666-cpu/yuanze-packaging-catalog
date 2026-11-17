"""Independent final source and GLB verification for 081 v2."""
import bpy,bmesh,json,math,struct,hashlib
from pathlib import Path
from mathutils import Vector

HERE=Path(__file__).resolve().parent;OLD=HERE.parent;CLIENT=HERE.parents[3]
def points(o):return [o.matrix_world@v.co for v in o.data.vertices]
bpy.ops.wm.open_mainfile(filepath=str(OLD/'poster-081-v1.blend'))
bpy.context.scene.frame_set(1);bpy.context.view_layer.update()
preserved={o.name:points(o) for root in ['Body','Pump'] for o in bpy.data.objects[root].children
           if o.name!='Complete dispenser barrel and tube socket'}
bpy.ops.wm.open_mainfile(filepath=str(HERE/'poster-081-v2.blend'))
scene=bpy.context.scene;scene.frame_set(1);bpy.context.view_layer.update()
config=json.loads((HERE/'review-product.json').read_text())
roots={p['node']:bpy.data.objects[p['node']] for p in config['parts']}
assert set(roots)=={'Body','Pump','Label','LogoInk','NameInk'}
assert all(o.parent is None for o in roots.values())
meshes=[o for root in roots.values() for o in root.children_recursive if o.type=='MESH']
assert len(meshes)==11 and len(roots['Pump'].children)==5
assert all(not o.hide_render for o in meshes)
assert all(all(abs(s-1)<1e-6 for s in o.scale) for o in list(roots.values())+meshes)
errors={}
for name,original in preserved.items():
    current=points(bpy.data.objects[name]);assert len(current)==len(original)
    error=max((p-q).length for p,q in zip(current,original));assert error==0,(name,error);errors[name]=error

ink_names={'liaose on woven sleeve','EXFOLIATING HAND GEL','liaose on black side flag'}
solids={}
for ob in meshes:
    if ob.name in ink_names:
        assert not ob.visible_shadow and ob.data.uv_layers.active
        assert any(n.type=='TEX_IMAGE' and n.image.packed_file for n in ob.data.materials[0].node_tree.nodes)
        continue
    bm=bmesh.new();bm.from_mesh(ob.data)
    assert all(e.is_manifold for e in bm.edges),ob.name
    volume=bm.calc_volume(signed=True);assert volume>0,(ob.name,volume)
    solids[ob.name]={'manifold':True,'positiveVolume':volume};bm.free()

cloth=bpy.data.objects['Ivory woven wrap sleeve | soft rolled edges']
flag=bpy.data.objects['Black woven side flag'];tag=bpy.data.objects['liaose on black side flag']
assert cloth.parent==flag.parent==tag.parent==roots['Label']
assert cloth.visible_shadow and flag.visible_shadow and not tag.visible_shadow
cloth.data.calc_loop_triangles();radius_samples=[]
for tri in cloth.data.loop_triangles:
    vs=[cloth.matrix_world@cloth.data.vertices[i].co for i in tri.vertices]
    radius_samples.extend(math.hypot(p.x,p.y) for p in vs)
    centroid=sum(vs,Vector())/3;radius_samples.append(math.hypot(centroid.x,centroid.y))
    for a,b in zip(vs,vs[1:]+vs[:1]):
        p=(a+b)/2;radius_samples.append(math.hypot(p.x,p.y))
minimum_gap=min(radius_samples)-.782;assert minimum_gap>.0020,minimum_gap
flag_minimum_gap=min(math.hypot(p.x,p.y) for p in points(flag))-.782
assert flag_minimum_gap>.010,flag_minimum_gap
assert abs(cloth['nominalThickness']-.010)<1e-6
for matname in ['Warm ivory woven label','Black woven side flag']:
    mat=bpy.data.materials[matname];pbr=mat.node_tree.nodes['Principled BSDF']
    assert not pbr.inputs['Alpha'].is_linked and pbr.inputs['Alpha'].default_value==1
    normal=[n for n in mat.node_tree.nodes if n.type=='TEX_IMAGE' and n.image.colorspace_settings.name=='Non-Color']
    assert len(normal)==1 and tuple(normal[0].image.size)==(512,512) and normal[0].image.packed_file
    maps=[n for n in mat.node_tree.nodes if n.type=='NORMAL_MAP']
    assert len(maps)==1 and abs(maps[0].inputs['Strength'].default_value-.84)<1e-6
assert max(uv.uv.x for uv in cloth.data.uv_layers.active.data)>=4
for name in ['logo','name','tag-logo']:
    for suffix in ['svg','png']:assert (OLD/(name+'.'+suffix)).read_bytes()==(HERE/(name+'.'+suffix)).read_bytes()

def ray(o,p,d,distance):
    inv=o.matrix_world.inverted()
    return o.ray_cast(inv@Vector(p),(inv.to_3x3()@Vector(d)).normalized(),distance=distance)[0]
body=bpy.data.objects['Clear hollow cylinder | thick base and open neck']
barrel=bpy.data.objects['Complete dispenser barrel and tube socket']
nozzle=bpy.data.objects['Arched lever with recessed open pump outlet']
tube=bpy.data.objects['Long clear hollow dip tube | angled pickup']
assert not ray(body,(0,0,2.30),(0,0,-1),2.10),'Bottle cavity blocked'
assert not ray(barrel,(0,0,1.94),(0,0,1),.52),'Connector through-bore blocked'
assert ray(barrel,(0,0,2.05),(1,0,0),.12),'Socket wall missing'
assert not ray(nozzle,(-.81,0,2.826),(.1,0,.021),.09),'Original nozzle recess blocked'
def tube_center(t):return Vector((.18*t**2.1,0,2.21-2.025*t))
for i in range(19):
    a=tube_center(.025+i*.05);b=tube_center(.025+(i+1)*.05);d=b-a
    assert not ray(tube,a,d,d.length),'Curved dip tube centre bore blocked'
assert not ray(tube,(.18,0,.145),(0,0,1),.08),'Angled intake blocked'
intake_floor_gap=min(p.z for p in points(tube))-.157;assert intake_floor_gap>.010

rest={name:(o.location.copy(),o.scale.copy()) for name,o in roots.items()}
pump_rest={o.name:o.matrix_world.copy() for o in roots['Pump'].children}
label_rest={o.name:o.matrix_local.copy() for o in roots['Label'].children}
poses=[]
for frame,t in [(1,0),(31,.5),(61,1)]:
    scene.frame_set(frame);bpy.context.view_layer.update()
    for part in config['parts']:
        key=part['key'];o=roots[part['node']];base,scale=rest[o.name]
        x,y,z=config['review']['explosion']['offsets'][key]
        assert (o.location-base-Vector((x,-z,y))*t).length<1e-6
        s=1+(config['review']['explosion']['scales'].get(key,1)-1)*t
        assert max(abs(v-s) for v in o.scale)<1e-6
    delta=roots['Pump'].location-rest['Pump'][0]
    for o in roots['Pump'].children:
        assert (o.matrix_world.translation-pump_rest[o.name].translation-delta).length<1e-6
    for o in roots['Label'].children:
        assert max(abs(o.matrix_local[i][j]-label_rest[o.name][i][j]) for i in range(4) for j in range(4))<1e-6
    poses.append({'frame':frame,'progress':t,'locations':{n:list(o.location) for n,o in roots.items()}})
scene.frame_set(61);bpy.context.view_layer.update()
exit_gap=min(p.z for p in points(tube))-max(p.z for p in points(body));assert exit_gap>.27
def radial_envelope(ob):
    ps=points(ob)
    center=Vector(((min(p.x for p in ps)+max(p.x for p in ps))/2,
                   (min(p.y for p in ps)+max(p.y for p in ps))/2))
    radius=max((Vector((p.x,p.y))-center).length for p in ps)
    return center,radius
body_center,body_radius=radial_envelope(body);cloth_center,cloth_radius=radial_envelope(cloth)
full_radial_gap=(body_center-cloth_center).length-body_radius-cloth_radius
assert full_radial_gap>.08,full_radial_gap
assert config['review']['explosion']['mobilePrintSpread']==1
scene.frame_set(1)
glb=CLIENT/'packaging-assets/poster-081-v2.glb';data=glb.read_bytes()
assert data[:4]==b'glTF' and struct.unpack_from('<I',data,8)[0]==len(data)
length,kind=struct.unpack_from('<II',data,12);assert kind==0x4e4f534a
j=json.loads(data[20:20+length]);assert not j.get('animations')
assert set(j['nodes'][i]['name'] for i in j['scenes'][0]['nodes'])==set(roots)
assert len(j['meshes'])==11 and len([n for n in j['nodes'] if 'mesh' in n])==11
assert len(j['images'])==6 and all('bufferView' in im and 'uri' not in im for im in j['images'])
for mat in j['materials']:
    if mat['name'] in ['Warm ivory woven label','Black woven side flag']:
        assert mat.get('alphaMode','OPAQUE')=='OPAQUE'
        assert 'normalTexture' in mat and abs(mat['normalTexture']['scale']-.84)<1e-6
    if mat['name'] in ['Separate black liaose ink','Separate product name ink','Ivory wordmark attached to black side flag']:
        assert mat['alphaMode']=='BLEND'
assert config['review']['appearance']['labelShadows']
oldbytes=(CLIENT/'packaging-assets/poster-081-v1.glb').stat().st_size
report={'passed':True,'roots':list(roots),'meshObjects':11,'wholePumpMeshes':5,'solidGeometry':solids,
        'preservedWorldVertexErrors':errors,'clothMinimumSampledGap':minimum_gap,'flagMinimumVertexGap':flag_minimum_gap,
        'clothNominalThickness':.010,'wovenNormalTextureSize':[512,512],'wovenMaterialsOpaque':True,
        'allThreeOriginalSvgAndPngPreserved':True,'allTransparentInkCarriersShadowDisabled':True,
        'sideFlagInkRemainsAttached':True,'openBottleCavity':True,'connectorThroughBoreOpen':True,
        'socketSideWallPresent':True,'originalNozzleRecessOpen':True,'continuousDipTubeBoreOpen':True,
        'angledIntakeOpen':True,'intakeToInnerFloorGap':intake_floor_gap,'fullyExpandedTubeExitGap':exit_gap,
        'fullyExpandedSleeveRadialGap':full_radial_gap,'mobilePrintSpread':1,
        'motionScope':'Layer comparison path; intermediate rigid sleeve motion is illustrative, not a physical removal simulation. Fully expanded sleeve is clear of bottle.',
        'completePumpRelativeTransformsPreserved':True,'sourceFrames':poses,'containsFormula':False,
        'glbAnimations':0,'glbEmbeddedImages':6,'glbBytes':len(data),'oldGlbBytes':oldbytes,
        'byteReductionPercent':(1-len(data)/oldbytes)*100,'glbSha256':hashlib.sha256(data).hexdigest(),
        'configSha256':hashlib.sha256((HERE/'review-product.json').read_bytes()).hexdigest(),
        'sourceBytes':(HERE/'poster-081-v2.blend').stat().st_size,'visualReviewPending':True,'productionRegistered':False}
(HERE/'source-verification.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
print('HAND_GEL_081_SOURCE_VERIFIED',json.dumps({k:report[k] for k in ['passed','meshObjects','glbBytes','byteReductionPercent','clothMinimumSampledGap','sourceBytes']}))
