import collection from './collection-products.json' with {type:'json'};
const print = {key:'print', node:'LogoPrint', title:['Logo 印刷','Logo print'], short:['印刷','Print'], detail:['随滑动向外展开，合拢后回到原位。','Moves outward as you scroll; returns to its original position.']};
export const PACKAGING_PRODUCTS = {
  ...collection,
  'poster-012': {file:'beach-magic-packaging.glb', scale:30, parts:[
    {key:'cap',node:'OuterCap',title:['旋盖','Screw cap'],short:['外盖','Cap'],detail:['侧边细纹，内侧螺纹。','Fine ribs around the edge; threads inside.']},
    {key:'liner',node:'InnerLid',title:['提拉内盖','Lift-out inner lid'],short:['内盖','Inner lid'],detail:['浅盘盖沿，带一体提拉片。','A shallow rim with an integral pull tab.']},
    {key:'jar',node:'Jar',title:['透明罐身','Clear jar'],short:['罐身','Jar'],detail:['查看罐口螺纹、罐壁与罐底。','Inspect the threaded neck, walls and base.']},print,
  ]},
  'poster-071': {file:'liaose-pump.glb', scale:1, parts:[
    {key:'head',node:'PumpHead',title:['长嘴泵头','Pump head'],short:['泵头','Head'],detail:['弧形长嘴与按压顶盖。','Curved spout and press pad.']},
    {key:'stem',node:'PumpStem',title:['泵杆','Pump stem'],short:['泵杆','Stem'],detail:['泵头与旋盖之间的连接层。','The connecting layer between head and closure.']},
    {key:'closure',node:'Closure',title:['细纹旋盖','Ribbed closure'],short:['旋盖','Closure'],detail:['竖向细纹与下方瓶颈套环。','Vertical ribs and a lower neck collar.']},
    {key:'jar',node:'BottleAssembly',title:['乳白瓶身','Ivory bottle'],short:['瓶身','Bottle'],detail:['长颈与宽底的雕塑轮廓。','A long neck and sculptural broad base.']},print,
  ]},
};
