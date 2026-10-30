"""Oil-Infused Body Cream 061: two reference-height frosted pump bottles, without cartons."""
import bpy,bmesh,math,json,subprocess,xml.etree.ElementTree as ET
from pathlib import Path
from mathutils import Vector
BASE=Path(__file__).resolve().parent;CLIENT=BASE.parents[1];OUT=BASE/'poster-061';OUT.mkdir(exist_ok=True)
logo=next(e.attrib['d'] for e in ET.parse(OUT/'print.svg').getroot().iter() if e.tag.endswith('path'))
label='<svg xmlns="http://www.w3.org/2000/svg" width="780" height="740" viewBox="0 0 780 740"><rect x="3" y="3" width="774" height="734" rx="24" fill="#fffdf7" fill-opacity=".14" stroke="#a89777" stroke-opacity=".5" stroke-width="4"/></svg>'
printing=f'''<svg xmlns="http://www.w3.org/2000/svg" width="780" height="740" viewBox="0 0 780 740"><svg x="80" y="99" width="616" height="283" viewBox="0 0 340 125" preserveAspectRatio="none"><path d="{logo}" fill="#211e18"/></svg><g fill="#211e18" text-anchor="middle" font-family="Helvetica Neue,Arial,sans-serif"><text x="0" transform="translate(390,0) scale(.87,1)" y="523" font-size="63" letter-spacing="3">OIL-INFUSED</text><text x="0" transform="translate(390,0) scale(.87,1)" y="593" font-size="63" letter-spacing="6">BODY CREAM</text></g></svg>'''
(OUT/'label.svg').write_text(label);(OUT/'print.svg').write_text(printing)
node='/Users/icecream/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/bin/node'
subprocess.run([node,'--input-type=module','-e',"""import sharp from '/Users/icecream/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/sharp/dist/index.mjs';import fs from 'node:fs/promises';for(const kind of ['label','print'])await sharp(await fs.readFile(process.argv[1]+'/'+kind+'.svg'),{density:144}).png().toFile(process.argv[1]+'/'+kind+'.png');""",str(OUT)],check=True)
bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False);groups={}
def mat(name,color,rough,transmission=0):
 m=bpy.data.materials.new(name);m.use_nodes=True;b=m.node_tree.nodes.get('Principled BSDF');rgb=[int(color[i:i+2],16)/255 for i in (1,3,5)];b.inputs['Base Color'].default_value=(*[v/12.92 if v<=.04045 else ((v+.055)/1.055)**2.4 for v in rgb],1);b.inputs['Roughness'].default_value=rough;b.inputs['Transmission Weight'].default_value=transmission;b.inputs['IOR'].default_value=1.48;return m
glass=mat('Body Cream frosted ivory glass','#f5f0e5',.39,.62)
tube_material=mat('Body Cream clear plastic dip tube','#ffffff',.06,1)
black=mat('Body Cream satin black pump polymer','#0b0c0a',.23)
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

for bottle,h,dx,dy in [('Smaller',1.40,-.43,-.28),('Taller',1.52,.43,.28)]:
 before=set(bpy.data.objects)
 outer=[(0,0),(0,.235),(.012,.310),(.042,.383),(.088,.440),(.145,.477),(.210,.496),(.270,.500),(h-.072,.500),(h-.043,.496),(h-.020,.484),(h,.455),(h+.012,.390),(h+.024,.290),(h+.036,.172),(h+.070,.160)]
 inner=[(h+.070,.111),(h+.033,.111),(h-.005,.140),(h-.024,.290),(h-.047,.410),(h-.074,.449),(h-.10,.458),(.289,.458),(.232,.452),(.181,.433),(.141,.396),(.118,.337),(.110,.251),(.110,0)]
 lathe(bottle+' hollow frosted round-bottom bottle',outer+inner,glass,'Body',160)
 lathe(bottle+' hollow black pump collar',[(h-.03,.200),(h-.03,.218),(h-.022,.229),(h-.010,.230),(h+.250,.230),(h+.264,.224),(h+.270,.211),(h+.270,.082),(h+.244,.082),(h+.244,.199),(h+.232,.205),(h-.017,.205),(h-.03,.200)],black,'Closure')
 lathe(bottle+' visible black rising pump stem',[(h-.055,.028),(h-.055,.070),(h-.025,.078),(h+.230,.078),(h+.255,.105),(h+.495,.105),(h+.515,.091),(h+.560,.071),(h+.560,.028),(h-.055,.028)],black,'PumpStem')
 # The clear tube stays fitted inside the pump stem and stops above the glass floor.
 lathe(bottle+' hollow clear dip tube',[(.14,.019),(.14,.028),(h-.065,.028),(h-.060,.0275),(h-.035,.0275),(h-.035,.019),(.14,.019)],tube_material,'PumpStem',96)
 lathe(bottle+' cylindrical hollow press head',[(h+.480,.071),(h+.480,.113),(h+.488,.128),(h+.503,.133),(h+.775,.133),(h+.790,.125),(h+.800,.106),(h+.800,0),(h+.778,0),(h+.778,.108),(h+.513,.108),(h+.505,.071),(h+.480,.071)],black,'Actuator')
 # Flat oval spout curves gently down and keeps a real open dispensing end.
 n,m=40,24;vs=[];rs=[]
 A=Vector((.108,0,h+.714));B=Vector((.236,0,h+.723));C=Vector((.344,0,h+.706));D=Vector((.442,0,h+.650))
 for layer in [0,1]:
  rings=[]
  for i in range(n+1):
   t=i/n;u=1-t;p=u**3*A+3*u*u*t*B+3*u*t*t*C+t**3*D;tangent=(3*u*u*(B-A)+6*u*t*(C-B)+3*t*t*(D-C)).normalized();e1=Vector((0,1,0));e2=tangent.cross(e1).normalized();rings.append(list(range(len(vs),len(vs)+m)))
   for j in range(m):
    a=j*math.tau/m;vs.append(tuple(p+(math.cos(a)*(.043 if layer==0 else .032))*e1+(math.sin(a)*(.025 if layer==0 else .015))*e2))
  rs.append(rings)
 fs=[]
 for i in range(n):
  for j in range(m):
   k=(j+1)%m;fs.extend([(rs[0][i][j],rs[0][i][k],rs[0][i+1][k],rs[0][i+1][j]),(rs[1][i][k],rs[1][i][j],rs[1][i+1][j],rs[1][i+1][k])])
 for j in range(m):
  k=(j+1)%m;fs.extend([(rs[0][0][k],rs[0][0][j],rs[1][0][j],rs[1][0][k]),(rs[0][-1][j],rs[0][-1][k],rs[1][-1][k],rs[1][-1][j])])
 obj=mesh(bottle+' curved hollow oval pump spout',vs,fs,black,'Actuator');bm=bmesh.new();bm.from_mesh(obj.data);bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));assert all(e.is_manifold for e in bm.edges);assert bm.calc_volume(signed=True)>0;bm.to_mesh(obj.data);bm.free()
 for kind,parent,name in [('label','PaperLabel',' transparent unprinted film'),('print','LogoPrint',' complete dark body cream lettering')]:
  material=mat('Body Cream transparent label carrier' if kind=='label' else 'Body Cream complete dark print','#ffffff',.24 if kind=='label' else .66)
  b=material.node_tree.nodes.get('Principled BSDF');b.inputs['Specular IOR Level'].default_value=.3 if kind=='label' else .02;t=material.node_tree.nodes.new('ShaderNodeTexImage');t.image=bpy.data.images.load(str(OUT/(kind+'.png')));t.image.pack();material.node_tree.links.new(t.outputs['Color'],b.inputs['Base Color']);material.node_tree.links.new(t.outputs['Alpha'],b.inputs['Alpha']);material.surface_render_method='DITHERED'
  nx,ny=80,12;vs=[];fs=[];zshift=.08 if bottle=='Taller' else 0
  for j in range(ny+1):
   for i in range(nx+1):
    x=(i/nx-.5)*.78;y=-math.sqrt(.25-x*x)-(.0014 if kind=='label' else .0022);vs.append((x,y,.37+zshift+.74*j/ny))
  for j in range(ny):
   for i in range(nx):a=j*(nx+1)+i;fs.append((a,a+1,a+nx+2,a+nx+1))
  obj=mesh(bottle+name,vs,fs,material,parent);uv=obj.data.uv_layers.new()
  for f in obj.data.polygons:
   for li in f.loop_indices:v=obj.data.loops[li].vertex_index;uv.data[li].uv=(v%(nx+1)/nx,v//(nx+1)/ny)
 for obj in set(bpy.data.objects)-before:
  if obj.type=='MESH':
   for v in obj.data.vertices:v.co.x+=dx;v.co.y+=dy
scale=2.9/2.32;pivots={'Body':0,'Closure':1.43,'PumpStem':1.70,'Actuator':1.94,'PaperLabel':.78,'LogoPrint':.78}
assert set(groups)==set(pivots)
for name,g in groups.items():
 pivot=Vector((0,0,pivots[name]))
 for obj in g.children:obj.location-=pivot
 g.location=pivot*scale;g.scale=(scale,scale,scale)
bpy.context.view_layer.update();bounds={}
for name,g in groups.items():
 pts=[o.matrix_world@v.co for o in g.children for v in o.data.vertices];bounds[name]={'min':[min(p[i] for p in pts) for i in range(3)],'max':[max(p[i] for p in pts) for i in range(3)]}
assert abs(bounds['Actuator']['max'][2]-2.9)<1e-6
assembly=bpy.data.objects.new('PumpAssembly',None);bpy.context.collection.objects.link(assembly)
for child in ('Closure','PumpStem','Actuator'):groups[child].parent=assembly
bounds['PumpAssembly']={'min':[min(bounds[child]['min'][i] for child in ('Closure','PumpStem','Actuator')) for i in range(3)],'max':[max(bounds[child]['max'][i] for child in ('Closure','PumpStem','Actuator')) for i in range(3)]}
for child in ('Closure','PumpStem','Actuator'):del groups[child]
groups['PumpAssembly']=assembly
bpy.ops.object.select_all(action='SELECT');bpy.ops.export_scene.gltf(filepath=str(CLIENT/'packaging-assets/poster-061.glb'),export_format='GLB',use_selection=True,export_apply=True,export_yup=True,export_extras=True);bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'poster-061.blend'))
info={'id':'poster-061','components':list(groups),'bottleCount':2,'height':2.9,'tallerHeight':2.9,'smallerHeight':2.2*scale,'singleBottleDiameter':scale,'pairWidth':1.86*scale,'pairDepth':1.56*scale,'tallerHeightToDiameter':2.32,'smallerHeightToDiameter':2.20,'tallerBodyHeightToDiameter':1.52,'smallerBodyHeightToDiameter':1.4,'bottleCentersToDiameter':[[-.43,-.28],[.43,.28]],'bottleCentreDistanceToDiameter':math.sqrt(.86**2+.56**2),'glassInnerFloorToDiameter':.11,'closureDiameterToBottle':.46,'closureHeightToDiameter':.30,'visibleStemDiameterToBottle':.21,'headDiameterToBottle':.266,'headTotalSpanToDiameter':.575,'spoutCrossSectionToDiameter':[.086,.05],'labelWidthToDiameter':.78,'labelHeightToDiameter':.74,'pivotsHeightToWidth':pivots,'componentBoundsBlenderXYZ':bounds,'illustrativeDimensions':True,'containsFormula':False,'reference':'../../mobile-client-preview/assets/posters/poster-061.webp','editableArtwork':['label.svg','print.svg'],'separateLabelAndPrint':True,'printIncludes':['liaose','OIL-INFUSED','BODY CREAM'],'hiddenStructure':'The photograph shows two similar diameters with different body heights. Bottles stand on a common ground here; scene stones and cartons are excluded. Wall thickness, pump internal connector and open spout construction are illustrative, not a manufacturing design. The added hollow transparent dip tubes follow the requested complete pump assembly and stop above each inner floor. Their hidden bore and connection are illustrative; no formula is added. Original direct printing is represented by a transparent unprinted carrier and separate full print.','material':'Ivory frosted empty glass with opaque satin black pump parts','revision':'complete-pump-assembly-review-20261030','nestedAssembly':{'PumpAssembly':['Closure','PumpStem','Actuator']},'dipTubeOuterDiameterToBody':.056,'dipTubeInnerDiameterToBody':.038,'dipTubeTipToBodyDiameter':.14,'generator':'build_oil_infused_body_cream.py'}
(OUT/'model-info.json').write_text(json.dumps(info,indent=2)+'\n');print('Oil Infused Body Cream rebuilt:',len(groups),'independent groups')
