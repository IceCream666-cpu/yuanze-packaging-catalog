"""Pure Volume 051: reference-led sculptural packaging, with illustrative unseen mechanics."""
import bpy, math, json, subprocess, xml.etree.ElementTree as ET
from pathlib import Path
from mathutils import Vector
BASE=Path(__file__).resolve().parent;CLIENT=BASE.parents[1];OUT=BASE/'poster-051';OUT.mkdir(exist_ok=True)
logo=next(e.attrib['d'] for e in ET.parse(OUT/'print.svg').getroot().iter() if e.tag.endswith('path'))
label='''<svg xmlns="http://www.w3.org/2000/svg" width="770" height="620" viewBox="0 0 770 620"><rect x="3" y="3" width="764" height="614" rx="38" fill="#fffdf7" fill-opacity="0.14" stroke="#87957e" stroke-opacity="0.5" stroke-width="4"/></svg>'''
printing=f'''<svg xmlns="http://www.w3.org/2000/svg" width="770" height="620" viewBox="0 0 770 620"><svg x="90" y="26" width="590" height="216.912" viewBox="0 0 340 125"><path d="{logo}" fill="#0b402a"/></svg><g fill="#173e2b" font-family="Helvetica Neue,Arial,sans-serif" text-anchor="middle"><text x="385" y="452" font-size="45" letter-spacing="16">PURE VOLUME</text><text x="385" y="545" font-size="40" letter-spacing="12">SHAMPOO</text></g></svg>'''
(OUT/'label.svg').write_text(label);(OUT/'print.svg').write_text(printing)
node='/Users/icecream/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/bin/node'
script="""import sharp from '/Users/icecream/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/sharp/dist/index.mjs';import fs from 'node:fs/promises';for(const kind of ['label','print']){const dir=process.argv[1];await sharp(await fs.readFile(dir+'/'+kind+'.svg'),{density:144}).png().toFile(dir+'/'+kind+'.png');}"""
subprocess.run([node,'--input-type=module','-e',script,str(OUT)],check=True)
bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)
groups={}
def mat(name,color,rough=.4,metal=0):
 m=bpy.data.materials.new(name);m.use_nodes=True;b=m.node_tree.nodes.get('Principled BSDF');rgb=[int(color[i:i+2],16)/255 for i in (1,3,5)];b.inputs['Base Color'].default_value=(*[v/12.92 if v<=.04045 else ((v+.055)/1.055)**2.4 for v in rgb],1);b.inputs['Roughness'].default_value=rough;b.inputs['Metallic'].default_value=metal;return m
body=mat('Pure Volume soft matte ivory body','#f3eee3',.48)
cap=mat('Pure Volume satin ivory pump','#f1eadc',.31)
gold=mat('Pure Volume narrow brushed gold ring','#a68c56',.24,1)
green=mat('Pure Volume dark forest braided cord','#073d29',.24)
green_hi=mat('Pure Volume cord raised strands','#10513a',.27)
inside=mat('Pure Volume hidden warm polymer','#d8d1c4',.46)
outlet=mat('Pure Volume recessed dispensing mouth','#57584b',.5)
def mesh(name,verts,faces,material,parent):
 data=bpy.data.meshes.new(name);data.from_pydata(verts,[],faces);data.update();o=bpy.data.objects.new(name,data);bpy.context.collection.objects.link(o);o.data.materials.append(material)
 if parent not in groups:groups[parent]=bpy.data.objects.new(parent,None);bpy.context.collection.objects.link(groups[parent])
 o.parent=groups[parent]
 for f in data.polygons:f.use_smooth=abs(f.normal.z)<.999
 return o
profile=[(0,.395,.185,3.2),(.025,.461,.216,3.2),(.06,.485,.231,3.2),(.13,.498,.239,3.1),(.25,.50,.24,3.1),(.36,.479,.237,3.0),(.45,.442,.226,2.8),(.55,.401,.214,2.6),(.65,.359,.196,2.4),(.74,.296,.175,2.2),(.80,.245,.153,2.1),(.86,.202,.134,2.0),(.92,.175,.121,2.0),(.96,.179,.123,2.0),(1.01,.205,.134,2.1),(1.05,.227,.145,2.3),(1.10,.234,.149,2.5),(1.145,.225,.148,2.7),(1.175,.211,.143,2.6),(1.188,.198,.137,2.4)]
def shape(z):
 for i,(a,b) in enumerate(zip(profile,profile[1:])):
  if z<=b[0]:
   t=max(0,min(1,(z-a[0])/(b[0]-a[0])));out=[]
   for k in range(1,4):
    prev=profile[max(0,i-1)];nxt=profile[min(len(profile)-1,i+2)]
    ma=(b[k]-prev[k])/(b[0]-prev[0]);mb=(nxt[k]-a[k])/(nxt[0]-a[0])
    v=(2*t**3-3*t*t+1)*a[k]+(t**3-2*t*t+t)*(b[0]-a[0])*ma+(-2*t**3+3*t*t)*b[k]+(t**3-t*t)*(b[0]-a[0])*mb
    out.append(min(max(a[k],b[k]),max(min(a[k],b[k]),v)))
   return out
 return profile[-1][1:]
def section(z,a,wall=0):
 rx,ry,e=shape(z);c,s=math.cos(a),math.sin(a)
 # Broad folds begin below the tie and rise into the uneven upturned collar.
 amp=.028*math.exp(-((z-.99)/.17)**2)
 fold=amp*(math.sin(7*a+z*3.2)+.26*math.sin(11*a-z*2.3))
 x=(rx-wall)*math.copysign(abs(c)**(2/e),c)+fold*c
 y=(ry-wall)*math.copysign(abs(s)**(2/e),s)+fold*s*.72
 return x,y,z
n=160;verts=[(0,0,0)];rings=[[0]];faces=[]
for j in range(151):
 z=1.188*j/150;rings.append(list(range(len(verts),len(verts)+n)));verts.extend(section(z,i*math.tau/n) for i in range(n))
# The top rolls inward to a pump opening; the lower interior closes above the foot.
for z,rx,ry in [(1.188,.143,.118),(1.166,.143,.118)]:
 rings.append(list(range(len(verts),len(verts)+n)));verts.extend((rx*math.cos(i*math.tau/n),ry*math.sin(i*math.tau/n),z) for i in range(n))
for j in range(148,-1,-1):
 z=.06+(1.145-.06)*j/148;rings.append(list(range(len(verts),len(verts)+n)));verts.extend(section(z,i*math.tau/n,.025) for i in range(n))
rings.append([len(verts)]);verts.append((0,0,.06))
for a,b in zip(rings,rings[1:]):
 for i in range(n):
  j=(i+1)%n
  faces.append((a[0],b[j],b[i]) if len(a)==1 else (a[i],a[j],b[0]) if len(b)==1 else (a[i],a[j],b[j],b[i]))
mesh('Hollow ivory pouch body with soft gathered folds',verts,faces,body,'Body')
def lathe(name,prof,material,parent,n=128):
 vs=[];rs=[];fs=[]
 for z,r in prof:
  if r==0:rs.append([len(vs)]);vs.append((0,0,z))
  else:rs.append(list(range(len(vs),len(vs)+n)));vs.extend((r*math.cos(i*math.tau/n),r*math.sin(i*math.tau/n),z) for i in range(n))
 for a,b in zip(rs,rs[1:]):
  if len(a)==len(b)==1:continue
  for i in range(n):
   j=(i+1)%n;fs.append((a[0],b[j],b[i]) if len(a)==1 else (a[i],a[j],b[0]) if len(b)==1 else (a[i],a[j],b[j],b[i]))
 return mesh(name,vs,fs,material,parent)
lathe('Broad ivory screw closure',[(1.176,.143),(1.180,.161),(1.185,.176),(1.196,.182),(1.208,.180),(1.218,.171),(1.223,.164),(1.240,.163),(1.442,.163),(1.460,.159),(1.470,.150),(1.473,.077),(1.450,.077),(1.450,.139),(1.235,.139),(1.176,.143)],cap,'Closure')
lathe('Single fine gold closure line',[(1.232,.163),(1.234,.165),(1.238,.165),(1.240,.163)],gold,'Closure')
lathe('Hidden closure screw seat',[(1.179,.138),(1.444,.138),(1.444,.077),(1.430,.077),(1.430,.124),(1.179,.124),(1.179,.138)],inside,'Closure')
lathe('Independent ivory pump stem',[(1.462,.063),(1.462,.078),(1.470,.082),(1.548,.082),(1.557,.076),(1.557,.063),(1.462,.063)],cap,'PumpStem')
lathe('Actuator connection shaft',[(1.528,0),(1.528,.063),(1.538,.071),(1.575,.071),(1.585,.066),(1.585,0)],cap,'Actuator')
# The flattened broad spout rises toward its open left outlet after photographic tilt is removed.
sections=[(-.400,1.653,.042,.027),(-.389,1.653,.047,.027),(-.345,1.648,.051,.027),(-.255,1.632,.057,.028),(-.145,1.603,.065,.029),(-.040,1.576,.083,.031),(.055,1.567,.101,.033),(.124,1.574,.080,.031),(.150,1.585,.045,.022)]
vs=[];fs=[];ns=40
def spout_section(x,z,w,h):
 return [(x,w*math.copysign(abs(math.cos(i*math.tau/ns))**.55,math.cos(i*math.tau/ns)),z+h*math.copysign(abs(math.sin(i*math.tau/ns))**.55,math.sin(i*math.tau/ns))) for i in range(ns)]
for args in sections:vs.extend(spout_section(*args))
for j in range(len(sections)-1):
 for i in range(ns):
  a=j*ns+i;b=j*ns+(i+1)%ns;fs.append((a,b,b+ns,a+ns))
end=len(vs);vs.append((.154,0,1.585))
for i in range(ns):fs.append(((len(sections)-1)*ns+i,(len(sections)-1)*ns+(i+1)%ns,end))
start=len(vs);vs.extend(spout_section(-.400,1.653,.025,.013));inner_end=len(vs);vs.extend(spout_section(-.368,1.650,.025,.013))
for i in range(ns):
 j=(i+1)%ns;fs.append((i,start+i,start+j,j));fs.append((start+i,inner_end+i,inner_end+j,start+j))
mesh('Left curved flattened dispensing lever',vs,fs,cap,'Actuator')
mesh('Recessed flattened outlet',spout_section(-.367,1.650,.025,.013),[tuple(reversed(range(ns)))],outlet,'Actuator')

def rope_path(points,closed=False):
 length=sum((b-a).length for a,b in zip(points,points[1:]));steps=max(24,int(length/.0034));d=[0]
 for a,b in zip(points,points[1:]):d.append(d[-1]+(b-a).length)
 path=[]
 for k in range(steps+1):
  at=length*k/steps;i=min(len(points)-2,next((j for j in range(len(d)-1) if d[j+1]>=at),len(points)-2));t=(at-d[i])/(d[i+1]-d[i]);path.append(points[i].lerp(points[i+1],t))
 frames=[];normal=None
 for i,p in enumerate(path):
  tangent=(path[min(i+1,len(path)-1)]-path[max(i-1,0)]).normalized()
  if normal is None:normal=Vector((0,0,1)) if abs(tangent.z)<.9 else Vector((0,1,0))
  normal=(normal-tangent*normal.dot(tangent)).normalized();binormal=tangent.cross(normal).normalized();frames.append((normal.copy(),binormal,tangent))
 return path,frames,length

def tube(name,centres,frames,r,material,parent='Cord',sides=6):
 vs=[];fs=[]
 for p,(n,b,t) in zip(centres,frames):
  vs.extend(tuple(p+r*(n*math.cos(i*math.tau/sides)+b*math.sin(i*math.tau/sides))) for i in range(sides))
 for j in range(len(centres)-1):
  for i in range(sides):
   a=j*sides+i;b=j*sides+(i+1)%sides;fs.append((a,b,b+sides,a+sides))
 fs.extend([tuple(reversed(range(sides))),tuple((len(centres)-1)*sides+i for i in range(sides))]);return mesh(name,vs,fs,material,parent)

def braid(name,points):
 path,frames,length=rope_path(points);tube(name+' inner rope core',path,frames,.0085,green,sides=8)
 for direction in [-1,1]:
  for strand in range(4):
   line=[]
   for i,(p,(n,b,t)) in enumerate(zip(path,frames)):
    angle=direction*length*(i/(len(path)-1))*math.tau/.045+strand*math.pi/2
    r=.0096+.0012*math.cos(4*angle+direction*math.pi/2)
    line.append(p+r*(n*math.cos(angle)+b*math.sin(angle)))
   tube(f'{name} woven {direction} strand {strand+1}',line,frames,.0031,green_hi if strand%3==0 else green)
for loop,z in enumerate([.916,.957],1):
 points=[Vector((.190*math.cos(i*math.tau/192),.140*math.sin(i*math.tau/192),z+.006*math.cos(i*math.tau/192+.8))) for i in range(193)]
 braid(f'Neck cord loop {loop}',points)
# A compact front-right tying loop and wrapping crossing preserve the asymmetric reference.
knot=[Vector((.197+.031*math.cos(i*math.tau/96),-.083+.012*math.sin(i*math.tau/96),.935+.035*math.sin(i*math.tau/96))) for i in range(97)]
braid('Right hand tying knot',knot)
for index,controls in enumerate([[(.215,.919),(.242,.857),(.267,.725),(.286,.57),(.294,.397)],[(.222,.927),(.266,.853),(.326,.677),(.405,.456),(.477,.234)]],1):
 # Front offsets follow the sculptural body so the hanging cord never cuts through it.
 points=[]
 for j,(a,b) in enumerate(zip(controls,controls[1:])):
  for k in range(25):
   t=k/25;x=a[0]+(b[0]-a[0])*t;z=a[1]+(b[1]-a[1])*t;rx,ry,e=shape(z);front=-ry*max(.02,1-min(.999,abs(x)/rx)**e)**(1/e);points.append(Vector((x,front-.024,z)))
 x,z=controls[-1];rx,ry,e=shape(z);front=-ry*max(.02,1-min(.999,abs(x)/rx)**e)**(1/e);points.append(Vector((x,front-.024,z)))
 braid('Short hanging tail' if index==1 else 'Long hanging tail',points)
 bpy.ops.mesh.primitive_uv_sphere_add(segments=32,ring_count=16,radius=.023,location=points[-1]);o=bpy.context.object;o.name='Green rounded short cord end' if index==1 else 'Green rounded long cord end';o.data.materials.append(green);o.parent=groups['Cord']
 for face in o.data.polygons:face.use_smooth=True

def front_surface(x,z):
 rx,ry,e=shape(z);return -ry*max(.0001,1-(abs(x)/rx)**e)**(1/e)
for kind,parent,name in [('label','PaperLabel','Illustrative transparent curved label carrier'),('print','LogoPrint','Complete Pure Volume green lettering')]:
 m=mat('Pure Volume clear label carrier' if kind=='label' else 'Pure Volume forest green lettering','#ffffff',.23 if kind=='label' else .65)
 b=m.node_tree.nodes.get('Principled BSDF');b.inputs['Specular IOR Level'].default_value=.35 if kind=='label' else .02
 tx=m.node_tree.nodes.new('ShaderNodeTexImage');tx.image=bpy.data.images.load(str(OUT/(kind+'.png')));tx.image.pack();m.node_tree.links.new(tx.outputs['Color'],b.inputs['Base Color']);m.node_tree.links.new(tx.outputs['Alpha'],b.inputs['Alpha']);m.surface_render_method='DITHERED'
 vs=[];fs=[];nx,ny=64,64
 for j in range(ny+1):
  z=.10+.45*j/ny
  for i in range(nx+1):
   x=(i/nx-.5)*.56;vs.append((x,front_surface(x,z)-(.0015 if kind=='label' else .0022),z))
 for j in range(ny):
  for i in range(nx):
   a=j*(nx+1)+i;fs.append((a,a+1,a+nx+2,a+nx+1))
 o=mesh(name,vs,fs,m,parent);uv=o.data.uv_layers.new()
 for f in o.data.polygons:
  for li in f.loop_indices:
   v=o.data.loops[li].vertex_index;uv.data[li].uv=(v%(nx+1)/nx,v//(nx+1)/ny)
scale=2.9/1.68;pivots={'Body':0,'Closure':1.19,'PumpStem':1.50,'Actuator':1.55,'Cord':.94,'PaperLabel':.325,'LogoPrint':.325}
assert set(groups)==set(pivots)
for name,g in groups.items():
 pivot=Vector((0,0,pivots[name]))
 for child in g.children:child.location-=pivot
 g.location=pivot*scale;g.scale=(scale,scale,scale)
# Preserve the fitted pump and keep the neck cord attached to the bottle.
assemblies={}
for name,children in [('PumpAssembly',('Closure','PumpStem','Actuator')),('BottleAssembly',('Body','Cord'))]:
 assembly=bpy.data.objects.new(name,None);bpy.context.collection.objects.link(assembly)
 for child in children:groups[child].parent=assembly
 assemblies[name]=assembly
groups={**assemblies,'PaperLabel':groups['PaperLabel'],'LogoPrint':groups['LogoPrint']}
assert abs(1.68*scale-2.9)<1e-9
bpy.ops.object.select_all(action='SELECT')
bpy.ops.export_scene.gltf(filepath=str(CLIENT/'packaging-assets/poster-051.glb'),export_format='GLB',use_selection=True,export_apply=True,export_yup=True,export_extras=True)
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'poster-051.blend'))
(OUT/'model-info.json').write_text(json.dumps({'id':'poster-051','components':list(groups),'assemblyChildren':{'PumpAssembly':['Closure','PumpStem','Actuator'],'BottleAssembly':['Body','Cord']},'completePumpLift':1.2,'cordStaysOnBottle':True,'height':2.9,'width':scale,'depth':.48*scale,'closedHeightToWidth':1.68,'bodyDepthToWidth':.48,'bodyPinchHeightToWidth':.92,'foldedNeckTopToWidth':1.188,'closureDiameterToWidth':.364,'pumpCylinderDiameterToWidth':.326,'cordDiameterToWidth':.0254,'nozzleSpanToWidth':.55,'illustrativeDimensions':True,'containsFormula':False,'reference':'featured-assets/poster-051.png','editableArtwork':['label.svg','print.svg'],'separateLabelAndPrint':True,'printIncludes':['liaose','PURE VOLUME','SHAMPOO'],'illustrativeHiddenStructure':'Inner pump seat and transparent label carrier are design illustrations; original has no visible paper boundary','material':'Opaque matte ivory packaging with dark green braided cord; not transparent glass','revision':'complete-pump-and-attached-cord-local-review-20261026','generator':'build_pure_volume.py'},indent=2)+'\n')
print('Pure Volume rebuilt:',len(groups),'independent groups')
