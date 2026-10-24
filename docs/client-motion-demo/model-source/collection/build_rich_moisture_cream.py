"""Rich Moisture Cream 063: frosted round jar, brushed champagne lid and copper label."""
import sys,math
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
from build_micro_cream import configure,mat,lathe,artwork,layer,part,finish

def build():
 configure('poster-063')
 glass=mat('Moisture frosted neutral glass','#fffdf8',.30,trans=1)
 gold=mat('Moisture brushed champagne metal','#c6ac8d',.27,1)
 insert=mat('Moisture ivory inner liner','#f4f0e7',.38)
 lathe('Hollow frosted circular cream jar',[(0,0),(0,.43),(.008,.464),(.025,.489),(.048,.499),(.076,.5),(.403,.5),(.425,.496),(.443,.480),(.455,.435),(.468,.426),(.57,.426),(.586,.424),(.59,.414),(.59,.385),(.578,.379),(.472,.379),(.433,.436),(.411,.447),(.125,.447),(.103,.428),(.090,.401),(.090,0)],glass,'Body')
 # A real raised bead around the open neck keeps the characteristic mouth profile.
 lathe('Glass neck sealing bead',[(.505,.425),(.509,.434),(.517,.439),(.525,.434),(.529,.425),(.505,.425)],glass,'Body')
 lathe('Champagne lid with closed top and hollow skirt',[(.449,.477),(.449,.49),(.450,.503),(.465,.507),(.657,.507),(.670,.502),(.680,.491),(.680,0),(.653,0),(.653,.468),(.642,.477),(.455,.477),(.449,.477)],gold,'Closure')
 lathe('Fine lower rolled metal rim',[(.447,.498),(.451,.510),(.456,.510),(.460,.500),(.447,.498)],gold,'Closure')
 lathe('Illustrative lift-out cream seal',[(.580,0),(.580,.368),(.585,.393),(.593,.404),(.602,.395),(.607,.372),(.607,0)],insert,'InnerLid')
 tab=lathe('Inner seal low lifting tab',[(0,0),(0,.025),(.007,.032),(.013,.024),(.013,0)],insert,'InnerLid',48);tab.location=(.275,-.08,.605);tab.scale=(1.5,.7,1)
 artwork(820,250,(240,20,340,137),[('RICH MOISTURE CREAM',221,29,3,'Helvetica Neue,Arial,sans-serif')],background='#be906e',ink='#201b17')
 front=lambda x,z:-math.sqrt(.5**2-x*x)
 layer('Blank copper foil curved label','PaperLabel','label',.82,.105,.355,front,rough=.32,metal=.72,offset=.0015)
 layer('Complete Rich Moisture cream black lettering','LogoPrint','print',.82,.105,.355,front,offset=.0023)
 parts=[part('closure','Closure','香槟金外盖','Champagne lid','圆筒金属盖、卷边与中空内壁。','Cylindrical metal lid with a rolled rim and hollow skirt.'),part('liner','InnerLid','提拉内盖','Inner seal','独立提拉薄内盖，隐藏结构示意。','Separate thin lift-out seal illustrates the hidden closure.'),part('jar','Body','磨砂圆罐','Frosted jar','空心磨砂罐壁与通透罐口。','Hollow frosted jar with a clear open neck.'),part('label','PaperLabel','铜色标签','Copper label','金属质感底材保持无字。','Blank copper metallic label remains separate from the text.'),part('print','LogoPrint','完整文字','Lettering','品牌与RICH MOISTURE CREAM一起展开。','Brand and RICH MOISTURE CREAM move out together.')]
 finish({'Body':0,'Closure':.445,'InnerLid':.59,'PaperLabel':.23,'LogoPrint':.23},parts,{'glass':True,'frosted':True,'pipette':False,'clearLabel':False,'metal':True,'studio':{'background':'#e9d7c7','ink':'#3d2c23'}},{'offsets':{'closure':[0,3.25,0],'liner':[0,1.4,0],'label':[-2.05,.08,.65],'print':[-4.1,.18,1.65]},'scales':{'label':1.15,'print':1.95},'rotations':{'closure':[-.55,-.4,0]},'camera':{'centerY':[1.45,3.0],'height':[4.8,7.9],'width':[5.8,10.4],'centerX':[0,-1.2]}},{'closedHeightToDiameter':.68/1.02,'mainBodyDiameter':1,'innerFloorToDiameter':.09,'printIncludes':['liaose','RICH MOISTURE CREAM'],'hiddenStructure':'No cream contents; closed placement and inner seal illustrate assembly. Photographic open lid is represented by interactive separation.','generator':'build_rich_moisture_cream.py'})

if __name__=='__main__':build()
