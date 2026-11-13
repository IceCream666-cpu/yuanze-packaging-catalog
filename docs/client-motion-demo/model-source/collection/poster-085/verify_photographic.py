"""Run inside the saved photographic .blend to check the deliverable scene."""
import hashlib, json
from pathlib import Path
import bpy
from mathutils import Vector
from bpy_extras.object_utils import world_to_camera_view

out = Path(bpy.data.filepath).parent
scene = bpy.context.scene
assert scene.render.engine == 'CYCLES'
assert scene.cycles.samples >= 512
assert scene.cycles.use_denoising and scene.cycles.adaptive_threshold <= .006001
assert [scene.render.resolution_x, scene.render.resolution_y] == [2400, 3000]
assert scene.render.image_settings.color_depth == '16'
assert scene.camera.data.type == 'PERSP' and scene.camera.data.lens == 85
assert scene.camera.data.dof.use_dof
assert len([o for o in scene.objects if o.type == 'LIGHT' and o.data.type == 'AREA']) == 4
floor = bpy.data.objects['Physical shadow receiving ground']
assert floor.visible_shadow and not floor.hide_render and abs(floor.location.z + .002) < 1e-6
groups = ['Body', 'Pump', 'TubeCap', 'Label', 'LogoInk', 'NameInk']
assert all(bpy.data.objects.get(name) for name in groups)
scene.frame_set(1)
bpy.context.view_layer.update()
rest = {name: bpy.data.objects[name].location.copy() for name in groups}
body = bpy.data.objects['Body']
bottom = min((o.matrix_world @ Vector(v)).z for o in body.children if o.type == 'MESH' for v in o.bound_box)
assert 0 <= bottom - floor.location.z < .004, 'Container must sit on the floor'
scene.frame_set(61)
bpy.context.view_layer.update()
pump_travel = bpy.data.objects['Pump'].location - rest['Pump']
assert abs(pump_travel.z - 2.95) < 1e-5
assert abs(bpy.data.objects['TubeCap'].location.z - rest['TubeCap'].z + .5) < 1e-5
assert abs(floor.location.z + .505) < 1e-6
assert abs(bpy.data.objects['Seamless curved studio backdrop'].location.z + .503) < 1e-6
product_objects = [o for name in groups for o in bpy.data.objects[name].children if o.type == 'MESH']
for frame in (1, 31, 61):
    scene.frame_set(frame)
    bpy.context.view_layer.update()
    projected = [world_to_camera_view(scene, scene.camera, o.matrix_world @ Vector(v)) for o in product_objects for v in o.bound_box]
    assert all(.025 < p.x < .975 and .025 < p.y < .975 for p in projected), ('Camera clipping', frame)
scene.frame_set(1)
for name in groups:
    assert (bpy.data.objects[name].location - rest[name]).length < 1e-6
for image in bpy.data.images:
    if image.source == 'FILE':
        assert image.packed_file or image.packed_files, image.name
for name in ['Satin copper bronze decorative finish', 'Muted rose bronze tube decoration', 'Warm ivory satin molded polymer']:
    mat = bpy.data.materials[name]
    assert any(n.type == 'BUMP' for n in mat.node_tree.nodes), name
assert all('liquid' not in o.name.lower() for o in scene.objects)
render_paths = [out / n for n in ['Daily-Hair-Ritual-Cycles-2400x3000.png', 'Daily-Hair-Ritual-Cycles-expanded-2400x3000.png']]
for p in render_paths:
    assert p.is_file() and p.stat().st_size > 100000
    with p.open('rb') as f:
        header = f.read(25)
    assert header[:8] == b'\x89PNG\r\n\x1a\n' and header[24] == 16, 'Expected a 16-bit PNG'
    image = bpy.data.images.load(str(p), check_existing=False)
    assert list(image.size) == [2400, 3000]
    bpy.data.images.remove(image)
report = {'savedSourceReopened': True, 'shadowReceivingGround': True, 'floorGap': bottom - floor.location.z,
          'completePumpTravelZ': pump_travel.z, 'componentGroups': groups, 'embeddedTextures': True,
          'sourceSha256': hashlib.sha256(Path(bpy.data.filepath).read_bytes()).hexdigest(),
          'renders': [{'file': p.name, 'bytes': p.stat().st_size, 'sha256': hashlib.sha256(p.read_bytes()).hexdigest()} for p in render_paths],
          'scope': 'Scene and output integrity; visual acceptance recorded separately'}
(out / 'verification.json').write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps(report, indent=2))
