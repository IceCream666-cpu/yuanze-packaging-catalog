"""B5 Serum 057: complete dropper and fitted bottle/base, calibrated to the full poster."""
import bpy, bmesh, math, json, subprocess, xml.etree.ElementTree as ET
from pathlib import Path
from mathutils import Vector

BASE=Path(__file__).resolve().parent;CLIENT=BASE.parents[1];OUT=BASE/'poster-057';OUT.mkdir(exist_ok=True)
logo=next(e.attrib['d'] for e in ET.parse(OUT/'print.svg').getroot().iter() if e.tag.endswith('path'))
label='<svg xmlns="http://www.w3.org/2000/svg" width="720" height="660" viewBox="0 0 720 660"><rect x="3" y="3" width="714" height="654" rx="28" fill="#fffdf7" fill-opacity=".14" stroke="#d9c8ca" stroke-opacity=".5" stroke-width="4"/></svg>'
printing=f'''<svg xmlns="http://www.w3.org/2000/svg" width="720" height="660" viewBox="0 0 720 660"><svg x="99.75" y="129" width="524" height="214" viewBox="0 0 340 125" preserveAspectRatio="none"><path d="{logo}" fill="#fffaf6"/></svg><g text-anchor="middle" font-family="Helvetica Neue,Arial,sans-serif" fill="#fffaf6"><text x="360" y="460" font-size="62" letter-spacing="3">B5 SERUM</text><text x="360" y="581.5" font-size="56">30 ml</text></g></svg>'''
(OUT/'label.svg').write_text(label);(OUT/'print.svg').write_text(printing)
(OUT/'base-logo.svg').write_text(f'<svg xmlns="http://www.w3.org/2000/svg" width="340" height="125" viewBox="0 0 340 125"><path d="{logo}" fill="#d4c6bd"/></svg>')
node='/Users/icecream/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/bin/node'
subprocess.run([node,'--input-type=module','-e',"""import sharp from '/Users/icecream/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/sharp/dist/index.mjs';import fs from 'node:fs/promises';for(const kind of ['label','print','base-logo'])await sharp(await fs.readFile(process.argv[1]+'/'+kind+'.svg'),{density:144}).png().toFile(process.argv[1]+'/'+kind+'.png');""",str(OUT)],check=True)
bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)
groups={}
def mat(name,color,rough,transmission=0):
 m=bpy.data.materials.new(name);m.use_nodes=True;b=m.node_tree.nodes.get('Principled BSDF');rgb=[int(color[i:i+2],16)/255 for i in (1,3,5)]
 b.inputs['Base Color'].default_value=(*[v/12.92 if v<=.04045 else ((v+.055)/1.055)**2.4 for v in rgb],1)
 b.inputs['Roughness'].default_value=rough;b.inputs['Transmission Weight'].default_value=transmission;b.inputs['IOR'].default_value=1.49
 return m
glass=mat('B5 neutral clear bottle glass','#ffffff',.024,1)
pipette_mat=mat('B5 neutral clear pipette glass','#ffffff',.028,1)
base=mat('B5 soft matte white base','#eee8e3',.55)
cap=mat('B5 satin white closure','#f3eee9',.30)
rubber=mat('B5 soft white dropper bulb','#f0ece7',.42)
emboss=mat('B5 warm white raised base logo','#d4c6bd',.36)

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
 bmesh.ops.remove_doubles(bm,verts=list(bm.verts),dist=1e-7);bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces))
 assert all(e.is_manifold for e in bm.edges),name
 assert bm.calc_volume(signed=True)>0,name
 bm.to_mesh(obj.data);bm.free();obj.data.update();return obj
def lathe(name,profile,material,parent,n=128):return loft(name,[(z,r,r,r) for z,r in profile],material,parent,n)

# Concealed bottle heel is slightly narrower than the visible body, leaving a real cup clearance.
outer=[(.055,0,0,0),(.055,.419,.131,.034),(.061,.445,.157,.036),(.078,.462,.174,.038),(.100,.466,.177,.039),(.456,.466,.177,.039),(.478,.467,.178,.039),(.494,.472,.184,.042),(.508,.480,.192,.045),(.526,.487,.198,.047),(.547,.49,.20,.049),(1.225,.49,.20,.049),(1.249,.486,.197,.049),(1.272,.475,.188,.049),(1.291,.454,.173,.050),(1.304,.425,.151,.054),(1.314,.347,.132,.068),(1.323,.210,.120,.095),(1.330,.128,.120,.118),(1.339,.125,.125,.125),(1.360,.125,.125,.125)]
inner=[(1.360,.089,.089,.089),(1.336,.089,.089,.089),(1.307,.105,.092,.090),(1.295,.210,.092,.074),(1.283,.333,.100,.051),(1.271,.415,.133,.041),(1.249,.443,.151,.039),(1.220,.451,.162,.039),(.548,.451,.162,.039),(.496,.430,.140,.039),(.158,.430,.140,.039),(.132,.420,.130,.040),(.115,.397,.107,.040),(.110,0,0,0)]
loft('Hollow rounded flat B5 glass bottle',outer+inner,glass,'Body')

# Open white cup with a sealed floor. The side-wall gap is retained even at the seating lip.
cup=[(0,0,0,0),(0,.456,.166,.035),(.005,.480,.190,.038),(.018,.495,.205,.040),(.034,.5,.21,.042),(.474,.5,.21,.042),(.489,.498,.208,.042),(.498,.492,.202,.042),(.500,.486,.196,.042),(.500,.480,.190,.041),(.492,.476,.186,.040),(.480,.474,.184,.039),(.066,.474,.184,.039),(.052,.466,.176,.039),(.045,.447,.157,.039),(.045,0,0,0)]
loft('Hollow matte white base cup with sealed floor',cup,base,'Base')
lathe('Smooth white open screw collar',[(1.35,.201),(1.35,.208),(1.354,.220),(1.362,.225),(1.732,.225),(1.745,.222),(1.75,.211),(1.75,.093),(1.724,.093),(1.724,.196),(1.716,.200),(1.365,.200),(1.35,.201)],cap,'Closure')

# A closed rubber dome and open lower bore make a bulb, not a solid capsule.
bulb=[(1.720,.069),(1.720,.087),(1.742,.087),(1.750,.140),(1.762,.135),(1.780,.124),(1.802,.114),(1.825,.110),(2.030,.110)]
for i in range(1,33):
 a=i*math.pi/64;bulb.append((2.030+.110*math.sin(a),.110*math.cos(a) if i<32 else 0))
bulb.append((2.121,0))
for i in range(1,33):
 a=math.pi/2-i*math.pi/64;bulb.append((2.030+.091*math.sin(a),.091*math.cos(a)))
bulb.extend([(1.827,.091),(1.794,.096),(1.765,.106),(1.755,.069),(1.720,.069)])
lathe('Hollow white elastomer dropper bulb',bulb,rubber,'DropperBulb',192)

# The thin tube is open at both ends and has a rounded, narrowed dispensing tip.
lathe('Hollow clear pipette with open tapered tip',[(.170,.010),(.170,.014),(.178,.016),(.198,.018),(.235,.025),(.270,.029),(1.806,.029),(1.820,.027),(1.820,.021),(1.805,.021),(.273,.021),(.240,.018),(.203,.011),(.179,.010),(.170,.010)],pipette_mat,'Pipette',96)

for kind,parent,name in [('label','PaperLabel','Transparent unprinted B5 label film'),('print','LogoPrint','Complete white B5 bottle printing')]:
 material=mat('B5 clear label film' if kind=='label' else 'B5 complete warm white bottle print','#ffffff',.24 if kind=='label' else .68)
 b=material.node_tree.nodes.get('Principled BSDF');b.inputs['Specular IOR Level'].default_value=.3 if kind=='label' else .015
 tex=material.node_tree.nodes.new('ShaderNodeTexImage');tex.image=bpy.data.images.load(str(OUT/(kind+'.png')));tex.image.pack();material.node_tree.links.new(tex.outputs['Color'],b.inputs['Base Color']);material.node_tree.links.new(tex.outputs['Alpha'],b.inputs['Alpha']);material.surface_render_method='DITHERED'
 y=-.2014 if kind=='label' else -.2022
 obj=mesh(name,[(-.36,y,.545),(.36,y,.545),(.36,y,1.205),(-.36,y,1.205)],[(0,1,2,3)],material,parent)
 uv=obj.data.uv_layers.new()
 for i,p in enumerate([(0,0),(1,0),(1,1),(0,1)]):uv.data[i].uv=p

# Real shallow relief follows the same approved brand path; the base itself stays unlettered.
bpy.ops.preferences.addon_enable(module='io_curve_svg')
before=set(bpy.data.objects);bpy.ops.import_curve.svg(filepath=str(OUT/'base-logo.svg'))
imported=[o for o in bpy.data.objects if o not in before and o.type=='CURVE']
assert len(imported)==1,'The wordmark must import as one compound curve'
obj=imported[0];obj.data.dimensions='2D';obj.data.fill_mode='BOTH';obj.data.extrude=.00015;obj.data.bevel_depth=.000035;obj.data.bevel_resolution=2;obj.data.resolution_u=8
bpy.ops.object.select_all(action='DESELECT');obj.select_set(True);bpy.context.view_layer.objects.active=obj;bpy.ops.object.convert(target='MESH');obj=bpy.context.object
bpy.ops.object.transform_apply(location=True,rotation=True,scale=True)
coords=[v.co.copy() for v in obj.data.vertices];mins=[min(p[i] for p in coords) for i in range(3)];maxs=[max(p[i] for p in coords) for i in range(3)]
for v,p in zip(obj.data.vertices,coords):
 v.co=((p.x-(mins[0]+maxs[0])/2)*.55/(maxs[0]-mins[0]),-.211-.003*(p.z-mins[2])/(maxs[2]-mins[2]),.230+(p.y-(mins[1]+maxs[1])/2)*.21/(maxs[1]-mins[1]))
obj.name='Raised liaose base lettering';obj.data.materials.clear();obj.data.materials.append(emboss);obj.parent=groups['LogoPrint']
bm=bmesh.new();bm.from_mesh(obj.data);bmesh.ops.remove_doubles(bm,verts=list(bm.verts),dist=1e-7);bmesh.ops.triangulate(bm,faces=list(bm.faces));bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(obj.data);bm.free();obj.data.update()
for f in obj.data.polygons:f.use_smooth=abs(f.normal.y)<.999
for _ in range(2):
 obj.data.update()
 corner_normals=[n.vector.copy() for n in obj.data.corner_normals]
 for f in obj.data.polygons:
  if f.normal.dot(sum((corner_normals[i] for i in f.loop_indices),Vector()))<.45:f.use_smooth=False

scale=2.9/2.14
pivots={'Body':0,'Base':.25,'Closure':1.35,'DropperBulb':1.75,'Pipette':1.35,'PaperLabel':.875,'LogoPrint':.72}
assert set(groups)==set(pivots)
for name,group in groups.items():
 pivot=Vector((0,0,pivots[name]))
 for child in group.children:child.location-=pivot
 group.location=pivot*scale;group.scale=(scale,scale,scale)
bpy.context.view_layer.update()
part_bounds={}
for name,group in groups.items():
 points=[o.matrix_world@v.co for o in group.children for v in o.data.vertices]
 part_bounds[name]={'min':[min(p[i] for p in points) for i in range(3)],'max':[max(p[i] for p in points) for i in range(3)]}
assert abs(part_bounds['DropperBulb']['max'][2]-2.9)<1e-6
# Identity parents preserve every mesh transform while exposing complete assemblies.
for name,children in [('DropperAssembly',('Closure','DropperBulb','Pipette')),('BottleAssembly',('Body','Base'))]:
 assembly=bpy.data.objects.new(name,None);bpy.context.collection.objects.link(assembly)
 for child in children:groups[child].parent=assembly
 groups[name]=assembly
 part_bounds[name]={'min':[min(part_bounds[child]['min'][i] for child in children) for i in range(3)],'max':[max(part_bounds[child]['max'][i] for child in children) for i in range(3)]}
groups={name:groups[name] for name in ('DropperAssembly','BottleAssembly','PaperLabel','LogoPrint')}
bpy.ops.object.select_all(action='SELECT')
bpy.ops.export_scene.gltf(filepath=str(CLIENT/'packaging-assets/poster-057.glb'),export_format='GLB',use_selection=True,export_apply=True,export_yup=True,export_extras=True)
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'poster-057.blend'))
info={'id':'poster-057','components':list(groups),'height':2.9,'nominalHeight':2.9,'actualHeight':part_bounds['DropperBulb']['max'][2],'width':scale,'depth':.42*scale,'closedHeightToWidth':2.14,'visibleGlassHeightToWidth':.82,'glassTopToWidth':1.36,'glassBottomToWidth':.055,'glassInnerFloorToWidth':.11,'glassVisibleWidthToBaseWidth':.98,'baseHeightToWidth':.50,'baseInnerFloorToWidth':.045,'baseInnerHalfWidth':.474,'baseInnerHalfDepth':.184,'concealedGlassHalfWidth':.466,'concealedGlassHalfDepth':.177,'baseSideClearanceToWidth':.008,'baseDepthClearanceToWidth':.007,'baseMinimumLipClearanceToWidth':.002,'closureDiameterToWidth':.45,'closureHeightToWidth':.40,'bulbMainDiameterToWidth':.22,'bulbRootDiameterToWidth':.28,'bulbVisibleHeightToWidth':.39,'pipetteOuterDiameterToWidth':.058,'pipetteInnerDiameterToWidth':.042,'pipetteBottomToWidth':.17,'pipetteTopToWidth':1.82,'pipetteInnerFloorClearanceToWidth':.06,'labelWidthToBodyWidth':.72,'labelHeightToBodyWidth':.66,'labelCentreHeightToWidth':.875,'labelPlaneBlenderY':-.2014,'printPlaneBlenderY':-.2022,'baseLogoWidthToWidth':.55,'baseLogoHeightToWidth':.21,'baseLogoCentreHeightToWidth':.23,'baseLogoReliefDepthToWidth':.003,'componentBoundsBlenderXYZ':part_bounds,'pivotsHeightToWidth':pivots,'illustrativeDimensions':True,'containsFormula':False,'reference':'../../mobile-client-preview/assets/posters/poster-057.webp','featuredReference':'featured-assets/poster-057.png','editableArtwork':['label.svg','print.svg','base-logo.svg'],'separateLabelAndPrint':True,'printIncludes':['liaose','B5 SERUM','30 ml','liaose relief on white base'],'hiddenStructure':'Bottle heel concealed inside the open base cup, dropper air connection, tube length and wall dimensions are illustrative. The reference gives no visible paper label boundary; a transparent unprinted film carrier is provided for layer interaction. White base material is unspecified rather than asserted ceramic or paper.','material':'Neutral empty glass, opaque white collar and hollow bulb, matte white base; no pink formula is modeled.','assemblyChildren':{'DropperAssembly':['Closure','DropperBulb','Pipette'],'BottleAssembly':['Body','Base']},'completeDropperLift':1.95,'baseStaysFitted':True,'camera':{'closedCenter':1.45,'openCenter':2.2,'closedHeight':4.2,'openHeight':6.3,'closedWidth':3.8,'openWidth':5.8,'openCenterX':-1.65},'revision':'complete-dropper-and-fitted-bottle-base-local-review-20261027','generator':'build_b5_serum.py'}
(OUT/'model-info.json').write_text(json.dumps(info,indent=2)+'\n')
print('B5 Serum rebuilt:',len(groups),'independent groups')
