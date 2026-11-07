"""Reference-led empty plastic tube and disc-pump duo, built with local Blender."""
import json, math, shutil, struct, subprocess, sys, zlib
from pathlib import Path
import bpy, bmesh
from mathutils import Vector

OUT=Path(__file__).resolve().parent
BASE=OUT.parent
sys.path.insert(0,str(BASE))
from tail_model_helpers import Model, NODE
GLB=BASE.parents[1]/'packaging-assets/poster-082-v1.glb'
TUBE_X=-.83; BOTTLE_X=.75
GROUPS=('Body','Pump','TubeCap','Label','LogoInk','NameInk')
PIVOTS={'Body':(0,0,1.40),'Pump':(BOTTLE_X,0,2.34),'TubeCap':(TUBE_X,0,.20),
        'Label':(0,0,1.50),'LogoInk':(0,0,2.12),'NameInk':(0,0,1.13)}

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

def artwork():
 # Reuse the approved bold identity from the preceding Soap Clean pack.
 for name in ['logo','soap-clean-soap']:
  shutil.copyfile(BASE/'poster-080'/f'{name}.svg',OUT/f'{name}.svg')
  shutil.copyfile(BASE/'poster-080'/f'{name}.png',OUT/f'{name}.png')
 for kind,words,capacity in [('tube','HAIR TREATMENT','180 ml'),('bottle','SHAMPOO','300 ml')]:
  source=OUT/f'spec-{kind}.svg'
  source.write_text('<svg xmlns="http://www.w3.org/2000/svg" width="1280" height="440" viewBox="0 0 1280 440">'
   '<g fill="#14120f" font-family="Helvetica Neue,Arial,sans-serif" font-weight="500" text-anchor="middle">'
   f'<text x="640" y="165" font-size="138">{words}</text><text x="640" y="375" font-size="142">{capacity}</text></g></svg>')
  subprocess.run([NODE,'--input-type=module','-e',"import sharp from '/Users/icecream/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/sharp/dist/index.mjs';await sharp(process.argv[1]).png().toFile(process.argv[2]);",str(source),str(source.with_suffix('.png'))],check=True)
 # Tiny embedded RGBA swatches make the existing viewer classify these as ink
 # surfaces, hence avoid opaque shadow-map rectangles from transparent carriers.
 def swatch(name,rgba):
  def chunk(t,b):return struct.pack('>I',len(b))+t+b+struct.pack('>I',zlib.crc32(t+b)&0xffffffff)
  raw=(b'\0'+bytes(rgba)*4)*4
  (OUT/name).write_bytes(b'\x89PNG\r\n\x1a\n'+chunk(b'IHDR',struct.pack('>IIBBBBB',4,4,8,6,0,0,0))+chunk(b'IDAT',zlib.compress(raw))+chunk(b'IEND',b''))
 swatch('carrier.png',(255,255,255,5));swatch('stripe.png',(145,191,213,255))

# Slowly changing elliptical cross-sections keep the front inflated, the tail flat.
TUBE_PROFILE=[(.39,.370,.273,2),(.42,.390,.289,2),(.48,.405,.300,2),(.65,.421,.304,2),
 (1.00,.451,.290,2),(1.40,.493,.252,2),(1.80,.541,.211,2),(2.20,.592,.159,2),
 (2.55,.639,.109,2),(2.82,.676,.062,2),(2.98,.696,.025,2),(3.015,.700,.020,2)]
def tube_radius(z):
 for a,b in zip(TUBE_PROFILE,TUBE_PROFILE[1:]):
  if a[0]<=z<=b[0]:
   t=(z-a[0])/(b[0]-a[0]);return a[1]*(1-t)+b[1]*t,a[2]*(1-t)+b[2]*t
 return TUBE_PROFILE[-1][1:3] if z>TUBE_PROFILE[-1][0] else TUBE_PROFILE[0][1:3]
def tube_front(x,z):
 rx,ry=tube_radius(z);return -ry*math.sqrt(max(0,1-(x/rx)**2))
def bottle_front(x,z):return -math.sqrt(max(0,.575**2-x*x))

def printing_sheet(name,cx,w,h,z,surf,mat,parent,offset=.003,nx=64,ny=20):
 ob=model.sheet(name,w,h,z,surf,mat,parent,nx,ny,offset)
 for v in ob.data.vertices:v.co.x+=cx
 return ob

def stripes():
 # Strip geometry follows the flexible tube. Gaps are intentional clear ink zones.
 vs=[];fs=[]
 zones=[(2.61,2.80,.285),(1.43,1.97,.365),(.545,.815,.35)]
 for side in [-1,1]:
  for fraction in [.105,.315,.525,.735,.915]:
   n=240
   for j in range(n):
    za=.465+(2.98-.465)*j/n;zb=.465+(2.98-.465)*(j+1)/n
    rx,_=tube_radius((za+zb)/2);x=side*fraction*rx
    if any(lo<((za+zb)/2)<hi and abs(x)<half for lo,hi,half in zones):continue
    ids=[]
    for z,sgn in [(za,-1),(za,1),(zb,1),(zb,-1)]:
     rx,_=tube_radius(z);xx=side*fraction*rx+sgn*.0048
     ids.append(len(vs));vs.append((TUBE_X+xx,tube_front(xx,z)-.0022,z))
    fs.append(tuple(ids))
 ob=model.mesh('Pale blue pinstripes | direct printing, no paper',vs,fs,stripe,'Label')
 return ob

def crimp():
 # One integrated heat seal: elongated flat bar with many small vertical embossments.
 vs=[];fs=[]
 n=180
 for row,z in enumerate([2.987,3.002,3.094,3.105]):
  for back in [False,True]:
   for i in range(n+1):
    x=-.7+1.4*i/n;wave=.0016*(.5+.5*math.cos(i*math.tau/2))
    y=(.021+wave)*(1 if back else -1)
    vs.append((TUBE_X+x,y,z))
 stride=2*(n+1)
 for row in range(3):
  for back in [0,1]:
   start=row*stride+back*(n+1)
   for i in range(n):a=start+i;fs.append((a,a+1,a+stride+1,a+stride))
 for row in range(3):
  for i in [0,n]:a=row*stride+i;b=a+n+1;fs.append((a,b,b+stride,a+stride))
 for row in [0,3]:
  for i in range(n):a=row*stride+i;b=a+n+1;fs.append((a,a+1,b+1,b))
 ob=model.mesh('Flattened heat-seal tail | 90 fine crimp ridges',vs,fs,ivory,'Body');fix(ob)

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

bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.context.preferences.filepaths.save_version=0
artwork();model=Duo()
ivory=model.mat('Ivory opaque soft plastic','#f2eee2',.30)
blue=model.mat('Powder blue molded plastic','#a9cfdf',.28)
stripe=model.texture('Powder blue pinstripe ink','stripe.png',.60)
clear_tube=model.mat('Transparent hollow polyethylene suction tube','#d9e9ed',.08)
bsdf=clear_tube.node_tree.nodes.get('Principled BSDF')
bsdf.inputs['Alpha'].default_value=.32;bsdf.inputs['Specular IOR Level'].default_value=.70
bsdf.inputs['Coat Weight'].default_value=.22;bsdf.inputs['Coat Roughness'].default_value=.08
clear_tube.surface_render_method='DITHERED';clear_tube.use_backface_culling=True
carrier=model.texture('Transparent direct-print carrier | conceptual ink layer','carrier.png',.42)
# Sealed, empty flexible tube with an open dispensing neck at the bottom.
outer=[(.27,.124,.124,2),(.286,.128,.128,2),(.31,.128,.128,2),(.33,.143,.143,2),(.353,.143,.143,2),(.367,.128,.128,2),(.39,.192,.160,2)]+TUBE_PROFILE
inner=[(z,rx-.013,max(.006,ry-.013),p) for z,rx,ry,p in reversed(TUBE_PROFILE[:-1])]
rows=outer+[(3.015,.688,.006,2)]+inner+[(.39,.178,.146,2),(.365,.107,.107,2),(.27,.101,.101,2),outer[0]]
rings('Empty flexible tube | flat sealed tail and open nozzle',rows,ivory,'Body',TUBE_X)
crimp()
# Hollow cylindrical bottle with broad low shoulder and a visible open neck.
profile=[(0,0),(0,.44),(.007,.49),(.022,.535),(.05,.561),(.09,.572),(.14,.575),(1.88,.575),(1.93,.571),(1.965,.552),(1.986,.514),(1.998,.40),(2.006,.26),(2.012,.18),(2.035,.166),(2.060,.166),(2.066,.176),(2.083,.176),(2.089,.166),(2.127,.166),(2.134,.171),(2.149,.171),(2.155,.164),(2.155,.136),(2.023,.136),(1.993,.18),(1.982,.40),(1.957,.509),(1.921,.536),(1.87,.543),(.17,.543),(.12,.522),(.095,.47),(.089,0)]
roundpart('Empty ivory cylinder | low shoulder and hollow neck',profile,ivory,'Body',BOTTLE_X)
# Flip top base cap stays one customer-facing assembly.
rings('Blue flip-top cap | lower hinged lid',[(0,0,0,2),(0,.31,.23,2),(.008,.373,.28,2),(.025,.394,.296,2),(.045,.400,.300,2),(.135,.400,.300,2),(.148,.398,.299,2),(.151,0,0,2)],blue,'TubeCap',TUBE_X)
upper=rings('Blue flip-top cap | complete closure sleeve',[(.155,0,0,2),(.155,.396,.297,2),(.168,.400,.300,2),(.365,.400,.300,2),(.399,.394,.295,2),(.413,.377,.281,2),(.416,.18,.15,2),(.410,.154,.144,2),(.285,.154,.144,2),(.285,0,0,2)],blue,'TubeCap',TUBE_X)
# Real shallow finger recess cut into the closure above the flip seam.
bpy.ops.mesh.primitive_uv_sphere_add(segments=48,ring_count=24,location=(TUBE_X,-.312,.166))
cutter=bpy.context.object;cutter.name='temporary thumb recess cutter';cutter.scale=(.135,.055,.092)
bpy.ops.object.transform_apply(location=False,rotation=False,scale=True)
bpy.context.view_layer.objects.active=upper;mod=upper.modifiers.new('Shallow front thumb recess','BOOLEAN');mod.operation='DIFFERENCE';mod.object=cutter
bpy.ops.object.modifier_apply(modifier=mod.name);bpy.data.objects.remove(cutter,do_unlink=True)
box('Blue flip-top rear hinge',(TUBE_X,.294,.156),(.12,.036,.067),blue,'TubeCap',.012)
# Single assembled pump: low collar, exposed stem, flat disc and small rear lip.
roundpart('Disc pump | rounded closure barrel',[(1.992,0),(1.992,.19),(2.000,.230),(2.013,.240),(2.315,.240),(2.333,.231),(2.340,.194),(2.340,0)],blue,'Pump',BOTTLE_X)
roundpart('Disc pump | assembled actuator neck',[(2.317,0),(2.317,.191),(2.340,.199),(2.365,.199),(2.375,.180),(2.515,.180),(2.527,.195),(2.540,.195),(2.540,0)],blue,'Pump',BOTTLE_X)
roundpart('Disc pump | wide flat circular pressing surface',[(2.521,0),(2.521,.270),(2.526,.292),(2.539,.302),(2.612,.302),(2.622,.295),(2.628,.270),(2.628,0)],blue,'Pump',BOTTLE_X)
box('Disc pump | low rear-edge dispensing lip',(BOTTLE_X,.248,2.639),(.119,.128,.031),blue,'Pump',.010)
roundpart('Disc pump | internal socket, stays with head',[(1.865,0),(1.865,.054),(1.890,.065),(1.940,.065),(1.96,.105),(2.04,.105),(2.04,0)],blue,'Pump',BOTTLE_X)
dip_tube()
# Printing follows curved package walls with only minimal skin clearance.
logo=model.texture('Bold black liaose ink','logo.png',.68)
name=model.texture('Bold stacked SOAP CLEAN SOAP ink','soap-clean-soap.png',.68)
spec_tube=model.texture('Hair treatment 180 ml ink','spec-tube.png',.68)
spec_bottle=model.texture('Shampoo 300 ml ink','spec-bottle.png',.68)
for mat in [logo,name,spec_tube,spec_bottle]:mat.use_backface_culling=True
stripes()
printing_sheet('Tube transparent print carrier',TUBE_X,.77,2.43,.46,tube_front,carrier,'Label',.001,64,100)
printing_sheet('Bottle transparent print carrier',BOTTLE_X,.80,1.60,.22,bottle_front,carrier,'Label',.001,64,48)
printing_sheet('Tube bold liaose',TUBE_X,.50,.146,2.635,tube_front,logo,'LogoInk',.004)
printing_sheet('Bottle bold liaose',BOTTLE_X,.45,.131,1.655,bottle_front,logo,'LogoInk',.004)
printing_sheet('Tube SOAP CLEAN SOAP',TUBE_X,.665,.471,1.45,tube_front,name,'NameInk',.004)
printing_sheet('Bottle SOAP CLEAN SOAP',BOTTLE_X,.715,.507,.81,bottle_front,name,'NameInk',.004)
printing_sheet('Tube HAIR TREATMENT 180 ml',TUBE_X,.625,.215,.56,tube_front,spec_tube,'NameInk',.004)
printing_sheet('Bottle SHAMPOO 300 ml',BOTTLE_X,.520,.179,.25,bottle_front,spec_bottle,'NameInk',.004)

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
config=json.loads((OUT/'review-product.json').read_text())
detail_en=['An empty flexible tube beside an opaque cylindrical bottle.','The disc actuator, closure and long clear hollow dip tube lift as one assembly.','The powder-blue flip-top closure separates as one complete component.','Blue pinstripes and transparent print surfaces separate; there is no paper label.','Both bold wordmarks lift farther forward than the print carrier.','The product names, uses and capacities form the outermost lettering layer.']
for p,d in zip(config['parts'],detail_en):p['detail'][1]=d
(OUT/'review-product.json').write_text(json.dumps(config,ensure_ascii=False,indent=2)+'\n')
node_to_key={p['node']:p['key'] for p in config['parts']}
for node,g in model.groups.items():
 key=node_to_key[node];x,y,z=config['review']['explosion']['offsets'][key];scale=config['review']['explosion']['scales'].get(key,1);start=g.location.copy()
 for frame,t in [(1,0),(31,.5),(61,1)]:
  g.location=start+Vector((x,-z,y))*t;g.scale=(1+(scale-1)*t,)*3
  g.keyframe_insert(data_path='location',frame=frame);g.keyframe_insert(data_path='scale',frame=frame)
scene=bpy.context.scene;scene.name='Soap Clean Duo | reference proportions';scene.frame_end=61;scene.frame_set(1)
for screen in bpy.data.screens:
 for area in screen.areas:
  if area.type=='VIEW_3D':
   s=area.spaces.active;s.region_3d.view_location=(0,0,1.55);s.region_3d.view_distance=5.5;s.region_3d.view_rotation=Vector((0,-1,.08)).to_track_quat('Z','Y');s.region_3d.view_perspective='ORTHO';s.overlay.show_overlays=False;s.shading.type='MATERIAL'
bpy.ops.object.select_all(action='DESELECT');bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'poster-082-v1.blend'),compress=True)
info={'id':'poster-082','name':'Soap Clean Duo','file':GLB.name,'source':'build_soap_duo.py','blenderVersion':bpy.app.version_string,'components':list(model.groups),'componentBoundsBlenderXYZ':bounds,'containsFormula':False,'illustrativeDimensions':True,'materials':'opaque ivory and pale-blue plastic; transparent hollow polyethylene suction tube','tubeHeight':3.105,'bottleWithPumpHeight':2.6545,'bottleBodyDiameter':1.15,'tubeTailWidth':1.40,'tubeCapWidth':.80,'centerSpacing':1.58,'capacitiesMl':{'tube':180,'bottle':300},'suctionTube':{'outerDiameter':.082,'innerDiameter':.058,'topZ':1.985,'tipCenterZ':.115,'containerInnerFloorZ':.089,'parent':'Pump'},'separateLabelAndPrint':True,'paperLabel':False,'flatDiscPump':True,'rearLipHeight':.031}
(OUT/'model-info.json').write_text(json.dumps(info,ensure_ascii=False,indent=2)+'\n')
print('SOAP DUO READY',GLB.stat().st_size,'bytes')
