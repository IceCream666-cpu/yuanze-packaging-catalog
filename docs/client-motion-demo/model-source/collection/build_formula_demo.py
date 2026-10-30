"""Separate optical demo; never register these filled assets in the empty packaging library."""
import bpy, sys, math, json
from pathlib import Path
from mathutils import Vector
BASE=Path(__file__).resolve().parent
sys.path.insert(0,str(BASE))
from tail_model_helpers import Model
OUT=Path(sys.argv[sys.argv.index('--')+1]);OUT.mkdir(parents=True,exist_ok=True)

for id,total in [('daily-emulsion',2.8),('body-oil-collection',2.182)]:
 bpy.ops.wm.open_mainfile(filepath=str(BASE/id/(id+'.blend')))
 m=object.__new__(Model);m.groups={};m.out=BASE/id
 cream=id=='daily-emulsion';scale=2.9/total
 material=m.mat('Demo ivory emulsion' if cream else 'Demo golden body oil','#f5efda' if cream else '#ffffff',.23 if cream else .018,0 if cream else 1)
 bsdf=material.node_tree.nodes.get('Principled BSDF');bsdf.inputs['IOR'].default_value=1.46
 if cream:
  bsdf.inputs['Subsurface Weight'].default_value=.06
  bsdf.inputs['Subsurface Radius'].default_value=(.12,.08,.04)
  profile=[(.145,0,0,0),(.146,.36,.18,.09),(.16,.42,.22,.1),(.20,.465,.255,.108),(1.63,.465,.255,.108),(1.67,.461,.251,.108),(1.673,.451,.241,.1),(1.669,0,0,0)]
  liquid=m.loft('Demo emulsion with gently curved surface',profile,material,'Formula',160)
 else:
  absorb=material.node_tree.nodes.new('ShaderNodeVolumeAbsorption');absorb.inputs['Color'].default_value=(1,.92,.015,1);absorb.inputs['Density'].default_value=2.8
  material.node_tree.links.new(absorb.outputs['Volume'],material.node_tree.nodes.get('Material Output').inputs['Volume'])
  profile=[(.144,0),(.149,.35),(.16,.40),(.18,.433),(.21,.45),(.25,.457),(1.12,.457),(1.18,.452),(1.24,.439),(1.30,.417),(1.36,.388),(1.42,.351),(1.46,.323),(1.468,.317),(1.46,.303),(1.456,.27),(1.455,0)]
  liquid=m.lathe('Demo golden oil with static meniscus',profile,material,'Formula',192)
 liquid.parent.scale=(scale,)*3
 bpy.context.view_layer.update()
 assert liquid.dimensions.z>1 and len(m.groups)==1
 # The same source geometry, camera, lighting and exposure serve both states.
 objects=list(bpy.context.scene.objects)
 bpy.ops.object.select_all(action='SELECT')
 bpy.ops.export_scene.gltf(filepath=str(OUT/(id+'-filled-demo.glb')),export_format='GLB',use_selection=True,export_apply=True,export_yup=True,export_extras=True)
 carrier=bpy.data.objects.get('PaperLabel')
 for o in carrier.children:o.hide_render=True
 # Thin printed decals should not appear a second time through the inner wall.
 for group in ['LogoPrint','ProductPrint']:
  for o in bpy.data.objects[group].children:o.visible_transmission=False;o.visible_glossy=False
 scene=bpy.context.scene;scene.render.engine='CYCLES';scene.cycles.samples=96;scene.cycles.use_denoising=True
 scene.cycles.max_bounces=16;scene.cycles.transmission_bounces=12;scene.cycles.transparent_max_bounces=16
 scene.render.resolution_x=768;scene.render.resolution_y=1024;scene.render.resolution_percentage=100
 scene.render.image_settings.file_format='PNG';scene.view_settings.view_transform='AgX';scene.view_settings.look='AgX - Medium High Contrast';scene.view_settings.exposure=.4
 world=bpy.data.worlds.new('Neutral studio');world.use_nodes=True;world.node_tree.nodes['Background'].inputs[0].default_value=(.63,.60,.55,1);world.node_tree.nodes['Background'].inputs[1].default_value=.5;scene.world=world
 floor=m.mat('Warm stone studio','#ede4d2',.65)
 bpy.ops.mesh.primitive_plane_add(size=200,location=(0,0,-.012));bpy.context.object.data.materials.append(floor)
 def area(name,pos,power,size,color):
  data=bpy.data.lights.new(name,'AREA');data.energy=power;data.shape='RECTANGLE';data.size=size[0];data.size_y=size[1];data.color=color
  obj=bpy.data.objects.new(name,data);scene.collection.objects.link(obj);obj.location=pos;obj.rotation_euler=(Vector((0,0,1.45))-obj.location).to_track_quat('-Z','Y').to_euler()
 area('Left strip',(-3,-4,4.5),450,(2,5),(1,.94,.86))
 area('Right strip',(3,-1,3),330,(.8,4),(1,1,1))
 area('Back softbox',(0,3,4),500,(3,3),(1,.96,.9))
 data=bpy.data.cameras.new('Matched comparison camera');cam=bpy.data.objects.new('Matched comparison camera',data);scene.collection.objects.link(cam)
 cam.location=(.22,-7,2.35);cam.rotation_euler=(Vector((0,0,1.46))-cam.location).to_track_quat('-Z','Y').to_euler();data.type='ORTHO';data.ortho_scale=3.65;scene.camera=cam
 bpy.ops.wm.save_as_mainfile(filepath=str(OUT/(id+'-demo-studio.blend')))
 for filled in [False,True]:
  liquid.hide_render=not filled;scene.render.filepath=str(OUT/(id+('-filled' if filled else '-empty')+'.png'));bpy.ops.render.render(write_still=True)
 print('VERIFIED',id,'same camera and lights; distinct Formula mesh; empty image hides formula',flush=True)
(OUT/'demo-info.json').write_text(json.dumps({'separateFromProduction':True,'renderer':'Blender Cycles','samples':96,'sameCameraAndLighting':True,'formula':'Static closed mesh, no flow simulation; golden oil volume absorption in Blender; GLB viewers may differ.'},indent=2))
