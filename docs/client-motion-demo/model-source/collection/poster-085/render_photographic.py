"""Reproducible Cycles studio scene for the approved empty packaging geometry.

Run with the v1 .blend open; pass -- preview for a fast lighting proof.
The photographic scene retains the original six animated component groups.
"""
import json, math, sys
from pathlib import Path
import bpy
from mathutils import Vector
from bpy_extras.object_utils import world_to_camera_view

HERE = Path(__file__).resolve().parent
OUT = HERE / 'photographic-v2'
OUT.mkdir(exist_ok=True)
preview = '--' in sys.argv and 'preview' in sys.argv[sys.argv.index('--') + 1:]
scene = bpy.context.scene
scene.frame_set(1)
bpy.context.preferences.filepaths.save_version = 0
scene.render.engine = 'CYCLES'
scene.cycles.samples = 48 if preview else 512
scene.cycles.use_adaptive_sampling = True
scene.cycles.adaptive_threshold = .035 if preview else .006
scene.cycles.use_denoising = True
scene.cycles.max_bounces = 12
scene.cycles.diffuse_bounces = 4
scene.cycles.glossy_bounces = 6
scene.cycles.transmission_bounces = 10
scene.cycles.transparent_max_bounces = 12
scene.cycles.sample_clamp_indirect = 5
device = 'CPU'
scene.cycles.device = 'CPU'
# Use the installed Mac GPU when available; keep a CPU fallback for other hosts.
prefs = bpy.context.preferences.addons['cycles'].preferences
try:
    prefs.compute_device_type = 'METAL'
    prefs.get_devices()
    if any(d.type == 'METAL' for d in prefs.devices):
        for d in prefs.devices:
            d.use = d.type == 'METAL'
        scene.cycles.device = 'GPU'
        device = 'METAL'
except (TypeError, RuntimeError):
    pass
scene.cycles.preview_samples = 32
scene.render.resolution_x = 900 if preview else 2400
scene.render.resolution_y = 1100 if preview else 3000
scene.render.resolution_percentage = 100
scene.render.image_settings.file_format = 'PNG'
scene.render.image_settings.color_mode = 'RGB'
scene.render.image_settings.color_depth = '16'
scene.render.film_transparent = False
scene.view_settings.view_transform = 'AgX'
scene.view_settings.look = 'AgX - Medium High Contrast'
scene.view_settings.exposure = 0

def linear(v):
    return v / 12.92 if v < .04045 else ((v + .055) / 1.055) ** 2.4

def rgb(code):
    return tuple(linear(int(code[i:i + 2], 16) / 255) for i in (1, 3, 5)) + (1,)

def micro_surface(mat, color, roughness, metallic, grain, strength):
    nodes, links = mat.node_tree.nodes, mat.node_tree.links
    bsdf = nodes.get('Principled BSDF')
    bsdf.inputs['Base Color'].default_value = rgb(color)
    bsdf.inputs['Metallic'].default_value = metallic
    bsdf.inputs['Roughness'].default_value = roughness
    bsdf.inputs['IOR'].default_value = 1.46
    tex = nodes.new('ShaderNodeTexNoise')
    tex.name = 'Microscopic molded surface variation'
    tex.inputs['Scale'].default_value = grain
    tex.inputs['Detail'].default_value = 2
    coord = nodes.new('ShaderNodeTexCoord')
    links.new(coord.outputs['Object'], tex.inputs['Vector'])
    ramp = nodes.new('ShaderNodeMapRange')
    ramp.inputs['From Min'].default_value = 0
    ramp.inputs['From Max'].default_value = 1
    ramp.inputs['To Min'].default_value = roughness - .035
    ramp.inputs['To Max'].default_value = roughness + .035
    links.new(tex.outputs['Fac'], ramp.inputs['Value'])
    links.new(ramp.outputs['Result'], bsdf.inputs['Roughness'])
    bump = nodes.new('ShaderNodeBump')
    bump.inputs['Strength'].default_value = strength
    bump.inputs['Distance'].default_value = .001
    links.new(tex.outputs['Fac'], bump.inputs['Height'])
    links.new(bump.outputs['Normal'], bsdf.inputs['Normal'])
    return bsdf

ivory = micro_surface(bpy.data.materials['Warm ivory satin molded polymer'], '#eee4d3', .30, 0, 330, .13)
ivory.inputs['Subsurface Weight'].default_value = .035
ivory.inputs['Subsurface Radius'].default_value = (.012, .008, .005)
ivory.inputs['Coat Weight'].default_value = .10
ivory.inputs['Coat Roughness'].default_value = .23
bronze = micro_surface(bpy.data.materials['Satin copper bronze decorative finish'], '#a77c5a', .32, .68, 420, .10)
bronze.inputs['Coat Weight'].default_value = .12
bronze.inputs['Coat Roughness'].default_value = .30
rose = micro_surface(bpy.data.materials['Muted rose bronze tube decoration'], '#aa7d6d', .43, .18, 250, .09)
rose.inputs['Coat Weight'].default_value = .08
pipe = bpy.data.materials['Transparent hollow polyethylene suction tube'].node_tree.nodes.get('Principled BSDF')
pipe.inputs['Base Color'].default_value = rgb('#fbfcfa')
pipe.inputs['Alpha'].default_value = 1
pipe.inputs['Transmission Weight'].default_value = .94
pipe.inputs['IOR'].default_value = 1.46
pipe.inputs['Roughness'].default_value = .10

# Smooth the broad actuator's loft without changing its recognizable silhouette.
spout = bpy.data.objects['Pump | wide flattened beak actuator']
mod = spout.modifiers.new('Continuous molded actuator surface', 'SUBSURF')
mod.levels = 1
mod.render_levels = 2
for mat in bpy.data.materials:
    if mat.name.startswith('White '):
        p = mat.node_tree.nodes.get('Principled BSDF')
        if p:
            p.inputs['Roughness'].default_value = .48
            p.inputs['Specular IOR Level'].default_value = .25

product_objects = [o for o in scene.objects if o.type == 'MESH']
world = bpy.data.worlds.new('Low neutral environment for shaped reflections')
world.use_nodes = True
world.node_tree.nodes['Background'].inputs['Color'].default_value = rgb('#d9d5cd')
world.node_tree.nodes['Background'].inputs['Strength'].default_value = .10
scene.world = world

floor_mat = bpy.data.materials.new('Warm limestone seamless studio surface')
floor_mat.use_nodes = True
micro_surface(floor_mat, '#c3b39a', .78, 0, 100, .20)
bpy.ops.mesh.primitive_plane_add(size=200, location=(0, 0, -.002))
floor = bpy.context.object
floor.name = 'Physical shadow receiving ground'
floor.data.materials.append(floor_mat)

# A curved sweep removes the false horizon of an isolated plane.
profile = [(3 + 2 * math.sin(i * math.pi / 64), -.002 + 2 * (1 - math.cos(i * math.pi / 64))) for i in range(33)]
profile.append((5, 14))
vertices = [(x, y, z) for y, z in profile for x in (-20, 20)]
faces = [(2 * i, 2 * i + 1, 2 * i + 3, 2 * i + 2) for i in range(len(profile) - 1)]
mesh = bpy.data.meshes.new('Seamless curved backdrop mesh')
mesh.from_pydata(vertices, [], faces)
backdrop = bpy.data.objects.new('Seamless curved studio backdrop', mesh)
scene.collection.objects.link(backdrop)
backdrop.data.materials.append(floor_mat)
for face in mesh.polygons:
    face.use_smooth = True

def area(name, pos, size, power, color, target, height=None):
    bpy.ops.object.light_add(type='AREA', location=pos)
    o = bpy.context.object
    o.name = name
    o.data.shape = 'RECTANGLE'
    o.data.size = size
    o.data.size_y = height or size
    o.data.energy = power
    o.data.color = color
    o.rotation_euler = (Vector(target) - o.location).to_track_quat('-Z', 'Y').to_euler()

area('Large left window key', (-3.7, -4.0, 6.2), 1.8, 950, (1, .94, .85), (0, 0, 1.5), 4)
area('Tall narrow right reflection', (3, -1.2, 4.2), .65, 90, (1, .98, .94), (.5, 0, 1.7), 4)
area('Soft front label fill', (-.5, -5, 3), 4, 35, (1, 1, 1), (0, 0, 1.5), 3)
area('Upper rear rim light', (1, 2.8, 5.4), 2.2, 200, (1, .91, .80), (0, 0, 1.5), 3)

bpy.ops.object.camera_add()
camera = bpy.context.object
camera.name = 'Product photography camera 85mm'
camera.data.type = 'PERSP'
camera.data.lens = 85
camera.data.clip_start = .01
camera.data.clip_end = 300
scene.camera = camera

def frame_product(frame, direction, margin=.10):
    scene.frame_set(frame)
    bpy.context.view_layer.update()
    points = [o.matrix_world @ Vector(v) for o in product_objects for v in o.bound_box]
    lo = Vector([min(p[i] for p in points) for i in range(3)])
    hi = Vector([max(p[i] for p in points) for i in range(3)])
    target = (lo + hi) / 2
    direction = Vector(direction).normalized()
    distance = 12.0
    for _ in range(8):
        camera.location = target + direction * distance
        camera.rotation_euler = (target - camera.location).to_track_quat('-Z', 'Y').to_euler()
        bpy.context.view_layer.update()
        projected = [world_to_camera_view(scene, camera, p) for p in points]
        extent = max(max(abs(p.x - .5), abs(p.y - .5)) for p in projected)
        distance *= extent / (.5 - margin)
    camera.location = target + direction * distance
    bpy.context.view_layer.update()
    camera.data.dof.use_dof = True
    camera.data.dof.focus_distance = distance
    camera.data.dof.aperture_fstop = 11
    projected = [world_to_camera_view(scene, camera, p) for p in points]
    assert all(.025 < p.x < .975 and .025 < p.y < .975 for p in projected), 'Product clipped'
    return {'frame': frame, 'camera': list(camera.location), 'focusDistance': distance}

pose = frame_product(1, (.12, -1, .18), .11)
assert floor.location.z < 0
assert len([o for o in scene.objects if o.type == 'LIGHT']) == 4
assert all(bpy.data.objects.get(n) for n in ['Body', 'Pump', 'TubeCap', 'Label', 'LogoInk', 'NameInk'])
scene.render.filepath = str(OUT / ('lighting-proof.png' if preview else 'Daily-Hair-Ritual-Cycles-2400x3000.png'))
if not preview:
    # Keep the source usable when scrubbing the complete assembled/exploded range.
    for frame, direction, margin in [(1, (.12, -1, .18), .11), (31, (.14, -1, .15), .12), (61, (.16, -1, .13), .12)]:
        frame_product(frame, direction, margin)
        camera.keyframe_insert(data_path='location', frame=frame)
        camera.keyframe_insert(data_path='rotation_euler', frame=frame)
        camera.data.dof.keyframe_insert(data_path='focus_distance', frame=frame)
        floor.location.z = -.002 - .503 * (frame - 1) / 60
        floor.keyframe_insert(data_path='location', frame=frame)
        backdrop.location.z = floor.location.z + .002
        backdrop.keyframe_insert(data_path='location', frame=frame)
    for name, frame in [('Assembled', 1), ('Half expanded', 31), ('Fully expanded', 61)]:
        scene.timeline_markers.new(name, frame=frame)
    scene.frame_set(1)
    for screen in bpy.data.screens:
        for a in screen.areas:
            if a.type == 'VIEW_3D':
                a.spaces.active.region_3d.view_perspective = 'CAMERA'
                a.spaces.active.overlay.show_overlays = False
                a.spaces.active.shading.type = 'RENDERED'
    bpy.ops.file.pack_all()
    bpy.ops.wm.save_as_mainfile(filepath=str(OUT / 'poster-085-photographic-v2.blend'), compress=True)
    if '--scene-only' in sys.argv:
        print('PHOTOGRAPHIC_SCENE_SAVED', flush=True)
if '--scene-only' not in sys.argv:
    bpy.ops.render.render(write_still=True)
    if not preview:
        closed_pose = pose
        scene.render.resolution_x = 2400
        scene.render.resolution_y = 3000
        pose = frame_product(61, (.16, -1, .13), .12)
        # Floating components keep cast shadows; only the decorative film and ink do not.
        floor.location.z = -.505
        backdrop.location.z = -.503
        scene.render.filepath = str(OUT / 'Daily-Hair-Ritual-Cycles-expanded-2400x3000.png')
        bpy.ops.render.render(write_still=True)
        (OUT / 'render-info.json').write_text(json.dumps({'engine': scene.render.engine, 'device': device,
            'blender': bpy.app.version_string, 'samples': scene.cycles.samples, 'adaptiveThreshold': scene.cycles.adaptive_threshold,
            'resolution': [2400, 3000], 'bitDepth': 16, 'groundReceivesShadows': True, 'lights': 4,
            'colorManagement': 'AgX Medium High Contrast', 'closed': closed_pose, 'expanded': pose,
            'source': 'poster-085-photographic-v2.blend', 'note': 'Cycles offline rendering; browser real-time quality is separate'}, indent=2) + '\n')
    print('PHOTOGRAPHIC_RENDER_COMPLETE', device, 'preview' if preview else 'final')
