"""084 v3: preserve empty glass, finish mechanical cavities, solid paper, five roots.

Run with the locally installed Blender. Old source and versioned assets stay intact.
"""
import bpy, bmesh, json, math, hashlib, shutil, subprocess
from pathlib import Path
from mathutils import Vector

HERE = Path(__file__).resolve().parent
OLD = HERE.parent
CLIENT = HERE.parents[3]
GLB = CLIENT / 'packaging-assets/poster-084-v3.glb'
ROOTS = ('Body', 'Pump', 'Label', 'LogoInk', 'NameInk')
bpy.ops.wm.open_mainfile(filepath=str(OLD / 'poster-084-v2.blend'))
bpy.context.preferences.filepaths.save_version = 0
scene = bpy.context.scene
scene.frame_set(1)
roots = {n: bpy.data.objects[n] for n in ROOTS}

def world_points(ob):
    return [ob.matrix_world @ v.co for v in ob.data.vertices]

original_bodies = {ob.name: [list(p) for p in world_points(ob)] for ob in roots['Body'].children}
original_ribs = {ob.name: [list(p) for p in world_points(ob)] for ob in roots['Pump'].children if 'closure rib' in ob.name}
original_mesh_count = sum(ob.type == 'MESH' for ob in scene.objects)

def activate(ob):
    bpy.ops.object.select_all(action='DESELECT')
    ob.select_set(True)
    bpy.context.view_layer.objects.active = ob

def manifold(ob):
    bm = bmesh.new(); bm.from_mesh(ob.data)
    bmesh.ops.recalc_face_normals(bm, faces=list(bm.faces))
    assert all(e.is_manifold for e in bm.edges), ob.name
    volume = bm.calc_volume(signed=True)
    assert volume > 0, (ob.name, volume)
    bm.to_mesh(ob.data); bm.free(); ob.data.update()
    return volume

def boolean_hole(ob, name, cx, cy, bottom, top, radius):
    bpy.ops.mesh.primitive_cylinder_add(vertices=96, radius=radius, depth=top-bottom,
                                      location=(cx, cy, (bottom+top)/2))
    cutter = bpy.context.object; cutter.name = name + ' temporary cutter'
    activate(ob)
    mod = ob.modifiers.new(name, 'BOOLEAN'); mod.operation = 'DIFFERENCE'; mod.solver = 'EXACT'; mod.object = cutter
    bpy.ops.object.modifier_apply(modifier=mod.name)
    bpy.data.objects.remove(cutter, do_unlink=True)
    manifold(ob)

def tube_socket(name, cx, material):
    # Hollow wall connects the tube to the inner ceiling of the pump collar.
    rows = [(1.89, .060), (1.90, .063), (2.035, .089), (2.295, .089),
            (2.307, .082), (2.307, .030), (1.89, .030)]
    n = 128; vs = []; faces = []
    for z, r in rows:
        vs.extend((cx+r*math.cos(i*math.tau/n), r*math.sin(i*math.tau/n), z) for i in range(n))
    for k in range(len(rows)):
        k2 = (k+1) % len(rows)
        for i in range(n):
            j = (i+1) % n
            faces.append((k*n+i, k*n+j, k2*n+j, k2*n+i))
    mesh = bpy.data.meshes.new(name); mesh.from_pydata(vs, [], faces); mesh.update()
    ob = bpy.data.objects.new(name, mesh); scene.collection.objects.link(ob)
    ob.parent = roots['Pump']; ob.location = -roots['Pump'].location
    mesh.materials.append(material)
    manifold(ob)
    for p in mesh.polygons: p.use_smooth = abs(p.normal.z) < .999
    return ob

pump_material = bpy.data.materials['Translucent pearl-white molded pump']
p = pump_material.node_tree.nodes.get('Principled BSDF')
p.inputs['Roughness'].default_value = .23
p.inputs['Transmission Weight'].default_value = .10
p.inputs['Coat Weight'].default_value = .12
p.inputs['Coat Roughness'].default_value = .17

mechanical = []
for cx, kind in [(-.7, 'LOTION'), (.7, 'WASH')]:
    closure = bpy.data.objects[kind+' pump closure']
    # Retain the original stepped closure/ribs and hollow only its underside.
    boolean_hole(closure, kind+' open inner closure', cx, 0, 1.98, 2.285, .185)
    old_socket = bpy.data.objects[kind+' integrated socket']
    bpy.data.objects.remove(old_socket, do_unlink=True)
    socket = tube_socket(kind+' hollow tube connector', cx, pump_material)
    spout = bpy.data.objects[kind+' horizontal spout']
    boolean_hole(spout, kind+' downward outlet', cx+.565, 0, 2.78, 2.885, .027)
    # Exact bores remain real geometry; the existing rounded outer spout stays unchanged.
    for face in spout.data.polygons:
        if abs(face.normal.z) > .999: face.use_smooth = False
    tube = next(o for o in roots['Pump'].children if 'dip tube' in o.name and ((sum(p.x for p in world_points(o))/len(o.data.vertices)) < 0) == (cx < 0))
    tube.name = kind+' hollow dip tube'
    tube['mechanicalRole'] = 'complete pump long hollow curved suction tube with angled open intake'
    socket['mechanicalRole'] = 'hollow tube socket with open bottom bore'
    mechanical.append({'kind':kind,'outletCenter':[cx+.565,0,2.8125], 'outletRadius':.027,
                       'socketBoreRadius':.030, 'closureInsideRadius':.185,
                       'sourceRibCount':96})

tube_material = bpy.data.materials['Clear polyethylene hollow suction tube']
p = tube_material.node_tree.nodes.get('Principled BSDF')
p.inputs['Base Color'].default_value = (.91, .94, .96, 1)
p.inputs['Transmission Weight'].default_value = .84
p.inputs['Roughness'].default_value = .16
p.inputs['IOR'].default_value = 1.46
p.inputs['Alpha'].default_value = 1
tube_material.use_backface_culling = False

# Original 64x24 curved grids remain dense. Front/back radial offsets guarantee
# that the sealed paper never crosses the glass, including its side edges.
label_front = bpy.data.materials['White satin wrap label']
label_back = label_front.copy(); label_back.name = 'Unprinted ivory paper back and sealed edges'
for m in [label_front, label_back]:
    p = m.node_tree.nodes.get('Principled BSDF')
    p.inputs['Roughness'].default_value = .61
    p.inputs['Specular IOR Level'].default_value = .22

label_report = []
for cx, kind in [(-.7, 'LOTION'), (.7, 'WASH')]:
    old = bpy.data.objects[kind+' white wrap label']
    points = world_points(old)
    faces_front = [tuple(p.vertices) for p in old.data.polygons]
    front = []; back = []
    for p in points:
        x = p.x-cx; y = -math.sqrt(max(0, .575**2-x*x))
        front.append((cx+x*.579/.575, y*.579/.575, p.z))
        back.append((cx+x*.577/.575, y*.577/.575, p.z))
    n = len(front); faces = list(faces_front) + [tuple(n+v for v in reversed(f)) for f in faces_front]
    counts = {}
    for f in faces_front:
        for a,b in zip(f, f[1:]+f[:1]):
            k = tuple(sorted((a,b))); counts[k] = counts.get(k,0)+1
    boundary = [edge for edge,count in counts.items() if count==1]
    faces.extend((a,b,n+b,n+a) for a,b in boundary)
    mesh = bpy.data.meshes.new(kind+' closed curved paper solid')
    mesh.from_pydata(front+back, [], faces); mesh.update()
    ob = bpy.data.objects.new(kind+' physical white wrap label', mesh); scene.collection.objects.link(ob)
    ob.parent = roots['Label']; ob.location = -roots['Label'].location
    mesh.materials.append(label_front); mesh.materials.append(label_back)
    for i, face in enumerate(mesh.polygons):
        face.material_index = 0 if i < len(faces_front) else 1
        face.use_smooth = i < 2*len(faces_front)
    volume = manifold(ob)
    ob.visible_shadow = True
    ob['thickness'] = .002
    ob['closedBackRadius'] = .577
    ob['closedFrontRadius'] = .579
    bpy.data.objects.remove(old, do_unlink=True)
    label_report.append({'kind':kind,'vertices':len(mesh.vertices),'faces':len(mesh.polygons),
                         'thickness':.002,'minimumRadialGlassGap':.002,'positiveVolume':volume,
                         'frontBackEdgesSealed':True,'castsShadow':True})
    for name, radius, root in [(kind+' rotated product lettering', .581, 'NameInk'),
                               (kind+' white liaose', .5762, 'LogoInk')]:
        ink = bpy.data.objects[name]
        inv = ink.matrix_world.inverted()
        for v in ink.data.vertices:
            p = ink.matrix_world@v.co; x = p.x-cx
            p.x = cx+x*radius/.575
            p.y = -math.sqrt(max(0,.575**2-x*x))*radius/.575
            v.co = inv@p
        ink.data.update(); ink.visible_shadow = False
        ink['mechanicalRole'] = 'alpha-only ink, no opaque carrier rectangle or carrier shadow'

# Retain exact SVG text/spacing. Rasterize at 2048 pixels wide, keeping PNG alpha.
NODE = '/Users/icecream/.local/bin/node'
sharp = '/Users/icecream/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/sharp/dist/index.mjs'
artwork = []
for name in ['label-LOTION','label-WASH','liaose-white']:
    shutil.copy2(OLD/(name+'.svg'), HERE/(name+'.svg'))
    js = "import sharp from '"+sharp+"';await sharp(process.argv[1],{density:147.456}).resize({width:2048}).png().toFile(process.argv[2]);"
    subprocess.run([NODE,'--input-type=module','-e',js,str(HERE/(name+'.svg')),str(HERE/(name+'.png'))],check=True)
    image = bpy.data.images.load(str(HERE/(name+'.png')),check_existing=False); image.pack()
    material = bpy.data.materials[name]
    for node in material.node_tree.nodes:
        if node.type == 'TEX_IMAGE': node.image = image
    material.use_backface_culling = False
    artwork.append({'name':name,'sourceSvgUnchanged':(OLD/(name+'.svg')).read_bytes()==(HERE/(name+'.svg')).read_bytes(),
                    'svgSha256':hashlib.sha256((HERE/(name+'.svg')).read_bytes()).hexdigest(), 'size':list(image.size)})

# Merge by identical material per complete white pump; preserve original rib vertices.
rib_distances = []
for kind in ['LOTION','WASH']:
    obs = [o for o in roots['Pump'].children if o.type=='MESH' and o.name.startswith(kind) and 'dip tube' not in o.name]
    names = [o.name for o in obs]
    bpy.ops.object.select_all(action='DESELECT')
    for ob in obs: ob.select_set(True)
    bpy.context.view_layer.objects.active = next(o for o in obs if 'pump closure' in o.name)
    bpy.ops.object.join()
    joined = bpy.context.object; joined.name = kind+' complete white pump'
    joined['mergedMechanicalParts'] = json.dumps(names)
    joined['preservedRibs'] = 96
    manifold(joined)
    kd = __import__('mathutils').kdtree.KDTree(len(joined.data.vertices))
    for i,p in enumerate(world_points(joined)): kd.insert(p,i)
    kd.balance()
    error = max(kd.find(Vector(v))[2] for name,points in original_ribs.items() if name.startswith(kind) for v in points)
    assert error < 2e-6, (kind,error)
    rib_distances.append({'kind':kind,'maximumPreservedRibVertexError':error})

bpy.context.view_layer.update()
body_errors = {}
for name, points in original_bodies.items():
    current = world_points(bpy.data.objects[name])
    assert len(current)==len(points)
    error = max((a-Vector(b)).length for a,b in zip(current,points)); assert error==0
    body_errors[name] = error

config = json.loads((OLD/'review-product.json').read_text())
config['file'] = 'poster-084-v3.glb'
config['review']['appearance'].update(labelShadows=True, glass=True, frosted=False, referenceGlass=True,
                                     studio={'background':'#aebbc6','ink':'#273744'})
config['review']['explosion'].update(
    offsets={'body':[.75,0,0],'pump':[.75,2.55,0],'label':[-.90,.10,.95],
             'logo':[-1.50,.05,1.50],'print':[-1.65,.13,1.80]},
    scales={'label':1,'logo':1.65,'print':1.08},
    camera={'centerX':[0,-.25],'centerY':[1.5,2.65],'width':[3.8,7.3],'height':[3.7,6.5]},
    mobilePrintSpread=.75)
for part in config['parts']:
    if part['key']=='label':
        part['detail']=['实体薄纸标贴保留贴合曲面与封边，展开时在玻璃瓶上留下对应阴影。',
                        'Sealed thin paper labels retain their curvature and cast corresponding shadows on the glass.']
    if part['key']=='pump':
        part['detail']=['两套完整白色泵头、带出口的泵嘴、内腔接口与长空心吸管一起抬起。',
                        'Two complete white pumps, real nozzle openings, hollow connectors and long hollow dip tubes lift together.']
config['design']['background']='#aebbc6'
(HERE/'review-product.json').write_text(json.dumps(config,ensure_ascii=False,indent=2)+'\n')
rest = {n:o.location.copy() for n,o in roots.items()}
for frame,t in [(1,0),(31,.5),(61,1)]:
    scene.frame_set(frame)
    for part in config['parts']:
        ob=roots[part['node']]; key=part['key']; x,y,z=config['review']['explosion']['offsets'][key]
        ob.location=rest[ob.name]+Vector((x,-z,y))*t
        s=1+(config['review']['explosion']['scales'].get(key,1)-1)*t; ob.scale=(s,s,s)
        ob.keyframe_insert(data_path='location',frame=frame); ob.keyframe_insert(data_path='scale',frame=frame)
scene.frame_start=1;scene.frame_end=61;scene.frame_set(1);bpy.context.view_layer.update()
for frame,label in [(1,'CLOSED'),(31,'HALF EXPANDED'),(61,'FULLY EXPANDED')]:
    scene.timeline_markers.new(label,frame=frame)

import sys
sys.path.insert(0,str(HERE))
from optimize_meshes import optimize
mesh_optimization=optimize()
bpy.ops.object.select_all(action='DESELECT')
for root in roots.values():
    root.select_set(True)
    for child in root.children_recursive: child.select_set(True)
bpy.ops.export_scene.gltf(filepath=str(GLB),export_format='GLB',use_selection=True,export_yup=True,
                          export_extras=True,export_animations=False)
bpy.ops.file.pack_all()
bpy.ops.wm.save_as_mainfile(filepath=str(HERE/'poster-084-v3.blend'),compress=True)
report={'originalMeshCount':original_mesh_count,'newMeshCount':sum(o.type=='MESH' for o in scene.objects),
        'rootNames':list(ROOTS),'originalBodyWorldVertexError':body_errors,
        'preservedRibGeometry':rib_distances,'mechanical':mechanical,'labels':label_report,'artwork':artwork,
        'containsFormula':False,'glbBytes':GLB.stat().st_size,'glbSha256':hashlib.sha256(GLB.read_bytes()).hexdigest(),
        'sourceFrames':[1,31,61],'glbHasAnimation':False,'renderingPending':True,'productionRegistered':False,
        'meshOptimization':mesh_optimization}
(HERE/'build-verification.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
print('SOFT_BODY_084_V3_READY',json.dumps(report))
