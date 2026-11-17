"""Reopen the packed deliverable and verify geometry, UV layers, poses and export."""
import bpy
import bmesh
import json
import math
import struct
from pathlib import Path
from mathutils import Vector

HERE = Path(__file__).resolve().parent
CLIENT = HERE.parents[3]
bpy.ops.wm.open_mainfile(filepath=str(HERE / 'poster-012-v2.blend'))
scene = bpy.context.scene
scene.frame_set(1)
bpy.context.view_layer.update()
config = json.loads((HERE / 'review-product.json').read_text())
names = [part['node'] for part in config['parts']]
assert all(bpy.data.objects[name].parent is None for name in names)
# The review render may later add camera, lights and a studio floor to the
# packed source. Validate the product hierarchy independently of that studio.
model_objects = [o for name in names for o in [bpy.data.objects[name]] + list(bpy.data.objects[name].children_recursive)]
assert all(all(abs(v - 1) < 1e-7 for v in o.scale) for o in model_objects)
assert bpy.data.objects['LogoPrint'].type == 'MESH'
assert bpy.data.objects['ProductPrint'].type == 'MESH'
assert all(not bpy.data.objects[name].hide_render for name in names)
paper = bpy.data.objects['PaperLabel'].children[0]
bm = bmesh.new()
bm.from_mesh(paper.data)
assert all(e.is_manifold for e in bm.edges)
assert bm.calc_volume(signed=True) > 0
volume = bm.calc_volume(signed=True)
bm.free()
front_radius = max(math.hypot(v.co.x, v.co.y) for v in paper.data.vertices)
back_radius = min(math.hypot(v.co.x, v.co.y) for v in paper.data.vertices)
min_z = min(v.co.z for v in paper.data.vertices)
max_z = max(v.co.z for v in paper.data.vertices)
jar = bpy.data.objects['Jar']
jar_points = [o.matrix_world @ v.co for o in jar.children_recursive if o.type == 'MESH' for v in o.data.vertices]
# Original long cylinder quads span this Z interval without intermediate rings;
# the whole-jar radial maximum conservatively covers all interpolated faces.
jar_radius_at_label = max(math.hypot(v.x, v.y) for v in jar_points)
clearance = back_radius - jar_radius_at_label
assert clearance > .0029, clearance
assert 0.00119 < front_radius - back_radius < .00121
back_material = paper.data.materials[1]
assert not any(n.type == 'TEX_IMAGE' for n in back_material.node_tree.nodes)
front_count = sum(f.material_index == 0 for f in paper.data.polygons)
back_count = sum(f.material_index == 1 for f in paper.data.polygons)
assert front_count > 0 and back_count > front_count
assert paper.visible_shadow
paper.data.calc_loop_triangles()
front_angle_span = max(max(math.atan2(paper.data.vertices[i].co.x, -paper.data.vertices[i].co.y) for i in t.vertices) - min(math.atan2(paper.data.vertices[i].co.x, -paper.data.vertices[i].co.y) for i in t.vertices) for t in paper.data.loop_triangles if paper.data.polygons[t.polygon_index].material_index == 0)
front_chord_sag_bound = front_radius * (1 - math.cos(front_angle_span / 2))
front_back_margin = front_radius - front_chord_sag_bound - back_radius
assert front_back_margin > .0006, (front_angle_span, front_back_margin)
ink_clearance = {}
for name in ['LogoPrint', 'ProductPrint']:
    o = bpy.data.objects[name]
    assert not o.visible_shadow
    assert len(o.data.vertices) == 4257 and len(o.data.polygons) == 8192
    assert o.data.uv_layers.active
    image_nodes = [n for n in o.data.materials[0].node_tree.nodes if n.type == 'TEX_IMAGE']
    assert len(image_nodes) == 1 and image_nodes[0].image.packed_file
    assert tuple(image_nodes[0].image.size) == (2048, 1280)
    ink_clearance[name] = min(math.hypot(*(o.matrix_world @ v.co)[:2]) for v in o.data.vertices) - front_radius
    assert ink_clearance[name] > .00049, (name, ink_clearance[name])
rest = {name: bpy.data.objects[name].location.copy() for name in names}
poses = []
for frame, progress in [(1, 0), (31, .5), (61, 1)]:
    scene.frame_set(frame)
    bpy.context.view_layer.update()
    for part in config['parts']:
        x, y, z = config['review']['explosion']['offsets'][part['key']]
        expected = rest[part['node']] + Vector((x, -z, y)) * progress
        assert (bpy.data.objects[part['node']].location - expected).length < 1e-6
    poses.append({'frame': frame, 'progress': progress, 'rootLocations': {name: list(bpy.data.objects[name].location) for name in names}})
scene.frame_set(1)

glb_path = CLIENT / 'packaging-assets/poster-012-v2.glb'
content = glb_path.read_bytes()
assert content[:4] == b'glTF'
length, chunk_type = struct.unpack_from('<II', content, 12)
assert chunk_type == 0x4E4F534A
gltf = json.loads(content[20:20 + length])
assert not gltf.get('animations')
assert sorted(gltf['nodes'][i]['name'] for i in gltf['scenes'][0]['nodes']) == sorted(names)
assert all('scale' not in node or all(abs(v-1) < 1e-6 for v in node['scale']) for node in gltf['nodes'])
materials = gltf['materials']
opaque_paper = [m for m in materials if 'paper' in m.get('name', '').lower()]
assert len(opaque_paper) == 2
assert all(m.get('alphaMode', 'OPAQUE') == 'OPAQUE' for m in opaque_paper)
ink_materials = [m for m in materials if 'shadowless alpha' in m.get('name', '')]
assert len(ink_materials) == 2 and all(m.get('alphaMode') == 'BLEND' for m in ink_materials)
assert all(image.get('bufferView') is not None and 'uri' not in image for image in gltf['images'])
report = {
    'passed': True, 'mechanicsPreservedByBuildComparison': True,
    'roots': names, 'paperClosedManifold': True, 'paperVolume': volume,
    'paperThickness': front_radius - back_radius, 'paperJarMinimumRadialClearance': clearance,
    'paperMaxFrontTriangleAngleSpan': front_angle_span, 'paperMaxFrontChordSagBound': front_chord_sag_bound,
    'paperFrontBackNonintersectionRadialMargin': front_back_margin,
    'paperBackAndEdgeUnprinted': True, 'paperFaceMaterialCounts': {'printedFront': front_count, 'unprintedBackAndEdge': back_count},
    'logoAndProductMeshRootsVisible': True, 'inkClearanceFromPaper': ink_clearance,
    'printCarrierShadowDisabled': True, 'packedRasterSize': [2048, 1280],
    'sourcePoses': poses, 'glbRootNames': names, 'glbAnimationCount': len(gltf.get('animations', [])),
    'glbEmbeddedImageCount': len(gltf.get('images', [])), 'glbBytes': len(content),
    'sourceBytes': (HERE / 'poster-012-v2.blend').stat().st_size,
    'visualReviewPending': True, 'productionRegistered': False,
}
(HERE / 'source-verification.json').write_text(json.dumps(report, indent=2) + '\n')
print('POSTER_012_SOURCE_VERIFIED', json.dumps({k: report[k] for k in ['passed', 'paperJarMinimumRadialClearance', 'paperBackAndEdgeUnprinted', 'inkClearanceFromPaper', 'glbAnimationCount', 'glbBytes', 'sourceBytes']}))
