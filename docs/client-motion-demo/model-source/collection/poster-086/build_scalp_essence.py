"""Reference-calibrated empty Scalp Essence packaging, five reviewable groups.
The closed reference does not establish the hidden dispensing mechanism.
"""
import json, math, sys, subprocess, xml.etree.ElementTree as ET
from pathlib import Path
import bpy
from mathutils import Vector
OUT=Path(__file__).resolve().parent
BASE=OUT.parent
sys.path.insert(0,str(BASE))
from tail_model_helpers import Model,NODE
GLB=BASE.parents[1]/'packaging-assets/poster-086-v1.glb'
class Essence(Model):
 def __init__(self): self.out=OUT;self.groups={}

bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.context.preferences.filepaths.save_version=0
model=Essence()
ivory=model.mat('Warm ivory satin exterior','#e7dfce',.32,metal=.10)
bronze=model.mat('Copper brown satin decorative label','#ab7957',.34,metal=.62)
inner=model.mat('Ivory cap liner','#d8d0bf',.42)
# Width one, total height 4.40. The underlying body is empty, with an open neck.
profile=[(0,0),(0,.43),(.008,.465),(.025,.486),(.055,.498),(.09,.50),(2.965,.50),(2.99,.492),(3.005,.46),(3.015,.30),(3.05,.26),(3.18,.26),(3.19,.245),(3.19,.218),(3.04,.218),(2.99,.28),(2.96,.445),(.10,.455),(.075,.42),(.075,0)]
model.lathe('Empty cylindrical bottle | rounded heel and hollow neck',profile,ivory,'Body',192)
# Long cap, liner and attachment sleeve remain one recognizable assembly.
cap=[(3.025,.473),(3.025,.491),(3.04,.50),(4.33,.50),(4.37,.488),(4.39,.46),(4.40,.42),(4.40,0),(4.35,0),(4.35,.42),(4.33,.452),(3.05,.473),(3.025,.473)]
model.lathe('Complete long cap | continuous satin shell',cap,ivory,'Cap',192)
model.lathe('Integrated cap liner',[(3.05,.276),(3.05,.298),(3.28,.298),(3.30,.276),(3.05,.276)],inner,'Cap',128)
# Real opaque front wrap, with a thin physical edge. Unlike ink it casts a shadow.
vs=[];fs=[];n=192;low=.065;high=1.65;angle=math.radians(135)
for radius in [.501,.505]:
 for z in [low,high]:
  for i in range(n+1):
   a=-angle+2*angle*i/n;vs.append((radius*math.sin(a),-radius*math.cos(a),z))
step=n+1
for i in range(n):
 fs.extend([(i,i+1,step+i+1,step+i),(2*step+i,3*step+i,3*step+i+1,2*step+i+1),
            (i,2*step+i,2*step+i+1,i+1),(step+i,step+i+1,3*step+i+1,3*step+i)])
fs.extend([(0,step,3*step,2*step),(n,2*step+n,3*step+n,step+n)])
label=model.mesh('Copper decorative label | physical curved surface',vs,fs,bronze,'Label')
import bmesh
bm=bmesh.new();bm.from_mesh(label.data);bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));assert all(e.is_manifold for e in bm.edges);assert bm.calc_volume(signed=True)>0;bm.to_mesh(label.data);bm.free()
path=next(e.attrib['d'] for e in ET.parse(BASE/'poster-073/print.svg').getroot().iter() if e.tag.endswith('path'))
art={'logo':f'<svg xmlns="http://www.w3.org/2000/svg" width="1360" height="500" viewBox="0 0 340 125"><path d="{path}" fill="#21170f"/></svg>',
'name':'<svg xmlns="http://www.w3.org/2000/svg" width="1200" height="480"><g text-anchor="middle" fill="#fff8eb" font-family="Helvetica Neue,Arial"><text x="600" y="180" font-size="100" letter-spacing="10">SCALP ESSENCE</text><text x="600" y="340" font-size="53" letter-spacing="18">HAIR CARE</text></g></svg>'}
for name,svg in art.items():
 p=OUT/(name+'.svg');p.write_text(svg)
 subprocess.run([NODE,'--input-type=module','-e',"import sharp from '/Users/icecream/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/sharp/dist/index.mjs';await sharp(process.argv[1]).png().toFile(process.argv[2]);",str(p),str(p.with_suffix('.png'))],check=True)
front=lambda x,z:-math.sqrt(.50**2-x*x)
for node,file,w,h,z,offset in [('LogoInk','logo',.68,.25,2.34,.003),('NameInk','name',.73,.292,.64,.008)]:
 mat=model.texture(file+' printed ink',file+'.png',.55);mat.use_backface_culling=True
 ob=model.sheet(file+' independent curved lettering',w,h,z,front,mat,node,96,32,offset);ob.visible_shadow=False
pivots={'Body':(0,0,1.5),'Cap':(0,0,3.7),'Label':(0,0,.85),'LogoInk':(0,0,2.465),'NameInk':(0,0,.786)}
for key,g in model.groups.items():
 pivot=Vector(pivots[key]);g['partKey']=key
 for child in g.children:child.location-=pivot
 g.location=pivot
bpy.context.view_layer.update()
bounds={k:{'min':[min((o.matrix_world@v.co)[a] for o in g.children for v in o.data.vertices) for a in range(3)],'max':[max((o.matrix_world@v.co)[a] for o in g.children for v in o.data.vertices) for a in range(3)]} for k,g in model.groups.items()}
assert set(bounds)==set(pivots)
assert abs(bounds['Cap']['max'][2]-4.4)<1e-5 and abs(bounds['Body']['min'][2])<1e-5
assert label.visible_shadow
bpy.ops.object.select_all(action='SELECT')
bpy.ops.export_scene.gltf(filepath=str(GLB),export_format='GLB',use_selection=True,export_yup=True,export_extras=True,export_animations=False)
cfg=json.loads((OUT/'review-product.json').read_text());mapping={p['node']:p['key'] for p in cfg['parts']}
for node,g in model.groups.items():
 key=mapping[node];x,y,z=cfg['review']['explosion']['offsets'][key];scale=cfg['review']['explosion']['scales'].get(key,1);start=g.location.copy()
 for frame,t in [(1,0),(31,.5),(61,1)]:
  g.location=start+Vector((x,-z,y))*t;g.scale=(1+(scale-1)*t,)*3
  g.keyframe_insert(data_path='location',frame=frame);g.keyframe_insert(data_path='scale',frame=frame)
scene=bpy.context.scene;scene.name='Scalp Essence | physical label shadow';scene.frame_end=61;scene.frame_set(1)
bpy.ops.object.select_all(action='DESELECT')
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'poster-086-v1.blend'),compress=True)
info={'id':'poster-086','file':GLB.name,'blender':bpy.app.version_string,'components':list(model.groups),'componentBoundsBlenderXYZ':bounds,'containsFormula':False,'illustrativeDimensions':True,'heightToDiameter':4.4,'capHeightFraction':(4.4-3.025)/4.4,'lowerCopperHeightFraction':1.65/4.4,'labelCastsShadow':True,'inkCastsShadow':False,'sourcePoster':'scalp-essence-poster-v2.png','hiddenMechanism':'Not inferred from a closed reference; complete cap and empty bottle only.'}
(OUT/'model-info.json').write_text(json.dumps(info,indent=2)+'\n')
print('SCALP MODEL READY',GLB.stat().st_size)
