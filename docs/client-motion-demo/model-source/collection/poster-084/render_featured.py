"""Render the approved assembled duo for the homepage; keep the model unchanged."""
from pathlib import Path

import bpy
from mathutils import Vector
from bpy_extras.object_utils import world_to_camera_view

scene = bpy.context.scene
scene.frame_set(1)
folder = Path(bpy.data.filepath).parent
output = folder.parents[2] / 'featured-assets' / 'poster-084.png'
assert {obj.name for obj in scene.objects if obj.type == 'EMPTY'} == {
    'Body', 'Pump', 'Label', 'LogoInk', 'NameInk'
}

target = Vector((0, 0, 1.47))

def aim(obj):
    obj.rotation_euler = (target - obj.location).to_track_quat('-Z', 'Y').to_euler()

bpy.ops.object.camera_add(location=(.2, -12, 2.10))
camera = bpy.context.object
camera.data.type = 'ORTHO'
camera.data.ortho_scale = 3.6
aim(camera)
scene.camera = camera

def softbox(position, width, height, power, color):
    bpy.ops.object.light_add(type='AREA', location=position)
    lamp = bpy.context.object
    lamp.data.shape = 'RECTANGLE'
    lamp.data.size = width
    lamp.data.size_y = height
    lamp.data.energy = power
    lamp.data.color = color
    aim(lamp)

softbox((-3.6, -4.0, 5.0), 2.1, 4.8, 440, (1, .97, .92))
softbox((3.0, -3.0, 3.4), 1.5, 4.0, 210, (.92, .97, 1))
softbox((.5, 2.0, 5.0), 2.7, 2.0, 260, (1, 1, 1))
softbox((0, -6, 2), 4, 4, 80, (1, 1, 1))
world = bpy.data.worlds.new('Soft duo clear glass studio')
world.use_nodes = True
world.node_tree.nodes['Background'].inputs['Color'].default_value = (.77, .80, .78, 1)
world.node_tree.nodes['Background'].inputs['Strength'].default_value = .5
scene.world = world

# Surface ink and the transparent print carrier must not cast detached shadows.
for name in ('Label', 'LogoInk', 'NameInk'):
    for ink in scene.objects[name].children:
        ink.visible_shadow = False
scene.view_settings.view_transform = 'AgX'
scene.view_settings.look = 'AgX - Medium High Contrast'
scene.render.engine = 'CYCLES'
scene.cycles.samples = 64
scene.cycles.use_denoising = True
scene.cycles.max_bounces = 10
scene.render.resolution_x = 1600
scene.render.resolution_y = 1800
scene.render.resolution_percentage = 100
scene.render.film_transparent = True
scene.render.image_settings.file_format = 'PNG'
scene.render.image_settings.color_mode = 'RGBA'
scene.render.filepath = str(output)
bpy.context.view_layer.update()
points = [world_to_camera_view(scene, camera, obj.matrix_world @ vertex.co)
          for obj in scene.objects if obj.type == 'MESH' for vertex in obj.data.vertices]
assert all(.015 < p.x < .985 and .015 < p.y < .985 for p in points), 'Homepage image clips product'
bpy.ops.render.render(write_still=True)
