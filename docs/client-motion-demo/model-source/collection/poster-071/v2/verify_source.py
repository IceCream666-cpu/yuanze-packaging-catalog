import bpy,json
from pathlib import Path
from mathutils import Vector
HERE=Path(__file__).resolve().parent
bpy.ops.wm.open_mainfile(filepath=str(HERE/'poster-071-v2.blend'));s=bpy.context.scene;s.frame_set(1);bpy.context.view_layer.update()
pump=bpy.data.objects['PumpAssembly'];body=bpy.data.objects['Body'];tube=bpy.data.objects['Long thick clear dip tube, open lower end'];bottle=bpy.data.objects['Bottle']
assert tube.parent==pump and len(pump.children)>70
rest={o.name:o.matrix_local.copy() for o in pump.children}
# The lower intake is a hole, with actual concentric wall geometry.
assert not tube.ray_cast(Vector((.14,0,.125)),Vector((0,0,1)))[0] or tube.ray_cast(Vector((.14,0,.125)),Vector((0,0,1)))[1].z>.15
assert min(v.co.z for v in tube.data.vertices)>.1
assert max(v.co.z for v in tube.data.vertices)>2
for f in [1,31,61,31,1]:
 s.frame_set(f);bpy.context.view_layer.update()
 for o in pump.children:assert max(abs(a-b) for r,t in zip(o.matrix_local,rest[o.name]) for a,b in zip(r,t))<2e-6
s.frame_set(61);bpy.context.view_layer.update()
assert min((tube.matrix_world@v.co).z for v in tube.data.vertices)>max((bottle.matrix_world@v.co).z for v in bottle.data.vertices)
assert all(o.visible_shadow for o in bpy.data.objects['Label'].children)
assert all(not o.visible_shadow for o in bpy.data.objects['LogoInk'].children)
s.frame_set(1);bpy.context.view_layer.update()
new_outer=[tuple(v.co) for v in bottle.data.vertices[:105*128]]
bpy.ops.wm.open_mainfile(filepath='/Users/icecream/Documents/Codex/2026-10-22/gen/work/client18/docs/long-neck-3d/liaose-pump.blend')
assert new_outer==[tuple(v.co) for v in bpy.data.objects['Bottle'].data.vertices[:105*128]]
(HERE/'source-verification.json').write_text(json.dumps({'reopenedSource':True,'externalBottleVerticesExactlyPreserved':len(new_outer),'pumpPiecesRemainFitted':len(rest),'dipTubeClearsBottleAtFullExpansion':True,'openIntake':True,'labelShadow':True,'inkShadowDisabled':True,'measuredManufacturingModel':False},indent=2)+'\n')
print('VERIFIED: original exterior, complete pump, open long dip tube, separate film and ink, shadows')
