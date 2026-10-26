"""070 Daylight: frosted conical empty glass, champagne cap and embossed wrap."""
import sys,math,numpy as np
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
from tail_model_helpers import *
m=Model('poster-070');frost=m.mat('Daylight neutral frosted empty glass','#ffffff',.24,1);silver=m.mat('Daylight satin champagne silver cap','#d2c7b5',.28,0,1);seal=m.mat('Daylight hidden inner closure seal','#e0dacf',.45)
m.lathe('Hollow tapered frosted cone bottle with thick rounded base',[(0,0),(0,.389),(.009,.451),(.025,.482),(.049,.496),(.075,.5),(.145,.5),(.202,.487),(.84,.224),(.90,.199),(.927,.191),(.950,.178),(.978,.169),(.985,.169),(.985,.126),(.953,.126),(.922,.151),(.894,.159),(.828,.182),(.198,.443),(.128,.455),(.105,.439),(.087,.392),(.080,0)],frost,'Body',192)
m.lathe('Champagne cylindrical metal screw cap',[(.97,.13),(.97,.169),(.978,.176),(1.374,.176),(1.386,.169),(1.390,.155),(1.390,0),(1.370,0),(1.370,.151),(.98,.151),(.98,.13),(.97,.13)],silver,'Closure',160)
m.lathe('Hidden cap seal',[(1.35,0),(1.35,.147),(1.365,.147),(1.365,0)],seal,'Closure')
# A procedural embossed fibre / curved thread surface, containing no artwork or lettering.
rng=np.random.default_rng(70);w,h=1024,512;u,v=np.meshgrid(np.linspace(0,1,w),np.linspace(0,1,h));gx=u*13+.16*np.sin(v*34);gy=v*6+.14*np.sin(u*45);x=(gx%1)-.5;y=(gy%1)-.5;r=np.sqrt(x*x+y*y);a=np.arctan2(y,x);curves=np.exp(-((np.sin(20*r-2*a+.6*np.sin(a*3)))/.16)**2)*np.clip(1-r*1.3,0,1);grain=rng.normal(0,.015,(h,w));fibres=.025*np.sin(u*2200+v*35)+.018*np.sin(v*1700+u*63);height=.55+.13*curves+grain+fibres;shade=.075*(curves-.25)+grain*.30+fibres*.22;rgb=np.dstack([.83+shade,.795+shade,.735+shade])
def save(name,rgba,normal=False):
 h,w=rgba.shape[:2]
 if not normal:rgba=rgba.copy();rgba[:,:,:3]=np.where(rgba[:,:,:3]<=.04045,rgba[:,:,:3]/12.92,((rgba[:,:,:3]+.055)/1.055)**2.4)
 im=bpy.data.images.new(name,width=w,height=h,alpha=True);im.colorspace_settings.name='Non-Color' if normal else 'sRGB';im.pixels.foreach_set(rgba[::-1].astype(np.float32).ravel());im.filepath_raw=str(m.out/name);im.file_format='PNG';im.save()
save('embossed-wrap.png',np.dstack([np.clip(rgb,0,1),np.ones((h,w))]));dx=(np.roll(height,-1,1)-np.roll(height,1,1))*3.6;dy=(np.roll(height,-1,0)-np.roll(height,1,0))*3.6;norm=np.dstack([-dx,-dy,np.ones((h,w))]);norm/=np.linalg.norm(norm,axis=2)[:,:,None];save('embossed-wrap-normal.png',np.dstack([norm*.5+.5,np.ones((h,w))]),True);wrap=m.texture('Daylight embossed ivory fibrous cap wrap','embossed-wrap.png',.78,normal='embossed-wrap-normal.png')
vs=[];fs=[];nx,ny=160,28
# Nearly one complete turn around the cap; the free edge remains at the front-right.
for j in range(ny+1):
 z=1.035+.305*j/ny
 for i in range(nx+1):
  a=-.6-(math.tau-.17)*i/nx;r=.1795+.0013*math.sin(a*7+z*17);vs.append((r*math.cos(a),r*math.sin(a),z+.0005*math.sin(a*19)))
for j in range(ny):
 for i in range(nx):a=j*(nx+1)+i;fs.append((a,a+1,a+nx+2,a+nx+1))
o=m.mesh('Embossed sleeve around the cap',vs,fs,wrap,'Closure');uv=o.data.uv_layers.new()
for f in o.data.polygons:
 for li in f.loop_indices:k=o.data.loops[li].vertex_index;uv.data[li].uv=(k%(nx+1)/nx,k//(nx+1)/ny)
solid=o.modifiers.new('Thin fibrous wrap','SOLIDIFY');solid.thickness=.0025;bpy.context.view_layer.objects.active=o;bpy.ops.object.modifier_apply(modifier=solid.name)
vs=[];fs=[];nx,ny=28,28;x0=.1795*math.cos(-.6);y0=.1795*math.sin(-.6)
for j in range(ny+1):
 for i in range(nx+1):
  t=i/nx;vs.append((x0+(.325-x0)*t,y0-.013*math.sin(math.pi*t),1.035+.305*j/ny+.0012*math.sin(t*5)))
for j in range(ny):
 for i in range(nx):a=j*(nx+1)+i;fs.append((a,a+1,a+nx+2,a+nx+1))
o=m.mesh('Original loose embossed wrap extension at right',vs,fs,wrap,'Closure');uv=o.data.uv_layers.new()
for f in o.data.polygons:
 for li in f.loop_indices:k=o.data.loops[li].vertex_index;uv.data[li].uv=(.78+.22*(k%(nx+1)/nx),k//(nx+1)/ny)
solid=o.modifiers.new('Thin fibrous flap','SOLIDIFY');solid.thickness=.0025;bpy.context.view_layer.objects.active=o;bpy.ops.object.modifier_apply(modifier=solid.name)
def radius(z):return .487+(z-.202)*(.224-.487)/(.84-.202)
def front(x,z):return -math.sqrt(radius(z)**2-x*x)
m.artwork(svg(470,320,'<rect x="2" y="2" width="466" height="316" rx="18" fill="#faf6eb" fill-opacity=".08"/>'),svg(470,320,logo(m,50,0,370,136,'#171917')+text(235,218,'DAYLIGHT',40,6,'#171917')+text(235,285,'ESSENTIAL OIL',26,6,'#171917')))
for kind,parent,name in [('label','PaperLabel','Unprinted clear demonstration print carrier'),('print','LogoPrint','Complete Daylight Essential Oil black lettering')]:m.sheet(name,.47,.32,.23,front,m.texture('Daylight '+kind,kind+'.png',.25 if kind=='label' else .65),parent,offset=.0015 if kind=='label' else .0025)
parts=[part('closure','Closure','整瓶盖','Complete cap','浅香槟银色圆筒盖、密封垫及压纹套纸保持组装，连同右侧延伸边整体上移。','The champagne-silver cap, internal seal and embossed wrap with its loose right edge stay assembled and lift together.'),part('jar','Body','磨砂瓶','Bottle','阔底锥形磨砂空玻璃。','Empty frosted glass with a broad base and tapered body.'),part('label','PaperLabel','透明膜','Carrier','无字透明承印膜。','Clear print carrier without any lettering.'),part('print','LogoPrint','黑印字','Print','liaose、DAYLIGHT、ESSENTIAL OIL 完整独立。','The complete liaose, DAYLIGHT and ESSENTIAL OIL print separates together.')]
c=config(parts,{'closure':[0,1.35,0],'label':[-1.6,.08,.65],'print':[-3.3,.18,1.65]},frosted=True,clear=True,metal=True);c['explosion']['camera'].update(centerY=[1.45,2.1],height=[4.2,5.3],width=[3.8,7.7])
m.export(1.39,{'Body':0,'Closure':.98,'PaperLabel':.39,'LogoPrint':.39},{'closedHeightToWidth':1.39,'bodyDepthToWidth':1,'glassHeightToWidth':.985,'capDiameterToWidth':.352,'capHeightToWidth':.42,'wrapExtensionToWidth':.325,'presentationRevision':'complete-cap-20261026','completeCapIncludes':['metal cap','internal seal','embossed sleeve','loose wrap extension'],'printIncludes':['liaose','DAYLIGHT','ESSENTIAL OIL'],'generator':'build_daylight_essential_oil.py','proceduralTextures':['embossed-wrap.png','embossed-wrap-normal.png'],'hiddenStructure':'Closure seal and transparent print carrier are illustrative. This is empty frosted glass, with no formula.'},c)
