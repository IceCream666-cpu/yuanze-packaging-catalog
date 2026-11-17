import bpy,json
from pathlib import Path
HERE=Path(__file__).resolve().parent;scene=bpy.context.scene
scene.frame_set(1);bpy.context.view_layer.update()
pump=bpy.data.objects['PumpAssembly'];tube=bpy.data.objects['Daily long hollow dip tube with open inlet']
assert tube.parent==pump
assert all(bpy.data.objects[n].parent==pump for n in ['Closure','Actuator','PumpStem'])
rest={o.name:o.matrix_local.copy() for o in pump.children_recursive}
for frame in [1,16,31,46,61,31,1]:
 scene.frame_set(frame);bpy.context.view_layer.update()
 for name,m in rest.items():assert all(abs(a-b)<1e-6 for row,r in zip(bpy.data.objects[name].matrix_local,m) for a,b in zip(row,r)),name
coords=[tube.matrix_world@v.co for v in tube.data.vertices];bounds=[min(v.z for v in coords),max(v.z for v in coords)]
assert .18<bounds[0]<.21 and bounds[1]>2.19
for group in ['LogoPrint','ProductPrint']:
 for o in bpy.data.objects[group].children:assert not o.visible_shadow
film=bpy.data.objects['PaperLabel'].children[0];assert film.visible_shadow
assert abs(film.active_material.node_tree.nodes['Principled BSDF'].inputs['Alpha'].default_value-.035)<1e-6
scene.frame_set(61);bpy.context.view_layer.update()
def zrange(root):
 ps=[o.matrix_world@v.co for o in bpy.data.objects[root].children_recursive if o.type=='MESH' for v in o.data.vertices];return min(p.z for p in ps),max(p.z for p in ps)
assert zrange('PumpAssembly')[0]>zrange('Body')[1]+.1
assert zrange('Overcap')[0]>zrange('PumpAssembly')[1]+.1
assert scene.render.engine=='CYCLES' and scene.cycles.samples==64
(HERE/'source-verification.json').write_text(json.dumps({'passed':True,'tubeBoundsZ':bounds,'pumpChildTransformsStable':True,'frames':[1,16,31,46,61,31,1],'fullExpansionClearances':True,'inkShadowDisabled':True,'filmShadowEnabled':True,'cyclesSamples':64,'containsFormula':False},indent=2)+'\n')
print('SOURCE VERIFICATION PASSED')
