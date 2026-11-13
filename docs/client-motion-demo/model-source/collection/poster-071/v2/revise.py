"""Keep the approved external bottle and combine the functional pump assembly."""
import bpy,math,json,sys
from pathlib import Path
from mathutils import Vector
HERE=Path(__file__).resolve().parent;CLIENT=HERE.parents[3]
sys.path.insert(0,str(HERE.parents[1]));from tail_model_helpers import Model
SOURCE=Path('/Users/icecream/Documents/Codex/2026-10-22/gen/work/client18/docs/long-neck-3d/liaose-pump.blend')
bpy.ops.wm.open_mainfile(filepath=str(SOURCE));scene=bpy.context.scene
for o in list(scene.objects):
 if o.parent is None and o.type!='EMPTY':bpy.data.objects.remove(o,do_unlink=True)
for o in scene.objects:o.animation_data_clear()
body=bpy.data.objects['BottleAssembly'];body.name='Body'
ink=bpy.data.objects['LogoPrint'];ink.name='LogoInk'
pump=bpy.data.objects.new('PumpAssembly',None);bpy.context.collection.objects.link(pump)
for name in ['Closure','PumpStem','PumpHead']:
 old=bpy.data.objects[name]
 for o in list(old.children):
  transform=o.matrix_world.copy();o.parent=pump;o.matrix_world=transform
 bpy.data.objects.remove(old,do_unlink=True)
# Retain every external vertex; replace only the old shallow cavity with an empty inner wall.
bottle=bpy.data.objects['Bottle'];old=bottle.data;N=128;R=105
outer=[tuple(v.co) for v in old.vertices[:N*R]];vs=list(outer)
for ring in range(R-1,7,-1):
 points=outer[ring*N:(ring+1)*N];z=points[0][2]
 if z<.11:continue
 for x,y,z in points:
  vs.append((x*.92,y*.90,max(.105,z-.018)))
fs=[];rings=len(vs)//N
for j in range(rings-1):
 for i in range(N):a=j*N+i;b=j*N+(i+1)%N;fs.append((a,b,b+N,a+N))
fs += [tuple(reversed(range(N))),tuple((rings-1)*N+i for i in range(N))]
mesh=bpy.data.meshes.new('Preserved exterior with hollow interior');mesh.from_pydata(vs,[],fs);mesh.update();mesh.materials.append(old.materials[0]);bottle.data=mesh
for f in mesh.polygons:f.use_smooth=True
assert all((mesh.vertices[i].co-old.vertices[i].co).length<1e-7 for i in range(len(outer)))
m=Model.__new__(Model);m.groups={};clear=m.mat('Sculptural clear hollow polyethylene dip tube','#f6faf7',.055,.98)
# A true hollow tube with open lower annulus; it remains captive to the complete pump.
vs=[];fs=[];steps=64;n=48
for radius in [.043,.029]:
 for j in range(steps+1):
  t=j/steps;z=.135+t*1.91;x=.14*(1-t)**3
  for i in range(n):a=math.tau*i/n;vs.append((x+radius*math.cos(a),radius*math.sin(a),z))
stride=(steps+1)*n
for side in range(2):
 for j in range(steps):
  for i in range(n):a=side*stride+j*n+i;b=side*stride+j*n+(i+1)%n;f=(a,b,b+n,a+n);fs.append(f if side==0 else f[::-1])
for j in [0,steps]:
 for i in range(n):a=j*n+i;b=j*n+(i+1)%n;fs.append((a,a+stride,b+stride,b))
tube=m.mesh('Long thick clear dip tube, open lower end',vs,fs,clear,'Build');tube.parent=pump
for o in list(m.groups.values()):bpy.data.objects.remove(o,do_unlink=True)
label=bpy.data.objects.new('Label',None);bpy.context.collection.objects.link(label)
original=bpy.data.objects['Front liaose print'];film=original.copy();film.data=original.data.copy();film.name='Transparent curved print carrier';bpy.context.collection.objects.link(film);film.parent=label
film.data.materials.clear();fm=m.mat('Clear neutral print carrier','#f5f4e9',.32);fm.node_tree.nodes['Principled BSDF'].inputs['Alpha'].default_value=.035;fm.surface_render_method='DITHERED';film.data.materials.append(fm)
for v in film.data.vertices:v.co.y+=.0007
original.visible_shadow=False
roots={n:bpy.data.objects[n] for n in ['Body','PumpAssembly','Label','LogoInk']}
# Use the art center as the pivot so enlargement does not pull the lettering below the bottle.
for g in [label,ink]:
 pivot=Vector((0,-.525,.3125))
 for o in g.children:o.location-=pivot
 g.location=pivot
p=json.loads((HERE/'review-product.json').read_text());ex=p['review']['explosion'];rest={n:(o.location.copy(),o.scale.copy()) for n,o in roots.items()}
for frame,t in [(1,0),(31,.5),(61,1)]:
 for part in p['parts']:
  k,n=part['key'],part['node'];o=roots[n];pos,sc=rest[n];x,y,z=ex['offsets'][k];o.location=pos+Vector((x,-z,y))*t;o.scale=sc*(1+(ex['scales'].get(k,1)-1)*t);o.keyframe_insert(data_path='location',frame=frame);o.keyframe_insert(data_path='scale',frame=frame)
 fm.node_tree.nodes['Principled BSDF'].inputs['Alpha'].default_value=.035+.245*t;fm.node_tree.nodes['Principled BSDF'].inputs['Alpha'].keyframe_insert(data_path='default_value',frame=frame)
scene.frame_set(1);bpy.context.view_layer.update();bpy.ops.object.select_all(action='DESELECT')
for o in roots.values():
 o.select_set(True)
 for child in o.children_recursive:child.select_set(True)
bpy.ops.export_scene.gltf(filepath=str(CLIENT/'packaging-assets/poster-071-v2.glb'),export_format='GLB',use_selection=True,export_apply=True,export_yup=True,export_animations=False,export_extras=True)
bpy.context.preferences.filepaths.save_version=0;bpy.ops.file.pack_all();bpy.ops.wm.save_as_mainfile(filepath=str(HERE/'poster-071-v2.blend'),compress=True)
(HERE/'build-verification.json').write_text(json.dumps({'roots':list(roots),'pumpMeshes':len(pump.children),'preservedExteriorVertices':len(outer),'dipTubeOuterDiameter':.086,'dipTubeInnerDiameter':.058,'dipTubeBottomZ':.135,'dipTubeTopZ':2.045,'containsFormula':False,'newProductCopy':False,'illustrativeInterior':True,'source':str(SOURCE)},indent=2)+'\n')
