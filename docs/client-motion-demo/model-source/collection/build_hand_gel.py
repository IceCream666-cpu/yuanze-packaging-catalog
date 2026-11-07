"""Reference-led poster-081: clear empty glass, woven sleeve and one complete dispenser."""
import json, math, struct, subprocess, sys, xml.etree.ElementTree as ET, zlib
from pathlib import Path
import bpy, bmesh
import numpy as np
from mathutils import Vector
BASE=Path(__file__).resolve().parent
sys.path.insert(0,str(BASE))
from tail_model_helpers import Model, NODE, part
OUT=BASE/'poster-081'; OUT.mkdir(exist_ok=True)
GLB=BASE.parents[1]/'packaging-assets/poster-081-v1.glb'
POSE={'Body':((0,0,0),1),'Pump':((0,2.30,0),1),'Label':((-1.20,.02,.72),1.03),
      'LogoInk':((-2.45,.24,1.62),1.18),'NameInk':((-2.45,-.08,2.04),1.18)}
PIVOTS={'Body':1.02,'Pump':2.23,'Label':1.21,'LogoInk':1.46,'NameInk':1.05}
class HandGel(Model):
 def __init__(self): self.out=OUT;self.groups={}

def png(path,a):
 h,w,c=a.shape
 def chunk(t,b):return struct.pack('>I',len(b))+t+b+struct.pack('>I',zlib.crc32(t+b)&0xffffffff)
 raw=b''.join(b'\0'+row.tobytes() for row in a)
 path.write_bytes(b'\x89PNG\r\n\x1a\n'+chunk(b'IHDR',struct.pack('>IIBBBBB',w,h,8,2 if c==3 else 6,0,0,0))+chunk(b'IDAT',zlib.compress(raw,8))+chunk(b'IEND',b''))

def artwork():
 logo=next(e.attrib['d'] for e in ET.parse(BASE/'poster-060/print.svg').getroot().iter() if e.tag.endswith('path'))
 sheets={'logo':f'<svg xmlns="http://www.w3.org/2000/svg" width="1360" height="500" viewBox="0 0 340 125"><path d="{logo}" fill="#171812"/></svg>',
 'tag-logo':f'<svg xmlns="http://www.w3.org/2000/svg" width="256" height="896" viewBox="0 0 80 280"><g transform="translate(68 24) rotate(90) scale(.65 .42)"><path d="{logo}" fill="#f0e5ce"/></g></svg>',
 'name':'<svg xmlns="http://www.w3.org/2000/svg" width="1440" height="430" viewBox="0 0 1440 430"><g fill="#171812" text-anchor="middle" font-family="Times New Roman,serif" font-weight="700"><text x="720" y="175" font-size="175" letter-spacing="2">EXFOLIATING</text><text x="720" y="365" font-size="175" letter-spacing="5">HAND GEL</text></g></svg>'}
 for k,s in sheets.items():
  (OUT/f'{k}.svg').write_text(s)
  subprocess.run([NODE,'--input-type=module','-e',"import sharp from '/Users/icecream/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/sharp/dist/index.mjs';await sharp(process.argv[1]).png().toFile(process.argv[2]);",str(OUT/f'{k}.svg'),str(OUT/f'{k}.png')],check=True)
 # Alternating over-under yarns, rather than random paper grain.
 h,w=512,2048;y,x=np.mgrid[0:h,0:w];u=x/6.4;v=y/6.4
 cross=(np.floor(u).astype(int)+np.floor(v).astype(int))%2
 warp=np.sin(math.pi*(u%1))**.55;weft=np.sin(math.pi*(v%1))**.55
 height=np.where(cross==0,warp*.75+weft*.12,weft*.75+warp*.12)
 rng=np.random.default_rng(81);height+=rng.normal(0,.035,(h,w))
 value=np.clip(.84+.13*height,.80,.99)
 rgb=np.clip(value[...,None]*np.array([246,236,215]),0,255).astype('uint8');png(OUT/'linen-color.png',rgb)
 gy,gx=np.gradient(height);normal=np.dstack([-gx*.85,-gy*.85,np.ones((h,w))]);normal/=np.linalg.norm(normal,axis=2)[...,None]
 png(OUT/'linen-normal.png',np.clip((normal*.5+.5)*255,0,255).astype('uint8'))
 png(OUT/'black-linen.png',np.clip((.55+.45*height)[...,None]*np.array([22,24,20]),0,255).astype('uint8'))

def fix_mesh(ob):
 bm=bmesh.new();bm.from_mesh(ob.data);bmesh.ops.remove_doubles(bm,verts=list(bm.verts),dist=1e-7);bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));assert all(e.is_manifold for e in bm.edges),ob.name;assert bm.calc_volume(signed=True)>0,ob.name;bm.to_mesh(ob.data);bm.free()

def fluted_collar():
 profile=[(2.015,.273,0),(2.019,.293,.002),(2.031,.302,.0045),(2.047,.303,.0055),(2.394,.303,.0055),(2.414,.300,.0045),(2.430,.286,.001),(2.434,.18,0),(2.411,.18,0),(2.411,.268,0),(2.037,.268,0),(2.015,.273,0)]
 n=384;vs=[];fs=[]
 for z,r,amp in profile:
  for i in range(n):
   t=i*math.tau/n;rr=r+amp*math.cos(96*t);vs.append((rr*math.cos(t),rr*math.sin(t),z))
 for row in range(len(profile)-1):
  for i in range(n):j=(i+1)%n;a=row*n;fs.append((a+i,a+j,a+n+j,a+n+i))
 ob=model.mesh('96 fine grip flutes | rounded black closure',vs,fs,black,'Pump');fix_mesh(ob)

def pump_spout():
 # Arched, broad pressing lever narrowing to a visibly hollow dispensing mouth.
 rows=[(.18,.112,.016,2.862),(.14,.145,.025,2.870),(.05,.160,.029,2.871),(-.08,.164,.030,2.870),(-.20,.159,.030,2.873),(-.34,.148,.029,2.880),(-.49,.134,.029,2.884),(-.64,.120,.029,2.868),(-.76,.105,.028,2.840),(-.78,.102,.028,2.832),(-.782,.076,.015,2.832),(-.72,.076,.015,2.850),(-.65,.076,.015,2.866)]
 n=48;vs=[];fs=[]
 for x,ry,rz,z in rows:
  for i in range(n):
   t=i*math.tau/n;y=ry*math.copysign(abs(math.cos(t))**.55,math.cos(t));zz=rz*math.copysign(abs(math.sin(t))**.55,math.sin(t));vs.append((x,y,z+zz))
 for j in range(len(rows)-1):
  for i in range(n):k=(i+1)%n;a=j*n;fs.append((a+i,a+k,a+n+k,a+n+i))
 fs.extend([tuple(range(n-1,-1,-1)),tuple((len(rows)-1)*n+i for i in range(n))])
 ob=model.mesh('Arched lever with recessed open pump outlet',vs,fs,gloss,'Pump');fix_mesh(ob)

def dip_tube():
 n,m=48,32;vs=[];outer=[];inner=[]
 for i in range(n+1):
  t=i/n;z=2.21-(2.21-.185)*t;x=.18*t**2.1
  for radius,rings in [(.038,outer),(.027,inner)]:
   rings.append(list(range(len(vs),len(vs)+m)))
   for j in range(m):
    a=j*math.tau/m;vs.append((x+radius*math.cos(a),radius*math.sin(a),z+(.45*radius*math.cos(a) if i==n else 0)))
 fs=[]
 for i in range(n):
  for j in range(m):k=(j+1)%m;fs.extend([(outer[i][j],outer[i][k],outer[i+1][k],outer[i+1][j]),(inner[i][k],inner[i][j],inner[i+1][j],inner[i+1][k])])
 for j in range(m):
  k=(j+1)%m;fs.extend([(outer[0][k],outer[0][j],inner[0][j],inner[0][k]),(outer[-1][j],outer[-1][k],inner[-1][k],inner[-1][j])])
 ob=model.mesh('Long clear hollow dip tube | angled pickup',vs,fs,clear_tube,'Pump');fix_mesh(ob)

def sleeve():
 # Continuous outer and inner cloth wall; the rear joining seam stays attached.
 n=192;rows=[(.70,.788),(.704,.795),(1.714,.795),(1.72,.789),(1.714,.782),(.704,.782),(.70,.788)];vs=[];fs=[]
 for j,(z,r) in enumerate(rows):
  for i in range(n+1):
   a=i*math.tau/n;vs.append((r*math.sin(a),-r*math.cos(a),z+.002*math.sin(31*a)))
 for j in range(len(rows)-1):
  for i in range(n):a=j*(n+1)+i;fs.append((a,a+1,a+n+2,a+n+1))
 ob=model.mesh('Ivory woven wrap sleeve | soft rolled edges',vs,fs,linen,'Label');uv=ob.data.uv_layers.new()
 for f in ob.data.polygons:
  for li in f.loop_indices:
   idx=ob.data.loops[li].vertex_index;uv.data[li].uv=(idx%(n+1)/n,(vs[idx][2]-.70)/1.02)
 fix_mesh(ob)
 # Side flag is one folded fabric detail, not a loose exploded component.
 bpy.ops.mesh.primitive_cube_add(size=1,location=(.823,-.18,1.25));ob=bpy.context.object;ob.name='Black woven side flag';ob.scale=(.23,.027,.72);bpy.ops.object.transform_apply(location=False,rotation=False,scale=True)
 bevel=ob.modifiers.new('Soft textile corners','BEVEL');bevel.width=.012;bevel.segments=3;bpy.context.view_layer.objects.active=ob;bpy.ops.object.modifier_apply(modifier=bevel.name)
 ob.data.materials.append(black_linen);ob.parent=model.groups['Label']
 # Cube UVs are adequate for the tiny sewn weave, all material images are packed.
 return ob

bpy.ops.wm.read_factory_settings(use_empty=True);bpy.context.preferences.filepaths.save_version=0
artwork();model=HandGel()
glass=model.mat('Crystal clear glass | thick heel','#ffffff',.02,1);glass.node_tree.nodes.get('Principled BSDF').inputs['IOR'].default_value=1.46
clear_tube=model.mat('Transparent polyethylene dip tube','#edf4ef',.12,.83)
black=model.mat('Fine fluted black closure','#111411',.28)
gloss=model.mat('Gloss black assembled pump','#0b0d0a',.20)
linen=model.texture('Warm ivory woven label','linen-color.png',.92,'linen-normal.png')
black_linen=model.texture('Black woven side flag','black-linen.png',.88,'linen-normal.png')
model.lathe('Clear hollow cylinder | thick base and open neck',[(0,0),(0,.61),(.006,.69),(.02,.738),(.045,.768),(.08,.780),(.15,.782),(1.93,.782),(1.99,.778),(2.02,.763),(2.041,.72),(2.049,.38),(2.052,.245),(2.073,.226),(2.100,.226),(2.104,.235),(2.122,.235),(2.127,.223),(2.164,.223),(2.171,.227),(2.190,.227),(2.195,.217),(2.195,.173),(2.066,.173),(2.023,.206),(2.008,.39),(2.006,.70),(1.982,.732),(1.93,.737),(.25,.737),(.192,.721),(.165,.66),(.157,0)],glass,'Body',192)
fluted_collar()
model.lathe('Complete dispenser barrel and tube socket',[(1.96,0),(1.96,.055),(2.02,.066),(2.07,.11),(2.25,.11),(2.30,.154),(2.43,.154),(2.43,0)],black,'Pump',80)
model.lathe('Piston collar and actuator stem',[(2.41,0),(2.41,.185),(2.422,.190),(2.489,.190),(2.503,.17),(2.51,.145),(2.803,.145),(2.824,.138),(2.84,0)],gloss,'Pump',96)
pump_spout();dip_tube();sleeve()
front=lambda x,z:-math.sqrt(.795**2-x*x)
logo_mat=model.texture('Separate black liaose ink','logo.png',.70);logo_mat.use_backface_culling=True
name_mat=model.texture('Separate product name ink','name.png',.70);name_mat.use_backface_culling=True
tag_mat=model.texture('Ivory wordmark attached to black side flag','tag-logo.png',.72);tag_mat.use_backface_culling=True
model.sheet('liaose on woven sleeve',1.045,.350,1.327,front,logo_mat,'LogoInk',64,16,.004)
model.sheet('EXFOLIATING HAND GEL',.995,.285,.917,front,name_mat,'NameInk',64,12,.004)
tag=model.sheet('liaose on black side flag',.17,.59,.955,lambda x,z:-.196,tag_mat,'Label',2,4,.001)
for v in tag.data.vertices:v.co.x+=.823
# Set independent local pivots before exporting closed pose.
for key,group in model.groups.items():
 pivot=Vector((0,0,PIVOTS[key]));group['partKey']=key
 for child in group.children:child.location-=pivot
 group.location=pivot
for group in model.groups.values():
 for ob in group.children:
  if group.name in ('LogoInk','NameInk'):ob.visible_shadow=False
bpy.context.view_layer.update()
bounds={k:{'min':[min((o.matrix_world@v.co)[axis] for o in g.children for v in o.data.vertices) for axis in range(3)],'max':[max((o.matrix_world@v.co)[axis] for o in g.children for v in o.data.vertices) for axis in range(3)]} for k,g in model.groups.items()}
assert bounds['Pump']['min'][2]<.18 and bounds['Pump']['max'][2]>2.88
assert len(model.groups)==5
bpy.ops.object.select_all(action='SELECT');bpy.ops.export_scene.gltf(filepath=str(GLB),export_format='GLB',use_selection=True,export_yup=True,export_extras=True,export_animations=False)
for key,group in model.groups.items():
 start=group.location.copy();(x,y,z),scale=POSE[key]
 for frame,t in [(1,0),(31,.5),(61,1)]:
  group.location=start+Vector((x,-z,y))*t;group.scale=(1+(scale-1)*t,)*3;group.keyframe_insert(data_path='location',frame=frame);group.keyframe_insert(data_path='scale',frame=frame)
scene=bpy.context.scene;scene.name='Exfoliating Hand Gel';scene.frame_end=61;scene.frame_set(1)
for screen in bpy.data.screens:
 for area in screen.areas:
  if area.type=='VIEW_3D':
   s=area.spaces.active;s.region_3d.view_location=(0,0,1.45);s.region_3d.view_distance=5.4;s.region_3d.view_rotation=Vector((.18,-1,.15)).to_track_quat('Z','Y');s.region_3d.view_perspective='ORTHO';s.overlay.show_overlays=False;s.shading.type='MATERIAL'
bpy.ops.object.select_all(action='DESELECT');bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'poster-081-v1.blend'),compress=True)
info={'id':'poster-081','name':'Exfoliating Hand Gel','file':GLB.name,'source':'build_hand_gel.py','height':2.913,'width':1.564,'depth':1.564,'bodyHeight':2.05,'capacity':None,'containsFormula':False,'illustrativeDimensions':True,'components':list(model.groups),'attachedTube':True,'separateLabelAndPrint':True,'labelMaterial':'ivory woven textile with attached black side flag','bottleMaterial':'clear hollow glass, not frosted','componentBoundsBlenderXYZ':bounds,'blenderVersion':bpy.app.version_string}
(OUT/'model-info.json').write_text(json.dumps(info,ensure_ascii=False,indent=2)+'\n')
parts=[part('body','Body','通透玻璃瓶','Clear glass bottle','宽直壁、圆润肩沿和厚实玻璃底。空瓶展示。','Clear straight walls, a rounded rim and a thick base. Empty bottle.'),part('pump','Pump','完整泵头','Complete pump','细齿旋盖、按压头与粗透明长吸管作为整体抬起。','The fluted collar, actuator and long clear dip tube lift together.'),part('label','Label','织物环标与布标','Woven label and side flag','奶白织物环标与右侧黑布标及其白色字标作为整体展开。','The ivory woven sleeve, black side flag and its ivory wordmark move as one piece.'),part('logo','LogoInk','liaose 字标','liaose wordmark','正面 liaose 字标独立移到标贴前方；侧布标白字保留在黑布标上。','The front liaose wordmark lifts ahead of the label; the side wordmark stays on the black flag.'),part('print','NameInk','产品名','Product name','EXFOLIATING HAND GEL 展开到更外一层。','The product name separates into the outermost print layer.')]
config={'file':GLB.name,'kind':'collection','scale':1,'parts':parts,'review':{'appearance':{'glass':True,'frosted':False,'referenceGlass':True,'studio':{'background':'#e6e7dc','ink':'#243025'}},'explosion':{'mobilePrintSpread':.86,'offsets':{k.lower() if k not in ('LogoInk','NameInk') else ('logo' if k=='LogoInk' else 'print'):v[0] for k,v in POSE.items()},'scales':{'label':1.03,'logo':1.18,'print':1.18},'camera':{'centerX':[0,-.90],'centerY':[1.45,2.62],'width':[2.85,5.35],'height':[3.60,6.05]}}},'design':{'name':'Exfoliating Hand Gel','kind':{'zh':'手部护理 · 织物标玻璃泵瓶','en':'Hand care · Woven-label glass pump bottle'},'background':'#e6e7dc','ink':'#243025','swatch':['#3e481b','#e7dfcc']}}
(OUT/'review-product.json').write_text(json.dumps(config,ensure_ascii=False,indent=2)+'\n')
print('HAND GEL READY',GLB.stat().st_size,'bytes',json.dumps(bounds))
