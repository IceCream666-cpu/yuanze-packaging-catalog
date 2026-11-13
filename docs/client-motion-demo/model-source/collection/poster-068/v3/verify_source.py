import bpy,json
from pathlib import Path
from mathutils import Vector
HERE=Path(__file__).resolve().parent;S=2.9/2.36
bpy.ops.wm.open_mainfile(filepath=str(HERE.parent/'v2/poster-068-v2.blend'));bpy.context.scene.frame_set(1);bpy.context.view_layer.update()
def points(o,below=None):
 p=[o.matrix_world@v.co for v in o.data.vertices]
 return sorted(tuple(round(c,6) for c in v) for v in p if below is None or v.z<=below+1e-6)
cap_original=points(bpy.data.objects['Lavender cap with original U folded front'])
body_original=points(bpy.data.objects['Tall hollow rounded rectangular bottle and heavy glass base'],1.78*S)
bpy.ops.wm.open_mainfile(filepath=str(HERE/'poster-068-v3.blend'));scene=bpy.context.scene;scene.frame_set(1);bpy.context.view_layer.update()
assert cap_original==points(bpy.data.objects['Lavender cap with original U folded front'])
newpoints=points(bpy.data.objects['Hollow glass bottle with open threaded neck'],1.78*S)
from mathutils.kdtree import KDTree
assert len(body_original)==len(newpoints)
tree=KDTree(len(newpoints))
for i,p in enumerate(newpoints):tree.insert(Vector(p),i)
tree.balance()
body_delta=max(tree.find(Vector(p))[2] for p in body_original)
assert body_delta<2e-6,body_delta

cap=bpy.data.objects['CapAssembly'];collar=bpy.data.objects['Silver neck ring'];reducer=bpy.data.objects['FlowReducer'];plug=reducer.children[0]
assert collar.parent.name=='Body' and len(cap.children)==5 and len(reducer.children)==1
# A real open axial passage, not a painted black dot or closed cylinder.
assert not plug.ray_cast(Vector((0,0,3)),Vector((0,0,-1)))[0]
assert plug.ray_cast(Vector((.08,0,3)),Vector((0,0,-1)))[0]
rest=[o.matrix_local.copy() for o in cap.children];collar_rest=collar.matrix_local.copy()
for frame in [1,31,61,31,1]:
 scene.frame_set(frame);bpy.context.view_layer.update()
 assert all(max(abs(a-b) for ra,rb in zip(o.matrix_local,m) for a,b in zip(ra,rb))<2e-6 for o,m in list(zip(cap.children,rest))+[(collar,collar_rest)])
scene.frame_set(61);bpy.context.view_layer.update()
def bounds(ob):
 vs=[o.matrix_world@v.co for o in ob.children for v in o.data.vertices]
 return min(v.z for v in vs),max(v.z for v in vs)
assert bounds(cap)[0]>bounds(reducer)[1] and bounds(reducer)[0]>bounds(bpy.data.objects['Body'])[1]
assert scene.render.engine=='CYCLES'
assert all(o.visible_shadow for o in bpy.data.objects['Label'].children)
assert all(not o.visible_shadow for n in ['LogoInk','NameInk'] for o in bpy.data.objects[n].children)
(HERE/'source-verification.json').write_text(json.dumps({'sourceReopened':True,'lowerBottleAndExternalCapPreserved':True,'bottleCollarFixed':True,'capPiecesMoveTogether':len(cap.children),'reducerOpenAxialHoleRayTest':True,'expandedMechanicalComponentsDoNotIntersect':True,'labelShadow':True,'inkShadowDisabled':True,'hiddenStructure':'proposed illustrative closure, no verified production dimensions'},indent=2)+'\n')
print('VERIFIED: glass lower body and cap retained, open orifice, fixed collar, fitted cap, separated mechanical groups')
