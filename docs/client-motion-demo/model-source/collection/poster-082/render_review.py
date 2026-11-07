"""Render actual saved Blender geometry in closed, side and fully separated poses."""
import sys
from pathlib import Path
import bpy
from mathutils import Vector
from bpy_extras.object_utils import world_to_camera_view
out=Path(sys.argv[sys.argv.index('--')+1]);out.mkdir(exist_ok=True,parents=True)
scene=bpy.context.scene
scene.render.engine='CYCLES';scene.cycles.samples=48;scene.cycles.use_denoising=True
scene.cycles.max_bounces=10;scene.cycles.transmission_bounces=8
scene.render.resolution_percentage=100;scene.render.image_settings.file_format='PNG'
scene.render.image_settings.color_mode='RGBA';scene.view_settings.view_transform='AgX'
scene.view_settings.look='AgX - Medium High Contrast'
world=bpy.data.worlds.new('Neutral blue ivory studio');world.use_nodes=True
world.node_tree.nodes['Background'].inputs['Color'].default_value=(.77,.80,.78,1)
world.node_tree.nodes['Background'].inputs['Strength'].default_value=.55;scene.world=world
def light(name,pos,w,h,power,color):
 bpy.ops.object.light_add(type='AREA',location=pos);o=bpy.context.object;o.name=name
 o.data.shape='RECTANGLE';o.data.size=w;o.data.size_y=h;o.data.energy=power;o.data.color=color
 o.rotation_euler=(Vector((0,0,1.7))-o.location).to_track_quat('-Z','Y').to_euler()
light('Broad left key',(-4,-4,5),3,5,450,(1,.97,.90))
light('Cool right fill',(4,-3,3.5),2,4,220,(.91,.97,1))
light('Upper edge',(1,3,6),3,2.5,350,(1,1,1))
light('Front soft fill',(0,-7,2),4,4,100,(1,1,1))
bpy.ops.object.camera_add();camera=bpy.context.object;camera.name='Review camera';camera.data.type='ORTHO';scene.camera=camera
for title,frame,direction,res in [('front',1,(0,-10,1.0),(1600,1800)),('side',1,(8,-10,2),(1800,1800)),('expanded',61,(1.5,-10,1.3),(2200,2000))]:
 scene.frame_set(frame);bpy.context.view_layer.update()
 points=[o.matrix_world@v.co for o in scene.objects if o.type=='MESH' for v in o.data.vertices]
 lo=Vector([min(p[i] for p in points) for i in range(3)]);hi=Vector([max(p[i] for p in points) for i in range(3)])
 target=(lo+hi)/2;camera.location=target+Vector(direction)
 camera.rotation_euler=(target-camera.location).to_track_quat('-Z','Y').to_euler()
 bpy.context.view_layer.update();basis=camera.matrix_world.inverted()
 local=[basis@p for p in points];dx=max(p.x for p in local)-min(p.x for p in local);dy=max(p.y for p in local)-min(p.y for p in local)
 center=Vector(((max(p.x for p in local)+min(p.x for p in local))/2,(max(p.y for p in local)+min(p.y for p in local))/2,0))
 camera.location+=camera.rotation_euler.to_matrix()@center
 scene.render.resolution_x,scene.render.resolution_y=res
 camera.data.ortho_scale=max(dy,dx*res[1]/res[0])*1.15
 scene.render.filepath=str(out/f'Soap-Clean-Duo-Blender-{title}.png')
 bpy.context.view_layer.update()
 clip=[world_to_camera_view(scene,camera,p) for p in points]
 assert all(.02<p.x<.98 and .02<p.y<.98 for p in clip),(title,'clipped')
 bpy.ops.render.render(write_still=True)
