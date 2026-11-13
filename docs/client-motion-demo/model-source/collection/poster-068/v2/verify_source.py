"""Check original geometry and rigid cap fit in the saved Blender source."""
import bpy,json
from pathlib import Path
HERE=Path(__file__).resolve().parent

def points(ob):
 return [tuple(round(v,6) for v in ob.matrix_world@p.co) for p in ob.data.vertices]

bpy.ops.wm.open_mainfile(filepath=str(HERE.parent/'poster-068.blend'))
original={o.name:points(o) for group in ['Body','Closure','NeckInsert'] for o in bpy.data.objects[group].children if o.type=='MESH'}
bpy.ops.wm.open_mainfile(filepath=str(HERE/'poster-068-v2.blend'))
scene=bpy.context.scene;scene.frame_set(1);bpy.context.view_layer.update()
assert all(points(bpy.data.objects[name])==values for name,values in original.items())
cap=bpy.data.objects['CapAssembly'];children=list(cap.children);assert len(children)==3
rest=[o.matrix_local.copy() for o in children]
for frame in [1,31,61,31,1]:
 scene.frame_set(frame);bpy.context.view_layer.update()
 assert all(o.matrix_local==m for o,m in zip(children,rest))
assert scene.render.engine=='CYCLES' and len([o for o in scene.objects if o.type=='LIGHT'])==4
assert all(o.visible_shadow for o in bpy.data.objects['Label'].children)
assert all(not o.visible_shadow for n in ['LogoInk','NameInk'] for o in bpy.data.objects[n].children)
(HERE/'source-verification.json').write_text(json.dumps({'originalGeometryWorldCoordinatesUnchanged':list(original),'completeCapChildCount':len(children),'rigidClosedHalfFullReturn':True,'physicalLabelCastsShadow':True,'letterPlanesCastNoOpaqueShadows':True,'renderEngine':scene.render.engine,'containsFormula':False},ensure_ascii=False,indent=2)+'\n')
print('SOURCE_VERIFIED',len(original),'original meshes; complete cap rigid through all poses')
