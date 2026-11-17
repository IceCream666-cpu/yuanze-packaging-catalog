"""Read the approved original Blender source without modifying it."""
import bpy,bmesh,json
from pathlib import Path
HERE=Path(__file__).resolve().parent
bpy.ops.wm.open_mainfile(filepath=str(HERE.parent/'poster-082-v1.blend'))
bpy.context.scene.frame_set(1);bpy.context.view_layer.update()
objects=[]
for o in bpy.context.scene.objects:
    row={'name':o.name,'type':o.type,'parent':o.parent.name if o.parent else None,
         'location':list(o.location),'scale':list(o.scale),'shadow':o.visible_shadow,
         'hasAnimation':bool(o.animation_data)}
    if o.type=='MESH':
        points=[o.matrix_world@v.co for v in o.data.vertices]
        bm=bmesh.new();bm.from_mesh(o.data)
        row.update(vertices=len(o.data.vertices),faces=len(o.data.polygons),
                   manifold=all(e.is_manifold for e in bm.edges),volume=bm.calc_volume(signed=True),
                   materials=[m.name if m else None for m in o.data.materials],
                   bounds=[[min(p[i] for p in points) for i in range(3)],
                           [max(p[i] for p in points) for i in range(3)]])
        bm.free()
    objects.append(row)
materials=[]
for m in bpy.data.materials:
    if not m.use_nodes:continue
    p=m.node_tree.nodes.get('Principled BSDF')
    if not p:continue
    materials.append({'name':m.name,'base':list(p.inputs['Base Color'].default_value),
                      'roughness':p.inputs['Roughness'].default_value,
                      'transmission':p.inputs['Transmission Weight'].default_value,
                      'alpha':p.inputs['Alpha'].default_value,
                      'images':[{'name':n.image.name,'file':n.image.filepath,'packed':bool(n.image.packed_file),'size':list(n.image.size)}
                                for n in m.node_tree.nodes if n.type=='TEX_IMAGE' and n.image]})
report={'objects':objects,'materials':materials,'frameRange':[bpy.context.scene.frame_start,bpy.context.scene.frame_end]}
(HERE/'original-inspection.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
print(json.dumps(report,ensure_ascii=False))
