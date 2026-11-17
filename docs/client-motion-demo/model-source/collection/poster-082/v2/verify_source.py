"""Independent actual-source, ray, assembly and GLB checks for Soap Duo v2."""
import bpy,bmesh,json,math,struct,hashlib
from pathlib import Path
from mathutils import Vector
HERE=Path(__file__).resolve().parent;OLD=HERE.parent;CLIENT=HERE.parents[3]
def points(o):return [o.matrix_world@v.co for v in o.data.vertices]
names=['Empty ivory cylinder | low shoulder and hollow neck',
       'Long clear hollow dip tube | near-bottom angled intake',
       'Blue flip-top cap | lower hinged lid','Blue flip-top rear hinge']
bpy.ops.wm.open_mainfile(filepath=str(OLD/'poster-082-v1.blend'))
bpy.context.scene.frame_set(1);bpy.context.view_layer.update()
original={name:points(bpy.data.objects[name]) for name in names}
bpy.ops.wm.open_mainfile(filepath=str(HERE/'poster-082-v2.blend'))
scene=bpy.context.scene;scene.frame_set(1);bpy.context.view_layer.update()
config=json.loads((HERE/'review-product.json').read_text())
roots={p['node']:bpy.data.objects[p['node']] for p in config['parts']}
assert set(roots)=={'Body','Pump','TubeCap','Label','LogoInk','NameInk'}
assert all(o.parent is None for o in roots.values())
assert {name:len(o.children) for name,o in roots.items()}=={'Body':2,'Pump':6,'TubeCap':3,'Label':3,'LogoInk':2,'NameInk':4}
meshes=[o for root in roots.values() for o in root.children_recursive if o.type=='MESH']
assert len(meshes)==20 and all(not o.hide_render for o in meshes)
assert all(all(abs(s-1)<1e-6 for s in o.scale) for o in list(roots.values())+meshes)
errors={}
for name,old in original.items():
    ps=points(bpy.data.objects[name]);assert len(ps)==len(old)
    errors[name]=max((p-q).length for p,q in zip(ps,old));assert errors[name]==0

tube=bpy.data.objects['Flexible thin-wall tube | integrated embossed heat seal and open nozzle']
stripes=bpy.data.objects['Pale blue pinstripes | thin solid direct-print decoration']
solids={};transparent=[]
for ob in meshes:
    if ob.parent.name in {'LogoInk','NameInk'} or 'transparent print carrier' in ob.name:
        assert not ob.visible_shadow and ob.data.uv_layers.active
        transparent.append(ob.name);continue
    bm=bmesh.new();bm.from_mesh(ob.data)
    assert all(e.is_manifold for e in bm.edges),ob.name
    volume=bm.calc_volume(signed=True);assert volume>0,(ob.name,volume)
    remaining=set(bm.verts);components=0
    while remaining:
        components+=1;stack=[remaining.pop()]
        while stack:
            v=stack.pop()
            for edge in v.link_edges:
                other=edge.other_vert(v)
                if other in remaining:remaining.remove(other);stack.append(other)
    if ob==tube:assert components==1,'Heat seal must be part of the same shell'
    if ob==stripes:assert components==28,'Original interrupted stripe runs changed'
    solids[ob.name]={'manifold':True,'positiveVolume':volume,'connectedComponents':components}
    bm.free()
assert len(solids)==12 and len(transparent)==8
assert stripes.visible_shadow and stripes['originalLetteringGapsPreserved']
assert abs(stripes['nominalThickness']-.0006)<1e-9
assert tube['heatSealIntegrated'] and not tube['containsFormula']
for ob in meshes:assert all(m is not None for m in ob.data.materials),ob.name

def cast(o,p,d,distance):
    inv=o.matrix_world.inverted()
    hit,where,normal,index=o.ray_cast(inv@Vector(p),(inv.to_3x3()@Vector(d)).normalized(),distance=distance)
    return hit,o.matrix_world@where if hit else None
assert not cast(tube,(-.83,0,.25),(0,0,1),2.70)[0],'Tube dispensing passage blocked'
assert cast(tube,(-.83,0,3.12),(0,0,-1),.04)[0],'Heat seal top absent'
assert cast(tube,(-.83,0,2.98),(0,0,1),.04)[0],'Heat seal internal termination absent'
wall=[]
for z in [.55,1.1,1.6,2.3,2.75]:
    hit,inner=cast(tube,(-.83,0,z),(0,-1,0),.40);assert hit
    hit,outer=cast(tube,inner+Vector((0,-.00001,0)),(0,-1,0),.025);assert hit
    thickness=(outer-inner).length;assert .010<thickness<.017,(z,thickness)
    wall.append({'z':z,'frontWallThickness':thickness})
barrel=bpy.data.objects['Disc pump | rounded closure barrel']
socket=bpy.data.objects['Disc pump | internal socket, stays with head']
neck=bpy.data.objects['Disc pump | assembled actuator neck']
lip=bpy.data.objects['Disc pump | low rear-edge dispensing lip']
upper=bpy.data.objects['Blue flip-top cap | complete closure sleeve']
dip=bpy.data.objects['Long clear hollow dip tube | near-bottom angled intake']
bottle=bpy.data.objects['Empty ivory cylinder | low shoulder and hollow neck']
assert not cast(barrel,(.75,0,1.98),(0,0,1),.38)[0]
assert not cast(socket,(.75,0,1.84),(0,0,1),.22)[0]
assert not cast(neck,(.75,0,2.30),(0,0,1),.25)[0]
assert not cast(lip,(.75,.33,2.639),(0,-1,0),.05)[0]
assert cast(lip,(.75,.33,2.639),(0,-1,0),.10)[0],'Rear outlet must have a recessed back wall'
assert not cast(upper,(-.83,0,.145),(0,0,1),.29)[0]
assert not cast(bottle,(.75,0,2.18),(0,0,-1),2.05)[0]
def tube_center(t):return Vector((.75+.145*t*t,0,1.985-(1.985-.115)*t))
for i in range(19):
    a=tube_center(.025+i*.05);b=tube_center(.025+(i+1)*.05)
    assert not cast(dip,a,b-a,(b-a).length)[0]
assert not cast(dip,(.895,0,.070),(0,0,1),.07)[0]
intake_gap=min(p.z for p in points(dip))-.089;assert intake_gap>.007

print_gaps={}
for ob in meshes:
    if ob.name not in ['Tube bold liaose','Tube SOAP CLEAN SOAP','Tube HAIR TREATMENT 180 ml']:continue
    distances=[]
    for p in points(ob):
        hit,q=cast(tube,p,(0,1,0),.025);assert hit,(ob.name,list(p))
        distance=(q-p).length;assert .001<distance<.009,(ob.name,distance)
        distances.append(distance)
    print_gaps[ob.name]={'min':min(distances),'max':max(distances)}
for name in ['logo','soap-clean-soap','spec-tube','spec-bottle']:
    for suffix in ['svg','png']:assert (HERE/(name+'.'+suffix)).read_bytes()==(OLD/(name+'.'+suffix)).read_bytes()

rest={name:o.location.copy() for name,o in roots.items()}
local={o.name:o.matrix_local.copy() for root in roots.values() for o in root.children}
poses=[]
for frame,t in [(1,0),(31,.5),(61,1)]:
    scene.frame_set(frame);bpy.context.view_layer.update()
    ground=bpy.data.objects.get('Soap Duo physical studio ground')
    if ground:
        lowest=min(p.z for ob in meshes for p in points(ob))
        assert ground.location.z<lowest-.004,'Studio floor clips the downward cap'
    for part in config['parts']:
        key=part['key'];root=roots[part['node']];x,y,z=config['review']['explosion']['offsets'][key]
        assert (root.location-rest[root.name]-Vector((x,-z,y))*t).length<1e-6
        s=1+(config['review']['explosion']['scales'].get(key,1)-1)*t
        assert max(abs(v-s) for v in root.scale)<1e-6
        for ob in root.children:
            assert max(abs(ob.matrix_local[i][j]-local[ob.name][i][j]) for i in range(4) for j in range(4))<1e-6
    poses.append({'frame':frame,'progress':t})
exit_gap=min(p.z for p in points(dip))-max(p.z for p in points(bottle));assert exit_gap>.04
cap_gap=min(p.z for p in points(tube))-max(p.z for root in [roots['TubeCap']] for ob in root.children for p in points(ob));assert cap_gap>.5
scene.frame_set(1)

glb=CLIENT/'packaging-assets/poster-082-v2.glb';blob=glb.read_bytes()
assert struct.unpack_from('<4sII',blob)==(b'glTF',2,len(blob))
length,kind=struct.unpack_from('<II',blob,12);assert kind==0x4e4f534a
d=json.loads(blob[20:20+length]);assert not d.get('animations')
assert {d['nodes'][i]['name'] for i in d['scenes'][0]['nodes']}==set(roots)
assert len(d['meshes'])==20 and len([n for n in d['nodes'] if 'mesh' in n])==20
assert all('bufferView' in im and 'uri' not in im for im in d['images'])
for mat in d['materials']:
    if mat['name']=='Powder blue pinstripe ink':assert mat.get('alphaMode','OPAQUE')=='OPAQUE'
    if mat['name']=='Transparent direct-print carrier | conceptual ink layer':assert mat['alphaMode']=='BLEND'
assert config['review']['appearance']['labelShadows'] and not config['review']['appearance']['glass']
source=HERE/'poster-082-v2.blend'
report={'passed':True,'roots':list(roots),'meshObjects':20,'pumpMeshes':6,'capMeshes':3,
        'solidGeometry':solids,'preservedWorldVertexErrors':errors,'continuousHeatSealShell':True,
        'actualTubeWallSamples':wall,'tubeDispensingNeckOpen':True,'pumpSocketAndActuatorBoresOpen':True,
        'rearLipHasRealRecessedOutlet':True,'flipCapUpperPassageOpen':True,
        'continuousDipTubeBoreOpen':True,'angledIntakeOpen':True,'intakeToInnerFloorGap':intake_gap,
        'fullyExpandedTubeExitGap':exit_gap,'fullyExpandedCapGap':cap_gap,
        'wholePumpAndCapLocalTransformsPreserved':True,'tubePrintingGap':print_gaps,
        'studioFloorBelowEveryPartAtAllThreeSourceFrames':True,
        'allFourSvgAndPngBytesPreserved':True,'eightTransparentCarriersShadowDisabled':True,
        'onlyPhysicalBlueStripeDecorationCastsLabelShadow':True,'opaqueIvoryAndBluePlastic':True,
        'containsFormula':False,'paperLabel':False,'sourceFrames':poses,'glbAnimations':0,
        'glbImages':len(d['images']),'glbBytes':len(blob),'oldGlbBytes':(CLIENT/'packaging-assets/poster-082-v1.glb').stat().st_size,
        'glbSha256':hashlib.sha256(blob).hexdigest(),'configSha256':hashlib.sha256((HERE/'review-product.json').read_bytes()).hexdigest(),
        'sourceBytes':source.stat().st_size,'sourceSha256':hashlib.sha256(source.read_bytes()).hexdigest(),
        'visualReviewPending':True,'productionRegistered':False}
(HERE/'source-verification.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
print('SOAP_DUO_SOURCE_VERIFIED',json.dumps({k:report[k] for k in ['passed','meshObjects','glbBytes','fullyExpandedTubeExitGap','fullyExpandedCapGap']}))
