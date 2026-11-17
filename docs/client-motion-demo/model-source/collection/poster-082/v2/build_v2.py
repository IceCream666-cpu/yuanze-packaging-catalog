"""082 v2: smooth thin-walled tube, integrated heat seal and complete blue pump.

This preserves the approved artwork and the measured silhouette of the v1 asset.
Scene units and hidden packaging details are illustrative, not manufacturing CAD.
"""
import bpy,bmesh,json,math,shutil,hashlib
from pathlib import Path
from mathutils import Vector

HERE=Path(__file__).resolve().parent;OLD=HERE.parent;CLIENT=HERE.parents[3]
GLB=CLIENT/'packaging-assets/poster-082-v2.glb'
bpy.ops.wm.open_mainfile(filepath=str(OLD/'poster-082-v1.blend'))
bpy.context.preferences.filepaths.save_version=0
scene=bpy.context.scene;scene.frame_set(1);bpy.context.view_layer.update()
ROOTS=['Body','Pump','TubeCap','Label','LogoInk','NameInk']
roots={name:bpy.data.objects[name] for name in ROOTS}
TX=-.83;BX=.75
def points(o):return [o.matrix_world@v.co for v in o.data.vertices]
preserved_names=['Empty ivory cylinder | low shoulder and hollow neck',
                 'Long clear hollow dip tube | near-bottom angled intake',
                 'Blue flip-top cap | lower hinged lid','Blue flip-top rear hinge']
preserved={name:points(bpy.data.objects[name]) for name in preserved_names}
for o in list(scene.objects):
    if o.type in {'LIGHT','CAMERA'} or (o.type=='MESH' and o.parent is None):
        bpy.data.objects.remove(o,do_unlink=True)

def fix(o):
    bm=bmesh.new();bm.from_mesh(o.data)
    bmesh.ops.remove_doubles(bm,verts=list(bm.verts),dist=1e-7)
    bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces))
    assert all(e.is_manifold for e in bm.edges),o.name
    volume=bm.calc_volume(signed=True);assert volume>0,(o.name,volume)
    bm.to_mesh(o.data);bm.free();o.data.update();return volume

def mesh(name,vs,fs,mat,root,smooth=True):
    data=bpy.data.meshes.new(name);data.from_pydata(vs,[],fs);data.update()
    ob=bpy.data.objects.new(name,data);scene.collection.objects.link(ob)
    ob.parent=roots[root];ob.location=-roots[root].location
    data.materials.append(mat)
    for f in data.polygons:f.use_smooth=smooth and abs(f.normal.z)<.999
    return ob

def monotone(values):
    # Fritsch-Carlson shape-preserving tangents avoid overshoot between references.
    x=[v[0] for v in values];y=[v[1] for v in values]
    d=[(b-a)/(xb-xa) for xa,xb,a,b in zip(x,x[1:],y,y[1:])]
    slopes=[d[0]]
    for i in range(1,len(x)-1):
        if d[i-1]*d[i]<=0:slopes.append(0)
        else:
            h0=x[i]-x[i-1];h1=x[i+1]-x[i]
            w1=2*h1+h0;w2=h1+2*h0
            slopes.append((w1+w2)/(w1/d[i-1]+w2/d[i]))
    slopes.append(d[-1])
    def evaluate(z):
        if z<=x[0]:return y[0]
        if z>=x[-1]:return y[-1]
        i=next(i for i in range(len(x)-1) if x[i]<=z<=x[i+1])
        h=x[i+1]-x[i];t=(z-x[i])/h
        return (2*t**3-3*t**2+1)*y[i]+(t**3-2*t*t+t)*h*slopes[i]+(-2*t**3+3*t*t)*y[i+1]+(t**3-t*t)*h*slopes[i+1]
    return evaluate

# Original dimensions retained, with a continuous molded shoulder rather than a
# same-height radius jump. The original 12 body sections become a smooth surface.
controls=[(.27,.124,.124),(.286,.128,.128),(.31,.128,.128),(.33,.143,.143),
          (.353,.143,.143),(.367,.128,.128),(.384,.181,.155),(.402,.285,.219),
          (.425,.373,.276),(.48,.405,.300),(.65,.421,.304),(1.,.451,.290),
          (1.4,.493,.252),(1.8,.541,.211),(2.2,.592,.159),(2.55,.639,.109),
          (2.82,.676,.062),(2.98,.696,.025),(3.015,.700,.021),
          (3.027,.700,.0215),(3.094,.700,.0215),(3.105,.697,.020)]
rx_at=monotone([(z,rx) for z,rx,ry in controls])
ry_at=monotone([(z,ry) for z,rx,ry in controls])
def smoothstep(t):t=max(0,min(1,t));return t*t*(3-2*t)
def power_at(z):return 2+4*smoothstep((z-2.92)/.095)
def center_y(z):
    t=max(0,min(1,(z-.425)/(2.98-.425)))
    return .0045*math.sin(math.pi*t)**2*math.sin(math.tau*t+.35)
def flex_amount(x,z):
    t=max(0,min(1,(z-.425)/(2.98-.425)))
    # Less than 0.004 total bow: restrained flexibility without a dented pack.
    return .0026*math.sin(math.pi*t)**2*math.sin(x*4.8+z*2.2)
def crimp_height(x,z):
    window=smoothstep((z-3.010)/.010)*(1-smoothstep((z-3.094)/.011))
    return .0008*window*(.5+.5*math.cos((x+.7)/1.4*math.tau*90))
def surface(x,z,front=True):
    rx=rx_at(z);ry=ry_at(z);p=power_at(z)
    t=max(0,1-abs(x/rx)**p)**(1/p)
    magnitude=ry*t+crimp_height(x,z)
    return center_y(z)+(-magnitude if front else magnitude)+flex_amount(x,z)

ivory=bpy.data.materials['Ivory opaque soft plastic']
soft=ivory.copy();soft.name='Ivory flexible laminated tube | subtle satin finish'
p=soft.node_tree.nodes['Principled BSDF'];p.inputs['Roughness'].default_value=.34
p.inputs['Coat Weight'].default_value=.10;p.inputs['Coat Roughness'].default_value=.28
blue=bpy.data.materials['Powder blue molded plastic'];p=blue.node_tree.nodes['Principled BSDF']
p.inputs['Roughness'].default_value=.235;p.inputs['Coat Weight'].default_value=.16;p.inputs['Coat Roughness'].default_value=.18
for name in ['Empty flexible tube | flat sealed tail and open nozzle','Flattened heat-seal tail | 90 fine crimp ridges']:
    bpy.data.objects.remove(bpy.data.objects[name],do_unlink=True)

def cross_section(z):
    p=power_at(z);result=[]
    for i in range(64):
        a=math.tau*i/64;signed=lambda q:math.copysign(abs(q)**(2/p),q)
        x=rx_at(z)*signed(math.cos(a));y=ry_at(z)*signed(math.sin(a))
        y+=center_y(z)+flex_amount(x,z)+math.copysign(crimp_height(x,z),y)
        result.append(Vector((x,y)))
    return result
zs=[];sampled_profile_error=0
def sample_interval(a,b,depth=0):
    global sampled_profile_error
    pa=cross_section(a);pb=cross_section(b);error=0
    for t in [.25,.5,.75]:
        error=max(error,max((r-(p*(1-t)+q*t)).length for p,q,r in zip(pa,pb,cross_section(a+(b-a)*t))))
    if error>.0002 and depth<12:
        m=(a+b)/2;sample_interval(a,m,depth+1);sample_interval(m,b,depth+1)
    else:zs.append(a);sampled_profile_error=max(sampled_profile_error,error)
anchors=sorted(set([r[0] for r in controls]+[2.92,3.010,3.020,3.10]))
for a,b in zip(anchors,anchors[1:]):sample_interval(a,b)
zs.append(anchors[-1])
# Each tuple is z, horizontal radius, depth radius, power, outer/inner identity.
rows=[(z,rx_at(z),ry_at(z),power_at(z),True) for z in zs]
rows.extend([(3.105,0,0,2,True),(2.994,0,0,2,False),(2.990,.680,.004,2.8,False)])
for z in reversed([z for z in zs if .425<=z<=2.98]):
    rows.append((z,rx_at(z)-.013,max(.005,ry_at(z)-.013),power_at(z),False))
rows.extend([(.410,.315,.224,2,False),(.390,.181,.144,2,False),
             (.367,.107,.107,2,False),(.270,.101,.101,2,False),rows[0]])
sections=128;vs=[];indices=[];fs=[]
for z,rx,ry,p,is_outer in rows:
    ids=[]
    for i in range(sections if rx else 1):
        a=math.tau*i/sections
        signed=lambda q:math.copysign(abs(q)**(2/p),q)
        x=rx*signed(math.cos(a));y=ry*signed(math.sin(a))
        if rx:
            y+=center_y(z)+flex_amount(x,z)
            if is_outer:y+=math.copysign(crimp_height(x,z),y-center_y(z))
        ids.append(len(vs));vs.append((TX+x,y,z))
    indices.append(ids)
for a,b in zip(indices,indices[1:]):
    if len(a)==len(b)==1:continue
    for i in range(sections):
        j=(i+1)%sections
        fs.append((a[0],b[j],b[i]) if len(a)==1 else (a[i],a[j],b[0]) if len(b)==1 else (a[i],a[j],b[j],b[i]))
tube=mesh('Flexible thin-wall tube | integrated embossed heat seal and open nozzle',vs,fs,soft,'Body')
tube_volume=fix(tube)
# Local heat-seal density resolves the fine ridge spacing without increasing
# the whole container's angular tessellation.
bm=bmesh.new();bm.from_mesh(tube.data)
edges=[e for e in bm.edges if all(v.co.z>=3.010 for v in e.verts)
       and abs(e.verts[0].co.z-e.verts[1].co.z)<1e-7
       and all(abs(v.co.x-TX)+abs(v.co.y)>.01 for v in e.verts)]
bmesh.ops.subdivide_edges(bm,edges=edges,cuts=3,use_grid_fill=True)
for v in bm.verts:
    if 3.010<=v.co.z<3.105 and abs(v.co.x-TX)+abs(v.co.y)>.01:
        v.co.y=surface(v.co.x-TX,v.co.z,front=v.co.y<center_y(v.co.z))
bm.to_mesh(tube.data);bm.free();tube_volume=fix(tube)
tube['nominalBodyWall']=.013;tube['heatSealIntegrated']=True;tube['containsFormula']=False

# Reproject the original UV artwork to the softer tube without changing its
# original X/Z coordinates, fonts, sizing or texture bytes.
artwork=[]
for name in ['logo','soap-clean-soap','spec-tube','spec-bottle']:
    for suffix in ['svg','png']:shutil.copy2(OLD/(name+'.'+suffix),HERE/(name+'.'+suffix))
    artwork.append({'name':name,'svgSha256':hashlib.sha256((HERE/(name+'.svg')).read_bytes()).hexdigest(),
                    'pngSha256':hashlib.sha256((HERE/(name+'.png')).read_bytes()).hexdigest()})
for name in ['carrier.png','stripe.png']:shutil.copy2(OLD/name,HERE/name)
for mat in bpy.data.materials:
    if not mat.use_nodes:continue
    for node in mat.node_tree.nodes:
        if node.type=='TEX_IMAGE' and node.image:
            filename=Path(node.image.filepath).name
            if (HERE/filename).exists():
                node.image=bpy.data.images.load(str(HERE/filename),check_existing=True);node.image.pack()
for root in ['Label','LogoInk','NameInk']:
    for ob in roots[root].children:
        if ob.type!='MESH':continue
        ob.visible_shadow=False
        ob['materialRole']='transparent print carrier, no rectangle shadow'
        if ob.name.startswith('Tube '):
            inv=ob.matrix_world.inverted()
            for vert in ob.data.vertices:
                q=ob.matrix_world@vert.co
                q.y=surface(q.x-TX,q.z)-(.001 if root=='Label' else .0036)
                vert.co=inv@q
            ob.data.update()

# The two almost-clear conceptual surfaces carry no artwork. Sample their
# continuous surface directly instead of keeping redundant original subdivisions.
for name,cx,width,height,z0,nx,ny in [
        ('Tube transparent print carrier',TX,.77,2.43,.46,32,48),
        ('Bottle transparent print carrier',BX,.80,1.60,.22,32,16)]:
    old=bpy.data.objects[name];mat=old.data.materials[0]
    bpy.data.objects.remove(old,do_unlink=True);cv=[];cf=[]
    for j in range(ny+1):
        z=z0+height*j/ny
        for i in range(nx+1):
            x=(i/nx-.5)*width
            y=surface(x,z) if cx==TX else -math.sqrt(.575**2-x*x)
            cv.append((cx+x,y-.001,z))
    for j in range(ny):
        for i in range(nx):a=j*(nx+1)+i;cf.append((a,a+1,a+nx+2,a+nx+1))
    ob=mesh(name,cv,cf,mat,'Label');ob.visible_shadow=False
    ob['materialRole']='transparent conceptual print carrier, no rectangle shadow'
    uv=ob.data.uv_layers.new(name='Carrier UV')
    for f in ob.data.polygons:
        for li in f.loop_indices:
            v=ob.data.loops[li].vertex_index;uv.data[li].uv=(v%(nx+1)/nx,v//(nx+1)/ny)

# The original stripe gaps remain exact. Only the visible ink gets a thin solid
# shell; the two conceptual transparent carrier sheets never become paper.
old=bpy.data.objects['Pale blue pinstripes | direct printing, no paper'];bpy.data.objects.remove(old,do_unlink=True)
stripe=bpy.data.materials['Powder blue pinstripe ink'];p=stripe.node_tree.nodes['Principled BSDF']
for link in list(p.inputs['Alpha'].links):stripe.node_tree.links.remove(link)
p.inputs['Alpha'].default_value=1;p.inputs['Roughness'].default_value=.43
zones=[(2.61,2.80,.285),(1.43,1.97,.365),(.545,.815,.35)]
sv=[];sf=[];n=240;ribbon_count=0
old_radius=[(.39,.370),(.42,.390),(.48,.405),(.65,.421),(1.,.451),(1.4,.493),(1.8,.541),(2.2,.592),(2.55,.639),(2.82,.676),(2.98,.696),(3.015,.700)]
def original_rx(z):
    for (za,ra),(zb,rb) in zip(old_radius,old_radius[1:]):
        if za<=z<=zb:return ra+(rb-ra)*(z-za)/(zb-za)
    return old_radius[-1][1] if z>old_radius[-1][0] else old_radius[0][1]
def ribbon(side,fraction,start,end):
    global ribbon_count
    ribbon_count+=1;front=[];back=[]
    for j in range(start,end+1):
        z=.465+(2.98-.465)*j/n
        for offset,rows in [(.0008,front),(.0002,back)]:
            row=[]
            for sgn in [-1,1]:
                x=side*fraction*rx_at(z)+sgn*.0048
                row.append(len(sv));sv.append((TX+x,surface(x,z)-offset,z))
            rows.append(row)
    for j in range(len(front)-1):
        a,b=front[j],front[j+1];c,d=back[j],back[j+1]
        sf.extend([(a[0],a[1],b[1],b[0]),(c[1],c[0],d[0],d[1]),
                   (a[0],b[0],d[0],c[0]),(a[1],c[1],d[1],b[1])])
    a,c=front[0],back[0];b,d=front[-1],back[-1]
    sf.extend([(a[0],c[0],c[1],a[1]),(b[0],b[1],d[1],d[0])])
for side in [-1,1]:
    for fraction in [.105,.315,.525,.735,.915]:
        start=None
        for j in range(n+1):
            z=.465+(2.98-.465)*(j+.5)/n
            x=side*fraction*original_rx(z)
            keep=j<n and not any(lo<z<hi and abs(x)<half for lo,hi,half in zones)
            if keep and start is None:start=j
            if not keep and start is not None:ribbon(side,fraction,start,j);start=None
stripes=mesh('Pale blue pinstripes | thin solid direct-print decoration',sv,sf,stripe,'Label')
stripe_volume=fix(stripes);stripes.visible_shadow=True
stripes['materialRole']='opaque physical pinstripe ink, no paper label'
stripes['nominalThickness']=.0006;stripes['originalLetteringGapsPreserved']=True
uv=stripes.data.uv_layers.new(name='Constant ink swatch')
for p in stripes.data.polygons:
    for li in p.loop_indices:uv.data[li].uv=(.5,.5)

def boolean_cut(ob,cutter,label):
    bpy.ops.object.select_all(action='DESELECT');ob.select_set(True);bpy.context.view_layer.objects.active=ob
    mod=ob.modifiers.new(label,'BOOLEAN');mod.operation='DIFFERENCE';mod.solver='EXACT';mod.object=cutter
    bpy.ops.object.modifier_apply(modifier=mod.name);bpy.data.objects.remove(cutter,do_unlink=True)
    # The original thumb recess had an unused/undefined material slot.
    good=next(m for m in ob.data.materials if m)
    ob.data.materials.clear();ob.data.materials.append(good)
    for f in ob.data.polygons:f.material_index=0
    return fix(ob)
def bore(ob,r,z0,z1,name,cx=BX):
    bpy.ops.mesh.primitive_cylinder_add(vertices=96,radius=r,depth=z1-z0,location=(cx,0,(z0+z1)/2))
    return boolean_cut(ob,bpy.context.object,name)
barrel=bpy.data.objects['Disc pump | rounded closure barrel']
socket=bpy.data.objects['Disc pump | internal socket, stays with head']
neck=bpy.data.objects['Disc pump | assembled actuator neck']
bore(barrel,.181,1.980,2.178,'Open collar neck socket')
bore(barrel,.031,1.98,2.36,'Central pump passage')
bore(socket,.030,1.84,2.06,'Open connector bore')
bore(socket,.0425,1.84,1.998,'Dip tube insertion socket')
bore(neck,.031,2.30,2.55,'Actuator lower passage')
# A true recessed outlet in the existing low rear-edge lip, no invented tall peg.
lip=bpy.data.objects['Disc pump | low rear-edge dispensing lip']
bpy.ops.mesh.primitive_cube_add(size=1,location=(BX,.312,2.639))
cutter=bpy.context.object;cutter.scale=(.064,.075,.012)
bpy.ops.object.transform_apply(location=False,rotation=False,scale=True)
bev=cutter.modifiers.new('Rounded outlet slot','BEVEL');bev.width=.004;bev.segments=4
bpy.ops.object.modifier_apply(modifier=bev.name)
boolean_cut(lip,cutter,'Open rear lip outlet recess')
lip['outletRecessDepth']=.0375
# Open the flip-cap upper passage to the dispensing aperture above its closed lid.
upper=bpy.data.objects['Blue flip-top cap | complete closure sleeve']
bore(upper,.070,.145,.430,'Flip closure dispensing bore',TX)

bpy.context.view_layer.update();errors={}
for name,old_points in preserved.items():
    current=points(bpy.data.objects[name]);assert len(current)==len(old_points)
    error=max((p-q).length for p,q in zip(current,old_points));assert error==0,(name,error);errors[name]=error
config=json.loads((OLD/'review-product.json').read_text());config['file']='poster-082-v2.glb'
config['review']['appearance'].update(labelShadows=True,studio={'background':'#cbd4d6','ink':'#263b3a'})
for part in config['parts']:
    if part['key']=='body':part['detail']=['连续薄壁软管、细压纹封尾与乳白圆柱泵瓶，两件空包材。','An empty thin-wall tube with integrated fine heat sealing beside an ivory cylindrical bottle.']
    if part['key']=='label':part['detail']=['浅蓝直印条纹为薄实体装饰层，独立展开并投影；透明印刷载体不投整片阴影，无纸标。','Thin blue direct-print stripes separate and cast their own shadows; clear print carriers cast no rectangular shadows. No paper label.']
(HERE/'review-product.json').write_text(json.dumps(config,ensure_ascii=False,indent=2)+'\n')
rest={name:o.location.copy() for name,o in roots.items()}
for frame,t in [(1,0),(31,.5),(61,1)]:
    for part in config['parts']:
        key=part['key'];o=roots[part['node']];x,y,z=config['review']['explosion']['offsets'][key]
        o.location=rest[o.name]+Vector((x,-z,y))*t
        s=1+(config['review']['explosion']['scales'].get(key,1)-1)*t;o.scale=(s,s,s)
        o.keyframe_insert(data_path='location',frame=frame);o.keyframe_insert(data_path='scale',frame=frame)
scene.frame_set(1);bpy.context.view_layer.update()
bpy.ops.object.select_all(action='DESELECT')
for root in roots.values():
    root.select_set(True)
    for child in root.children_recursive:child.select_set(True)
bpy.ops.export_scene.gltf(filepath=str(GLB),export_format='GLB',use_selection=True,
                          export_yup=True,export_extras=True,export_animations=False)
bpy.ops.file.pack_all();bpy.ops.wm.save_as_mainfile(filepath=str(HERE/'poster-082-v2.blend'),compress=True)
report={'roots':ROOTS,'meshObjects':sum(o.type=='MESH' for root in roots.values() for o in root.children_recursive),
        'preservedWorldVertexErrors':errors,'softTubeVolume':tube_volume,'stripeVolume':stripe_volume,
        'stripeRibbons':ribbon_count,'stripeThickness':.0006,'tubeWallNominal':.013,
        'adaptiveTubeRows':len(zs),'sampledLongitudinalChordError':sampled_profile_error,
        'continuousHeatSeal':True,'paperLabel':False,'containsFormula':False,'artwork':artwork,
        'sourceFrames':[1,31,61],'glbBytes':GLB.stat().st_size,
        'glbSha256':hashlib.sha256(GLB.read_bytes()).hexdigest(),
        'configSha256':hashlib.sha256((HERE/'review-product.json').read_bytes()).hexdigest(),
        'visualReviewPending':True,'productionRegistered':False}
(HERE/'build-verification.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
print('SOAP_DUO_082_V2_READY',json.dumps(report))
