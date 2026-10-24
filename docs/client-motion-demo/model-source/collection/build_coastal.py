"""Coastal 047 clear empty bottle and two-step cork, calibrated to the original poster."""
import bpy, math, json, subprocess, xml.etree.ElementTree as ET
from pathlib import Path
from mathutils import Vector
import numpy as np
BASE=Path(__file__).resolve().parent;CLIENT=BASE.parents[1];OUT=BASE/'poster-047';OUT.mkdir(exist_ok=True)
logo=next(e.attrib['d'] for e in ET.parse(OUT/'print.svg').getroot().iter() if e.tag.endswith('path'))
printing=f'''<svg xmlns="http://www.w3.org/2000/svg" width="850" height="720" viewBox="0 0 850 720"><svg x="168.5" y="69.5" width="513" height="239" viewBox="0 0 340 125" preserveAspectRatio="none"><path d="{logo}" fill="#24211c"/></svg><g fill="#29251e" font-family="Helvetica Neue,Arial,sans-serif" text-anchor="middle"><text x="425" y="398" font-size="50" letter-spacing="20">COASTAL</text><path d="M374 460H476" fill="none" stroke="#29251e" stroke-width="2"/><text x="425" y="551" font-size="36" letter-spacing="13.15">PERFUME</text><text x="425" y="666" font-size="58">50 ml</text></g></svg>'''
(OUT/'print.svg').write_text(printing)
def save_image(name,rgba):
 h,w=rgba.shape[:2];image=bpy.data.images.new(name,width=w,height=h,alpha=True);image.colorspace_settings.name='Non-Color' if 'normal' in name else 'sRGB';image.pixels.foreach_set(rgba[::-1].astype(np.float32).ravel());image.filepath_raw=str(OUT/name);image.file_format='PNG';image.save();return image
rng=np.random.default_rng(47)
# Jittered coarse cells and fine pores model compressed cork chips, not granite speckles.
w,h=1536,512;ny,nx=13,38
u,v=np.meshgrid(np.linspace(0,1,w,endpoint=False),np.linspace(0,1,h))
gx=u*nx+.085*np.sin(v*137+u*19)+.035*np.sin(u*421+v*96)
gy=v*ny+.070*np.sin(u*297)+.045*np.sin(v*283+u*118)
ix=np.floor(gx).astype(int);iy=np.floor(gy).astype(int)
jx=rng.uniform(.13,.87,(ny+3,nx));jy=rng.uniform(.13,.87,(ny+3,nx));tone=rng.random((ny+3,nx));heights=rng.random((ny+3,nx))
best=np.full((h,w),99.0);second=best.copy();cell=np.zeros((h,w));height=np.zeros((h,w))
for dy in [-1,0,1]:
 for dx in [-1,0,1]:
  cx=ix+dx;cy=np.clip(iy+dy,-1,ny+1);a=cx%nx;b=cy+1
  dist=(gx-cx-jx[b,a])**2+(gy-cy-jy[b,a])**2
  closer=dist<best;second=np.where(closer,best,np.minimum(second,dist));best=np.minimum(best,dist)
  cell=np.where(closer,tone[b,a],cell);height=np.where(closer,heights[b,a],height)
gap=np.clip((.052-(second-best))/.052,0,1)
noise=rng.random((h,w));pores=(noise>.988).astype(float)
for dy,dx in [(0,1),(1,0),(-1,0),(0,-1)]:pores=np.maximum(pores*.8,np.roll(pores,(dy,dx),(0,1))*.50)
crack=gap*(.08+.92*np.clip((height-.25)*2,0,1))
holes=np.zeros((h,w))
for _ in range(260):
 cx=int(rng.integers(12,w-12));cy=int(rng.integers(8,h-8));rx=float(rng.uniform(2.0,8.0));ry=float(rng.uniform(1.2,4.0));angle=float(rng.uniform(-1.0,1.0))
 yy,xx=np.mgrid[-7:8,-11:12];xx=xx.astype(float);yy=yy.astype(float)
 ax=(xx*math.cos(angle)+yy*math.sin(angle))/rx;ay=(-xx*math.sin(angle)+yy*math.cos(angle))/ry
 mask=np.clip((1-ax*ax-ay*ay+.12*np.sin(xx*2.3+yy)) * 5,0,1)
 holes[cy-7:cy+8,cx-11:cx+12]=np.maximum(holes[cy-7:cy+8,cx-11:cx+12],mask)
base=np.dstack([.62+.15*cell,.39+.16*cell,.205+.13*cell])
base-=crack[:,:,None]*np.array([.42,.32,.22]);base-=pores[:,:,None]*.12;base+=(noise[:,:,None]-.5)*.035
base=base*(1-holes[:,:,None])+np.array([.13,.073,.031])*holes[:,:,None]
rgb=np.clip(base,.025,.98)
heightfield=.60+height*.13-crack*.34-pores*.15-holes*.35+(noise-.5)*.020
save_image('cork.png',np.dstack([rgb,np.ones((h,w))]))
dx=(np.roll(heightfield,-1,1)-np.roll(heightfield,1,1))*2.2;dy=(np.roll(heightfield,-1,0)-np.roll(heightfield,1,0))*2.2
norm=np.dstack([-dx,-dy,np.ones((h,w))]);norm/=np.linalg.norm(norm,axis=2)[:,:,None]
save_image('cork-normal.png',np.dstack([norm*.5+.5,np.ones((h,w))]))
# Warm uncoated paper with fine fibres; its texture contains no lettering.
w,h=1275,1080;x,y=np.meshgrid(np.linspace(-1,1,w),np.linspace(-1,1,h));grain=rng.normal(0,.004,(h,w));fibres=.003*np.sin(y*1300+x*53)+.002*np.sin(x*2100+y*24)
rgb=np.dstack([.947+grain+fibres,.928+grain+fibres,.883+grain+fibres]);rad=.05
qx=np.maximum(np.abs(x)-(1-rad),0);qy=np.maximum(np.abs(y)-(1-rad),0);alpha=np.clip((rad-np.sqrt(qx*qx+qy*qy))*600,0,1)
save_image('paper.png',np.dstack([np.clip(rgb,0,1),alpha]))
(OUT/'label.svg').write_text('<svg xmlns="http://www.w3.org/2000/svg" width="850" height="720" viewBox="0 0 850 720"><image href="paper.png" width="850" height="720"/></svg>')
node='/Users/icecream/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/bin/node'
script="""import sharp from '/Users/icecream/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/sharp/dist/index.mjs';import fs from 'node:fs/promises';const dir=process.argv[1];await sharp(await fs.readFile(dir+'/print.svg'),{density:144}).png().toFile(dir+'/print.png');await sharp(dir+'/paper.png').png({palette:true,colours:128}).toFile(dir+'/label.png');await sharp(dir+'/cork.png').jpeg({quality:95,chromaSubsampling:'4:4:4'}).toFile(dir+'/cork-color.jpg');"""
subprocess.run([node,'--input-type=module','-e',script,str(OUT)],check=True)
bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)
groups={}
def mat(name,color,rough,transmission=0):
 m=bpy.data.materials.new(name);m.use_nodes=True;b=m.node_tree.nodes.get('Principled BSDF');rgb=[int(color[i:i+2],16)/255 for i in (1,3,5)];b.inputs['Base Color'].default_value=(*[v/12.92 if v<=.04045 else ((v+.055)/1.055)**2.4 for v in rgb],1);b.inputs['Roughness'].default_value=rough;b.inputs['Transmission Weight'].default_value=transmission;b.inputs['IOR'].default_value=1.49;return m
clear=mat('Coastal neutral clear thick glass','#ffffff',.025,1)
cork=mat('Coastal coarse natural cork','#ffffff',.84);b=cork.node_tree.nodes.get('Principled BSDF');b.inputs['Specular IOR Level'].default_value=.15
for file,key in [('cork-color.jpg','Base Color'),('cork-normal.png','Normal')]:
 t=cork.node_tree.nodes.new('ShaderNodeTexImage');t.image=bpy.data.images.load(str(OUT/file));t.image.pack()
 if key=='Normal':
  t.image.colorspace_settings.name='Non-Color';n=cork.node_tree.nodes.new('ShaderNodeNormalMap');n.inputs['Strength'].default_value=.7;cork.node_tree.links.new(t.outputs['Color'],n.inputs['Color']);cork.node_tree.links.new(n.outputs['Normal'],b.inputs['Normal'])
 else:cork.node_tree.links.new(t.outputs['Color'],b.inputs[key])
def mesh(name,vs,fs,material,parent):
 data=bpy.data.meshes.new(name);data.from_pydata(vs,[],fs);data.update();o=bpy.data.objects.new(name,data);bpy.context.collection.objects.link(o);o.data.materials.append(material)
 if parent not in groups:groups[parent]=bpy.data.objects.new(parent,None);bpy.context.collection.objects.link(groups[parent])
 o.parent=groups[parent]
 for f in data.polygons:f.use_smooth=abs(f.normal.z)<.999
 return o

def lathe(name,profile,material,parent,n=192,cork_uv=False):
 vs=[];rs=[];fs=[]
 for z,r in profile:
  if r==0:rs.append([len(vs)]);vs.append((0,0,z))
  else:
   rs.append(list(range(len(vs),len(vs)+n)))
   for i in range(n):
    a=i*math.tau/n
    irregular=.0014*(math.sin(37*a+z*109)+.4*math.sin(61*a-z*71)) if cork_uv else 0
    vs.append(((r+irregular)*math.cos(a),(r+irregular)*math.sin(a),z))
 for a,b in zip(rs,rs[1:]):
  if len(a)==len(b)==1:continue
  for i in range(n):
   j=(i+1)%n;fs.append((a[0],b[j],b[i]) if len(a)==1 else (a[i],a[j],b[0]) if len(b)==1 else (a[i],a[j],b[j],b[i]))
 o=mesh(name,vs,fs,material,parent)
 if cork_uv:
  uv=o.data.uv_layers.new()
  for face in o.data.polygons:
   coords=[vs[o.data.loops[li].vertex_index] for li in face.loop_indices]
   flat=abs(face.normal.z)>.85
   us=[(math.atan2(y,x)/math.tau)%1 for x,y,z in coords]
   if max(us)-min(us)>.5:us=[u+1 if u<.5 else u for u in us]
   for li,(x,y,z),u in zip(face.loop_indices,coords,us):uv.data[li].uv=((x/.70+.5)/3,y/.70+.5) if flat else (u,(z-1.32)/.57)
 return o
lathe('Hollow short cylindrical bottle with heavy glass base',[(0,0),(0,.375),(.007,.435),(.020,.476),(.040,.494),(.064,.500),(1.185,.500),(1.210,.498),(1.232,.488),(1.247,.460),(1.262,.398),(1.280,.326),(1.296,.270),(1.312,.253),(1.323,.253),(1.329,.243),(1.329,.203),(1.317,.198),(1.284,.198),(1.267,.270),(1.246,.354),(1.223,.427),(1.198,.462),(.257,.462),(.233,.444),(.216,.402),(.210,.350),(.210,0)],clear,'Body')
# The narrow hidden foot remains one piece with the two visible cork sections.
profile=[(1.175,0),(1.175,.174),(1.184,.188),(1.304,.198),(1.315,.211),(1.322,.245),(1.331,.251),(1.442,.255),(1.450,.278),(1.459,.285),(1.475,.287),(1.482,.283),(1.488,.287),(1.535,.294),(1.590,.300),(1.650,.309),(1.710,.317),(1.763,.324),(1.772,.325),(1.776,.319),(1.782,.326),(1.850,.335),(1.874,.337),(1.884,.329),(1.890,.312),(1.890,0)]
# Extra profile rings carry subtle physical granule relief without altering the reference silhouette.
refined=[]
for a,b in zip(profile,profile[1:]):
 count=max(1,int(abs(b[0]-a[0])/.007)) if a[1] and b[1] else 1
 for i in range(count):t=i/count;refined.append((a[0]+(b[0]-a[0])*t,a[1]+(b[1]-a[1])*t))
refined.append(profile[-1]);lathe('Two-step tapered cork with integrated stopper foot',refined,cork,'Closure',256,True)
for kind,parent,name in [('label','PaperLabel','Warm white textured paper label'),('print','LogoPrint','Complete Coastal perfume lettering')]:
 m=mat('Coastal warm uncoated paper' if kind=='label' else 'Coastal complete dark print','#ffffff',.76 if kind=='label' else .66)
 b=m.node_tree.nodes.get('Principled BSDF');b.inputs['Specular IOR Level'].default_value=.06 if kind=='label' else .02
 t=m.node_tree.nodes.new('ShaderNodeTexImage');t.image=bpy.data.images.load(str(OUT/(kind+'.png')));t.image.pack();m.node_tree.links.new(t.outputs['Color'],b.inputs['Base Color']);m.node_tree.links.new(t.outputs['Alpha'],b.inputs['Alpha']);m.surface_render_method='DITHERED'
 nx,ny=96,64;vs=[];fs=[]
 for j in range(ny+1):
  for i in range(nx+1):
   x=(i/nx-.5)*.85;y=-math.sqrt(.5*.5-x*x)-(.0015 if kind=='label' else .0022);vs.append((x,y,.32+.72*j/ny))
 for j in range(ny):
  for i in range(nx):a=j*(nx+1)+i;fs.append((a,a+1,a+nx+2,a+nx+1))
 o=mesh(name,vs,fs,m,parent);uv=o.data.uv_layers.new()
 for f in o.data.polygons:
  for li in f.loop_indices:v=o.data.loops[li].vertex_index;uv.data[li].uv=(v%(nx+1)/nx,v//(nx+1)/ny)
scale=2.9/1.89;pivots={'Body':0,'Closure':1.32,'PaperLabel':.68,'LogoPrint':.68}
assert set(groups)==set(pivots)
for name,g in groups.items():
 pivot=Vector((0,0,pivots[name]))
 for child in g.children:child.location-=pivot
 g.location=pivot*scale;g.scale=(scale,scale,scale)
assert abs(1.89*scale-2.9)<1e-9
bpy.ops.object.select_all(action='SELECT')
bpy.ops.export_scene.gltf(filepath=str(CLIENT/'packaging-assets/poster-047.glb'),export_format='GLB',use_selection=True,export_apply=True,export_yup=True,export_extras=True)
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'poster-047.blend'))
(OUT/'model-info.json').write_text(json.dumps({'id':'poster-047','components':list(groups),'height':2.9,'width':scale,'closedHeightToDiameter':1.89,'glassHeightToDiameter':1.329,'thickBaseToDiameter':.21,'corkVisibleHeightToDiameter':.57,'corkUpperDiameterToBody':.674,'corkLowerDiameterToBody':.510,'corkUpperHeightToDiameter':.44,'labelWidthToDiameter':.85,'labelHeightToDiameter':.72,'labelBottomToDiameter':.32,'labelCentreHeightToDiameter':.68,'illustrativeDimensions':True,'containsFormula':False,'reference':'../../mobile-client-preview/assets/posters/poster-047.webp','featuredReference':'featured-assets/poster-047.png','editableArtwork':['label.svg','print.svg'],'proceduralTextures':['paper.png','cork.png','cork-color.jpg','cork-normal.png'],'separateLabelAndPrint':True,'printIncludes':['liaose','COASTAL','short separator rule','PERFUME','50 ml'],'hiddenStructure':'The short concealed cork foot and wall thickness need physical measurement; cork is removed as one piece','revision':'individual-reference-review-20261024','generator':'build_coastal.py'},indent=2)+'\n')
print('Coastal rebuilt:',len(groups),'independent groups')
