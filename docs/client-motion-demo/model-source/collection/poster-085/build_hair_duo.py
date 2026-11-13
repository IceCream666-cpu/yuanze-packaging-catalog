"""Daily Hair Ritual empty pump bottle and tube, calibrated to the approved poster.
Geometry reuses the existing soap-duo mesh primitives, with product-specific profiles.
"""
import json, math, sys, subprocess, xml.etree.ElementTree as ET
from pathlib import Path
import bpy,bmesh
from mathutils import Vector
OUT=Path(__file__).resolve().parent
BASE=OUT.parent
sys.path.insert(0,str(BASE))
from tail_model_helpers import Model,NODE
GLB=BASE.parents[1]/'packaging-assets/poster-085-v1.glb'
TUBE_X=-.72;BOTTLE_X=.64
GROUPS=('Body','Pump','TubeCap','Label','LogoInk','NameInk')
PIVOTS={'Body':(0,0,1.4),'Pump':(BOTTLE_X,0,2.9),'TubeCap':(TUBE_X,0,.17),'Label':(0,0,1.4),'LogoInk':(0,0,1.85),'NameInk':(0,0,1.0)}
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

def printing_sheet(name,cx,w,h,z,surf,mat,parent,offset=.003,nx=64,ny=20):
 ob=model.sheet(name,w,h,z,surf,mat,parent,nx,ny,offset)
 for v in ob.data.vertices:v.co.x+=cx
 return ob

def dip_tube():
 vs=[];fs=[];outer=[];inner=[];n=48;m=48
 for i in range(n+1):
  t=i/n;z=2.61-(2.61-.135)*t;dx=.145*t**2
  for radius,rows in [(.041,outer),(.029,inner)]:
   rows.append(list(range(len(vs),len(vs)+m)))
   for j in range(m):
    a=j*math.tau/m;vs.append((BOTTLE_X+dx+radius*math.cos(a),radius*math.sin(a),z+(.45*radius*math.cos(a) if i==n else 0)))
 for i in range(n):
  for j in range(m):k=(j+1)%m;fs.extend([(outer[i][j],outer[i][k],outer[i+1][k],outer[i+1][j]),(inner[i][k],inner[i][j],inner[i+1][j],inner[i+1][k])])
 for j in range(m):
  k=(j+1)%m;fs.extend([(outer[0][k],outer[0][j],inner[0][j],inner[0][k]),(outer[-1][j],outer[-1][k],inner[-1][k],inner[-1][j])])
 ob=model.mesh('Long clear hollow dip tube | near-bottom angled intake',vs,fs,clear_tube,'Pump');fix(ob)

def artwork():
 path=next(e.attrib['d'] for e in ET.parse(BASE/'poster-073/print.svg').getroot().iter() if e.tag.endswith('path'))
 files={'logo':f'<svg xmlns="http://www.w3.org/2000/svg" width="1360" height="500" viewBox="0 0 340 125"><path d="{path}" fill="#fff9ef"/></svg>',
 'shampoo':'<svg xmlns="http://www.w3.org/2000/svg" width="1400" height="220"><text x="700" y="150" text-anchor="middle" font-family="Helvetica Neue,Arial" font-size="112" letter-spacing="25" fill="#fff9ef">SHAMPOO</text></svg>',
 'treatment':'<svg xmlns="http://www.w3.org/2000/svg" width="900" height="450"><g fill="#fff9ef" text-anchor="middle" font-family="Helvetica Neue,Arial" font-size="98" letter-spacing="21"><text x="450" y="170">HAIR</text><text x="450" y="340">TREATMENT</text></g></svg>'}
 for name,svg in files.items():
  p=OUT/(name+'.svg');p.write_text(svg)
  subprocess.run([NODE,'--input-type=module','-e',"import sharp from '/Users/icecream/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/sharp/dist/index.mjs';await sharp(process.argv[1]).png().toFile(process.argv[2]);",str(p),str(p.with_suffix('.png'))],check=True)

TUBE_PROFILE=[(.29,.245,.173),(.33,.25,.18),(.40,.256,.186),(.55,.272,.19),(.85,.293,.181),(1.2,.315,.157),(1.55,.341,.122),(1.9,.366,.077),(2.17,.38,.025),(2.21,.38,.018)]
def tube_radius(z):
 for a,b in zip(TUBE_PROFILE,TUBE_PROFILE[1:]):
  if a[0]<=z<=b[0]:
   t=(z-a[0])/(b[0]-a[0]);return a[1]*(1-t)+b[1]*t,a[2]*(1-t)+b[2]*t
 return TUBE_PROFILE[0][1:] if z<TUBE_PROFILE[0][0] else TUBE_PROFILE[-1][1:]
def tube_front(x,z):
 rx,ry=tube_radius(z);return -ry*math.sqrt(max(0,1-(x/rx)**2))
def bottle_front(x,z):return -math.sqrt(max(0,.512**2-x*x))

def wrap(name,cx,low,high,surface,material,parent,rxry,angle=math.pi):
 vs=[];fs=[];nx=160;ny=64
 for j in range(ny+1):
  z=low+(high-low)*j/ny;rx,ry=rxry(z)
  for i in range(nx+1):
   a=-angle+2*angle*i/nx;vs.append((cx+(rx+.002)*math.sin(a),-(ry+.002)*math.cos(a),z))
 for j in range(ny):
  for i in range(nx):
   a=j*(nx+1)+i;fs.append((a,a+1,a+nx+2,a+nx+1))
 ob=model.mesh(name,vs,fs,material,parent)
 # Double-sided cosmetic film; a surface rather than an invented paper thickness.
 material.use_backface_culling=False
 return ob

bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.context.preferences.filepaths.save_version=0
artwork();model=Duo()
ivory=model.mat('Warm ivory satin molded polymer','#eee4d5',.28)
bronze=model.mat('Satin copper bronze decorative finish','#a77650',.30,metal=.65)
rose=model.mat('Muted rose bronze tube decoration','#a47b67',.42,metal=.15)
clear_tube=model.mat('Transparent hollow polyethylene suction tube','#e5e7e5',.07)
p=clear_tube.node_tree.nodes.get('Principled BSDF');p.inputs['Alpha'].default_value=.36;p.inputs['Coat Weight'].default_value=.25
clear_tube.surface_render_method='DITHERED';clear_tube.use_backface_culling=True
# A hollow container; the bronze decorative wrap moves separately during inspection.
profile=[(0,0),(0,.30),(.008,.37),(.04,.43),(.10,.47),(.18,.497),(.25,.508),(.65,.508),(.68,.510),(2.54,.510),(2.59,.503),(2.62,.48),(2.64,.42),(2.65,.23),(2.67,.17),(2.74,.17),(2.75,.181),(2.77,.181),(2.78,.17),(2.79,.14),(2.67,.14),(2.62,.23),(2.61,.41),(2.57,.47),(.28,.475),(.19,.455),(.12,.39),(.10,0)]
roundpart('Empty tall cylinder | ivory rounded heel and hollow threaded neck',profile,ivory,'Body',BOTTLE_X)
# Tube is narrower and 69 percent of the pump bottle height, matching the poster.
outer=[(.18,.092,.092,2),(.25,.096,.096,2),(.27,.125,.116,2)]+[(z,x,y,2) for z,x,y in TUBE_PROFILE]
inner=[(z,x-.012,max(.005,y-.012),2) for z,x,y in reversed(TUBE_PROFILE[:-1])]
rings('Empty flexible tube | sealed tail and open dispensing nozzle',outer+[(2.21,.368,.005,2)]+inner+[(.27,.105,.095,2),(.25,.076,.076,2),(.18,.076,.076,2),outer[0]],ivory,'Body',TUBE_X)
box('Tube integrated flattened heat seal',(TUBE_X,0,2.245),(.765,.041,.07),ivory,'Body',.006)
for i in range(72):
 x=TUBE_X-.37+i*.74/71
 box(f'Tube seal ridge {i:02}',(x,-.022,2.244),(.003,.003,.047),ivory,'Body',.001)
# Ivory flip-top closure is one assembly; narrow seam and a shallow thumb notch.
rings('Tube cap | lower hinged lid',[(0,0,0,2),(0,.205,.151,2),(.015,.242,.175,2),(.035,.25,.18,2),(.11,.25,.18,2),(.116,0,0,2)],ivory,'TubeCap',TUBE_X)
upper=rings('Tube cap | closure sleeve',[(.120,0,0,2),(.12,.249,.179,2),(.15,.25,.18,2),(.29,.25,.18,2),(.31,.24,.17,2),(.315,.12,.11,2),(.29,.11,.10,2),(.19,.11,.10,2),(.19,0,0,2)],ivory,'TubeCap',TUBE_X)
bpy.ops.mesh.primitive_uv_sphere_add(segments=48,ring_count=24,location=(TUBE_X,-.186,.126));cut=bpy.context.object;cut.scale=(.105,.029,.068)
bpy.ops.object.transform_apply(location=False,rotation=False,scale=True);bpy.context.view_layer.objects.active=upper
mod=upper.modifiers.new('Shallow thumb recess','BOOLEAN');mod.operation='DIFFERENCE';mod.object=cut;bpy.ops.object.modifier_apply(modifier=mod.name);bpy.data.objects.remove(cut,do_unlink=True)
box('Tube cap | rear hinge',(TUBE_X,.178,.12),(.09,.023,.047),ivory,'TubeCap',.007)
# The broad shoulder collar belongs to the complete pump assembly.
roundpart('Pump | broad ivory shoulder collar',[(2.615,0),(2.615,.48),(2.625,.514),(2.64,.522),(2.75,.522),(2.77,.51),(2.78,.27),(2.78,0)],ivory,'Pump',BOTTLE_X)
roundpart('Pump | actuator barrel and stem',[(2.76,0),(2.76,.25),(2.79,.26),(3.04,.26),(3.06,.24),(3.07,.15),(3.14,.15),(3.16,.19),(3.18,.19),(3.18,0)],ivory,'Pump',BOTTLE_X)
# Loft a rounded broad beak, with its outlet underneath the left tip.
vs=[];fs=[];n=64
spout=[(-.68,3.244,.023,.018),(-.64,3.252,.085,.026),(-.52,3.264,.145,.032),(-.29,3.271,.205,.042),(-.04,3.259,.251,.070),(.19,3.249,.245,.074),(.31,3.245,.188,.061),(.36,3.245,.075,.035)]
for x,z,ry,rz in spout:
 for i in range(n):
  a=math.tau*i/n;vs.append((BOTTLE_X+x,ry*math.sin(a),z+rz*math.cos(a)))
for j in range(len(spout)-1):
 for i in range(n):a=j*n+i;k=j*n+(i+1)%n;fs.append((a,k,k+n,a+n))
fs.extend([tuple(range(n-1,-1,-1)),tuple((len(spout)-1)*n+i for i in range(n))])
sp=model.mesh('Pump | wide flattened beak actuator',vs,fs,ivory,'Pump');fix(sp)
nozzle=model.mat('Recessed pump outlet interior','#675d50',.65)
box('Pump | recessed dispensing outlet',(BOTTLE_X-.642,-.002,3.228),(.037,.065,.006),nozzle,'Pump',.005)
roundpart('Pump | internal connector',[(2.53,0),(2.53,.055),(2.58,.065),(2.64,.065),(2.67,.11),(2.72,.11),(2.72,0)],ivory,'Pump',BOTTLE_X)
dip_tube()
wrap('Bottle copper bronze decorative wrap',BOTTLE_X,.69,2.61,bottle_front,bronze,'Label',lambda z:(.510,.510))
wrap('Tube rose bronze decorative wrap',TUBE_X,.50,1.87,tube_front,rose,'Label',tube_radius)
logo=model.texture('White script liaose ink','logo.png',.65)
shampoo=model.texture('White SHAMPOO product lettering','shampoo.png',.65)
treatment=model.texture('White HAIR TREATMENT product lettering','treatment.png',.65)
for m in [logo,shampoo,treatment]:m.use_backface_culling=True
printing_sheet('Bottle liaose',BOTTLE_X,.66,.243,1.95,bottle_front,logo,'LogoInk',.006)
printing_sheet('Tube liaose',TUBE_X,.48,.176,1.46,tube_front,logo,'LogoInk',.006)
printing_sheet('Bottle SHAMPOO',BOTTLE_X,.64,.100,1.13,bottle_front,shampoo,'NameInk',.006)
printing_sheet('Tube HAIR TREATMENT',TUBE_X,.43,.215,.88,tube_front,treatment,'NameInk',.006)
for key,g in model.groups.items():
 pivot=Vector(PIVOTS[key]);g['partKey']=key
 for child in g.children:
  child.location-=pivot
  if key in ('Label','LogoInk','NameInk'):child.visible_shadow=False
 g.location=pivot
bpy.context.view_layer.update()
bounds={k:{'min':[min((o.matrix_world@v.co)[a] for o in g.children for v in o.data.vertices) for a in range(3)],'max':[max((o.matrix_world@v.co)[a] for o in g.children for v in o.data.vertices) for a in range(3)]} for k,g in model.groups.items()}
assert set(model.groups)==set(GROUPS)
assert .11<bounds['Pump']['min'][2]<.15
assert not any(w in ob.name.lower() for ob in bpy.data.objects for w in ['liquid','formula'])
bpy.ops.object.select_all(action='SELECT')
bpy.ops.export_scene.gltf(filepath=str(GLB),export_format='GLB',use_selection=True,export_yup=True,export_extras=True,export_animations=False)
cfg=json.loads((OUT/'review-product.json').read_text());mapping={p['node']:p['key'] for p in cfg['parts']}
for node,g in model.groups.items():
 key=mapping[node];x,y,z=cfg['review']['explosion']['offsets'][key];scale=cfg['review']['explosion']['scales'].get(key,1);start=g.location.copy()
 for frame,t in [(1,0),(31,.5),(61,1)]:
  g.location=start+Vector((x,-z,y))*t;g.scale=(1+(scale-1)*t,)*3
  g.keyframe_insert(data_path='location',frame=frame);g.keyframe_insert(data_path='scale',frame=frame)
scene=bpy.context.scene;scene.name='Daily Hair Ritual | reference proportions';scene.frame_end=61;scene.frame_set(1)
for screen in bpy.data.screens:
 for area in screen.areas:
  if area.type=='VIEW_3D':
   s=area.spaces.active;s.region_3d.view_location=(0,0,1.65);s.region_3d.view_distance=5.8;s.region_3d.view_rotation=Vector((0,-1,.04)).to_track_quat('Z','Y');s.region_3d.view_perspective='ORTHO';s.overlay.show_overlays=False;s.shading.type='MATERIAL'
bpy.ops.object.select_all(action='DESELECT');bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'poster-085-v1.blend'),compress=True)
info={'id':'poster-085','name':'Daily Hair Ritual','file':GLB.name,'source':'build_hair_duo.py','blenderVersion':bpy.app.version_string,'components':list(model.groups),'componentBoundsBlenderXYZ':bounds,'containsFormula':False,'illustrativeDimensions':True,'materials':'Ivory molded containers, satin bronze and rose decorative surfaces, white lettering, clear hollow dip tube','tubeHeight':2.28,'bottleWithPumpHeight':3.33,'bottleBodyDiameter':1.02,'tubeTailWidth':.765,'tubeCapWidth':.50,'centerSpacing':1.36,'suctionTube':{'outerDiameter':.082,'innerDiameter':.058,'topZ':2.61,'tipCenterZ':.135,'containerInnerFloorZ':.10,'parent':'Pump'},'separateLabelAndPrint':True,'paperLabel':False,'note':'Decorative surfaces separated for presentation; construction is illustrative, not manufacturing CAD.'}
(OUT/'model-info.json').write_text(json.dumps(info,indent=2)+'\n');print('HAIR DUO READY',GLB.stat().st_size,'bytes')
