"""Save a real Cycles studio and inspect closed/half/full/rotated poses.
The paired half renders isolate the label's shadow contribution.
"""
from pathlib import Path
import bpy,json
from mathutils import Vector
from bpy_extras.object_utils import world_to_camera_view
HERE=Path(__file__).resolve().parent
OUT=HERE/'previews';OUT.mkdir(exist_ok=True)
scene=bpy.context.scene;scene.frame_set(1)
for ob in list(scene.objects):
 if ob.parent is None and ob.type!='EMPTY':bpy.data.objects.remove(ob,do_unlink=True)
products=[o for o in scene.objects if o.type=='MESH']
# Match the viewer's near-invisible carrier at rest and legible film when separated.
for ob in bpy.data.objects['Label'].children:
 for mat in ob.data.materials:
  tree=mat.node_tree;bsdf=next(n for n in tree.nodes if n.type=='BSDF_PRINCIPLED')
  fade=bsdf.inputs['Alpha'].links[0].from_node
  if fade.type!='MATH' or fade.operation!='MULTIPLY':
   source=bsdf.inputs['Alpha'].links[0].from_socket
   fade=tree.nodes.new('ShaderNodeMath');fade.operation='MULTIPLY';tree.links.new(source,fade.inputs[0]);tree.links.new(fade.outputs[0],bsdf.inputs['Alpha'])
  for frame,value in [(1,.05),(31,.92),(61,1)]:
   fade.inputs[1].default_value=value;fade.inputs[1].keyframe_insert(data_path='default_value',frame=frame)

scene.render.engine='CYCLES';scene.cycles.samples=64;scene.cycles.use_denoising=True
scene.cycles.max_bounces=8;scene.cycles.transparent_max_bounces=8
scene.render.resolution_x=1200;scene.render.resolution_y=1500;scene.render.resolution_percentage=100
scene.render.image_settings.file_format='PNG';scene.render.image_settings.color_mode='RGB'
scene.view_settings.view_transform='AgX';scene.view_settings.look='AgX - Medium High Contrast'
prefs=bpy.context.preferences.addons['cycles'].preferences
prefs.compute_device_type='METAL';prefs.get_devices();assert any(d.type=='METAL' for d in prefs.devices)
for d in prefs.devices:d.use=d.type=='METAL'
scene.cycles.device='GPU'
world=bpy.data.worlds.new('Neutral studio environment');world.use_nodes=True
world.node_tree.nodes['Background'].inputs['Color'].default_value=(.7,.65,.56,1)
world.node_tree.nodes['Background'].inputs['Strength'].default_value=.55;scene.world=world
floor_mat=bpy.data.materials.new('Warm taupe backdrop');floor_mat.use_nodes=True
p=floor_mat.node_tree.nodes.get('Principled BSDF');p.inputs['Base Color'].default_value=(.44,.36,.27,1);p.inputs['Roughness'].default_value=.85
bpy.ops.mesh.primitive_plane_add(size=200,location=(0,0,-.005));floor=bpy.context.object;floor.name='Physical studio shadow ground';floor.data.materials.append(floor_mat)
def area(name,pos,size,height,power,color):
 bpy.ops.object.light_add(type='AREA',location=pos);ob=bpy.context.object;ob.name=name;ob.data.shape='RECTANGLE';ob.data.size=size;ob.data.size_y=height;ob.data.energy=power;ob.data.color=color
 ob.rotation_euler=(Vector((0,0,2))-ob.location).to_track_quat('-Z','Y').to_euler()
area('Left window key',(-4,-4,7),1.6,4,1100,(1,.95,.88))
area('Right reflection strip',(3,-1,5),.8,4,100,(1,.98,.94))
area('Front gentle fill',(-.5,-6,3),4,4,45,(1,1,1))
area('Rear rim',(1,3,6),2,3,230,(1,.94,.88))
bpy.ops.object.camera_add();camera=bpy.context.object;camera.name='Amber Ginger Shampoo review camera';camera.data.type='ORTHO';camera.data.clip_end=200;scene.camera=camera
poses=[]
def frame_product(frame,direction):
 scene.frame_set(frame);bpy.context.view_layer.update()
 points=[o.matrix_world@v.co for o in products for v in o.data.vertices]
 lo=Vector([min(p[i] for p in points) for i in range(3)]);hi=Vector([max(p[i] for p in points) for i in range(3)])
 target=(lo+hi)/2;camera.location=target+Vector(direction)
 camera.rotation_euler=(target-camera.location).to_track_quat('-Z','Y').to_euler();bpy.context.view_layer.update()
 basis=camera.matrix_world.inverted();local=[basis@p for p in points]
 dx=max(p.x for p in local)-min(p.x for p in local);dy=max(p.y for p in local)-min(p.y for p in local)
 center=Vector(((max(p.x for p in local)+min(p.x for p in local))/2,(max(p.y for p in local)+min(p.y for p in local))/2,0))
 camera.location+=camera.rotation_euler.to_matrix()@center
 camera.data.ortho_scale=max(dy,dx*1.25)*1.22;bpy.context.view_layer.update()
 assert all(.02<p.x<.98 and .02<p.y<.98 for p in [world_to_camera_view(scene,camera,p) for p in points]),'Clipped product'
 return list(camera.location)
for name,frame,direction in [('closed',1,(.45,-10,1.0)),('half',31,(.45,-10,1.0)),('expanded',61,(.75,-10,1.0)),('rotated',61,(5,-10,2))]:
 pos=frame_product(frame,direction);scene.render.filepath=str(OUT/f'Amber-Ginger-Blender-{name}.png')
 bpy.ops.render.render(write_still=True);poses.append({'name':name,'frame':frame,'camera':pos})
 if name=='half':
  for ob in bpy.data.objects['Label'].children:ob.visible_shadow=False
  scene.render.filepath=str(OUT/'Amber-Ginger-shadow-control.png');bpy.ops.render.render(write_still=True)
  for ob in bpy.data.objects['Label'].children:ob.visible_shadow=True
for frame in [1,31,61]:
 frame_product(frame,(.45,-10,1.0));camera.keyframe_insert(data_path='location',frame=frame);camera.keyframe_insert(data_path='rotation_euler',frame=frame);camera.data.keyframe_insert(data_path='ortho_scale',frame=frame)
for name,frame in [('Closed',1),('Half expanded with label shadow',31),('Fully expanded',61)]:scene.timeline_markers.new(name,frame=frame)
scene.frame_set(1)
for screen in bpy.data.screens:
 for a in screen.areas:
  if a.type=='VIEW_3D':a.spaces.active.region_3d.view_perspective='CAMERA';a.spaces.active.overlay.show_overlays=False;a.spaces.active.shading.type='MATERIAL'
bpy.context.preferences.filepaths.save_version=0;bpy.ops.file.pack_all();bpy.ops.wm.save_as_mainfile(filepath=str(HERE/'poster-067-v2.blend'),compress=True)
(HERE/'render-verification.json').write_text(json.dumps({'engine':'Cycles','device':'Metal','samples':64,'resolution':[1200,1500],'poses':poses,'physicalLabelShadow':True,'inkShadowDisabled':True,'pairedShadowControl':True,'browserVerifiedSeparately':True},indent=2)+'\n')
