"""068 Essence Water: heavy flat glass, folded lavender cap and chrome neck."""
import sys,math,bmesh
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
from tail_model_helpers import *
m=Model('poster-068');glass=m.mat('Essence Water neutral empty glass','#ffffff',.018,1);lavender=m.mat('Essence Water satin lavender sculpted cover','#b9aab5',.25);silver=m.mat('Essence Water polished silver neck collar','#e7e7e5',.13,0,1);poly=m.mat('Essence Water concealed ivory neck seal','#d8d3d5',.43)
outer=[(0,0,0,0),(0,.41,.15,.05),(.018,.467,.207,.060),(.044,.492,.232,.064),(.075,.5,.24,.067),(1.69,.5,.24,.067),(1.72,.493,.233,.072),(1.75,.472,.213,.079),(1.768,.430,.173,.075),(1.780,.295,.132,.10),(1.792,.205,.125,.10),(1.850,.205,.205,.205)]
inner=[(1.850,.149,.149,.149),(1.790,.149,.149,.149),(1.750,.240,.100,.07),(1.735,.394,.140,.045),(1.708,.456,.196,.052),(.179,.456,.196,.052),(.141,.441,.181,.052),(.122,.405,.145,.05),(.115,0,0,0)]
m.loft('Tall hollow rounded rectangular bottle and heavy glass base',outer+inner,glass,'Body',160)
m.lathe('Silver neck ring',[(1.794,.147),(1.794,.246),(1.801,.254),(1.856,.254),(1.866,.245),(1.866,.150),(1.794,.147)],silver,'NeckInsert')
m.lathe('Concealed closing insert and center seal',[(1.78,0),(1.78,.145),(1.88,.145),(1.88,0)],poly,'NeckInsert')
# The cap has a shallow U-shaped folded front, rising at either side like the original.
vs=[];rings=[];fs=[];n=160
for j in range(85):
 z=1.86+.50*j/84;r=.263-.003*math.cos(math.pi*j/84)
 if j>81:r-=.006*(j-81)/3
 ring=[]
 for i in range(n):
  a=i*math.tau/n;x=r*math.cos(a);y=r*math.sin(a);front=max(0,-math.sin(a))**1.15;u=(x/.265);crease=2.005+.36*u*u;inside=max(0,min(1,(z-crease)/max(.01,2.36-crease)));dip=front*(.025*math.exp(-((z-crease)/.035)**2)+.080*math.sin(math.pi*inside)**.65)
  y+=dip;ring.append(len(vs));vs.append((x,y,z))
 rings.append(ring)
rings.append([len(vs)]);vs.append((0,0,2.36))
# Return through the cap interior; a closed top and open bottom can separate cleanly.
rings.append([len(vs)]);vs.append((0,0,2.337))
for j in range(64,-1,-1):
 z=1.86+.475*j/64;r=.263-.003*math.cos(math.pi*(z-1.86)/.5);ring=[]
 for i in range(n):
  a=i*math.tau/n;u=r*math.cos(a)/.265;crease=2.005+.36*u*u;inside=max(0,min(1,(z-crease)/max(.01,2.36-crease)));dip=max(0,-math.sin(a))**1.15*(.025*math.exp(-((z-crease)/.035)**2)+.080*math.sin(math.pi*inside)**.65);ring.append(len(vs));vs.append(((r-.028)*math.cos(a),(r-.028)*math.sin(a)+dip,z))
 rings.append(ring)
rings.append(rings[0])
for a,b in zip(rings,rings[1:]):
 if len(a)==len(b)==1:continue
 for i in range(n):
  k=(i+1)%n;fs.append((a[0],b[k],b[i]) if len(a)==1 else (a[i],a[k],b[0]) if len(b)==1 else (a[i],a[k],b[k],b[i]))
o=m.mesh('Lavender cap with original U folded front',vs,fs,lavender,'Closure');bm=bmesh.new();bm.from_mesh(o.data);bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));assert all(e.is_manifold for e in bm.edges);bm.to_mesh(o.data);bm.free()
m.artwork(svg(680,1340,'<rect x="1" y="1" width="678" height="1338" fill="#e8dfe4" fill-opacity=".22"/>'),svg(680,1340,'<rect x="6" y="6" width="668" height="1328" fill="none" stroke="#34302f" stroke-width="2"/>'+logo(m,116,350,448,165,'#191919')+text(340,820,'ESSENCE WATER',37,5,'#34302f')+'<path d="M295 925H385" stroke="#34302f" stroke-width="2"/>'+text(340,1290,'200 ml',45,0,'#34302f')))
for kind,parent,name in [('label','PaperLabel','Unprinted translucent pale label carrier'),('print','LogoPrint','Complete Essence Water lettering border and capacity')]:m.sheet(name,.68,1.34,.24,lambda x,z:-.241,m.texture('Essence Water '+kind,kind+'.png'),parent,offset=.0015 if kind=='label' else .0025)
parts=[part('closure','Closure','折面盖','Cap','淡紫色盖子保留前侧 U 形凹折。','The lavender cap retains the U-shaped folded front.'),part('liner','NeckInsert','银颈圈','Collar','银色颈圈与内封口独立。','The silver neck collar and inner seal lift separately.'),part('jar','Body','玻璃瓶','Bottle','透明扁方空瓶与厚玻璃底。','Empty clear rectangular bottle with a thick glass base.'),part('label','PaperLabel','底膜','Carrier','淡色无字底膜。','A pale translucent carrier without lettering.'),part('print','LogoPrint','印刷','Print','原字标、细框线和 200 ml 全部独立。','The original wordmark, fine border and 200 ml capacity move as one print layer.')]
c=config(parts,{'closure':[0,2.8,0],'liner':[0,1.2,0],'label':[-1.6,.08,.65],'print':[-3.3,.18,1.65]},clear=True,metal=True)
m.export(2.36,{'Body':0,'Closure':1.86,'NeckInsert':1.82,'PaperLabel':.91,'LogoPrint':.91},{'closedHeightToWidth':2.36,'bodyDepthToWidth':.48,'glassHeightToWidth':1.85,'capDiameterToWidth':.532,'printIncludes':['liaose','ESSENCE WATER','200 ml','thin rectangular border and separator'],'generator':'build_essence_water.py','hiddenStructure':'Internal seal dimensions are illustrative; the package contains no formula or carton.'},c)
