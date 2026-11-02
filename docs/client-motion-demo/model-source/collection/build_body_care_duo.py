"""Body Care Duo: two opposed pebble pumps in an open circular presentation case."""
import math,sys,shutil,subprocess,json
from pathlib import Path
import bpy
from mathutils import Matrix,Vector
BASE=Path(__file__).resolve().parent
sys.path.insert(0,str(BASE))
from tail_model_helpers import Model,logo,svg,text,part,config,NODE
ID='poster-079'; out=BASE/ID; out.mkdir(exist_ok=True)
shutil.copyfile(BASE/'body-oil-collection/print.svg',out/'print.svg')
m=Model(ID)
def art(name,words):
    s=svg(700,330,logo(m,65,5,570,210,'#282919')+(text(350,285,words,40,9) if words else ''))
    (out/(name+'.svg')).write_text(s)
    subprocess.run([NODE,'--input-type=module','-e',"import sharp from '/Users/icecream/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/sharp/dist/index.mjs';await sharp(process.argv[1]).png().toFile(process.argv[2]);",str(out/(name+'.svg')),str(out/(name+'.png'))],check=True)
    return m.texture(name,name+'.png')
def pose(o,x,y,z,rx=0,ry=0):
    o.data.transform(Matrix.Translation((x,y,z))@Matrix.Rotation(ry,4,'Y')@Matrix.Rotation(rx,4,'X'));return o
cream=m.mat('Warm ivory satin', '#e6e2c9',.38); board=m.mat('Fine straw paperboard','#d6c89d',.67)
tray=m.mat('Warm pale moulded tray','#e4dfc5',.64); pump=m.mat('Ivory moulded pumps','#eee9cf',.31)
glass=m.mat('Frosted citron translucent wall','#d1d592',.34,.50); tube=m.mat('Translucent dip tube','#edefd6',.24,.74)
# Case parts stand face-on, as in the overhead poster view.
for name,x,profile,material in [('Lid',-1.48,[(0,0),(0,1.405),(.02,1.45),(.05,1.46),(.34,1.46),(.36,1.45),(.36,1.428),(.34,1.421),(.32,1.408),(.32,0)],board),('Tray',1.48,[(0,0),(0,1.41),(.025,1.45),(.05,1.46),(.55,1.46),(.57,1.45),(.57,1.425),(.55,1.413),(.13,1.413),(.09,1.39),(.09,0)],tray)]:
    pose(m.lathe(name+' profile',profile,material,name,160),x,.27,1.46,math.pi/2)
pose(m.sheet('Lid signature',1.04,.48,0,lambda x,z:0,art('lidmark',''),'Lid'),-1.48,-.053,1.22)
for idx,(sgn,x,body,words) in enumerate([(-1,.88,cream,'BODY CREAM'),(1,2.08,glass,'BODY WASH')]):
    g='Cream' if idx==0 else 'Wash'; rot=math.pi if sgn<0 else 0
    base=2.42 if sgn<0 else .49
    def place(o):return pose(o,x,-.11,base,ry=rot)
    def ring(z,w,d):return (z,w,d,min(w,d)*.91)
    profile=[(0,0,0,0)]+[ring(z,w,d) for z,w,d in [(.002,.28,.09),(.022,.405,.15),(.08,.485,.20),(.16,.525,.23),(.27,.545,.245),(.42,.55,.25),(1.06,.55,.25),(1.18,.541,.245),(1.29,.515,.23),(1.38,.46,.204),(1.445,.36,.155),(1.476,.22,.113),(1.48,.14,.11)]]+[(1.48,0,0,0)]
    place(m.loft(g+' pebble shell',profile,body,g))
    place(m.lathe(g+' bottle neck',[(1.45,0),(1.45,.148),(1.57,.148),(1.57,.11),(1.465,.11),(1.465,0)],body,g))
    p=g+'Pump'
    place(m.lathe(g+' collar and piston',[(1.49,0),(1.49,.183),(1.51,.19),(1.71,.19),(1.735,.18),(1.735,.095),(1.85,.095),(1.85,0)],pump,p))
    sp=m.loft(g+' rounded paddle',[(1.835,0,0,0),(1.835,.27,.082,.075),(1.851,.29,.096,.084),(1.902,.29,.096,.084),(1.916,.275,.083,.073),(1.916,0,0,0)],pump,p)
    sp.data.transform(Matrix.Translation((-.175,0,0)));place(sp)
    place(m.lathe(g+' attached hollow tube',[(.075,.03),(1.52,.03),(1.52,.021),(.075,.021),(.075,.03)],tube,p))
    pose(m.sheet(g+' direct print',.76,.36,0,lambda x,z:0,art(g+'Art',words),g+'Ink'),x,-.362,base+sgn*.69-.18)
names=[('lid','Lid','圆盒盖','Round lid'),('tray','Tray','圆盒内托','Tray'),('cream','Cream','乳霜瓶','Cream bottle'),('wash','Wash','沐浴瓶','Wash bottle'),('cp','CreamPump','身体乳完整泵组','Cream pump'),('pump','WashPump','沐浴露完整泵组','Wash pump'),('ci','CreamInk','身体乳瓶身印字','Cream print'),('print','WashInk','沐浴露瓶身印字','Wash print')]
cfg=config([part(k,n,zh,en,zh,en) for k,n,zh,en in names],{'lid':[-.95,0,.35],'tray':[0,0,-.8],'cream':[-.40,0,.6],'wash':[.51,0,.60],'cp':[-.40,-1.55,.6],'pump':[.51,1.55,.6],'ci':[-1.23,.17,1.65],'print':[1.53,-.18,1.65]},glass=False)
cfg['explosion'].update(scales={},camera={'centerX':[0,-.10],'centerY':[1.45,1.45],'height':[3.6,5.6],'width':[6.4,9.4]})
cfg['appearance']['studio']={'background':'#e9e8df','ink':'#373c2e'}
m.export(2.92,{n:0 for _,n,_,_ in names},{'name':'Body Care Duo'},cfg)
