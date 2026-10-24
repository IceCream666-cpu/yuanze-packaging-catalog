"""Single-product reconstruction from poster-039; dimensions are visual ratios only."""
import bpy, math, json
from pathlib import Path
from mathutils import Vector

BASE = Path(__file__).resolve().parent
CLIENT = BASE.parents[1]
OUT = BASE / 'poster-039'
bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete(use_global=False)
groups = {}

def material(name, color, roughness, metal=0, transmission=0):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    b = m.node_tree.nodes.get('Principled BSDF')
    rgb = [int(color[i:i+2], 16)/255 for i in (1,3,5)]
    b.inputs['Base Color'].default_value = (*[v/12.92 if v <= .04045 else ((v+.055)/1.055)**2.4 for v in rgb],1)
    b.inputs['Roughness'].default_value = roughness
    b.inputs['Metallic'].default_value = metal
    b.inputs['Transmission Weight'].default_value = transmission
    b.inputs['IOR'].default_value = 1.48
    return m

glass = material('PDRN neutral clear glass', '#ffffff', .028, transmission=1)
silver = material('PDRN polished silver', '#ededed', .075, metal=1)
insert = material('PDRN ivory polypropylene', '#f4f3ed', .30)

def mesh(name, verts, faces, mat, parent):
    data = bpy.data.meshes.new(name)
    data.from_pydata(verts, [], faces)
    data.update()
    o = bpy.data.objects.new(name, data)
    bpy.context.collection.objects.link(o)
    o.data.materials.append(mat)
    if parent not in groups:
        groups[parent] = bpy.data.objects.new(parent, None)
        bpy.context.collection.objects.link(groups[parent])
    o.parent = groups[parent]
    for f in data.polygons:
        f.use_smooth = abs(f.normal.z) < .999
    return o

def lathe(name, profile, mat, parent, segments=192):
    # Axis rings collapse to a single vertex, sealing the lid without a pinhole.
    verts, rings, faces = [], [], []
    for z,r in profile:
        if r == 0:
            rings.append([len(verts)])
            verts.append((0,0,z))
        else:
            rings.append(list(range(len(verts), len(verts)+segments)))
            verts += [(r*math.cos(i*2*math.pi/segments),r*math.sin(i*2*math.pi/segments),z) for i in range(segments)]
    for a,b in zip(rings,rings[1:]):
        if len(a)==len(b)==1: continue
        for i in range(segments):
            j=(i+1)%segments
            faces.append((a[0],b[j],b[i]) if len(a)==1 else (a[i],a[j],b[0]) if len(b)==1 else (a[i],a[j],b[j],b[i]))
    return mesh(name,verts,faces,mat,parent)

lathe('Clear thick-bottom jar',[
    (0,0),(0,.91),(.008,.95),(.025,.977),(.055,.993),(.09,1),
    (.16,1),(1.07,1),(1.10,.999),(1.125,.989),(1.145,.965),
    (1.18,.958),(1.27,.958),(1.29,.953),(1.295,.941),(1.29,.930),
    (1.27,.925),(.25,.925),(.215,.918),(.185,.898),(.17,.866),(.17,0)
],glass,'Body')
# The neck bead and two-turn thread are appearance details, not a tooling drawing.
lathe('Glass neck bead',[(1.14,.96),(1.146,.977),(1.158,.984),(1.17,.977),(1.176,.96)],glass,'Body')
def helix(name, radius, z, turns, pitch, thickness, mat, parent):
    verts, faces = [], []
    count = int(180*turns)
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
helix('Visible glass screw thread',.964,1.185,1.7,.043,.009,glass,'Body')

lathe('Polished silver lid shell',[
    (1.15,1.002),(1.156,1.013),(1.17,1.020),(1.19,1.022),
    (1.59,1.022),(1.61,1.018),(1.623,1.008),(1.630,.993),
    (1.632,.975),(1.632,0),(1.582,0),(1.582,.934),
    (1.574,.947),(1.56,.955),(1.17,.955),(1.15,.962),(1.15,1.002)
],silver,'Closure')
lathe('Lid inner polymer seating',[(1.175,.948),(1.55,.948),(1.563,.93),(1.563,.86),(1.54,.86),(1.54,.91),(1.175,.91),(1.175,.948)],insert,'Closure')
helix('Lid inner thread',.914,1.20,1.8,.043,.012,insert,'Closure')

lathe('Lift-out inner seal',[
    (1.27,0),(1.27,.881),(1.278,.923),(1.292,.942),(1.306,.946),
    (1.317,.937),(1.32,.913),(1.308,.884),(1.302,0)
],insert,'InnerLid')
# A shallow moulded lifting tab, kept below the closed lid's ceiling.
tab = lathe('Inner seal lifting tab',[(0,0),(0,.10),(.012,.12),(.025,.10),(.025,0)],insert,'InnerLid',64)
tab.location = (.59,-.10,1.31)
tab.scale = (1.40,.62,1)

for kind,parent in [('label','Body'),('print','LogoPrint')]:
    m = material('PDRN fixed serif copy' if kind=='label' else 'PDRN independent wordmark','#ffffff',.44)
    b=m.node_tree.nodes.get('Principled BSDF')
    tex=m.node_tree.nodes.new('ShaderNodeTexImage')
    tex.image=bpy.data.images.load(str(OUT/(kind+'.png')))
    tex.image.pack()
    m.node_tree.links.new(tex.outputs['Color'],b.inputs['Base Color'])
    m.node_tree.links.new(tex.outputs['Alpha'],b.inputs['Alpha'])
    m.surface_render_method='DITHERED'
    verts,faces=[],[]
    nx,ny=80,32
    for j in range(ny+1):
        for i in range(nx+1):
            x=(i/nx-.5)*1.42
            verts.append((x,-math.sqrt(1-x*x)-(.002 if kind=='label' else .003),.21+.88*j/ny))
    for j in range(ny):
        for i in range(nx):
            a=j*(nx+1)+i
            faces.append((a,a+1,a+nx+2,a+nx+1))
    o=mesh('Serif copy and underline' if kind=='label' else 'Liaose separate print',verts,faces,m,parent)
    uv=o.data.uv_layers.new()
    for f in o.data.polygons:
        for li in f.loop_indices:
            v=o.data.loops[li].vertex_index
            uv.data[li].uv=(v%(nx+1)/nx,v//(nx+1)/ny)

scale=2.9/1.632
for key,g in groups.items():
    pivot=Vector((0,0,1.39 if key=='Closure' else 1.30 if key=='InnerLid' else .65 if key=='LogoPrint' else 0))
    for child in g.children: child.location-=pivot
    g.location=pivot*scale
    g.scale=(scale,scale,scale)
assert abs((2*1.022*scale)/2.9 - 1.25245)<.001
bpy.ops.object.select_all(action='SELECT')
bpy.ops.export_scene.gltf(filepath=str(CLIENT/'packaging-assets/poster-039.glb'),export_format='GLB',use_selection=True,export_apply=True,export_yup=True,export_extras=True)
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'poster-039.blend'))
(OUT/'model-info.json').write_text(json.dumps({
    'id':'poster-039','components':list(groups),'height':2.9,'width':2.044*scale,
    'bodyHeightToDiameter':1.295/2.044,'closedHeightToDiameter':1.632/2.044,
    'capHeightToDiameter':.482/2.044,'illustrativeDimensions':True,'containsFormula':False,
    'reference':'featured-assets/poster-039.png','editableArtwork':['label.svg','print.svg'],
    'revision':'individual-reference-review-20261024','generator':'build_pdrn.py'
},indent=2)+'\n')
