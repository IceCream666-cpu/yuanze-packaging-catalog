"""Coral & Aqua 013: rounded square clear jar, smooth aqua lid, separate print."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import build_micro_cream as h

def build():
 out=h.configure('poster-013')
 glass=h.mat('Coral Aqua neutral clear glass','#ffffff',.028,trans=1)
 cap=h.mat('Smooth aqua polypropylene lid','#24b5bd',.29)
 inner=h.mat('Cream lift-out liner','#eeeee7',.38)
 h.loft('Rounded-square hollow clear jar',[
  (0,0,0,0),(0,.41,.36,.09),(.018,.474,.424,.105),(.045,.498,.448,.112),
  (.08,.5,.45,.115),(.70,.5,.45,.115),(.76,.491,.444,.14),(.80,.474,.437,.20),
  (.835,.444,.43,.32),(.855,.43,.43,.43),(.92,.43,.43,.43),
  (.92,.405,.405,.405),(.855,.405,.405,.405),(.83,.419,.407,.32),
  (.78,.445,.409,.20),(.74,.46,.413,.14),(.69,.465,.415,.11),
  (.105,.465,.415,.11),(.080,.445,.395,.10),(.070,.40,.35,.09),(.070,0,0,0)],glass,'Body')
 for z in (.87,.897):
  h.lathe('Visible glass neck thread',[(z,.429),(z+.003,.435),(z+.011,.435),(z+.014,.429),(z,.429)],glass,'Body')
 h.lathe('Smooth aqua screw cap shell',[
  (.88,.434),(.88,.446),(.89,.45),(1.058,.45),(1.07,.442),(1.075,.423),
  (1.075,0),(1.048,0),(1.048,.421),(1.041,.426),(.891,.434),(.88,.434)],cap,'Closure')
 h.lathe('Lift-out inner seal',[(.914,0),(.914,.390),(.918,.404),(.928,.406),(.934,.396),(.934,0)],inner,'InnerLid')
 tab=h.lathe('Inner seal lifting tongue',[(0,0),(0,.035),(.009,.048),(.014,.036),(.014,0)],inner,'InnerLid',48)
 tab.scale=(1.6,.65,1);tab.location=(.27,-.12,.932)
 h.artwork(800,440,(90,18,620,225),[
  ('BEACH MAGIC',305,61,3.8,'Helvetica Neue,Arial,sans-serif'),
  ('SUGAR SCRUB',375,49,4,'Helvetica Neue,Arial,sans-serif')],background='#efe5cf',ink='#28140f')
 # The coral and aqua border is printed decoration, so it travels with the lettering.
 art=out/'print.svg';s=art.read_text().replace('<text ', '<text font-weight="600" ')
 s=s[:-6]+'<path d="M14 218 V38 Q14 14 38 14 H762 Q786 14 786 38 V218" fill="none" stroke="#db6256" stroke-width="7"/><path d="M14 218 V402 Q14 426 38 426 H762 Q786 426 786 402 V218" fill="none" stroke="#23a9af" stroke-width="7"/></svg>'
 art.write_text(s)
 import subprocess
 subprocess.run(['/Users/icecream/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/bin/node','--input-type=module','-e',"import sharp from '/Users/icecream/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/sharp/dist/index.mjs';await sharp(process.argv[1],{density:144}).png().toFile(process.argv[2]);",str(art),str(out/'print.png')],check=True)
 h.layer('Blank warm cream paper label','PaperLabel','label',.80,.205,.645,lambda x,z:-.45,offset=.0014)
 h.layer('Complete logo name and two-colour border','LogoPrint','print',.80,.205,.645,lambda x,z:-.45,offset=.0022)
 parts=[
  h.part('closure','Closure','水蓝色平滑外盖','Aqua cap','平滑圆筒盖与圆形内侧开口。','Smooth cylindrical cap with a circular inner opening.'),
  h.part('liner','InnerLid','提拉内盖','Inner liner','隐藏内盖为结构示意。','The concealed lift-out liner is an illustrative structure.'),
  h.part('jar','Body','透明圆角方罐','Square jar','圆角方形罐身、圆形罐口与透明厚底。','Rounded square walls, circular neck and a clear heavy base.'),
  h.part('label','PaperLabel','米色无字标贴','Paper label','纸标与全部印刷分别展开。','Blank paper separates from the complete printed artwork.'),
  h.part('print','LogoPrint','Logo、品名与双色边线','Complete print','品牌、BEACH MAGIC、SUGAR SCRUB和双色边线一起向外展开。','The brand, BEACH MAGIC, SUGAR SCRUB and two-colour border move outward together.'),
 ]
 h.finish({'Body':0,'Closure':.88,'InnerLid':.925,'PaperLabel':.425,'LogoPrint':.425},parts,
  {'glass':True,'frosted':False,'pipette':False,'clearLabel':False,'metal':False,'studio':{'background':'#c5e5e3','ink':'#174c50'}},
  {'offsets':{'closure':[0,3.35,0],'liner':[0,1.50,0],'label':[-1.8,.08,.65],'print':[-3.65,.18,1.65]},'scales':{'label':1.15,'print':1.95},'rotations':{'closure':[-.60,-.55,-.05]},'camera':{'centerY':[1.45,3.05],'height':[4.3,7.8],'width':[4.1,9.1],'centerX':[0,-1.15]}},
  {'generator':'build_coral_aqua.py','closedHeightToWidth':1.075,'depthToWidth':.90,'capDiameterToWidth':.90,'capHeightToWidth':.195,'printIncludes':['liaose','BEACH MAGIC','SUGAR SCRUB','coral upper border','aqua lower border'],'hiddenStructure':'Empty packaging only. No scrub, spoon, bubbles, tiles or scene props. Hidden inner liner is illustrative.'})

if __name__=='__main__':build()
