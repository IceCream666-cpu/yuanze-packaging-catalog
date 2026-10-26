"""Micro Cream 062: individually calibrated rectangular clear jar and black cap.

The small mesh/artwork helpers are reused by the following three reviewed models.
"""
import bpy, bmesh, math, json, subprocess, xml.etree.ElementTree as ET
from pathlib import Path
from mathutils import Vector

BASE=Path(__file__).resolve().parent
CLIENT=BASE.parents[1]
groups={}

def configure(identifier):
 global OUT,ID,groups
 ID=identifier;OUT=BASE/ID;OUT.mkdir(exist_ok=True);groups={}
 bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)
 return OUT

def mat(name,color,rough=.4,metal=0,trans=0):
 m=bpy.data.materials.new(name);m.use_nodes=True;b=m.node_tree.nodes.get('Principled BSDF')
 rgb=[int(color[i:i+2],16)/255 for i in (1,3,5)]
 b.inputs['Base Color'].default_value=(*[v/12.92 if v<=.04045 else ((v+.055)/1.055)**2.4 for v in rgb],1)
 b.inputs['Roughness'].default_value=rough;b.inputs['Metallic'].default_value=metal;b.inputs['Transmission Weight'].default_value=trans;b.inputs['IOR'].default_value=1.49
 return m

def mesh(name,vertices,faces,material,parent,solid=False):
 data=bpy.data.meshes.new(name);data.from_pydata(vertices,[],faces);data.update()
 obj=bpy.data.objects.new(name,data);bpy.context.collection.objects.link(obj);obj.data.materials.append(material)
 if parent not in groups:groups[parent]=bpy.data.objects.new(parent,None);bpy.context.collection.objects.link(groups[parent])
 obj.parent=groups[parent]
 if solid:
  bm=bmesh.new();bm.from_mesh(data);bmesh.ops.remove_doubles(bm,verts=list(bm.verts),dist=1e-6);bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces))
  assert all(e.is_manifold for e in bm.edges),name+' must be a closed solid'
  assert bm.calc_volume(signed=True)>0,name+' must face outward'
  bm.to_mesh(data);bm.free();data.update()
 for face in data.polygons:face.use_smooth=abs(face.normal.z)<.999
 return obj

def ring(rx,ry,r,n=128):
 result=[]
 for q in range(4):
  cx=(rx-r)*(1 if q in (0,3) else -1);cy=(ry-r)*(1 if q<2 else -1)
  for i in range(n//4):
   a=q*math.pi/2+i/(n//4-1)*math.pi/2;result.append((cx+r*math.cos(a),cy+r*math.sin(a)))
 return result

def loft(name,profile,material,parent,n=128):
 vs=[];rs=[];fs=[]
 for z,rx,ry,r in profile:
  if rx==0:rs.append([len(vs)]);vs.append((0,0,z))
  else:rs.append(list(range(len(vs),len(vs)+n)));vs.extend((x,y,z) for x,y in ring(rx,ry,r,n))
 for a,b in zip(rs,rs[1:]):
  if len(a)==len(b)==1:continue
  for i in range(n):
   j=(i+1)%n;fs.append((a[0],b[j],b[i]) if len(a)==1 else (a[i],a[j],b[0]) if len(b)==1 else (a[i],a[j],b[j],b[i]))
 return mesh(name,vs,fs,material,parent,True)

def lathe(name,profile,material,parent,n=128):
 return loft(name,[(z,r,r,r) for z,r in profile],material,parent,n)

def artwork(width,height,logo_rect,lines,background='clear',ink='#111815',name='print',label_name='label'):
 logo=next(e.attrib['d'] for e in ET.parse(BASE/'poster-039/print.svg').getroot().iter() if e.tag.endswith('path'))
 if background=='clear':paper=f'<rect x="2" y="2" width="{width-4}" height="{height-4}" rx="15" fill="#fffdf7" fill-opacity=".14" stroke="#899798" stroke-opacity=".5" stroke-width="3"/>'
 else:paper=f'<defs><filter id="grain"><feTurbulence type="fractalNoise" baseFrequency=".62" numOctaves="3" stitchTiles="stitch"/><feColorMatrix type="saturate" values="0"/><feComponentTransfer><feFuncA type="linear" slope=".07"/></feComponentTransfer><feBlend in="SourceGraphic" mode="multiply"/></filter></defs><rect x="1" y="1" width="{width-2}" height="{height-2}" rx="8" fill="{background}" filter="url(#grain)"/>'
 header=f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">'
 (OUT/(label_name+'.svg')).write_text(header+paper+'</svg>')
 x,y,w,h=logo_rect
 contents=f'<svg x="{x}" y="{y}" width="{w}" height="{h}" viewBox="0 0 340 125" preserveAspectRatio="none"><path d="{logo}" fill="{ink}"/></svg>'
 for text,z,size,spacing,font in lines:
  if text=='—':contents+=f'<path d="M {width*.41} {z} H {width*.59}" stroke="{ink}" stroke-width="1.1"/>'
  else:contents+=f'<text x="{width/2}" y="{z}" text-anchor="middle" fill="{ink}" font-family="{font}" font-size="{size}" letter-spacing="{spacing}">{text}</text>'
 (OUT/(name+'.svg')).write_text(header+contents+'</svg>')
 node='/Users/icecream/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/bin/node'
 js="""import sharp from '/Users/icecream/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/sharp/dist/index.mjs';import fs from 'node:fs/promises';for(const n of process.argv.slice(2))await sharp(await fs.readFile(process.argv[1]+'/'+n+'.svg'),{density:144}).png().toFile(process.argv[1]+'/'+n+'.png');"""
 subprocess.run([node,'--input-type=module','-e',js,str(OUT),name,label_name],check=True)

def layer(name,parent,filename,width,bottom,top,surface,rough=.65,metal=0,offset=0):
 m=mat(name+' material','#ffffff',rough,metal);b=m.node_tree.nodes.get('Principled BSDF');b.inputs['Specular IOR Level'].default_value=.02 if parent=='LogoPrint' else .3
 tex=m.node_tree.nodes.new('ShaderNodeTexImage');tex.image=bpy.data.images.load(str(OUT/(filename+'.png')));tex.image.pack();m.node_tree.links.new(tex.outputs['Color'],b.inputs['Base Color']);m.node_tree.links.new(tex.outputs['Alpha'],b.inputs['Alpha']);m.surface_render_method='DITHERED'
 nx,ny=64,8;vs=[];fs=[]
 for j in range(ny+1):
  z=bottom+(top-bottom)*j/ny
  for i in range(nx+1):
   x=(i/nx-.5)*width;vs.append((x,surface(x,z)-offset,z))
 for j in range(ny):
  for i in range(nx):a=j*(nx+1)+i;fs.append((a,a+1,a+nx+2,a+nx+1))
 obj=mesh(name,vs,fs,m,parent);uv=obj.data.uv_layers.new()
 for face in obj.data.polygons:
  for k in face.loop_indices:
   v=obj.data.loops[k].vertex_index;uv.data[k].uv=(v%(nx+1)/nx,v//(nx+1)/ny)
 return obj

def part(key,node,zh,en,detail,detail_en):
 short={'closure':'外盖','liner':'内盖','jar':'瓶身' if '瓶' in zh else '罐身','label':'标贴','print':'文字','head':'泵头','stem':'泵杆','cord':'编绳','refill':'补充袋'}
 return {'key':key,'node':node,'title':[zh,en],'short':[short.get(key,zh),en.split()[0]],'detail':[detail,detail_en]}

def finish(pivots,parts,appearance,explosion,info):
 bpy.context.view_layer.update()
 vertices=[o.matrix_world@v.co for o in bpy.data.objects if o.type=='MESH' for v in o.data.vertices]
 bottom=min(v.z for v in vertices);top=max(v.z for v in vertices);scale=2.9/(top-bottom)
 assert abs(bottom)<1e-6
 assert set(groups)==set(pivots)
 for name,g in groups.items():
  pivot=Vector((0,0,pivots[name]))
  for child in g.children:child.location-=pivot
  g.location=pivot*scale;g.scale=(scale,scale,scale)
 bpy.context.view_layer.update()
 bounds={}
 for name,g in groups.items():
  pts=[o.matrix_world@v.co for o in g.children for v in o.data.vertices]
  bounds[name]={'min':[min(p[i] for p in pts) for i in range(3)],'max':[max(p[i] for p in pts) for i in range(3)]}
 bpy.ops.object.select_all(action='SELECT')
 bpy.ops.export_scene.gltf(filepath=str(CLIENT/'packaging-assets'/f'{ID}.glb'),export_format='GLB',use_selection=True,export_apply=True,export_yup=True,export_extras=True)
 bpy.ops.wm.save_as_mainfile(filepath=str(OUT/(ID+'.blend')))
 info.update({'id':ID,'components':list(groups),'height':2.9,'scaleFromReferenceWidth':scale,'componentBoundsBlenderXYZ':bounds,'illustrativeDimensions':True,'containsFormula':False,'reference':f'../../mobile-client-preview/assets/posters/{ID}.webp','separateLabelAndPrint':True})
 (OUT/'model-info.json').write_text(json.dumps(info,indent=2)+'\n')
 (OUT/'review-config.json').write_text(json.dumps({'parts':parts,'appearance':appearance,'explosion':explosion},ensure_ascii=False,indent=2)+'\n')
 print(ID,'complete',len(groups),'groups',bounds)

def build():
 configure('poster-062')
 glass=mat('Micro neutral clear glass','#ffffff',.025,trans=1)
 black=mat('Micro polished black lid','#080c0e',.105);black.node_tree.nodes.get('Principled BSDF').inputs['Coat Weight'].default_value=.25
 inner=mat('Micro warm white liner','#eceee8',.35)
 outer=[(0,0,0,0),(0,.455,.255,.025),(.008,.48,.28,.03),(.023,.495,.295,.038),(.04,.5,.30,.044),(.400,.5,.30,.044),(.420,.496,.296,.047),(.437,.481,.281,.052),(.449,.462,.263,.058),(.481,.462,.263,.058)]
 inside=[(.481,.419,.220,.060),(.461,.419,.220,.060),(.422,.438,.239,.055),(.396,.451,.251,.047),(.125,.451,.251,.047),(.108,.437,.237,.049),(.10,.405,.205,.052),(.10,0,0,0)]
 loft('Hollow wide rectangular glass jar',outer+inside,glass,'Body')
 loft('Rounded black rectangular cap shell',[(.452,.479,.280,.026),(.452,.491,.292,.026),(.461,.499,.30,.028),(.678,.499,.30,.028),(.690,.495,.296,.027),(.700,.482,.283,.026),(.700,0,0,0),(.674,0,0,0),(.674,.469,.270,.032),(.466,.469,.270,.032),(.452,.479,.280,.026)],black,'Closure')
 loft('Rectangular lift-out inner liner',[(.476,0,0,0),(.476,.411,.211,.05),(.482,.426,.227,.052),(.489,.431,.232,.054),(.497,.423,.224,.054),(.498,0,0,0)],inner,'InnerLid')
 tab=lathe('Inner liner lifting tab',[(0,0),(0,.028),(.010,.035),(.015,.025),(.015,0)],inner,'InnerLid',48);tab.scale=(1.6,.65,1);tab.location=(.30,-.09,.496)
 artwork(740,250,(165,15,410,150),[('MICRO HYDRATION CREAM',224,28,1.9,'Helvetica Neue,Arial,sans-serif')])
 layer('Blank transparent Micro carrier','PaperLabel','label',.74,.135,.385,lambda x,z:-.30,rough=.24,offset=.0014)
 layer('Complete Micro logo and product name','LogoPrint','print',.74,.135,.385,lambda x,z:-.30,offset=.0022)
 parts=[part('closure','Closure','黑亮外盖','Black lid','圆角长方形盖壳，内侧中空。','Rounded rectangular lid with a hollow inner shell.'),part('liner','InnerLid','提拉内盖','Inner liner','隐藏结构示意，独立上提。','Illustrative inner liner lifts out separately.'),part('jar','Body','透明方罐','Clear jar','厚底、圆角方形罐壁与宽开口。','Rounded rectangular jar with a thick base and wide opening.'),part('label','PaperLabel','透明膜','Clear film','原图无纸标边界，透明底材示意。','Clear carrier film represents the unmarked label boundary.'),part('print','LogoPrint','完整文字','Lettering','品牌与完整产品名一同展开。','Brand and complete product name move out together.')]
 finish({'Body':0,'Closure':.46,'InnerLid':.49,'PaperLabel':.26,'LogoPrint':.26},parts,{'glass':True,'frosted':False,'pipette':False,'clearLabel':True,'metal':False,'studio':{'background':'#d5e5e6','ink':'#142c32'}},{'offsets':{'closure':[0,3.2,0],'liner':[0,1.45,0],'label':[-2.1,.08,.65],'print':[-4.2,.18,1.65]},'scales':{'label':1.15,'print':1.95},'rotations':{'closure':[-.6,-.5,-.05]},'camera':{'centerY':[1.45,3.05],'height':[4.3,7.8],'width':[5.1,10.2],'centerX':[0,-1.25]}},{'closedHeightToWidth':.70,'depthToWidth':.60,'innerFloorToWidth':.10,'printIncludes':['liaose','MICRO HYDRATION CREAM'],'hiddenStructure':'Inner lift-out liner and clear carrier are illustrative; no gel, bubbles or background bottle.','generator':'build_micro_cream.py'})

if __name__=='__main__':build()
