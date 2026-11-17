import bpy,json
from pathlib import Path
from mathutils import Vector
HERE=Path(__file__).resolve().parent
scene=bpy.context.scene;scene.frame_set(1);bpy.context.view_layer.update()
pump=bpy.data.objects['PumpAssembly'];tube=bpy.data.objects['Long hollow dip tube with open inlet']
assert tube.parent==pump
rest={o.name:o.matrix_local.copy() for o in pump.children_recursive}
assert all(bpy.data.objects[n].parent==pump for n in ['Closure','Actuator','PumpStem'])
for f in [1,31,61,31,1]:
 scene.frame_set(f);bpy.context.view_layer.update()
 for n,m in rest.items():assert all(abs(a-b)<1e-6 for row,r in zip(bpy.data.objects[n].matrix_local,m) for a,b in zip(row,r)),n
coords=[tube.matrix_world@v.co for v in tube.data.vertices];lo=min(v.z for v in coords);hi=max(v.z for v in coords)
assert .15<lo<.2 and hi>2
for group in ['LogoInk','ProductPrint']:
 for o in bpy.data.objects[group].children:assert not o.visible_shadow
assert all(o.visible_shadow for o in bpy.data.objects['PaperLabel'].children)
assert scene.render.engine=='CYCLES' and scene.cycles.samples==64
(HERE/'source-verification.json').write_text(json.dumps({'passed':True,'tubeBoundsZ':[lo,hi],'pumpChildTransformsStable':True,'frames':[1,31,61,31,1],'inkShadowDisabled':True,'labelShadowEnabled':True,'cyclesSamples':64},indent=2)+'\n')
print('SOURCE VERIFICATION PASSED')
