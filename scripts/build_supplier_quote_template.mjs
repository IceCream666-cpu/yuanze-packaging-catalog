import fs from 'node:fs/promises';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
import {createRequire} from 'node:module';

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const out = path.join(root, 'outputs/supplier-quote-template-20261014');
const qa = path.join(root, 'work/supplier-quote-template-20261014');
const deps = process.env.CODEX_BUNDLED_NODE_MODULES || '/Users/icecream/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules';
await fs.mkdir(qa, {recursive:true});
await fs.mkdir(out, {recursive:true});
try { await fs.symlink(deps, path.join(qa, 'node_modules')); }
catch (e) { if (e.code !== 'EEXIST') throw e; }
const requireBundled = createRequire(path.join(qa, 'package.json'));
const {Workbook, SpreadsheetFile} = await import(requireBundled.resolve('@oai/artifact-tool'));
const wb = Workbook.create();
const color = {teal:'#164B47', ink:'#243D39', input:'#FFF8E6', muted:'#637872'};
const col = n => {let s='';for(;n;n=Math.floor((n-1)/26))s=String.fromCharCode(65+(n-1)%26)+s;return s;};
function init(name,title,widths,end) {
  const s=wb.worksheets.add(name); s.showGridLines=false;
  s.getRange(`A1:${col(widths.length)}${end}`).format={font:{name:'Arial',size:11,color:color.ink},verticalAlignment:'center',rowHeight:28};
  widths.forEach((w,i)=>s.getRange(`${col(i+1)}1:${col(i+1)}${end}`).format.columnWidth=w);
  s.getRange('A2').values=[[title]];s.getRange('A2').format.font={name:'Arial',size:16,bold:true,color:color.teal};
  s.getRange(`A3:${col(widths.length)}3`).format.borders={bottom:{style:'thin',color:'#A9BEB0'}};
  return s;
}
function text(s,address,value){s.getRange(address).values=[[value]];}
function list(s,range,values){s.getRange(range).dataValidation={rule:{type:'list',values}};}
function numeric(s,range,integer=false,min=0){
  s.getRange(range).setNumberFormat(integer?'#,##0':'0.0000');
  s.getRange(range).dataValidation={rule:{type:integer?'whole':'decimal',operator:'greaterThanOrEqual',formula1:min}};
}
function table(s,headers,start,count,name) {
  const last=col(headers.length),end=start+count;
  s.getRange(`A${start}:${last}${start}`).values=[headers];
  const t=s.tables.add(`A${start}:${last}${end}`,true,name);t.style='TableStyleLight1';t.showFilterButton=true;
  s.getRange(`A${start}:${last}${start}`).format={fill:color.teal,font:{name:'Arial',size:11,bold:true,color:'#FFFFFF'},wrapText:true,rowHeight:62,horizontalAlignment:'center'};
  s.getRange(`A${start+1}:${last}${end}`).format={fill:color.input,wrapText:true};
  s.freezePanes.freezeRows(start);s.freezePanes.freezeColumns(2);
  return {start,end};
}
const p=init('报价信息与产品','源泽包材库供应商阶梯报价',[24,26,24,24,22,18,18,18,28,29,30,28],116);
text(p,'A4','供应商名称 *');text(p,'D4','联系人 *');text(p,'G4','电话／微信 *');text(p,'J4','报价单号 *');
text(p,'A6','报价日期 *');text(p,'D6','有效期至 *');text(p,'G6','币种 *');text(p,'J6','默认含税口径 *');
text(p,'A8','默认税率');text(p,'D8','默认运费口径 *');text(p,'G8','收货地区／运费条件');text(p,'J8','付款条件');
for(const r of [5,7,9])for(const c of ['A','D','G','J'])p.getRange(`${c}${r}`).format.fill=color.input;
p.getRange('A7').setNumberFormat('yyyy-mm-dd');p.getRange('D7').setNumberFormat('yyyy-mm-dd');p.getRange('A9').setNumberFormat('0.0%');
list(p,'G7',['CNY','USD','EUR','其他（备注说明）']);list(p,'J7',['含税','未税']);list(p,'D9',['含运','不含运','条件含运（填写条件）']);
text(p,'A11','浅黄色为填写区，* 为必填。每份文件限一家供应商、一个币种；价格有特殊税运条件时在对应报价行说明。');
text(p,'A12','每种规格／材质／基础颜色／配件组合单独一个报价产品编号。裸瓶与工艺表必须沿用同一编号。');
text(p,'A13','已有源泽编号请保留；没有则留空。报价产品编号可自编，例如 P001。不要合并数据单元格。');
const ph=['报价产品编号 *','源泽产品编号（已有则填）','供应商型号 *','产品名称 *','材质 *','规格数值 *','规格单位 *','基础颜色 *','价格所含配件 *','价格不含配件','配件另购价／条件','其他配置说明'];
table(p,ph,16,100,'SupplierProducts');
p.getRange('A17:C116').setNumberFormat('@');numeric(p,'F17:F116');list(p,'G17:G116',['mL','g','L','kg','mm','其他']);

const b=init('裸瓶阶梯报价','裸瓶价格按订购数量分档填写',[24,24,20,24,20,20,22,23,22,24,22,28,32,36],306);
text(b,'A4','一行一个价格档。区间上下限均包含；最高档上限留空。订购量、MOQ、起止数量使用同一单位与计量口径。');
text(b,'A5','裸瓶价按产品表所列配置填写。交货期按自然日，起算条件必须说明。一次性费用只计一次，不按件叠加。');
const bh=['报价产品编号 *','报价档编号 *','数量单位 *','MOQ计算口径 *','裸瓶MOQ *','档位起始数量 *','档位截止数量','裸瓶单价 *','交货期（自然日）','交期起算条件','一次性费用金额','一次性费用项目及计收条件','税运口径差异（无则留空）','低于MOQ处理／其他条件'];
table(b,bh,6,300,'BareBottleTiers');b.getRange('A7:B306').setNumberFormat('@');
list(b,'C7:C306',['个','套','支','只','件']);list(b,'D7:D306',['每款每规格每色','每款每规格可混色','同系列可混规格','其他（备注说明）']);
for(const c of ['E','F','G'])numeric(b,`${c}7:${c}306`,true,1);
numeric(b,'H7:H306');numeric(b,'I7:I306',true);numeric(b,'K7:K306');
b.getRange('E7:H306').conditionalFormats.addCustom('AND($A7<>"",OR(AND(ISNUMBER($E7),ISNUMBER($F7),$F7<$E7),AND(ISNUMBER($G7),ISNUMBER($F7),$G7<$F7)))',{fill:'#FCE4D6'});

const g=init('工艺阶梯报价','工艺价格按材质、工艺条件与数量分档填写',[24,24,22,24,22,24,18,18,24,20,20,20,22,22,22,22,22,24,22,28,22,28,32,34],306);
text(g,'A4','每行只对应一个产品、一个工艺方案和一个价格档。材质、颜色数、面积或部位不同，价格不同则另建方案。');
text(g,'A5','组合工艺填写完整组合并注明，不能再叠加其中单项费用。单位、MOQ、费用、交期与叠加工艺条件向右填写。');
const gh=['报价产品编号 *','工艺方案编号 *','报价形式 *','工艺名称／组合 *','加工部位 *','材质／表面条件 *','色数 *','印刷面积／覆盖率','MOQ计算口径 *','工艺MOQ *','档位起始数量 *','档位截止数量','数量单位 *','工艺价格 *','价格计费单位 *','最低加工收费（每批）','一次性费用金额','费用项目及计收条件','工艺周期（自然日）','周期性质 *','交期起算条件','可叠加／互斥工艺','税运口径差异（无则留空）','不足起订／返单／其他条件'];
table(g,gh,6,300,'ProcessTiers');g.getRange('A7:B306').setNumberFormat('@');
list(g,'C7:C306',['单项工艺','组合工艺']);
list(g,'D7:D306',['丝印','烫金／烫银','注塑色','喷涂','蒙砂','电镀瓶身','电镀盖子','贴标','组合／其他（备注说明）']);
list(g,'I7:I306',['每款每规格每色','每款每规格可混色','同系列可混规格','其他（备注说明）']);
list(g,'M7:M306',['个','套','支','只','件']);
list(g,'O7:O306',['币种/数量单位','币种/数量单位/色','币种/批']);
list(g,'T7:T306',['在裸瓶交期上增加','含裸瓶的总交期','独立加工周期']);
numeric(g,'G7:G306',true,1);
for(const c of ['J','K','L'])numeric(g,`${c}7:${c}306`,true,1);
for(const c of ['N','P','Q'])numeric(g,`${c}7:${c}306`);
numeric(g,'S7:S306',true);
g.getRange('J7:L306').conditionalFormats.addCustom('AND($A7<>"",OR(AND(ISNUMBER($J7),ISNUMBER($K7),$K7<$J7),AND(ISNUMBER($L7),ISNUMBER($K7),$L7<$K7)))',{fill:'#FCE4D6'});

const e=init('填写说明与示例','填写规则与示例（示例不是实际报价）',[25,24,21,23,22,22,22,25],45);e.tabColor='#A9BEB0';
const rules=[
 ['填写顺序','先填报价信息与产品，再填裸瓶阶梯价，最后填工艺阶梯价。'],
 ['产品关联','同一编号代表同一规格、材质、基础色及配件配置。250mL与500mL使用不同编号。'],
 ['批量填写','一款多档重复产品编号，每档另起一行。空白预留100款产品、各300条裸瓶／工艺报价。'],
 ['继续增加','用Excel表格“插入表格行”扩展，并复制上一空白行的格式与验证；保留列名、编号和单位。'],
 ['MOQ与阶梯','MOQ是最低接单数量。阶梯起止数是该价格的适用数量。同条件下区间不得重叠。'],
 ['数量边界','上下限均包含：5000—9999、10000—29999、30000及以上。最高档截止数量留空。'],
 ['不同工艺MOQ','裸瓶可5000起订，丝印可能10000起订。不得把工艺MOQ直接当作裸瓶MOQ。'],
 ['合并起订','若按每色起订，不能用多个颜色总量代替。可混色／混规格须写明允许组合及各自最低数量。'],
 ['计费单位','所有金额使用首页币种。按件收费按数量计算；按色收费还需乘色数；按批收费不乘件数。'],
 ['最低加工收费','指工艺加工费最低收取额，不含另列的一次性费用。无最低收费填0，未知留空。'],
 ['费用口径','一次性费用写清制版／开机／模具等、按款还是按色计收、首单／返单及抵扣返还条件。'],
 ['组合工艺','选择组合工艺时，备注写清包含的每项。组合价与所含单项价不能重复计收。'],
 ['材质与配件','材质、表面、加工部位、色数、面积影响工艺报价。裸瓶价是否含盖／泵／内塞必须写清。'],
 ['交货期','统一自然日，并填写从付款、确认样品或确认稿件哪一天起算。各工艺交期不能直接全部相加。'],
 ['必填与空值','* 为报价所需字段。没有准确数据先留空，并在备注说明。确认免费填0，不能用0代表未知。'],
 ['特殊税运','首页填写默认税运条款。特殊行必须写清含税情况、税率、运费及目的地，不能混用口径。'],
 ['核对与回传','检查编号关联、区间重叠／空档、金额单位和条件，保存XLSX返回。示例页不作为报价导入。'],
 ['估价原则','按实际订购数量分别匹配裸瓶与工艺档位。MOQ不作为金额相加；条件未满足时先另行确认。'],
];
e.getRange('A4:B21').values=rules;
e.getRange('A4:A21').format.font={name:'Arial',size:11,bold:true,color:color.teal};
// A narrow label column plus an ordinary wide explanation column keeps guidance editable.
e.getRange('B4:B21').format.wrapText=false;
e.getRange('A4:H21').format.rowHeight=30;
text(e,'A23','裸瓶填写示例：P001，PET，250mL，白色，不含泵头。以下金额均为虚构演示。');
e.getRange('A25:H28').values=[['产品编号','报价档编号','数量单位','MOQ口径','MOQ','起始数量','截止数量','裸瓶单价'],['P001','B001','个','每款每规格每色',5000,5000,9999,1.5],['P001','B002','个','每款每规格每色',5000,10000,29999,1.4],['P001','B003','个','每款每规格每色',5000,30000,null,1.3]];
text(e,'A30','工艺填写示例：P001，瓶身丝印，PET表面，1色，面积≤20cm²。价格单位为CNY/个/色。');
e.getRange('A32:H34').values=[['产品编号','工艺方案编号','工艺','色数','工艺MOQ','起始数量','截止数量','工艺价格'],['P001','S001','丝印',1,10000,10000,29999,0.12],['P001','S001','丝印',1,10000,30000,null,0.10]];
text(e,'A36','示例中订购5000个能满足裸瓶MOQ，但不能直接按丝印档报价；需增加数量或确认不足起订方案。');
text(e,'A38','工艺表“色数”：按实际色数填整数。不分色的工艺填1，并在其他条件说明。');
text(e,'A40','未填写单价、一次性费用、最低收费或税运条件时，不应默认无费用或视为最终报价。');
text(e,'A42','本表用于供应商采集报价。回传后需核对并适配系统导入，填表不会直接修改网站价格。');
for(const r of [25,32])e.getRange(`A${r}:H${r}`).format={fill:color.teal,font:{name:'Arial',size:11,bold:true,color:'#FFFFFF'},horizontalAlignment:'center',rowHeight:38,wrapText:true};
e.getRange('E26:G28').setNumberFormat('#,##0');e.getRange('D33:G34').setNumberFormat('#,##0');
e.getRange('H26:H28').setNumberFormat('0.0000');e.getRange('H33:H34').setNumberFormat('0.0000');
for(const s of [p,b,g])s.tabColor=color.teal;
wb.recalculate();
const inspection=await wb.inspect({kind:'region',sheetId:'填写说明与示例',range:'A25:H34',maxChars:3000,tableMaxCols:8,tableMaxRows:10});
await fs.writeFile(path.join(qa,'inspection.ndjson'),inspection.ndjson);
const errors=await wb.inspect({kind:'match',searchTerm:'#REF!|#DIV/0!|#VALUE!|#NAME\\?|#N/A|#NUM!|#NULL!|#SPILL!|#CALC!',options:{useRegex:true,maxResults:30}});
await fs.writeFile(path.join(qa,'errors.ndjson'),errors.ndjson);
const previews=[['报价信息与产品','A1:L20','products'],['裸瓶阶梯报价','A1:H11','bare-left'],['裸瓶阶梯报价','I6:N11','bare-right'],['工艺阶梯报价','A1:H11','process-left'],['工艺阶梯报价','I6:P11','process-middle'],['工艺阶梯报价','Q6:X11','process-right'],['填写说明与示例','A1:H21','guide'],['填写说明与示例','A23:H42','examples']];
for(const [sheetName,range,file] of previews){const image=await wb.render({sheetName,range,scale:1.5,format:'png'});await fs.writeFile(path.join(qa,`${file}.png`),new Uint8Array(await image.arrayBuffer()));}
const dest=path.join(out,'源泽包材库_供应商阶梯报价填写模板.xlsx');
await (await SpreadsheetFile.exportXlsx(wb)).save(dest);
console.log(JSON.stringify({output:dest,previews:qa,products:100,bareTiers:300,processTiers:300}));
