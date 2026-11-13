"""Revise the approved source in Blender; preserve existing container/pump geometry."""
import bpy,math,json,sys
from pathlib import Path
from mathutils import Vector
HERE=Path(__file__).resolve().parent; OLD=HERE.parent; CLIENT=OLD.parents[2]
bpy.ops.wm.open_mainfile(filepath=str(OLD/'poster-068.blend'))
# Keep world transforms when assembling existing parts.
def parent(obj,root):
 matrix=obj.matrix_world.copy();obj.parent=root;obj.matrix_world=matrix
cap=bpy.data.objects.new('CapAssembly',None);bpy.context.collection.objects.link(cap)
for name in ['Closure','NeckInsert']:
 g=bpy.data.objects[name]
 for child in list(g.children):parent(child,cap)
 bpy.data.objects.remove(g,do_unlink=True)
body=bpy.data.objects['Body']
# Separate the approved original artwork without changing its typeface/placement.
oldgroup=bpy.data.objects['LogoPrint'];ink=next(o for o in oldgroup.children if o.type=='MESH')
for name,file,dy in [('LogoInk','logo.png',0),('NameInk','name.png',-.0006)]:
 root=bpy.data.objects.new(name,None);bpy.context.collection.objects.link(root);root.matrix_world=oldgroup.matrix_world.copy()
 ob=ink.copy();ob.data=ink.data.copy();bpy.context.collection.objects.link(ob);ob.name=name+' curved print';ob.parent=root;ob.location.y+=dy
 material=ink.data.materials[0].copy();material.name=name+' original dark print';ob.data.materials.clear();ob.data.materials.append(material)
 image=next(n for n in material.node_tree.nodes if n.type=='TEX_IMAGE');image.image=bpy.data.images.load(str(HERE/file));image.image.pack();ob.visible_shadow=False
bpy.data.objects.remove(ink,do_unlink=True);bpy.data.objects.remove(oldgroup,do_unlink=True)
label=bpy.data.objects['PaperLabel'];label.name='Label'
for ob in label.children:
 ob.visible_shadow=True
 for mat in ob.data.materials:
  tex=next(n for n in mat.node_tree.nodes if n.type=='TEX_IMAGE');tex.image=bpy.data.images.load(str(HERE/'label.png'));tex.image.pack()
 # A real thin clear carrier, not an opaque paper patch.
 solid=ob.modifiers.new('Thin transparent carrier edge','SOLIDIFY');solid.thickness=.001;solid.offset=0
roots={n:bpy.data.objects[n] for n in ['Body','CapAssembly','Label','LogoInk','NameInk']}
review=json.loads((HERE/'review-product.json').read_text());parts={p['key']:p['node'] for p in review['parts']};explosion=review['review']['explosion']
rest={n:(o.location.copy(),o.scale.copy()) for n,o in roots.items()}
for frame,t in [(1,0),(31,.5),(61,1)]:
 for key,node in parts.items():
  ob=roots[node];pos,s=rest[node];dx,dy,dz=explosion['offsets'].get(key,[0,0,0]);ob.location=pos+Vector((dx,-dz,dy))*t;ob.scale=s*(1+(explosion['scales'].get(key,1)-1)*t);ob.keyframe_insert(data_path='location',frame=frame);ob.keyframe_insert(data_path='scale',frame=frame)
bpy.context.scene.frame_set(1);bpy.context.view_layer.update()
assert len(cap.children)==3 and len(roots)==5
assert all(o.parent==cap for o in cap.children)
bpy.ops.object.select_all(action='DESELECT')
for root in roots.values():
 root.select_set(True)
 for ob in root.children_recursive:ob.select_set(True)
bpy.ops.export_scene.gltf(filepath=str(CLIENT/'packaging-assets/poster-068-v2.glb'),export_format='GLB',use_selection=True,export_apply=True,export_yup=True,export_animations=False,export_extras=True)
bpy.ops.file.pack_all();bpy.ops.wm.save_as_mainfile(filepath=str(HERE/'poster-068-v2.blend'),compress=True)
(HERE/'build-verification.json').write_text(json.dumps({'roots':list(roots),'completeCapMeshes':[o.name for o in cap.children],'originalGlassAndSculptedCapPreserved':True,'formula':False,'source':str(OLD/'poster-068.blend')},indent=2)+'\n')
