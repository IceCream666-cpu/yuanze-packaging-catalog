"""Refine the approved Daily Emulsion with a captive hollow dip tube and thin film."""
import bpy, bmesh, math, json
from pathlib import Path
from mathutils import Vector
HERE=Path(__file__).resolve().parent;CLIENT=HERE.parents[3]
SOURCE=HERE.parents[1]/'daily-emulsion/daily-emulsion.blend'
bpy.ops.wm.open_mainfile(filepath=str(SOURCE))
scene=bpy.context.scene
for o in scene.objects:o.animation_data_clear()
pump=bpy.data.objects['PumpAssembly'];bpy.context.view_layer.update()
originals={o.name:[tuple(v.co) for v in o.data.vertices] for o in scene.objects if o.type=='MESH' and o.parent.name!='PaperLabel'}
def material(name,color,rough,trans=0):
 m=bpy.data.materials.new(name);m.use_nodes=True;p=m.node_tree.nodes.get('Principled BSDF')
 p.inputs['Base Color'].default_value=(*color,1);p.inputs['Roughness'].default_value=rough;p.inputs['Transmission Weight'].default_value=trans;p.inputs['IOR'].default_value=1.46
 return m
def mesh(name,vs,fs,mat,parent):
 d=bpy.data.meshes.new(name);d.from_pydata(vs,[],fs);d.update();o=bpy.data.objects.new(name,d);bpy.context.collection.objects.link(o);o.parent=parent;d.materials.append(mat)
 for f in d.polygons:f.use_smooth=True
 bm=bmesh.new();bm.from_mesh(d);bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(d);bm.free()
 return o
s=2.9/2.8;n=48;steps=64;vs=[];fs=[]
# A small bent inlet stays above the internal glass floor and reaches the fitted connector.
for radius in [.027,.017]:
 for j in range(steps+1):
  t=j/steps;z=.185+1.94*t;x=.10*(1-t)**3
  for i in range(n):
   a=math.tau*i/n;vs.append(tuple(pump.matrix_world.inverted()@Vector(((x+radius*math.cos(a))*s,radius*math.sin(a)*s,z*s))))
stride=(steps+1)*n
for side in range(2):
 for j in range(steps):
  for i in range(n):
   a=side*stride+j*n+i;b=side*stride+j*n+(i+1)%n;f=(a,b,b+n,a+n);fs.append(f if side==0 else f[::-1])
for j in [0,steps]:
 for i in range(n):
  a=j*n+i;b=j*n+(i+1)%n;fs.append((a,a+stride,b+stride,b))
tube=mesh('Daily long hollow dip tube with open inlet',vs,fs,material('Clear polyethylene hollow suction tube',(.94,.97,.95),.055,.98),pump)
bm=bmesh.new();bm.from_mesh(tube.data);assert all(e.is_manifold for e in bm.edges);assert bm.calc_volume(signed=True)>0;bm.free()
glass=bpy.data.materials['Daily neutral frosted empty glass'].node_tree.nodes['Principled BSDF']
glass.inputs['Transmission Weight'].default_value=.94;glass.inputs['Roughness'].default_value=.28
# The reference is directly printed; this subtle rounded film explains the separated print layers.
label=bpy.data.objects['PaperLabel'];old=label.children[0];bpy.data.objects.remove(old,do_unlink=True)
outline=[]
for x,z,start in [(.33-.025,.45-.025,0),(-.33+.025,.45-.025,90),(-.33+.025,-.45+.025,180),(.33-.025,-.45+.025,270)]:
 for i in range(16):
  a=math.radians(start+90*i/16);outline.append((x+.025*math.cos(a),-.2914,z+.025*math.sin(a)))
fm=material('Daily clear rounded print film',(.95,.96,.92),.32);fm.surface_render_method='DITHERED';alpha=fm.node_tree.nodes['Principled BSDF'].inputs['Alpha'];alpha.default_value=.035
film=mesh('Daily rounded thin transparent print carrier',[(0,-.2914,0)]+outline,[(0,i+1,(i+1)%len(outline)+1) for i in range(len(outline))],fm,label)
mod=film.modifiers.new('Thin film edge','SOLIDIFY');mod.thickness=.001
bpy.context.view_layer.objects.active=film;film.select_set(True);bpy.ops.object.modifier_apply(modifier=mod.name)
for f in film.data.polygons:f.use_smooth=False
fm.node_tree.nodes['Principled BSDF'].inputs['Specular IOR Level'].default_value=.15
for root in ['LogoPrint','ProductPrint']:
 for o in bpy.data.objects[root].children:o.visible_shadow=False
for name,coords in originals.items():assert coords==[tuple(v.co) for v in bpy.data.objects[name].data.vertices],name
p=json.loads((HERE/'review-product.json').read_text());roots={v['node']:bpy.data.objects[v['node']] for v in p['parts']};ex=p['review']['explosion'];rest={n:(o.location.copy(),o.scale.copy()) for n,o in roots.items()}
for frame,t in [(1,0),(31,.5),(61,1)]:
 for part in p['parts']:
  k,n=part['key'],part['node'];o=roots[n];pos,sc=rest[n];x,y,z=ex['offsets'][k];o.location=pos+Vector((x,-z,y))*t;o.scale=sc*(1+(ex['scales'].get(k,1)-1)*t);o.keyframe_insert(data_path='location',frame=frame);o.keyframe_insert(data_path='scale',frame=frame)
 alpha.default_value=[.035,.26,.28][[1,31,61].index(frame)];alpha.keyframe_insert(data_path='default_value',frame=frame)
scene.frame_set(1);bpy.context.view_layer.update();bpy.ops.object.select_all(action='DESELECT')
for o in roots.values():
 o.select_set(True)
 for child in o.children_recursive:child.select_set(True)
bpy.ops.export_scene.gltf(filepath=str(CLIENT/'packaging-assets/poster-072-v2.glb'),export_format='GLB',use_selection=True,export_apply=True,export_yup=True,export_animations=False,export_extras=True)
bpy.context.preferences.filepaths.save_version=0;bpy.ops.file.pack_all();bpy.ops.wm.save_as_mainfile(filepath=str(HERE/'poster-072-v2.blend'),compress=True)
(HERE/'build-verification.json').write_text(json.dumps({'roots':list(roots),'preservedMeshes':list(originals),'tubeBottomZ':.185*s,'tubeTopZ':2.125*s,'tubeOuterDiameter':.054*s,'tubeInnerDiameter':.034*s,'openBore':True,'containsFormula':False,'illustrativeInterior':True,'source':'../../daily-emulsion/daily-emulsion.blend'},indent=2)+'\n')
