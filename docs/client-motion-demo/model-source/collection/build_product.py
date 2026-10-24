"""Poster-derived appearance models. No measured dimensions or concealed pump mechanics.
Blender --background --python build_product.py -- poster-013
"""
import bpy,math,json,sys
from pathlib import Path
from mathutils import Vector
BASE=Path(__file__).resolve().parent;CLIENT=BASE.parents[1]
if sys.argv[-1]=='poster-039':
 import runpy
 runpy.run_path(str(BASE/'build_pdrn.py'));sys.exit(0)
if sys.argv[-1]=='poster-056':
 import runpy
 runpy.run_path(str(BASE/'build_golden_face_oil.py'));sys.exit(0)
if sys.argv[-1]=='poster-047':
 import runpy
 runpy.run_path(str(BASE/'build_coastal.py'));sys.exit(0)
if sys.argv[-1]=='poster-044':
 import runpy
 runpy.run_path(str(BASE/'build_gentle_cleansing.py'));sys.exit(0)
if sys.argv[-1]=='poster-051':
 import runpy
 runpy.run_path(str(BASE/'build_pure_volume.py'));sys.exit(0)
if sys.argv[-1]=='poster-042':
 import runpy
 runpy.run_path(str(BASE/'build_woodland.py'));sys.exit(0)
if sys.argv[-1]=='poster-049':
 import runpy
 runpy.run_path(str(BASE/'build_moisture.py'));sys.exit(0)
p=next(x for x in json.loads((BASE/'products.json').read_text()) if x['id']==sys.argv[-1]);out=BASE/p['id']
bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)
for data in list(bpy.data.materials):bpy.data.materials.remove(data)
groups={};objects=[]
def group(key):
 if key not in groups:
  o=bpy.data.objects.new(key,None);bpy.context.collection.objects.link(o);groups[key]=o
 return groups[key]
def linear(hex):
 c=[int(hex[i:i+2],16)/255 for i in (1,3,5)];return tuple(v/12.92 if v<=.04045 else ((v+.055)/1.055)**2.4 for v in c)
def mat(name,color,rough=.28,metal=0,glass=False):
 m=bpy.data.materials.new(name);m.use_nodes=True;b=m.node_tree.nodes.get('Principled BSDF');b.inputs['Base Color'].default_value=(*linear(color),1);b.inputs['Roughness'].default_value=rough;b.inputs['Metallic'].default_value=metal
 if glass:b.inputs['Transmission Weight'].default_value=.92;b.inputs['IOR'].default_value=1.46
 return m
body=mat('Frosted glass' if p.get('frosted') else 'Packaging body',p.get('body',p.get('glass')),.27 if p.get('frosted') else .075 if p.get('glass') else .34,glass=bool(p.get('glass')))
cap=mat('Closure finish',p['cap'],.22 if p.get('metal') else .32,p.get('metal',0));white=mat('Soft ivory insert','#efede5',.4);clear=mat('Clear overcap','#f3f4ed',.07,glass=True)
def mesh(name,verts,faces,material,key):
 me=bpy.data.meshes.new(name);me.from_pydata(verts,[],faces);me.update();o=bpy.data.objects.new(name,me);bpy.context.collection.objects.link(o);o.data.materials.append(material);o.parent=group(key);objects.append(o)
 for f in me.polygons:f.use_smooth=abs(f.normal.z)<.98
 return o
def revolve(name,profile,material,key,n=64,depth=1,exponent=2,closed=True):
 vs=[];fs=[]
 for z,r in profile:
  for i in range(n):
   a=2*math.pi*i/n;c,s=math.cos(a),math.sin(a);vs.append((r*math.copysign(abs(c)**(2/exponent),c),r*depth*math.copysign(abs(s)**(2/exponent),s),z))
 for j in range(len(profile)-1):
  for i in range(n):a=j*n+i;b=j*n+(i+1)%n;fs.append((a,b,b+n,a+n))
 if closed:fs.extend([tuple(reversed(range(n))),tuple((len(profile)-1)*n+i for i in range(n))])
 o=mesh(name,vs,fs,material,key)
 uv=o.data.uv_layers.new()
 for f in o.data.polygons:
  for li in f.loop_indices:
   vi=o.data.loops[li].vertex_index;uv.data[li].uv=(vi%n/n,vi//n/max(1,len(profile)-1))
 return o
def sphere(name,loc,scale,material,key):
 bpy.ops.mesh.primitive_uv_sphere_add(segments=32,ring_count=16,location=loc);o=bpy.context.object;o.name=name;o.scale=scale;bpy.ops.object.transform_apply(location=False,rotation=False,scale=True);o.data.materials.append(material);o.parent=group(key);objects.append(o)
 for f in o.data.polygons:f.use_smooth=True
 return o
def box(name,loc,size,material,key,bevel=.04):
 bpy.ops.mesh.primitive_cube_add(size=1,location=loc);o=bpy.context.object;o.name=name;o.scale=size;bpy.ops.object.transform_apply(location=False,rotation=False,scale=True);o.data.materials.append(material);o.parent=group(key)
 mod=o.modifiers.new('Soft edge','BEVEL');mod.width=bevel;mod.segments=4;bpy.context.view_layer.objects.active=o;bpy.ops.object.modifier_apply(modifier=mod.name)
 o.modifiers.new('Weighted corner normals','WEIGHTED_NORMAL');objects.append(o);return o
def tube(name,points,r,material,key):
 curve=bpy.data.curves.new(name,'CURVE');curve.dimensions='3D';curve.resolution_u=12;curve.bevel_depth=r;curve.bevel_resolution=3;sp=curve.splines.new('BEZIER');sp.bezier_points.add(len(points)-1)
 for b,co in zip(sp.bezier_points,points):b.co=co;b.handle_left_type=b.handle_right_type='AUTO'
 o=bpy.data.objects.new(name,curve);bpy.context.collection.objects.link(o);bpy.context.view_layer.objects.active=o;o.select_set(True);bpy.ops.object.convert(target='MESH');o=bpy.context.object;o.data.materials.append(material);o.parent=group(key);objects.append(o);return o
w,h,d,e=p['w'],p['h'],p['depth'],p['exponent'];neck=w if p['shape']=='jar' else min(.22,w*.58)
if p['shape']=='jar':profile=[(0,w*.88),(.04,w*.97),(.10,w),(h-.14,w),(h-.08,w*.94),(h,neck*.94)]
elif p['shape']=='cone':profile=[(0,w*.92),(.06,w),(.27,w),(h-.28,neck*1.5),(h-.12,neck),(h,neck)]
elif p['shape']=='pouch':profile=[(0,w*.80),(.06,w*.94),(.15,w),(h*.28,w*.96),(h*.58,w*.74),(h*.78,w*.41),(h*.89,neck),(h*.94,neck*1.25),(h,neck)]
elif p['shape']=='oval':profile=[(0,w*.65),(.05,w*.8),(.20,w*.95),(h*.4,w),(h*.62,w*.94),(h*.78,w*.72),(h*.91,neck),(h,neck)]
else:profile=[(0,w*.9),(.05,w*.98),(.12,w),(h-.37,w),(h-.25,w*.92),(h-.14,neck*1.2),(h-.07,neck),(h,neck)]
# Rounded interpolation preserves flat sides while softening shoulders and base.
def rad(z):
 for i in range(len(profile)-1):
  a,b=profile[i:i+2]
  if z<=b[0]:
   t=max(0,min(1,(z-a[0])/(b[0]-a[0])));t=t if p['shape']=='cone' else t*t*(3-2*t);return a[1]+(b[1]-a[1])*t
 return profile[-1][1]
outer=[(a[0]+(b[0]-a[0])*k/6,rad(a[0]+(b[0]-a[0])*k/6)) for a,b in zip(profile,profile[1:]) for k in range(6)]+[profile[-1]]
wall=.045 if p['shape']=='jar' else .035
inner=[(z,max(.04,r-wall)) for z,r in reversed(outer) if z>.12]+[(.12,.04)]
revolve('Hollow body',outer+inner,body,'Body',96,d,e)
# Visible neck rings only; thread pitch is illustrative, not a tooling specification.
for z in (h-.04,h-.10):revolve('Neck bead',[(z-.012,neck),(z,neck+.015),(z+.012,neck)],body,'Body',64,d if p['shape']=='jar' else 1,2 if p['shape']!='jar' else e)
top=p['top'];topz=h
if top=='screw':
 r=w*1.025;ch=.36;revolve('Open screw lid',[(h-.02,r*.94),(h,r),(h+ch-.05,r),(h+ch,r*.95),(h+ch,.01),(h+ch-.055,.01),(h+ch-.055,r-.06),(h-.02,r-.06)],cap,'Closure',96,d,e,False)
 revolve('Inner lid',[(h-.03,w*.91),(h+.005,w*.91),(h+.025,w*.85),(h+.025,.01)],white,'InnerLid',64,d,e)
 sphere('Lift tab',(w*.42,0,h+.04),(.15,.10,.025),white,'InnerLid')
 topz=h+ch
elif top in ('pump','foam','spray','dropper'):
 r=neck*1.17;ch=.30 if top=='foam' else .24
 revolve('Closure collar',[(h-.03,r*.91),(h,r),(h+ch,r),(h+ch+.025,r*.87),(h+ch+.025,neck*.38),(h+ch-.04,neck*.38),(h+ch-.04,r-.04),(h-.03,r-.04)],cap,'Closure',64,1,2,False)
 for i in range(40):
  a=i*2*math.pi/40;sphere('Closure grip',(r*math.cos(a),r*math.sin(a),h+ch*.5),(.006,.006,ch*.43),cap,'Closure')
 stemz=h+ch
 if top=='dropper':
  revolve('Rubber bulb',[(stemz,.11),(stemz+.06,.12),(stemz+.34,.11),(stemz+.41,.075),(stemz+.43,.01)],white,'Actuator');topz=stemz+.43
  revolve('Visible dropper tube',[(h-.65,.022),(stemz+.05,.022)],clear,'Actuator',24)
 else:
  stemh=.12 if top=='spray' else .25
  revolve('Pump stem',[(stemz,.065),(stemz+stemh,.065)],cap,'PumpStem',40)
  headz=stemz+stemh;hr=.105 if top=='spray' else .18
  revolve('Press head',[(headz,hr*.9),(headz+.02,hr),(headz+.16,hr),(headz+.19,hr*.85)],cap,'Actuator',64,1.1)
  if top!='spray':
   tube('Curved dispensing spout',[(0,0,headz+.14),(-.22 if top=='pump' and not p.get('overcap') else -.09,0,headz+.15),(-.45 if top=='pump' and not p.get('overcap') else -.16,0,headz+.13),(-.54 if top=='pump' and not p.get('overcap') else -.20,0,headz+.10)],.033,cap,'Actuator')
  else:sphere('Spray outlet',(0,-hr-.002,headz+.10),(.023,.006,.023),white,'Actuator')
  topz=headz+.19
else:
 ch=.43 if top=='cork' else .50;r=neck*1.6
 if top=='sphere':sphere('Spherical stopper',(0,0,h+.26),(.31,.31,.31),cap,'Closure');topz=h+.57
 else:
  textured=top=='cork' or p['id']=='poster-070'
  if textured:
   from mathutils import noise
   bs=cap.node_tree.nodes.get('Principled BSDF');bs.inputs['Roughness'].default_value=.72
   im=bpy.data.images.new('Cork grain',width=256,height=256);pixels=[];basecolor=tuple(int(p['cap'][i:i+2],16)/255 for i in (1,3,5))
   for yy in range(256):
    for xx in range(256):
     n=noise.fractal(Vector((xx*.12,yy*.19,3.7)),1,2,3);fine=noise.noise(Vector((xx*.8,yy*.8,2)))
     shade=(max(.85,min(1.15,1+n*.12+fine*.08)) if p['id']=='poster-070' else .65 if n>.40 else max(.60,min(1.35,1+n*.55+fine*.16)));pixels.extend([min(1,c*shade) for c in basecolor]+[1])
   im.pixels=pixels;im.pack();tx=cap.node_tree.nodes.new('ShaderNodeTexImage');tx.image=im;cap.node_tree.links.new(tx.outputs['Color'],bs.inputs['Base Color'])

  if top=='faceted':r=w*.8
  revolve('Bottle stopper',[(h-.03,r*.90),(h+.02,r),(h+ch-.035,r*1.04),(h+ch,r*.97),(h+ch,.01),(h+ch-.06,.01),(h+ch-.06,r-.06),(h-.03,r-.06)],cap,'Closure',8 if top=='faceted' else 64, p['depth'] if top=='faceted' else 1,2,False);topz=h+ch
if p.get('overcap'):
 r=neck*1.5;revolve('Protective clear cap',[(h-.02,r),(topz+.08,r),(topz+.10,r*.90),(topz+.10,.01),(topz+.07,.01),(topz+.07,r-.025),(h-.02,r-.025)],clear,'Overcap',64,closed=False);topz+=.10
if p.get('plinth'):box('White pedestal base',(0,0,.17),(w*2.01,w*d*2.01,.34),white,'Body',.045)
if p.get('rope'):
 rope=mat('Cord',p['rope'],.72)
 for strand in range(3 if p['id']=='poster-064' else 1):
  pts=[]
  for i in range(65):
   a=i*2*math.pi/64;rr=neck*1.2+.025*math.cos(i*.6+strand*2);pts.append((rr*math.cos(a),rr*math.sin(a),h-.12+.025*math.sin(i*.6+strand*2)))
  tube('Neck cord',pts,.025 if p['id']=='poster-064' else .016,rope,'Body')
 for dx in (.04,-.035):tube('Cord tail',[(neck,0,h-.12),(w*.83,-w*d*.65,h*.7),(w+dx,-w*d*.65,h*.36)],.025 if p['id']=='poster-064' else .014,rope,'Body')
# Separate curved label and logo plates, both from editable vector artwork.
for kind,key in [('label','Body'),('print','LogoPrint')]:
 m=mat('Fixed label' if kind=='label' else 'Logo print', '#ffffff',.42,p.get('labelMetal',0) if kind=='label' else 0);bs=m.node_tree.nodes.get('Principled BSDF');tx=m.node_tree.nodes.new('ShaderNodeTexImage');tx.image=bpy.data.images.load(str(out/(kind+'.png')));tx.image.pack();m.node_tree.links.new(tx.outputs['Color'],bs.inputs['Base Color']);m.node_tree.links.new(tx.outputs['Alpha'],bs.inputs['Alpha']);m.surface_render_method='DITHERED'
 z0=h*.17;dh=h*.62;dw=w*1.50;vs=[];fs=[];nx,ny=40,30
 for j in range(ny+1):
  z=z0+dh*j/ny;r=rad(z)
  for i in range(nx+1):
   x=(-.5+i/nx)*min(dw,r*1.70);y=-r*d*(max(.001,1-(abs(x)/r)**e))**(1/e)-(.002 if kind=='label' else .003);vs.append((x,y,z))
 for j in range(ny):
  for i in range(nx):a=j*(nx+1)+i;fs.append((a,a+1,a+nx+2,a+nx+1))
 o=mesh('Label artwork' if kind=='label' else 'Independent liaose wordmark',vs,fs,m,key);uv=o.data.uv_layers.new()
 for f in o.data.polygons:
  for li in f.loop_indices:
   vi=o.data.loops[li].vertex_index;uv.data[li].uv=(vi%(nx+1)/nx,vi//(nx+1)/ny)
# Preserve the supplied floral border through UV mapping; the central print stays independent.
if p.get('floral'):
 m=mat('Reference floral border','#ffffff',.48);bs=m.node_tree.nodes.get('Principled BSDF');tx=m.node_tree.nodes.new('ShaderNodeTexImage');tx.image=bpy.data.images.load(str(CLIENT/'featured-assets/poster-066.png'));tx.image.pack();m.node_tree.links.new(tx.outputs['Color'],bs.inputs['Base Color'])
 vs=[];fs=[];nx,ny=40,40;z0=h*.17;dh=h*.62;dw=w*1.50
 for j in range(ny+1):
  z=z0+dh*j/ny;r=rad(z)
  for i in range(nx+1):
   x=(-.5+i/nx)*min(dw,r*1.70);y=-r*d*max(.001,1-(abs(x)/r)**e)**(1/e)-.004;vs.append((x,y,z))
 for j in range(ny):
  for i in range(nx):
   u=(i+.5)/nx;v=(j+.5)/ny
   if u<.18 or u>.84 or v<.16 or v>.77:
    a=j*(nx+1)+i;fs.append((a,a+1,a+nx+2,a+nx+1))
 ob=mesh('Original rose artwork border',vs,fs,m,'Body');uv=ob.data.uv_layers.new()
 for f in ob.data.polygons:
  for li in f.loop_indices:
   vi=ob.data.loops[li].vertex_index;u=vi%(nx+1)/nx;v=vi//(nx+1)/ny;uv.data[li].uv=((345+u*520)/tx.image.size[0],(tx.image.size[1]-1108+v*512)/tx.image.size[1])

# Keep paired bottles and outer packaging as genuine geometry.
if p.get('duo') or p.get('smallTwin'):
 originals=list(objects);offset=.63 if p.get('duo') else .47
 for o in originals:
  twin=o.copy();twin.data=o.data.copy();bpy.context.collection.objects.link(twin);twin.parent=o.parent;factor=.76 if p.get('smallTwin') else 1;twin.scale*=factor;twin.location*=factor;twin.location.x-=offset*2;objects.append(twin)
 for g in groups.values():
  for o in g.children:o.location.x+=offset
if p.get('carton') or p.get('refill'):
 cm=mat('Outer packaging',p.get('cap') if p['id']=='poster-068' else '#dbccb0',.75);cx=-w*2.5
 if p.get('refill'):
  cm=mat('Refill pouch','#c9a35c',.4);o=revolve('Stand-up refill pouch',[(.02,.36),(.10,.52),(topz-.10,.47),(topz,.43)],cm,'OuterPack',48,.28,7);o.location.x=cx
  box('Top heat seal',(cx,0,topz-.03),(.88,.12,.10),cm,'OuterPack',.01)
 else:box('Folding carton',(cx,.12,topz*.49),(w*1.65,w*d*1.5,topz*.98),cm,'OuterPack',.016)
 # Front branding of the secondary package uses the same separate print plate.
 for kind,key in [('label','OuterPack'),('print','LogoPrint')]:
  source=next(o for o in objects if o.name==('Label artwork' if kind=='label' else 'Independent liaose wordmark'))
  material=source.data.materials[0];z0=topz*.2;z1=topz*.8;ww=w*1.40;yy=-(.17 if p.get('refill') else w*d*.75)-(.006 if kind=='print' else .004)
  ob=mesh('Secondary '+kind,[(cx-ww/2,yy,z0),(cx+ww/2,yy,z0),(cx+ww/2,yy,z1),(cx-ww/2,yy,z1)],[(0,1,2,3)],material,key);uv=ob.data.uv_layers.new()
  for li,co in enumerate([(0,0),(1,0),(1,1),(0,1)]):uv.data[li].uv=co
# Normalize the visual set to the shared studio height without changing its proportions.
scale=2.9/topz
for g in groups.values():g.scale=(scale,scale,scale)
if p.get('carton') or p.get('refill'):
 for g in groups.values():g.location.x=w*.75*scale
bpy.ops.object.select_all(action='DESELECT')
for o in objects+list(groups.values()):o.select_set(True)
bpy.context.view_layer.objects.active=objects[0]
model=CLIENT/'packaging-assets'/f"{p['id']}.glb"
bpy.ops.export_scene.gltf(filepath=str(model),export_format='GLB',use_selection=True,export_apply=True,export_yup=True,export_extras=True)
bpy.ops.wm.save_as_mainfile(filepath=str(out/(p['id']+'.blend')))
meta={'id':p['id'],'components':list(groups),'height':2.9,'illustrativeDimensions':True,'containsFormula':False,'reference':f'featured-assets/{p["id"]}.png','editableArtwork':['label.svg','print.svg']}
(out/'model-info.json').write_text(json.dumps(meta,indent=2)+'\n');print(json.dumps(meta))
