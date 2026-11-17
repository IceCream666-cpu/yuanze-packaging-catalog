"""Reopen the 056 deliverable and independently inspect solids, bores and poses."""
import bpy,bmesh,json,math,struct,hashlib
from pathlib import Path
from mathutils import Vector

HERE=Path(__file__).resolve().parent;CLIENT=HERE.parents[3];S=2.9/1.41
bpy.ops.wm.open_mainfile(filepath=str(HERE/'poster-056-v2.blend'))
scene=bpy.context.scene;scene.frame_set(1);bpy.context.view_layer.update()
config=json.loads((HERE/'review-product.json').read_text())
roots={p['node']:bpy.data.objects[p['node']] for p in config['parts']}
assert len(roots)==6 and all(o.parent is None for o in roots.values())
meshes=[m for root in roots.values() for m in root.children_recursive if m.type=='MESH']
assert all(not o.hide_render for o in meshes)
assert all(all(abs(v-1)<1e-6 for v in o.scale) for o in list(roots.values())+meshes)
solid_report={}
for o in meshes:
    if 'print layer' in o.name:continue
    bm=bmesh.new();bm.from_mesh(o.data)
    assert all(e.is_manifold for e in bm.edges),o.name
    volume=bm.calc_volume(signed=True);assert volume>0,(o.name,volume)
    solid_report[o.name]={'manifold':True,'positiveVolume':volume};bm.free()
body=bpy.data.objects['Hollow rounded rectangular bottle with thick clear base']
assert len(body.data.materials)==2 and set(p.material_index for p in body.data.polygons)=={0,1}
body_points=[body.matrix_world@v.co for v in body.data.vertices]
body_height=max(p.z for p in body_points)-min(p.z for p in body_points)
body_width=max(p.x for p in body_points)-min(p.x for p in body_points)
body_depth=max(p.y for p in body_points)-min(p.y for p in body_points)
assert abs(body_height/body_width-.92)<1e-5
assert abs(body_depth/body_width-.34)<1e-5
film=roots['PaperLabel'].children[0]
film_points=[film.matrix_world@v.co for v in film.data.vertices]
film_front=min(p.y for p in film_points);film_back=max(p.y for p in film_points)
body_front=min(p.y for p in body_points)
assert .00089<film_back-film_front<.00091
film_gap=body_front-film_back;assert film_gap>.0019,film_gap
assert film.visible_shadow
for name in ['LogoPrint','ProductPrint']:
    o=roots[name].children[0];assert not o.visible_shadow and o.data.uv_layers.active
    points=[o.matrix_world@v.co for v in o.data.vertices]
    assert max(p.y for p in points)<film_front-.0015
    tex=[n for n in o.data.materials[0].node_tree.nodes if n.type=='TEX_IMAGE']
    assert len(tex)==1 and tex[0].image.packed_file and tuple(tex[0].image.size)==(2048,1156)
assert not any(n.type=='TEX_IMAGE' for n in film.data.materials[0].node_tree.nodes)

def ray_in_world(o,origin,direction,distance):
    inv=o.matrix_world.inverted();local_origin=inv@Vector(origin);local_direction=(inv.to_3x3()@Vector(direction)).normalized()
    return o.ray_cast(local_origin,local_direction,distance=distance)[0]
tube=bpy.data.objects['Hollow clear Golden pump dip tube']
stem=bpy.data.objects['Hollow olive pump connector with tube socket']
actuator=bpy.data.objects['Tall cylindrical press actuator']
assert not ray_in_world(tube,(0,0,.10*S),(0,0,1),1.1*S),'Dip-tube centre bore is blocked'
assert not ray_in_world(stem,(0,0,.90*S),(0,0,1),.25*S),'Connector centre bore is blocked'
assert not ray_in_world(actuator,(0,-.20*S,1.25*S),(0,1,0),.2*S),'Actuator side outlet is blocked'
assert all(o.parent==roots['PumpAssembly'] for o in [tube,stem,actuator])
tube_points=[tube.matrix_world@v.co for v in tube.data.vertices]
tube_bottom=min(p.z for p in tube_points);tube_top=max(p.z for p in tube_points)
assert tube_bottom-.14*S>.08
assert tube_top>.985*S

rest={name:(o.location.copy(),o.scale.copy()) for name,o in roots.items()}
pump_relative={o.name:o.matrix_world.copy() for o in roots['PumpAssembly'].children_recursive}
poses=[]
for frame,t in [(1,0),(31,.5),(61,1)]:
    scene.frame_set(frame);bpy.context.view_layer.update()
    for part in config['parts']:
        key,name=part['key'],part['node'];o=roots[name];pos,scale=rest[name];x,y,z=config['review']['explosion']['offsets'][key]
        amount=t
        if key in config['review']['explosion'].get('timing',{}):
            start,end=config['review']['explosion']['timing'][key];amount=max(0,min(1,(t-start)/(end-start)));amount=amount**2*(3-2*amount)
        assert (o.location-pos-Vector((x,-z,y))*amount).length<1e-6
        expected=scale*(1+(config['review']['explosion']['scales'].get(key,1)-1)*amount)
        assert (o.scale-expected).length<1e-6
    pump_translation=roots['PumpAssembly'].location-rest['PumpAssembly'][0]
    for o in roots['PumpAssembly'].children_recursive:
        assert (o.matrix_world.translation-pump_relative[o.name].translation-pump_translation).length<1e-6
    poses.append({'frame':frame,'progress':t,'roots':{name:list(o.location) for name,o in roots.items()}})
scene.frame_set(61);bpy.context.view_layer.update()
tube_exit_gap=min((tube.matrix_world@v.co).z for v in tube.data.vertices)-max((body.matrix_world@v.co).z for v in body.data.vertices)
assert tube_exit_gap>.5,tube_exit_gap
scene.frame_set(1)
glb=CLIENT/'packaging-assets/poster-056-v2.glb';data=glb.read_bytes()
assert data[:4]==b'glTF';size,kind=struct.unpack_from('<II',data,12);assert kind==0x4e4f534a
j=json.loads(data[20:20+size]);assert not j.get('animations')
assert sorted(j['nodes'][n]['name'] for n in j['scenes'][0]['nodes'])==sorted(roots)
assert all('uri' not in image and 'bufferView' in image for image in j['images'])
assert len(j['images'])==2
assert all(m.get('alphaMode')=='BLEND' for m in j['materials'] if 'alpha ink' in m.get('name',''))
assert all(n.get('scale',[1,1,1])==[1,1,1] for n in j['nodes'])
report={'passed':True,'roots':list(roots),'solidGeometry':solid_report,'bodyDimensions':[body_width,body_depth,body_height],'bodyHeightToWidth':body_height/body_width,'bodyDepthToWidth':body_depth/body_width,'filmThickness':film_back-film_front,'filmBackToBottleGap':film_gap,'filmIsIllustrativeClearCarrier':True,'transparentInkShadowDisabled':True,'dipTubeOpenBoreRayPassed':True,'connectorOpenBoreRayPassed':True,'sideOutletOpenRayPassed':True,'tubeBottomToInteriorFloorGap':tube_bottom-.14*S,'fullyExpandedTubeExitGap':tube_exit_gap,'completePumpRelativeTransformsPreserved':True,'sourcePoses':poses,'glbAnimations':len(j.get('animations',[])),'glbEmbeddedImages':len(j['images']),'glbBytes':len(data),'glbSha256':hashlib.sha256(data).hexdigest(),'sourceBytes':(HERE/'poster-056-v2.blend').stat().st_size,'visualReviewPending':True,'productionRegistered':False}
(HERE/'source-verification.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
print('GOLDEN_056_SOURCE_VERIFIED',json.dumps({k:report[k] for k in ['passed','filmBackToBottleGap','fullyExpandedTubeExitGap','glbBytes','sourceBytes']}))
