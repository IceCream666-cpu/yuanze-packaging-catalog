"""Daily Emulsion: one empty, reference-calibrated frosted bottle for local review."""
import hashlib, json, math, shutil, struct, subprocess, sys, zlib
from pathlib import Path
import bpy, bmesh
from mathutils import Vector

BASE = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE))
from tail_model_helpers import Model, svg, logo, part, NODE

ID = 'daily-emulsion'
CLIENT = BASE.parents[1]
OUT = BASE / ID
PUBLIC = CLIENT / 'public/review' / ID
OUT.mkdir(exist_ok=True)
PUBLIC.mkdir(parents=True, exist_ok=True)
SOURCE = Path('/Users/icecream/Library/Containers/com.tencent.xinWeChat/Data/Documents/xwechat_files/wxid_1zvd90xm0two22_7a55/temp/RWTemp/2026-10/9e20f478899dc29eb19741386f9343c8/e457e0c2f526b6391fa83feedc8e5e7f.png')
if SOURCE.exists():
    shutil.copy2(SOURCE, OUT / 'reference.png')
assert (OUT / 'reference.png').exists()
if not (OUT / 'print.svg').exists():
    shutil.copy2(BASE / 'body-oil-collection/print.svg', OUT / 'print.svg')
m = Model(ID)

# The photo has direct printing, without a visible paper-label boundary.
art = {
    'label': svg(1000, 1364, '<rect x="5" y="5" width="990" height="1354" rx="48" fill="#fffdf6" fill-opacity=".12" stroke="#8b947f" stroke-opacity=".55" stroke-width="4"/>'),
    'print': svg(1000, 1364, logo(m, 76, 181, 848, 333, '#151511')),
    'name': svg(1000, 1364, '''<path d="M401.5 811H598.5" fill="none" stroke="#151511" stroke-width="3"/>
      <text x="500" y="1023" transform="translate(-37 0) scale(1.074 1)" fill="#151511" text-anchor="middle" font-family="Times New Roman,serif" font-size="90" letter-spacing="1.8" textLength="833" lengthAdjust="spacingAndGlyphs">DAILY EMULSION</text>
      <text x="500" y="1210" transform="translate(-90 0) scale(1.18 1)" fill="#151511" text-anchor="middle" font-family="Helvetica Neue,Arial,sans-serif" font-size="53" letter-spacing="11.8" textLength="445" lengthAdjust="spacingAndGlyphs">FACE CARE</text>'''),
}
for name, content in art.items():
    (OUT / (name + '.svg')).write_text(content)
subprocess.run([NODE, '--input-type=module', '-e', "import sharp from '/Users/icecream/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/sharp/dist/index.mjs';import fs from 'node:fs/promises';for(const n of ['label','print','name'])await sharp(await fs.readFile(process.argv[1]+'/'+n+'.svg'),{density:144}).png().toFile(process.argv[1]+'/'+n+'.png');", str(OUT)], check=True)

glass = m.mat('Daily neutral frosted empty glass', '#ffffff', .28, 1)
cover = m.mat('Daily clear protective cover', '#ffffff', .035, 1)
white = m.mat('Daily neutral white satin closure', '#f5f5ef', .24)
headwhite = m.mat('Daily opaque white actuator', '#f7f7f2', .23)
stemwhite = m.mat('Daily hidden short connector illustration', '#ebeee7', .38)
film = m.texture('Daily unprinted transparent carrier', 'label.png', .23)
brand = m.texture('Daily independent liaose lettering', 'print.png', .65)
names = m.texture('Daily rule product name and FACE CARE', 'name.png', .65)

# Width is 1.0; depth .58 and the concealed neck/fit are inferred, not measured specifications.
outer = [
    (0, 0, 0, 0), (0, .370, .200, .090), (.014, .424, .231, .100),
    (.040, .462, .260, .105), (.080, .485, .280, .110),
    (.130, .497, .288, .110), (.180, .500, .290, .110),
    (1.610, .500, .290, .110), (1.680, .494, .285, .112),
    (1.735, .479, .275, .116), (1.780, .453, .258, .125),
    (1.815, .410, .246, .135), (1.842, .350, .240, .155),
    (1.863, .270, .263, .263), (1.885, .255, .255, .255),
    (1.963, .255, .255, .255), (1.972, .251, .251, .251),
]
inner = [
    (1.972, .219, .219, .219), (1.884, .219, .219, .219),
    (1.853, .236, .230, .230), (1.819, .329, .207, .125),
    (1.779, .402, .222, .105), (1.730, .439, .240, .102),
    (1.675, .459, .251, .100), (1.603, .468, .258, .100),
    (.230, .468, .258, .100), (.198, .459, .251, .100),
    (.168, .436, .234, .100), (.148, .390, .202, .090),
    (.140, 0, 0, 0),
]
body = m.loft('Daily hollow flat rounded glass bottle', outer + inner, glass, 'Body', 160)

# A small neutral normal texture suggests etched micro-grain; no milk-coloured body or contents.
N = 256
normal_pixels = bytearray()
for y in range(N):
    normal_pixels.append(0)
    for x in range(N):
        a = math.sin(x * 12.9898 + y * 78.233) * 43758.5453
        b = math.sin(x * 39.3467 + y * 11.135) * 24123.529
        normal_pixels.extend((round(128 + 12 * (a % 1 - .5)), round(128 + 12 * (b % 1 - .5)), 255, 255))
def png_chunk(tag, data):
    return struct.pack('>I', len(data)) + tag + data + struct.pack('>I', zlib.crc32(tag + data) & 0xffffffff)
raw = b'\x89PNG\r\n\x1a\n' + png_chunk(b'IHDR', struct.pack('>IIBBBBB', N, N, 8, 6, 0, 0, 0)) + png_chunk(b'IDAT', zlib.compress(normal_pixels, 9)) + png_chunk(b'IEND', b'')
(OUT / 'frost-normal.png').write_bytes(raw)
uv = body.data.uv_layers.new(name='Frost grain UV')
for face in body.data.polygons:
    us = [(math.atan2(body.data.vertices[body.data.loops[i].vertex_index].co.y / .29, body.data.vertices[body.data.loops[i].vertex_index].co.x / .5) / math.tau + .5) for i in face.loop_indices]
    crossing = max(us) - min(us) > .5
    for li, u in zip(face.loop_indices, us):
        if crossing and u < .5: u += 1
        uv.data[li].uv = (u * 8, body.data.vertices[body.data.loops[li].vertex_index].co.z * 5)
nodes = glass.node_tree.nodes
image = nodes.new('ShaderNodeTexImage')
image.image = bpy.data.images.load(str(OUT / 'frost-normal.png'))
image.image.colorspace_settings.name = 'Non-Color'
image.image.pack()
normal = nodes.new('ShaderNodeNormalMap')
normal.inputs['Strength'].default_value = .18
glass.node_tree.links.new(image.outputs['Color'], normal.inputs['Color'])
glass.node_tree.links.new(normal.outputs['Normal'], nodes.get('Principled BSDF').inputs['Normal'])

def lathe(name, profile, material, parent, n=160):
    # Closed meridian, sampled without coincident quadrant endpoints.
    if profile[0] == profile[-1]: profile = profile[:-1]
    vertices=[]; rings=[]; faces=[]
    for z,r in profile:
        points=[(0,0,z)] if r == 0 else [(r*math.cos(i*math.tau/n),r*math.sin(i*math.tau/n),z) for i in range(n)]
        rings.append(list(range(len(vertices),len(vertices)+len(points))));vertices.extend(points)
    for a,b in zip(rings,rings[1:]+rings[:1]):
        if len(a)==len(b)==1: continue
        for i in range(n):
            j=(i+1)%n
            faces.append((a[0],b[j],b[i]) if len(a)==1 else (a[i],a[j],b[0]) if len(b)==1 else (a[i],a[j],b[j],b[i]))
    return m.mesh(name,vertices,faces,material,parent)

lathe('Daily wide smooth white closure and stepped pedestal', [
    (1.828,.274),(1.828,.322),(1.835,.338),(1.851,.345),
    (2.096,.345),(2.115,.338),(2.128,.321),(2.128,.230),
    (2.175,.230),(2.185,.219),(2.185,.183),(2.224,.183),
    (2.235,.170),(2.235,.065),(2.087,.065),(2.087,.274),(1.828,.274)
], white, 'Closure', 160)
lathe('Daily short hollow pump connector illustration', [
    (2.110,.035),(2.110,.056),(2.312,.056),(2.326,.048),
    (2.326,.035),(2.110,.035)
], stemwhite, 'PumpStem', 128)

def head_ring(z, r, extension=0, slope=0, count=160):
    if r == 0: return [(0,0,z)]
    points=[]
    for i in range(count):
        theta=i*math.tau/count
        bulge=extension*math.exp(-(math.sin(theta)/.48)**8) if math.cos(theta)>0 else 0
        x=(r+bulge)*math.cos(theta)
        points.append((x,r*math.sin(theta),z+slope*x))
    return points
profiles=[
    (2.275,.145,0,0),(2.285,.157,0,0),(2.530,.157,0,0),
    (2.550,.160,.045,0),(2.565,.160,.104,0),
    (2.625,.160,.104,.14),(2.645,.152,.097,.14),
    (2.651,0,0,0),(2.615,0,0,0),(2.615,.118,0,0),
    (2.285,.118,0,0),(2.275,.118,0,0)
]
vs=[];rings=[];faces=[]
for profile in profiles:
    points=head_ring(*profile);rings.append(list(range(len(vs),len(vs)+len(points))));vs.extend(points)
for a,b in zip(rings,rings[1:]+rings[:1]):
    if len(a)==len(b)==1: continue
    for i in range(160):
        j=(i+1)%160
        faces.append((a[0],b[j],b[i]) if len(a)==1 else (a[i],a[j],b[0]) if len(b)==1 else (a[i],a[j],b[j],b[i]))
head=m.mesh('Daily sloped press head with short right nozzle',vs,faces,headwhite,'Actuator')
def clean_solid(obj):
    bm=bmesh.new();bm.from_mesh(obj.data)
    bmesh.ops.remove_doubles(bm,verts=list(bm.verts),dist=1e-7)
    bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces))
    bad_edges=[e for e in bm.edges if not e.is_manifold]
    assert not bad_edges, (obj.name,len(bad_edges),[(len(e.link_faces),[tuple(v.co) for v in e.verts]) for e in bad_edges[:3]])
    assert bm.calc_volume(signed=True)>0, obj.name
    assert all(f.calc_area()>1e-12 for f in bm.faces), obj.name
    bm.to_mesh(obj.data);bm.free();obj.data.update()
clean_solid(head)
# The visible small side outlet is a blind recess; the unseen internal passage remains illustrative.
bpy.ops.mesh.primitive_uv_sphere_add(segments=32,ring_count=16,radius=1,location=(.264,0,2.596))
cutter=bpy.context.object;cutter.name='Temporary dispensing recess';cutter.scale=(.048,.033,.014)
bpy.ops.object.transform_apply(location=False,rotation=False,scale=True)
bpy.context.view_layer.objects.active=head
mod=head.modifiers.new('Small visible outlet recess','BOOLEAN');mod.operation='DIFFERENCE';mod.solver='EXACT';mod.object=cutter
bpy.ops.object.modifier_apply(modifier=mod.name)
bpy.data.objects.remove(cutter,do_unlink=True)
clean_solid(head)

lathe('Daily hollow clear overcap with soft top and mould dimple', [
    (2.116,.294),(2.116,.307),(2.123,.314),(2.145,.314),
    (2.153,.310),(2.751,.310),(2.775,.307),(2.788,.300),
    (2.797,.287),(2.800,.262),(2.800,.060),(2.798,.025),(2.797,0),
    (2.779,0),(2.779,.060),(2.779,.257),(2.775,.279),
    (2.765,.289),(2.747,.294),(2.151,.294),(2.116,.294)
],cover,'Overcap',192)

surface=lambda x,z:-.290
for name,mat,group,offset in [
    ('Daily blank transparent carrier',film,'PaperLabel',.0014),
    ('Daily liaose independent brand',brand,'LogoPrint',.0022),
    ('Daily rule DAILY EMULSION FACE CARE independent lettering',names,'ProductPrint',.0030),
]:
    m.sheet(name,.66,.90,.70,surface,mat,group,48,24,offset)

total=2.800
scale=2.9/total
pivots={'Body':0,'Closure':1.97,'PumpStem':2.20,'Actuator':2.45,'Overcap':2.116,'PaperLabel':1.15,'LogoPrint':1.15,'ProductPrint':1.15}
assert set(m.groups)==set(pivots)
solid_checks={}
for name,g in m.groups.items():
    if name not in ['PaperLabel','LogoPrint','ProductPrint']:
        for obj in g.children:
            clean_solid(obj)
            bm=bmesh.new();bm.from_mesh(obj.data)
            solid_checks[obj.name]={'manifold':all(e.is_manifold for e in bm.edges),'positiveVolume':bm.calc_volume(signed=True)>0,'minimumFaceArea':min(f.calc_area() for f in bm.faces)}
            bm.free()
    pivot=Vector((0,0,pivots[name]))
    for obj in g.children:obj.location-=pivot
    g.location=pivot*scale;g.scale=(scale,)*3
bpy.context.view_layer.update()
bounds={}
for name,g in m.groups.items():
    points=[o.matrix_world@v.co for o in g.children for v in o.data.vertices]
    bounds[name]={'min':[min(p[i] for p in points) for i in range(3)],'max':[max(p[i] for p in points) for i in range(3)]}
assert abs(max(b['max'][2] for b in bounds.values())-2.9)<1e-6
assert len(solid_checks)==5
assert 2.779-max(v.co.z for v in head.data.vertices)>.075, 'Cover roof must clear the press head.'
glb=PUBLIC/(ID+'.glb')
bpy.ops.object.select_all(action='SELECT')
bpy.ops.export_scene.gltf(filepath=str(glb),export_format='GLB',use_selection=True,export_apply=True,export_yup=True,export_extras=True)
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/(ID+'.blend')))
shutil.copy2(OUT/'reference.png',PUBLIC/'reference.png')

parts=[
    part('overcap','Overcap','透明保护罩','Clear cover','薄壁透明罩向上移开，保留圆顶和底沿。','A hollow clear cover lifts away.'),
    part('head','Actuator','白色短嘴泵头','White actuator','斜面按压头与朝右短嘴一起分离。','The sloped white actuator and short right-facing outlet separate.'),
    part('stem','PumpStem','连接泵杆','Connector','独立短连接杆，隐藏结构为示意。','An independent short connector; the concealed fit is illustrative.'),
    part('closure','Closure','白色盖座','White closure','光滑宽盖座及泵头底座向上分离。','The wide smooth closure and stepped pump pedestal lift away.'),
    part('body','Body','磨砂空玻璃瓶','Frosted glass','扁圆角方形玻璃、短肩与厚底，不含乳液。','An empty flat rounded glass bottle with frosted walls and a thick base.'),
    part('label','PaperLabel','透明底材','Clear carrier','无字透明膜示意，闭合时几乎不可见。','An unprinted transparent carrier, nearly invisible when closed.'),
    part('print','LogoPrint','品牌字','Brand','liaose独立离开瓶身，比底材更向外展开。','The liaose mark moves farther outward than the carrier.'),
    part('name','ProductPrint','产品名','Product name','横线、DAILY EMULSION及FACE CARE一同展开。','The rule, DAILY EMULSION and FACE CARE move as one print layer.'),
]
for p,short in zip(parts,['罩盖','泵头','泵杆','盖座','瓶身','标贴','品牌','品名']):p['short'][0]=short
review={'parts':parts,'appearance':{'glass':True,'frosted':True,'clearOvercap':True,'pipette':False,'clearLabel':True,'metal':False},'explosion':{'offsets':{'overcap':[0,4.55,0],'head':[0,2.65,0],'stem':[0,1.55,0],'closure':[0,.80,0],'label':[-.85,.03,.70],'print':[-1.90,.30,1.90],'name':[-1.90,-.12,1.90]},'scales':{'label':1.10,'print':1.50,'name':1.55},'timing':{'overcap':[0,.65]},'camera':{'centerY':[1.45,3.66],'centerX':[0,-.90],'height':[3.7,8.05],'width':[2.1,5.1]}}}
config={'product':{'file':ID+'.glb','kind':'collection','scale':1,'parts':parts,'review':review},'design':{'name':'Daily Emulsion','background':'#e9e5d8','ink':'#34372e'}}
source=CLIENT/'review-source'/ID;source.mkdir(parents=True,exist_ok=True)
(source/'review-config.json').write_text(json.dumps(config,ensure_ascii=False,indent=2)+'\n')
(OUT/'review-config.json').write_text(json.dumps(review,ensure_ascii=False,indent=2)+'\n')
info={'id':ID,'state':'local-review','productCount':1,'bottleCount':1,'height':2.9,'components':list(m.groups),'componentBoundsBlenderXYZ':bounds,'normalizationScale':scale,'closedHeightToWidth':total,'bodyDepthToWidth':.58,'visibleGlassHeightToWidth':1.84,'actualGlassHeightToWidth':1.972,'glassBaseToWidth':.14,'closureDiameterToWidth':.69,'visibleClosureHeightToWidth':.30,'coverDiameterToWidth':.628,'coverHeightToWidth':.684,'containsFormula':False,'bodyFrosted':True,'coverClear':True,'colorlessGlass':True,'separateLabelBrandAndName':True,'printIncludes':['liaose','horizontal rule','DAILY EMULSION','FACE CARE'],'noInventedCapacity':True,'illustrativeDimensions':True,'hiddenStructure':'Depth, glass wall, screw fit and short connector are indicative; no liquid, long dip tube or unseen elaborate mechanism. The visible actuator outlet is a shallow recess. The transparent unprinted carrier explains separated print layers; the reference has no paper-label border.','solidChecks':solid_checks,'referenceSha256':hashlib.sha256((OUT/'reference.png').read_bytes()).hexdigest(),'glbSha256':hashlib.sha256(glb.read_bytes()).hexdigest(),'glbBytes':glb.stat().st_size,'generator':Path(__file__).name,'generatorDependencies':['tail_model_helpers.py']}
(OUT/'model-info.json').write_text(json.dumps(info,ensure_ascii=False,indent=2)+'\n')
(OUT/'README.md').write_text('''# Daily Emulsion — local single-bottle review

One empty bottle, calibrated to the supplied reference. Eight independent roots: Body, Closure, PumpStem, Actuator, Overcap, PaperLabel, LogoPrint, ProductPrint. The glass body is neutral frosted glass; the protective cover is clear. All lettering remains separate from the unprinted clear carrier.

Rebuild with Blender 4.5: `Blender --background --python-exit-code 1 --python build_daily_emulsion.py` from the collection directory. The existing Node/Sharp runtime converts the three SVGs; `tail_model_helpers.py` supplies manifold lofts and the approved liaose vector. Source, packed blend, SVG/PNG artwork, normal map, measurements and review config are retained here.

The single front photo is a visual reference, not manufacturing data. Body depth, wall thickness, screw fit and short concealed connector are indicative. There is no formula, milk-coloured fill, capacity text or additional bottle. The apparent milky reference contents are intentionally absent. Inspect closed, fully separated and rotated views before publication.
''')
print('Daily Emulsion ready:',glb.stat().st_size,'bytes',info['glbSha256'])
