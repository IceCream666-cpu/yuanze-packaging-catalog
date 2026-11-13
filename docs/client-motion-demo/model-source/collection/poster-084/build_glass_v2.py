"""Correct the reviewed empty duo to neutral clear glass in local Blender."""
from pathlib import Path
import json
import bpy
P=Path(__file__).resolve().parent
bpy.ops.wm.open_mainfile(filepath=str(P/'poster-084-v1.blend'))
bpy.context.preferences.filepaths.save_version=0
body=bpy.data.objects['Body']
assert len(body.children)==2
mat=bpy.data.materials.new('Neutral clear glass | no blue or pink formula');mat.use_nodes=True
b=mat.node_tree.nodes.get('Principled BSDF')
b.inputs['Base Color'].default_value=(1,1,1,1)
b.inputs['Transmission Weight'].default_value=1
b.inputs['Roughness'].default_value=.035
b.inputs['IOR'].default_value=1.52
for o in body.children:
 assert 'hollow cylinder' in o.name
 o.data.materials.clear();o.data.materials.append(mat)
# All geometry, complete pumps, UVs and separate ink groups remain from v1.
bpy.ops.object.select_all(action='SELECT')
glb=P.parents[2]/'packaging-assets/poster-084-v2.glb'
bpy.ops.export_scene.gltf(filepath=str(glb),export_format='GLB',use_selection=True,export_yup=True,export_extras=True,export_animations=False)
bpy.ops.wm.save_as_mainfile(filepath=str(P/'poster-084-v2.blend'),compress=True)
info=json.loads((P/'model-info.json').read_text());info.update(file=glb.name,source='build_glass_v2.py',bodyMaterial='neutral transparent glass',containsFormula=False,referenceColorMeaning='blue and pink belong to contents, not container',blenderVersion=bpy.app.version_string)
(P/'model-info-v2.json').write_text(json.dumps(info,ensure_ascii=False,indent=2))
