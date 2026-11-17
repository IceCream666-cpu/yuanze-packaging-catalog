"""Independent source/GLB checks for 084 v3, including real bores and sealed paper."""
import bpy,bmesh,json,struct,hashlib,math
from pathlib import Path
from mathutils import Vector

HERE=Path(__file__).resolve().parent; CLIENT=HERE.parents[3]
bpy.ops.wm.open_mainfile(filepath=str(HERE/'poster-084-v3.blend'))
scene=bpy.context.scene; scene.frame_set(1); bpy.context.view_layer.update()
config=json.loads((HERE/'review-product.json').read_text())
roots={p['node']:bpy.data.objects[p['node']] for p in config['parts']}
assert set(roots)=={'Body','Pump','Label','LogoInk','NameInk'}
assert all(o.parent is None for o in roots.values())
meshes=[o for r in roots.values() for o in r.children_recursive if o.type=='MESH']
assert len(meshes)==12
assert all(not o.hide_render for o in meshes)
assert not any('liquid' in o.name.lower() or 'formula' in o.name.lower() for o in meshes)
assert all(all(abs(s-1)<1e-6 for s in o.scale) for o in list(roots.values())+meshes)

def points(ob):return [ob.matrix_world@v.co for v in ob.data.vertices]
def ray(ob,origin,direction,distance):
    inv=ob.matrix_world.inverted()
    return ob.ray_cast(inv@Vector(origin),(inv.to_3x3()@Vector(direction)).normalized(),distance=distance)[0]

solids={}; ink={}; label_report={}; bore_report={}
for ob in meshes:
    if ob.parent.name in {'LogoInk','NameInk'}:
        assert not ob.visible_shadow
        nodes=[n for n in ob.data.materials[0].node_tree.nodes if n.type=='TEX_IMAGE']
        assert nodes and all(n.image.packed_file and n.image.size[0]==2048 for n in nodes)
        assert ob.data.uv_layers.active
        ink[ob.name]={'shadow':False,'width':2048,'alphaImagePacked':True}
        continue
    bm=bmesh.new(); bm.from_mesh(ob.data)
    assert all(e.is_manifold for e in bm.edges),ob.name
    volume=bm.calc_volume(signed=True); assert volume>0,ob.name
    bm.free(); solids[ob.name]={'manifold':True,'positiveVolume':volume}

for cx,kind in [(-.7,'LOTION'),(.7,'WASH')]:
    body=bpy.data.objects[kind+' hollow cylinder']; body_points=points(body)
    assert len(body.data.vertices)==3970
    dims=[max(p[i] for p in body_points)-min(p[i] for p in body_points) for i in range(3)]
    assert all(abs(a-b)<1e-6 for a,b in zip(dims,[1.15,1.15,2.155]))
    pbr=body.data.materials[0].node_tree.nodes['Principled BSDF']
    assert list(pbr.inputs['Base Color'].default_value)==[1,1,1,1]
    assert pbr.inputs['Transmission Weight'].default_value==1
    assert abs(pbr.inputs['IOR'].default_value-1.52)<1e-6
    assert not ray(body,(cx,0,2.30),(0,0,-1),2.1),'Bottle inner cavity is obstructed'
    pump=bpy.data.objects[kind+' complete white pump']
    assert pump.parent==roots['Pump'] and pump['preservedRibs']==96
    merged=json.loads(pump['mergedMechanicalParts'])
    assert sum('closure rib' in n for n in merged)==96
    assert not pump.data.uv_layers
    # Probe the socket's centre to just below the inner ceiling, and real outlet recess.
    assert not ray(pump,(cx,0,1.88),(0,0,1),.38),'Socket bottom bore is blocked'
    assert ray(pump,(cx,0,1.94),(1,0,0),.10),'Socket wall is missing'
    assert not ray(pump,(cx+.565,0,2.79),(0,0,1),.085),'Nozzle mouth is blocked'
    assert ray(pump,(cx+.565,0,2.84),(0,1,0),.06),'Nozzle cavity side wall is missing'
    assert not ray(pump,(cx+.13,0,1.99),(0,0,1),.27),'Closure underside is not hollow'
    tube=bpy.data.objects[kind+' hollow dip tube']; assert tube.parent==roots['Pump']
    def center(t):return Vector((cx+.145*t*t,0,1.985-1.87*t))
    for i in range(19):
        a=center(.025+i*.05); b=center(.025+(i+1)*.05); d=b-a
        assert not ray(tube,a,d,d.length),'Long dip tube centre bore obstructed'
    assert not ray(tube,(cx+.145,0,.08),(0,0,1),.08),'Angled tube intake blocked'
    bore_report[kind]={'glassCavityOpen':True,'socketBoreOpen':True,'socketWallPresent':True,
                       'closureUndersideOpen':True,'nozzleOutletOpen':True,'nozzleSideWallPresent':True,
                       'continuousDipTubeBoreOpen':True,'angledIntakeOpen':True}
    label=bpy.data.objects[kind+' physical white wrap label']; assert label.visible_shadow
    assert len(label.data.materials)==2
    assert not any(n.type=='TEX_IMAGE' for m in label.data.materials for n in m.node_tree.nodes)
    label.data.calc_loop_triangles()
    samples=[]
    for tri in label.data.loop_triangles:
        vs=[label.matrix_world@label.data.vertices[i].co for i in tri.vertices]
        samples.extend(vs); samples.append(sum(vs,Vector())/3)
        samples.extend((a+b)/2 for a,b in zip(vs,vs[1:]+vs[:1]))
    min_radius=min(math.hypot(p.x-cx,p.y) for p in samples)
    assert min_radius>.5751,('Paper intersects glass',kind,min_radius)
    label_report[kind]={'thickness':label['thickness'],'sampledMinimumBackToCylinderGap':min_radius-.575,
                        'sealedThinSolid':True,'shadowEnabled':True,'unprintedPaperBack':True}

assert bpy.data.objects['LOTION complete white pump'].data is bpy.data.objects['WASH complete white pump'].data
rest={n:(o.location.copy(),o.scale.copy()) for n,o in roots.items()}
pump_rest={o.name:o.matrix_world.copy() for o in roots['Pump'].children}
poses=[]
for frame,t in [(1,0),(31,.5),(61,1)]:
    scene.frame_set(frame); bpy.context.view_layer.update()
    for part in config['parts']:
        key=part['key']; ob=roots[part['node']]; pos,scale=rest[ob.name]
        x,y,z=config['review']['explosion']['offsets'][key]
        assert (ob.location-pos-Vector((x,-z,y))*t).length<1e-6
        target_scale=1+(config['review']['explosion']['scales'].get(key,1)-1)*t
        assert max(abs(s-target_scale) for s in ob.scale)<1e-6
    translation=roots['Pump'].location-rest['Pump'][0]
    for ob in roots['Pump'].children:
        assert (ob.matrix_world.translation-pump_rest[ob.name].translation-translation).length<1e-6
    poses.append({'frame':frame,'amount':t,'rootLocations':{n:list(o.location) for n,o in roots.items()}})
scene.frame_set(61);bpy.context.view_layer.update()
exit_gaps={}
for kind in ['LOTION','WASH']:
    gap=min(p.z for p in points(bpy.data.objects[kind+' hollow dip tube']))-max(p.z for p in points(bpy.data.objects[kind+' hollow cylinder']))
    assert gap>.49;exit_gaps[kind]=gap
scene.frame_set(1)

glb=CLIENT/'packaging-assets/poster-084-v3.glb'; data=glb.read_bytes()
assert data[:4]==b'glTF' and struct.unpack_from('<I',data,8)[0]==len(data)
length,kind=struct.unpack_from('<II',data,12); assert kind==0x4e4f534a
j=json.loads(data[20:20+length]); assert not j.get('animations')
assert set(j['nodes'][n]['name'] for n in j['scenes'][0]['nodes'])==set(roots)
mesh_nodes=[n for n in j['nodes'] if 'mesh' in n]
assert len(mesh_nodes)==12 and len(j['meshes'])==11
assert sum(len(j['meshes'][n['mesh']]['primitives']) for n in mesh_nodes)==14
assert len(j['images'])==3 and all('uri' not in i and 'bufferView' in i for i in j['images'])
assert all(n.get('scale',[1,1,1])==[1,1,1] for n in j['nodes'])
assert config['review']['appearance']['labelShadows']
old_bytes=(CLIENT/'packaging-assets/poster-084-v2.glb').stat().st_size
report={'passed':True,'roots':list(roots),'logicalMeshes':len(meshes),'meshDefinitions':len(j['meshes']),
        'renderedPrimitiveInstances':14,'solidGeometry':solids,'ink':ink,'labels':label_report,'bores':bore_report,
        'preservedRibsPerPump':96,'whitePumpMeshShared':True,'wholePumpRelativeTransformsPreserved':True,
        'poses':poses,'fullyExpandedTubeExitGaps':exit_gaps,'containsFormula':False,
        'glbAnimations':0,'glbEmbeddedImages':3,'glbBytes':len(data),'oldGlbBytes':old_bytes,
        'byteReductionPercent':(1-len(data)/old_bytes)*100,'glbSha256':hashlib.sha256(data).hexdigest(),
        'configSha256':hashlib.sha256((HERE/'review-product.json').read_bytes()).hexdigest(),
        'sourceBytes':(HERE/'poster-084-v3.blend').stat().st_size,'browserVerifiedSeparately':False}
(HERE/'source-verification.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
print('SOFT_BODY_084_SOURCE_VERIFIED',json.dumps({k:report[k] for k in ['passed','logicalMeshes','meshDefinitions','glbBytes','byteReductionPercent','sourceBytes']}))
