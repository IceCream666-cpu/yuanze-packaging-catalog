"""Tea Tree Shampoo 065: separate empty pump bottle and sealed refill pouch."""
import sys,math,bpy,json
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
from build_micro_cream import configure,mat,mesh,lathe,artwork,layer,part,finish

POUCH_X=1.48
POUCH_Y=.19
HALF_WIDTHS=[(0,.70),(.035,.76),(.10,.78),(.40,.79),(1.60,.84),(2.42,.89),(2.59,.94),(2.68,.92),(2.745,.85),(2.76,.79)]

def pouch_width(z):
 for (a,x),(b,y) in zip(HALF_WIDTHS,HALF_WIDTHS[1:]):
  if z<=b:return x+(y-x)*max(0,(z-a)/(b-a))
 return HALF_WIDTHS[-1][1]

def pouch_front(x,z,back=False):
 u=max(-1,min(1,x/pouch_width(z)));v=max(0,min(1,z/2.76))
 bulge=.105*max(0,1-u*u)**.7*math.sin(math.pi*v)**.55
 folds=.009*math.sin(u*22+v*9)*abs(u)**3*math.sin(math.pi*v)
 # Near-flat sealed edges and a gently shaped empty cavity; no liquid surface or bubbles.
 return POUCH_Y+(1 if back else -1)*(.003+bulge+folds)

def film_surface(name,back,material):
 nx,ny=64,96;vs=[];fs=[]
 for side in [0,1]:
  for j in range(ny+1):
   z=2.76*j/ny;half=pouch_width(z)
   for i in range(nx+1):
    x=(i/nx*2-1)*half;y=pouch_front(x,z,back)+(1 if not back else -1)*.0025*side;vs.append((x+POUCH_X,y,z+.035))
 count=(nx+1)*(ny+1)
 for side in [0,1]:
  for j in range(ny):
   for i in range(nx):
    a=side*count+j*(nx+1)+i;face=(a,a+1,a+nx+2,a+nx+1);fs.append(tuple(reversed(face)) if side else face)
 boundary=list(range(nx+1))+[j*(nx+1)+nx for j in range(1,ny+1)]+[ny*(nx+1)+i for i in range(nx-1,-1,-1)]+[j*(nx+1) for j in range(ny-1,0,-1)]
 for a,b in zip(boundary,boundary[1:]+boundary[:1]):fs.append((a,b,b+count,a+count))
 return mesh(name,vs,fs,material,'RefillPouch',True)

def build():
 configure('poster-065')
 glass=mat('Tea Tree neutral clear empty bottle','#ffffff',.027,trans=1)
 navy=mat('Tea Tree glossy navy pump','#071b3c',.21);navy.node_tree.nodes.get('Principled BSDF').inputs['Coat Weight'].default_value=.25
 inside=mat('Tea Tree ivory pump mechanism','#e8e3d5',.31)
 clear_tube=mat('Tea Tree clear plastic dip tube','#ffffff',.06,trans=1)
 bag=mat('Tea Tree translucent refill film','#fff7e8',.18,trans=.92)
 seam=mat('Tea Tree sealed ivory pouch edges','#e8d9bf',.35,trans=.45)
 recess=mat('Tea Tree dark nozzle opening','#020a18',.5)
 lathe('Hollow round shampoo bottle with sloping shoulder',[(0,0),(0,.33),(.008,.39),(.025,.434),(.060,.466),(.11,.488),(.20,.50),(1.25,.50),(1.38,.49),(1.50,.464),(1.61,.418),(1.72,.350),(1.82,.272),(1.90,.205),(1.955,.171),(1.990,.163),(2.040,.163),(2.040,.127),(1.985,.127),(1.94,.140),(1.87,.178),(1.79,.244),(1.69,.323),(1.58,.385),(1.47,.432),(1.35,.456),(1.23,.466),(.18,.466),(.12,.444),(.085,.404),(.070,.350),(.070,0)],glass,'Body')
 lathe('Navy smooth pump screw collar',[(2.010,.174),(2.010,.195),(2.024,.205),(2.235,.205),(2.250,.195),(2.250,.091),(2.228,.091),(2.228,.174),(2.010,.174)],navy,'Closure')
 lathe('Navy raised collar step',[(2.238,.096),(2.238,.161),(2.254,.164),(2.300,.164),(2.309,.153),(2.309,.096),(2.238,.096)],navy,'Closure')
 lathe('Visible navy connecting pump stem',[(2.286,.062),(2.286,.082),(2.304,.087),(2.487,.087),(2.501,.080),(2.501,.062),(2.286,.062)],navy,'PumpStem')
 lathe('Ivory internal pump chamber',[(1.40,.026),(1.40,.060),(1.44,.078),(1.73,.078),(1.75,.092),(1.82,.092),(1.84,.065),(2.285,.065),(2.285,.026),(1.40,.026)],inside,'PumpStem')
 dip=lathe('Open hollow dip tube',[(.090,.026),(.090,.035),(1.34,.035),(1.39,.024),(1.48,.024),(1.48,.018),(1.39,.018),(1.34,.026),(.090,.026)],clear_tube,'PumpStem',96)
 # Recenter the tapered tip before it enters the original narrow pump chamber.
 for vertex in dip.data.vertices:vertex.co.x+=.13*max(0,1-vertex.co.z/1.39)
 lathe('Navy actuator hub',[(2.470,0),(2.470,.105),(2.481,.145),(2.625,.145),(2.640,.132),(2.640,0)],navy,'Actuator')
 sections=[(-.40,2.570,.046,.025),(-.370,2.588,.050,.025),(-.28,2.624,.062,.029),(-.14,2.649,.078,.030),(0,2.656,.108,.031),(.15,2.649,.092,.030),(.20,2.641,.045,.026)]
 ns=32;vs=[];fs=[]
 def section(x,z,w,h):return [(x,w*math.copysign(abs(math.cos(i*math.tau/ns))**.6,math.cos(i*math.tau/ns)),z+h*math.copysign(abs(math.sin(i*math.tau/ns))**.6,math.sin(i*math.tau/ns))) for i in range(ns)]
 for row in sections:vs.extend(section(*row))
 for j in range(len(sections)-1):
  for i in range(ns):a=j*ns+i;b=j*ns+(i+1)%ns;fs.append((a,b,b+ns,a+ns))
 fs.append(tuple((len(sections)-1)*ns+i for i in range(ns)))
 start=len(vs);vs.extend(section(-.40,2.570,.027,.012));end=len(vs);vs.extend(section(-.370,2.588,.027,.012))
 for i in range(ns):j=(i+1)%ns;fs.extend([(i,start+i,start+j,j),(start+i,end+i,end+j,start+j)])
 fs.append(tuple(reversed([end+i for i in range(ns)])))
 mesh('Long curved navy dispensing head',vs,fs,navy,'Actuator',True)
 mesh('Dark recessed nozzle opening',section(-.3699,2.588,.026,.011),[tuple(reversed(range(ns)))],recess,'Actuator')
 film_surface('Front thin refill pouch skin',False,bag);film_surface('Rear thin refill pouch skin',True,bag)
 # Thin welded perimeter follows the actual taper and soft top corners, not a cardboard rectangle.
 for side in [-1,1]:
  vs=[];fs=[]
  for j in range(97):
   z=2.76*j/96;half=pouch_width(z)
   vs.extend([(POUCH_X+side*half,POUCH_Y-.004,z+.035),(POUCH_X+side*(half-.045),pouch_front(side*(half-.045),z)-.0005,z+.035)])
  for j in range(96):a=j*2;fs.append((a,a+1,a+3,a+2))
  mesh(('Left' if side<0 else 'Right')+' heat sealed pouch margin',vs,fs,seam,'RefillPouch')
 for z0,z1,name in [(0,.060,'Bottom gusset seal'),(2.68,2.76,'Wide top heat seal')]:
  nx,ny=48,6;vs=[];fs=[]
  for j in range(ny+1):
   z=z0+(z1-z0)*j/ny
   for i in range(nx+1):
    x=(i/nx*2-1)*pouch_width(z);vs.append((POUCH_X+x,pouch_front(x,z)-.0007,z+.035))
  for j in range(ny):
   for i in range(nx):a=j*(nx+1)+i;fs.append((a,a+1,a+nx+2,a+nx+1))
  mesh(name,vs,fs,seam,'RefillPouch')
 artwork(680,870,(117.5,110,445,200),[('—',350,1,0,'Arial'),('TEA TREE',490,70,5,'Helvetica Neue,Arial,sans-serif'),('SHAMPOO',565,68,4,'Helvetica Neue,Arial,sans-serif'),('750 mL',785,54,3,'Helvetica Neue,Arial,sans-serif')],background='#12243e',ink='#fff1d6')
 front=lambda x,z:-math.sqrt(.5*.5-x*x)
 layer('Blank navy bottle paper label','PaperLabel','label',.68,.34,1.21,front,rough=.65,offset=.0015)
 layer('Complete Tea Tree bottle lettering','LogoPrint','print',.68,.34,1.21,front,offset=.0023)
 artwork(910,1080,(172.5,110,565,245),[('—',450,1,0,'Arial'),('TEA TREE',620,82,6,'Helvetica Neue,Arial,sans-serif'),('SHAMPOO',714,80,4.5,'Helvetica Neue,Arial,sans-serif'),('REFILL',940,62,7,'Helvetica Neue,Arial,sans-serif')],background='#12243e',ink='#fff1d6',name='refill-print',label_name='refill-label')
 for name,parent,file,offset in [('Blank navy refill pouch label','PaperLabel','refill-label',.0015),('Complete Tea Tree refill lettering','LogoPrint','refill-print',.0023)]:
  o=layer(name,parent,file,.91,.46,1.54,lambda x,z:pouch_front(x,z-.035),offset=offset);o.location.x=POUCH_X
 parts=[part('closure','PumpAssembly','完整深蓝泵头与吸管','Complete navy pump and dip tube','长嘴按头、旋盖、泵芯与透明长吸管保持连接，整体上提。','The spout, collar, pump chamber and clear dip tube lift as one unit.'),part('jar','Body','透明洗发水瓶','Clear bottle','圆肩空瓶与加厚圆底。','Empty round-shouldered bottle with a thick circular base.'),part('refill','RefillPouch','透明补充袋','Refill pouch','独立薄膜前后壁、收边和封口。','Separate thin front and rear films with sealed edges.'),part('label','PaperLabel','双款深蓝标签','Navy labels','瓶标与补充袋标都保持无字。','Bottle and refill labels both remain blank.'),part('print','LogoPrint','两套完整文字','Lettering','瓶身750 mL与袋上REFILL分别完整展开。','Complete bottle 750 mL and pouch REFILL lettering move out together.')]
 parts[0]['short']=['泵头总成','Pump']
 finish({'Body':0,'Closure':2.02,'PumpStem':2.28,'Actuator':2.50,'RefillPouch':1.4,'PaperLabel':.90,'LogoPrint':.90},parts,{'glass':True,'frosted':False,'pipette':False,'clearLabel':False,'metal':False,'studio':{'background':'#626d7c','ink':'#fff4dd'}},{'offsets':{'closure':[0,2.45,0],'refill':[1.15,.05,0],'label':[-2.55,.65,.65],'print':[-4.8,-1.6,1.65]},'scales':{'label':1.15,'print':1.95},'camera':{'centerY':[1.45,1.6],'height':[4.3,8.1],'width':[4.7,11.8],'centerX':[.8,-.6]}},{'bottleHeightToDiameter':2.687,'refillHeightToBottleDiameter':2.76,'refillMaxWidthToBottleDiameter':1.88,'pouchFilmThicknessToBottleDiameter':.0025,'printIncludes':['liaose','TEA TREE','SHAMPOO','750 mL','liaose','TEA TREE','SHAMPOO','REFILL','two fine rules'],'hiddenStructure':'Refill pouch is retained as packaging; no liquid, bubbles, herbs or platform. A shallow preformed empty pouch and pump internals are illustrative.','generator':'build_tea_tree_shampoo.py'})
 # Retain fitted child transforms while the complete pump moves as one group.
 out=Path(__file__).resolve().parent/'poster-065';info=json.loads((out/'model-info.json').read_text());bounds=info['componentBoundsBlenderXYZ']
 children=['Closure','PumpStem','Actuator'];assembly=bpy.data.objects.new('PumpAssembly',None);bpy.context.collection.objects.link(assembly)
 for child in children:bpy.data.objects[child].parent=assembly
 bounds['PumpAssembly']={'min':[min(bounds[child]['min'][i] for child in children) for i in range(3)],'max':[max(bounds[child]['max'][i] for child in children) for i in range(3)]}
 info.update(components=['PumpAssembly','Body','RefillPouch','PaperLabel','LogoPrint'],assemblyChildren={'PumpAssembly':children},completePumpLift=2.45,revision='complete-pump-clear-tube-review-20261030',dipTube={'mesh':'Open hollow dip tube','outerDiameterToBody':.07,'innerDiameterToBody':.052,'bottomToBody':.09,'topToBody':1.48,'innerFloorToBody':.07,'tipOuterDiameterToBody':.048,'tipInnerDiameterToBody':.036,'centredTipStartsAt':1.39,'illustrativeDimensions':True})
 bpy.context.view_layer.update();bpy.ops.object.select_all(action='SELECT')
 bpy.ops.export_scene.gltf(filepath=str(out.parents[2]/'packaging-assets/poster-065.glb'),export_format='GLB',use_selection=True,export_apply=True,export_yup=True,export_extras=True)
 bpy.ops.wm.save_as_mainfile(filepath=str(out/'poster-065.blend'));(out/'model-info.json').write_text(json.dumps(info,indent=2)+'\n')

if __name__=='__main__':build()
