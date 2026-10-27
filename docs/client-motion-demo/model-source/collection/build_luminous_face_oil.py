"""Luminous 058: narrow empty flat glass, mirror silver collar and warm curved paper label."""
import bpy, bmesh, math, json, subprocess, xml.etree.ElementTree as ET
from pathlib import Path
from mathutils import Vector
BASE=Path(__file__).resolve().parent;CLIENT=BASE.parents[1];OUT=BASE/'poster-058';OUT.mkdir(exist_ok=True)
logo=next(e.attrib['d'] for e in ET.parse(OUT/'print.svg').getroot().iter() if e.tag.endswith('path'))
label='<svg xmlns="http://www.w3.org/2000/svg" width="980" height="1415" viewBox="0 0 980 1415"><defs><filter id="paper"><feTurbulence type="fractalNoise" baseFrequency=".75" numOctaves="2" stitchTiles="stitch"/><feColorMatrix type="saturate" values="0"/><feComponentTransfer><feFuncA type="linear" slope=".07"/></feComponentTransfer><feBlend in="SourceGraphic" mode="multiply"/></filter></defs><rect x="1" y="1" width="978" height="1413" rx="10" fill="#f2dcc1" filter="url(#paper)"/></svg>'
printing=f'''<svg xmlns="http://www.w3.org/2000/svg" width="980" height="1415" viewBox="0 0 980 1415"><svg x="138" y="345.75" width="708" height="312" viewBox="0 0 340 125" preserveAspectRatio="none"><path d="{logo}" fill="#28231c"/></svg><g text-anchor="middle" fill="#2b251e" font-family="Helvetica Neue,Arial,sans-serif"><text x="490" y="816" font-size="84" letter-spacing="18">LUMINOUS</text><text x="490" y="916" font-size="84" letter-spacing="18">FACE OIL</text></g><path d="M412.5 1015H567.5" fill="none" stroke="#a78270" stroke-width="4"/><text x="0" y="1198" transform="translate(490,0) scale(.98,1)" text-anchor="middle" fill="#2b251e" font-family="Georgia,Times New Roman,serif" font-size="96">50 ml</text></svg>'''
(OUT/'label.svg').write_text(label);(OUT/'print.svg').write_text(printing)
node='/Users/icecream/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/bin/node'
subprocess.run([node,'--input-type=module','-e',"""import sharp from '/Users/icecream/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/sharp/dist/index.mjs';import fs from 'node:fs/promises';for(const kind of ['label','print'])await sharp(await fs.readFile(process.argv[1]+'/'+kind+'.svg'),{density:kind==='label'?96:144}).png(kind==='label'?{palette:true,colours:128}:{}).toFile(process.argv[1]+'/'+kind+'.png');""",str(OUT)],check=True)
bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False);groups={}
def mat(name,color,rough,transmission=0,metal=0):
 m=bpy.data.materials.new(name);m.use_nodes=True;b=m.node_tree.nodes.get('Principled BSDF');rgb=[int(color[i:i+2],16)/255 for i in (1,3,5)];b.inputs['Base Color'].default_value=(*[v/12.92 if v<=.04045 else ((v+.055)/1.055)**2.4 for v in rgb],1);b.inputs['Roughness'].default_value=rough;b.inputs['Transmission Weight'].default_value=transmission;b.inputs['Metallic'].default_value=metal;b.inputs['IOR'].default_value=1.49;return m
glass=mat('Luminous neutral clear bottle glass','#ffffff',.024,1)
pipette_mat=mat('Luminous neutral clear pipette glass','#ffffff',.026,1)
silver=mat('Luminous mirror silver collar','#e8e8e8',.075,0,1)
rubber=mat('Luminous soft white dropper bulb','#f4eee8',.39)
def mesh(name,vertices,faces,material,parent):
 data=bpy.data.meshes.new(name);data.from_pydata(vertices,[],faces);data.update();obj=bpy.data.objects.new(name,data);bpy.context.collection.objects.link(obj);data.materials.append(material)
 if parent not in groups:groups[parent]=bpy.data.objects.new(parent,None);bpy.context.collection.objects.link(groups[parent])
 obj.parent=groups[parent]
 for face in data.polygons:face.use_smooth=abs(face.normal.z)<.999
 return obj

def ring(rx,ry,r,n=128):
 points=[]
 for q in range(4):
  cx=(rx-r)*(1 if q in (0,3) else -1);cy=(ry-r)*(1 if q<2 else -1)
  for i in range(n//4):
   a=q*math.pi/2+i/(n//4-1)*math.pi/2;points.append((cx+r*math.cos(a),cy+r*math.sin(a)))
 return points

def loft(name,profile,material,parent,n=128):
 vs=[];rings=[];fs=[]
 for z,rx,ry,r in profile:
  if rx==0:rings.append([len(vs)]);vs.append((0,0,z))
  else:rings.append(list(range(len(vs),len(vs)+n)));vs.extend((x,y,z) for x,y in ring(rx,ry,r,n))
 for a,b in zip(rings,rings[1:]):
  if len(a)==len(b)==1:continue
  for i in range(n):
   j=(i+1)%n;fs.append((a[0],b[j],b[i]) if len(a)==1 else (a[i],a[j],b[0]) if len(b)==1 else (a[i],a[j],b[j],b[i]))
 obj=mesh(name,vs,fs,material,parent);bm=bmesh.new();bm.from_mesh(obj.data)
 bmesh.ops.remove_doubles(bm,verts=list(bm.verts),dist=1e-6);bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces))
 assert all(e.is_manifold for e in bm.edges),name
 assert bm.calc_volume(signed=True)>0,name
 bm.to_mesh(obj.data);bm.free();obj.data.update();return obj
def lathe(name,profile,material,parent,n=128):return loft(name,[(z,r,r,r) for z,r in profile],material,parent,n)

# The wide, flat shoulder closes into a short neck hidden under the silver collar.
outer=[(0,0,0,0),(0,.440,.140,.032),(.006,.470,.170,.038),(.017,.488,.188,.044),(.035,.497,.197,.050),(.052,.500,.200,.055),(2.555,.500,.200,.055),(2.581,.497,.197,.055),(2.605,.488,.188,.055),(2.623,.470,.170,.055),(2.637,.444,.147,.057),(2.647,.350,.132,.071),(2.655,.217,.130,.115),(2.670,.143,.143,.143),(2.750,.143,.143,.143)]
inner=[(2.750,.104,.104,.104),(2.676,.104,.104,.104),(2.641,.126,.100,.100),(2.621,.247,.098,.066),(2.606,.377,.117,.041),(2.581,.439,.143,.040),(2.548,.456,.156,.040),(.164,.456,.156,.040),(.142,.445,.145,.040),(.128,.421,.121,.040),(.124,0,0,0)]
loft('Hollow slender flat Luminous glass bottle',outer+inner,glass,'Body')
lathe('Mirror silver hollow cylindrical collar',[(2.660,.282),(2.660,.294),(2.665,.305),(2.674,.310),(3.103,.310),(3.114,.306),(3.120,.294),(3.120,.127),(3.094,.127),(3.094,.281),(3.086,.286),(2.674,.286),(2.660,.282)],silver,'Closure')
bulb=[(3.087,.105),(3.087,.122),(3.118,.122),(3.120,.190),(3.133,.183),(3.152,.173),(3.178,.166),(3.205,.165),(3.485,.165)]
for i in range(1,33):
 a=i*math.pi/64;bulb.append((3.485+.165*math.sin(a),.165*math.cos(a) if i<32 else 0))
bulb.append((3.628,0))
for i in range(1,33):
 a=math.pi/2-i*math.pi/64;bulb.append((3.485+.143*math.sin(a),.143*math.cos(a)))
bulb.extend([(3.208,.143),(3.178,.146),(3.147,.156),(3.137,.105),(3.087,.105)])
lathe('Hollow white Luminous dropper bulb',bulb,rubber,'DropperBulb',160)
# User-requested near-bottom hollow pipette: lower the unchanged tip profile and lengthen only the straight barrel.
# Internal length and floor clearance are illustrative; no oil or hanging liquid drop is included.
lathe('Long hollow clear pipette without suspended formula',[(.220,.014),(.220,.020),(.234,.022),(.270,.031),(.300,.036),(3.214,.036),(3.230,.034),(3.230,.026),(3.214,.026),(.302,.026),(.275,.021),(.237,.014),(.220,.014)],pipette_mat,'Pipette',96)
for kind,parent,name in [('label','PaperLabel','Warm ivory unprinted paper label'),('print','LogoPrint','Complete Luminous Face Oil print')]:
 material=mat('Luminous warm cream paper substrate' if kind=='label' else 'Luminous complete dark lettering','#ffffff',.67)
 b=material.node_tree.nodes.get('Principled BSDF');b.inputs['Specular IOR Level'].default_value=.08 if kind=='label' else .02
 t=material.node_tree.nodes.new('ShaderNodeTexImage');t.image=bpy.data.images.load(str(OUT/(kind+'.png')));t.image.pack();material.node_tree.links.new(t.outputs['Color'],b.inputs['Base Color']);material.node_tree.links.new(t.outputs['Alpha'],b.inputs['Alpha']);material.surface_render_method='DITHERED'
 nx,ny=80,8;vs=[];fs=[]
 for j in range(ny+1):
  for i in range(nx+1):
   x=(i/nx-.5)*.98;edge=max(abs(x)-.445,0);y=-.145-math.sqrt(max(.055**2-edge**2,0))-(.0014 if kind=='label' else .0022)
   vs.append((x,y,.035+1.415*j/ny))
 for j in range(ny):
  for i in range(nx):a=j*(nx+1)+i;fs.append((a,a+1,a+nx+2,a+nx+1))
 obj=mesh(name,vs,fs,material,parent);uv=obj.data.uv_layers.new()
 for f in obj.data.polygons:
  for li in f.loop_indices:v=obj.data.loops[li].vertex_index;uv.data[li].uv=(v%(nx+1)/nx,v//(nx+1)/ny)
scale=2.9/3.65;pivots={'Body':0,'Closure':2.66,'DropperBulb':3.12,'Pipette':2.66,'PaperLabel':.7425,'LogoPrint':.7425}
assert set(groups)==set(pivots)
for name,group in groups.items():
 pivot=Vector((0,0,pivots[name]))
 for obj in group.children:obj.location-=pivot
 group.location=pivot*scale;group.scale=(scale,scale,scale)
bpy.context.view_layer.update();part_bounds={}
for name,group in groups.items():
 points=[obj.matrix_world@v.co for obj in group.children for v in obj.data.vertices];part_bounds[name]={'min':[min(p[i] for p in points) for i in range(3)],'max':[max(p[i] for p in points) for i in range(3)]}
assert abs(part_bounds['DropperBulb']['max'][2]-2.9)<1e-6
# Keep the visible dropper parts connected without changing their world transforms.
assembly=bpy.data.objects.new('DropperAssembly',None);bpy.context.collection.objects.link(assembly)
for child in ('Closure','DropperBulb','Pipette'):groups[child].parent=assembly
part_bounds['DropperAssembly']={'min':[min(part_bounds[child]['min'][i] for child in ('Closure','DropperBulb','Pipette')) for i in range(3)],'max':[max(part_bounds[child]['max'][i] for child in ('Closure','DropperBulb','Pipette')) for i in range(3)]}
groups={name:groups[name] for name in ('Body','PaperLabel','LogoPrint')}
groups['DropperAssembly']=assembly
bpy.ops.object.select_all(action='SELECT')
bpy.ops.export_scene.gltf(filepath=str(CLIENT/'packaging-assets/poster-058.glb'),export_format='GLB',use_selection=True,export_apply=True,export_yup=True,export_extras=True)
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'poster-058.blend'))
info={'id':'poster-058','components':list(groups),'height':2.9,'nominalHeight':2.9,'actualHeight':part_bounds['DropperBulb']['max'][2],'width':scale,'depth':.4*scale,'closedHeightToWidth':3.65,'glassVisibleHeightToWidth':2.66,'glassNeckTopToWidth':2.75,'glassInnerFloorToWidth':.124,'closureDiameterToWidth':.62,'closureHeightToWidth':.46,'bulbMainDiameterToWidth':.33,'bulbRootDiameterToWidth':.38,'bulbVisibleHeightToWidth':.53,'pipetteBottomToWidth':.22,'pipetteTopToWidth':3.23,'pipetteOuterDiameterToWidth':.072,'pipetteInnerDiameterToWidth':.052,'labelWidthToBodyWidth':.98,'labelHeightToBodyWidth':1.415,'labelBottomToWidth':.035,'labelCentreHeightToWidth':.7425,'labelCurve':'Plane across the broad front; only outer .045W on each side follows the .055W glass corner, with .0014W surface clearance','pivotsHeightToWidth':pivots,'componentBoundsBlenderXYZ':part_bounds,'illustrativeDimensions':True,'containsFormula':False,'reference':'../../mobile-client-preview/assets/posters/poster-058.webp','featuredReference':'featured-assets/poster-058.png','editableArtwork':['label.svg','print.svg'],'separateLabelAndPrint':True,'printIncludes':['liaose','LUMINOUS','FACE OIL','warm separator rule','50 ml'],'hiddenStructure':'Neck, collar connection, wall thickness and bulb air path are illustrative; body depth cannot be measured exactly from one poster. The existing hollow pipette is extended near the inner floor at the user request; the retained tip shape, tube diameter, upper connection and illustrative floor clearance are not manufacturing specifications. No oil or suspended liquid drop is included.','material':'Neutral empty glass, mirror silver metal collar, opaque soft white hollow bulb, warm ivory paper','assemblyChildren':{'DropperAssembly':['Closure','DropperBulb','Pipette']},'completeDropperLift':2.4,'camera':{'closedCenter':1.45,'openCenter':2.45,'closedHeight':4.2,'openHeight':6.8,'closedWidth':3.8,'openWidth':5.2,'openCenterX':-1.6},'revision':'near-bottom-complete-dropper-local-review-20261027','generator':'build_luminous_face_oil.py'}
(OUT/'model-info.json').write_text(json.dumps(info,indent=2)+'\n')
print('Luminous Face Oil rebuilt:',len(groups),'independent groups')
