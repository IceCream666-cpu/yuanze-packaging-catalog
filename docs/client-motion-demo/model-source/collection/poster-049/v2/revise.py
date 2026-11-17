"""Revise the approved 049 source without rebuilding its bottle or silver pump."""
import bpy, math, json
import numpy as np
from pathlib import Path
from mathutils import Vector
HERE=Path(__file__).resolve().parent; CLIENT=HERE.parents[3]
bpy.ops.wm.open_mainfile(filepath=str(HERE.parent/'poster-049.blend'))
scene=bpy.context.scene
for o in scene.objects:o.animation_data_clear()
pump=bpy.data.objects['PumpAssembly'];bpy.context.view_layer.update()
originals={o.name:[tuple(v.co) for v in o.data.vertices] for o in scene.objects if o.type=='MESH' and o.parent and o.parent.name not in ['PaperLabel','LogoPrint']}
def mat(name,color,rough=.3,trans=0):
 m=bpy.data.materials.new(name);m.use_nodes=True;p=m.node_tree.nodes.get('Principled BSDF')
 p.inputs['Base Color'].default_value=(*color,1);p.inputs['Roughness'].default_value=rough;p.inputs['Transmission Weight'].default_value=trans;p.inputs['IOR'].default_value=1.46
 return m
def mesh(name,vs,fs,material,parent):
 data=bpy.data.meshes.new(name);data.from_pydata(vs,[],fs);data.update();o=bpy.data.objects.new(name,data);bpy.context.collection.objects.link(o);o.parent=parent;o.data.materials.append(material)
 for f in data.polygons:f.use_smooth=True
 return o
s=2.9/2.45
# True open tube, near-floor inlet, retaining a broad enough bore for a lotion pump.
vs=[];fs=[];n=48;steps=56
for rad in [.035,.023]:
 for j in range(steps+1):
  t=j/steps;z=.145+1.585*t;x=.13*(1-t)**3
  for i in range(n):
   a=math.tau*i/n;w=Vector(((x+rad*math.cos(a))*s,rad*math.sin(a)*s,z*s));vs.append(tuple(pump.matrix_world.inverted()@w))
stride=(steps+1)*n
for side in range(2):
 for j in range(steps):
  for i in range(n):
   a=side*stride+j*n+i;b=side*stride+j*n+(i+1)%n;f=(a,b,b+n,a+n);fs.append(f if side==0 else f[::-1])
for j in [0,steps]:
 for i in range(n):a=j*n+i;b=j*n+(i+1)%n;fs.append((a,a+stride,b+stride,b))
tube=mesh('Long hollow dip tube with open inlet',vs,fs,mat('Clear polyethylene hollow suction tube',(.92,.96,.94),.055,.98),pump)
# The tube enters the concealed polymer connector below the actuator.
vs=[];fs=[]
profile=[(1.68,.034),(1.69,.065),(1.82,.065),(1.84,.09),(1.87,.09),(1.87,.025),(1.68,.025),(1.68,.034)]
for z,rad in profile:
 for i in range(64):
  a=math.tau*i/64;vs.append(tuple(pump.matrix_world.inverted()@Vector((rad*math.cos(a)*s,rad*math.sin(a)*s,z*s))))
for j in range(len(profile)-1):
 for i in range(64):a=j*64+i;b=j*64+(i+1)%64;fs.append((a,b,b+64,a+64))
mesh('Fitted internal pump connector',vs,fs,mat('Ivory polymer pump connector',(.76,.75,.69),.32),pump)
# Replace a rectangular alpha card with the matching curved, rounded paper outline.
label=bpy.data.objects['PaperLabel'];old=bpy.data.objects['Ivory paper label'];bpy.data.objects.remove(old,do_unlink=True)
outline=[]
for cx,cz,start in [(.497-.420,.577-.420,0),(-.497+.420,.577-.420,90),(-.497+.420,-.577+.420,180),(.497-.420,-.577+.420,270)]:
 for i in range(32):
  a=math.radians(start+90*i/32);outline.append(((cx+.420*math.cos(a))*.810,(cz+.420*math.sin(a))*.940/1.160))
# Sample straight spans too: long chords would sink below the cylindrical bottle.
dense=[]
for a,b in zip(outline,outline[1:]+outline[:1]):
 count=max(1,math.ceil(math.dist(a,b)/.008))
 for i in range(count):dense.append(tuple(a[k]+(b[k]-a[k])*i/count for k in range(2)))
outline=dense
vs=[(0,-.5015,0)];fs=[];rings=24;n=len(outline)
for j in range(1,rings+1):
 for x,z in outline:
  x*=j/rings;z*=j/rings;vs.append((x,-math.sqrt(.25-x*x)-.0015,z))
for i in range(n):fs.append((0,1+i,1+(i+1)%n))
for j in range(rings-1):
 for i in range(n):a=1+j*n+i;b=1+j*n+(i+1)%n;fs.append((a,a+n,b+n,b))
# Front faces must face the camera at Blender -Y.
ob=mesh('Solid curved ivory paper label',vs,fs,mat('Moisture ivory paper stock',(.904,.871,.784),.72),label)
mod=ob.modifiers.new('Paper edge thickness','SOLIDIFY');mod.thickness=.0012
bpy.context.view_layer.objects.active=ob;ob.select_set(True);bpy.ops.object.modifier_apply(modifier=mod.name)
# Split the existing raster ink at a blank gap; every printed pixel is retained.
ink=bpy.data.objects['LogoPrint'];ink.name='LogoInk';logo=ink.children[0]
for v in logo.data.vertices:v.co.y-=.003
new=bpy.data.objects.new('ProductPrint',None);bpy.context.collection.objects.link(new);new.matrix_world=ink.matrix_world.copy()
copy=logo.copy();copy.data=logo.data.copy();copy.name='Product name and separator rules';bpy.context.collection.objects.link(copy);copy.parent=new;copy.matrix_basis=logo.matrix_basis.copy()
source=next(n.image for n in logo.active_material.node_tree.nodes if n.type=='TEX_IMAGE');w,h=source.size
pixels=np.array(source.pixels[:],dtype=np.float32).reshape(h,w,4);split=int(h*(1-550/1160))
for target,part in [(logo,'logo'),(copy,'product-print')]:
 data=pixels.copy()
 if part=='logo':data[:split,:,3]=0
 else:data[split:,:,3]=0
 img=bpy.data.images.new('Moisture '+part,width=w,height=h,alpha=True);img.pixels.foreach_set(data.ravel());img.filepath_raw=str(HERE/(part+'.png'));img.file_format='PNG';img.save();img.pack()
 m=target.active_material.copy();m.name='Moisture '+part+' ink';target.data.materials.clear();target.data.materials.append(m)
 next(n for n in m.node_tree.nodes if n.type=='TEX_IMAGE').image=img;target.visible_shadow=False
# Preserve all already approved bottle and pump vertices.
for name,coords in originals.items():assert coords==[tuple(v.co) for v in bpy.data.objects[name].data.vertices],name
p=json.loads((HERE/'review-product.json').read_text());roots={v['node']:bpy.data.objects[v['node']] for v in p['parts']}
rest={n:(o.location.copy(),o.scale.copy()) for n,o in roots.items()};ex=p['review']['explosion']
for frame,t in [(1,0),(31,.5),(61,1)]:
 for part in p['parts']:
  k,n=part['key'],part['node'];o=roots[n];pos,sc=rest[n];x,y,z=ex['offsets'][k];o.location=pos+Vector((x,-z,y))*t;o.scale=sc*(1+(ex['scales'].get(k,1)-1)*t);o.keyframe_insert(data_path='location',frame=frame);o.keyframe_insert(data_path='scale',frame=frame)
scene.frame_set(1);bpy.context.view_layer.update();bpy.ops.object.select_all(action='DESELECT')
for o in roots.values():
 o.select_set(True)
 for c in o.children_recursive:c.select_set(True)
bpy.ops.export_scene.gltf(filepath=str(CLIENT/'packaging-assets/poster-049-v2.glb'),export_format='GLB',use_selection=True,export_apply=True,export_yup=True,export_animations=False,export_extras=True)
bpy.context.preferences.filepaths.save_version=0;bpy.ops.file.pack_all();bpy.ops.wm.save_as_mainfile(filepath=str(HERE/'poster-049-v2.blend'),compress=True)
(HERE/'build-verification.json').write_text(json.dumps({'roots':list(roots),'preservedMeshes':list(originals),'tubeBottomZ':.145*s,'tubeTopZ':1.73*s,'tubeOuterDiameter':.070*s,'tubeInnerDiameter':.046*s,'openBore':True,'containsFormula':False,'illustrativeInterior':True,'source':'../poster-049.blend'},indent=2)+'\n')
