"""Golden Face Oil 056: frosted empty glass and a matching front/rear U-skirt cover."""
import bpy, bmesh, math, json, subprocess, xml.etree.ElementTree as ET
from pathlib import Path
from mathutils import Vector

BASE=Path(__file__).resolve().parent
CLIENT=BASE.parents[1]
OUT=BASE/'poster-056'
OUT.mkdir(exist_ok=True)
logo=next(e.attrib['d'] for e in ET.parse(OUT/'print.svg').getroot().iter() if e.tag.endswith('path'))
label='<svg xmlns="http://www.w3.org/2000/svg" width="620" height="350" viewBox="0 0 620 350"><rect x="3" y="3" width="614" height="344" rx="23" fill="#fffdf7" fill-opacity=".14" stroke="#87957e" stroke-opacity=".5" stroke-width="4"/></svg>'
printing=f'''<svg xmlns="http://www.w3.org/2000/svg" width="620" height="350" viewBox="0 0 620 350"><svg x="119" y="51.5" width="385" height="159" viewBox="0 0 340 125" preserveAspectRatio="none"><path d="{logo}" fill="#29301b"/></svg><text x="310" y="279" text-anchor="middle" fill="#29301b" font-family="Helvetica Neue,Arial,sans-serif" font-size="38" letter-spacing="13">GOLDEN FACE OIL</text></svg>'''
(OUT/'label.svg').write_text(label)
(OUT/'print.svg').write_text(printing)
node='/Users/icecream/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/bin/node'
script="""import sharp from '/Users/icecream/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/sharp/dist/index.mjs';import fs from 'node:fs/promises';for(const kind of ['label','print'])await sharp(await fs.readFile(process.argv[1]+'/'+kind+'.svg'),{density:144}).png().toFile(process.argv[1]+'/'+kind+'.png');"""
subprocess.run([node,'--input-type=module','-e',script,str(OUT)],check=True)
bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete(use_global=False)
groups={}

def mat(name,color,rough,transmission=0):
 m=bpy.data.materials.new(name);m.use_nodes=True
 b=m.node_tree.nodes.get('Principled BSDF')
 rgb=[int(color[i:i+2],16)/255 for i in (1,3,5)]
 b.inputs['Base Color'].default_value=(*[v/12.92 if v<=.04045 else ((v+.055)/1.055)**2.4 for v in rgb],1)
 b.inputs['Roughness'].default_value=rough
 b.inputs['Transmission Weight'].default_value=transmission
 b.inputs['IOR'].default_value=1.49
 return m

glass=mat('Golden neutral frosted thick glass','#ffffff',.28,1)
cover=mat('Golden translucent deep olive overcap','#4b5524',.065,.86)
cover.node_tree.nodes.get('Principled BSDF').inputs['Coat Weight'].default_value=.28
cover.node_tree.nodes.get('Principled BSDF').inputs['Coat Roughness'].default_value=.055
closure=mat('Golden olive stepped closure','#38421b',.16)
stem=mat('Golden olive pump stem','#657137',.24)
actuator=mat('Golden olive cylindrical actuator','#414e1d',.12)
dip_tube=mat('Golden clear plastic dip tube','#ffffff',.06,.98)
dip_tube.node_tree.nodes.get('Principled BSDF').inputs['IOR'].default_value=1.46
dip_tube.use_backface_culling=True

def mesh(name,vertices,faces,material,parent,smooth=True):
 data=bpy.data.meshes.new(name);data.from_pydata(vertices,[],faces);data.update()
 obj=bpy.data.objects.new(name,data);bpy.context.collection.objects.link(obj)
 obj.data.materials.append(material)
 if parent not in groups:
  groups[parent]=bpy.data.objects.new(parent,None);bpy.context.collection.objects.link(groups[parent])
 obj.parent=groups[parent]
 for f in data.polygons:f.use_smooth=smooth and abs(f.normal.z)<.999
 return obj

def ring(rx,ry,r,n=128):
 points=[]
 for q in range(4):
  cx=(rx-r)*(1 if q in (0,3) else -1)
  cy=(ry-r)*(1 if q<2 else -1)
  for i in range(n//4):
   angle=q*math.pi/2+i/(n//4-1)*math.pi/2
   points.append((cx+r*math.cos(angle),cy+r*math.sin(angle)))
 return points

def loft(name,profile,material,parent,n=128):
 vertices=[];rings=[];faces=[]
 for z,rx,ry,r in profile:
  if rx==0:rings.append([len(vertices)]);vertices.append((0,0,z))
  else:
   rings.append(list(range(len(vertices),len(vertices)+n)))
   vertices.extend((x,y,z) for x,y in ring(rx,ry,r,n))
 for a,b in zip(rings,rings[1:]):
  if len(a)==len(b)==1:continue
  for i in range(n):
   j=(i+1)%n
   faces.append((a[0],b[j],b[i]) if len(a)==1 else (a[i],a[j],b[0]) if len(b)==1 else (a[i],a[j],b[j],b[i]))
 obj=mesh(name,vertices,faces,material,parent)
 bm=bmesh.new();bm.from_mesh(obj.data)
 bmesh.ops.remove_doubles(bm,verts=list(bm.verts),dist=1e-7)
 bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces))
 assert all(edge.is_manifold for edge in bm.edges),name+' must be a closed solid'
 bm.to_mesh(obj.data);bm.free();obj.data.update()
 return obj

def lathe(name,profile,material,parent,n=128):
 return loft(name,[(z,r,r,r) for z,r in profile],material,parent,n)

# One connected surface runs from the underside around the lip and down to the inner floor.
outer=[(0,0,0,0),(0,.453,.123,.028),(.003,.475,.145,.032),(.012,.489,.159,.035),(.026,.497,.167,.037),(.040,.5,.17,.038),(.838,.5,.17,.038),(.857,.497,.168,.039),(.872,.490,.163,.041),(.884,.478,.155,.043),(.894,.459,.144,.045),(.903,.402,.132,.052),(.909,.275,.126,.075),(.914,.139,.122,.117),(.920,.125,.125,.125)]
inner=[(.920,.091,.091,.091),(.908,.091,.091,.091),(.884,.112,.095,.091),(.869,.247,.105,.067),(.857,.393,.118,.043),(.843,.455,.131,.035),(.819,.468,.138,.033),(.184,.468,.138,.033),(.161,.461,.131,.034),(.146,.445,.115,.035),(.140,.419,.089,.035),(.140,0,0,0)]
loft('Hollow rounded rectangular bottle with thick clear base',outer+inner,glass,'Body')

# The visible two-step seat and cylinder are retained; hidden pump mechanics are schematic.
lathe('Olive stepped pump collar',[(.904,.082),(.904,.128),(.910,.144),(.918,.150),(.932,.150),(.936,.143),(.941,.143),(.946,.150),(.958,.150),(.965,.145),(.972,.141),(.986,.141),(.992,.132),(1.001,.128),(1.001,.074),(.904,.074),(.904,.082)],closure,'Closure')
# The unseen tube is illustrative and remains open at both annular ends.
lathe('Hollow clear Golden pump dip tube',[(.18,.026),(.1815,.0275),(.9885,.0275),(.99,.026),(.99,.021),(.9885,.0195),(.1815,.0195),(.18,.021),(.18,.026)],dip_tube,'Closure')
lathe('Short illustrative connecting stem',[(.969,0),(.969,.062),(.976,.071),(1.044,.071),(1.053,.064),(1.053,0)],stem,'PumpStem')
lathe('Tall cylindrical press actuator',[(1.035,.078),(1.035,.113),(1.042,.128),(1.055,.132),(1.318,.132),(1.335,.128),(1.346,.118),(1.350,.103),(1.350,0),(1.332,0),(1.332,.099),(1.315,.106),(1.068,.106),(1.052,.078),(1.035,.078)],actuator,'Actuator')
lathe('Subtle actuator top inset',[(1.349,0),(1.349,.081),(1.350,.089),(1.351,.081),(1.351,0)],actuator,'Actuator')

# One continuous shell avoids overlapping Boolean seams at the two rounded skirts.
# Each horizontal ring has front/rear sheets; short sides join them above the shoulder.
levels={.50,.61,.96,1.39,1.398,1.41}
for i in range(25):
 angle=i*math.pi/48
 levels.add(.61-.11*math.cos(angle))
 levels.add(1.39+.02*math.sin(angle))
levels=sorted(levels)
vertices=[]
for z in levels:
 half_width=.20+math.sqrt(max(0,.11**2-(z-.61)**2)) if z<.61 else .29+math.sqrt(max(0,.02**2-(z-1.39)**2)) if z>1.39 else .31
 for x in [-half_width,-half_width+.012,half_width-.012,half_width]:
  for y in [-.197,-.185,.211,.223]:vertices.append((x,y,z))
faces=[]
slabs=[]
for lower,upper in zip(levels,levels[1:]):
 middle=(lower+upper)/2
 slabs.append({(x,y) for x in range(3) for y in range(3) if y in (0,2) or middle>=1.398 or (middle>=.96 and x in (0,2))})
for layer,cells in enumerate(slabs):
 for x,y in cells:
  a=layer*16+x*4+y;b=a+4;c=b+1;d=a+1
  A=a+16;B=b+16;C=c+16;D=d+16
  if (x-1,y) not in cells:faces.append((a,d,D,A))
  if (x+1,y) not in cells:faces.append((b,B,C,c))
  if (x,y-1) not in cells:faces.append((a,A,B,b))
  if (x,y+1) not in cells:faces.append((d,c,C,D))
  if layer==0 or (x,y) not in slabs[layer-1]:faces.append((d,c,b,a))
  if layer==len(slabs)-1 or (x,y) not in slabs[layer+1]:faces.append((A,B,C,D))
front=mesh('Hollow olive cover with matching front and rear U skirts',vertices,faces,cover,'Overcap',False)
bm=bmesh.new();bm.from_mesh(front.data)
bmesh.ops.remove_doubles(bm,verts=list(bm.verts),dist=1e-7)
bmesh.ops.dissolve_degenerate(bm,edges=list(bm.edges),dist=1e-7)
bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces))
if bm.calc_volume(signed=True)<0:bmesh.ops.reverse_faces(bm,faces=list(bm.faces))
assert all(edge.is_manifold for edge in bm.edges), 'The dual-skirt cover must be a closed solid'
bm.to_mesh(front.data);bm.free();front.data.update()
bpy.context.view_layer.objects.active=front
bevel=front.modifiers.new('Soft polished cover edge','BEVEL');bevel.width=.0025;bevel.segments=4;bevel.limit_method='ANGLE'
bevel.use_clamp_overlap=False
bpy.ops.object.modifier_apply(modifier=bevel.name)
bm=bmesh.new();bm.from_mesh(front.data)
bmesh.ops.remove_doubles(bm,verts=list(bm.verts),dist=1e-7)
bmesh.ops.dissolve_degenerate(bm,edges=list(bm.edges),dist=1e-7)
bmesh.ops.triangulate(bm,faces=list(bm.faces),quad_method='BEAUTY',ngon_method='BEAUTY')
bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces))
if bm.calc_volume(signed=True)<0:bmesh.ops.reverse_faces(bm,faces=list(bm.faces))
assert all(edge.is_manifold for edge in bm.edges), 'The beveled cover must retain a closed solid'
bm.to_mesh(front.data);bm.free();front.data.update()
for f in front.data.polygons:f.use_smooth=True
normal=front.modifiers.new('Flat panels with rounded highlight normals','WEIGHTED_NORMAL');normal.keep_sharp=True;normal.weight=50
bpy.ops.object.modifier_apply(modifier=normal.name)

for kind,parent,name in [('label','PaperLabel','Transparent unprinted film carrier'),('print','LogoPrint','Complete Golden Face Oil lettering')]:
 material=mat('Golden clear label film' if kind=='label' else 'Golden dark olive complete print','#ffffff',.22 if kind=='label' else .64)
 b=material.node_tree.nodes.get('Principled BSDF');b.inputs['Specular IOR Level'].default_value=.3 if kind=='label' else .015
 texture=material.node_tree.nodes.new('ShaderNodeTexImage');texture.image=bpy.data.images.load(str(OUT/(kind+'.png')));texture.image.pack()
 material.node_tree.links.new(texture.outputs['Color'],b.inputs['Base Color']);material.node_tree.links.new(texture.outputs['Alpha'],b.inputs['Alpha'])
 material.surface_render_method='DITHERED'
 y=-.1714 if kind=='label' else -.1722
 obj=mesh(name,[(-.31,y,.125),(.31,y,.125),(.31,y,.475),(-.31,y,.475)],[(0,1,2,3)],material,parent,False)
 uv=obj.data.uv_layers.new()
 for i,co in enumerate([(0,0),(1,0),(1,1),(0,1)]):uv.data[i].uv=co

scale=2.9/1.41
pivots={'Body':0,'Closure':.93,'PumpStem':1.01,'Actuator':1.04,'Overcap':.96,'PaperLabel':.30,'LogoPrint':.30}
assert set(groups)==set(pivots)
assert .185-.17>=.0149 and .96>.92 and 1.398-1.351>.046
for name,group in groups.items():
 pivot=Vector((0,0,pivots[name]))
 for child in group.children:child.location-=pivot
 group.location=pivot*scale;group.scale=(scale,scale,scale)
assembly=bpy.data.objects.new('PumpAssembly',None);bpy.context.collection.objects.link(assembly)
for child in ('Closure','PumpStem','Actuator'):groups[child].parent=assembly
groups={name:groups[name] for name in ('Body','Overcap','PaperLabel','LogoPrint')}
groups['PumpAssembly']=assembly
bpy.ops.object.select_all(action='SELECT')
bpy.ops.export_scene.gltf(filepath=str(CLIENT/'packaging-assets/poster-056.glb'),export_format='GLB',use_selection=True,export_apply=True,export_yup=True,export_extras=True)
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'poster-056.blend'))
info={'id':'poster-056','components':list(groups),'assemblyChildren':{'PumpAssembly':['Closure','PumpStem','Actuator']},'completePumpLift':1.85,'overcapLift':3.95,'camera':{'closedCenter':1.45,'openCenter':3.4275,'closedHeight':4.2,'openHeight':8.0},'dipTube':{'mesh':'Hollow clear Golden pump dip tube','parent':'Closure','outerDiameterToWidth':.055,'innerDiameterToWidth':.039,'bottomToWidth':.18,'topToWidth':.99,'bodyInnerFloorToWidth':.14,'bottomClearance':.04*scale,'fullyOpenBottleClearance':(.18-.92)*scale+1.85,'openAtBothEnds':True,'dimensionsIllustrative':True},'height':2.9,'width':scale,'depth':.34*scale,'closedHeightToWidth':1.41,'glassHeightToWidth':.92,'bodyDepthToWidth':.34,'glassInnerFloorToWidth':.14,'overcapWidthToBodyWidth':.62,'overcapDepthToBodyWidth':.42,'overcapTopToWidth':1.41,'overcapFrontSkirtBottomToWidth':.50,'overcapRearSkirtBottomToWidth':.50,'overcapSkirtLowerCornerRadiusToWidth':.11,'overcapWallThicknessToWidth':.012,'overcapInnerFrontBlenderY':-.185,'bodyFrontBlenderY':-.17,'overcapFrontGapToWidth':.015,'overcapInnerRearBlenderY':.211,'bodyRearBlenderY':.17,'overcapRearGapToWidth':.041,'coverProfileSymmetryCentreBlenderY':.013,'overcapShortWallsBottomToWidth':.96,'overcapInnerTopToWidth':1.398,'actuatorTopToWidth':1.351,'labelWidthToBodyWidth':.62,'labelHeightToBodyWidth':.35,'labelCentreHeightToWidth':.30,'labelPlaneBlenderY':-.1714,'printPlaneBlenderY':-.1722,'illustrativeDimensions':True,'containsFormula':False,'reference':'../../mobile-client-preview/assets/posters/poster-056.webp','featuredReference':'featured-assets/poster-056.png','editableArtwork':['label.svg','print.svg'],'separateLabelAndPrint':True,'printIncludes':['liaose','GOLDEN FACE OIL'],'perspectiveCalibration':'Approximate orthographic deprojection: yaw 28 degrees, elevation 10 degrees; dimensions require physical measurement','hiddenStructure':'Short connecting stem, hidden actuator cavity, pump seat, dip tube dimensions and connection are illustrative. The transparent unprinted carrier is a layer illustration; no paper label boundary appears in the reference. No liquid, long nozzle or dropper is added.','coverConstruction':'Matching long U-profile front and rear sheets sit outside both glass faces. They share one connected hood with short shoulder-clearing side walls and a top. Front/rear profiles match about the cover centre at Blender Y=.013, not about the bottle centre; clearances are .015W/.041W. The hood lifts without intersecting the bottle.','revision':'physical-reference-frosted-glass-dual-u-cover-local-review-20261027','glassFinish':{'name':'neutral frosted glass','transmission':1,'roughness':.28,'containsTintedLiquid':False},'physicalReferenceFiles':['f115f9755d4125e0aa29da51445e39e6.jpg','b7d130f05e8e1d7b54012a283021203d.jpg','ad46e83363916961db71f99923582e77.jpg'],'generator':'build_golden_face_oil.py'}
bpy.context.view_layer.update()
world_vertices=[obj.matrix_world @ vertex.co for obj in bpy.data.objects if obj.type=='MESH' for vertex in obj.data.vertices]
cover_vertices=[obj.matrix_world @ vertex.co for obj in groups['Overcap'].children for vertex in obj.data.vertices]
def bounds(points):return [[min(p[i] for p in points) for i in range(3)],[max(p[i] for p in points) for i in range(3)]]
world_bounds=bounds(world_vertices);cover_bounds=bounds(cover_vertices)
info.update({'nominalHeight':2.9,'actualHeight':world_bounds[1][2]-world_bounds[0][2],'nominalOvercapWidthToBodyWidth':.62,'nominalOvercapDepthToBodyWidth':.42,'actualOvercapWidthToBodyWidth':(cover_bounds[1][0]-cover_bounds[0][0])/scale,'actualOvercapDepthToBodyWidth':(cover_bounds[1][1]-cover_bounds[0][1])/scale,'actualBoundsBlenderXYZ':world_bounds,'actualOvercapBoundsBlenderXYZ':cover_bounds,'dimensionNote':'height and unsuffixed design ratios are nominal. Small corner-bevel envelope growth is reported separately in actual fields; this remains a reference-based visualization.'})
(OUT/'model-info.json').write_text(json.dumps(info,indent=2)+'\n')
print('Golden Face Oil rebuilt:',len(groups),'independent groups')
