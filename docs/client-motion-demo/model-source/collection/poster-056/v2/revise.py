"""Refine the approved Golden Face Oil source, retaining its measured silhouette.

The reference is directly printed. Its physical clear carrier is an explanatory
exploded layer, not a claim that a paper label is present on the real bottle.
"""
import bpy, bmesh, math, json, hashlib
from pathlib import Path
from mathutils import Vector, Matrix

HERE=Path(__file__).resolve().parent
CLIENT=HERE.parents[3]
SOURCE=HERE.parent/'poster-056.blend'
S=2.9/1.41
bpy.ops.wm.open_mainfile(filepath=str(SOURCE))
scene=bpy.context.scene
scene.frame_set(1)
for o in scene.objects:o.animation_data_clear()
bpy.context.view_layer.update()
root_names=['Body','Overcap','PaperLabel','LogoPrint','PumpAssembly']
roots={name:bpy.data.objects[name] for name in root_names}
original={}
mesh_roots={}
for o in [o for o in scene.objects if o.type=='MESH']:
    ancestor=o
    while ancestor.parent:ancestor=ancestor.parent
    assert ancestor.name in roots,ancestor.name
    original[o.name]={'worldVertices':[o.matrix_world@v.co for v in o.data.vertices], 'vertexCount':len(o.data.vertices),'faceCount':len(o.data.polygons)}
    mesh_roots[o.name]=ancestor.name
root_locations={name:o.matrix_world.translation.copy() for name,o in roots.items()}
# Bake nested historical scale into mesh coordinates without changing positions.
for name,o in roots.items():
    o.parent=None;o.location=root_locations[name];o.rotation_euler=(0,0,0);o.scale=(1,1,1)
for name,record in original.items():
    o=bpy.data.objects[name];root=roots[mesh_roots[name]]
    for v,world in zip(o.data.vertices,record['worldVertices']):v.co=world-root.location
    o.parent=root;o.matrix_parent_inverse=Matrix.Identity(4);o.location=(0,0,0);o.rotation_euler=(0,0,0);o.scale=(1,1,1);o.data.update()
for o in list(scene.objects):
    if o.type=='EMPTY' and o.name not in roots:bpy.data.objects.remove(o,do_unlink=True)
bpy.context.view_layer.update()
normalized_errors={name:max((bpy.data.objects[name].matrix_world@v.co-p).length for v,p in zip(bpy.data.objects[name].data.vertices,data['worldVertices'])) for name,data in original.items()}
assert max(normalized_errors.values())<1e-6

def material(name,hexcolor,rough,trans=0):
    m=bpy.data.materials.new(name);m.use_nodes=True
    p=m.node_tree.nodes.get('Principled BSDF')
    rgb=[int(hexcolor[i:i+2],16)/255 for i in (1,3,5)]
    p.inputs['Base Color'].default_value=(*[v/12.92 if v<=.04045 else ((v+.055)/1.055)**2.4 for v in rgb],1)
    p.inputs['Roughness'].default_value=rough;p.inputs['Transmission Weight'].default_value=trans;p.inputs['IOR'].default_value=1.49
    return m

def make_mesh(name,world_vertices,faces,mat,root_name):
    root=roots[root_name]
    data=bpy.data.meshes.new(name);data.from_pydata([Vector(v)-root.location for v in world_vertices],[],faces);data.update()
    o=bpy.data.objects.new(name,data);bpy.context.collection.objects.link(o);o.parent=root;data.materials.append(mat)
    return o

def clean_solid(o,triangulate=False):
    bm=bmesh.new();bm.from_mesh(o.data)
    bmesh.ops.remove_doubles(bm,verts=list(bm.verts),dist=1e-7)
    bmesh.ops.dissolve_degenerate(bm,edges=list(bm.edges),dist=1e-7)
    loose=[v for v in bm.verts if not v.link_edges]
    if loose:bmesh.ops.delete(bm,geom=loose,context='VERTS')
    if triangulate:bmesh.ops.triangulate(bm,faces=list(bm.faces),quad_method='BEAUTY',ngon_method='BEAUTY')
    bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces))
    if bm.calc_volume(signed=True)<0:bmesh.ops.reverse_faces(bm,faces=list(bm.faces))
    assert all(e.is_manifold for e in bm.edges),o.name
    volume=bm.calc_volume(signed=True);assert volume>0,(o.name,volume)
    bm.to_mesh(o.data);bm.free();o.data.update();return volume

def polished_normals(o):
    for f in o.data.polygons:f.use_smooth=True
    bpy.ops.object.select_all(action='DESELECT');o.select_set(True);bpy.context.view_layer.objects.active=o
    mod=o.modifiers.new('Polished flat panels and soft edge normals','WEIGHTED_NORMAL');mod.keep_sharp=True;mod.weight=50
    bpy.ops.object.modifier_apply(modifier=mod.name)

def lathe(name,profile,mat,root_name,n=128):
    vertices=[];faces=[]
    for z,r in profile:
        for i in range(n):
            a=math.tau*i/n;vertices.append((r*S*math.cos(a),r*S*math.sin(a),z*S))
    for j in range(len(profile)-1):
        for i in range(n):
            k=j*n+i;next_k=j*n+(i+1)%n;faces.append((k,next_k,next_k+n,k+n))
    o=make_mesh(name,vertices,faces,mat,root_name);clean_solid(o)
    for f in o.data.polygons:f.use_smooth=abs(f.normal.z)<.999
    return o

# Keep the approved hollow bottle and its thick base exactly. Frost belongs on
# the outside; a clearer interior and bottom edge preserve genuine glass depth.
body=bpy.data.objects['Hollow rounded rectangular bottle with thick clear base']
outer_glass=material('Golden frosted outer empty glass','#ffffff',.255,1)
inner_glass=material('Golden polished inner glass and thick base','#ffffff',.085,1)
for m in [outer_glass,inner_glass]:
    p=m.node_tree.nodes['Principled BSDF'];p.inputs['IOR'].default_value=1.49;p.inputs['Coat Weight'].default_value=.035;p.inputs['Coat Roughness'].default_value=.12
body.data.materials.clear();body.data.materials.append(outer_glass);body.data.materials.append(inner_glass)
material_counts={'frostedOuter':0,'polishedInnerAndBase':0}
for f in body.data.polygons:
    c=f.center
    inner=f.normal.dot(Vector((c.x,c.y,0)))<-.001
    lower=c.z<.08*S or (c.z<.17*S and f.normal.z>.5)
    f.material_index=1 if inner or lower else 0
    material_counts['polishedInnerAndBase' if f.material_index else 'frostedOuter']+=1

# Keep the already approved continuous U-skirt hood, including its small bevel.
# A wider bevel was visually rejected: thin-wall joins generated pinched miters.
cover=bpy.data.objects['Hollow olive cover with matching front and rear U skirts']
cover.name='Olive protective cover with original continuous U skirts'
cover_mat=material('Golden deep olive translucent polished protective cover','#4b5524',.085,.93)
cp=cover_mat.node_tree.nodes['Principled BSDF'];cp.inputs['Coat Weight'].default_value=.24;cp.inputs['Coat Roughness'].default_value=.075
cover.data.materials.clear();cover.data.materials.append(cover_mat)
# Do not re-bevel or subdivide this accepted profile; preserve original normals.
bm=bmesh.new();bm.from_mesh(cover.data)
assert all(e.is_manifold for e in bm.edges)
cover_volume=bm.calc_volume(signed=True);assert cover_volume>0;bm.free()
cover['front_and_rear_u_skirt_match']=True;cover['nominal_wall_thickness']=.012*S;cover['bevel_width']=.0025*S

# A hollow connector accepts the existing open dip tube instead of plugging it.
old_stem=bpy.data.objects['Short illustrative connecting stem'];stem_mat=old_stem.data.materials[0]
bpy.data.objects.remove(old_stem,do_unlink=True)
stem=lathe('Hollow olive pump connector with tube socket',[(.969,.028),(.969,.062),(.976,.071),(1.044,.071),(1.053,.064),(1.053,.022),(.998,.022),(.991,.028),(.969,.028)],stem_mat,'PumpAssembly')
stem['hidden_geometry_illustrative']=True;stem['open_bore']=True

# Retain the tall cylindrical actuator and add a small recessed side outlet.
# No long nozzle is invented. This hidden dispensing detail is illustrative.
actuator=bpy.data.objects['Tall cylindrical press actuator']
bpy.ops.mesh.primitive_cylinder_add(vertices=64,radius=.012*S,depth=.09*S,location=(0,-.127*S,1.25*S),rotation=(math.pi/2,0,0))
cutter=bpy.context.object;cutter.name='Temporary side outlet cutter'
bpy.context.view_layer.objects.active=actuator
boolean=actuator.modifiers.new('Small recessed dispensing outlet','BOOLEAN');boolean.operation='DIFFERENCE';boolean.solver='EXACT';boolean.object=cutter
bpy.ops.object.modifier_apply(modifier=boolean.name);bpy.data.objects.remove(cutter,do_unlink=True)
for f in actuator.data.polygons:f.material_index=0
for i in reversed(range(len(actuator.data.materials))):
    if actuator.data.materials[i] is None:actuator.data.materials.pop(index=i)
clean_solid(actuator,True);polished_normals(actuator)
# The small Boolean outlet creates long side triangles. Their default averaged
# normals pinch specular stripes; restore the untouched cylinder's radial normal
# on outer vertical faces while retaining the cavity/rim normals.
actuator_normals=[Vector(n.vector) for n in actuator.data.corner_normals]
for face in actuator.data.polygons:
    radial=Vector((face.center.x,face.center.y,0)).normalized()
    if abs(face.normal.z)<.15 and face.normal.dot(radial)>.985:
        for li in face.loop_indices:
            co=actuator.data.vertices[actuator.data.loops[li].vertex_index].co
            actuator_normals[li]=Vector((co.x,co.y,0)).normalized()
actuator.data.normals_split_custom_set(actuator_normals)
actuator['hidden_outlet_illustrative']=True;actuator['outlet_diameter']=.024*S

def ink_material(name,path):
    m=material(name,'#ffffff',.6);p=m.node_tree.nodes['Principled BSDF'];p.inputs['Specular IOR Level'].default_value=.015
    tex=m.node_tree.nodes.new('ShaderNodeTexImage');tex.image=bpy.data.images.load(str(path),check_existing=False);tex.image.pack()
    m.node_tree.links.new(tex.outputs['Color'],p.inputs['Base Color']);m.node_tree.links.new(tex.outputs['Alpha'],p.inputs['Alpha'])
    m.surface_render_method='BLENDED';return m

original_ink=roots['LogoPrint'].children[0]
original_ink.name='Golden original liaose print layer'
original_ink.data.name='Golden original liaose UV layer'
original_ink.data.materials.clear();original_ink.data.materials.append(ink_material('Golden original liaose alpha ink, no carrier shadow',HERE/'logo.png'))
product_root=bpy.data.objects.new('ProductPrint',None);bpy.context.collection.objects.link(product_root);product_root.location=roots['LogoPrint'].location;roots['ProductPrint']=product_root
product=original_ink.copy();product.data=original_ink.data.copy();product.name='Golden original product-name print layer';product.parent=product_root;product.location.y-=.0003;bpy.context.collection.objects.link(product)
product.data.name='Golden original product-name UV layer'
product.data.materials.clear();product.data.materials.append(ink_material('Golden original product-name alpha ink, no carrier shadow',HERE/'product.png'))
for o in [original_ink,product]:o.visible_shadow=False;o['castShadow']=False;o['original_lettering_preserved']=True

# A sealed thin clear film carries no printed rectangle or artificial paper tint.
old_film=roots['PaperLabel'].children[0];bpy.data.objects.remove(old_film,do_unlink=True)
film_mat=material('Golden clear illustrative print carrier','#fffdf7',.18,.35)
fp=film_mat.node_tree.nodes['Principled BSDF'];fp.inputs['Alpha'].default_value=.004;fp.inputs['Specular IOR Level'].default_value=.17
film_mat.surface_render_method='BLENDED'
rx=.31*S;rz=.175*S;r=.023*S;center_z=.3*S;y=-.1714*S;thickness=.0009
outline=[]
for x,z,start in [(rx-r,rz-r,0),(-rx+r,rz-r,90),(-rx+r,-rz+r,180),(rx-r,-rz+r,270)]:
    for i in range(20):
        a=math.radians(start+i*90/20);outline.append((x+r*math.cos(a),z+r*math.sin(a)+center_z))
n=len(outline);verts=[(x,y,z) for x,z in outline]+[(x,y+thickness,z) for x,z in outline]
faces=[tuple(range(n)),tuple(range(n,2*n))[::-1]]+[(i,(i+1)%n,(i+1)%n+n,i+n) for i in range(n)]
film=make_mesh('Golden closed rounded transparent print carrier',verts,faces,film_mat,'PaperLabel');film_volume=clean_solid(film,True)
for f in film.data.polygons:f.use_smooth=False
film.visible_shadow=True;film['castShadow']=True;film['physical_thickness']=thickness;film['illustrative_carrier_for_direct_print']=True

preserved=['Hollow rounded rectangular bottle with thick clear base','Olive stepped pump collar','Hollow clear Golden pump dip tube','Subtle actuator top inset']
bpy.context.view_layer.update()
preserved_report={}
for name in preserved:
    o=bpy.data.objects[name];old=original[name]
    assert len(o.data.vertices)==old['vertexCount'] and len(o.data.polygons)==old['faceCount']
    error=max((o.matrix_world@v.co-p).length for v,p in zip(o.data.vertices,old['worldVertices']));assert error<1e-6
    preserved_report[name]={'vertices':len(o.data.vertices),'polygons':len(o.data.polygons),'maximumWorldError':error}
old_cover_record=original['Hollow olive cover with matching front and rear U skirts']
cover_error=max((cover.matrix_world@v.co-p).length for v,p in zip(cover.data.vertices,old_cover_record['worldVertices']))
assert cover_error<1e-6 and len(cover.data.vertices)==old_cover_record['vertexCount'] and len(cover.data.polygons)==old_cover_record['faceCount']
preserved_report[cover.name]={'sourceMeshName':'Hollow olive cover with matching front and rear U skirts','vertices':len(cover.data.vertices),'polygons':len(cover.data.polygons),'maximumWorldError':cover_error}

config=json.loads((HERE/'review-product.json').read_text());ex=config['review']['explosion']
rest={name:(o.location.copy(),o.scale.copy()) for name,o in roots.items()}
for frame,t in [(1,0),(31,.5),(61,1)]:
    for part in config['parts']:
        key,name=part['key'],part['node'];o=roots[name];position,scale=rest[name];x,y,z=ex['offsets'][key]
        amount=t
        if key in ex.get('timing',{}):
            start,end=ex['timing'][key];amount=max(0,min(1,(t-start)/(end-start)));amount=amount**2*(3-2*amount)
        o.location=position+Vector((x,-z,y))*amount;o.scale=scale*(1+(ex['scales'].get(key,1)-1)*amount)
        o.keyframe_insert(data_path='location',frame=frame);o.keyframe_insert(data_path='scale',frame=frame)
    film_progress=max(0,min(1,(t-.03)/(.6-.03)));film_progress=film_progress**2*(3-2*film_progress)
    fp.inputs['Alpha'].default_value=.004+.156*film_progress;fp.inputs['Alpha'].keyframe_insert(data_path='default_value',frame=frame)
scene.frame_start=1;scene.frame_end=61
for name,frame in [('Closed',1),('Half expanded',31),('Fully expanded',61)]:scene.timeline_markers.new(name,frame=frame)
scene.frame_set(1);bpy.context.view_layer.update()
scene.render.engine='CYCLES';scene.cycles.samples=64;scene.cycles.use_denoising=True
scene['model_id']='poster-056';scene['model_version']='v2';scene['contains_formula']=False
scene['carrier_interpretation']='Direct-print reference; clear film is a separated-layer illustration, no paper label claimed.'
scene['hidden_geometry']='Pump connector bore, small side outlet and tube fitting are illustrative; no measured engineering drawing available.'
for mat in list(bpy.data.materials):
    if mat.users==0:bpy.data.materials.remove(mat)
for image in list(bpy.data.images):
    if image.users==0:bpy.data.images.remove(image)
bpy.ops.object.select_all(action='DESELECT')
for o in roots.values():
    o.select_set(True)
    for child in o.children_recursive:child.select_set(True)
glb=CLIENT/'packaging-assets/poster-056-v2.glb'
bpy.ops.export_scene.gltf(filepath=str(glb),export_format='GLB',use_selection=True,export_apply=True,export_yup=True,export_animations=False,export_extras=True)
bpy.context.preferences.filepaths.save_version=0;bpy.ops.file.pack_all();bpy.ops.wm.save_as_mainfile(filepath=str(HERE/'poster-056-v2.blend'),compress=True)
root_report={name:{'location':list(o.location),'scale':list(o.scale),'meshes':[{'name':m.name,'vertices':len(m.data.vertices),'polygons':len(m.data.polygons),'materials':[mat.name for mat in m.data.materials],'visibleShadow':m.visible_shadow} for m in o.children_recursive if m.type=='MESH']} for name,o in roots.items()}
report={'source':str(SOURCE),'sourceSha256':hashlib.sha256(SOURCE.read_bytes()).hexdigest(),'coordinateScale':S,'preservedGeometry':preserved_report,'initialNormalizationErrors':normalized_errors,'roots':root_report,'bodyMaterialFaceCounts':material_counts,'coverClosedManifold':True,'coverVolume':cover_volume,'coverWallThickness':.012*S,'coverBevelWidth':.0025*S,'carrierClosedManifold':True,'carrierVolume':film_volume,'carrierThickness':thickness,'carrierInterpretation':'Illustrative clear layer for directly printed reference','carrierBackToBodyFrontGap':(.1714-.17)*S-thickness,'tubeBottomToInteriorFloorGap':(.18-.14)*S,'tubeToConnectorSocketRadialClearance':(.028-.0275)*S,'tubeToConnectorAxialEngagement':(.99-.969)*S,'nominalGlassWallThickness':.032*S,'nominalGlassBaseThickness':.14*S,'containsFormula':False,'hiddenPumpDetailsIllustrative':True,'sourcePoseFrames':[1,31,61],'glbAnimationRequested':False,'glbBytes':glb.stat().st_size,'visualReviewPending':True,'productionRegistered':False}
(HERE/'build-verification.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
print('GOLDEN_056_BUILD',json.dumps({'glbBytes':glb.stat().st_size,'roots':list(roots),'filmBackGap':report['carrierBackToBodyFrontGap'],'coverManifold':True,'originalBottlePreserved':True}))
