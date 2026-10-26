"""066 Rose Hair Oil: original floral artwork on a thick flat clear pump bottle."""
import sys,math,base64
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
from tail_model_helpers import *
m=Model('poster-066');glass=m.mat('Rose neutral clear bottle glass','#ffffff',.024,1);gold=m.mat('Rose champagne gold pump seat','#c9a374',.22,0,1);white=m.mat('Rose satin white press head','#f5f0e9',.25);inside=m.mat('Rose hidden pump connector','#e4dfd6',.38)
# Flat broad bottle silhouette, total 1.77W, body top 1.05W; no oil solid.
outer=[(0,0,0,0),(0,.42,.16,.05),(.009,.466,.201,.055),(.026,.489,.224,.06),(.049,.5,.235,.063),(.975,.5,.235,.063),(1.005,.493,.227,.065),(1.023,.475,.208,.064),(1.038,.430,.172,.065),(1.047,.300,.130,.065),(1.055,.168,.130,.125),(1.082,.168,.168,.168)]
inner=[(1.082,.120,.120,.120),(1.052,.120,.120,.120),(1.029,.264,.100,.065),(1.017,.396,.133,.05),(.990,.459,.193,.049),(.150,.459,.193,.049),(.116,.447,.180,.049),(.100,.414,.147,.049),(.095,0,0,0)]
m.loft('Hollow flat rectangular rose bottle with thick base',outer+inner,glass,'Body')
m.lathe('Gold base ring and tapered pump housing',[(1.066,.119),(1.066,.235),(1.075,.240),(1.116,.240),(1.122,.225),(1.122,.190),(1.350,.190),(1.374,.184),(1.392,.163),(1.423,.147),(1.458,.141),(1.476,.139),(1.479,.095),(1.456,.095),(1.456,.114),(1.411,.128),(1.369,.163),(1.100,.163),(1.090,.119),(1.066,.119)],gold,'Closure')
m.lathe('Independent white connecting stem',[(1.420,.041),(1.420,.064),(1.540,.064),(1.548,.054),(1.548,.041),(1.420,.041)],inside,'PumpStem')
m.lathe('White cylindrical press head',[(1.470,.060),(1.470,.125),(1.480,.132),(1.625,.132),(1.662,.127),(1.676,.112),(1.680,0),(1.651,0),(1.651,.098),(1.480,.098),(1.480,.060),(1.470,.060)],white,'Actuator')
# Short left-facing spout visible inside the transparent closed protective cap.
m.loft('Short white left dispensing lip',[(1.615,0,0,0),(1.615,.075,.047,.022),(1.652,.075,.047,.022),(1.652,0,0,0)],white,'Actuator').location.x=-.105
m.lathe('Thin transparent closed protective cover',[(1.122,.217),(1.122,.229),(1.744,.229),(1.759,.225),(1.770,.212),(1.770,0),(1.756,0),(1.756,.205),(1.744,.215),(1.122,.215),(1.122,.217)],glass,'Overcap',192)
floral=base64.b64encode((m.out/'floral.png').read_bytes()).decode()
label=svg(810,800,'<rect x="2" y="2" width="806" height="796" rx="42" fill="#f7f3e8"/>')
printing=svg(810,800,f'<image href="data:image/png;base64,{floral}" width="810" height="800"/>'+logo(m,180,232,460,169,'#171917')+text(405,495,'ROSE HAIR OIL',29,10)+text(405,735,'120 ml',29,9))
m.artwork(label,printing)
for kind,parent,name in [('label','PaperLabel','Unprinted ivory rounded rose paper'),('print','LogoPrint','Original watercolor roses and complete black lettering')]:m.sheet(name,.81,.80,.15,lambda x,z:-.236,m.texture('Rose '+kind,kind+'.png'),parent,offset=.0015 if kind=='label' else .0025)
parts=[part('overcap','Overcap','透明罩','Cover','薄壁保护罩先行抬起。','The thin protective cover lifts first.'),part('head','Actuator','按压头','Head','白色短嘴按压件。','White press head with a short dispensing spout.'),part('stem','PumpStem','连接杆','Stem','独立泵连接层。','The pump connector separates from the head and seat.'),part('closure','Closure','金泵座','Gold seat','浅香槟金阶梯泵座。','Stepped pump seat in pale champagne gold.'),part('jar','Body','玻璃瓶','Bottle','厚底透明扁方空瓶。','Empty clear flat bottle with a thick glass base.'),part('label','PaperLabel','底纸','Paper','无字乳白底纸。','Ivory paper backing without lettering.'),part('print','LogoPrint','印花','Artwork','原玫瑰印花与全部黑字独立外展。','The original rose artwork and all black lettering move outward together.')]
c=config(parts,{'overcap':[0,4.6,0],'head':[0,2.8,0],'stem':[0,1.6,0],'closure':[0,.8,0],'label':[-1.6,.08,.65],'print':[-3.3,.18,1.65]},metal=True);c['explosion']['timing']={'overcap':[0,.65]};c['explosion']['camera'].update(centerY=[1.45,3.6],height=[4.2,8.8])
m.export(1.77,{'Body':0,'Closure':1.09,'PumpStem':1.47,'Actuator':1.54,'Overcap':1.12,'PaperLabel':.55,'LogoPrint':.55},{'closedHeightToWidth':1.77,'bodyDepthToWidth':.47,'glassHeightToWidth':1.082,'coverDiameterToWidth':.458,'labelWidthToWidth':.81,'labelHeightToWidth':.80,'printIncludes':['original watercolor rose and leaf design','liaose','ROSE HAIR OIL','120 ml'],'floralReferenceCrop':[738,468,1094,814],'generator':'build_rose_hair_oil.py','hiddenStructure':'Pump stem, wall thickness and hidden nozzle mechanism are illustrative; no liquid is modeled.'},c)
