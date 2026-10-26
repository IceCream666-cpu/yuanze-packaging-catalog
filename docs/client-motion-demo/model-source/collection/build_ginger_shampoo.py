"""067: round amber gathered glass, black pump and real twin braided cords."""
import sys, math, bmesh
from pathlib import Path
from mathutils import Vector
sys.path.insert(0,str(Path(__file__).resolve().parent))
from tail_model_helpers import *
m=Model('poster-067');glass=m.mat('Ginger light amber empty glass','#dfc28a',.025,1);black=m.mat('Ginger glossy black pump','#10110f',.15);brown=m.mat('Ginger cinnamon cord core','#785031',.62);high=m.mat('Ginger raised tan braid','#bb8d58',.68);outlet=m.mat('Ginger outlet recess','#040503',.56)
profile=[(0,.405,.28),(.025,.47,.335),(.07,.495,.357),(.14,.5,.36),(.35,.496,.358),(.55,.476,.346),(.72,.437,.319),(.88,.366,.275),(1.01,.274,.214),(1.10,.201,.161),(1.135,.185,.15),(1.19,.224,.177),(1.26,.264,.210),(1.34,.275,.218),(1.405,.276,.22),(1.43,.252,.203)]
def shape(z):
 for i,(a,b) in enumerate(zip(profile,profile[1:])):
  if z<=b[0]:
   t=max(0,min(1,(z-a[0])/(b[0]-a[0])));prev=profile[max(0,i-1)];nxt=profile[min(len(profile)-1,i+2)];out=[]
   for k in (1,2):
    ma=(b[k]-prev[k])/(b[0]-prev[0]);mb=(nxt[k]-a[k])/(nxt[0]-a[0]);v=(2*t**3-3*t*t+1)*a[k]+(t**3-2*t*t+t)*(b[0]-a[0])*ma+(-2*t**3+3*t*t)*b[k]+(t**3-t*t)*(b[0]-a[0])*mb;out.append(min(max(a[k],b[k]),max(min(a[k],b[k]),v)))
   return out
 return profile[-1][1:]
def section(z,a,wall=0):
 rx,ry=shape(z);fold=.014*math.exp(-((z-1.14)/.16)**2)*(math.sin(8*a+.4)+.3*math.sin(13*a));return ((rx-wall+fold)*math.cos(a),(ry-wall+fold*.7)*math.sin(a),z)
n=144;vs=[(0,0,0)];rings=[[0]];fs=[]
for j in range(151):
 z=1.43*j/150;rings.append(list(range(len(vs),len(vs)+n)));vs.extend(section(z,i*math.tau/n) for i in range(n))
for z,r in [(1.433,.14),(1.477,.14),(1.477,.107),(1.425,.107)]:
 rings.append(list(range(len(vs),len(vs)+n)));vs.extend((r*math.cos(i*math.tau/n),r*math.sin(i*math.tau/n),z) for i in range(n))
for j in range(148,-1,-1):
 z=.065+(1.405-.065)*j/148;rings.append(list(range(len(vs),len(vs)+n)));vs.extend(section(z,i*math.tau/n,.025) for i in range(n))
rings.append([len(vs)]);vs.append((0,0,.065))
for a,b in zip(rings,rings[1:]):
 for i in range(n):
  j=(i+1)%n;fs.append((a[0],b[j],b[i]) if len(a)==1 else (a[i],a[j],b[0]) if len(b)==1 else (a[i],a[j],b[j],b[i]))
o=m.mesh('Hollow broad amber bottle with gathered neck',vs,fs,glass,'Body');bm=bmesh.new();bm.from_mesh(o.data);bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));assert all(e.is_manifold for e in bm.edges);bm.to_mesh(o.data);bm.free()
m.lathe('Black collar flange and tall cylindrical closure',[(1.455,.108),(1.455,.194),(1.464,.202),(1.489,.202),(1.497,.18),(1.510,.18),(1.515,.176),(1.782,.176),(1.795,.167),(1.802,.150),(1.802,.074),(1.784,.074),(1.784,.153),(1.485,.153),(1.480,.108),(1.455,.108)],black,'Closure')
m.lathe('Black raised pump connector',[(1.79,.05),(1.79,.077),(1.917,.077),(1.922,.065),(1.922,.05),(1.79,.05)],black,'PumpStem')
m.lathe('Black head axis',[(1.89,0),(1.89,.062),(1.947,.079),(1.956,0)],black,'Actuator')
# The original long, shallow S-curve pump has a slightly lifted rear and short down-facing outlet.
sections=[(-.49,1.985,.034,.024),(-.47,1.990,.040,.025),(-.40,1.995,.048,.025),(-.30,1.992,.052,.024),(-.18,1.977,.061,.023),(-.04,1.957,.082,.025),(.07,1.954,.097,.027),(.13,1.963,.077,.027),(.164,1.986,.040,.024)]
vs=[];fs=[];ns=32
for x,z,w,h in sections:
 vs.extend((x,w*math.copysign(abs(math.cos(i*math.tau/ns))**.65,math.cos(i*math.tau/ns)),z+h*math.copysign(abs(math.sin(i*math.tau/ns))**.65,math.sin(i*math.tau/ns))) for i in range(ns))
for j in range(len(sections)-1):
 for i in range(ns):a=j*ns+i;b=j*ns+(i+1)%ns;fs.append((a,b,b+ns,a+ns))
fs.extend([tuple(reversed(range(ns))),tuple((len(sections)-1)*ns+i for i in range(ns))]);m.mesh('Long shallow curved black dispensing lever',vs,fs,black,'Actuator')
# Small separate dark outlet sits beneath the tip rather than piercing the visible top.
m.loft('Recessed black outlet',[(1.957,0,0,0),(1.957,.022,.022,.022),(1.965,.022,.022,.022),(1.965,0,0,0)],outlet,'Actuator').location.x=-.467

def braid(name,controls):
 distances=[0]
 for a,b in zip(controls,controls[1:]):distances.append(distances[-1]+(b-a).length)
 length=distances[-1];steps=max(48,int(length/.005));path=[];frames=[];normal=None
 for k in range(steps+1):
  at=length*k/steps;i=min(len(controls)-2,next((j for j in range(len(distances)-1) if distances[j+1]>=at),len(controls)-2));t=(at-distances[i])/(distances[i+1]-distances[i]);path.append(controls[i].lerp(controls[i+1],t))
 for i,p in enumerate(path):
  tangent=(path[min(i+1,len(path)-1)]-path[max(i-1,0)]).normalized()
  if normal is None:normal=Vector((0,0,1)) if abs(tangent.z)<.9 else Vector((0,1,0))
  normal=(normal-tangent*normal.dot(tangent)).normalized();binormal=tangent.cross(normal).normalized();frames.append((normal.copy(),binormal,tangent))
 for s in range(9):
  centres=[]
  for i,(p,(n,b,t)) in enumerate(zip(path,frames)):
   a=(1 if s<5 else -1)*length*i/(len(path)-1)*math.tau/.042+(s%4)*math.pi/2;r=0 if s==0 else .010;centres.append(p+r*(n*math.cos(a)+b*math.sin(a)))
  vs=[];fs=[];rad=.009 if s==0 else .0036;sides=6
  for p,(n,b,t) in zip(centres,frames):vs.extend(tuple(p+rad*(n*math.cos(i*math.tau/sides)+b*math.sin(i*math.tau/sides))) for i in range(sides))
  for j in range(len(centres)-1):
   for i in range(sides):a=j*sides+i;b=j*sides+(i+1)%sides;fs.append((a,b,b+sides,a+sides))
  fs.extend([tuple(reversed(range(sides))),tuple((len(centres)-1)*sides+i for i in range(sides))]);m.mesh(name+f' strand {s}',vs,fs,high if s%3==1 else brown,'Cord')
for index,z in enumerate([1.106,1.143],1):braid(f'Double neck tie {index}',[Vector((.216*math.cos(i*math.tau/128),.172*math.sin(i*math.tau/128),z+.004*math.cos(i*math.tau/128))) for i in range(129)])
braid('Front right tying knot',[Vector((.218+.025*math.cos(i*math.tau/80),-.105+.013*math.cos(i*math.tau/80),1.132+.045*math.sin(i*math.tau/80))) for i in range(81)])
for index,controls in enumerate([[(.232,1.12),(.31,1.02),(.397,.80),(.47,.51),(.517,.22)],[(.245,1.12),(.34,1.04),(.43,.80),(.50,.53),(.545,.26)]],1):
 pts=[]
 for a,b in zip(controls,controls[1:]):
  for k in range(24):
   t=k/24;x=a[0]+(b[0]-a[0])*t;z=a[1]+(b[1]-a[1])*t;rx,ry=shape(z);front=-ry*math.sqrt(max(.015,1-min(.999,abs(x)/rx)**2));pts.append(Vector((x,front-.025,z)))
 braid(f'Right hanging braided cord {index}',pts)
def front(x,z):
 rx,ry=shape(z);return -ry*math.sqrt(max(.001,1-(x/rx)**2))
m.artwork(svg(660,380,'<rect x="2" y="2" width="656" height="376" rx="25" fill="#fff7de" fill-opacity=".07" stroke="#fff7de" stroke-opacity=".15"/>'),svg(660,380,logo(m,105,85,450,165,'#fffcf4')+text(330,326,'GINGER SHAMPOO',35,14,'#fffcf4')))
for kind,parent,name in [('label','PaperLabel','Illustrative clear carrier without text'),('print','LogoPrint','Complete original white Ginger Shampoo lettering')]:m.sheet(name,.62,.36,.145,front,m.texture('Ginger '+kind,kind+'.png',.24 if kind=='label' else .65),parent,offset=.0015 if kind=='label' else .0025)
parts=[part('head','Actuator','黑泵头','Head','原图长弧形黑色泵嘴。','Long curved black dispensing head from the reference.'),part('stem','PumpStem','泵杆','Stem','短黑色连接杆独立上移。','The short black pump connector lifts independently.'),part('closure','Closure','旋盖','Closure','光面黑色长筒旋盖。','Tall cylindrical closure in glossy black.'),part('cord','Cord','编绳','Cord','双圈棕色编绳及右侧长绳尾。','Two brown braided loops with a knot and long tails on the right.'),part('jar','Body','玻璃瓶','Bottle','保留收腰轮廓与浅琥珀玻璃，空瓶无料液。','Empty light amber glass retains the gathered waist and rounded body.'),part('label','PaperLabel','透明膜','Carrier','演示用无字透明承印膜。','An unprinted clear carrier illustrates the print layer.'),part('print','LogoPrint','白印字','Print','liaose 与 GINGER SHAMPOO 完整独立。','The complete liaose and GINGER SHAMPOO lettering forms one separate layer.')]
c=config(parts,{'closure':[0,.85,0],'stem':[0,1.75,0],'head':[0,2.9,0],'cord':[1.15,.2,.25],'label':[-1.6,.08,.65],'print':[-3.3,.18,1.65]},clear=True,extra={'tintedGlass':True,'attenuationDistance':.3,'studio':{'background':'#786047','ink':'#fff2db'}})
m.export(2.02,{'Body':0,'Closure':1.48,'PumpStem':1.85,'Actuator':1.94,'Cord':1.12,'PaperLabel':.325,'LogoPrint':.325},{'closedHeightToWidth':2.02,'bodyDepthToWidth':.72,'glassHeightToWidth':1.477,'pinchHeightToWidth':1.135,'closureDiameterToWidth':.352,'cordDiameterToWidth':.0272,'printIncludes':['liaose','GINGER SHAMPOO'],'generator':'build_ginger_shampoo.py','hiddenStructure':'Amber glass tint follows the visible neck; there is no liquid. Inner pump mechanics and clear carrier are illustrative.'},c)
