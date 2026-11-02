"""Render the carousel cutout from the assembled Body Care Duo Blender file."""
from pathlib import Path
import math

import bpy
from mathutils import Matrix, Vector
from bpy_extras.object_utils import world_to_camera_view

scene = bpy.context.scene
scene.frame_set(1)
folder = Path(bpy.data.filepath).parent
output = folder.parents[2] / "featured-assets" / "poster-079.png"

# Treat the tray plus its contents as one unit. The lid shifts behind it like
# a presentation-box sleeve; neither the bottles nor the box are rescaled.
def arrange(names, center, angle, translation):
    pivot = Vector(center)
    transform = (Matrix.Translation(Vector(translation)) @ Matrix.Translation(pivot)
                 @ Matrix.Rotation(math.radians(angle), 4, 'Z') @ Matrix.Translation(-pivot))
    for name in names:
        part = bpy.data.objects[name]
        part.animation_data_clear()
        part.matrix_world = transform @ part.matrix_world

arrange(["Lid", "LidInk"], (-1.47, 0, 1.45), -9, (1.05, .70, 1.48))
arrange(["Tray", "Cream", "CreamPump", "CreamInk", "Wash", "WashPump", "WashInk"],
        (1.47, 0, 1.45), 7, (-1.05, 0, 0))

def aim(obj, target):
    obj.rotation_euler = (Vector(target) - obj.location).to_track_quat('-Z', 'Y').to_euler()

product_center = (0, .3, 2.2)
bpy.ops.object.camera_add(location=(1.25, -14, 4.0))
camera = bpy.context.object
aim(camera, product_center)
camera.data.type = 'ORTHO'
camera.data.ortho_scale = 4.75
scene.camera = camera
scene.render.resolution_x = 1440
scene.render.resolution_y = 1696
scene.render.resolution_percentage = 100

# Warm key and a slim reflected strip define the satin pumps and the frosted wall.
def softbox(position, energy, size, height, color):
    bpy.ops.object.light_add(type='AREA', location=position)
    obj = bpy.context.object
    obj.data.shape = 'RECTANGLE'
    obj.data.size = size
    obj.data.size_y = height
    obj.data.energy = energy
    obj.data.color = color
    aim(obj, product_center)

softbox((-3.8, -4.0, 6.6), 520, 2.0, 4, (1, .95, .86))
softbox((3.2, -1.4, 4.4), 255, .55, 4.0, (.90, .95, 1))
softbox((.3, 2.4, 5.2), 300, 2.4, 2.4, (1, .98, .92))
scene.world.color = (.36, .36, .36)
scene.view_settings.view_transform = 'AgX'
scene.view_settings.look = 'AgX - Medium High Contrast'
scene.view_settings.exposure = .12
scene.render.engine = 'CYCLES'
scene.cycles.samples = 64
scene.cycles.use_denoising = True
scene.render.film_transparent = True
scene.render.image_settings.color_mode = 'RGBA'
scene.render.filepath = str(output)
bpy.context.view_layer.update()
points = [world_to_camera_view(scene, camera, obj.matrix_world @ vertex.co)
          for obj in scene.objects if obj.type == 'MESH' for vertex in obj.data.vertices]
assert all(.008 < p.x < .992 and .008 < p.y < .992 for p in points), 'Framing cuts the product'
bpy.ops.render.render(write_still=True)
