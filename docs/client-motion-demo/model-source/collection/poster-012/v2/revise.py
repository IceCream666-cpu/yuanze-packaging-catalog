"""Preserve Beach Magic mechanics; split a physical label and original print plates.

Run with the user's local Blender. No render is produced. The packed source keeps
three review poses; the GLB is exported assembled without animation.
"""
import bpy
import bmesh
import json
import math
from pathlib import Path
from mathutils import Vector, Quaternion

HERE = Path(__file__).resolve().parent
CLIENT = HERE.parents[3]
SOURCE = HERE.parents[2] / 'beach-magic/beach-magic.blend'
bpy.ops.wm.open_mainfile(filepath=str(SOURCE))
scene = bpy.context.scene
scene.frame_set(1)
for o in scene.objects:
    o.animation_data_clear()
mechanics = [o for o in scene.objects if o.type == 'MESH' and o.name not in ['Label • reconstructed clean front artwork', 'LogoPrint']]
original = {o.name: {'worldVertices': [o.matrix_world @ v.co * 30 for v in o.data.vertices], 'vertices': len(o.data.vertices), 'polygons': len(o.data.polygons)} for o in mechanics}
# The original is metre-sized; change every local mesh and translation equally,
# preserving geometry and hierarchy while allowing the web model to use scale 1.
seen = set()
for o in scene.objects:
    o.location *= 30
    if o.type == 'MESH' and o.data.as_pointer() not in seen:
        seen.add(o.data.as_pointer())
        for v in o.data.vertices:
            v.co *= 30
        o.data.update()
bpy.context.view_layer.update()
mechanical_errors = {}
for o in mechanics:
    data = original[o.name]
    assert len(o.data.vertices) == data['vertices'] and len(o.data.polygons) == data['polygons']
    error = max((o.matrix_world @ v.co - old).length for v, old in zip(o.data.vertices, data['worldVertices']))
    assert error < 1e-6, (o.name, error)
    mechanical_errors[o.name] = error

old_label = bpy.data.objects['Label • reconstructed clean front artwork']
logo = bpy.data.objects['LogoPrint']
product = old_label.copy()
product.data = old_label.data.copy()
product.name = 'ProductPrint'
product.parent = None
product.location = (0, -.0015, 0)
bpy.context.collection.objects.link(product)
product.data.name = 'Beach Magic unchanged product print cylindrical UV surface'
logo.data.name = 'Beach Magic unchanged logo cylindrical UV surface'

def plate_material(name, filename, alpha=False):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    bs = m.node_tree.nodes.get('Principled BSDF')
    bs.inputs['Roughness'].default_value = .44 if not alpha else .40
    bs.inputs['Specular IOR Level'].default_value = .22
    bs.inputs['Coat Weight'].default_value = .025
    image = bpy.data.images.load(str(HERE / filename), check_existing=False)
    image.pack()
    texture = m.node_tree.nodes.new('ShaderNodeTexImage')
    texture.image = image
    texture.interpolation = 'Linear'
    m.node_tree.links.new(texture.outputs['Color'], bs.inputs['Base Color'])
    if alpha:
        m.surface_render_method = 'BLENDED'
        m.node_tree.links.new(texture.outputs['Alpha'], bs.inputs['Alpha'])
    else:
        bs.inputs['Alpha'].default_value = 1
    return m

logo.data.materials.clear()
logo.data.materials.append(plate_material('Beach Magic original logo ink - shadowless alpha', 'logo.png', True))
product.data.materials.clear()
product.data.materials.append(plate_material('Beach Magic original product ink - shadowless alpha', 'product.png', True))
for o in [logo, product]:
    o.visible_shadow = False
    o['transparent_print_carrier'] = True
    o['castShadow'] = False
    o['original_vector_paths_preserved'] = True

# Reconstruct exactly the original cylindrical UV mapping. Its Y depth measures
# curvature, not physical thickness. The solid paper front stays on that surface.
radius = sum(math.hypot(v.co.x, v.co.y) for v in old_label.data.vertices) / len(old_label.data.vertices)
angle_min = min(math.atan2(v.co.x, -v.co.y) for v in old_label.data.vertices)
angle_max = max(math.atan2(v.co.x, -v.co.y) for v in old_label.data.vertices)
z_min = min(v.co.z for v in old_label.data.vertices)
z_max = max(v.co.z for v in old_label.data.vertices)
thickness = .0012
parent = bpy.data.objects.new('PaperLabel', None)
bpy.context.collection.objects.link(parent)
parent['physical_closed_label'] = True
parent['thickness'] = thickness

# Original SVG rectangle: 1600 x 1000, rx = ry = 130. Build its rounded
# silhouette as real geometry, with front/back and a continuous sealed edge.
outline = []
for cx, cy, start in [(1470, 870, 0), (130, 870, 90), (130, 130, 180), (1470, 130, 270)]:
    for i in range(40):
        a = math.radians(start + i * 90 / 40)
        outline.append(((cx + 130 * math.cos(a)) / 1600, (cy + 130 * math.sin(a)) / 1000))
# A straight UV edge becomes an arc on the cylinder. Subdivide the four long
# edges too; bridging them with a single chord would cut through the paper back.
dense_outline = []
for i, (u, v) in enumerate(outline):
    next_u, next_v = outline[(i + 1) % len(outline)]
    steps = max(1, math.ceil(max(abs(next_u - u), abs(next_v - v)) / .01))
    for j in range(steps):
        t = j / steps
        dense_outline.append((u + (next_u - u) * t, v + (next_v - v) * t))
outline = dense_outline
uv = [(.5, .5)]
rings = 24
for j in range(1, rings + 1):
    t = j / rings
    uv.extend((.5 + (u - .5) * t, .5 + (v - .5) * t) for u, v in outline)
def point(u, v, r):
    a = angle_min + (angle_max - angle_min) * u
    return (r * math.sin(a), -r * math.cos(a), z_min + (z_max - z_min) * v)
vertices = [point(u, v, radius) for u, v in uv] + [point(u, v, radius - thickness) for u, v in uv]
size = len(uv)
n = len(outline)
front = [(0, i + 1, (i + 1) % n + 1) for i in range(n)]
for ring in range(1, rings):
    a = 1 + (ring - 1) * n
    b = a + n
    for i in range(n):
        next_i = (i + 1) % n
        front.append((a + i, b + i, b + next_i, a + next_i))
back = [tuple(k + size for k in reversed(face)) for face in front]
edge = []
base = 1 + (rings - 1) * n
for i in range(n):
    a, b = base + i, base + (i + 1) % n
    edge.append((a, a + size, b + size, b))
mesh = bpy.data.meshes.new('Beach Magic solid rounded paper with original cylindrical UV')
mesh.from_pydata(vertices, [], front + back + edge)
mesh.update()
paper = bpy.data.objects.new('Beach Magic physical rounded paper label', mesh)
bpy.context.collection.objects.link(paper)
paper.parent = parent
paper.data.materials.append(plate_material('Beach Magic ivory paper and gold border - opaque', 'paper.png'))
back_material = bpy.data.materials.new('Beach Magic unprinted ivory paper back and sealed edge')
back_material.use_nodes = True
back_bs = back_material.node_tree.nodes.get('Principled BSDF')
# The original paper #f5eadc, converted from display sRGB to scene-linear RGB.
def srgb_to_linear(v):
    return v / 12.92 if v <= .04045 else ((v + .055) / 1.055) ** 2.4
back_bs.inputs['Base Color'].default_value = (*[srgb_to_linear(v / 255) for v in [245, 234, 220]], 1)
back_bs.inputs['Roughness'].default_value = .52
back_bs.inputs['Specular IOR Level'].default_value = .18
paper.data.materials.append(back_material)
uv_layer = mesh.uv_layers.new(name='Original front artwork UV')
for polygon in mesh.polygons:
    for li in polygon.loop_indices:
        uv_layer.data[li].uv = uv[mesh.loops[li].vertex_index % size]
bm = bmesh.new()
bm.from_mesh(mesh)
bmesh.ops.recalc_face_normals(bm, faces=list(bm.faces))
assert all(e.is_manifold for e in bm.edges)
volume = bm.calc_volume(signed=True)
assert volume > 0
bm.to_mesh(mesh)
bm.free()
mesh.update()
# Analytic cylindrical normals avoid a visible triangle fan in the front paper.
normals = []
for face in mesh.polygons:
    face.use_smooth = True
    front_face = all(i < size for i in face.vertices)
    back_face = all(i >= size for i in face.vertices)
    face.material_index = 0 if front_face else 1
    for li in face.loop_indices:
        co = mesh.vertices[mesh.loops[li].vertex_index].co
        normals.append(tuple(Vector((co.x, co.y, 0)).normalized() * (1 if front_face else -1)) if front_face or back_face else tuple(face.normal))
mesh.normals_split_custom_set(normals)
mesh.calc_loop_triangles()
front_angle_span = max(max(math.atan2(mesh.vertices[i].co.x, -mesh.vertices[i].co.y) for i in t.vertices) - min(math.atan2(mesh.vertices[i].co.x, -mesh.vertices[i].co.y) for i in t.vertices) for t in mesh.loop_triangles if mesh.polygons[t.polygon_index].material_index == 0)
front_chord_sag_bound = radius * (1 - math.cos(front_angle_span / 2))
assert front_chord_sag_bound < thickness / 2, (front_angle_span, front_chord_sag_bound)
paper.visible_shadow = True
paper['castShadow'] = True
paper['receiveShadow'] = True
paper['contains_formula'] = False
bpy.data.objects.remove(old_label, do_unlink=True)

# Neutral clear material; no opaque or tinted fake glass shell is introduced.
glass = bpy.data.materials['ClearPolymer']
glass.name = 'Beach Magic neutral clear empty jar'
bs = glass.node_tree.nodes.get('Principled BSDF')
bs.inputs['Base Color'].default_value = (.995, .998, 1, 1)
bs.inputs['Transmission Weight'].default_value = 1
bs.inputs['IOR'].default_value = 1.47
bs.inputs['Roughness'].default_value = .075
bs.inputs['Coat Weight'].default_value = .05
bs.inputs['Coat Roughness'].default_value = .12

config = json.loads((HERE / 'review-product.json').read_text())
roots = {p['node']: bpy.data.objects[p['node']] for p in config['parts']}
rest = {name: (o.location.copy(), o.rotation_quaternion.copy()) for name, o in roots.items()}
ex = config['review']['explosion']
def quaternion_from_three_xyz(angles):
    a, b, c = [v / 2 for v in angles]
    ca, cb, cc, sa, sb, sc = math.cos(a), math.cos(b), math.cos(c), math.sin(a), math.sin(b), math.sin(c)
    x, y, z = sa * cb * cc + ca * sb * sc, ca * sb * cc - sa * cb * sc, ca * cb * sc + sa * sb * cc
    w = ca * cb * cc - sa * sb * sc
    return Quaternion((w, x, -z, y))
for frame, t in [(1, 0), (31, .5), (61, 1)]:
    for part in config['parts']:
        key, name = part['key'], part['node']
        o = roots[name]
        location, rotation = rest[name]
        x, y, z = ex['offsets'][key]
        o.location = location + Vector((x, -z, y)) * t
        o.rotation_mode = 'QUATERNION'
        o.rotation_quaternion = rotation @ quaternion_from_three_xyz([v * t for v in ex.get('rotations', {}).get(key, [0, 0, 0])])
        o.keyframe_insert(data_path='location', frame=frame)
        o.keyframe_insert(data_path='rotation_quaternion', frame=frame)
scene.frame_start = 1
scene.frame_end = 61
for name, frame in [('Closed', 1), ('Half expanded', 31), ('Fully expanded', 61)]:
    scene.timeline_markers.new(name, frame=frame)
scene.frame_set(1)
bpy.context.view_layer.update()
assert all(abs(v - 1) < 1e-7 for o in scene.objects for v in o.scale)
all_meshes = [o for o in scene.objects if o.type == 'MESH']
points = [o.matrix_world @ v.co for o in all_meshes for v in o.data.vertices]
bounds = {'min': [min(v[a] for v in points) for a in range(3)], 'max': [max(v[a] for v in points) for a in range(3)]}
bounds['size'] = [b - a for a, b in zip(bounds['min'], bounds['max'])]
root_report = {}
for name, o in roots.items():
    members = [m for m in [o] + list(o.children_recursive) if m.type == 'MESH']
    root_report[name] = {'position': list(o.location), 'scale': list(o.scale), 'meshes': [{'name': m.name, 'vertices': len(m.data.vertices), 'polygons': len(m.data.polygons), 'materials': [mat.name for mat in m.data.materials], 'visibleShadow': m.visible_shadow} for m in members]}
bpy.ops.object.select_all(action='DESELECT')
for o in roots.values():
    o.select_set(True)
    for child in o.children_recursive:
        child.select_set(True)
scene['model_id'] = 'poster-012'
scene['model_version'] = 'v2'
scene['normalization'] = 'Original world coordinates x 30; root and object scales remain 1'
scene['contains_formula'] = False
scene['qa_status'] = 'Geometry verified; renders and browser shadow review pending'
output = CLIENT / 'packaging-assets/poster-012-v2.glb'
bpy.ops.export_scene.gltf(filepath=str(output), export_format='GLB', use_selection=True, export_apply=True, export_yup=True, export_animations=False, export_extras=True)
bpy.context.preferences.filepaths.save_version = 0
bpy.ops.file.pack_all()
bpy.ops.wm.save_as_mainfile(filepath=str(HERE / 'poster-012-v2.blend'), compress=True)
report = {
    'source': str(SOURCE), 'coordinateScale': 30, 'sourceUp': '+Z', 'sourceFront': '-Y', 'exportUp': '+Y',
    'originalMechanicalMeshVertexAndPolygonCountsPreserved': True, 'mechanicalWorldCoordinateMaxErrors': mechanical_errors,
    'roots': root_report, 'worldBoundsClosed': bounds, 'paperThickness': thickness, 'paperVolume': volume,
    'paperClosedManifold': True, 'paperFrontRadius': radius, 'paperBackRadius': radius - thickness,
    'paperBoundarySamples': n, 'paperRadialRings': rings, 'paperMaxFrontTriangleAngleSpan': front_angle_span,
    'paperMaxFrontChordSagBound': front_chord_sag_bound, 'paperFrontBackNonintersectionRadialMargin': thickness - front_chord_sag_bound,
    'labelOriginalAngleRange': [angle_min, angle_max], 'labelOriginalZRange': [z_min, z_max],
    'paperBackMinusJarOuterRadius': radius - thickness - .0465 * 30,
    'printCarrierShadowDisabled': True, 'containsFormula': False, 'sourcePoseFrames': [1, 31, 61],
    'glbAssembled': True, 'glbAnimationsRequested': False, 'glbBytes': output.stat().st_size,
    'visualReviewPending': True, 'productionRegistered': False,
}
(HERE / 'build-verification.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
print('POSTER_012_BUILD', json.dumps({'glbBytes': report['glbBytes'], 'roots': list(roots), 'paperClosedManifold': True, 'maxMechanicalWorldError': max(mechanical_errors.values())}))
