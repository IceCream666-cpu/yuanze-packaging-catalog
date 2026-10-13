// Reproducible internal report workbook. Uses the public @oai/artifact-tool API.
import fs from 'node:fs/promises';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
import {SpreadsheetFile, Workbook} from '@oai/artifact-tool';

const root=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'..');
const data=JSON.parse(await fs.readFile(path.join(root,'docs/包材库内部汇报-20261013.json'),'utf8'));
const outDir=path.join(root,'outputs/internal-report-20261013');
const qaDir=path.join(root,'work/internal-report-20261013/workbook-qa');
await fs.mkdir(outDir,{recursive:true}); await fs.mkdir(qaDir,{recursive:true});
const wb=Workbook.create();
const overview=wb.worksheets.add('汇报总览');
const updates=wb.worksheets.add('更新与微调');
const prompts=wb.worksheets.add('提示词目的');
const tasks=wb.worksheets.add('任务时段');
const spans=wb.worksheets.add('去重时段');
const TEAL='#164B47', MIST='#E5EDE7', INK='#243D39', MUTED='#617770', LINE='#CEDBD3';
// Excel stores timezone-free wall-clock dates. Shift explicitly to the displayed
// Beijing clock before export; never allow the host timezone to shift the cells.
const wallDate=(s)=>s ? new Date(s.replace(/\+08:00$/,'Z')) : null;
const dayDate=(s)=>new Date(s.slice(0,10)+'T00:00:00Z');
function col(n){let s=''; for(let k=n;k;k=Math.floor((k-1)/26)) s=String.fromCharCode(65+(k-1)%26)+s; return s;}
function fmt(sheet, range, values){sheet.getRange(range).values=values;}
function title(sheet,text,note,lastCol){
  sheet.showGridLines=false; sheet.tabColor=TEAL;
  sheet.getRange(`A1:${lastCol}1`).merge();
  sheet.getRange('A1').values=[[text]];
  sheet.getRange(`A1:${lastCol}1`).format={font:{name:'Arial',size:16,bold:true,color:TEAL},rowHeight:32};
  sheet.getRange(`A2:${lastCol}3`).merge();sheet.getRange('A2').values=[[note]];
  sheet.getRange(`A2:${lastCol}3`).format={font:{name:'Arial',size:10,color:MUTED},wrapText:true,verticalAlignment:'center',rowHeight:25};
}
function table(sheet,headers,rows,widths,name,start=5){
  const end=start+rows.length, last=col(headers.length);
  fmt(sheet,`A${start}:${last}${end}`,[headers,...rows]);
  sheet.getRange(`A${start}:${last}${end}`).format={font:{name:'Arial',size:11,color:INK},wrapText:true,verticalAlignment:'top',rowHeight:42};
  sheet.getRange(`A${start}:${last}${start}`).format={fill:TEAL,font:{name:'Arial',size:11,color:'#FFFFFF',bold:true},verticalAlignment:'center',rowHeight:30};
  widths.forEach((w,i)=>{sheet.getRange(`${col(i+1)}${start}:${col(i+1)}${end}`).format.columnWidth=w;});
  for(let r=start+2;r<=end;r+=2) sheet.getRange(`A${r}:${last}${r}`).format.fill='#F3F6F2';
  const t=sheet.tables.add(`A${start}:${last}${end}`,true,name);t.showFilterButton=true;t.style='TableStyleLight1';
  sheet.freezePanes.freezeRows(start);sheet.freezePanes.freezeColumns(2);
  return end;
}
const byTask=new Map(data.tasks.map(x=>[x.id,x]));
const sEnd=table(spans,['段编号','工作日期','开始（北京时间）','结束（北京时间）','运行及等待分钟（去重）','计时口径'],
  data.segments.map(x=>[x.id,dayDate(x.date),wallDate(x.start),wallDate(x.end),null,x.method]),
  [10,15,25,25,20,60],'UniqueWorkWindows');
title(spans,'去重工作时段','主时长只从本表计算。可观测活动与明确工具运行／等待区间取并集，跨午夜拆分；无工具证据的长空档不计。不是人工工时。','F');
spans.getRange(`B6:B${sEnd}`).setNumberFormat('yyyy-mm-dd');
spans.getRange(`C6:D${sEnd}`).setNumberFormat('yyyy-mm-dd hh:mm:ss');
spans.getRange(`E6:E${sEnd}`).formulas=data.segments.map((x,i)=>[`=(D${i+6}-C${i+6})*1440`]);
spans.getRange(`E6:E${sEnd}`).setNumberFormat('0.00');
spans.getRange(`A6:F${sEnd}`).format.rowHeight=35;

const tEnd=table(tasks,['任务编号','任务开始（北京时间）','任务结束（北京时间）','生命周期跨度分钟','明确输入等待分钟','运行及等待分钟（未跨任务去重）','计时依据','本轮状态','涉及提示编号','本轮目的','系统duration记录分钟','无活动证据空档分钟','主会话短ID','事件行定位'],
  data.tasks.map(x=>[x.id,wallDate(x.start),wallDate(x.end),x.elapsed_minutes,x.explicit_wait_minutes,x.execution_minutes,x.basis,x.lifecycle,x.request_ids.join('、'),x.purpose,x.recorded_runtime_minutes,x.unobserved_gap_minutes,x.source.session_id.slice(0,8),`${x.source.start_line??'缺'} → ${x.source.end_line??'缺'}`]),
  [10,25,25,24,24,31,31,18,25,75,26,27,17,22],'TaskExecutionWindows');
title(tasks,'主任务执行记录','并列任务日历跨度、已记录运行及工具等待、系统duration原值和无证据空档。任务可能重叠，不跨行累计；本轮结束不等于功能上线。','N');
tasks.getRange(`B6:C${tEnd}`).setNumberFormat('yyyy-mm-dd hh:mm:ss');
tasks.getRange(`D6:F${tEnd}`).setNumberFormat('0.00');
tasks.getRange(`K6:L${tEnd}`).setNumberFormat('0.00');
data.tasks.forEach((x,i)=>{const lines=Math.ceil(x.purpose.length/65); tasks.getRange(`A${i+6}:N${i+6}`).format.rowHeight=Math.max(44,lines*17+12);});

const pEnd=table(prompts,['提示编号','需求记录时间（北京时间）','提示词目的（概括）','记录性质','关联任务','任务开始','任务结束','共享运行及等待分钟','计时依据','本轮状态','证据：会话／行'],
  data.requests.map(x=>{const t=byTask.get(x.task_id);return [x.id,wallDate(x.time),x.purpose,x.kind,x.task_id,wallDate(t.start),wallDate(t.end),t.execution_minutes,t.basis,t.lifecycle,`${x.source.session_id.slice(0,8)}／${x.source.event_line}`];}),
  [10,25,65,18,13,25,25,18,25,18,22],'RequestPurposeLog');
title(prompts,'完整提示词目的与微调记录','每条需求、补充、确认、重试均保留。目的已概括，不含账号密钥及原附件正文。同一T任务下的多个P提示共用时间，不重复累计。','K');
prompts.getRange(`B6:B${pEnd}`).setNumberFormat('yyyy-mm-dd hh:mm:ss');
prompts.getRange(`F6:G${pEnd}`).setNumberFormat('yyyy-mm-dd hh:mm:ss');
prompts.getRange(`H6:H${pEnd}`).setNumberFormat('0.00');
data.requests.forEach((x,i)=>{prompts.getRange(`A${i+6}:K${i+6}`).format.rowHeight=Math.max(44,Math.ceil(x.purpose.length/46)*17+12);});

const uEnd=table(updates,['事项编号','资料／发布日期','更新模块','目的','具体操作','完成情况／限制','证据状态','关联任务编号','共享运行及等待分钟','核验依据','对应提示编号'],
  data.updates.map(x=>[x.id,x.date,x.module,x.purpose,x.change,x.result,x.status,x.task_ids.join('、'),x.shared_execution_minutes,x.evidence,x.request_ids.join('、')]),
  [10,22,28,45,62,65,30,25,18,43,28],'UpdateAndRefinementInventory');
title(updates,'更新与微调事项总表','按需求目的拆分，按档案与发布证据判断状态。资料／发布日期与真实执行时段分列；I列是关联任务的共享范围，禁止跨事项求和。','K');
updates.getRange(`I6:I${uEnd}`).setNumberFormat('0.00');
data.updates.forEach((x,i)=>{const lines=Math.max(Math.ceil(x.purpose.length/30),Math.ceil(x.change.length/43),Math.ceil(x.result.length/46),Math.ceil(x.evidence.length/29));updates.getRange(`A${i+6}:K${i+6}`).format.rowHeight=Math.max(68,lines*17+16);});

title(overview,'源泽包材库内部汇报','更新目的、微调、完成情况与可核对的工作时段。统计至 '+data.as_of.replace('T',' ').replace('+08:00','')+' 北京时间；本次报表制作不计入历史投入。','H');
overview.getRange('A5:H30').format={font:{name:'Arial',size:11,color:INK},wrapText:true,verticalAlignment:'center'};
for(let i=1;i<=8;i++) overview.getRange(`${col(i)}1:${col(i)}75`).format.columnWidth=[20,16,16,20,18,18,22,28][i-1];
const stats=[['汇报范围',data.period,'资料及执行记录均以北京时间呈现'],['更新／微调事项',data.totals.update_count,'目的拆分，不等于独立发布次数'],['历史提示目的',data.totals.request_count,'包含补充、确认、重试与方案讨论'],['主任务轮次',data.totals.primary_task_count,'另含'+data.totals.subtask_count+'轮协作子任务，以并集去重'],['相关工程主会话',data.totals.primary_session_count,'跨工程同目录工作已纳入；其他设备未同步历史不在范围'],['可核对活动日期',data.totals.recorded_days,'未记录日期不补零，不当作一直开发'],['运行及等待分钟',null,'主指标，并行去重；不是人工工时、额度消耗或人日'],['运行及等待小时',null,'包含AI与工具处理／等待，不把无证据长空档算连续工作'],['去重活动时段',data.totals.segment_count,'主／子任务与并行工程的时间并集'],['Git证据提交数',data.totals.commit_count,'冻结至'+data.source_head.slice(0,7)+'；不以提交时间差计时'],['生命周期跨度分钟',data.totals.lifecycle_calendar_union_minutes,'辅助上界，含无记录空档，不能当连续使用'],['长工具区间分钟',data.totals.long_tool_wait_union_minutes,'单段超过5分钟的已记录工具运行／等待，并行去重；已包含在主指标中']];
for(let i=0;i<stats.length;i++){const r=5+i; overview.getRange(`A${r}:B${r}`).merge();overview.getRange(`D${r}:H${r}`).merge();fmt(overview,`A${r}`,[[stats[i][0]]]);fmt(overview,`C${r}`,[[stats[i][1]]]);fmt(overview,`D${r}`,[[stats[i][2]]]);overview.getRange(`A${r}:H${r}`).format.rowHeight=30; if(i%2===0)overview.getRange(`A${r}:H${r}`).format.fill='#F3F6F2';}
overview.getRange('C11').formulas=[[`=SUM('去重时段'!E6:E${sEnd})`]];
overview.getRange('C12').formulas=[['=C11/60']];
overview.getRange('C11:C16').setNumberFormat('0.00');
overview.getRange('C13:C14').setNumberFormat('0');
overview.getRange('A18:H18').merge();fmt(overview,'A18',[['时间与完成情况的统计口径']]);overview.getRange('A18:H18').format={font:{name:'Arial',size:13,bold:true,color:TEAL},rowHeight:27};
data.method_notes.forEach((note,i)=>{const r=19+i; overview.getRange(`A${r}:H${r}`).merge();fmt(overview,`A${r}`,[[`${i+1}. ${note}`]]);overview.getRange(`A${r}:H${r}`).format.rowHeight=Math.max(28,Math.ceil(note.length/75)*18+8);});
const dayStart=33, dayEnd=dayStart+data.daily.length;
table(overview,['工作日期','首段开始','末段结束','去重分钟','去重小时','连续段数','提示目的数','完整段位置'],data.daily.map(x=>[dayDate(x.date),wallDate(x.first),wallDate(x.last),null,null,x.segment_count,x.request_count,x.segment_ids[0]+'～'+x.segment_ids.at(-1)]),[20,16,16,20,18,18,22,28],'DailyDeduplicatedWork',dayStart);
overview.getRange(`A${dayStart+1}:A${dayEnd}`).setNumberFormat('yyyy-mm-dd');
overview.getRange(`B${dayStart+1}:C${dayEnd}`).setNumberFormat('mm-dd hh:mm');
overview.getRange(`D${dayStart+1}:D${dayEnd}`).formulas=data.daily.map((x,i)=>[`=SUMIF('去重时段'!$B$6:$B$${sEnd},A${dayStart+1+i},'去重时段'!$E$6:$E$${sEnd})`]);
overview.getRange(`E${dayStart+1}:E${dayEnd}`).formulas=data.daily.map((x,i)=>[`=D${dayStart+1+i}/60`]);
overview.getRange(`D${dayStart+1}:E${dayEnd}`).setNumberFormat('0.00');
const pendingStart=dayEnd+3;
overview.getRange(`A${pendingStart}:H${pendingStart}`).merge();fmt(overview,`A${pendingStart}`,[['仍待完善／验证的内容']]);overview.getRange(`A${pendingStart}:H${pendingStart}`).format={font:{name:'Arial',size:13,bold:true,color:TEAL},rowHeight:27};
data.pending.forEach((note,i)=>{const r=pendingStart+1+i;overview.getRange(`A${r}:H${r}`).merge();fmt(overview,`A${r}`,[[`${i+1}. ${note}`]]);overview.getRange(`A${r}:H${r}`).format={font:{name:'Arial',size:11,color:INK},wrapText:true,rowHeight:42,verticalAlignment:'center'};});
const srcStart=pendingStart+data.pending.length+3;
overview.getRange(`A${srcStart}:H${srcStart}`).merge();fmt(overview,`A${srcStart}`,[['证据与范围说明']]);overview.getRange(`A${srcStart}:H${srcStart}`).format={font:{name:'Arial',size:13,bold:true,color:TEAL},rowHeight:27};
data.source_registry.forEach((x,i)=>{const r=srcStart+i+1;overview.getRange(`A${r}:H${r}`).merge();fmt(overview,`A${r}`,[[`${x.id} ${x.title}：${x.detail}`]]);overview.getRange(`A${r}:H${r}`).format={font:{name:'Arial',size:10,color:MUTED},wrapText:true,rowHeight:36,verticalAlignment:'center'};});
overview.freezePanes.freezeRows(4);overview.freezePanes.freezeColumns(0);
wb.recalculate();
const expected=data.totals.deduplicated_minutes;
const actual=overview.getRange('C11').values[0][0];
if(typeof actual!=='number'||Math.abs(actual-expected)>0.001)throw new Error(`Duration total mismatch ${actual} != ${expected}`);
const checks=await wb.inspect({kind:'match',searchTerm:'#REF!|#DIV/0!|#VALUE!|#NAME\\?|#NUM!|#N/A',options:{useRegex:true,maxResults:30},maxChars:2000});
await fs.writeFile(path.join(qaDir,'formula-error-inspection.json'),JSON.stringify(checks,null,2));
const summary=await wb.inspect({kind:'region',sheetId:'汇报总览',range:'A5:H14',maxChars:3000,tableMaxRows:12,tableMaxCols:8});
await fs.writeFile(path.join(qaDir,'summary-inspection.json'),JSON.stringify(summary,null,2));
for(const [sheetName,range,name] of [['汇报总览','A1:H29','overview'],['更新与微调','A1:K9','updates'],['提示词目的','A1:K10','prompts'],['任务时段','A1:N10','tasks'],['去重时段','A1:F12','segments']]){
  const preview=await wb.render({sheetName,range,scale:1,format:'png'});
  await fs.writeFile(path.join(qaDir,`${name}.png`),new Uint8Array(await preview.arrayBuffer()));
}
const out=await SpreadsheetFile.exportXlsx(wb);
const output=path.join(outDir,'源泽包材库_更新微调与工作时段汇报_20260922-20261013.xlsx');
await out.save(output);
await fs.writeFile(path.join(qaDir,'export-summary.json'),JSON.stringify({output,sheets:5,updates:data.updates.length,requests:data.requests.length,tasks:data.tasks.length,segments:data.segments.length,totalMinutes:actual,totalHours:actual/60},null,2));
console.log(JSON.stringify({output,totalMinutes:actual,totalHours:actual/60,sheets:5}));
