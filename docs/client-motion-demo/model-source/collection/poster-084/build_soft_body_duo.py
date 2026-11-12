"""Reference-led empty plastic tube and disc-pump duo, built with local Blender."""
import json, math, shutil, struct, subprocess, sys, zlib
from pathlib import Path
import bpy, bmesh
from mathutils import Vector

OUT=Path(__file__).resolve().parent
BASE=OUT.parent
sys.path.insert(0,str(BASE))
from tail_model_helpers import Model, NODE
GLB=BASE.parents[1]/'packaging-assets/poster-084-v1.glb'
GROUPS=('Body','Pump','Label','LogoInk','NameInk')
PIVOTS={'Body':(0,0,1),'Pump':(0,0,2.4),'Label':(0,0,1.7),'LogoInk':(0,0,.4),'NameInk':(0,0,1.7)}
class Duo(Model):
 def __init__(self): self.out=OUT;self.groups={}

def fix(ob):
 bm=bmesh.new();bm.from_mesh(ob.data)
 bmesh.ops.remove_doubles(bm,verts=list(bm.verts),dist=1e-7)
 bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces))
 assert all(e.is_manifold for e in bm.edges),ob.name
 assert bm.calc_volume(signed=True)>0,ob.name
 bm.to_mesh(ob.data);bm.free();ob.data.update()

def rings(name,rows,mat,parent,cx,sections=128):
 vs=[];fs=[];indices=[]
 for z,rx,ry,power in rows:
  row=[]
  for i in range(sections if rx and ry else 1):
   t=math.tau*i/sections
   signed=lambda v:math.copysign(abs(v)**(2/power),v)
   row.append(len(vs));vs.append((cx+rx*signed(math.cos(t)),ry*signed(math.sin(t)),z))
  indices.append(row)
 for a,b in zip(indices,indices[1:]):
  for i in range(sections):
   j=(i+1)%sections
   if len(a)==len(b)==1:continue
   fs.append((a[0],b[j],b[i]) if len(a)==1 else (a[i],a[j],b[0]) if len(b)==1 else (a[i],a[j],b[j],b[i]))
 ob=model.mesh(name,vs,fs,mat,parent);fix(ob);return ob

def roundpart(name,profile,mat,parent,cx):
 ob=model.lathe(name,profile,mat,parent,128)
 for v in ob.data.vertices:v.co.x+=cx
 return ob

def box(name,location,scale,material,parent,r=.015):
 bpy.ops.mesh.primitive_cube_add(size=1,location=location)
 ob=bpy.context.object;ob.name=name;ob.scale=scale
 bpy.ops.object.transform_apply(location=False,rotation=False,scale=True)
 mod=ob.modifiers.new('Soft molded edge','BEVEL');mod.width=r;mod.segments=4
 bpy.ops.object.modifier_apply(modifier=mod.name)
 ob.data.materials.append(material)
 ob.parent=model.groups[parent]
 for face in ob.data.polygons:face.use_smooth=True
 mod=ob.modifiers.new('Weighted face normals','WEIGHTED_NORMAL');mod.keep_sharp=True
 bpy.ops.object.modifier_apply(modifier=mod.name)
 return ob

def dip_tube():
 vs=[];fs=[];outer=[];inner=[];n=48;m=48
 for i in range(n+1):
  t=i/n;z=1.985-(1.985-.115)*t;dx=.145*t**2
  for radius,rows in [(.041,outer),(.029,inner)]:
   rows.append(list(range(len(vs),len(vs)+m)))
   for j in range(m):
    a=j*math.tau/m;vs.append((BOTTLE_X+dx+radius*math.cos(a),radius*math.sin(a),z+(.45*radius*math.cos(a) if i==n else 0)))
 for i in range(n):
  for j in range(m):k=(j+1)%m;fs.extend([(outer[i][j],outer[i][k],outer[i+1][k],outer[i+1][j]),(inner[i][k],inner[i][j],inner[i+1][j],inner[i+1][k])])
 for j in range(m):
  k=(j+1)%m;fs.extend([(outer[0][k],outer[0][j],inner[0][j],inner[0][k]),(outer[-1][j],outer[-1][k],inner[-1][k],inner[-1][j])])
 ob=model.mesh('Long clear hollow dip tube | near-bottom angled intake',vs,fs,clear_tube,'Pump');fix(ob)

def printing_sheet(name,cx,w,h,z,mat,parent,offset=.003):
 ob=model.sheet(name,w,h,z,lambda x,z:-math.sqrt(max(0,.575**2-x*x)),mat,parent,64,24,offset)
 for v in ob.data.vertices:v.co.x+=cx
 return ob

def art(name,content,w=1000,h=600):
 p=OUT/(name+'.svg');p.write_text(f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}">{content}</svg>')
 subprocess.run([NODE,'--input-type=module','-e',"import sharp from '/Users/icecream/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/sharp/dist/index.mjs';await sharp(process.argv[1]).png().toFile(process.argv[2]);",str(p),str(p.with_suffix('.png'))],check=True)
 return model.texture(name,name+'.png',.6)

bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.context.preferences.filepaths.save_version=0
model=Duo()
clear_tube=model.mat('Clear polyethylene hollow suction tube','#e1e9f0',.1)
bsdf=clear_tube.node_tree.nodes.get('Principled BSDF');bsdf.inputs['Alpha'].default_value=.32
clear_tube.surface_render_method='DITHERED';clear_tube.use_backface_culling=True
pump=model.mat('Translucent pearl-white molded pump','#eef0f4',.24,trans=.15)
label=model.mat('White satin wrap label','#faf9f7',.65)
logo=art('liaose-white','<text x="500" y="150" text-anchor="middle" fill="white" font-family="Helvetica Neue,Arial" font-size="150" letter-spacing="18">liaose</text>',1000,190)
profile=[(0,0),(0,.44),(.007,.49),(.022,.535),(.05,.561),(.09,.572),(.14,.575),(1.88,.575),(1.93,.571),(1.965,.552),(1.986,.514),(1.998,.40),(2.006,.26),(2.012,.18),(2.035,.166),(2.060,.166),(2.066,.176),(2.083,.176),(2.089,.166),(2.127,.166),(2.134,.171),(2.149,.171),(2.155,.164),(2.155,.136),(2.023,.136),(1.993,.18),(1.982,.40),(1.957,.509),(1.921,.536),(1.87,.543),(.17,.543),(.12,.522),(.095,.47),(.089,0)]

for BOTTLE_X,color,kind in [(-.70,'#b3c9df','LOTION'),(.70,'#e1c6d0','WASH')]:
 mat=model.mat('Satin '+kind+' empty plastic',color,.30)
 roundpart(kind+' hollow cylinder',profile,mat,'Body',BOTTLE_X)
 roundpart(kind+' pump closure',[(2.02,0),(2.02,.22),(2.03,.25),(2.31,.25),(2.32,.24),(2.32,.20),(2.43,.20),(2.44,.18),(2.44,0)],pump,'Pump',BOTTLE_X)
 # Fine molded ribs remain part of the complete pump.
 for i in range(96):
  a=i*math.tau/96
  box(kind+' closure rib',(BOTTLE_X+.25*math.cos(a),.25*math.sin(a),2.17),(.006,.006,.25),pump,'Pump',.002)
 roundpart(kind+' tall actuator stem',[(2.42,0),(2.42,.108),(2.82,.108),(2.82,0)],pump,'Pump',BOTTLE_X)
 roundpart(kind+' flat circular actuator',[(2.80,0),(2.80,.23),(2.81,.255),(2.92,.255),(2.94,.23),(2.94,0)],pump,'Pump',BOTTLE_X)
 box(kind+' horizontal spout',(BOTTLE_X+.38,0,2.865),(.48,.125,.105),pump,'Pump',.025)
 roundpart(kind+' integrated socket',[(1.89,0),(1.89,.06),(2.04,.09),(2.04,0)],pump,'Pump',BOTTLE_X)
 dip_tube()
 printing_sheet(kind+' white wrap label',BOTTLE_X,1.11,.53,1.40,label,'Label',.004)
 ink=art('label-'+kind,'<g transform="translate(1000 0) rotate(90)" fill="#17191b" font-family="Helvetica Neue,Arial"><text x="60" y="140" font-size="68" font-weight="700">BODY</text><text x="60" y="215" font-size="68" font-weight="700">'+kind+'</text><path d="M40 300H540 M40 670H540" fill="none" stroke="#17191b" stroke-width="3" stroke-dasharray="14 8"/><text x="60" y="430" font-size="43">DAILY</text><text x="60" y="495" font-size="43">BODY CARE</text><text x="60" y="800" font-size="39">PACKAGING</text><text x="60" y="860" font-size="39">COLLECTION</text></g>')
 printing_sheet(kind+' rotated product lettering',BOTTLE_X,1.02,.48,1.425,ink,'NameInk',.008)
 printing_sheet(kind+' white liaose',BOTTLE_X,.52,.099,.37,logo,'LogoInk',.006)
for key,g in model.groups.items():
 pivot=Vector(PIVOTS[key]);g['partKey']=key
 for child in g.children:
  child.location-=pivot
  if key in ('Label','LogoInk','NameInk'):child.visible_shadow=False
 g.location=pivot
bpy.context.view_layer.update()
bounds={k:{'min':[min((o.matrix_world@v.co)[a] for o in g.children for v in o.data.vertices) for a in range(3)],'max':[max((o.matrix_world@v.co)[a] for o in g.children for v in o.data.vertices) for a in range(3)]} for k,g in model.groups.items()}
assert set(model.groups)==set(GROUPS)
assert .09<bounds['Pump']['min'][2]<.13
assert not any(w in ob.name.lower() for ob in bpy.data.objects for w in ['liquid','formula'])
bpy.ops.object.select_all(action='SELECT')
bpy.ops.export_scene.gltf(filepath=str(GLB),export_format='GLB',use_selection=True,export_yup=True,export_extras=True,export_animations=False)
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'poster-084-v1.blend'),compress=True)
(OUT/'model-info.json').write_text(json.dumps({'id':'poster-084','blenderVersion':bpy.app.version_string,'groups':list(model.groups),'bounds':bounds,'containsFormula':False,'illustrativeDimensions':True,'bodyDiameter':1.15,'bodyHeight':2,'heightWithPump':2.94,'suctionTubeBottom':.115,'suctionTubeParent':'Pump'},indent=2))
print('SOFT BODY DUO READY',GLB.stat().st_size)
