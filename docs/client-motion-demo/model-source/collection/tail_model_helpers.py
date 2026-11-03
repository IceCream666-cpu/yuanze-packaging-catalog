"""Shared mesh and export primitives for the separately calibrated 066–070 models."""
import bpy,bmesh,math,json,subprocess,xml.etree.ElementTree as ET
from pathlib import Path
from mathutils import Vector
BASE=Path(__file__).resolve().parent;CLIENT=BASE.parents[1]
NODE='/Users/icecream/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/bin/node'
class Model:
 def __init__(self,id):
  self.id=id;self.out=BASE/id;self.out.mkdir(exist_ok=True);self.groups={}
  self.logo=next(e.attrib['d'] for e in ET.parse(self.out/'print.svg').getroot().iter() if e.tag.endswith('path'))
  bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)
 def mat(self,name,color,rough=.3,trans=0,metal=0):
  m=bpy.data.materials.new(name);m.use_nodes=True;b=m.node_tree.nodes.get('Principled BSDF');rgb=[int(color[i:i+2],16)/255 for i in (1,3,5)];b.inputs['Base Color'].default_value=(*[v/12.92 if v<=.04045 else ((v+.055)/1.055)**2.4 for v in rgb],1);b.inputs['Roughness'].default_value=rough;b.inputs['Transmission Weight'].default_value=trans;b.inputs['Metallic'].default_value=metal;b.inputs['IOR'].default_value=1.49;return m
 def mesh(self,name,vs,fs,m,parent,smooth=True):
  data=bpy.data.meshes.new(name);data.from_pydata(vs,[],fs);data.update();o=bpy.data.objects.new(name,data);bpy.context.collection.objects.link(o);data.materials.append(m)
  if parent not in self.groups:self.groups[parent]=bpy.data.objects.new(parent,None);bpy.context.collection.objects.link(self.groups[parent])
  o.parent=self.groups[parent]
  for f in data.polygons:f.use_smooth=smooth and abs(f.normal.z)<.999
  return o
 def loft(self,name,profile,m,parent,n=128):
  vs=[];rings=[];fs=[]
  for z,rx,ry,r in profile:
   if rx==0:rings.append([len(vs)]);vs.append((0,0,z));continue
   points=[]
   for q in range(4):
    cx=(rx-r)*(1 if q in (0,3) else -1);cy=(ry-r)*(1 if q<2 else -1)
    for i in range(n//4):
     a=q*math.pi/2+i/(n//4-1)*math.pi/2;points.append((cx+r*math.cos(a),cy+r*math.sin(a),z))
   rings.append(list(range(len(vs),len(vs)+n)));vs.extend(points)
  for a,b in zip(rings,rings[1:]):
   if len(a)==len(b)==1:continue
   for i in range(n):
    j=(i+1)%n;fs.append((a[0],b[j],b[i]) if len(a)==1 else (a[i],a[j],b[0]) if len(b)==1 else (a[i],a[j],b[j],b[i]))
  o=self.mesh(name,vs,fs,m,parent);bm=bmesh.new();bm.from_mesh(o.data);bmesh.ops.remove_doubles(bm,verts=list(bm.verts),dist=1e-7);bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));assert all(e.is_manifold for e in bm.edges),name;assert bm.calc_volume(signed=True)>0,name;bm.to_mesh(o.data);bm.free();o.data.update();return o
 def lathe(self,name,profile,m,parent,n=128):return self.loft(name,[(z,r,r,r) for z,r in profile],m,parent,n)
 def texture(self,name,file,rough=.65,normal=None):
  m=self.mat(name,'#ffffff',rough);b=m.node_tree.nodes.get('Principled BSDF');b.inputs['Specular IOR Level'].default_value=.025
  t=m.node_tree.nodes.new('ShaderNodeTexImage');t.image=bpy.data.images.load(str(self.out/file));t.image.pack();m.node_tree.links.new(t.outputs['Color'],b.inputs['Base Color']);m.node_tree.links.new(t.outputs['Alpha'],b.inputs['Alpha']);m.surface_render_method='DITHERED'
  if normal:
   t=m.node_tree.nodes.new('ShaderNodeTexImage');t.image=bpy.data.images.load(str(self.out/normal));t.image.colorspace_settings.name='Non-Color';t.image.pack();n=m.node_tree.nodes.new('ShaderNodeNormalMap');n.inputs['Strength'].default_value=.55;m.node_tree.links.new(t.outputs['Color'],n.inputs['Color']);m.node_tree.links.new(n.outputs['Normal'],b.inputs['Normal'])
  return m
 def artwork(self,label,printing):
  for kind,svg in [('label',label),('print',printing)]: (self.out/(kind+'.svg')).write_text(svg)
  subprocess.run([NODE,'--input-type=module','-e',"import sharp from '/Users/icecream/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/sharp/dist/index.mjs';import fs from 'node:fs/promises';for(const k of ['label','print'])await sharp(await fs.readFile(process.argv[1]+'/'+k+'.svg'),{density:144}).png().toFile(process.argv[1]+'/'+k+'.png');",str(self.out)],check=True)
 def sheet(self,name,width,height,bottom,surface,material,parent,nx=64,ny=48,offset=.001):
  vs=[];fs=[]
  for j in range(ny+1):
   z=bottom+height*j/ny
   for i in range(nx+1):
    x=(i/nx-.5)*width;vs.append((x,surface(x,z)-offset,z))
  for j in range(ny):
   for i in range(nx):a=j*(nx+1)+i;fs.append((a,a+1,a+nx+2,a+nx+1))
  o=self.mesh(name,vs,fs,material,parent);uv=o.data.uv_layers.new()
  for f in o.data.polygons:
   for li in f.loop_indices:
    v=o.data.loops[li].vertex_index;uv.data[li].uv=(v%(nx+1)/nx,v//(nx+1)/ny)
  return o
 def export(self,total,pivots,info,config,version=''):
  scale=2.9/total;assert set(pivots)==set(self.groups)
  for name,g in self.groups.items():
   pivot=Vector((0,0,pivots[name]))
   for child in g.children:child.location-=pivot
   g.location=pivot*scale;g.scale=(scale,scale,scale)
  bpy.context.view_layer.update();bounds={}
  for name,g in self.groups.items():
   points=[o.matrix_world@v.co for o in g.children for v in o.data.vertices];bounds[name]={'min':[min(p[i] for p in points) for i in range(3)],'max':[max(p[i] for p in points) for i in range(3)]}
  actual=max(v['max'][2] for v in bounds.values())-min(v['min'][2] for v in bounds.values());assert abs(actual-2.9)<.015,(actual,total)
  bpy.ops.object.select_all(action='SELECT');bpy.ops.export_scene.gltf(filepath=str(CLIENT/'packaging-assets'/f'{self.id}{version}.glb'),export_format='GLB',use_selection=True,export_apply=True,export_yup=True,export_extras=True)
  bpy.ops.wm.save_as_mainfile(filepath=str(self.out/f'{self.id}.blend'))
  info.update(id=self.id,components=list(self.groups),height=2.9,actualHeight=actual,width=scale,componentBoundsBlenderXYZ=bounds,pivotsHeightToWidth=pivots,containsFormula=False,illustrativeDimensions=True,separateLabelAndPrint=True,reference=f'../../mobile-client-preview/assets/posters/{self.id}.webp',featuredReference=f'featured-assets/{self.id}.png',generatorDependencies=['tail_model_helpers.py'],revision='individual-reference-review-20261025')
  (self.out/'model-info.json').write_text(json.dumps(info,indent=2)+'\n');(self.out/'review-config.json').write_text(json.dumps(config,ensure_ascii=False,indent=2)+'\n');print(self.id,json.dumps({'bounds':bounds,'ratio':total}))
def svg(w,h,body):return f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}">{body}</svg>'
def logo(m,x,y,w,h,color):return f'<svg x="{x}" y="{y}" width="{w}" height="{h}" viewBox="0 0 340 125"><path d="{m.logo}" fill="{color}"/></svg>'
def text(x,y,value,size,spacing=0,color='#191917',serif=False):return f'<text x="{x}" y="{y}" text-anchor="middle" font-family="{("Times New Roman,serif" if serif else "Helvetica Neue,Arial,sans-serif")}" font-size="{size}" letter-spacing="{spacing}" fill="{color}">{value}</text>'
def part(key,node,zh,en,detail,en_detail):return {'key':key,'node':node,'title':[zh,en],'short':[zh,en],'detail':[detail,en_detail]}
def config(parts,offsets,glass=True,frosted=False,clear=False,metal=False,extra=None):
 a={'glass':glass,'frosted':frosted,'pipette':False,'clearLabel':clear,'metal':metal};a.update(extra or {})
 return {'parts':parts,'appearance':a,'explosion':{'offsets':offsets,'scales':{'label':1.15,'print':1.95},'camera':{'centerY':[1.45,3.1],'height':[4.2,7.8],'width':[3.8,7.6],'centerX':[0,-.9]}}}
