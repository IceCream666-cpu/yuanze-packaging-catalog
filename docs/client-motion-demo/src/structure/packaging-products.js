import collection from './collection-products.json' with {type:'json'};
const print = {key:'print', node:'LogoPrint', title:['Logo 印刷','Logo print'], short:['印刷','Print'], detail:['随滑动向外展开，合拢后回到原位。','Moves outward as you scroll; returns to its original position.']};
export const PACKAGING_PRODUCTS = {
  ...collection,
  'poster-012': {file:'beach-magic-packaging.glb', scale:30, parts:[
    {key:'cap',node:'OuterCap',title:['旋盖','Screw cap'],short:['外盖','Cap'],detail:['侧边细纹，内侧螺纹。','Fine ribs around the edge; threads inside.']},
    {key:'liner',node:'InnerLid',title:['提拉内盖','Lift-out inner lid'],short:['内盖','Inner lid'],detail:['浅盘盖沿，带一体提拉片。','A shallow rim with an integral pull tab.']},
    {key:'jar',node:'Jar',title:['透明罐身','Clear jar'],short:['罐身','Jar'],detail:['查看罐口螺纹、罐壁与罐底。','Inspect the threaded neck, walls and base.']},print,
  ]},
};
