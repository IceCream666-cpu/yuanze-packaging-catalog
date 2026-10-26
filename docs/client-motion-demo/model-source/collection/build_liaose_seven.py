"""Seven poster-derived empty packages. Hidden seals are illustrative, not tooling geometry."""
import sys,math,shutil,json
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
from tail_model_helpers import *
BASE=Path(__file__).resolve().parent
PID=sys.argv[-1]
assert PID in [f'poster-{n:03}' for n in range(72,79)]
out=BASE/PID;out.mkdir(exist_ok=True)
if not (out/'print.svg').exists():shutil.copyfile(BASE/'poster-069/print.svg',out/'print.svg')
m=Model(PID)

# Reuse seam vertices explicitly; avoid tolerance-dependent welding at thin cap rims.
def lathe(name,profile,material,parent,n=128):
 vs=[];rings=[];fs=[]
 for k,(z,r) in enumerate(profile):
  if k and (z,r)==profile[0]:rings.append(rings[0]);continue
  if r==0:rings.append([len(vs)]);vs.append((0,0,z))
  else:rings.append(list(range(len(vs),len(vs)+n)));vs.extend((r*math.cos(i*math.tau/n),r*math.sin(i*math.tau/n),z) for i in range(n))
 for a,b in zip(rings,rings[1:]):
  if len(a)==len(b)==1:continue
  for i in range(n):
   j=(i+1)%n;fs.append((a[0],b[j],b[i]) if len(a)==1 else (a[i],a[j],b[0]) if len(b)==1 else (a[i],a[j],b[j],b[i]))
 o=m.mesh(name,vs,fs,material,parent);bm=bmesh.new();bm.from_mesh(o.data);bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));assert all(e.is_manifold for e in bm.edges),name;assert bm.calc_volume(signed=True)>0,name;bm.to_mesh(o.data);bm.free();return o
m.lathe=lathe
clear=m.mat('Neutral empty glass','#ffffff',.035,1)
frost=m.mat('Frosted empty glass','#f6f6ee',.26,1)
white=m.mat('Ivory molded closure','#f2eee4',.28)
yellow=m.mat('Butter yellow pump','#f2e4a0',.3)
silver=m.mat('Pearl silver casing','#e5e6e2',.27,0,.8)
black=m.mat('Gloss black roller seat','#101210',.17)
metal=m.mat('Polished stainless roller ball','#e6e6e6',.08,0,1)
parts=[];pivots={};offsets={};total=0

def add(key,node,zh,en,z,move=None):
 parts.append(part(key,node,zh,en,zh+'独立展示。',en+' shown as a separate component.'));pivots[node]=z
 if move:offsets[key]=move

def cylinder(name,z,h,r,mat,node,wall=.035):
 return m.lathe(name,[(z,r-wall),(z,r),(z+h,r),(z+h,0),(z+h-wall,0),(z+h-wall,r-wall),(z,r-wall)],mat,node,128)

def hollow(name,profile,mat,node='Body',wall=.035):
 inner=[(z,max(.02,r-wall)) for z,r in reversed(profile) if z>.11]+[(.11,0)]
 return m.lathe(name,[(0,0)]+profile+inner,mat,node,128)

def stem(z,h,r,mat=white):
 m.lathe('Visible connection stem',[(z,0),(z,r),(z+h,r),(z+h,0)],mat,'PumpStem',64)
 add('stem','PumpStem','连接杆','Stem',z,[0,1.5,0])

def head(z,h,r,mat=white):
 m.lathe('Rounded pump press head',[(z,0),(z,r*.93),(z+.02,r),(z+h-.025,r),(z+h,r*.93),(z+h,0)],mat,'Actuator',96)
 # Short tubular nozzle includes an open outlet and a visible dark recess.
 o=m.lathe('Short dispensing nozzle',[(0,.055),(.22,.055),(.22,.032),(.01,.032),(0,.055)],mat,'Actuator',48)
 o.rotation_euler.y=math.pi/2;o.location=(r*.55,0,z+h-.07)
 add('head','Actuator','按压头','Actuator',z,[0,2.4,0])

def flat_body(height,depth=.28,neck=.24,material=frost):
 outer=[(0,0,0,0),(0,.36,depth-.07,.07),(.025,.46,depth-.01,.10),(.08,.5,depth,.12),(height-.23,.5,depth,.12),(height-.16,.48,depth-.01,.13),(height-.09,.40,depth-.025,.15),(height-.04,neck,neck,neck),(height,neck,neck,neck)]
 inner=[(height,neck-.035,neck-.035,neck-.035),(height-.09,neck-.035,neck-.035,neck-.035),(height-.16,.38,depth-.055,.11),(height-.24,.465,depth-.035,.10),(.14,.465,depth-.035,.10),(.11,.38,depth-.07,.08),(.11,0,0,0)]
 m.loft('Hollow rounded rectangular bottle with thick base',outer+inner,material,'Body',128)

def artwork(title,category,w,h,z,surface,paper=None,ink='#171914',number=None):
 label=svg(800,1000,f'<rect width="800" height="1000" rx="5" fill="{paper or "#ffffff"}" fill-opacity="{1 if paper else .025}"/>')
 printing=svg(800,1000,logo(m,90,75,620,228,ink)+text(400,640,title,40,3,ink,True)+'<path d="M340 450H460" stroke="'+ink+'" stroke-width="2"/>'+text(400,760,category,24,7,ink)+(text(400,900,number,30,2,ink) if number else ''))
 m.artwork(label,printing)
 if paper:
  m.sheet('Unprinted paper label',w,h,z,surface,m.texture('Paper label','label.png'),'PaperLabel',nx=40,ny=28)
  add('label','PaperLabel','纸标','Label',z+h/2,[-1.35,.08,.5])
 m.sheet('Complete Liaose wordmark and product print',w,h,z,surface,m.texture('Complete print','print.png'),'LogoPrint',nx=40,ny=28,offset=.0025)
 add('print','LogoPrint','完整印刷','Print',z+h/2,[-2.75,.15,1.2])

if PID=='poster-072':
 flat_body(1.85)
 cylinder('Ivory pump collar',1.81,.30,.32,white,'Closure');add('closure','Closure','泵座','Collar',1.81,[0,.9,0])
 stem(2.08,.13,.12);head(2.19,.46,.185)
 cylinder('Hollow transparent pump cover',2.08,.67,.34,clear,'Overcap',.025);add('overcap','Overcap','透明罩','Cover',2.08,[0,3.2,0])
 total=2.75;add('jar','Body','磨砂方瓶','Bottle',0)
 artwork('DAILY EMULSION','FACE CARE',.78,1.18,.3,lambda x,z:-.28)
elif PID=='poster-073':
 hollow('Empty sloping shoulder oil bottle',[(0,.36),(.03,.46),(.08,.50),(1.12,.50),(1.30,.48),(1.48,.40),(1.64,.28),(1.76,.195),(1.95,.195)],clear)
 cylinder('Ivory cylindrical oil screw cap',1.90,.36,.235,white,'Closure');add('closure','Closure','旋盖','Cap',1.90,[0,1.5,0])
 total=2.26;add('jar','Body','透明油瓶','Bottles',0)
 artwork('BODY OIL','',.68,.92,.30,lambda x,z:-math.sqrt(.5**2-x*x),number='02')
 # Three packages share component groups so lids and printed artwork open together.
 for node,g in list(m.groups.items()):
  originals=list(g.children)
  for idx,dx in [(1,-1.13),(2,1.13)]:
   for src in originals:
    o=src.copy();o.data=src.data.copy();bpy.context.collection.objects.link(o);o.parent=g;o.location.x+=dx;o.name=src.name+f' variant {idx+1}'
    if node=='LogoPrint':
     number='01' if dx<0 else '03'; svgpath=out/f'print-{number}.svg'; svgpath.write_text((out/'print.svg').read_text().replace('>02</text>',f'>{number}</text>'))
     subprocess.run([NODE,'--input-type=module','-e',"import sharp from '/Users/icecream/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/sharp/dist/index.mjs';await sharp(process.argv[1],{density:144}).png().toFile(process.argv[2]);",str(svgpath),str(out/f'print-{number}.png')],check=True)
     o.data.materials.clear();o.data.materials.append(m.texture(f'Print {number}',f'print-{number}.png'))
 # All three are empty; liquid colours belong to the poster, not structural material claims.
elif PID=='poster-074':
 hollow('Frosted hollow cylindrical airless body',[(0,.38),(.025,.47),(.07,.50),(1.65,.50),(1.72,.47),(1.78,.40)],frost)
 cylinder('Pale yellow airless collar',1.72,.22,.46,yellow,'Closure');add('closure','Closure','泵座','Collar',1.72,[0,.85,0])
 stem(1.91,.12,.18,yellow);head(2.01,.30,.30,yellow)
 cylinder('Transparent dust cover',1.92,.47,.46,clear,'Overcap',.025);add('overcap','Overcap','透明罩','Cover',1.92,[0,3.0,0])
 # shortcut: hidden lift plate is illustrative until a measured airless assembly is supplied.
 m.lathe('Illustrative internal rising plate',[(.16,0),(.16,.455),(.20,.455),(.20,0)],white,'Piston',96);add('liner','Piston','升降托盘','Lift plate',.18,[1.15,.35,.2])
 total=2.39;add('jar','Body','磨砂筒身','Body',0)
 artwork('AIRLESS PUMP','',.74,1.13,.25,lambda x,z:-math.sqrt(.5**2-x*x))
elif PID=='poster-075':
 red=m.mat('Rose tinted empty container','#b54b43',.12,.8)
 hollow('Wide empty rounded red jar',[(0,.38),(.025,.47),(.06,.50),(.85,.50),(.92,.48),(.98,.45)],red)
 cylinder('Broad ivory pump collar',.93,.31,.51,white,'Closure');add('closure','Closure','宽泵座','Collar',.93,[0,.95,0])
 stem(1.21,.28,.20)
 profile=[(1.46,0,0,0),(1.46,.49,.33,.25),(1.49,.59,.39,.30),(1.54,.62,.41,.31),(1.57,.60,.40,.30),(1.59,0,0,0)]
 m.loft('Wide flat oval press disk',profile,white,'Actuator',128)
 outlet=m.mat('Recessed pump outlet','#b7a17c',.48)
 o=m.lathe('Front dispensing recess',[(0,0),(0,.035),(.012,.035),(.012,0)],outlet,'Actuator',32);o.rotation_euler.x=math.pi/2;o.location=(0,-.395,1.525)
 add('head','Actuator','椭圆泵头','Oval head',1.46,[0,2,0]);add('jar','Body','红色罐身','Jar',0);total=1.59
 artwork('EXFOLIATING GEL','',.78,.62,.18,lambda x,z:-math.sqrt(.5**2-x*x),ink='#ffffff')
elif PID=='poster-076':
 green=m.mat('Pale celadon frosted empty bottle','#e8edda',.23,.9)
 flat_body(1.71,.30,.29,green)
 cylinder('White inner screw closure',1.67,.34,.30,white,'Closure');add('closure','Closure','旋盖','Cap',1.67,[0,1.3,0])
 cylinder('Transparent ribbed cap shell',1.69,.35,.345,clear,'Overcap',.025)
 for i in range(28):
  a=i*math.tau/28;o=m.lathe('Cap vertical grip',[(0,0),(0,.009),(.27,.009),(.27,0)],clear,'Overcap',12);o.location=(.345*math.cos(a),.345*math.sin(a),1.73)
 add('overcap','Overcap','透明外盖','Outer cap',1.69,[0,2.4,0]);add('jar','Body','浅绿方瓶','Bottle',0);total=2.04
 artwork('DAILY MOUTHWASH','ORAL CARE',.68,1.10,.28,lambda x,z:-.30,paper='#f1eee5')
elif PID=='poster-077':
 hollow('Slim pearl silver hollow applicator casing',[(0,.40),(.03,.48),(.09,.50),(4.25,.50),(4.32,.46),(4.38,.39)],silver)
 m.lathe('Black stepped applicator collar',[(4.28,.34),(4.28,.44),(4.48,.44),(4.52,.39),(4.74,.39),(4.78,.34),(4.78,.28),(4.40,.28),(4.28,.34)],black,'NeckInsert');add('liner','NeckInsert','黑色连接座','Seat',4.38,[0,.75,0])
 m.lathe('Sculpted black roller neck',[(4.70,.28),(4.75,.32),(4.87,.30),(5.15,.16),(5.30,.16),(5.40,.25),(5.55,.25),(5.57,.18),(5.43,.17),(5.28,.10),(4.70,.10),(4.70,.28)],black,'RollerSeat');add('head','RollerSeat','滚珠头座','Roller seat',4.74,[0,1.55,0])
 bpy.ops.mesh.primitive_uv_sphere_add(segments=48,ring_count=24,radius=.215,location=(0,0,5.55));o=bpy.context.object;o.name='Polished visible rolling ball';o.data.materials.append(metal)
 g=bpy.data.objects.new('RollerBall',None);bpy.context.collection.objects.link(g);m.groups['RollerBall']=g;o.parent=g
 for f in o.data.polygons:f.use_smooth=True
 add('ball','RollerBall','金属滚珠','Metal ball',5.55,[0,2.2,0])
 cylinder('Pearl silver protective cap',4.34,1.48,.515,silver,'Closure');add('closure','Closure','银色保护盖','Cap',4.34,[1.15,2.3,0])
 add('jar','Body','银色笔管','Tube',0);total=5.82
 artwork('EYE SERUM ROLLER','EYE CARE',.74,1.25,2.5,lambda x,z:-math.sqrt(.5**2-x*x))
else:
 olive=m.mat('Smoky olive empty glass','#6d7d48',.09,.92)
 hollow('Tall olive hollow cylinder with heavy base',[(0,.36),(.025,.46),(.08,.50),(2.05,.50),(2.10,.47),(2.14,.42),(2.25,.42)],olive)
 profile=[(2.10,.46),(2.10,.505),(2.75,.505),(2.81,.49),(2.86,.455),(2.90,.39),(2.935,.28),(2.95,0),(2.92,0),(2.905,.27),(2.87,.38),(2.83,.43),(2.78,.46),(2.13,.46),(2.10,.46)]
 m.lathe('Large smooth rounded dome white cap',profile,white,'Closure',128);add('closure','Closure','圆顶白盖','Dome cap',2.10,[0,2.4,0]);add('jar','Body','橄榄绿瓶','Bottle',0);total=2.95
 artwork('TEA ESSENCE','FACE CARE',.80,.93,.25,lambda x,z:-math.sqrt(.5**2-x*x),paper='#b8c69a',ink='#26361a')

c=config(parts,offsets,glass=PID!='poster-077',frosted=False,metal=PID=='poster-077')
c['appearance']['overcapToneMapped']=False
c['explosion']['scales']['print']=1.55
c['explosion']['camera'].update(centerY=[1.45,2.85],height=[3.8,7.0],width=[4.4 if PID=='poster-073' else 3.4,7.7 if PID=='poster-073' else 6.7],centerX=[0,-.8])
# Retain the reference tint in the GLB; no extra WebGL attenuation is needed.
if PID=='poster-073':
 c['explosion']['offsets']['print']=[0,-1.5,1.2];c['explosion']['scales']['print']=1.1
 c['explosion']['camera'].update(width=[4.8,6],height=[3.8,7.8],centerY=[1.45,1.2],centerX=[0,0])
if PID=='poster-075':c['appearance']['studio']={'background':'#80534d','ink':'#fff1e7','swatch':['#b54b43','#f2eee4']}
if PID=='poster-077':c['appearance'].update(glass=False);c['explosion']['camera'].update(width=[2.8,6.3],height=[3.7,6.7])
m.export(total,pivots,{'closedHeightToWidth':total,'generator':'build_liaose_seven.py','referencePoster':PID,'printIncludes':['liaose'],'primaryContainers':3 if PID=='poster-073' else 1,'hiddenStructure':'Hidden seals and pump mechanics are illustrative. Empty packaging, no formula.'},c)
