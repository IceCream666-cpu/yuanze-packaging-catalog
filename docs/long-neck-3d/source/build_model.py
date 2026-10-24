"""Rebuild the poster-derived display model with Blender 4.5; dimensions are illustrative."""
import bpy, math, json
from pathlib import Path
from mathutils import Vector

BASE = Path(__file__).resolve().parents[1]
bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete(use_global=False)

def material(name, color, roughness):
    m = bpy.data.materials.new(name); m.diffuse_color = (*color, 1); m.use_nodes = True
    p = m.node_tree.nodes.get('Principled BSDF')
    p.inputs['Base Color'].default_value = (*color, 1)
    p.inputs['Roughness'].default_value = roughness
    return m

body_mat = material('Ivory satin frosted finish', (.87, .855, .81), .4)
pump_mat = material('Warm ivory pump', (.82, .795, .72), .31)
dark_mat = material('Nozzle recess', (.14, .13, .105), .55)
parts = []

def mesh(name, vertices, faces, mat):
    data = bpy.data.meshes.new(name); data.from_pydata(vertices, [], faces); data.update()
    obj = bpy.data.objects.new(name, data); bpy.context.collection.objects.link(obj)
    obj.data.materials.append(mat)
    for polygon in data.polygons: polygon.use_smooth = True
    parts.append(obj)
    return obj

def revolve(name, profile, mat, sides=96, depth=1, exponent=2):
    vertices=[]; faces=[]
    for z,r in profile:
        for i in range(sides):
            t=2*math.pi*i/sides; c,s=math.cos(t),math.sin(t)
            vertices.append((r*math.copysign(abs(c)**(2/exponent),c), r*depth*math.copysign(abs(s)**(2/exponent),s), z))
    for j in range(len(profile)-1):
        for i in range(sides):
            a=j*sides+i; b=j*sides+(i+1)%sides
            faces.append((a,b,b+sides,a+sides))
    faces += [tuple(reversed(range(sides))), tuple((len(profile)-1)*sides+i for i in range(sides))]
    return mesh(name,vertices,faces,mat)

outline=[(.0,.57),(.016,.65),(.045,.70),(.09,.725),(.19,.735),(.40,.735),(.57,.72),(.73,.665),(.91,.53),(1.09,.385),(1.29,.275),(1.49,.223),(1.7,.21),(1.9,.21)]
def radius(z):
    for i in range(len(outline)-1):
        if z<=outline[i+1][0]:
            a,b=outline[i:i+2]; t=(z-a[0])/(b[0]-a[0]); prev=outline[max(0,i-1)]; nxt=outline[min(len(outline)-1,i+2)]
            m0=(b[1]-prev[1])/(b[0]-prev[0]); m1=(nxt[1]-a[1])/(nxt[0]-a[0]); dz=b[0]-a[0]
            return (2*t**3-3*t*t+1)*a[1]+(t**3-2*t*t+t)*dz*m0+(-2*t**3+3*t*t)*b[1]+(t**3-t*t)*dz*m1
    return outline[-1][1]
profile=[(a[0]+(b[0]-a[0])*j/8,radius(a[0]+(b[0]-a[0])*j/8)) for a,b in zip(outline,outline[1:]) for j in range(8)]+[outline[-1]]
bottle=revolve('Bottle',profile,body_mat,128,.72,2.65)
revolve('Neck collar',[(1.87,.21),(1.88,.243),(1.90,.259),(1.93,.266),(2.015,.266),(2.045,.25),(2.055,.235)],pump_mat)
revolve('Ribbed closure',[(2.045,.226),(2.06,.235),(2.32,.235),(2.35,.224),(2.36,.215)],pump_mat)
for i in range(64):
    a=2*math.pi*i/64
    bpy.ops.mesh.primitive_uv_sphere_add(segments=8, ring_count=6, location=(.235*math.cos(a),.235*math.sin(a),2.203))
    o=bpy.context.object;o.name=f'Closure rib {i+1:02}';o.scale=(.008,.008,.143)
    bpy.ops.object.transform_apply(location=False,rotation=False,scale=True)
    o.data.materials.append(pump_mat)
    for f in o.data.polygons:f.use_smooth=True
    parts.append(o)
revolve('Stem seat',[(2.355,.165),(2.36,.171),(2.415,.171),(2.43,.16)],pump_mat)
revolve('Pump stem',[(2.42,.079),(2.69,.079),(2.7,.09)],pump_mat)
revolve('Actuator neck',[(2.66,.088),(2.72,.093),(2.75,.082),(2.84,.071),(2.89,.073),(2.91,.103)],pump_mat)
for z in (2.7,2.735,2.77):
    bpy.ops.mesh.primitive_torus_add(major_radius=.09,minor_radius=.012,major_segments=64,minor_segments=12,location=(0,0,z))
    o=bpy.context.object;o.name='Actuator ring';o.data.materials.append(pump_mat);parts.append(o)
    for f in o.data.polygons:f.use_smooth=True
revolve('Press pad',[(2.89,.08),(2.91,.122),(2.93,.134),(2.955,.132),(2.969,.115),(2.974,.015)],pump_mat,96,1.12)

# A swept hollow nozzle keeps its curved silhouette and opening from all viewing angles.
path=[(0,2.865),(-.12,2.87),(-.26,2.892),(-.40,2.907),(-.49,2.892),(-.57,2.855),(-.615,2.821)]
curve=[]
for i in range(len(path)-1):
    p0=Vector(path[max(0,i-1)]);p1=Vector(path[i]);p2=Vector(path[i+1]);p3=Vector(path[min(len(path)-1,i+2)])
    for j in range(8):
        t=j/8;curve.append(.5*((2*p1)+(-p0+p2)*t+(2*p0-5*p1+4*p2-p3)*t*t+(-p0+3*p1-3*p2+p3)*t*t*t))
curve.append(Vector(path[-1]));verts=[];faces=[];N=24
for ring,p in enumerate(curve):
    tangent=(curve[min(ring+1,len(curve)-1)]-curve[max(0,ring-1)]).normalized(); normal=Vector((-tangent.y,tangent.x))
    for i in range(N):
        t=2*math.pi*i/N;v=p+normal*(math.cos(t)*.034)
        verts.append((v.x,math.sin(t)*.045,v.y))
for j in range(len(curve)-1):
    for i in range(N):
        a=j*N+i;b=j*N+(i+1)%N;faces.append((a,a+N,b+N,b))
mesh('Curved dispensing spout',verts,faces,pump_mat)
end=curve[-1];tangent=(curve[-1]-curve[-2]).normalized();normal=Vector((-tangent.y,tangent.x));v=[]
for r in (1,.65):
    for i in range(N):
        a=2*math.pi*i/N;p=end+normal*(math.cos(a)*.034*r)
        v.append((p.x,math.sin(a)*.045*r,p.y))
mesh('Nozzle lip',v,[(i,(i+1)%N,(i+1)%N+N,i+N) for i in range(N)],pump_mat)
mesh('Nozzle interior',[(x-tangent.x*.012,y,z-tangent.y*.012) for x,y,z in v[N:]],[tuple(range(N))],dark_mat)

logo=material('liaose printed wordmark',(.015,.03,.02),.5)
tree=logo.node_tree;shader=tree.nodes.get('Principled BSDF');tex=tree.nodes.new('ShaderNodeTexImage');tex.image=bpy.data.images.load(str(BASE/'assets/liaose.png'));tex.image.pack()
tree.links.new(tex.outputs['Color'],shader.inputs['Base Color']);tree.links.new(tex.outputs['Alpha'],shader.inputs['Alpha']);logo.surface_render_method='DITHERED'
vertices=[];faces=[];nx,ny=48,8
for j in range(ny+1):
    z=.20+j/ny*.225;r=radius(z)
    for i in range(nx+1):
        x=-.305+i/nx*.61;y=-.72*r*(1-(abs(x)/r)**2.65)**(1/2.65)-.0015
        vertices.append((x,y,z))
for j in range(ny):
    for i in range(nx):
        a=j*(nx+1)+i;faces.append((a,a+1,a+nx+2,a+nx+1))
decal=mesh('Front liaose print',vertices,faces,logo);uv=decal.data.uv_layers.new()
for f in decal.data.polygons:
    for li in f.loop_indices:
        vi=decal.data.loops[li].vertex_index;uv.data[li].uv=(vi%(nx+1)/nx,vi//(nx+1)/ny)

bpy.ops.object.select_all(action='DESELECT')
for o in parts:o.select_set(True)
bpy.context.view_layer.objects.active=bottle
bpy.ops.export_scene.gltf(filepath=str(BASE/'assets/liaose-pump.glb'),export_format='GLB',use_selection=True,export_apply=True,export_yup=True)

floor_mat=material('Sage studio floor',(.69,.72,.62),.82)
bpy.ops.mesh.primitive_plane_add(size=200,location=(0,0,-.008));bpy.context.object.data.materials.append(floor_mat)
def area(name,loc,power,size,color):
    data=bpy.data.lights.new(name,'AREA');data.energy=power;data.shape='DISK';data.size=size;data.color=color
    o=bpy.data.objects.new(name,data);bpy.context.collection.objects.link(o);o.location=loc;o.rotation_euler=(Vector((0,0,1.3))-o.location).to_track_quat('-Z','Y').to_euler()
area('Large softbox',(-3,-4,6),450,4,(1,.95,.85));area('Fill',(4,-1,3),180,3,(.87,.93,1));area('Rim',(1,3,5),360,3,(1,1,1))
bpy.ops.object.camera_add(location=(.55,-7,3.05));camera=bpy.context.object;camera.rotation_euler=(Vector((-.08,0,1.46))-camera.location).to_track_quat('-Z','Y').to_euler();camera.data.type='ORTHO';camera.data.ortho_scale=3.7
scene=bpy.context.scene;scene.camera=camera;scene.render.engine='CYCLES';scene.cycles.samples=48;scene.cycles.use_denoising=True;scene.world.color=(.25,.25,.25)
scene.render.resolution_x=1400;scene.render.resolution_y=1400;scene.render.resolution_percentage=100;scene.render.image_settings.file_format='PNG';scene.view_settings.view_transform='AgX';scene.render.filepath=str(BASE/'assets/studio.png')
bpy.ops.wm.save_as_mainfile(filepath=str(BASE/'liaose-pump.blend'))
assert len(parts)>70 and all(len(o.data.polygons)>0 for o in parts)
(BASE/'assets/model-info.json').write_text(json.dumps({'source':'poster-071','units':'illustrative proportions, not manufacturing dimensions','objects':len(parts),'vertices':sum(len(o.data.vertices) for o in parts),'height':2.974,'width':1.47,'parts':['Bottle','Neck collar','Ribbed closure','Pump stem','Press pad','Curved dispensing spout','Front liaose print']},indent=2)+'\n')
bpy.ops.render.render(write_still=True)
