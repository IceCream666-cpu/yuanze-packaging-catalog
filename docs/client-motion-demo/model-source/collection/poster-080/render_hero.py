"""Blender background render of the assembled After Bath finish. Optional -- /path/to/hero.png."""
import sys
from pathlib import Path

import bpy
from bpy_extras.object_utils import world_to_camera_view
from mathutils import Vector

scene = bpy.data.scenes['after']
bpy.context.window.scene = scene
scene.frame_set(1)
assert {obj.name for obj in scene.objects if obj.type == 'EMPTY'} == {
    f'{part}_After' for part in ('Body', 'Pump', 'Label', 'LogoInk', 'NameInk')
}
target = Vector((0, 0, 1.46))

def aim(obj):
    obj.rotation_euler = (target - obj.location).to_track_quat('-Z', 'Y').to_euler()

bpy.ops.object.camera_add(location=(1.6, -10, 3.45))
camera = bpy.context.object
camera.data.type = 'ORTHO'
camera.data.ortho_scale = 3.24
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

softbox((-2.3, -3.5, 3.6), 1.55, 4.4, 245, (1, .97, .94))
softbox((1, -4.8, 1.7), 3.4, 4, 135, (.94, .96, 1))
softbox((2.4, -.8, 3.3), .42, 3.4, 80, (.9, .95, 1))
softbox((-.1, 1.9, 4.7), 2.1, 1.6, 160, (1, .98, .95))
scene.world.color = (.24, .24, .24)
# Surface ink has negligible thickness and cannot cast a detached drop shadow.
for group in ('LogoInk_After', 'NameInk_After'):
    for ink in scene.objects[group].children:
        ink.visible_shadow = False
scene.view_settings.view_transform = 'AgX'
scene.view_settings.look = 'AgX - Medium High Contrast'

scene.render.resolution_x = 1280
scene.render.resolution_y = 1792
scene.render.resolution_percentage = 100
scene.render.engine = 'CYCLES'
scene.cycles.samples = 48
scene.cycles.use_denoising = True
scene.render.film_transparent = True
scene.render.image_settings.file_format = 'PNG'
scene.render.image_settings.color_mode = 'RGBA'
folder = Path(bpy.data.filepath).parent
output = Path(sys.argv[sys.argv.index('--') + 1]) if '--' in sys.argv else folder / 'review-hero.png'
scene.render.filepath = str(output)

bpy.context.view_layer.update()
projected = [world_to_camera_view(scene, camera, obj.matrix_world @ vert.co)
             for obj in scene.objects if obj.type == 'MESH' for vert in obj.data.vertices]
assert all(.015 < p.x < .985 and .015 < p.y < .985 for p in projected), 'Hero camera clips product'
bpy.ops.render.render(write_still=True)
