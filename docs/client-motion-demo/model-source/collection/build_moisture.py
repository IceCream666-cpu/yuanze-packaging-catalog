"""Poster-049 empty packaging reconstruction; visual ratios, not tooling dimensions."""
import bpy, math, json
from pathlib import Path
from mathutils import Vector

BASE = Path(__file__).resolve().parent
CLIENT = BASE.parents[1]
OUT = BASE / 'poster-049'
OUT.mkdir(exist_ok=True)
bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete(use_global=False)
groups = {}

def material(name, color, roughness, metal=0, transmission=0):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    b = m.node_tree.nodes.get('Principled BSDF')
    rgb = [int(color[i:i+2],16)/255 for i in (1,3,5)]
    b.inputs['Base Color'].default_value = (*[v/12.92 if v <= .04045 else ((v+.055)/1.055)**2.4 for v in rgb],1)
    b.inputs['Roughness'].default_value = roughness
    b.inputs['Metallic'].default_value = metal
    b.inputs['Transmission Weight'].default_value = transmission
    b.inputs['IOR'].default_value = 1.48
    return m

glass = material('Moisture neutral clear glass','#ffffff',.025,transmission=1)
silver = material('Moisture satin silver','#ededed',.16,metal=1)
insert = material('Moisture hidden ivory insert','#efeee8',.38)
outlet = material('Moisture recessed nozzle interior','#232522',.38)

def mesh(name, verts, faces, mat, parent):
    data = bpy.data.meshes.new(name)
    data.from_pydata(verts,[],faces)
    data.update()
    ob = bpy.data.objects.new(name,data)
    bpy.context.collection.objects.link(ob)
    ob.data.materials.append(mat)
    if parent not in groups:
        groups[parent] = bpy.data.objects.new(parent,None)
        bpy.context.collection.objects.link(groups[parent])
    ob.parent = groups[parent]
    for face in data.polygons:
        face.use_smooth = abs(face.normal.z)<.999
    return ob

def lathe(name, profile, mat, parent, segments=192):
    verts, rings, faces = [],[],[]
    for z,r in profile:
        if r == 0:
            rings.append([len(verts)])
            verts.append((0,0,z))
        else:
            rings.append(list(range(len(verts),len(verts)+segments)))
            verts.extend((r*math.cos(i*math.tau/segments),r*math.sin(i*math.tau/segments),z) for i in range(segments))
    for a,b in zip(rings,rings[1:]):
        if len(a)==len(b)==1: continue
        for i in range(segments):
            j=(i+1)%segments
            faces.append((a[0],b[j],b[i]) if len(a)==1 else (a[i],a[j],b[0]) if len(b)==1 else (a[i],a[j],b[j],b[i]))
    return mesh(name,verts,faces,mat,parent)

def helix(name, radius, z, turns, pitch, thickness, mat, parent):
    verts,faces=[],[]
    count=int(180*turns)
    for i in range(count+1):
        a=i/count*math.tau*turns
        for j in range(8):
            q=j/8*math.tau
            r=radius+thickness*math.cos(q)
            verts.append((r*math.cos(a),r*math.sin(a),z+pitch*a/math.tau+thickness*math.sin(q)))
    for i in range(count):
        for j in range(8):
            k=i*8+j; nxt=i*8+(j+1)%8
            faces.append((k,nxt,nxt+8,k+8))
    return mesh(name,verts,faces,mat,parent)

lathe('Clear wide-mouth bottle',[
    (0,0),(0,.345),(.008,.365),(.025,.385),(.055,.411),(.09,.435),
    (.14,.462),(.20,.486),(.26,.497),(.31,.500),(1.34,.500),
    (1.38,.497),(1.42,.489),(1.46,.476),(1.50,.458),(1.54,.440),
    (1.58,.428),(1.61,.425),(1.66,.425),(1.67,.421),(1.673,.412),
    (1.668,.402),(1.65,.400),(1.59,.400),(1.55,.414),(1.51,.433),
    (1.46,.454),(1.41,.468),(1.36,.475),(.29,.475),(.24,.470),
    (.19,.455),(.145,.425),(.115,.387),(.105,.350),(.105,0)
],glass,'Body')
lathe('Glass neck bead',[(1.574,.425),(1.580,.432),(1.591,.434),(1.60,.427)],glass,'Body')
# The visible screw detail remains illustrative until a real neck finish is supplied.
helix('Visible bottle thread',.426,1.61,1.7,.025,.005,glass,'Body')

lathe('Silver wide screw collar',[
    (1.602,.422),(1.608,.439),(1.617,.445),(1.625,.445),(1.634,.435),
    (1.646,.432),(1.655,.442),(1.669,.444),(1.679,.436),
    (1.700,.434),(1.710,.443),(1.725,.444),(1.736,.435),
    (1.758,.435),(1.769,.439),(1.870,.439),(1.880,.432),
    (1.883,.414),(1.883,.116),(1.861,.116),(1.861,.405),
    (1.835,.410),(1.616,.410),(1.602,.422)
],silver,'Closure')
flute_count=88; n=flute_count*8; verts=[];faces=[]
for z,amount in [(1.770,0),(1.777,.65),(1.785,1),(1.865,1),(1.875,.6),(1.880,0)]:
    for i in range(n):
        a=i*math.tau/n
        ridge=(.5+.5*math.cos(a*flute_count))**.65
        r=.439+.006*amount*ridge
        verts.append((r*math.cos(a),r*math.sin(a),z))
for ring in range(5):
    for i in range(n):
        j=(i+1)%n;a=ring*n+i;b=ring*n+j
        faces.append((a,b,b+n,a+n))
mesh('Fine vertical collar flutes',verts,faces,silver,'Closure')
lathe('Inner closure polymer seat',[(1.615,.408),(1.851,.408),(1.851,.116),(1.838,.116),(1.838,.395),(1.615,.395),(1.615,.408)],insert,'Closure')

lathe('Silver stepped pump housing',[
    (1.875,.109),(1.875,.206),(1.884,.221),(1.899,.225),
    (2.105,.225),(2.120,.219),(2.129,.202),(2.132,.175),
    (2.145,.175),(2.151,.181),(2.160,.183),(2.205,.183),
    (2.218,.174),(2.222,.151),(2.222,.111),(1.875,.111),(1.875,.109)
],silver,'PumpStem')
lathe('Silver actuator shaft',[
    (2.190,0),(2.190,.146),(2.202,.158),(2.370,.158),
    (2.382,.153),(2.389,.142),(2.389,0)
],silver,'Actuator')

# A broad flattened hollow lever, with a downturned rectangular mouth instead of a round tube.
sections=[(-.515,2.320,.080,.027),(-.491,2.345,.084,.028),
          (-.40,2.373,.099,.030),(-.22,2.404,.122,.031),
          (0,2.418,.160,.032),(.120,2.418,.160,.032),
          (.175,2.413,.125,.029),(.197,2.408,.060,.020)]
verts=[];faces=[];n=40
def section(x,z,half_width,half_height):
    return [(x,half_width*math.copysign(abs(math.cos(i*math.tau/n))**.5,math.cos(i*math.tau/n)),
             z+half_height*math.copysign(abs(math.sin(i*math.tau/n))**.5,math.sin(i*math.tau/n))) for i in range(n)]
for args in sections: verts.extend(section(*args))
for ring in range(len(sections)-1):
    for i in range(n):
        a=ring*n+i;b=ring*n+(i+1)%n
        faces.append((a,b,b+n,a+n))
back=len(verts);verts.append((.203,0,2.408))
for i in range(n):faces.append(((len(sections)-1)*n+i,(len(sections)-1)*n+(i+1)%n,back))
inner=len(verts);verts.extend(section(-.515,2.320,.052,.012))
inner_end=len(verts);verts.extend(section(-.468,2.342,.052,.012))
for i in range(n):
    j=(i+1)%n
    faces.append((i,inner+i,inner+j,j))
    faces.append((inner+i,inner_end+i,inner_end+j,inner+j))
mesh('Flattened dispensing lever',verts,faces,silver,'Actuator')
mesh('Recessed dispensing outlet',section(-.467,2.342,.052,.012),[tuple(reversed(range(n)))],outlet,'Actuator')

for kind,parent in [('label','Body'),('print','LogoPrint')]:
    m=material('Moisture ivory paper stock' if kind=='label' else 'Moisture complete black print','#ffffff',.72 if kind=='label' else .66)
    b=m.node_tree.nodes.get('Principled BSDF')
    b.inputs['Specular IOR Level'].default_value=.12 if kind=='label' else .025
    tex=m.node_tree.nodes.new('ShaderNodeTexImage')
    tex.image=bpy.data.images.load(str(OUT/(kind+'.png')))
    tex.image.pack()
    m.node_tree.links.new(tex.outputs['Color'],b.inputs['Base Color'])
    m.node_tree.links.new(tex.outputs['Alpha'],b.inputs['Alpha'])
    m.surface_render_method='DITHERED'
    verts=[];faces=[];nx,ny=96,64
    for j in range(ny+1):
        for i in range(nx+1):
            x=(i/nx-.5)*.810
            verts.append((x,-math.sqrt(.5*.5-x*x)-(.0015 if kind=='label' else .0022),.370+.940*j/ny))
    for j in range(ny):
        for i in range(nx):
            a=j*(nx+1)+i;faces.append((a,a+1,a+nx+2,a+nx+1))
    ob=mesh('Ivory paper label' if kind=='label' else 'Complete shampoo print',verts,faces,m,parent)
    uv=ob.data.uv_layers.new()
    for face in ob.data.polygons:
        for li in face.loop_indices:
            v=ob.data.loops[li].vertex_index
            uv.data[li].uv=(v%(nx+1)/nx,v//(nx+1)/ny)

scale=2.9/2.45
pivots={'Body':0,'Closure':1.74,'PumpStem':2.05,'Actuator':2.35,'LogoPrint':.84}
for key,group in groups.items():
    pivot=Vector((0,0,pivots[key]))
    for child in group.children:child.location-=pivot
    group.location=pivot*scale
    group.scale=(scale,scale,scale)
assert set(groups)==set(pivots)
assert abs(2.45*scale-2.9)<1e-9
bpy.ops.object.select_all(action='SELECT')
bpy.ops.export_scene.gltf(filepath=str(CLIENT/'packaging-assets/poster-049.glb'),export_format='GLB',use_selection=True,export_apply=True,export_yup=True,export_extras=True)
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'poster-049.blend'))
(OUT/'model-info.json').write_text(json.dumps({
    'id':'poster-049','components':list(groups),'height':2.9,'width':scale,
    'closedHeightToDiameter':2.45,'bodyHeightToDiameter':1.673,'closureDiameterToBody':.89,
    'illustrativeDimensions':True,'containsFormula':False,
    'reference':'featured-assets/poster-049.png','editableArtwork':['label.svg','print.svg'],
    'printIncludes':['liaose','WHIPPED MOISTURE','SHAMPOO','two separator rules'],
    'revision':'individual-reference-review-20261024','generator':'build_moisture.py'
},indent=2)+'\n')
