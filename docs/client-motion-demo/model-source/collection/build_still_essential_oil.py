"""069 Still: slim clear heavy-base glass, tall cork and a separate unprinted neck seal."""
import sys,math,numpy as np,base64
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
from tail_model_helpers import *
m=Model('poster-069');glass=m.mat('Still neutral clear empty glass','#ffffff',.022,1)
def save(name,pixels,normal=False):
 h,w=pixels.shape[:2]
 im=bpy.data.images.new(name,width=w,height=h,alpha=True);im.colorspace_settings.name='Non-Color' if normal else 'sRGB';im.pixels.foreach_set(pixels[::-1].astype(np.float32).ravel());im.filepath_raw=str(m.out/name);im.file_format='PNG';im.save()
rng=np.random.default_rng(69);w,h=1024,512;nx,ny=30,22;u,v=np.meshgrid(np.linspace(0,1,w,endpoint=False),np.linspace(0,1,h));gx=u*nx+.10*np.sin(v*95+u*13)+.06*np.sin(u*379+v*77);gy=v*ny+.09*np.sin(u*183)+.05*np.sin(v*311);ix=np.floor(gx).astype(int);iy=np.floor(gy).astype(int);jx=rng.uniform(.1,.9,(ny+3,nx));jy=rng.uniform(.1,.9,(ny+3,nx));tones=rng.random((ny+3,nx));depths=rng.random((ny+3,nx));best=np.full((h,w),99.);second=best.copy();cell=np.zeros((h,w));height=cell.copy()
for dy in (-1,0,1):
 for dx in (-1,0,1):
  cx=ix+dx;cy=np.clip(iy+dy,-1,ny+1);a=cx%nx;b=cy+1;d=(gx-cx-jx[b,a])**2+(gy-cy-jy[b,a])**2;closer=d<best;second=np.where(closer,best,np.minimum(second,d));best=np.minimum(best,d);cell=np.where(closer,tones[b,a],cell);height=np.where(closer,depths[b,a],height)
crack=np.clip((.07-(second-best))/.07,0,1);noise=rng.random((h,w));pores=(noise>.985).astype(float);base=np.dstack([.44+.18*cell,.225+.16*cell,.105+.12*cell]);base-=crack[:,:,None]*np.array([.23,.15,.08]);base+=(noise[:,:,None]-.5)*.045;base-=pores[:,:,None]*.17;save('cork-color.png',np.dstack([np.clip(base,.015,.95),np.ones((h,w))]));heightfield=.6+height*.18-crack*.3-pores*.15+(noise-.5)*.018;dx=(np.roll(heightfield,-1,1)-np.roll(heightfield,1,1))*2.5;dy=(np.roll(heightfield,-1,0)-np.roll(heightfield,1,0))*2.5;normal=np.dstack([-dx,-dy,np.ones((h,w))]);normal/=np.linalg.norm(normal,axis=2)[:,:,None];save('cork-normal.png',np.dstack([normal*.5+.5,np.ones((h,w))]),True)
# Fine ivory fibres also form the seal tag, with no text embedded in either paper texture.
w,h=600,960;x,y=np.meshgrid(np.linspace(0,1,w),np.linspace(0,1,h));grain=rng.normal(0,.006,(h,w))+.004*np.sin(y*1300+x*60)+.002*np.sin(x*1700);paper=np.dstack([.955+grain,.93+grain,.87+grain]);save('paper.png',np.dstack([np.clip(paper,0,1),np.ones((h,w))]));paper64=base64.b64encode((m.out/'paper.png').read_bytes()).decode()
m.lathe('Tall hollow cylindrical glass with half-diameter solid foot',[(0,0),(0,.39),(.012,.457),(.035,.489),(.07,.5),(2.82,.5),(2.855,.495),(2.88,.475),(2.90,.43),(2.925,.353),(2.95,.335),(2.95,.276),(2.91,.276),(2.875,.333),(2.85,.415),(2.81,.46),(.58,.46),(.54,.442),(.505,.40),(.495,0)],glass,'Body',192)
subprocess.run([NODE,'--input-type=module','-e',"import sharp from '/Users/icecream/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/sharp/dist/index.mjs';for(const name of ['cork-color','paper'])await sharp(process.argv[1]+'/'+name+'.png').jpeg({quality:94,chromaSubsampling:'4:4:4'}).toFile(process.argv[1]+'/'+name+'.jpg');",str(m.out)],check=True)
def opaque_texture(name,file,rough,normal=None):
 material=m.texture(name,file,rough,normal);b=material.node_tree.nodes.get('Principled BSDF')
 for link in list(b.inputs['Alpha'].links):material.node_tree.links.remove(link)
 return material
cork=opaque_texture('Still coarse warm brown cork','cork-color.jpg',.82,normal='cork-normal.png')
prof=[(2.76,0),(2.76,.257),(2.78,.273),(2.94,.278),(2.947,.335),(2.96,.375),(3.00,.404),(3.06,.421),(3.14,.425),(3.87,.425),(3.89,.415),(3.9,.397),(3.9,0)]
refined=[]
for a,b in zip(prof,prof[1:]):
 n=max(1,int((b[0]-a[0])/.013)) if a[1] and b[1] else 1
 for j in range(n):t=j/n;refined.append((a[0]+(b[0]-a[0])*t,a[1]+(b[1]-a[1])*t))
refined.append(prof[-1]);o=m.lathe('Tall rounded cork with integrated hidden stopper',refined,cork,'Closure',192)
# UV seam follows the rear; flat surfaces use planar coordinates.
uv=o.data.uv_layers.new()
for face in o.data.polygons:
 coords=[o.data.vertices[o.data.loops[li].vertex_index].co for li in face.loop_indices];us=[(math.atan2(v.y,v.x)/math.tau)%1 for v in coords]
 if max(us)-min(us)>.5:us=[u+1 if u<.5 else u for u in us]
 for li,v,u in zip(face.loop_indices,coords,us):uv.data[li].uv=((v.x/.85+.5)/2.6,v.y/.85+.5) if abs(face.normal.z)>.8 else (u,(v.z-2.94)/.96)
# Unprinted neck seal exits beneath the stopper and drapes down at the right.
material=opaque_texture('Still uncoated warm paper seal','paper.jpg',.82);controls=[(.24,-.04,2.95),(.35,-.055,2.965),(.45,-.065,2.92),(.52,-.075,2.78),(.59,-.085,2.58),(.66,-.095,2.23)];vs=[];fs=[]
for j in range(51):
 at=j/50*(len(controls)-1);i=min(len(controls)-2,int(at));t=at-i;a=Vector(controls[i]);b=Vector(controls[i+1]);p=a.lerp(b,t);vs.extend([(p.x-.17,p.y-.17,p.z),(p.x+.17,p.y+.17,p.z)])
for j in range(50):a=j*2;fs.append((a,a+1,a+3,a+2))
o=m.mesh('Curved original neck paper seal without text',vs,fs,material,'NeckSeal');uv=o.data.uv_layers.new()
for face in o.data.polygons:
 for li in face.loop_indices:v=o.data.loops[li].vertex_index;uv.data[li].uv=(v%2,v//2/50)
# Two real paper faces, separated by an imperceptible thickness, render from either rotation.
solid=o.modifiers.new('Paper thickness','SOLIDIFY');solid.thickness=.006;bpy.context.view_layer.objects.active=o;bpy.ops.object.modifier_apply(modifier=solid.name)
m.artwork(svg(900,1460,f'<image href="data:image/png;base64,{paper64}" width="900" height="1460"/>'),svg(900,1460,logo(m,100,120,700,257,'#231f19')+text(450,705,'STILL',124,20,'#231f19',True)+text(450,880,'ESSENTIAL OIL',62,7,'#231f19',True)+text(450,1350,'30 ml',65,0,'#231f19',True)))
subprocess.run([NODE,'--input-type=module','-e',"import sharp from '/Users/icecream/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/sharp/dist/index.mjs';import fs from 'node:fs/promises';const f=process.argv[1]+'/label.png';await sharp(await fs.readFile(f)).jpeg({quality:95,chromaSubsampling:'4:4:4'}).toFile(process.argv[1]+'/label.jpg');",str(m.out)],check=True)
for kind,parent,name in [('label','PaperLabel','Unprinted warm ivory paper label'),('print','LogoPrint','Complete Still Essential Oil black type and capacity')]:m.sheet(name,.90,1.46,.86,lambda x,z:-math.sqrt(.5*.5-x*x),(opaque_texture('Still '+kind,kind+'.jpg',.78) if kind=='label' else m.texture('Still '+kind,kind+'.png',.78)),parent,offset=.0015 if kind=='label' else .0025)
parts=[part('closure','Closure','软木盖','Cork','高软木盖带独立可提起的塞脚。','The tall cork and its concealed stopper foot lift as one piece.'),part('seal','NeckSeal','颈封签','Seal','原图右侧无字封签可独立展开。','The original unprinted neck seal opens independently on the right.'),part('jar','Body','玻璃瓶','Bottle','细长透明空瓶，保留厚玻璃底。','Slender clear empty bottle with its heavy glass base.'),part('label','PaperLabel','纸标','Label','无字暖白纤维纸。','Warm white textured paper without lettering.'),part('print','LogoPrint','印刷','Print','liaose、STILL、ESSENTIAL OIL、30 ml 完整独立。','The full liaose, STILL, ESSENTIAL OIL and 30 ml print forms a separate layer.')]
c=config(parts,{'closure':[0,2.8,0],'seal':[1.1,.9,.25],'label':[-1.5,.08,.65],'print':[-3.1,.18,1.65]});c['explosion']['camera'].update(width=[3.8,7.0])
m.export(3.9,{'Body':0,'Closure':2.95,'NeckSeal':2.87,'PaperLabel':1.59,'LogoPrint':1.59},{'closedHeightToWidth':3.9,'bodyDepthToWidth':1,'glassHeightToWidth':2.95,'solidBaseHeightToWidth':.495,'corkDiameterToWidth':.85,'visibleCorkHeightToWidth':.96,'labelWidthToWidth':.90,'labelHeightToWidth':1.46,'printIncludes':['liaose','STILL','ESSENTIAL OIL','30 ml'],'generator':'build_still_essential_oil.py','proceduralTextures':['cork-color.png','cork-color.jpg','cork-normal.png','paper.png','paper.jpg','label.jpg'],'hiddenStructure':'The concealed cork foot and wall thickness are illustrative; no oil or box is included.'},c)
