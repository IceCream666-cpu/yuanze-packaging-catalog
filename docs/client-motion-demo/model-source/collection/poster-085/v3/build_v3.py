"""085 v3: preserve approved proportions/artwork, export actual textured PBR.

All dimensions are illustrative scene units, not manufacturing measurements.
Run with the locally installed Blender; previous source and assets stay intact.
"""
import bpy,bmesh,json,math,shutil,hashlib,sys
import numpy as np
from pathlib import Path
from mathutils import Vector

HERE=Path(__file__).resolve().parent;OLD=HERE.parent;CLIENT=HERE.parents[3]
GLB=CLIENT/'packaging-assets/poster-085-v3.glb'
bpy.ops.wm.open_mainfile(filepath=str(OLD/'poster-085-v2.blend'))
bpy.context.preferences.filepaths.save_version=0
scene=bpy.context.scene;scene.frame_set(1);bpy.context.view_layer.update()
NAMES=['Body','Pump','TubeCap','Label','LogoInk','NameInk']
roots={n:bpy.data.objects[n] for n in NAMES};TX=-.72;BX=.64
def points(o):return [o.matrix_world@v.co for v in o.data.vertices]
preserved_names=['Empty tall cylinder | ivory rounded heel and hollow threaded neck',
 'Long clear hollow dip tube | near-bottom angled intake','Tube cap | lower hinged lid','Tube cap | rear hinge']
preserved={n:points(bpy.data.objects[n]) for n in preserved_names}
for o in list(scene.objects):
 if o.type in {'CAMERA','LIGHT'} or (o.type=='MESH' and o.parent is None):bpy.data.objects.remove(o,do_unlink=True)

def fix(o):
 bm=bmesh.new();bm.from_mesh(o.data)
 bmesh.ops.remove_doubles(bm,verts=list(bm.verts),dist=1e-7)
 bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces))
 assert all(e.is_manifold for e in bm.edges),o.name
 vol=bm.calc_volume(signed=True);assert vol>0,(o.name,vol)
 bm.to_mesh(o.data);bm.free();o.data.update();return vol

def mesh(name,vs,fs,mat,root):
 data=bpy.data.meshes.new(name);data.from_pydata(vs,[],fs);data.update()
 ob=bpy.data.objects.new(name,data);scene.collection.objects.link(ob)
 ob.parent=roots[root];ob.location=-roots[root].location;data.materials.append(mat)
 for f in data.polygons:f.use_smooth=abs(f.normal.z)<.999
 return ob

def monotone(values):
 x=[v[0] for v in values];y=[v[1] for v in values]
 d=[(b-a)/(xb-xa) for xa,xb,a,b in zip(x,x[1:],y,y[1:])];slopes=[d[0]]
 for i in range(1,len(x)-1):
  if d[i-1]*d[i]<=0:slopes.append(0)
  else:
   h0=x[i]-x[i-1];h1=x[i+1]-x[i];w1=2*h1+h0;w2=h1+2*h0
   slopes.append((w1+w2)/(w1/d[i-1]+w2/d[i]))
 slopes.append(d[-1])
 def evaluate(z):
  if z<=x[0]:return y[0]
  if z>=x[-1]:return y[-1]
  i=next(i for i in range(len(x)-1) if x[i]<=z<=x[i+1]);h=x[i+1]-x[i];t=(z-x[i])/h
  return (2*t**3-3*t*t+1)*y[i]+(t**3-2*t*t+t)*h*slopes[i]+(-2*t**3+3*t*t)*y[i+1]+(t**3-t*t)*h*slopes[i+1]
 return evaluate

ivory=bpy.data.materials['Warm ivory satin molded polymer']
bronze=bpy.data.materials['Satin copper bronze decorative finish']
rose=bpy.data.materials['Muted rose bronze tube decoration']
controls=[(.18,.092,.092),(.25,.096,.096),(.27,.125,.116),(.29,.245,.173),(.33,.25,.18),
 (.40,.256,.186),(.55,.272,.19),(.85,.293,.181),(1.2,.315,.157),(1.55,.341,.122),
 (1.9,.366,.077),(2.17,.38,.025),(2.21,.38,.018)]
rx_at=monotone([(z,x) for z,x,y in controls]);ry_at=monotone([(z,y) for z,x,y in controls])
def tube_front(x,z):return -ry_at(z)*math.sqrt(max(0,1-(x/rx_at(z))**2))
old_tube=bpy.data.objects['Empty flexible tube | sealed tail and open dispensing nozzle'];bpy.data.objects.remove(old_tube,do_unlink=True)
zs=[];maximum_profile_error=0
def sample_interval(a,b,depth=0):
 global maximum_profile_error
 pa=Vector((rx_at(a),ry_at(a)));pb=Vector((rx_at(b),ry_at(b)))
 error=max((Vector((rx_at(a+(b-a)*t),ry_at(a+(b-a)*t)))-(pa*(1-t)+pb*t)).length for t in [.25,.5,.75])
 if error>.0002 and depth<14:
  m=(a+b)/2;sample_interval(a,m,depth+1);sample_interval(m,b,depth+1)
 else:zs.append(a);maximum_profile_error=max(maximum_profile_error,error)
for a,b in zip(controls,controls[1:]):sample_interval(a[0],b[0])
zs.append(controls[-1][0])
rows=[(z,rx_at(z),ry_at(z)) for z in zs]
rows += [(2.21,.368,.005)]+[(z,rx_at(z)-.012,max(.005,ry_at(z)-.012)) for z in reversed(zs) if .29<=z<=2.17]
rows += [(.27,.105,.095),(.25,.076,.076),(.18,.076,.076),rows[0]]
vs=[];fs=[];n=128
for z,rx,ry in rows:
 for i in range(n):
  a=math.tau*i/n;vs.append((TX+rx*math.cos(a),ry*math.sin(a),z))
for j in range(len(rows)-1):
 for i in range(n):a=j*n+i;b=j*n+(i+1)%n;fs.append((a,b,b+n,a+n))
tube=mesh('Empty flexible tube | sealed tail and open dispensing nozzle',vs,fs,ivory,'Body');fix(tube)
tube['nominalBodyWall']=.012;tube['containsFormula']=False

# Preserve all 72 original embossed ridges and the exact seal-block geometry.
seal=bpy.data.objects['Tube integrated flattened heat seal'];ridges=[bpy.data.objects[f'Tube seal ridge {i:02}'] for i in range(72)]
seal_vertices=sum(len(o.data.vertices) for o in [seal]+ridges)
bpy.ops.object.select_all(action='DESELECT')
for o in [seal]+ridges:o.select_set(True)
bpy.context.view_layer.objects.active=seal;bpy.ops.object.join()
seal.name='Tube heat seal | original 72 fine ridges merged';assert len(seal.data.vertices)==seal_vertices
seal['originalRidgesPreserved']=72

# Reproject only depth of existing tube lettering. Original UV, X/Z and artwork remain.
for name in ['Tube liaose','Tube HAIR TREATMENT']:
 ob=bpy.data.objects[name];inv=ob.matrix_world.inverted()
 for v in ob.data.vertices:
  q=ob.matrix_world@v.co;q.y=tube_front(q.x-TX,q.z)-.006;v.co=inv@q
 ob.data.update()
artwork=[]
for name in ['logo','shampoo','treatment']:
 for suffix in ['svg','png']:shutil.copy2(OLD/f'{name}.{suffix}',HERE/f'{name}.{suffix}')
 artwork.append({'name':name,'svgSha256':hashlib.sha256((HERE/f'{name}.svg').read_bytes()).hexdigest(),
  'pngSha256':hashlib.sha256((HERE/f'{name}.png').read_bytes()).hexdigest()})
for mat in bpy.data.materials:
 if not mat.use_nodes:continue
 for node in mat.node_tree.nodes:
  if node.type=='TEX_IMAGE' and node.image:
   path=HERE/Path(node.image.filepath).name
   if path.exists():node.image=bpy.data.images.load(str(path),check_existing=True);node.image.pack()

def shell(name,cx,low,high,mat,radius):
 old=bpy.data.objects[name];bpy.data.objects.remove(old,do_unlink=True)
 vs=[];fs=[];uvfaces=[];na=128
 heights=[low,high] if cx==BX else sorted(set([low,high]+[z for z in zs if low<z<high]))
 nz=len(heights)-1
 for off in [.0020,.0011]:
  for z in heights:
   rx,ry=radius(z)
   for i in range(na):
    a=-math.pi+math.tau*i/na;vs.append((cx+(rx+off)*math.sin(a),-(ry+off)*math.cos(a),z))
 side=(nz+1)*na
 def face(ids,uv):fs.append(ids);uvfaces.append(uv)
 for j in range(nz):
  for i in range(na):
   k=(i+1)%na;a=j*na+i;b=j*na+k;c=(j+1)*na+k;d=(j+1)*na+i
   v0=(heights[j]-low)/(high-low);v1=(heights[j+1]-low)/(high-low)
   uv=[(i/na,v0),((i+1)/na,v0),((i+1)/na,v1),(i/na,v1)]
   face((a,b,c,d),uv);face((d+side,c+side,b+side,a+side),list(reversed(uv)))
 for j in [0,nz]:
  for i in range(na):
   k=(i+1)%na;a=j*na+i;b=j*na+k
   face((b,a,a+side,b+side) if j==0 else (a,b,b+side,a+side),[(i/na,j/nz)]*4)
 ob=mesh(name,vs,fs,mat,'Label');volume=fix(ob)
 # The source face order is unchanged by normal correction; preserve UV seams.
 uv=ob.data.uv_layers.new(name='Decorative wrap UV')
 for f,coords in zip(ob.data.polygons,uvfaces):
  for li,coord in zip(f.loop_indices,coords):uv.data[li].uv=coord
 ob.visible_shadow=True;ob['nominalThickness']=.0009;ob['materialRole']='thin physical decorative surface, not paper'
 return ob,volume
label_bottle,vol_bottle=shell('Bottle copper bronze decorative wrap',BX,.69,2.61,bronze,lambda z:(.510,.510))
label_tube,vol_tube=shell('Tube rose bronze decorative wrap',TX,.50,1.87,rose,lambda z:(rx_at(z),ry_at(z)))

def boolean_cut(ob,cutter,label):
 bpy.ops.object.select_all(action='DESELECT');ob.select_set(True);bpy.context.view_layer.objects.active=ob
 mod=ob.modifiers.new(label,'BOOLEAN');mod.operation='DIFFERENCE';mod.solver='EXACT';mod.object=cutter
 bpy.ops.object.modifier_apply(modifier=mod.name);bpy.data.objects.remove(cutter,do_unlink=True)
 good=next(m for m in ob.data.materials if m);ob.data.materials.clear();ob.data.materials.append(good)
 for f in ob.data.polygons:f.material_index=0
 return fix(ob)
def bore(ob,r,z0,z1,name,cx=BX):
 bpy.ops.mesh.primitive_cylinder_add(vertices=96,radius=r,depth=z1-z0,location=(cx,0,(z0+z1)/2))
 return boolean_cut(ob,bpy.context.object,name)
collar=bpy.data.objects['Pump | broad ivory shoulder collar']
stem=bpy.data.objects['Pump | actuator barrel and stem'];connector=bpy.data.objects['Pump | internal connector']
profile=[(2.59,.510),(2.620,.489),(2.640,.429),(2.650,.239),(2.670,.187),(2.774,.187)]
cv=[];cf=[];segments=96
for z,r in profile:
 for i in range(segments):
  a=math.tau*i/segments;cv.append((BX+r*math.cos(a),r*math.sin(a),z))
for j in range(len(profile)-1):
 for i in range(segments):a=j*segments+i;b=j*segments+(i+1)%segments;cf.append((a,b,b+segments,a+segments))
cf.extend([tuple(range(segments-1,-1,-1)),tuple((len(profile)-1)*segments+i for i in range(segments))])
cavity=mesh('Temporary neck-shaped cavity',cv,cf,ivory,'Pump');fix(cavity)
boolean_cut(collar,cavity,'Shoulder-conforming neck receiving cup')
bore(collar,.031,2.59,2.80,'Through pump center passage')
bore(stem,.187,2.74,2.798,'Bottle lip receiving space')
bore(stem,.031,2.74,3.20,'Through actuator stem passage')
bore(connector,.030,2.50,2.74,'Through connector fluid bore')
bore(connector,.0425,2.50,2.612,'Hollow dip-tube receiving socket')
upper=bpy.data.objects['Tube cap | closure sleeve'];bore(upper,.060,.10,.35,'Flip-cap dispensing aperture',TX)
# Apply the existing approved one-level pump smoothing before opening its underside outlet.
beak=bpy.data.objects['Pump | wide flattened beak actuator'];bpy.context.view_layer.objects.active=beak
for mod in list(beak.modifiers):bpy.ops.object.modifier_apply(modifier=mod.name)
bpy.ops.mesh.primitive_cube_add(size=1,location=(BX-.60,0,3.220))
cutter=bpy.context.object;cutter.scale=(.034,.053,.055)
bpy.ops.object.transform_apply(location=False,rotation=False,scale=True)
mod=cutter.modifiers.new('Rounded dispensing outlet','BEVEL');mod.width=.004;mod.segments=4
bpy.ops.object.modifier_apply(modifier=mod.name);boolean_cut(beak,cutter,'Real recessed underside dispensing mouth')
# Retain the sixth assembly object as a recessed back wall inside the real mouth.
outlet=bpy.data.objects['Pump | recessed dispensing outlet'];inv=outlet.matrix_world.inverted()
old_points=points(outlet);old_center=sum(old_points,Vector())/len(old_points)
for v in outlet.data.vertices:
 q=outlet.matrix_world@v.co;q=Vector((BX-.60+(q.x-old_center.x)*.68,(q.y-old_center.y)*.58,3.246+(q.z-old_center.z)*.30));v.co=inv@q
outlet.data.update();outlet['role']='back wall recessed inside actual outlet aperture'

# Give non-artwork ivory meshes stable UVs so exported grain reaches every component.
for ob in [o for n in NAMES for o in roots[n].children_recursive if o.type=='MESH']:
 if ivory not in ob.data.materials[:]:continue
 while ob.data.uv_layers:ob.data.uv_layers.remove(ob.data.uv_layers[0])
 uv=ob.data.uv_layers.new(name='Molded polymer grain UV')
 for f in ob.data.polygons:
  axis=max(range(3),key=lambda a:abs(f.normal[a]));axes=[a for a in range(3) if a!=axis]
  for li in f.loop_indices:
   q=ob.matrix_world@ob.data.vertices[ob.data.loops[li].vertex_index].co
   uv.data[li].uv=(q[axes[0]]*1.7,q[axes[1]]*1.7)

def image_array(name,rgb,noncolor=True):
 h,w=rgb.shape[:2];rgba=np.ones((h,w,4),dtype=np.float32);rgba[:,:,:3]=rgb
 image=bpy.data.images.new(name,width=w,height=h,alpha=False,float_buffer=False)
 image.colorspace_settings.name='Non-Color' if noncolor else 'sRGB'
 image.pixels.foreach_set(rgba.ravel());image.filepath_raw=str(HERE/f'{name}.png');image.file_format='PNG';image.save();image.pack()
 return image
def grain_maps(prefix,size,rough,amplitude,normal_scale,seed):
 rng=np.random.default_rng(seed);raw=rng.normal(size=(size,size))
 fy=np.fft.fftfreq(size)[:,None];fx=np.fft.rfftfreq(size)[None,:]
 filtered=np.fft.irfft2(np.fft.rfft2(raw)*np.exp(-(fx*fx+fy*fy)*20),s=(size,size))
 filtered/=filtered.std();height=np.clip(filtered,-2.4,2.4)
 gx=(np.roll(height,-1,axis=1)-np.roll(height,1,axis=1))*.5*normal_scale
 gy=(np.roll(height,-1,axis=0)-np.roll(height,1,axis=0))*.5*normal_scale
 normals=np.stack((-gx,-gy,np.ones_like(gx)),axis=-1);normals/=np.linalg.norm(normals,axis=-1,keepdims=True)
 roughmap=np.repeat(np.clip(rough+height*amplitude,.05,.95)[:,:,None],3,axis=2)
 return image_array(prefix+'-roughness',roughmap),image_array(prefix+'-normal',normals*.5+.5)
texture_records=[]
def setup_surface(mat,prefix,size,rough,metal,coat,amplitude,normal_scale,seed,base=None):
 nodes=mat.node_tree.nodes;links=mat.node_tree.links;p=nodes.get('Principled BSDF')
 for node in list(nodes):
  if node.type not in {'BSDF_PRINCIPLED','OUTPUT_MATERIAL'}:nodes.remove(node)
 for key in ['Base Color','Roughness','Metallic','Normal']:
  for link in list(p.inputs[key].links):links.remove(link)
 p.inputs['Roughness'].default_value=rough;p.inputs['Metallic'].default_value=metal
 p.inputs['Coat Weight'].default_value=coat;p.inputs['Alpha'].default_value=1
 r,n=grain_maps(prefix,size,rough,amplitude,normal_scale,seed)
 rn=nodes.new('ShaderNodeTexImage');rn.name='Exported roughness texture';rn.image=r
 links.new(rn.outputs['Color'],p.inputs['Roughness'])
 nn=nodes.new('ShaderNodeTexImage');nn.name='Exported tangent grain';nn.image=n
 normal=nodes.new('ShaderNodeNormalMap');normal.inputs['Strength'].default_value=.22
 links.new(nn.outputs['Color'],normal.inputs['Color']);links.new(normal.outputs['Normal'],p.inputs['Normal'])
 if base is not None:
  image=image_array(prefix+'-color',base,False);bn=nodes.new('ShaderNodeTexImage');bn.image=image
  links.new(bn.outputs['Color'],p.inputs['Base Color'])
 texture_records.append({'material':mat.name,'size':size,'roughnessCenter':rough,'metallic':metal,'normalEncodedAmplitude':normal_scale,'normalMapStrength':.22,'colorTexture':base is not None})
 return p
setup_surface(ivory,'ivory-grain',256,.30,0,.10,.013,.045,851)
setup_surface(bronze,'bronze-grain',512,.32,.68,.12,.025,.070,852)
size=1024;v,u=np.mgrid[0:1:complex(size),0:1:complex(size)]
# Low-contrast, slanted abstract brush movement from the approved poster. No baked lighting.
phase=u*3.1+v*.54+.10*np.sin(v*5.3)+.045*np.sin(u*19+v*8)
brush=(.5+.5*np.sin(phase*math.tau))**8
fine=np.sin((u*41+v*6.8+.07*np.sin(v*11))*math.tau)
pattern=(brush-.28)*.070+fine*.005*brush
base=np.clip(np.array([170,125,109],dtype=float)[None,None,:]/255+pattern[:,:,None]*np.array([1,.83,.77]),0,1)
setup_surface(rose,'rose-brush',512,.43,.18,.08,.018,.045,853,base)
for name in ['LogoInk','NameInk']:
 for o in roots[name].children_recursive:
  if o.type=='MESH':o.visible_shadow=False;o['materialRole']='transparent original ink, no rectangular shadow'

# Prove protected components have their exact original world vertices.
bpy.context.view_layer.update();errors={}
for name,oldpoints in preserved.items():
 current=points(bpy.data.objects[name]);assert len(current)==len(oldpoints)
 err=max((a-b).length for a,b in zip(current,oldpoints));assert err==0,(name,err);errors[name]=err
config=json.loads((OLD/'review-product.json').read_text());config['file']='poster-085-v3.glb'
config['review']['appearance']['labelShadows']=True
config['review']['appearance']['studio']={'background':'#75685f','ink':'#fff5e7'}
for part in config['parts']:
 if part['key']=='label':part['detail']=['铜棕与玫瑰棕薄实体装饰面，保留细砂与刷纹并独立投影；非纸标。','Thin physical bronze and rose decorative surfaces retain their grain and brush pattern, casting their own shadows; not paper labels.']
(HERE/'review-product.json').write_text(json.dumps(config,ensure_ascii=False,indent=2)+'\n')
rest={name:o.location.copy() for name,o in roots.items()}
for frame,t in [(1,0),(31,.5),(61,1)]:
 for part in config['parts']:
  key=part['key'];o=roots[part['node']];x,y,z=config['review']['explosion']['offsets'][key]
  o.location=rest[o.name]+Vector((x,-z,y))*t
  scale=1+(config['review']['explosion']['scales'].get(key,1)-1)*t;o.scale=(scale,scale,scale)
  o.keyframe_insert(data_path='location',frame=frame);o.keyframe_insert(data_path='scale',frame=frame)
scene.frame_set(1);bpy.context.view_layer.update();bpy.ops.object.select_all(action='DESELECT')
objects=[o for root in roots.values() for o in root.children_recursive if o.type=='MESH']
for root in roots.values():
 root.select_set(True)
 for child in root.children_recursive:child.select_set(True)
assert len(objects)==18,len(objects)
bpy.ops.export_scene.gltf(filepath=str(GLB),export_format='GLB',use_selection=True,export_yup=True,
 export_extras=True,export_animations=False,export_apply=True)
bpy.ops.file.pack_all();bpy.ops.wm.save_as_mainfile(filepath=str(HERE/'poster-085-v3.blend'),compress=True)
report={'product':'poster-085','version':'v3','roots':NAMES,'meshObjects':len(objects),
 'groups':{n:len([o for o in roots[n].children_recursive if o.type=='MESH']) for n in NAMES},
 'preservedWorldVertexErrors':errors,'originalSealRidgesPreserved':72,'mergedSealVertexCount':seal_vertices,
 'labelVolumes':[vol_bottle,vol_tube],'labelThickness':.0009,'adaptiveTubeRows':len(zs),'maximumSampledProfileError':maximum_profile_error,
 'originalArtwork':artwork,'materialTextures':texture_records,
 'sourceFrames':[1,31,61],'containsFormula':False,'paperLabel':False,'glbBytes':GLB.stat().st_size,
 'glbSha256':hashlib.sha256(GLB.read_bytes()).hexdigest(),'configSha256':hashlib.sha256((HERE/'review-product.json').read_bytes()).hexdigest(),
 'visualReviewPending':True,'productionRegistered':False}
(HERE/'build-verification.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
ops={'phase':'initial model build','argv':['/Applications/Blender.app/Contents/MacOS/Blender','--background','--python-exit-code','1','--python',str(HERE/'build_v3.py')],
 'sourceRead':str(OLD/'poster-085-v2.blend'),'outputGlb':str(GLB),'outputSource':str(HERE/'poster-085-v3.blend'),
 'scriptSha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'formalRegistryChanged':False}
(HERE/'operations-build.json').write_text(json.dumps(ops,ensure_ascii=False,indent=2)+'\n')
print('085_V3_READY',json.dumps(report))
