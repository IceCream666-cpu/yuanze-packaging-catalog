"""081 v2: restrained woven sleeve revision, unchanged clear vessel and complete pump."""
import bpy,bmesh,json,math,shutil,struct,zlib,hashlib
import numpy as np
from pathlib import Path
from mathutils import Vector

HERE=Path(__file__).resolve().parent; OLD=HERE.parent; CLIENT=HERE.parents[3]
GLB=CLIENT/'packaging-assets/poster-081-v2.glb'
bpy.ops.wm.open_mainfile(filepath=str(OLD/'poster-081-v1.blend'))
bpy.context.preferences.filepaths.save_version=0
scene=bpy.context.scene;scene.frame_set(1);bpy.context.view_layer.update()
roots={name:bpy.data.objects[name] for name in ['Body','Pump','Label','LogoInk','NameInk']}
def points(o):return [o.matrix_world@v.co for v in o.data.vertices]
preserved={o.name:[list(p) for p in points(o)] for root in ['Body','Pump'] for o in roots[root].children
           if o.name!='Complete dispenser barrel and tube socket'}

def fix(o):
    bm=bmesh.new();bm.from_mesh(o.data)
    bmesh.ops.remove_doubles(bm,verts=list(bm.verts),dist=1e-7)
    bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces))
    assert all(e.is_manifold for e in bm.edges),o.name
    volume=bm.calc_volume(signed=True);assert volume>0,(o.name,volume)
    bm.to_mesh(o.data);bm.free();o.data.update();return volume

def png(path,array):
    h,w,c=array.shape
    def chunk(t,data):return struct.pack('>I',len(data))+t+data+struct.pack('>I',zlib.crc32(t+data)&0xffffffff)
    raw=b''.join(b'\0'+row.tobytes() for row in array)
    path.write_bytes(b'\x89PNG\r\n\x1a\n'+chunk(b'IHDR',struct.pack('>IIBBBBB',w,h,8,2,0,0,0))+
                     chunk(b'IDAT',zlib.compress(raw,9))+chunk(b'IEND',b''))

# A seamless physical weave tile replaces the high-entropy panoramic maps.
# 60 yarns per tile, four tiles per circumference; equal physical X/Y pitch.
n=512;y,x=np.mgrid[0:n,0:n];u=x*60/n;v=y*60/n
alternate=(np.floor(u).astype(int)+np.floor(v).astype(int))%2
warp=np.sin(math.pi*(u%1))**.70;weft=np.sin(math.pi*(v%1))**.70
height=np.where(alternate==0,.78*warp+.12*weft,.78*weft+.12*warp)
# Fine periodic fibres, rather than random grit. Both texture edges tile exactly.
fibre=.018*np.sin(x*math.tau*173/n)*np.sin(y*math.tau*211/n)
height+=fibre
shade=np.clip(.84+.15*height,.80,.995)
png(HERE/'linen-color.png',np.clip(shade[...,None]*np.array([246,236,215]),0,255).astype('uint8'))
png(HERE/'black-linen.png',np.clip((.60+.40*height)[...,None]*np.array([22,24,20]),0,255).astype('uint8'))
gx=(np.roll(height,-1,axis=1)-np.roll(height,1,axis=1))*.5
gy=(np.roll(height,-1,axis=0)-np.roll(height,1,axis=0))*.5
normal=np.dstack([-gx*1.35,-gy*1.35,np.ones((n,n))]);normal/=np.linalg.norm(normal,axis=2)[...,None]
png(HERE/'linen-normal.png',np.clip((normal*.5+.5)*255,0,255).astype('uint8'))
normal_image=bpy.data.images.load(str(HERE/'linen-normal.png'),check_existing=False)
normal_image.colorspace_settings.name='Non-Color';normal_image.pack()
for matname,imagefile in [('Warm ivory woven label','linen-color.png'),('Black woven side flag','black-linen.png')]:
    material=bpy.data.materials[matname];nodes=material.node_tree.nodes;links=material.node_tree.links
    color_image=bpy.data.images.load(str(HERE/imagefile),check_existing=False);color_image.pack()
    for node in nodes:
        if node.type=='TEX_IMAGE':
            node.image=normal_image if node.image and 'normal' in node.image.name else color_image
            node.extension='REPEAT'
        if node.type=='NORMAL_MAP':node.inputs['Strength'].default_value=.84
    p=nodes['Principled BSDF'];p.inputs['Roughness'].default_value=.84
    p.inputs['Specular IOR Level'].default_value=.12
    p.inputs['Sheen Weight'].default_value=.16;p.inputs['Sheen Roughness'].default_value=.86
    for link in list(p.inputs['Alpha'].links):links.remove(link)
    p.inputs['Alpha'].default_value=1
    material.use_backface_culling=False

linen=bpy.data.materials['Warm ivory woven label']; black_linen=bpy.data.materials['Black woven side flag']
def deformation(angle,z):
    t=max(0,min(1,(z-.70)/1.02))
    return .0008*math.sin(3*angle+.4)*math.sin(math.pi*t)
def edge_wave(angle):return .0012*math.sin(5*angle+.8)+.0005*math.sin(11*angle)
def outer_radius(angle,z):return .795+deformation(angle,z)

old=bpy.data.objects['Ivory woven wrap sleeve | soft rolled edges']
# Closed textile wall: rounded top/bottom, dense but restrained low-amplitude curvature.
profile=[(.700,.790),(.7015,.7935),(.705,.795)]
profile.extend((.710+i/24, .795) for i in range(25))
profile.extend([(1.715,.795),(1.7185,.7935),(1.720,.790),
                (1.7185,.7865),(1.715,.785)])
profile.extend((1.710-i/24,.785) for i in range(25))
profile.extend([(.705,.785),(.7015,.7865),(.700,.790)])
sections=192;vs=[];faces=[]
for z,r in profile:
    for i in range(sections+1):
        a=i*math.tau/sections;rr=r+deformation(a,z)
        vs.append((rr*math.sin(a),-rr*math.cos(a),z+edge_wave(a)))
for k in range(len(profile)-1):
    for i in range(sections):
        a=k*(sections+1)+i;faces.append((a,a+1,a+sections+2,a+sections+1))
mesh=bpy.data.meshes.new('Closed woven sleeve with rolled thin edges')
mesh.from_pydata(vs,[],faces);mesh.update()
ob=bpy.data.objects.new('Ivory woven wrap sleeve | soft rolled edges v2',mesh);scene.collection.objects.link(ob)
ob.parent=roots['Label'];ob.location=-roots['Label'].location;mesh.materials.append(linen)
uv=mesh.uv_layers.new(name='Physical woven pitch')
for face in mesh.polygons:
    face.use_smooth=True
    for li in face.loop_indices:
        vi=mesh.loops[li].vertex_index;k=vi//(sections+1);i=vi%(sections+1)
        uv.data[li].uv=(i/sections*4,(profile[k][0]-.70)/(math.tau*.795/4))
label_volume=fix(ob);ob.visible_shadow=True
ob['materialRole']='opaque physical woven textile, casts shadow';ob['innerRadius']=.785;ob['outerRadius']=.795
ob['nominalThickness']=.010;ob['physicalYarnPitch']=math.tau*.795/240
bpy.data.objects.remove(old,do_unlink=True);ob.name='Ivory woven wrap sleeve | soft rolled edges'

# Preserve the visible black flag silhouette, remove the previously buried inner width.
flag=bpy.data.objects['Black woven side flag'];bpy.data.objects.remove(flag,do_unlink=True)
bpy.ops.mesh.primitive_cube_add(size=1,location=(.855,-.1895,1.25));flag=bpy.context.object
flag.name='Black woven side flag';flag.scale=(.166,.008,.72)
bpy.ops.object.transform_apply(location=False,rotation=False,scale=True)
bevel=flag.modifiers.new('Soft thin fabric edge','BEVEL');bevel.width=.0038;bevel.segments=4
bpy.ops.object.modifier_apply(modifier=bevel.name)
def flag_bow(x,z):
    u=max(0,min(1,(x-.772)/.166));v=max(0,min(1,(z-.89)/.72))
    return .0025*math.sin(math.pi*u)*math.sin(math.pi*v)
for vert in flag.data.vertices:
    p=flag.matrix_world@vert.co;vert.co.y+=flag_bow(p.x,p.z)
flag.data.materials.append(black_linen)
if flag.data.uv_layers:flag.data.uv_layers.remove(flag.data.uv_layers[0])
uv=flag.data.uv_layers.new(name='Physical woven pitch')
period=math.tau*.795/4
for face in flag.data.polygons:
    face.use_smooth=False
    for li in face.loop_indices:
        p=flag.matrix_world@flag.data.vertices[flag.data.loops[li].vertex_index].co
        uv.data[li].uv=((p.x-.772)/period,(p.z-.89)/period)
matrix=flag.matrix_world.copy();flag.parent=roots['Label'];flag.matrix_world=matrix
flag_volume=fix(flag);flag.visible_shadow=True;flag['materialRole']='opaque attached black textile flag, casts shadow'

# Original artwork is copied, never redrawn or re-fonted.
artwork=[]
for name in ['logo','name','tag-logo']:
    for suffix in ['svg','png']:shutil.copy2(OLD/(name+'.'+suffix),HERE/(name+'.'+suffix))
    artwork.append({'name':name,'svgUnchanged':True,'pngUnchanged':True,
                    'svgSha256':hashlib.sha256((HERE/(name+'.svg')).read_bytes()).hexdigest()})
for matname,art in [('Separate black liaose ink','logo'),('Separate product name ink','name'),
                   ('Ivory wordmark attached to black side flag','tag-logo')]:
    image=bpy.data.images.load(str(HERE/(art+'.png')),check_existing=False);image.pack()
    for node in bpy.data.materials[matname].node_tree.nodes:
        if node.type=='TEX_IMAGE':node.image=image

for name in ['liaose on woven sleeve','EXFOLIATING HAND GEL']:
    ink=bpy.data.objects[name];inv=ink.matrix_world.inverted()
    for v in ink.data.vertices:
        p=ink.matrix_world@v.co;angle=math.asin(p.x/.795)
        r=outer_radius(angle,p.z);p.y=-math.sqrt(r*r-p.x*p.x)-.0035;v.co=inv@p
    ink.data.update();ink.visible_shadow=False;ink['materialRole']='transparent ink carrier, no rectangle shadow'
tag=bpy.data.objects['liaose on black side flag'];inv=tag.matrix_world.inverted()
for vert in tag.data.vertices:
    p=tag.matrix_world@vert.co;p.y=-.197+flag_bow(p.x,p.z);vert.co=inv@p
tag.data.update();tag.visible_shadow=False;tag['materialRole']='attached transparent side-flag ink, no rectangle shadow'

# Hollow the original socket through its axis; keep the complete exterior unchanged.
barrel=bpy.data.objects['Complete dispenser barrel and tube socket']
def bore(radius,bottom,top,name):
    bpy.ops.mesh.primitive_cylinder_add(vertices=96,radius=radius,depth=top-bottom,location=(0,0,(bottom+top)/2))
    cutter=bpy.context.object
    bpy.ops.object.select_all(action='DESELECT');barrel.select_set(True);bpy.context.view_layer.objects.active=barrel
    mod=barrel.modifiers.new(name,'BOOLEAN');mod.operation='DIFFERENCE';mod.solver='EXACT';mod.object=cutter
    bpy.ops.object.modifier_apply(modifier=mod.name);bpy.data.objects.remove(cutter,do_unlink=True)
    fix(barrel)
bore(.028,1.94,2.45,'Open connector bore')
bore(.0395,1.94,2.22,'Dip tube insertion socket')
barrel['socketBoreRadius']=.028;barrel['insertionRadius']=.0395

bpy.context.view_layer.update()
errors={}
for name,old_points in preserved.items():
    now=points(bpy.data.objects[name]);assert len(now)==len(old_points)
    error=max((p-Vector(q)).length for p,q in zip(now,old_points));assert error==0,(name,error)
    errors[name]=error

config=json.loads((OLD/'review-product.json').read_text());config['file']='poster-081-v2.glb'
config['review']['explosion']['offsets']['label']=[-1.45,.02,.9]
# A full circular sleeve needs the same radial clearance on narrow screens.
config['review']['explosion']['mobilePrintSpread']=1
config['review']['appearance'].update(labelShadows=True,glass=True,frosted=False,referenceGlass=True,
                                    studio={'background':'#d7d8ca','ink':'#243025'})
for part in config['parts']:
    if part['key']=='label':part['detail']=['米白织物环标保留真实薄边、经纬织纹与投影，黑色侧旗及其白字一起展开。',
        'The ivory woven sleeve retains thin rolled edges, yarn texture and physical shadows; its black flag and ivory mark remain attached.']
    if part['key']=='pump':part['detail']=['96齿旋盖、弧形按压头、开放接口与中空长吸管整体抬起。',
        'The 96-flute collar, arched actuator, open connector and long hollow dip tube lift as one complete pump.']
(HERE/'review-product.json').write_text(json.dumps(config,ensure_ascii=False,indent=2)+'\n')
# Retain the five existing assembly roots and synchronize saved review frames.
rest={name:o.location.copy() for name,o in roots.items()}
for frame,t in [(1,0),(31,.5),(61,1)]:
    for part in config['parts']:
        key=part['key'];o=roots[part['node']]
        x,y,z=config['review']['explosion']['offsets'][key]
        o.location=rest[o.name]+Vector((x,-z,y))*t
        s=1+(config['review']['explosion']['scales'].get(key,1)-1)*t
        o.scale=(s,s,s)
        o.keyframe_insert(data_path='location',frame=frame)
        o.keyframe_insert(data_path='scale',frame=frame)
scene.frame_set(1);bpy.context.view_layer.update()
bpy.ops.object.select_all(action='DESELECT')
for root in roots.values():
    root.select_set(True)
    for child in root.children_recursive:child.select_set(True)
bpy.ops.export_scene.gltf(filepath=str(GLB),export_format='GLB',use_selection=True,export_yup=True,
                          export_extras=True,export_animations=False)
bpy.ops.file.pack_all();bpy.ops.wm.save_as_mainfile(filepath=str(HERE/'poster-081-v2.blend'),compress=True)
report={'rootNames':list(roots),'meshObjects':sum(o.type=='MESH' for o in scene.objects),
        'preservedWorldVertexErrors':errors,'opaqueClothMaterialNames':['Warm ivory woven label','Black woven side flag'],
        'clothVolume':label_volume,'flagVolume':flag_volume,'clothInnerRadius':.785,'clothOuterRadius':.795,
        'nominalClothThickness':.010,'yarnPitch':math.tau*.795/240,'weaveTileSize':[512,512],
        'sideWordmarkAttachedToLabelRoot':True,'sideWordmarkShadow':False,'artwork':artwork,
        'wholePumpChildren':len(roots['Pump'].children),'containsFormula':False,'sourceFrames':[1,31,61],
        'glbBytes':GLB.stat().st_size,'glbSha256':hashlib.sha256(GLB.read_bytes()).hexdigest(),
        'configSha256':hashlib.sha256((HERE/'review-product.json').read_bytes()).hexdigest(),
        'productionRegistered':False,'visualReviewPending':True}
(HERE/'build-verification.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
print('HAND_GEL_081_V2_READY',json.dumps(report))
