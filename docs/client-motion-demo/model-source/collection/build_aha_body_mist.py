"""AHA Body Mist 060: cylindrical empty bottle, atomizer and brushed silver label."""
import bpy,bmesh,math,json,subprocess,xml.etree.ElementTree as ET
from pathlib import Path
from mathutils import Vector
import numpy as np
BASE=Path(__file__).resolve().parent;CLIENT=BASE.parents[1];OUT=BASE/'poster-060';OUT.mkdir(exist_ok=True)
logo=next(e.attrib['d'] for e in ET.parse(OUT/'print.svg').getroot().iter() if e.tag.endswith('path'))
rng=np.random.default_rng(60);w,h=1024,1482
row=rng.normal(0,.009,(h,1));noise=rng.normal(0,.003,(h,w));value=np.clip(.74+row+noise,.68,.80)
rgba=np.dstack([value,value,value,np.ones((h,w))]).astype(np.float32)
im=bpy.data.images.new('Original brushed silver substrate',width=w,height=h,alpha=True);im.pixels.foreach_set(rgba[::-1].ravel());im.filepath_raw=str(OUT/'brushed-silver.png');im.file_format='PNG';im.save()
label='<svg xmlns="http://www.w3.org/2000/svg" width="760" height="1100" viewBox="0 0 760 1100"><defs><clipPath id="edge"><rect width="760" height="1100" rx="7"/></clipPath></defs><image href="brushed-silver.png" width="760" height="1100" preserveAspectRatio="none" clip-path="url(#edge)"/></svg>'
printing=f'''<svg xmlns="http://www.w3.org/2000/svg" width="760" height="1100" viewBox="0 0 760 1100"><svg x="120" y="216" width="524" height="226" viewBox="0 0 340 125" preserveAspectRatio="none"><path d="{logo}" fill="#1d1b18"/></svg><g fill="#1d1b18" text-anchor="middle" font-family="Helvetica Neue,Arial,sans-serif"><text x="380" y="608" font-size="78" letter-spacing="5">AHA</text><text x="380" y="711" font-size="78" letter-spacing="9">BODY MIST</text><path d="M332 801H428" fill="none" stroke="#34302a" stroke-width="3"/><text x="380" y="945" font-size="78" letter-spacing="9">160 ml</text></g></svg>'''
(OUT/'label.svg').write_text(label);(OUT/'print.svg').write_text(printing)
node='/Users/icecream/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/bin/node'
subprocess.run([node,'--input-type=module','-e',"""import sharp from '/Users/icecream/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/sharp/dist/index.mjs';import fs from 'node:fs/promises';const d=process.argv[1];for(const kind of ['label','print']){let s=await fs.readFile(d+'/'+kind+'.svg','utf8');s=s.replace('brushed-silver.png','data:image/png;base64,'+(await fs.readFile(d+'/brushed-silver.png')).toString('base64'));await sharp(Buffer.from(s),{density:kind==='label'?96:144}).png(kind==='label'?{palette:true,colours:64}:{}).toFile(d+'/'+kind+'.png');}""",str(OUT)],check=True)
bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False);groups={}
def mat(name,color,rough,transmission=0,metal=0):
 m=bpy.data.materials.new(name);m.use_nodes=True;b=m.node_tree.nodes.get('Principled BSDF');rgb=[int(color[i:i+2],16)/255 for i in (1,3,5)];b.inputs['Base Color'].default_value=(*[v/12.92 if v<=.04045 else ((v+.055)/1.055)**2.4 for v in rgb],1);b.inputs['Roughness'].default_value=rough;b.inputs['Transmission Weight'].default_value=transmission;b.inputs['Metallic'].default_value=metal;b.inputs['IOR'].default_value=1.49;return m
glass=mat('AHA neutral clear cylindrical glass','#ffffff',.024,1)
tube_mat=mat('AHA clear pipette dip tube','#ffffff',.04,1)
black=mat('AHA polished black atomizer polymer','#090909',.13)
white=mat('AHA ivory spray outlet and connector','#eeebe4',.38)
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

lathe('Hollow cylindrical glass with rounded shoulder and thick base',[(0,0),(0,.399),(.006,.447),(.020,.478),(.044,.494),(.071,.500),(2.438,.500),(2.490,.494),(2.548,.479),(2.606,.454),(2.663,.416),(2.711,.370),(2.751,.312),(2.779,.252),(2.796,.191),(2.809,.169),(2.900,.169),(2.900,.118),(2.820,.118),(2.778,.137),(2.754,.204),(2.723,.267),(2.685,.319),(2.640,.363),(2.590,.398),(2.534,.424),(2.474,.441),(2.429,.448),(.235,.448),(.207,.434),(.187,.406),(.180,0)],glass,'Body',192)
lathe('Hollow glossy black atomizer collar',[(2.800,.222),(2.800,.242),(2.808,.253),(2.820,.255),(3.219,.255),(3.233,.250),(3.240,.237),(3.240,.076),(3.214,.076),(3.214,.225),(3.203,.229),(2.817,.229),(2.800,.222)],black,'Closure')
lathe('Opaque illustrative white pump connector',[(2.795,.025),(2.795,.055),(2.806,.066),(2.878,.066),(2.892,.055),(3.287,.055),(3.300,.050),(3.300,.025),(2.795,.025)],white,'PumpStem')
lathe('Black cylindrical spray actuator',[(3.210,.060),(3.210,.144),(3.216,.157),(3.228,.160),(3.510,.160),(3.522,.156),(3.530,.143),(3.530,0),(3.507,0),(3.507,.130),(3.239,.130),(3.231,.060),(3.210,.060)],black,'Actuator')
# White outlet is a true shallow annular insert; its dark centre remains recessed.
nozzle=lathe('White circular recessed spray nozzle',[(0,.007),(0,.036),(.002,.041),(.006,.041),(.009,.036),(.009,.007),(0,.007)],white,'Actuator',96)
for v in nozzle.data.vertices:
 x,y,z=v.co;v.co=(x,-.160-z,3.447+y)
# Hollow suction tube follows the reference bend towards the lower right of the bottle.
n,m=100,16;vs=[];outer=[];inner=[]
for i in range(n+1):
 t=i/n;u=1-t;A=Vector((0,0,2.84));B=Vector((-.12,0,1.72));C=Vector((-.10,0,.65));D=Vector((.29,0,.212))
 p=u**3*A+3*u*u*t*B+3*u*t*t*C+t**3*D;tangent=(3*u*u*(B-A)+6*u*t*(C-B)+3*t*t*(D-C)).normalized();e1=Vector((0,1,0));e2=tangent.cross(e1).normalized()
 for radius,rs in [(.018,outer),(.012,inner)]:
  rs.append(list(range(len(vs),len(vs)+m)))
  for j in range(m):a=j*math.tau/m;vs.append(tuple(p+radius*(math.cos(a)*e1+math.sin(a)*e2)))
fs=[]
for i in range(n):
 for j in range(m):k=(j+1)%m;fs.extend([(outer[i][j],outer[i][k],outer[i+1][k],outer[i+1][j]),(inner[i][k],inner[i][j],inner[i+1][j],inner[i+1][k])])
for j in range(m):
 k=(j+1)%m;fs.extend([(outer[0][k],outer[0][j],inner[0][j],inner[0][k]),(outer[-1][j],outer[-1][k],inner[-1][k],inner[-1][j])])
obj=mesh('Curved hollow clear suction tube',vs,fs,tube_mat,'PumpStem');bm=bmesh.new();bm.from_mesh(obj.data);bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));assert all(e.is_manifold for e in bm.edges);assert bm.calc_volume(signed=True)>0;bm.to_mesh(obj.data);bm.free()
for kind,parent,name in [('label','PaperLabel','Brushed silver unprinted label substrate'),('print','LogoPrint','Complete AHA Body Mist print')]:
 material=mat('AHA brushed silver label foil' if kind=='label' else 'AHA complete dark lettering','#ffffff',.30 if kind=='label' else .68,0,1 if kind=='label' else 0)
 b=material.node_tree.nodes.get('Principled BSDF');b.inputs['Specular IOR Level'].default_value=.5 if kind=='label' else .02
 t=material.node_tree.nodes.new('ShaderNodeTexImage');t.image=bpy.data.images.load(str(OUT/(kind+'.png')));t.image.pack();material.node_tree.links.new(t.outputs['Color'],b.inputs['Base Color']);material.node_tree.links.new(t.outputs['Alpha'],b.inputs['Alpha']);material.surface_render_method='DITHERED'
 nx,ny=80,16;vs=[];fs=[]
 for j in range(ny+1):
  for i in range(nx+1):
   x=(i/nx-.5)*.76;y=-math.sqrt(.25-x*x)-(.0016 if kind=='label' else .0026);vs.append((x,y,1.28+1.10*j/ny))
 for j in range(ny):
  for i in range(nx):a=j*(nx+1)+i;fs.append((a,a+1,a+nx+2,a+nx+1))
 obj=mesh(name,vs,fs,material,parent);uv=obj.data.uv_layers.new()
 for f in obj.data.polygons:
  for li in f.loop_indices:v=obj.data.loops[li].vertex_index;uv.data[li].uv=(v%(nx+1)/nx,v//(nx+1)/ny)
scale=2.9/3.53;pivots={'Body':0,'Closure':2.80,'PumpStem':2.8,'Actuator':3.21,'PaperLabel':1.83,'LogoPrint':1.83}
assert set(groups)==set(pivots)
for name,g in groups.items():
 pivot=Vector((0,0,pivots[name]))
 for o in g.children:o.location-=pivot
 g.location=pivot*scale;g.scale=(scale,scale,scale)
bpy.context.view_layer.update();part_bounds={}
for name,g in groups.items():
 pts=[o.matrix_world@v.co for o in g.children for v in o.data.vertices];part_bounds[name]={'min':[min(p[i] for p in pts) for i in range(3)],'max':[max(p[i] for p in pts) for i in range(3)]}
assert abs(part_bounds['Actuator']['max'][2]-2.9)<1e-6
assembly=bpy.data.objects.new('PumpAssembly',None);bpy.context.collection.objects.link(assembly)
for child in ('Closure','PumpStem','Actuator'):groups[child].parent=assembly
part_bounds['PumpAssembly']={'min':[min(part_bounds[child]['min'][i] for child in ('Closure','PumpStem','Actuator')) for i in range(3)],'max':[max(part_bounds[child]['max'][i] for child in ('Closure','PumpStem','Actuator')) for i in range(3)]}
for child in ('Closure','PumpStem','Actuator'):del groups[child]
groups['PumpAssembly']=assembly
bpy.ops.object.select_all(action='SELECT');bpy.ops.export_scene.gltf(filepath=str(CLIENT/'packaging-assets/poster-060.glb'),export_format='GLB',use_selection=True,export_apply=True,export_yup=True,export_extras=True);bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'poster-060.blend'))
info={'id':'poster-060','components':list(groups),'height':2.9,'width':scale,'depth':scale,'closedHeightToDiameter':3.53,'glassVisibleHeightToDiameter':2.80,'glassNeckTopToDiameter':2.90,'glassInnerFloorToDiameter':.18,'closureDiameterToBody':.51,'closureHeightToDiameter':.44,'actuatorDiameterToBody':.32,'actuatorVisibleHeightToDiameter':.29,'dipTubeOuterDiameterToBody':.036,'dipTubeInnerDiameterToBody':.024,'dipTubeLowestCentreToDiameter':.212,'labelWidthToDiameter':.76,'labelHeightToDiameter':1.10,'labelBottomToDiameter':1.28,'labelCurve':'Both substrate and text follow the cylindrical front with distinct surface offsets','pivotsHeightToWidth':pivots,'componentBoundsBlenderXYZ':part_bounds,'illustrativeDimensions':True,'containsFormula':False,'reference':'../../mobile-client-preview/assets/posters/poster-060.webp','editableArtwork':['label.svg','print.svg'],'proceduralTextures':['brushed-silver.png'],'separateLabelAndPrint':True,'printIncludes':['liaose','AHA','BODY MIST','short separator rule','160 ml'],'hiddenStructure':'Pump connector, internal tube bend and wall dimensions are illustrative. No fluid or mist is modeled. The curved flexible tube is shown as a rigid display shape; the lift is illustrative rather than a validated assembly path. The visible spray insert is a shallow annular piece, not a functional engineered nozzle.','material':'Neutral clear bottle, black opaque atomizer, silver brushed foil label with independent dark printing','revision':'complete-spray-assembly-review-20261030','nestedAssembly':{'PumpAssembly':['Closure','PumpStem','Actuator']},'generator':'build_aha_body_mist.py'}
(OUT/'model-info.json').write_text(json.dumps(info,indent=2)+'\n');print('AHA Body Mist rebuilt:',len(groups),'independent groups')
