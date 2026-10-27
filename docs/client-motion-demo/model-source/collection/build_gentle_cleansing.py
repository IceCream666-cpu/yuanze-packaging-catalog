"""Gentle Cleansing 044: empty packaging, calibrated to the full original poster."""
import bpy, math, json, subprocess, xml.etree.ElementTree as ET
from pathlib import Path
from mathutils import Vector
import numpy as np
BASE=Path(__file__).resolve().parent;CLIENT=BASE.parents[1];OUT=BASE/'poster-044';OUT.mkdir(exist_ok=True)
logo=next(e.attrib['d'] for e in ET.parse(OUT/'print.svg').getroot().iter() if e.tag.endswith('path'))
printing=f'''<svg xmlns="http://www.w3.org/2000/svg" width="820" height="1640" viewBox="0 0 820 1640"><svg x="102.5" y="70.2" width="615" height="270" viewBox="0 0 340 125" preserveAspectRatio="none"><path d="{logo}" fill="#111714"/></svg><g fill="#101612" font-family="Helvetica Neue,Arial,sans-serif" text-anchor="middle"><text x="410" y="1252" font-size="49" letter-spacing="13.5">GENTLE</text><text x="410" y="1337" font-size="49" letter-spacing="15.2">CLEANSING FOAM</text><path d="M344.5 1436H475.5" fill="none" stroke="#101612" stroke-width="3.2"/><text x="410" y="1590" font-size="64" letter-spacing="2">120 ml</text></g></svg>'''
(OUT/'print.svg').write_text(printing)
# Fine stochastic alpha gives the pearl-white oval a translucent frosted finish.
w,h=900,1138;x,y=np.meshgrid(np.linspace(-1,1,w),np.linspace(-1,1,h));rr=x*x+y*y
rng=np.random.default_rng(44);grain=rng.random((h,w));edge=np.clip((1-rr)*350,0,1)
alpha=edge*(.46+.11*grain+.04*np.sin(y*2+1))
rgba=np.dstack([np.clip(.88+.045*grain,0,1),np.clip(.925+.04*grain,0,1),np.clip(.95+.035*grain,0,1),alpha]).astype(np.float32)
im=bpy.data.images.new('Gentle pearl frost oval',width=w,height=h,alpha=True);im.pixels.foreach_set(rgba[::-1].ravel());im.filepath_raw=str(OUT/'label.png');im.file_format='PNG';im.save();im.filepath_raw=str(OUT/'oval-frost.png');im.save()
(OUT/'label.svg').write_text('<svg xmlns="http://www.w3.org/2000/svg" width="720" height="910" viewBox="0 0 720 910"><image href="oval-frost.png" width="720" height="910"/></svg>')
node='/Users/icecream/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/bin/node'
script="""import sharp from '/Users/icecream/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/sharp/dist/index.mjs';import fs from 'node:fs/promises';const dir=process.argv[1];await sharp(await fs.readFile(dir+'/print.svg'),{density:144}).png().toFile(dir+'/print.png');await sharp(dir+'/label.png').png({palette:true,colours:128}).toFile(dir+'/label-optimized.png');await fs.rename(dir+'/label-optimized.png',dir+'/label.png');"""
subprocess.run([node,'--input-type=module','-e',script,str(OUT)],check=True)
bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)
groups={}
def mat(name,color,rough,transmission=0,ior=1.49):
 m=bpy.data.materials.new(name);m.use_nodes=True;b=m.node_tree.nodes.get('Principled BSDF');rgb=[int(color[i:i+2],16)/255 for i in (1,3,5)];b.inputs['Base Color'].default_value=(*[v/12.92 if v<=.04045 else ((v+.055)/1.055)**2.4 for v in rgb],1);b.inputs['Roughness'].default_value=rough;b.inputs['Transmission Weight'].default_value=transmission;b.inputs['IOR'].default_value=ior;return m
clear=mat('Gentle neutral clear bottle wall','#ffffff',.025,1,1.49)
cover=mat('Gentle clear thin protective cover','#f8fcff',.045,1,1.46)
white=mat('Gentle glossy neutral white closure','#f6f6f3',.23)
headwhite=mat('Gentle satin white foamer head','#f5f5f1',.28)
inner=mat('Gentle hidden pump polymer','#e2e4df',.42)
dark=mat('Gentle recessed outlet interior','#b4b8b1',.45)
dip_tube=mat('Gentle clear plastic dip tube','#ffffff',.06,.98,1.46)
dip_tube.use_backface_culling=True
def mesh(name,vs,fs,material,parent):
 data=bpy.data.meshes.new(name);data.from_pydata(vs,[],fs);data.update();o=bpy.data.objects.new(name,data);bpy.context.collection.objects.link(o);o.data.materials.append(material)
 if parent not in groups:groups[parent]=bpy.data.objects.new(parent,None);bpy.context.collection.objects.link(groups[parent])
 o.parent=groups[parent]
 for f in data.polygons:f.use_smooth=abs(f.normal.z)<.999
 return o

def lathe(name,profile,material,parent,n=192):
 vs=[];rs=[];fs=[]
 for z,r in profile:
  if r==0:rs.append([len(vs)]);vs.append((0,0,z))
  else:rs.append(list(range(len(vs),len(vs)+n)));vs.extend((r*math.cos(i*math.tau/n),r*math.sin(i*math.tau/n),z) for i in range(n))
 for a,b in zip(rs,rs[1:]):
  if len(a)==len(b)==1:continue
  for i in range(n):
   j=(i+1)%n;fs.append((a[0],b[j],b[i]) if len(a)==1 else (a[i],a[j],b[0]) if len(b)==1 else (a[i],a[j],b[j],b[i]))
 return mesh(name,vs,fs,material,parent)
lathe('Hollow straight clear bottle with rounded thick base',[(0,0),(0,.338),(.008,.394),(.025,.443),(.051,.478),(.082,.495),(.12,.500),(2.110,.500),(2.142,.495),(2.163,.481),(2.175,.455),(2.191,.428),(2.276,.428),(2.286,.418),(2.286,.393),(2.272,.390),(2.188,.390),(2.160,.435),(2.135,.463),(.132,.474),(.112,.462),(.097,.424),(.087,.360),(.087,0)],clear,'Body')
lathe('Illustrative bottle neck retention bead',[(2.204,.428),(2.209,.436),(2.219,.436),(2.224,.428)],clear,'Body')
lathe('Wide smooth white screw closure',[(2.170,.449),(2.170,.478),(2.181,.489),(2.198,.491),(2.471,.491),(2.494,.483),(2.510,.462),(2.520,.439),(2.520,.239),(2.494,.239),(2.494,.444),(2.190,.449),(2.170,.449)],white,'Closure')
lathe('Hidden closure screw seat',[(2.183,.445),(2.480,.445),(2.480,.238),(2.460,.238),(2.460,.413),(2.183,.413),(2.183,.445)],inner,'Closure')
# Concealed tube dimensions and connection are illustrative; both annular ends remain open.
lathe('Hollow clear Gentle pump dip tube',[(.16,.0335),(.1615,.035),(2.6885,.035),(2.69,.0335),(2.69,.0275),(2.6885,.026),(.1615,.026),(.16,.0275),(.16,.0335)],dip_tube,'Closure')
lathe('Clear overcap seating flange',[(2.514,.248),(2.514,.421),(2.520,.439),(2.535,.443),(2.545,.435),(2.550,.414),(2.550,.248),(2.514,.248)],cover,'Closure')
lathe('Foamer stepped pump pedestal',[(2.503,.145),(2.503,.274),(2.516,.300),(2.541,.300),(2.555,.285),(2.602,.285),(2.614,.273),(2.630,.252),(2.683,.252),(2.697,.230),(2.702,.145),(2.503,.145)],headwhite,'PumpStem')
# shortcut: the concealed short stem is illustrative until the physical foamer is supplied.
lathe('Illustrative short foamer connection',[(2.430,.125),(2.430,.143),(2.684,.143),(2.684,.125),(2.430,.125)],inner,'PumpStem')
lathe('Foamer actuator shaft',[(2.674,0),(2.674,.150),(2.687,.160),(2.732,.160),(2.740,0)],headwhite,'Actuator')
lathe('Tall rounded foamer actuator',[(2.696,0),(2.696,.224),(2.707,.248),(2.725,.260),(3.260,.260),(3.286,.255),(3.303,.238),(3.312,.210),(3.315,0)],headwhite,'Actuator')
# A short right-facing flat nozzle replaces the long lever used on ordinary lotion pumps.
ns=48;sections=[(.125,3.246,.173,.064),(.210,3.250,.154,.063),(.295,3.259,.117,.059),(.357,3.269,.092,.053),(.382,3.272,.087,.049)]
def sec(x,z,w,h):return [(x,w*math.copysign(abs(math.cos(i*math.tau/ns))**.48,math.cos(i*math.tau/ns)),z+h*math.copysign(abs(math.sin(i*math.tau/ns))**.48,math.sin(i*math.tau/ns))) for i in range(ns)]
vs=[];fs=[]
for s in sections:vs.extend(sec(*s))
for k in range(len(sections)-1):
 for i in range(ns):
  a=k*ns+i;b=k*ns+(i+1)%ns;fs.append((a,b,b+ns,a+ns))
end=(len(sections)-1)*ns;inner_start=len(vs);vs.extend(sec(.382,3.272,.060,.022));inner_back=len(vs);vs.extend(sec(.347,3.266,.060,.022))
for i in range(ns):
 j=(i+1)%ns;fs.append((end+i,end+j,inner_start+j,inner_start+i));fs.append((inner_start+i,inner_start+j,inner_back+j,inner_back+i))
mesh('Short curved right dispensing spout',vs,fs,headwhite,'Actuator')
mesh('Recessed foamer outlet',sec(.346,3.266,.060,.022),[tuple(range(ns))],dark,'Actuator')
# Continuous outer wall, rounded top and returning inner wall form a genuine hollow dust cover.
lathe('Hollow clear protective overcap with top dimple',[(2.540,.447),(2.553,.452),(2.575,.450),(3.367,.446),(3.397,.440),(3.417,.425),(3.430,.399),(3.438,.360),(3.440,.080),(3.438,.050),(3.432,.035),(3.426,.022),(3.425,0),(3.410,0),(3.409,.040),(3.411,.080),(3.410,.352),(3.403,.386),(3.391,.410),(3.370,.426),(2.572,.431),(2.540,.430),(2.540,.447)],cover,'Overcap')
lathe('Clear lower overcap retention rim',[(2.543,.430),(2.543,.451),(2.553,.455),(2.565,.455),(2.576,.450),(2.576,.432),(2.543,.430)],cover,'Overcap')
for kind,parent,name in [('label','PaperLabel','Translucent frosted white oval decoration'),('print','LogoPrint','Complete Gentle Cleansing lettering')]:
 m=mat('Gentle pearl white frosted oval' if kind=='label' else 'Gentle complete black printing','#ffffff',.79 if kind=='label' else .67)
 b=m.node_tree.nodes.get('Principled BSDF');b.inputs['Specular IOR Level'].default_value=.12 if kind=='label' else .02
 tx=m.node_tree.nodes.new('ShaderNodeTexImage');tx.image=bpy.data.images.load(str(OUT/(kind+'.png')));tx.image.pack();m.node_tree.links.new(tx.outputs['Color'],b.inputs['Base Color']);m.node_tree.links.new(tx.outputs['Alpha'],b.inputs['Alpha']);m.surface_render_method='DITHERED'
 width,z0,height=(.72,.605,.91) if kind=='label' else (.82,.24,1.64)
 nx,ny=96,96;vs=[];fs=[]
 for j in range(ny+1):
  for i in range(nx+1):
   x=(i/nx-.5)*width;y=-math.sqrt(.5*.5-x*x)-(.0015 if kind=='label' else .0022);vs.append((x,y,z0+height*j/ny))
 for j in range(ny):
  for i in range(nx):
   a=j*(nx+1)+i;fs.append((a,a+1,a+nx+2,a+nx+1))
 o=mesh(name,vs,fs,m,parent);uv=o.data.uv_layers.new()
 for f in o.data.polygons:
  for li in f.loop_indices:
   v=o.data.loops[li].vertex_index;uv.data[li].uv=(v%(nx+1)/nx,v//(nx+1)/ny)
scale=2.9/3.44;pivots={'Body':0,'Closure':2.17,'PumpStem':2.56,'Actuator':2.70,'Overcap':2.54,'PaperLabel':1.06,'LogoPrint':1.06}
assert set(groups)==set(pivots)
for name,g in groups.items():
 pivot=Vector((0,0,pivots[name]))
 for child in g.children:child.location-=pivot
 g.location=pivot*scale;g.scale=(scale,scale,scale)
assembly=bpy.data.objects.new('PumpAssembly',None);bpy.context.collection.objects.link(assembly)
for child in ('Closure','PumpStem','Actuator'):groups[child].parent=assembly
groups={name:groups[name] for name in ('Body','Overcap','PaperLabel','LogoPrint')}
groups['PumpAssembly']=assembly
assert abs(scale*3.44-2.9)<1e-9
bpy.ops.object.select_all(action='SELECT')
bpy.ops.export_scene.gltf(filepath=str(CLIENT/'packaging-assets/poster-044.glb'),export_format='GLB',use_selection=True,export_apply=True,export_yup=True,export_extras=True)
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'poster-044.blend'))
(OUT/'model-info.json').write_text(json.dumps({'id':'poster-044','components':list(groups),'assemblyChildren':{'PumpAssembly':['Closure','PumpStem','Actuator']},'completePumpLift':2.15,'overcapLift':3.15,'camera':{'closedCenter':1.45,'openCenter':3.025,'closedHeight':4.2,'openHeight':7.2},'dipTube':{'mesh':'Hollow clear Gentle pump dip tube','parent':'Closure','outerDiameterToBody':.07,'innerDiameterToBody':.052,'bottomToBody':.16,'topToBody':2.69,'bodyInnerFloorToBody':.087,'bottomClearance':(.16-.087)*scale,'fullyOpenBottleClearance':(.16-2.286)*scale+2.15,'openAtBothEnds':True,'dimensionsIllustrative':True},'height':2.9,'width':scale,'closedHeightToDiameter':3.44,'visibleBodyHeightToDiameter':2.17,'closureHeightToDiameter':.35,'closureDiameterToBody':.982,'overcapHeightToDiameter':.90,'overcapDiameterToBody':.91,'ovalWidthToBody':.72,'ovalHeightToBody':.91,'ovalBottomToBody':.605,'printIncludes':['liaose','GENTLE','CLEANSING FOAM','short separator rule','120 ml'],'illustrativeDimensions':True,'containsFormula':False,'containsFoam':False,'reference':'../../mobile-client-preview/assets/posters/poster-044.webp','featuredReference':'featured-assets/poster-044.png','editableArtwork':['label.svg','print.svg'],'proceduralTexture':'oval-frost.png','separateLabelAndPrint':True,'hiddenStructure':'Bottle neck, concealed short foamer stem, dip tube dimensions and actuator connection are illustrative; top-cover dimple is not a through-hole','material':'Neutral clear empty bottle, separate thin clear protective cover, glossy white closure, translucent frosted oval','revision':'complete-foamer-with-clear-dip-tube-local-review-20261027','generator':'build_gentle_cleansing.py'},indent=2)+'\n')
print('Gentle Cleansing rebuilt:',len(groups),'independent groups')
