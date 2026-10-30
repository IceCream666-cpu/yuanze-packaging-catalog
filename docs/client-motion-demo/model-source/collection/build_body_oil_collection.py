"""Reference-calibrated Body Oil 02 representative empty bottle; local review only."""
import hashlib, json, math, shutil, subprocess, sys
from pathlib import Path
import bpy
from mathutils import Vector

BASE=Path(__file__).resolve().parent
sys.path.insert(0,str(BASE))
from tail_model_helpers import Model, svg, logo, part, NODE

ID='body-oil-collection'
CLIENT=BASE.parents[1]
OUT=BASE/ID
OUT.mkdir(exist_ok=True)
PUBLIC=CLIENT/'public/review'/ID
PUBLIC.mkdir(parents=True,exist_ok=True)
SOURCE=Path('/Users/icecream/Library/Containers/com.tencent.xinWeChat/Data/Documents/xwechat_files/wxid_1zvd90xm0two22_7a55/temp/RWTemp/2026-10/9e20f478899dc29eb19741386f9343c8/358ecac387d18682ac54cd46afa54e8d.png')
if SOURCE.exists(): shutil.copy2(SOURCE,OUT/'reference.png')
assert (OUT/'reference.png').exists(),'Keep the supplied reference with the editable source.'
if not (OUT/'print.svg').exists():shutil.copy2(BASE/'poster-059/print.svg',OUT/'print.svg')
m=Model(ID)

# No paper label boundary is visible: the blank transparent carrier explains the print layers.
art={
 'label':svg(620,520,'<rect x="4" y="4" width="612" height="512" rx="28" fill="#fff8e8" fill-opacity=".12" stroke="#a48b66" stroke-opacity=".55" stroke-width="3"/>'),
 'print':svg(620,520,logo(m,60,30,500,200,'#25180f')),
}
for number in ['02']:
 art['name-'+number]=svg(620,520,f'<g fill="#25180f" text-anchor="middle" font-family="Helvetica Neue,Arial,sans-serif"><text x="310" y="310" font-size="35" letter-spacing="17">BODY OIL</text><text x="310" y="412" font-size="38" letter-spacing="7">{number}</text></g>')
for name,content in art.items():(OUT/(name+'.svg')).write_text(content)
subprocess.run([NODE,'--input-type=module','-e',"import sharp from '/Users/icecream/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/sharp/dist/index.mjs';import fs from 'node:fs/promises';for(const n of JSON.parse(process.argv[2]))await sharp(await fs.readFile(process.argv[1]+'/'+n+'.svg'),{density:192}).png().toFile(process.argv[1]+'/'+n+'.png');",str(OUT),json.dumps(list(art))],check=True)

glass=m.mat('Body Oil colourless clear glass','#ffffff',.035,1)
cap=m.mat('Body Oil warm ivory satin cap','#eee3d1',.30)
liner=m.mat('Body Oil ivory seal illustration','#f4eadb',.46)
film=m.texture('Body Oil unprinted transparent carrier','label.png',.24)
brand=m.texture('Body Oil independent liaose lettering','print.png',.60)
name_mats={n:m.texture('Body Oil name and number '+n,'name-'+n+'.png',.60) for n in ['02']}

# Dimensions in body diameters, inferred from the visible silhouette rather than a factory drawing.
outer=[(0,0),(.0,.355),(.008,.395),(.022,.431),(.043,.459),(.072,.480),(.109,.492),(.154,.498),(.205,.500),(1.080,.500),(1.140,.499),(1.200,.491),(1.260,.477),(1.320,.455),(1.380,.422),(1.440,.385),(1.500,.345),(1.560,.301),(1.620,.253),(1.670,.214),(1.710,.190),(1.745,.178),(1.780,.172),(1.840,.172)]
inner=[(1.840,.132),(1.780,.132),(1.743,.139),(1.700,.154),(1.655,.184),(1.600,.226),(1.540,.274),(1.480,.317),(1.420,.356),(1.360,.393),(1.300,.422),(1.240,.444),(1.180,.457),(1.120,.462),(.242,.462),(.204,.454),(.174,.436),(.153,.405),(.143,.363),(.139,0)]
positions=[('02',0,0,0)]
for number,x,y,z in positions:
 before=set(bpy.data.objects)
 m.lathe('Body Oil '+number+' hollow long-shoulder glass bottle',outer+inner,glass,'Body',192)
 m.lathe('Body Oil '+number+' hollow satin ivory cap',[(1.835,.224),(1.835,.242),(1.839,.252),(1.847,.257),(2.166,.257),(2.177,.251),(2.182,.238),(2.182,0),(2.151,0),(2.151,.218),(2.145,.226),(1.848,.226),(1.835,.224)],cap,'Closure',160)
 m.lathe('Body Oil '+number+' internal seal illustration',[(1.846,0),(1.846,.155),(1.849,.163),(1.863,.163),(1.867,.155),(1.867,0)],liner,'InnerSeal',128)
 surface=lambda x,z:-math.sqrt(max(.5**2-x*x,0))
 m.sheet('Body Oil '+number+' blank curved transparent carrier',.62,.52,.49,surface,film,'PaperLabel',64,12,.0014)
 m.sheet('Body Oil '+number+' liaose only',.62,.52,.49,surface,brand,'LogoPrint',64,12,.0022)
 m.sheet('Body Oil '+number+' BODY OIL and '+number,.62,.52,.49,surface,name_mats[number],'ProductPrint',64,12,.0030)
 for o in set(bpy.data.objects)-before:
  if o.type=='MESH':
   for vertex in o.data.vertices:vertex.co+=Vector((x,y,z))

# The poster cap is approximately half the bottle width; preserve the neck clearance.
for obj in m.groups['Closure'].children:
 for v in obj.data.vertices:v.co.x *= .504/.514;v.co.y *= .504/.514

total=2.182
scale=2.9/total
pivots={'Body':0,'Closure':2.25,'InnerSeal':2.25,'PaperLabel':1.18,'LogoPrint':1.18,'ProductPrint':1.18}
assert set(m.groups)==set(pivots)
for name,g in m.groups.items():
 pivot=Vector((0,0,pivots[name]))
 for o in g.children:o.location-=pivot
 g.location=pivot*scale;g.scale=(scale,)*3
bpy.context.view_layer.update()
bounds={}
for name,g in m.groups.items():
 points=[o.matrix_world@v.co for o in g.children for v in o.data.vertices]
 bounds[name]={'min':[min(p[i] for p in points) for i in range(3)],'max':[max(p[i] for p in points) for i in range(3)]}
assert abs(max(b['max'][2] for b in bounds.values())-2.9)<1e-6
# Keep the concealed seal with the complete cap without changing its fitted position.
seal = m.groups.pop('InnerSeal')
fitted = seal.matrix_world.copy()
seal.parent = m.groups['Closure']
seal.matrix_world = fitted
bpy.context.view_layer.update()
seal_bounds = bounds.pop('InnerSeal')
cap_bounds = bounds['Closure']
bounds['Closure'] = {'min':[min(cap_bounds['min'][i],seal_bounds['min'][i]) for i in range(3)],
                     'max':[max(cap_bounds['max'][i],seal_bounds['max'][i]) for i in range(3)]}
glb=PUBLIC/(ID+'.glb')
bpy.ops.object.select_all(action='SELECT')
bpy.ops.export_scene.gltf(filepath=str(glb),export_format='GLB',use_selection=True,export_apply=True,export_yup=True,export_extras=True)
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/(ID+'.blend')))
shutil.copy2(OUT/'reference.png',PUBLIC/'reference.png')
parts=[
 part('closure','Closure','完整米白瓶盖','Complete ivory cap','瓶盖与盖内密封垫保持组装，作为整体向上移开。','The satin cap and its internal seal stay assembled and lift together.'),
 part('body','Body','透明玻璃瓶','Clear glass','取原图02号同型空瓶，保留长肩、短颈与圆润厚底。','One representative empty long-shoulder bottle with a thick glass base.'),
 part('label','PaperLabel','透明底材','Clear carriers','无字薄膜示意，不添加原图没有的纸标。','Unprinted clear carriers, without an invented paper label.'),
 part('print','LogoPrint','品牌字','Brand lettering','liaose独立向外展开。','The liaose mark moves outward independently.'),
 part('name','ProductPrint','产品名与编号','Names and numbers','BODY OIL及02比标贴更向外展开。','BODY OIL and 02 move farther out than the carriers.'),
]
review={'parts':parts,'appearance':{'glass':True,'frosted':False,'referenceGlass':True,'pipette':False,'clearLabel':True,'metal':False},'explosion':{'offsets':{'closure':[0,1.4,0],'label':[-.65,.02,.70],'print':[-1.50,.23,1.85],'name':[-1.50,-.18,1.85]},'scales':{'label':1.08,'print':1.3,'name':1.3},'camera':{'centerY':[1.45,2.10],'centerX':[0,-.75],'height':[3.7,4.95],'width':[2.1,4.0]}}}
config={'product':{'file':ID+'.glb','kind':'collection','scale':1,'parts':parts,'review':review},'design':{'name':'Body Oil Collection','background':'#eadbc5','ink':'#3e2b1d'}}
source=CLIENT/'review-source'/ID;source.mkdir(parents=True,exist_ok=True)
(source/'review-config.json').write_text(json.dumps(config,ensure_ascii=False,indent=2)+'\n')
(OUT/'review-config.json').write_text(json.dumps(review,ensure_ascii=False,indent=2)+'\n')
info={'id':ID,'state':'local-review','productCount':1,'bottleCount':1,'height':2.9,'components':list(m.groups),'componentBoundsBlenderXYZ':bounds,'singleClosedHeightToWidth':2.182,'glassHeightToWidth':1.840,'glassBaseToWidth':.139,'capDiameterToWidth':.504,'capHeightToWidth':.347,'bottlePositionsInDiameters':positions,'normalizationScale':scale,'containsFormula':False,'colorlessGlass':True,'separateLabelBrandAndName':True,'printIncludes':['liaose','BODY OIL','02'],'illustrativeDimensions':True,'hiddenStructure':'Seal, wall thickness, internal fit and circular depth inferred from one front image; not manufacturing dimensions. Transparent blank carrier illustrates separate printing; no paper edge is visible in the reference.','referenceSha256':hashlib.sha256((OUT/'reference.png').read_bytes()).hexdigest(),'glbSha256':hashlib.sha256(glb.read_bytes()).hexdigest(),'glbBytes':glb.stat().st_size,'generator':Path(__file__).name}
(OUT/'model-info.json').write_text(json.dumps(info,ensure_ascii=False,indent=2)+'\n')
print('Body Oil Collection: 1 empty bottle, 5 groups with one complete cap,',glb.stat().st_size,'bytes')
