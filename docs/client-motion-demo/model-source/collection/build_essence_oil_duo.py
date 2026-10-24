"""Essence Oil Duo 059: paired rounded empty bottles with separate complete printing."""
import bpy,bmesh,math,json,subprocess,xml.etree.ElementTree as ET
from pathlib import Path
from mathutils import Vector
BASE=Path(__file__).resolve().parent;CLIENT=BASE.parents[1];OUT=BASE/'poster-059';OUT.mkdir(exist_ok=True)
logo=next(e.attrib['d'] for e in ET.parse(OUT/'print.svg').getroot().iter() if e.tag.endswith('path'))
label='<svg xmlns="http://www.w3.org/2000/svg" width="820" height="580" viewBox="0 0 820 580"><rect x="3" y="3" width="814" height="574" rx="26" fill="#fffdf7" fill-opacity=".14" stroke="#a89777" stroke-opacity=".5" stroke-width="4"/></svg>'
(OUT/'label.svg').write_text(label)
for kind,title,spacing in [('print','ESSENCE OIL',2.3),('print-biphase','BIPHASE ESSENCE OIL',1.5)]:
 printing=f'''<svg xmlns="http://www.w3.org/2000/svg" width="820" height="580" viewBox="0 0 820 580"><svg x="133" y="136" width="544" height="249" viewBox="0 0 340 125" preserveAspectRatio="none"><path d="{logo}" fill="#211e17"/></svg><text x="0" transform="translate(410,0) scale({.89 if kind=='print' else .87},1)" y="487" text-anchor="middle" fill="#211e17" font-family="Helvetica Neue,Arial,sans-serif" font-size="67" letter-spacing="{spacing}">{title}</text></svg>''';(OUT/(kind+'.svg')).write_text(printing)
node='/Users/icecream/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/bin/node'
subprocess.run([node,'--input-type=module','-e',"""import sharp from '/Users/icecream/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/sharp/dist/index.mjs';import fs from 'node:fs/promises';for(const kind of ['label','print','print-biphase'])await sharp(await fs.readFile(process.argv[1]+'/'+kind+'.svg'),{density:144}).png().toFile(process.argv[1]+'/'+kind+'.png');""",str(OUT)],check=True)
bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False);groups={}
def mat(name,color,rough,transmission=0):
 m=bpy.data.materials.new(name);m.use_nodes=True;b=m.node_tree.nodes.get('Principled BSDF');rgb=[int(color[i:i+2],16)/255 for i in (1,3,5)];b.inputs['Base Color'].default_value=(*[v/12.92 if v<=.04045 else ((v+.055)/1.055)**2.4 for v in rgb],1);b.inputs['Roughness'].default_value=rough;b.inputs['Transmission Weight'].default_value=transmission;b.inputs['IOR'].default_value=1.49;return m
glass=mat('Essence Duo neutral clear glass','#ffffff',.026,1)
pipette_mat=mat('Essence Duo clear pipette glass','#ffffff',.028,1)
cream=mat('Essence Duo glossy cream collar','#eee2c9',.19)
white=mat('Essence Duo soft white bulb','#f3eee5',.40)
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

for bottle,x in [('Essence',-.53),('Biphase',.53)]:
 before=set(bpy.data.objects)
 outer=[(0,0,0,0),(0,.358,.088,.050),(.010,.408,.138,.065),(.031,.451,.171,.072),(.070,.482,.190,.074),(.118,.497,.199,.075),(.164,.500,.200,.075),(1.040,.500,.200,.075),(1.090,.493,.197,.080),(1.145,.473,.189,.087),(1.197,.438,.177,.097),(1.239,.395,.160,.107),(1.272,.340,.143,.118),(1.291,.275,.133,.126),(1.300,.190,.128,.127),(1.312,.140,.140,.140),(1.345,.140,.140,.140)]
 inner=[(1.345,.097,.097,.097),(1.308,.097,.097,.097),(1.278,.120,.098,.095),(1.262,.246,.094,.080),(1.239,.311,.109,.078),(1.208,.367,.131,.075),(1.167,.411,.147,.068),(1.117,.440,.156,.063),(1.037,.456,.158,.060),(.240,.456,.158,.060),(.195,.445,.147,.061),(.164,.419,.121,.061),(.146,.376,.078,.055),(.143,0,0,0)]
 loft(bottle+' hollow rounded rectangular glass',outer+inner,glass,'Body')
 lathe(bottle+' hollow cream dropper collar',[(1.300,.220),(1.300,.238),(1.309,.249),(1.322,.250),(1.661,.250),(1.676,.245),(1.680,.233),(1.680,.095),(1.654,.095),(1.654,.220),(1.641,.225),(1.314,.225),(1.300,.220)],cream,'Closure')
 bulb=[(1.651,.073),(1.651,.091),(1.678,.091),(1.680,.151),(1.695,.145),(1.712,.132),(1.735,.119),(1.758,.115),(2.005,.115)]
 for i in range(1,29):
  a=i*math.pi/56;bulb.append((2.005+.115*math.sin(a),.115*math.cos(a) if i<28 else 0))
 bulb.append((2.102,0))
 for i in range(1,29):
  a=math.pi/2-i*math.pi/56;bulb.append((2.005+.097*math.sin(a),.097*math.cos(a)))
 bulb.extend([(1.760,.097),(1.725,.104),(1.702,.121),(1.691,.073),(1.651,.073)])
 lathe(bottle+' hollow soft white bulb',bulb,white,'DropperBulb',128)
 lathe(bottle+' hollow pipette without oil drop',[(.430,.015),(.430,.021),(.444,.023),(.474,.032),(.510,.038),(1.768,.038),(1.780,.035),(1.780,.028),(1.766,.028),(.514,.028),(.482,.024),(.446,.015),(.430,.015)],pipette_mat,'Pipette',96)
 for kind,parent in [('label','PaperLabel'),('print','LogoPrint')]:
  filename=kind if kind=='label' or bottle=='Essence' else 'print-biphase'
  material=mat('Essence Duo transparent label film' if kind=='label' else bottle+' complete dark lettering','#ffffff',.24 if kind=='label' else .66)
  b=material.node_tree.nodes.get('Principled BSDF');b.inputs['Specular IOR Level'].default_value=.3 if kind=='label' else .02
  t=material.node_tree.nodes.new('ShaderNodeTexImage');t.image=bpy.data.images.load(str(OUT/(filename+'.png')));t.image.pack();material.node_tree.links.new(t.outputs['Color'],b.inputs['Base Color']);material.node_tree.links.new(t.outputs['Alpha'],b.inputs['Alpha']);material.surface_render_method='DITHERED'
  y=-.2014 if kind=='label' else -.2022
  obj=mesh(bottle+(' unprinted film carrier' if kind=='label' else ' complete bottle print'),[(-.41,y,.47),(.41,y,.47),(.41,y,1.05),(-.41,y,1.05)],[(0,1,2,3)],material,parent);uv=obj.data.uv_layers.new()
  for i,p in enumerate([(0,0),(1,0),(1,1),(0,1)]):uv.data[i].uv=p
 for obj in set(bpy.data.objects)-before:
  if obj.type=='MESH':
   for vertex in obj.data.vertices:vertex.co.x+=x
scale=2.9/2.12;pivots={'Body':0,'Closure':1.30,'DropperBulb':1.68,'Pipette':1.30,'PaperLabel':.76,'LogoPrint':.76}
assert set(groups)==set(pivots)
for name,group in groups.items():
 pivot=Vector((0,0,pivots[name]))
 for obj in group.children:obj.location-=pivot
 group.location=pivot*scale;group.scale=(scale,scale,scale)
bpy.context.view_layer.update();part_bounds={}
for name,group in groups.items():
 points=[obj.matrix_world@v.co for obj in group.children for v in obj.data.vertices];part_bounds[name]={'min':[min(p[i] for p in points) for i in range(3)],'max':[max(p[i] for p in points) for i in range(3)]}
assert abs(part_bounds['DropperBulb']['max'][2]-2.9)<1e-6
bpy.ops.object.select_all(action='SELECT');bpy.ops.export_scene.gltf(filepath=str(CLIENT/'packaging-assets/poster-059.glb'),export_format='GLB',use_selection=True,export_apply=True,export_yup=True,export_extras=True);bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'poster-059.blend'))
info={'id':'poster-059','components':list(groups),'bottleCount':2,'height':2.9,'width':2.06*scale,'singleBottleWidth':scale,'depth':.4*scale,'singleClosedHeightToWidth':2.12,'glassVisibleHeightToWidth':1.30,'glassNeckTopToWidth':1.345,'glassInnerFloorToWidth':.143,'bottleCentreSpacingToWidth':1.06,'closureDiameterToWidth':.5,'closureHeightToWidth':.38,'bulbMainDiameterToWidth':.23,'bulbVisibleHeightToWidth':.44,'pipetteBottomToWidth':.43,'pipetteTopToWidth':1.78,'pipetteOuterDiameterToWidth':.076,'pipetteInnerDiameterToWidth':.056,'labelWidthToBottleWidth':.82,'labelHeightToBottleWidth':.58,'labelBottomToWidth':.47,'pivotsHeightToWidth':pivots,'componentBoundsBlenderXYZ':part_bounds,'illustrativeDimensions':True,'containsFormula':False,'reference':'../../mobile-client-preview/assets/posters/poster-059.webp','editableArtwork':['label.svg','print.svg','print-biphase.svg'],'separateLabelAndPrint':True,'printIncludes':['liaose','ESSENCE OIL','liaose','BIPHASE ESSENCE OIL'],'hiddenStructure':'Bottle depth, concealed connection and wall dimensions are illustrative; the original has no paper-label boundary, so two transparent film carriers are provided. Dropper tubes stop at their visible solid ends; liquid globules and oil/water layers are excluded.','material':'Two neutral empty clear bottles, opaque cream collars and white hollow bulbs','revision':'individual-reference-review-20261025','generator':'build_essence_oil_duo.py'}
(OUT/'model-info.json').write_text(json.dumps(info,indent=2)+'\n');print('Essence Oil Duo rebuilt:',len(groups),'independent groups')
