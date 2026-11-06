"""Model the poster-080 oval dispenser once; package its three finishes as standard glTF scenes."""
import json
import math
import struct
import sys
from pathlib import Path

import bpy
from mathutils import Matrix, Vector

BASE = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE))
from tail_model_helpers import Model

OUT = BASE / 'poster-080'
GLB = BASE.parents[1] / 'packaging-assets/poster-080-v2.glb'
FINISHES = ('soap', 'after', 'baby')
GROUPS = ('Body', 'Pump', 'Label', 'LogoInk', 'NameInk')
# Translations in the viewer's Y-up coordinates, with scale about each part's own centre.
POSE = {'Body': ((0, 0, 0), 1), 'Pump': ((0, 2.62, 0), 1),
        'Label': ((-1.03, .03, .68), 1.06), 'LogoInk': ((-2.10, .22, 1.47), 1.24),
        'NameInk': ((-2.12, -.09, 1.92), 1.28)}
PIVOTS = {'Body': 1.15, 'Pump': 2.40, 'Label': 1.23, 'LogoInk': 1.91, 'NameInk': 1.12}

class BathBottle(Model):
    # This product uses the approved geometric wordmark, not the handwritten archive logo.
    def __init__(self):
        self.out = OUT
        self.groups = {}

def signed_power(x, exponent):
    return math.copysign(abs(x) ** exponent, x)

def ring_mesh(name, rows, material, parent, sections=72, axis='z'):
    """Surface of a continuous sequence of superelliptic rings with optional point end caps."""
    verts, faces, rings = [], [], []
    for height, a, b, power, dx, dy in rows:
        ids = []
        for i in range(sections if a and b else 1):
            theta = math.tau * i / sections
            x = a * signed_power(math.cos(theta), 2 / power) + dx
            y = b * signed_power(math.sin(theta), 2 / power) + dy
            ids.append(len(verts))
            verts.append((x, y, height) if axis == 'z' else (height, x, y))
        rings.append(ids)
    for a, b in zip(rings, rings[1:]):
        for i in range(sections):
            j = (i + 1) % sections
            if len(a) == 1: faces.append((a[0], b[j], b[i]))
            elif len(b) == 1: faces.append((a[i], a[j], b[0]))
            else: faces.append((a[i], a[j], b[j], b[i]))
    return model.mesh(name, verts, faces, material, parent)

def shell():
    # Outer heel → foot → broad side → short shoulder → mouth → inner wall → raised base.
    profiles = [
        (.056,0,0,2),(.056,.28,.12,2.5),(.044,.53,.26,2.5),
        (.023,.602,.324,2.5),(.006,.62,.332,2.5),(.003,.635,.344,2.5),
        (.007,.649,.352,2.5),(.023,.666,.363,2.5),(.057,.685,.373,2.5),
        (.109,.694,.38,2.5),(.19,.697,.381,2.5),(.55,.701,.382,2.5),
        (1.16,.705,.384,2.5),(1.72,.706,.385,2.5),(1.98,.705,.384,2.5),
        (2.085,.701,.382,2.5),(2.145,.690,.377,2.5),(2.187,.667,.366,2.5),
        (2.213,.626,.349,2.5),(2.235,.54,.311,2.45),(2.252,.37,.257,2.25),
        (2.260,.217,.208,2),(2.269,.190,.19,2),(2.282,.178,.178,2),
        (2.302,.178,.178,2),(2.311,.188,.188,2),(2.325,.188,.188,2),
        (2.336,.178,.178,2),(2.380,.178,.178,2),(2.392,.182,.182,2),
        (2.405,.182,.182,2),(2.411,.177,.177,2),(2.411,.151,.151,2),
        (2.402,.145,.145,2),(2.293,.145,.145,2),(2.255,.151,.151,2),
        (2.237,.210,.198,2),(2.218,.36,.234,2.3),(2.195,.53,.287,2.4),
        (2.171,.61,.318,2.5),(2.133,.655,.343,2.5),(2.079,.672,.351,2.5),
        (1.96,.678,.355,2.5),(1.16,.680,.355,2.5),(.27,.674,.351,2.5),
        (.155,.663,.345,2.5),(.105,.634,.320,2.5),(.089,.55,.275,2.5),
        (.099,.38,.18,2.5),(.112,0,0,2)]
    return ring_mesh('Seamless flacon | open mouth and recessed heel',
                     [(*p, 0, 0) for p in profiles], slate, 'Body', 112)

def tube():
    # Two continuous surfaces joined at the angled pickup end; no loose pump parts.
    rows = []
    for z,r in [(1.98,.032),(1.75,.032),(1.35,.032),(.90,.032),(.55,.032),(.32,.032),
                (.19,.032),(.115,.032),(.115,.023),(.19,.023),(.32,.023),(.55,.023),
                (.90,.023),(1.35,.023),(1.75,.023),(1.98,.023),(1.98,.032)]:
        drift = .133 * (max(0,1.90-z)/1.79)**1.75
        rows.append((z,r,r,2,drift,.012*drift))
    ob = ring_mesh('Connected hollow dip tube | slant-cut intake', rows, clear_tube, 'Pump', 40)
    for v in ob.data.vertices:
        if v.co.z < .12: v.co.z += (v.co.x-.133)*.50
    # Tube rows run down the outside, so invert the whole winding.
    ob.data.flip_normals()
    return ob

def bottle_front(x,z):
    # Sidewall is almost parallel over the printed area, with gently rounded lateral edges.
    return -.384 * (1 - abs(x/.705)**2.5)**.4

def material_for_text(name, path):
    m = model.texture(name, path, .68)
    m.use_backface_culling = True
    return m

def label_text():
    from tail_model_helpers import NODE
    import subprocess
    # Preserve clean, small, high-resolution utility type in its own print group.
    for variant, words in [('wash','BODY WASH'), ('lotion','BODY LOTION')]:
        svg = ('<svg xmlns="http://www.w3.org/2000/svg" width="560" height="228" viewBox="0 0 560 228">'
               f'<g fill="#181512" font-family="Helvetica Neue,Arial,sans-serif" text-anchor="middle">'
               f'<text x="280" y="83" font-size="75">{words}</text>'
               '<text x="280" y="203" font-size="68">300 ml</text></g></svg>')
        source = OUT/f'spec-{variant}.svg'; source.write_text(svg)
        subprocess.run([NODE, '--input-type=module','-e',
            "import sharp from '/Users/icecream/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/sharp/dist/index.mjs';await sharp(process.argv[1]).png().toFile(process.argv[2]);",
            str(source), str(source.with_suffix('.png'))],check=True)

def sheet(name,width,height,bottom,mat,parent,clearance):
    return model.sheet(name,width,height,bottom,bottle_front,mat,parent,nx=32,ny=8,offset=clearance)

def rounded_carrier():
    # A thin removable carrier illustrates the printing region. The assembled pack reads as direct ink.
    nx, ny, halfw, halfh, corner = 44, 42, .49,.88,.075
    vs,fs=[],[]
    for j in range(ny+1):
        dz=(2*j/ny-1)*halfh; z=1.21+dz
        ry=max(0,abs(dz)-(halfh-corner))
        w=halfw-corner+math.sqrt(max(0,corner**2-ry**2))
        for i in range(nx+1):
            x=(2*i/nx-1)*w
            vs.append((x,bottle_front(x,z)-.003,z))
    for j in range(ny):
        for i in range(nx):
            a=j*(nx+1)+i;fs.append((a,a+1,a+nx+2,a+nx+1))
    model.mesh('Transparent print carrier | rounded corners',vs,fs,film,'Label')

def split_gltf_scenes(path):
    # Blender exports one active scene. Keep its shared buffers and meshes, split only the root node list.
    raw=path.read_bytes()
    header=struct.Struct('<II')
    n,typ=header.unpack_from(raw,12)
    assert typ==0x4e4f534a
    doc=json.loads(raw[20:20+n]); binary=raw[20+n:]
    scene_roots=doc['scenes'][doc.get('scene',0)]['nodes']
    roots={doc['nodes'][idx]['name']:idx for idx in scene_roots}
    assert len(roots)==len(GROUPS)*len(FINISHES),list(roots)
    doc['scenes']=[{'name':finish,'nodes':[roots[f'{p}_{finish.title()}'] for p in GROUPS]}
                   for finish in FINISHES]
    doc['scene']=0
    entry=json.dumps(doc,separators=(',',':'),ensure_ascii=False).encode()
    entry+=b' '*((-len(entry))%4)
    body=header.pack(len(entry),0x4e4f534a)+entry+binary
    path.write_bytes(struct.pack('<4sII',b'glTF',2,len(body)+12)+body)
    assert all(doc['nodes'][i]['extras']['partKey']==part for s in doc['scenes']
               for i,part in zip(s['nodes'],GROUPS))
    return doc

def animate(group, key):
    start=group.location.copy()
    (x,y,z),scale=POSE[key]
    for frame,t in [(1,0),(31,.5),(61,1)]:
        group.location=start+Vector((x,-z,y))*t
        group.scale=(1+(scale-1)*t,)*3
        group.keyframe_insert(data_path='location',frame=frame)
        group.keyframe_insert(data_path='scale',frame=frame)

bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.context.preferences.filepaths.save_version=0
default_scene=bpy.context.scene
model=BathBottle()
slate=model.mat('After Bath | smoky slate satin','#728797',.31,.31)
ivory=model.mat('Body lotion | opaque warm ivory satin','#eeeade',.34)
pump_clear=model.mat('After Bath | translucent pearl dispenser','#dbe2e4',.27,.63)
pump_white=model.mat('Body lotion | ivory dispenser','#f2ede2',.28)
clear_tube=model.mat('Hollow clear polyethylene dip tube','#edf2f1',.15,.80)
film=model.mat('Unprinted clear carrier','#dfebe9',.37)
bsdf=film.node_tree.nodes.get('Principled BSDF')
bsdf.inputs['Alpha'].default_value=.014
bsdf.inputs['Specular IOR Level'].default_value=.13
film.surface_render_method='DITHERED'
shell()
model.lathe('Smooth collar | rolled lower and upper edges',[
 (2.253,.205),(2.253,.23),(2.262,.244),(2.277,.25),(2.34,.251),(2.44,.251),
 (2.48,.246),(2.501,.235),(2.507,.18),(2.507,.145),(2.474,.144),(2.47,.205),(2.253,.205)],pump_clear,'Pump',80)
model.lathe('Stepped actuator base and piston',[
 (2.47,0),(2.47,.186),(2.492,.201),(2.525,.208),(2.539,.202),(2.546,.175),
 (2.61,.174),(2.626,.165),(2.626,.104),(2.74,.103),(2.74,0)],pump_clear,'Pump',72)
model.lathe('One-piece pump barrel and tube socket',[
 (1.89,0),(1.89,.05),(1.91,.068),(1.98,.068),(2.015,.099),(2.17,.104),
 (2.215,.137),(2.25,.137),(2.27,.171),(2.45,.171),(2.45,0)],pump_clear,'Pump',64)
tube()
model.lathe('Actuator disk | shallow circular pressing deck',[
 (2.704,0),(2.704,.189),(2.71,.247),(2.722,.285),(2.74,.308),(2.759,.319),
 (2.858,.319),(2.878,.310),(2.888,.282),(2.897,.200),(2.900,0)],pump_clear,'Pump',96)
spout_rows=[
 (.12,0,0,2,0,2.787),(.16,.131,.062,4,0,2.786),(.29,.116,.059,4,0,2.78),
 (.42,.110,.054,4,0,2.766),(.565,.106,.052,4,0,2.742),(.587,.104,.051,4,0,2.739),
 (.591,.103,.050,4,0,2.738),(.591,.077,.024,3.2,0,2.738),(.581,.076,.023,3.2,0,2.740),
 (.49,.076,.023,3.2,0,2.754),(.48,0,0,2,0,2.755)]
spout=ring_mesh('Spout | sloping paddle with open dispensing aperture',spout_rows,pump_clear,'Pump',64,'x')
rounded_carrier()
label_text()
logo_mat=material_for_text('Heavy liaose wordmark', 'logo.png')
sheet('Bottle shoulder | liaose',.598,.598*bpy.data.images['logo.png'].size[1]/bpy.data.images['logo.png'].size[0],
      1.832,logo_mat,'LogoInk',.008)
names={}
for finish,file,width in [('after','after-bath.png',.770),('soap','soap-clean-soap.png',.777),('baby','baby-blusher.png',.941)]:
    mat=material_for_text(f'{finish} | bold product typography',file)
    img=mat.node_tree.nodes.get('Image Texture').image
    names[finish]=sheet(f'{finish} product name',width,width*img.size[1]/img.size[0],
                        1.13-width*img.size[1]/img.size[0]/2,mat,'NameInk',.008)
spec=sheet('Type and capacity',.50,.204,.407,material_for_text('Body wash | small print',
           'spec-wash.png'),'NameInk',.008)
lotion_spec=material_for_text('Body lotion | small print','spec-lotion.png')
# Reuse the same mesh data in all three finishes; only object material slots and the spout direction change.
for finish in FINISHES:
    suffix=finish.title()
    for key in GROUPS:
        group=bpy.data.objects.new(f'{key}_{suffix}',None);bpy.context.collection.objects.link(group)
        group['partKey']=key
        group.location.z=PIVOTS[key]
        for source in list(model.groups[key].children):
            if source in names.values() and source!=names[finish]: continue
            child=source.copy()
            child.name=f'{source.name} ({suffix})'
            bpy.context.collection.objects.link(child);child.parent=group
            child.location.z=-PIVOTS[key]
            if child.data==spout.data and finish=='soap':child.rotation_euler.z=math.pi
            if finish!='after':
                slot=child.material_slots[0];orig=slot.material;slot.link='OBJECT'
                if source==spec:slot.material=lotion_spec
                elif orig==slate:slot.material=ivory
                elif orig==pump_clear:slot.material=pump_white
                else:slot.material=orig

for old_group in model.groups.values():
    for child in list(old_group.children):bpy.data.objects.remove(child,do_unlink=True)
    bpy.data.objects.remove(old_group,do_unlink=True)
bpy.context.view_layer.update()
bpy.ops.object.select_all(action='SELECT')
bpy.ops.export_scene.gltf(filepath=str(GLB),export_format='GLB',use_selection=True,export_apply=False,
                          export_yup=True,export_extras=True,export_animations=False)
doc=split_gltf_scenes(GLB)
# A direct-print reference has almost no visible film at rest.
for frame, opacity in [(1,.014),(31,.09),(61,.17)]:
    bsdf.inputs['Alpha'].default_value=opacity
    bsdf.inputs['Alpha'].keyframe_insert(data_path='default_value',frame=frame)
# Give Blender reviewers independently selectable scenes; open on the approved white Soap finish.
default_scene.name='after'
for finish in FINISHES:
    sc=default_scene if finish=='after' else bpy.data.scenes.new(finish)
    for key in GROUPS:
        group=bpy.data.objects[f'{key}_{finish.title()}']
        if finish!='after':
            for ob in [group,*group.children]:
                for coll in list(ob.users_collection):coll.objects.unlink(ob)
                sc.collection.objects.link(ob)
        animate(group,key)
    sc.frame_end=61; sc.frame_set(1)
    sc.world=bpy.data.worlds.get('World') or bpy.data.worlds.new('World')
bpy.context.window.scene=bpy.data.scenes['soap']
for screen in bpy.data.screens:
    for area in screen.areas:
        if area.type=='VIEW_3D':
            space=area.spaces.active
            space.region_3d.view_location=(0,0,1.52);space.region_3d.view_distance=5.3
            space.region_3d.view_rotation=(Vector((.18,-1,.13))*5).to_track_quat('Z','Y')
            space.region_3d.view_perspective='ORTHO';space.overlay.show_overlays=False
            space.shading.type='MATERIAL'
bpy.ops.object.select_all(action='DESELECT')
default_scene.frame_set(1)
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'poster-080-v2.blend'),compress=True)
info={'id':'poster-080','name':'Bath Trio','file':GLB.name,'height':2.9,'width':1.412,'depth':.77,
      'containsFormula':False,'illustrativeDimensions':True,'source':'build_bath_trio.py',
      'finishScenes':list(FINISHES),'defaultFinish':'soap','components':list(GROUPS),'singleSharedBottleGeometry':True,
      'attachedTube':True,'separateLabelAndPrint':True,'blenderVersion':bpy.app.version_string}
(OUT/'model-info.json').write_text(json.dumps(info,indent=2)+'\n')
print('Bath Trio:',len(doc['meshes']),'glTF meshes,',len(doc['accessors']),'accessors;',GLB.stat().st_size,'bytes')
