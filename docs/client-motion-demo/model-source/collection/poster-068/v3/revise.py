"""A proposed pour-out toner closure, not a reverse-engineered production finish."""
import bpy,math,json,sys
from pathlib import Path
from mathutils import Vector,Matrix
HERE=Path(__file__).resolve().parent;CLIENT=HERE.parents[3]
sys.path.insert(0,str(HERE.parents[1]));from tail_model_helpers import Model
bpy.ops.wm.open_mainfile(filepath=str(HERE.parent/'v2/poster-068-v2.blend'))
scene=bpy.context.scene;scene.frame_set(1);bpy.context.view_layer.update()
for ob in list(scene.objects):
 if ob.parent is None and ob.type!='EMPTY':bpy.data.objects.remove(ob,do_unlink=True)
for ob in scene.objects:ob.animation_data_clear()
body=bpy.data.objects['Body'];cap=bpy.data.objects['CapAssembly']
def reparent(ob,group):
 mat=ob.matrix_world.copy();ob.parent=group;ob.matrix_world=mat
# A decorative collar belongs to the bottle, not the removable closure.
reparent(bpy.data.objects['Silver neck ring'],body)
bpy.data.objects.remove(bpy.data.objects['Concealed closing insert and center seal'],do_unlink=True)
oldglass=bpy.data.objects['Tall hollow rounded rectangular bottle and heavy glass base'];glass=oldglass.data.materials[0]
bpy.data.objects.remove(oldglass,do_unlink=True)
reducer=bpy.data.objects.new('FlowReducer',None);bpy.context.collection.objects.link(reducer)
m=Model.__new__(Model);m.groups={};S=2.9/2.36
pp=m.mat('Ivory PP inner screw cap','#dfdce0',.29)
pe=m.mat('Natural translucent PE flow reducer','#edeae6',.27,.16)
seal=m.mat('Soft PE sealing seat','#e9e7e3',.42)
def fitted(ob,group):
 ob.matrix_world=Matrix.Scale(S,4);reparent(ob,group);return ob
outer=[(0,0,0,0),(0,.41,.15,.05),(.018,.467,.207,.060),(.044,.492,.232,.064),(.075,.5,.24,.067),(1.69,.5,.24,.067),(1.72,.493,.233,.072),(1.75,.472,.213,.079),(1.768,.430,.173,.075),(1.780,.295,.132,.10),(1.798,.205,.125,.10),(1.83,.156,.156,.156),(1.958,.156,.156,.156),(1.97,.153,.153,.153)]
inner=[(1.97,.117,.117,.117),(1.83,.117,.117,.117),(1.750,.240,.100,.07),(1.735,.394,.140,.045),(1.708,.456,.196,.052),(.179,.456,.196,.052),(.141,.441,.181,.052),(.122,.405,.145,.05),(.115,0,0,0)]
fitted(m.loft('Hollow glass bottle with open threaded neck',outer+inner,glass,'Build',160),body)
def lathe(name,profile,material,group):return fitted(m.lathe(name,profile,material,'Build',160),group)
def helix(name,r,z,pitch,turns,thick,material,group):
 curve=bpy.data.curves.new(name,'CURVE');curve.dimensions='3D';curve.bevel_depth=thick;curve.bevel_resolution=4;curve.resolution_u=1
 spline=curve.splines.new('POLY');count=round(turns*160)+1;spline.points.add(count-1)
 for i,point in enumerate(spline.points):
  a=i/(count-1)*turns*math.tau;point.co=(r*math.cos(a),r*math.sin(a),z+a/math.tau*pitch,1)
 curve.use_fill_caps=True;ob=bpy.data.objects.new(name,curve);bpy.context.collection.objects.link(ob);curve.materials.append(material)
 bpy.ops.object.select_all(action='DESELECT');ob.select_set(True);bpy.context.view_layer.objects.active=ob;bpy.ops.object.convert(target='MESH');return fitted(bpy.context.object,group)
helix('Glass external neck thread',.159,1.846,.046,2.15,.008,glass,body)
# One hollow reducer part: flange, retention ribs and small through-orifice.
profile=[(1.903,.099),(1.903,.112),(1.914,.116),(1.937,.116),(1.941,.121),(1.947,.121),(1.951,.116),(1.975,.116),(1.979,.121),(1.985,.121),(1.99,.116),(2.009,.116),(2.01,.161),(2.022,.161),(2.026,.153),(2.026,.023),(2.01,.023),(2.004,.099),(1.903,.099)]
lathe('PE reducer flange retention ribs and through-hole',[(z-.04,r) for z,r in profile],pe,reducer)
# Concealed cup and seal stay inside the intact sculpted outer cap.
lathe('PP threaded inner cap cup',[(1.865,.176),(1.865,.191),(2.029,.191),(2.038,.184),(2.038,0),(2.007,0),(2.007,.175),(1.865,.176)],pp,cap)
helix('PP internal mating screw thread',.173,1.869,.046,2.15,.007,pp,cap)
lathe('Captive annular sealing seat',[(1.988,.038),(1.988,.151),(2.007,.151),(2.007,.038),(1.988,.038)],seal,cap)
lathe('Captive center sealing pin',[(1.966,0),(1.966,.017),(1.974,.022),(2.007,.022),(2.007,0)],seal,cap)
for ob in list(m.groups.values()):bpy.data.objects.remove(ob,do_unlink=True)
roots={name:bpy.data.objects[name] for name in ['Body','CapAssembly','FlowReducer','Label','LogoInk','NameInk']}
p=json.loads((HERE/'review-product.json').read_text());ex=p['review']['explosion'];rest={n:(o.location.copy(),o.scale.copy()) for n,o in roots.items()}
for frame,t in [(1,0),(31,.5),(61,1)]:
 for part in p['parts']:
  key,node=part['key'],part['node'];ob=roots[node];pos,scale=rest[node];x,y,z=ex['offsets'][key]
  ob.location=pos+Vector((x,-z,y))*t;ob.scale=scale*(1+(ex['scales'].get(key,1)-1)*t)
  ob.keyframe_insert(data_path='location',frame=frame);ob.keyframe_insert(data_path='scale',frame=frame)
scene.frame_set(1);bpy.context.view_layer.update()
# Validate the proposed fit and open liquid path in model units, not manufacturing tolerances.
assert .117 < .121 and .153 < .161 and .022 < .023
assert .159+.008 < .175 and 1.986 < 1.988
assert len(cap.children)==5 and len(reducer.children)==1
bpy.ops.object.select_all(action='DESELECT')
for ob in roots.values():
 ob.select_set(True)
 for child in ob.children_recursive:child.select_set(True)
bpy.ops.export_scene.gltf(filepath=str(CLIENT/'packaging-assets/poster-068-v3.glb'),export_format='GLB',use_selection=True,export_apply=True,export_yup=True,export_animations=False,export_extras=True)
bpy.context.preferences.filepaths.save_version=0;bpy.ops.file.pack_all();bpy.ops.wm.save_as_mainfile(filepath=str(HERE/'poster-068-v3.blend'),compress=True)
(HERE/'build-verification.json').write_text(json.dumps({'roots':list(roots),'capChildren':[o.name for o in cap.children],'bottleChildren':[o.name for o in body.children],'reducerChildren':[o.name for o in reducer.children],'liquidPathOpen':True,'illustrativeHiddenStructure':True,'containsFormula':False,'source':'../v2/poster-068-v2.blend'},indent=2)+'\n')
