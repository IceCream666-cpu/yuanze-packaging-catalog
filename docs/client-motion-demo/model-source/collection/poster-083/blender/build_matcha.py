import bpy, math, os, sys, json
from pathlib import Path
from mathutils import Vector
ROOT=Path(__file__).resolve().parent
bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)
scene=bpy.context.scene

def mat(name,color,rough=.4,metal=0):
 m=bpy.data.materials.new(name);m.use_nodes=True;p=m.node_tree.nodes.get('Principled BSDF');p.inputs['Base Color'].default_value=(*color,1);p.inputs['Roughness'].default_value=rough;p.inputs['Metallic'].default_value=metal;return m
olive=mat('Deep olive satin empty bottle',(.040,.070,.022),.43)
cream=mat('Pale butter cream pump',(.78,.75,.48),.29)
ink=mat('Deep olive typography',(.018,.034,.013),.65)
lightink=mat('Ivory small typography',(.79,.82,.63),.6)
label=mat('Low contrast matcha checkerboard paper',(.64,.72,.34),.72)
n=label.node_tree.nodes;links=label.node_tree.links;p=n.get('Principled BSDF');uv=n.new('ShaderNodeTexCoord');mapping=n.new('ShaderNodeVectorMath');mapping.operation='MULTIPLY';mapping.inputs[1].default_value=(28,6,1);checker=n.new('ShaderNodeTexChecker');checker.inputs['Color1'].default_value=(.59,.66,.31,1);checker.inputs['Color2'].default_value=(.66,.72,.38,1);checker.inputs['Scale'].default_value=1;links.new(uv.outputs['UV'],mapping.inputs[0]);links.new(mapping.outputs['Vector'],checker.inputs['Vector']);links.new(checker.outputs['Color'],p.inputs['Base Color'])

def lathe(name,profile,material,segments=192):
 vs=[];fs=[]
 for r,z in profile:
  for i in range(segments):
   a=2*math.pi*i/segments;vs.append((r*math.sin(a),-r*math.cos(a),z))
 for j in range(len(profile)-1):
  for i in range(segments):
   a=j*segments+i;b=j*segments+(i+1)%segments;fs.append((a,b,b+segments,a+segments))
 mesh=bpy.data.meshes.new(name);mesh.from_pydata(vs,[],fs);mesh.update();o=bpy.data.objects.new(name,mesh);bpy.context.collection.objects.link(o);o.data.materials.append(material)
 for f in mesh.polygons:f.use_smooth=True
 uv=o.data.uv_layers.new()
 for p in mesh.polygons:
  j=p.index//segments;i=p.index%segments
  coords=[(i/segments,j/(len(profile)-1)),((i+1)/segments,j/(len(profile)-1)),((i+1)/segments,(j+1)/(len(profile)-1)),(i/segments,(j+1)/(len(profile)-1))]
  for li,co in zip(p.loop_indices,coords):uv.data[li].uv=co
 return o
# A hollow shell, not a formula-filled cylinder. Shoulder and side proportions follow reference.
body=lathe('Bottle shell',[(0,.08),(.82,.08),(.94,.09),(.995,.14),(1.015,.24),(1.025,.6),(1.045,1.2),(1.065,2.0),(1.075,2.52),(1.072,2.70),(1.06,2.77),(1.02,2.83),(.96,2.87),(.80,2.89),(.37,2.89),(.33,2.93),(.33,3.10),(.28,3.10),(.28,2.90),(.80,2.82),(.99,2.76),(1.01,2.64),(.99,1.2),(.95,.28),(.84,.19),(0,.19)],olive)
# Wide raised shoulder disk edge, visible as in the real bottle.
lathe('Shoulder rim',[(.98,2.83),(1.025,2.84),(1.042,2.87),(1.02,2.905),(.37,2.905)],olive)
lathe('Cream complete pump collar',[(0,2.93),(.36,2.93),(.405,2.96),(.415,3.02),(.415,3.34),(.40,3.38),(.34,3.40),(0,3.40)],cream)
lathe('Cream pump stem',[(0,3.38),(.22,3.38),(.22,3.56),(.25,3.59),(0,3.59)],cream)
lathe('Round pressing disk',[(0,3.55),(.42,3.55),(.48,3.58),(.49,3.66),(.475,3.70),(.42,3.715),(0,3.715)],cream)

def rounded_box(name,loc,scale,material,bevel=.04):
 bpy.ops.mesh.primitive_cube_add(size=1,location=loc);o=bpy.context.object;o.name=name;o.dimensions=scale;bpy.ops.object.transform_apply(location=False,rotation=False,scale=True);o.data.materials.append(material);m=o.modifiers.new('Soft molded corners','BEVEL');m.width=bevel;m.segments=5;o.modifiers.new('Weighted normals','WEIGHTED_NORMAL');return o
rounded_box('Short flat pump tab',(-.49,-.01,3.635),(.71,.255,.145),cream,.035)
nozzle=mat('Recessed outlet shadow',(.19,.21,.10),.52)
rounded_box('Short tab underside outlet',(-.77,-.01,3.557),(.09,.10,.011),nozzle,.01)
# Wraparound printed label. Label remains a single continuous paper band.
LABEL_ROWS=[(1.045,.59),(1.054,.85),(1.078,1.70),(1.088,2.12)]
lathe('Checkerboard wrap label',LABEL_ROWS,label)
def label_radius(z):
 for (r0,z0),(r1,z1) in zip(LABEL_ROWS,LABEL_ROWS[1:]):
  if z0<=z<=z1:return r0+(r1-r0)*(z-z0)/(z1-z0)
 return LABEL_ROWS[0][0] if z<LABEL_ROWS[0][1] else LABEL_ROWS[-1][0]

def wrapped_text(name,body,z,size,font,material,max_width=None,radius=1.074):
 curve=bpy.data.curves.new(name,'FONT');curve.body=body;curve.align_x='CENTER';curve.align_y='CENTER';curve.size=size;curve.extrude=0;curve.resolution_u=12;curve.font=bpy.data.fonts.load(font)
 o=bpy.data.objects.new(name,curve);bpy.context.collection.objects.link(o);o.data.materials.append(material);bpy.context.view_layer.objects.active=o;o.select_set(True);bpy.context.view_layer.update()
 if max_width and o.dimensions.x>max_width:o.scale.x=max_width/o.dimensions.x
 bpy.ops.object.convert(target='MESH');bpy.ops.object.transform_apply(location=False,rotation=False,scale=True)
 for v in o.data.vertices:
  x,y=v.co.x,v.co.y
  rr=label_radius(z+y)+.004 if name in ('Matcha product lettering','Shampoo product subtitle') else radius
  a=x/rr;v.co=(rr*math.sin(a),-rr*math.cos(a)-.006,z+y)
 o.select_set(False);o.visible_shadow=False
 return o
F='/System/Library/Fonts/Supplemental/'
wrapped_text('Brand liaose','liaose',2.47,.29,F+'Arial Black.ttf',lightink,1.30,1.08)
wrapped_text('Matcha product lettering','matcha',1.47,.68,F+'Georgia Italic.ttf',ink,2.05,1.074)
wrapped_text('Shampoo product subtitle','SHAMPOO',.94,.123,F+'Arial.ttf',ink,1.1,1.048)
wrapped_text('Bottom product category','HAIR CARE',.40,.088,F+'Arial.ttf',lightink,.8,1.02)
wrapped_text('Bottom net weight','500 g',.25,.10,F+'Arial.ttf',lightink,.4,1.02)
# Studio plane catches only the contact shadow so it remains reusable over a poster background.
bpy.ops.mesh.primitive_plane_add(size=200,location=(0,0,.075));floor=bpy.context.object;floor.name='Optional contact shadow catcher';floor.is_shadow_catcher=True;floor.hide_render=True;floor.data.materials.append(mat('Neutral shadow catcher',(.7,.7,.7),.8))
world=bpy.data.worlds.new('Neutral warm ivory studio');world.use_nodes=True;world.node_tree.nodes['Background'].inputs['Color'].default_value=(.80,.81,.78,1);world.node_tree.nodes['Background'].inputs['Strength'].default_value=.34;scene.world=world

def aim(o,target):o.rotation_euler=(Vector(target)-o.location).to_track_quat('-Z','Y').to_euler()
def softbox(name,loc,width,height,energy,color):
 bpy.ops.object.light_add(type='AREA',location=loc);o=bpy.context.object;o.name=name;o.data.shape='RECTANGLE';o.data.size=width;o.data.size_y=height;o.data.energy=energy;o.data.color=color;aim(o,(0,0,1.7))
softbox('Large warm key',(-3.5,-4.5,6),3,5,560,(1,.97,.89))
softbox('Broad frontal fill',(2.8,-4.5,3.4),3.5,4,200,(.95,.98,1))
softbox('Soft upper edge',(1.5,2.0,5.5),2.5,3,380,(1,1,.95))
bpy.ops.object.camera_add(location=(.25,-12,5.1));cam=bpy.context.object;cam.name='Poster product camera';cam.data.type='ORTHO';cam.data.ortho_scale=4.8;aim(cam,(0,0,1.83));scene.camera=cam
final='--final' in sys.argv
scene.render.engine='CYCLES';scene.cycles.device='CPU';scene.cycles.samples=96 if final else 16;scene.cycles.use_denoising=True;scene.cycles.max_bounces=10
scene.render.resolution_x=2000 if final else 800;scene.render.resolution_y=2400 if final else 960;scene.render.resolution_percentage=100;scene.render.film_transparent=True;scene.render.image_settings.file_format='PNG';scene.render.image_settings.color_mode='RGBA';scene.view_settings.view_transform='AgX';scene.view_settings.look='AgX - Medium High Contrast'
scene.render.filepath=str(ROOT/('matcha-product-final.png' if final else 'matcha-product-preview-v2.png'))
bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'matcha-shampoo.blend'))
bpy.ops.render.render(write_still=True)
(ROOT/'scene-info.json').write_text(json.dumps({'front':'negative Y','up':'positive Z','camera':list(cam.location),'dimensions':{'bodyDiameter':2.15,'bodyHeight':2.89,'totalHeight':3.715},'source':'reference-05-matcha.jpg','containsFormula':False,'realDimensions':False},indent=2))
