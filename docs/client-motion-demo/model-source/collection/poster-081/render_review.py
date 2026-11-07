"""Render the saved Blender model for visual review; source geometry remains unchanged."""
import sys
from pathlib import Path
import bpy
from mathutils import Vector
from bpy_extras.object_utils import world_to_camera_view
out=Path(sys.argv[sys.argv.index('--')+1]);out.mkdir(exist_ok=True,parents=True)
scene=bpy.context.scene
scene.render.engine='CYCLES';scene.cycles.samples=64;scene.cycles.use_denoising=True
scene.cycles.transmission_bounces=12;scene.cycles.max_bounces=16
scene.render.resolution_percentage=100;scene.render.image_settings.file_format='PNG';scene.render.image_settings.color_mode='RGBA'
scene.view_settings.view_transform='AgX';scene.view_settings.look='AgX - Medium High Contrast'
world=bpy.data.worlds.new('Soft warm studio');world.use_nodes=True;world.node_tree.nodes['Background'].inputs['Color'].default_value=(.73,.75,.69,1);world.node_tree.nodes['Background'].inputs['Strength'].default_value=.45;scene.world=world
bpy.ops.object.camera_add();camera=bpy.context.object;camera.name='Review camera';camera.data.type='ORTHO';scene.camera=camera

def light(name,pos,w,h,power,color):
 bpy.ops.object.light_add(type='AREA',location=pos);ob=bpy.context.object;ob.name=name;ob.data.shape='RECTANGLE';ob.data.size=w;ob.data.size_y=h;ob.data.energy=power;ob.data.color=color;ob.rotation_euler=(Vector((-.2,0,1.6))-ob.location).to_track_quat('-Z','Y').to_euler()
light('Tall left softbox',(-3.8,-3.2,3.8),1.4,4.8,350,(1,.97,.91))
light('Front soft fill',(1.7,-4.9,2.5),3,3.5,180,(.91,.95,1))
light('Glass right strip',(2.5,1.6,3.3),.55,4.3,260,(1,1,1))
light('Top edge',(-.5,1,6),3,2.2,280,(1,.98,.92))
for title,frame,transparent in [('合拢',1,False),('透明主图',1,True),('完全展开',61,False)]:
 scene.frame_set(frame);target=Vector((0,0,1.45)) if frame==1 else Vector((-.95,-.45,2.45))
 camera.location=target+Vector((.8,-11,2.2));camera.rotation_euler=(target-camera.location).to_track_quat('-Z','Y').to_euler();camera.data.ortho_scale=3.45 if frame==1 else 6.15
 scene.render.resolution_x=1400 if frame==1 else 1920;scene.render.resolution_y=1800;scene.render.film_transparent=transparent
 scene.render.filepath=str(out/f'Hand-Gel-Blender-{title}.png')
 bpy.context.view_layer.update()
 points=[world_to_camera_view(scene,camera,o.matrix_world@v.co) for o in scene.objects if o.type=='MESH' for v in o.data.vertices]
 assert all(0<p.x<1 and 0<p.y<1 for p in points),f'{title} clipped'
 bpy.ops.render.render(write_still=True)
