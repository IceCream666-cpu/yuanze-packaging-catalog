"""Aromatic Body Lotion 064: matte yellow stepped bottle and three-ply cotton cord."""
import sys,math,bmesh
from pathlib import Path
from mathutils import Vector
sys.path.insert(0,str(Path(__file__).resolve().parent))
from build_micro_cream import configure,mat,mesh,loft,lathe,artwork,layer,part,finish

def tube(name,centres,r,material,parent='Cord',sides=8):
 vs=[];fs=[];frames=[];normal=Vector((0,0,1))
 for i,p in enumerate(centres):
  t=(centres[min(i+1,len(centres)-1)]-centres[max(i-1,0)]).normalized()
  if abs(normal.dot(t))>.98:normal=Vector((0,1,0))
  normal=(normal-t*normal.dot(t)).normalized();b=t.cross(normal).normalized();frames.append((normal.copy(),b))
  vs.extend(tuple(p+r*(normal*math.cos(j*math.tau/sides)+b*math.sin(j*math.tau/sides))) for j in range(sides))
 for i in range(len(centres)-1):
  for j in range(sides):a=i*sides+j;b=i*sides+(j+1)%sides;fs.append((a,b,b+sides,a+sides))
 fs+=[tuple(reversed(range(sides))),tuple((len(centres)-1)*sides+j for j in range(sides))]
 obj=mesh(name,vs,fs,material,parent,True)
 # Tight strand turns need explicit triangles and local flat normals to avoid
 # smooth interpolation pointing through the surface at tiny cotton creases.
 data=obj.data;bm=bmesh.new();bm.from_mesh(data)
 bmesh.ops.triangulate(bm,faces=list(bm.faces));bm.to_mesh(data);bm.free();data.update()
 for _ in range(4):
  changed=False
  for face in data.polygons:
   if not face.use_smooth:continue
   normal=sum((data.corner_normals[i].vector for i in face.loop_indices),Vector())
   if normal.length and face.normal.dot(normal.normalized())<.10:
    face.use_smooth=False;changed=True
  if not changed:break
  data.update()
 return frames

def braid(name,points,cotton,light):
 # Parallel-transport frames keep real twisted strands continuous around the neck and tails.
 length=sum((b-a).length for a,b in zip(points,points[1:]));steps=max(40,int(length/.010));dist=[0]
 for a,b in zip(points,points[1:]):dist.append(dist[-1]+(b-a).length)
 centre=[]
 for i in range(steps+1):
  at=length*i/steps;k=min(len(points)-2,next((j for j in range(len(dist)-1) if dist[j+1]>=at),len(points)-2));centre.append(points[k].lerp(points[k+1],(at-dist[k])/(dist[k+1]-dist[k])))
 frames=tube(name+' cotton core',centre,.018,cotton)
 for strand in range(3):
  line=[]
  for i,(p,(n,b)) in enumerate(zip(centre,frames)):
   a=length*i/steps*math.tau/.18+strand*math.tau/3;line.append(p+.026*(n*math.cos(a)+b*math.sin(a)))
  strand_frames=tube(name+f' twisted ply {strand+1}',line,.019,cotton if strand!=1 else light)
  for fibre in range(2):
   fine=[]
   for i,(p,(n,b)) in enumerate(zip(line,strand_frames)):
    a=length*i/steps*math.tau/.023+fibre*math.pi;fine.append(p+.0192*(n*math.cos(a)+b*math.sin(a)))
   tube(name+f' ply {strand+1} surface thread {fibre+1}',fine,.0015,light,sides=5)

def build():
 configure('poster-064')
 yellow=mat('Aromatic soft matte warm yellow body','#e6bb60',.48)
 white=mat('Aromatic satin warm white pump','#f3ebdc',.30)
 cotton=mat('Aromatic natural cotton cord','#e5cfaa',.75);light=mat('Aromatic raised cotton fibres','#f5e7cd',.82)
 dark=mat('Aromatic recessed outlet','#8d806d',.55)
 outer=[(0,0,0,0),(0,.390,.190,.04),(.008,.418,.218,.046),(.025,.430,.230,.048),(.175,.445,.242,.05),(.190,.450,.247,.05),(.198,.487,.267,.055),(.210,.500,.275,.058),(1.035,.500,.275,.058),(1.060,.490,.265,.059),(1.083,.461,.237,.06),(1.102,.345,.190,.075),(1.120,.224,.157,.10),(1.135,.212,.154,.12),(1.275,.165,.145,.14),(1.325,.155,.155,.155)]
 inside=[(1.325,.120,.120,.120),(1.275,.120,.120,.120),(1.115,.155,.120,.115),(1.080,.300,.140,.065),(1.040,.467,.242,.052),(.228,.467,.242,.052),(.202,.412,.213,.045),(.065,.398,.199,.043),(.052,.367,.168,.041),(.052,0,0,0)]
 loft('Hollow matte yellow stepped rectangular bottle',outer+inside,yellow,'Body')
 lathe('Smooth wide white screw collar',[(1.308,.166),(1.308,.198),(1.321,.210),(1.526,.210),(1.544,.202),(1.550,.187),(1.550,.092),(1.526,.092),(1.526,.175),(1.321,.175),(1.308,.166)],white,'Closure')
 lathe('Short independent white pump stem',[(1.525,.070),(1.525,.084),(1.537,.088),(1.645,.088),(1.650,.079),(1.650,.070),(1.525,.070)],white,'PumpStem')
 lathe('White actuator cylindrical hub',[(1.620,0),(1.620,.092),(1.631,.125),(1.725,.125),(1.740,.116),(1.740,0)],white,'Actuator')
 sections=[(-.45,1.735,.048,.026),(-.424,1.740,.052,.026),(-.32,1.748,.067,.028),(-.16,1.756,.085,.030),(0,1.757,.12,.032),(.14,1.752,.103,.031),(.205,1.742,.048,.024)]
 ns=32;vs=[];fs=[]
 def section(x,z,w,h):return [(x,w*math.copysign(abs(math.cos(i*math.tau/ns))**.6,math.cos(i*math.tau/ns)),z+h*math.copysign(abs(math.sin(i*math.tau/ns))**.6,math.sin(i*math.tau/ns))) for i in range(ns)]
 for row in sections:vs.extend(section(*row))
 for j in range(len(sections)-1):
  for i in range(ns):a=j*ns+i;b=j*ns+(i+1)%ns;fs.append((a,b,b+ns,a+ns))
 fs.append(tuple((len(sections)-1)*ns+i for i in range(ns)))
 start=len(vs);vs.extend(section(-.45,1.735,.029,.012));end=len(vs);vs.extend(section(-.415,1.739,.029,.012))
 for i in range(ns):j=(i+1)%ns;fs.extend([(i,start+i,start+j,j),(start+i,end+i,end+j,start+j)])
 fs.append(tuple(reversed([end+i for i in range(ns)])))
 mesh('Flattened long left dispensing head with recessed opening',vs,fs,white,'Actuator',True)
 mesh('Shaded left nozzle recess',section(-.4149,1.739,.028,.011),[tuple(reversed(range(ns)))],dark,'Actuator')
 for index,z in enumerate([1.155,1.235,1.315]):
  points=[Vector((.290*math.cos(i*math.tau/160),.225*math.sin(i*math.tau/160),z+.008*math.sin(i*math.tau/160+.7))) for i in range(161)]
  braid(f'Cotton neck wrap {index+1}',points,cotton,light)
 for index,endz in enumerate([.20,.37]):
  x0=.35+index*.10;endx=.57+index*.17
  points=[Vector((x0+(endx-x0)*(i/100)**.55,-.11-.215*min(1,(1.28-(1.28+(endz-1.28)*i/100))/.16),1.28+(endz-1.28)*i/100)) for i in range(101)]
  braid(f'Cotton hanging tail {index+1}',points,cotton,light)
  knot=[Vector((endx+.038*math.cos(i*math.tau/64),-.255+.028*math.sin(i*math.tau/64),endz+.05*math.sin(i*math.tau/64))) for i in range(65)]
  braid(f'Cotton tied end {index+1}',knot,cotton,light)
  for fibre in range(30):
   phase=fibre*2.39996;length=.10+.045*(.5+.5*math.sin(fibre*7.1));start=Vector((endx+.03*math.cos(phase),-.255+.024*math.sin(phase),endz-.025))
   line=[start+Vector((.025*math.sin(phase)*t+.008*math.sin(phase+t*14)*t,.03*math.cos(phase)*t,-length*t)) for t in [j/12 for j in range(13)]]
   tube(f'Cotton fringe {index+1} fibre {fibre+1}',line,.0012,light,sides=5)
 artwork(650,700,(90,80,470,185),[('—',345,1,0,'Arial'),('AROMATIC',431,43,8,'Helvetica Neue,Arial,sans-serif'),('BODY LOTION',489,40,5.8,'Helvetica Neue,Arial,sans-serif'),('—',550,1,0,'Arial'),('300 ml',650,36,0,'Helvetica Neue,Arial,sans-serif')],background='#eee2c9',ink='#4b301d')
 layer('Blank warm cream paper label','PaperLabel','label',.65,.28,.98,lambda x,z:-.275,rough=.77,offset=.0015)
 layer('Complete Aromatic Body Lotion lettering','LogoPrint','print',.65,.28,.98,lambda x,z:-.275,offset=.0023)
 parts=[part('head','Actuator','长嘴白泵头','White pump','扁长左向出液嘴与凹入出口。','Flat elongated left-facing spout with a recessed outlet.'),part('stem','PumpStem','白色连接泵杆','Pump stem','独立向上拔出的连接段。','Connecting stem lifts out as an independent part.'),part('closure','Closure','白色宽旋盖','White collar','光滑圆筒宽盖座。','Wide smooth cylindrical screw collar.'),part('cord','Cord','天然棉编绳','Cotton cord','三圈股绳、两条长短尾与散纤维。','Three braided wraps, two unequal tails and fine fringe fibers.'),part('jar','Body','黄色阶梯瓶身','Yellow bottle','哑光不透明瓶壁与收窄底脚。','Opaque matte bottle with a narrower stepped foot.'),part('label','PaperLabel','暖白纸标','Paper label','保留无字纸质底材。','Blank warm paper label remains separate from the print.'),part('print','LogoPrint','完整印刷文字','Lettering','品牌、两道细线、产品名与300 ml一同展开。','Brand, two fine rules, product name and 300 ml move together.')]
 finish({'Body':0,'Closure':1.31,'PumpStem':1.55,'Actuator':1.65,'Cord':1.22,'PaperLabel':.63,'LogoPrint':.63},parts,{'glass':False,'frosted':False,'pipette':False,'clearLabel':False,'metal':False,'studio':{'background':'#e4d2ac','ink':'#4c351d'}},{'offsets':{'head':[0,2.9,0],'stem':[0,1.8,0],'closure':[0,.9,0],'cord':[1.35,.22,.35],'label':[-1.55,.08,.65],'print':[-3.3,.18,1.65]},'scales':{'label':1.15,'print':1.95},'camera':{'centerY':[1.45,2.9],'height':[4.2,7.1],'width':[4.1,8.2],'centerX':[0,-.7]}},{'closedHeightToBottleWidth':1.789,'bodyDepthToWidth':.55,'bodyMainShoulderHeight':1.083,'cordWrapCount':3,'cordPlyCount':3,'printIncludes':['liaose','AROMATIC','BODY LOTION','300 ml','two fine rules'],'hiddenStructure':'White pump internal connection and bottle inner wall are illustrative; no lotion.','generator':'build_aromatic_body_lotion.py'})

if __name__=='__main__':build()
