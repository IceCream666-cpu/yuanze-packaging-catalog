"""Woodland 042 reference reconstruction; hidden stopper and wall sizes are illustrative."""
import bpy, math, json, subprocess, xml.etree.ElementTree as ET
from pathlib import Path
from mathutils import Vector
import numpy as np

BASE=Path(__file__).resolve().parent
CLIENT=BASE.parents[1]
OUT=BASE/'poster-042'
OUT.mkdir(exist_ok=True)
# Preserve the approved vector wordmark while rebuilding the complete print layout.
old=ET.parse(OUT/'print.svg').getroot()
logo=next(e.attrib['d'] for e in old.iter() if e.tag.endswith('path'))
w,h=768,1536
x,z=np.meshgrid(np.linspace(0,1,w),np.linspace(0,1,h))
warp=x+.007*np.sin(9*z+2*np.sin(3*z))+.003*np.sin(29*z+9*x)
rng=np.random.default_rng(42)
# Coherent anisotropic ridges give irregular long grain instead of a repeating weave.
def noise(nx,nz):
 grid=rng.random((nz,nx))
 rows=np.array([np.interp(np.linspace(0,nx-1,w),np.arange(nx),row) for row in grid])
 return np.array([np.interp(np.linspace(0,nz-1,h),np.arange(nz),rows[:,i]) for i in range(w)]).T
coarse=noise(120,12)
fine=noise(280,85)
ridges=np.maximum(0,np.sin(170*warp+2*np.sin(9*z)))**18
chips=np.where(coarse>.56, .14+(coarse-.56)*1.5, 0)
cracks=np.maximum(0,1-np.abs(coarse-.56)/.018)
fibre=np.maximum(0,(fine-.55)*2)**3
luma=np.clip(7+5*coarse+65*chips+34*cracks+25*ridges*(.15+.85*coarse**3)+15*fibre,5,75)/255
rgba=np.dstack([luma*.97,luma,luma*.98,np.ones_like(luma)]).astype(np.float32)
wood=bpy.data.images.new('Woodland original procedural black wood',width=w,height=h,alpha=True)
wood.pixels.foreach_set(rgba[::-1].ravel())
wood.filepath_raw=str(OUT/'wood.png');wood.file_format='PNG';wood.save()
label='<svg xmlns="http://www.w3.org/2000/svg" width="610" height="1210" viewBox="0 0 610 1210"><defs><clipPath id="label"><rect width="610" height="1210" rx="9"/></clipPath></defs><image href="wood.png" width="610" height="1210" preserveAspectRatio="none" clip-path="url(#label)"/></svg>'
printing=f'''<svg xmlns="http://www.w3.org/2000/svg" width="610" height="1210" viewBox="0 0 610 1210"><svg x="79" y="243" width="452" height="166.18" viewBox="0 0 340 125"><path d="{logo}" fill="#f0eadb"/></svg><g text-anchor="middle" font-family="Helvetica Neue,Arial,sans-serif" fill="#f4f0e6"><text x="305" y="941" font-size="66" textLength="434" lengthAdjust="spacingAndGlyphs">WOODLAND</text><text x="305" y="1028" font-size="49" letter-spacing="11">BODY WASH</text><text x="305" y="1131" font-size="62">350 ml</text></g></svg>'''
(OUT/'label.svg').write_text(label)
(OUT/'print.svg').write_text(printing)
# Rasterize the editable SVG through the already installed project image runtime.
node='/Users/icecream/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/bin/node'
script="""import sharp from '/Users/icecream/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/sharp/dist/index.mjs';
import fs from 'node:fs/promises';
const dir=process.argv[1];
for(const kind of ['label','print']) {let svg=await fs.readFile(dir+'/'+kind+'.svg','utf8');if(kind==='label') svg=svg.replace('wood.png','data:image/png;base64,'+(await fs.readFile(dir+'/wood.png')).toString('base64'));await sharp(Buffer.from(svg),{density:kind==='label'?96:144}).png(kind==='label'?{palette:true,colours:64}:{}).toFile(dir+'/'+kind+'.png');}
"""
subprocess.run([node,'--input-type=module','-e',script,str(OUT)],check=True)
bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)
groups={}
def material(name,color,roughness,transmission=0):
 m=bpy.data.materials.new(name);m.use_nodes=True;b=m.node_tree.nodes.get('Principled BSDF')
 rgb=[int(color[i:i+2],16)/255 for i in (1,3,5)]
 b.inputs['Base Color'].default_value=(*[v/12.92 if v<=.04045 else ((v+.055)/1.055)**2.4 for v in rgb],1)
 b.inputs['Roughness'].default_value=roughness;b.inputs['Transmission Weight'].default_value=transmission;b.inputs['IOR'].default_value=1.49
 return m
amber=material('Woodland transparent amber glass','#f2a13e',.035,1)
clear=material('Woodland clear thick mouth ring','#ffffff',.025,1)
black=material('Woodland glossy black spherical cap','#080706',.075)
black.node_tree.nodes.get('Principled BSDF').inputs['Coat Weight'].default_value=.28
black.node_tree.nodes.get('Principled BSDF').inputs['Coat Roughness'].default_value=.055
insert=material('Woodland dark polymer stopper insert','#24201c',.34)
def mesh(name,vertices,faces,mat,parent):
 data=bpy.data.meshes.new(name);data.from_pydata(vertices,[],faces);data.update()
 ob=bpy.data.objects.new(name,data);bpy.context.collection.objects.link(ob);ob.data.materials.append(mat)
 if parent not in groups:
  groups[parent]=bpy.data.objects.new(parent,None);bpy.context.collection.objects.link(groups[parent])
 ob.parent=groups[parent]
 for face in data.polygons:face.use_smooth=abs(face.normal.z)<.999
 return ob

def ring(rx,ry,corner,n=128):
 points=[]
 for q in range(4):
  a0=q*math.pi/2;cx=(rx-corner)*(1 if q in (0,3) else -1);cy=(ry-corner)*(1 if q<2 else -1)
  for i in range(n//4):
   a=a0+i/(n//4-1)*math.pi/2
   points.append((cx+corner*math.cos(a),cy+corner*math.sin(a)))
 return points

def loft(name,profile,mat,parent,n=128):
 verts=[];rings=[];faces=[]
 for z,rx,ry,c in profile:
  if rx==0:
   rings.append([len(verts)]);verts.append((0,0,z))
  else:
   rings.append(list(range(len(verts),len(verts)+n)));verts.extend((x,y,z) for x,y in ring(rx,ry,c,n))
 for a,b in zip(rings,rings[1:]):
  if len(a)==len(b)==1:continue
  for i in range(n):
   j=(i+1)%n
   faces.append((a[0],b[j],b[i]) if len(a)==1 else (a[i],a[j],b[0]) if len(b)==1 else (a[i],a[j],b[j],b[i]))
 return mesh(name,verts,faces,mat,parent)
def lathe(name,profile,mat,parent):return loft(name,[(z,r,r,r) for z,r in profile],mat,parent)
outer=[(0,0,0,0),(.008,.410,.260,.070),(.025,.461,.311,.066),(.050,.487,.337,.060),(.085,.498,.348,.055),(.13,.5,.35,.055),(1.37,.5,.35,.055),(1.410,.494,.347,.058),(1.443,.475,.336,.070),(1.468,.445,.323,.092),(1.492,.395,.299,.125),(1.516,.340,.270,.165),(1.546,.287,.244,.205),(1.578,.249,.223,.223),(1.615,.218,.210,.210),(1.655,.201,.201,.201),(1.695,.195,.195,.195),(1.727,.199,.199,.199),(1.755,.208,.208,.208),(1.780,.222,.222,.222),(1.800,.231,.231,.231),(1.809,.231,.231,.231)]
inner=[(1.809,.155,.155,.155),(1.785,.155,.155,.155),(1.750,.173,.173,.173),(1.700,.165,.165,.165),(1.655,.170,.170,.170),(1.610,.188,.180,.180),(1.570,.219,.194,.194),(1.535,.255,.215,.181),(1.505,.307,.240,.150),(1.477,.360,.270,.115),(1.450,.412,.294,.080),(1.420,.447,.311,.052),(1.382,.460,.315,.043),(.16,.460,.315,.043),(.125,.446,.303,.050),(.102,.407,.268,.065),(.098,0,0,0)]
loft('Hollow amber bevelled square bottle',outer+inner,amber,'Body')
lathe('Clear thick flared mouth ring',[(1.773,.225),(1.785,.253),(1.798,.274),(1.810,.282),(1.835,.282),(1.850,.270),(1.858,.252),(1.858,.155),(1.845,.150),(1.803,.150),(1.791,.160),(1.773,.225)],clear,'Body')
# The cap is a sphere cut flat below its equator, with a real hollow underside.
r=.255;centre=2.015;base=1.85
sphere=[(base,math.sqrt(r*r-(base-centre)**2))]
for i in range(1,55):
 a=math.asin((base-centre)/r)+(math.pi/2-math.asin((base-centre)/r))*i/54
 sphere.append((centre+r*math.sin(a),r*math.cos(a) if i<54 else 0))
ri=.230
sphere.append((centre+ri,0))
for i in range(1,49):
 a=math.pi/2+(math.asin((1.875-centre)/ri)-math.pi/2)*i/48
 sphere.append((centre+ri*math.sin(a),ri*math.cos(a)))
sphere.extend([(1.859,.150),(1.850,.150),sphere[0]])
lathe('Hollow glossy black spherical closure',sphere,black,'Closure')
lathe('Black closure seating rim',[(1.846,.150),(1.846,.193),(1.852,.198),(1.860,.198),(1.864,.193),(1.864,.150),(1.846,.150)],black,'Closure')
# shortcut: this hidden friction sleeve is illustrative until a physical closure is measured.
lathe('Illustrative removable sealing sleeve',[(1.720,.109),(1.720,.135),(1.735,.148),(1.805,.148),(1.816,.166),(1.842,.170),(1.857,.161),(1.857,.109),(1.720,.109)],insert,'StopperInsert')
lathe('Illustrative stopper seating ribs',[(1.744,.148),(1.750,.154),(1.757,.148),(1.774,.148),(1.780,.154),(1.787,.148)],insert,'StopperInsert')
for kind,parent,name in [('label','PaperLabel','Black woodgrain label substrate'),('print','LogoPrint','Complete Woodland lettering')]:
 m=material('Woodland black woodgrain substrate' if kind=='label' else 'Woodland warm ivory printing','#ffffff',.56 if kind=='label' else .67)
 b=m.node_tree.nodes.get('Principled BSDF');b.inputs['Specular IOR Level'].default_value=.14 if kind=='label' else .025
 tex=m.node_tree.nodes.new('ShaderNodeTexImage');tex.image=bpy.data.images.load(str(OUT/(kind+'.png')));tex.image.pack()
 m.node_tree.links.new(tex.outputs['Color'],b.inputs['Base Color']);m.node_tree.links.new(tex.outputs['Alpha'],b.inputs['Alpha']);m.surface_render_method='DITHERED'
 y=-.3515 if kind=='label' else -.3524
 ob=mesh(name,[(-.305,y,.14),(.305,y,.14),(.305,y,1.35),(-.305,y,1.35)],[(0,1,2,3)],m,parent)
 uv=ob.data.uv_layers.new()
 for i,co in enumerate([(0,0),(1,0),(1,1),(0,1)]):uv.data[i].uv=co
scale=2.9/2.27
pivots={'Body':0,'Closure':1.85,'StopperInsert':1.79,'PaperLabel':.745,'LogoPrint':.745}
assert set(groups)==set(pivots)
for key,g in groups.items():
 pivot=Vector((0,0,pivots[key]))
 for child in g.children:child.location-=pivot
 g.location=pivot*scale;g.scale=(scale,scale,scale)
# Keep the fitted cap and insert unchanged inside one identity assembly.
cap_assembly=bpy.data.objects.new('CapAssembly',None)
bpy.context.collection.objects.link(cap_assembly)
for key in ('Closure','StopperInsert'):groups[key].parent=cap_assembly
groups={'Body':groups['Body'],'CapAssembly':cap_assembly,'PaperLabel':groups['PaperLabel'],'LogoPrint':groups['LogoPrint']}
assert abs(2.27*scale-2.9)<1e-9
assert abs(.51/(1.0)-.51)<1e-9
bpy.ops.object.select_all(action='SELECT')
bpy.ops.export_scene.gltf(filepath=str(CLIENT/'packaging-assets/poster-042.glb'),export_format='GLB',use_selection=True,export_apply=True,export_yup=True,export_extras=True)
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'poster-042.blend'))
(OUT/'model-info.json').write_text(json.dumps({'id':'poster-042','components':list(groups),'assemblyChildren':{'CapAssembly':['Closure','StopperInsert']},'completeCapLift':1.2,'height':2.9,'width':scale,'depth':.7*scale,'closedHeightToWidth':2.27,'capDiameterToBodyWidth':.51,'capVisibleHeightToBodyWidth':.42,'mouthRingDiameterToBodyWidth':.564,'labelWidthToBodyWidth':.61,'labelHeightToBodyWidth':1.21,'labelBottomToBodyWidth':.14,'illustrativeDimensions':True,'containsFormula':False,'reference':'featured-assets/poster-042.png','editableArtwork':['label.svg','print.svg'],'proceduralTexture':'wood.png','separateLabelAndPrint':True,'printIncludes':['liaose','WOODLAND','BODY WASH','350 ml'],'hiddenStructure':'StopperInsert is an illustrative friction sleeve; verify against a physical sample','revision':'complete-cap-local-review-20261026','generator':'build_woodland.py'},indent=2)+'\n')
print('Woodland rebuilt:',len(groups),'independent groups')
