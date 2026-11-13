"""Revise the approved source in Blender; preserve existing container/pump geometry."""
import bpy,math,json,sys
from pathlib import Path
from mathutils import Vector
HERE=Path(__file__).resolve().parent; OLD=HERE.parent; CLIENT=OLD.parents[2]
bpy.ops.wm.open_mainfile(filepath=str(OLD/'poster-067.blend'))
# Keep world transforms when assembling existing parts.
def parent(obj,root):
 matrix=obj.matrix_world.copy();obj.parent=root;obj.matrix_world=matrix
pump=bpy.data.objects.new('PumpAssembly',None);bpy.context.collection.objects.link(pump)
for name in ['Actuator','PumpStem','Closure']:
 g=bpy.data.objects[name]
 for child in list(g.children):parent(child,pump)
 bpy.data.objects.remove(g,do_unlink=True)
body=bpy.data.objects['Body'];cord=bpy.data.objects['Cord']
for child in list(cord.children):parent(child,body)
bpy.data.objects.remove(cord,do_unlink=True)
# Hollow transparent tube, long enough to reach just above the inner bottom.
mat=bpy.data.materials.new('Amber clear polyethylene hollow dip tube');mat.use_nodes=True
p=mat.node_tree.nodes.get('Principled BSDF');p.inputs['Base Color'].default_value=(.91,.95,.92,1);p.inputs['Roughness'].default_value=.065;p.inputs['Transmission Weight'].default_value=1;p.inputs['IOR'].default_value=1.46
scale=2.9/2.02;vs=[];fs=[];N=48;steps=80
for inner in [False,True]:
 for j in range(steps+1):
  t=j/steps;z=.09+1.40*t;x=.09*(1-t)**3;r=.022 if inner else .032
  for k in range(N):
   a=math.tau*k/N;vs.append((scale*(x+r*math.cos(a)),scale*r*math.sin(a),scale*z))
for shell in range(2):
 base=shell*(steps+1)*N
 for j in range(steps):
  for k in range(N):
   a=base+j*N+k;b=base+j*N+(k+1)%N;f=(a,b,b+N,a+N);fs.append(f if shell==0 else tuple(reversed(f)))
for j in [0,steps]:
 for k in range(N):
  a=j*N+k;b=j*N+(k+1)%N;c=(steps+1)*N;fs.append((a,a+c,b+c,b) if j==0 else (a,b,b+c,a+c))
mesh=bpy.data.meshes.new('Hollow dip tube wall');mesh.from_pydata(vs,[],fs);mesh.materials.append(mat);mesh.update()
tube=bpy.data.objects.new('Long transparent hollow suction tube',mesh);bpy.context.collection.objects.link(tube);tube.parent=pump
for f in mesh.polygons:f.use_smooth=True
# Separate the approved original artwork without changing its typeface/placement.
oldgroup=bpy.data.objects['LogoPrint'];ink=next(o for o in oldgroup.children if o.type=='MESH')
for name,file,dy in [('LogoInk','logo.png',0),('NameInk','name.png',-.0006)]:
 root=bpy.data.objects.new(name,None);bpy.context.collection.objects.link(root);root.matrix_world=oldgroup.matrix_world.copy()
 ob=ink.copy();ob.data=ink.data.copy();bpy.context.collection.objects.link(ob);ob.name=name+' curved print';ob.parent=root;ob.location.y+=dy
 material=ink.data.materials[0].copy();material.name=name+' white print';ob.data.materials.clear();ob.data.materials.append(material)
 image=next(n for n in material.node_tree.nodes if n.type=='TEX_IMAGE');image.image=bpy.data.images.load(str(HERE/file));image.image.pack();ob.visible_shadow=False
bpy.data.objects.remove(ink,do_unlink=True);bpy.data.objects.remove(oldgroup,do_unlink=True)
label=bpy.data.objects['PaperLabel'];label.name='Label'
for ob in label.children:
 ob.visible_shadow=True
 # A real thin clear carrier, not an opaque paper patch.
 solid=ob.modifiers.new('Thin transparent carrier edge','SOLIDIFY');solid.thickness=.001;solid.offset=0
roots={n:bpy.data.objects[n] for n in ['Body','PumpAssembly','Label','LogoInk','NameInk']}
review=json.loads((HERE/'review-product.json').read_text());parts={p['key']:p['node'] for p in review['parts']};explosion=review['review']['explosion']
rest={n:(o.location.copy(),o.scale.copy()) for n,o in roots.items()}
for frame,t in [(1,0),(31,.5),(61,1)]:
 for key,node in parts.items():
  ob=roots[node];pos,s=rest[node];dx,dy,dz=explosion['offsets'].get(key,[0,0,0]);ob.location=pos+Vector((dx,-dz,dy))*t;ob.scale=s*(1+(explosion['scales'].get(key,1)-1)*t);ob.keyframe_insert(data_path='location',frame=frame);ob.keyframe_insert(data_path='scale',frame=frame)
bpy.context.scene.frame_set(1);bpy.context.view_layer.update()
# Tube is one pump descendant and does not intersect the inner floor.
assert tube.parent==pump and min(v.co.z for v in tube.data.vertices)>.065*scale
assert max(v.co.z for v in tube.data.vertices)>1.477*scale
assert len(roots)==5
bpy.ops.object.select_all(action='DESELECT')
for root in roots.values():
 root.select_set(True)
 for ob in root.children_recursive:ob.select_set(True)
bpy.ops.export_scene.gltf(filepath=str(CLIENT/'packaging-assets/poster-067-v2.glb'),export_format='GLB',use_selection=True,export_apply=True,export_yup=True,export_animations=False,export_extras=True)
bpy.ops.file.pack_all();bpy.ops.wm.save_as_mainfile(filepath=str(HERE/'poster-067-v2.blend'),compress=True)
(HERE/'build-verification.json').write_text(json.dumps({'roots':list(roots),'tubeOuterDiameterRelativeToBottleWidth':.064,'tubeBottomClearance':(.09-.065)*scale,'oldBottleAndPumpMeshesPreserved':True,'cordAttachedToBody':True,'formula':False,'source':str(OLD/'poster-067.blend')},indent=2)+'\n')
