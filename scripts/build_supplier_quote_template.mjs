import fs from 'node:fs/promises';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
import {createRequire} from 'node:module';
const root=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'..');
const out=path.join(root,'outputs/supplier-quote-simple-20261014');
const qa=path.join(root,'work/supplier-quote-simple-20261014');
await fs.mkdir(out,{recursive:true});await fs.mkdir(qa,{recursive:true});
try {await fs.symlink('/Users/icecream/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules',path.join(qa,'node_modules'));}catch(e){if(e.code!=='EEXIST')throw e;}
const req=createRequire(path.join(qa,'package.json'));
const {Workbook,SpreadsheetFile}=await import(req.resolve('@oai/artifact-tool'));
const wb=Workbook.create(),s=wb.worksheets.add('供应商产品报价');
const teal='#164B47',input='#FFF7E5',line='#D9E3DD';
s.showGridLines=false;
s.getRange('A1:G275').format={font:{name:'Arial',size:11,color:'#243D39'},rowHeight:27,verticalAlignment:'center',wrapText:true};
[20,16,17,20,17,16,28].forEach((w,i)=>s.getRange(`${String.fromCharCode(65+i)}1:${String.fromCharCode(65+i)}275`).format.columnWidth=w);
function cell(a,v){s.getRange(a).values=[[v]];}
function merged(a,v,fill){const r=s.getRange(a);r.merge();r.values=[[v]];if(fill)r.format.fill=fill;return r;}
function blank(a){s.getRange(a).format.fill=input;}
merged('A1:G1','源泽包材库 · 供应商产品报价').format.font={name:'Arial',size:16,bold:true,color:teal};
cell('A3','供应商');merged('B3:C3','',input);cell('D3','联系人／电话');merged('E3:G3','',input);
cell('A4','报价日期');merged('B4:C4','',input);cell('D4','报价有效期至');merged('E4:G4','',input);
s.getRange('B4').setNumberFormat('yyyy-mm-dd');s.getRange('E4').setNumberFormat('yyyy-mm-dd');
cell('A5','价格口径');merged('B5:C5','',input);cell('D5','运费口径');merged('E5:G5','',input);
s.getRange('B5').dataValidation={rule:{type:'list',values:['含税','不含税']}};
s.getRange('E5').dataValidation={rule:{type:'list',values:['含运（备注收货地区）','不含运']}};
merged('A6:G6','每款贴一张图，填规格和报价。金额统一为人民币；浅黄色填写，未知留空，确认免费填0。');
s.getRange('A6:G6').format.font.color='#637872';
const items=['裸瓶','丝印','烫金／烫银','注塑色','喷涂','蒙砂','电镀瓶身','电镀盖子','其他工艺'];
for(let i=0;i<10;i++){
 const r=8+i*27;
 merged(`A${r}:G${r}`,`产品 ${String(i+1).padStart(2,'0')}　同款不同规格请分别填写`,teal).format.font={name:'Arial',size:12,bold:true,color:'#FFFFFF'};
 const photo=merged(`A${r+1}:C${r+7}`,'在此插入产品图片\n\n建议一图一款，保留规格区别','#F0F4F1');
 photo.format.horizontalAlignment='center';photo.format.borders={preset:'outside',style:'thin',color:line};
 for(const [delta,label] of [[1,'产品名称／型号'],[3,'材质'],[5,'规格（如250mL）'],[7,'裸瓶价含哪些配件']]){
  cell(`D${r+delta}`,label);merged(`E${r+delta}:G${r+delta}`,'',input);
 }
 merged(`A${r+8}:G${r+8}`,'先填下方3个数量档（由小到大），再填对应单价。不做的工艺在备注写“不做”；低于该工艺MOQ的价格留空。');
 s.getRange(`A${r+8}:G${r+8}`).format.rowHeight=34;
 s.getRange(`A${r+9}:G${r+9}`).values=[['项目','最低起订量\n（个）','数量档一\n单价','数量档二\n单价','数量档三\n单价','计费单位','备注／适用条件']];
 s.getRange(`A${r+9}:G${r+9}`).format={fill:'#E5EDE7',font:{name:'Arial',size:11,bold:true,color:teal},rowHeight:40,horizontalAlignment:'center'};
 merged(`A${r+10}:B${r+10}`,'订购数量达到');blank(`C${r+10}:E${r+10}`);
 merged(`F${r+10}:G${r+10}`,'个（默认每款／每规格／每色）');
 s.getRange(`C${r+10}:E${r+10}`).setNumberFormat('#,##0');
 s.getRange(`C${r+10}:E${r+10}`).dataValidation={rule:{type:'whole',operator:'greaterThanOrEqual',formula1:1}};
 for(const [j,name] of items.entries()){
  const n=r+11+j;cell(`A${n}`,name);blank(`B${n}:G${n}`);
  s.getRange(`B${n}`).setNumberFormat('#,##0');s.getRange(`C${n}:E${n}`).setNumberFormat('0.0000');
  s.getRange(`B${n}`).dataValidation={rule:{type:'whole',operator:'greaterThanOrEqual',formula1:1}};
  s.getRange(`C${n}:E${n}`).dataValidation={rule:{type:'decimal',operator:'greaterThanOrEqual',formula1:0}};
  cell(`F${n}`,j===0?'元/个':'');
  s.getRange(`F${n}`).dataValidation={rule:{type:'list',values:['元/个','元/个/色','元/批']}};
  s.getRange(`A${n}:G${n}`).format.borders={bottom:{style:'thin',color:line}};
 }
 s.getRange(`B${r+11}:G${r+19}`).format.borders={preset:'all',style:'thin',color:line};
 s.getRange(`C${r+10}:E${r+10}`).format.borders={preset:'all',style:'thin',color:'#A9BEB0'};
 merged(`A${r+20}:B${r+20}`,'制版／开机等额外费用');merged(`C${r+20}:G${r+20}`,'',input);
 cell(`A${r+21}`,'裸瓶货期（天）');merged(`B${r+21}:C${r+21}`,'',input);cell(`D${r+21}`,'加工后总货期（天）');merged(`E${r+21}:G${r+21}`,'',input);
 merged(`A${r+22}:B${r+22}`,'其他条件');merged(`C${r+22}:G${r+22}`,'',input);
 merged(`A${r+23}:G${r+23}`,'备注可写：工艺色数／面积／材质价差、混色起订、最低加工费、货期起算条件。额外费用注明金额和收费方式。');
 s.getRange(`A${r+23}:G${r+23}`).format={font:{name:'Arial',size:11,color:'#637872'},rowHeight:34};
}
wb.recalculate();
await fs.writeFile(path.join(qa,'inspection.ndjson'),(await wb.inspect({kind:'region',sheetId:s.name,range:'A17:G27',maxChars:2000,tableMaxRows:11,tableMaxCols:7})).ndjson);
await fs.writeFile(path.join(qa,'errors.ndjson'),(await wb.inspect({kind:'match',searchTerm:'#REF!|#DIV/0!|#VALUE!|#NAME\\?|#N/A',options:{useRegex:true,maxResults:20}})).ndjson);
for(const [name,range] of [['first','A1:G31'],['last','A251:G274']]){
 const blob=await wb.render({sheetName:s.name,range,scale:1.5,format:'png'});
 await fs.writeFile(path.join(qa,`${name}.png`),new Uint8Array(await blob.arrayBuffer()));
}
const file=path.join(out,'源泽包材库_供应商图文报价简表.xlsx');
await(await SpreadsheetFile.exportXlsx(wb)).save(file);
console.log(file);
