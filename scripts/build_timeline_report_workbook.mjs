import fs from 'node:fs/promises';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
import {SpreadsheetFile,Workbook} from '@oai/artifact-tool';

const root=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'..');
const d=JSON.parse(await fs.readFile(path.join(root,'docs/包材库时间线汇报-20261013.json'),'utf8'));
const outDir=path.join(root,'outputs/timeline-report-20261013');
const qaDir=path.join(root,'work/timeline-report-20261013');
await fs.mkdir(outDir,{recursive:true});await fs.mkdir(qaDir,{recursive:true});
const wb=Workbook.create();
const timeline=wb.worksheets.add('时间线汇报');
const images=wb.worksheets.add('图片批次与并行');
const work=wb.worksheets.add('每日与时段');
const teal='#164B47',ink='#243D39',muted='#617770';
const wall=(s)=>s?new Date(s.replace(/\+08:00$/,'Z')):null;
const day=(s)=>new Date(s.slice(0,10)+'T00:00:00Z');
const stamp=(s)=>s?s.slice(0,19).replace('T',' '):'未记录';
function letter(i){let s='';while(i){s=String.fromCharCode(65+(i-1)%26)+s;i=Math.floor((i-1)/26);}return s;}
function write(s,range,values){s.getRange(range).values=values;}
function heading(s,title,last){s.showGridLines=false;s.tabColor=teal;s.getRange(`A1:${last}1`).merge();write(s,'A1',[[title]]);s.getRange(`A1:${last}1`).format={font:{name:'Arial',size:16,bold:true,color:teal},rowHeight:32};}
function addTable(s,headers,rows,widths,name,start){
  const last=letter(headers.length),end=start+rows.length;
  write(s,`A${start}:${last}${end}`,[headers,...rows]);
  s.getRange(`A${start}:${last}${end}`).format={font:{name:'Arial',size:11,color:ink},wrapText:true,verticalAlignment:'top',rowHeight:42};
  s.getRange(`A${start}:${last}${start}`).format={fill:teal,font:{name:'Arial',size:11,bold:true,color:'#FFFFFF'},verticalAlignment:'center',rowHeight:32};
  widths.forEach((x,i)=>{s.getRange(`${letter(i+1)}1:${letter(i+1)}${end}`).format.columnWidth=x;});
  const t=s.tables.add(`A${start}:${last}${end}`,true,name);t.showFilterButton=true;t.style='TableStyleLight1';
  s.freezePanes.freezeRows(start);s.freezePanes.freezeColumns(2);
  return end;
}
function imageNotes(headers,rows,start){
  const end=start+rows.length;
  images.getRange(`A${start}:M${end}`).format={font:{name:'Arial',size:11,color:ink},wrapText:true,verticalAlignment:'top',rowHeight:90};
  for(const [i,row] of [headers,...rows].entries()){
    const r=start+i;write(images,`A${r}:F${r}`,[row.slice(0,6)]);images.getRange(`G${r}:M${r}`).merge();write(images,`G${r}`,[[row[6]]]);
    if(i%2===0&&i>0)images.getRange(`A${r}:M${r}`).format.fill='#F3F6F2';
  }
  images.getRange(`A${start}:M${start}`).format={fill:teal,font:{name:'Arial',size:11,bold:true,color:'#FFFFFF'},rowHeight:32};
}

heading(work,'按日汇总与唯一可加总时段','G');
work.getRange('A2:G3').merge();write(work,'A2',[['总时长只从下方W区间计算，父子任务与并行工程已去重。跨午夜按北京时间拆分，后台服务持续存活与无证据长空档不计。不是员工人工工时。']]);
work.getRange('A2:G3').format={font:{name:'Arial',size:11,color:muted},wrapText:true,rowHeight:25};
write(work,'A4',[['去重运行与等待分钟']]);
const dailyStart=6;
const dailyEnd=addTable(work,['日期','首段开始（完整日期时间）','末段结束（完整日期时间）','去重分钟','去重小时','去重区间数','对应W编号'],d.daily.map(x=>[day(x.date),wall(x.first),wall(x.last),null,null,x.segment_count,x.segment_ids.join('、')]),[17,27,27,18,18,18,60],'TimelineDaily',dailyStart);
work.getRange(`A7:A${dailyEnd}`).setNumberFormat('yyyy-mm-dd');work.getRange(`B7:C${dailyEnd}`).setNumberFormat('yyyy-mm-dd hh:mm:ss');
const wStart=dailyEnd+5;
work.getRange(`A${wStart-2}:G${wStart-1}`).merge();write(work,`A${wStart-2}`,[['以下为全部119段并行去重记录，开始与结束显示完整日期时间。总值从这些区间计算，不从时间线的共享任务行累计。']]);work.getRange(`A${wStart-2}:G${wStart-1}`).format={font:{name:'Arial',size:11,color:muted},wrapText:true,rowHeight:23};
const wEnd=addTable(work,['时段编号','日期','开始（北京时间）','结束（北京时间）','持续分钟（可加总）','秒数','计时依据'],d.segments.map(x=>[x.id,day(x.date),wall(x.start),wall(x.end),null,null,x.method]),[17,27,27,27,23,18,60],'TimelineUniqueSpans',wStart);
work.getRange(`B${wStart+1}:B${wEnd}`).setNumberFormat('yyyy-mm-dd');work.getRange(`C${wStart+1}:D${wEnd}`).setNumberFormat('yyyy-mm-dd hh:mm:ss');
work.getRange(`E${wStart+1}:E${wEnd}`).formulas=d.segments.map((x,i)=>[`=(D${wStart+1+i}-C${wStart+1+i})*1440`]);
work.getRange(`F${wStart+1}:F${wEnd}`).formulas=d.segments.map((x,i)=>[`=E${wStart+1+i}*60`]);
work.getRange(`E${wStart+1}:F${wEnd}`).setNumberFormat('0.00');
work.getRange('E4').formulas=[[`=SUM(E${wStart+1}:E${wEnd})`]];work.getRange('E4').setNumberFormat('0.00');
work.getRange(`D7:D${dailyEnd}`).formulas=d.daily.map((x,i)=>[`=SUMIF($B$${wStart+1}:$B$${wEnd},A${7+i},$E$${wStart+1}:$E$${wEnd})`]);
work.getRange(`E7:E${dailyEnd}`).formulas=d.daily.map((x,i)=>[`=D${7+i}/60`]);work.getRange(`D7:E${dailyEnd}`).setNumberFormat('0.00');
work.freezePanes.freezeRows(dailyStart);

heading(timeline,'源泽包材库建设与优化 · 精确时间线','K');
for(const r of [2,3])timeline.getRange(`B${r}:K${r}`).merge();
write(timeline,'A2',[['报告期间']]);write(timeline,'B2',[[d.period+'；截至 '+stamp(d.as_of)+' 北京时间']]);
write(timeline,'A3',[['主统计']]);write(timeline,'B3',[[`${d.totals.timeline_event_count}条事件，114项关联更新，183条需求目的，65次提交；16个活动日期。`]]);
write(timeline,'A4',[['去重运行等待']]);timeline.getRange('B4').formulas=[["='每日与时段'!E4/60"]];timeline.getRange('B4').setNumberFormat('0.00"小时"');timeline.getRange('C4:K4').merge();write(timeline,'C4',[['含AI与工具处理／等待，不等于人工工时；共用T编号的行不能重复累计。多个工程共用同一正式库和网站。']]);
timeline.getRange('A2:K4').format={font:{name:'Arial',size:11,color:ink},rowHeight:28,wrapText:true,verticalAlignment:'center'};
timeline.getRange('A5:K6').merge();write(timeline,'A5',[['左侧日期时刻是需求日志或Git提交记录。U行是该需求的关联成果（截至报告的核验状态），不能当作这个时刻已经完成；具体执行范围见T起止。图片批次在单独表按I编号计一次；事件重复提到同批不算再制作。']]);timeline.getRange('A5:K6').format={font:{name:'Arial',size:11,color:muted},rowHeight:26,wrapText:true,verticalAlignment:'center'};
const tasks=new Map(d.events.filter(e=>e.task).map(e=>[e.task.id,e.task]));
const events=new Map(d.events.map(e=>[e.id,e]));
const batches=new Map([...d.image_batches,...d.image_operations].map(b=>[b.batch_id,b]));
const rows=[];const kinds=[];
for(const group of d.days){
  if(!group.event_ids.length){const a=group.activity_summary;rows.push(['跨日延续',day(group.date),wall(a.first),'活动记录','跨日关联任务', '无新需求或提交，上一日任务跨午夜延续','仅列已记录的运行／工具等待，不产生新功能或新任务。','活动时长已包含在W并集；无独立发布结论。',stamp(a.first)+' → '+stamp(a.last),a.minutes,a.segment_ids.join('、')]);kinds.push('continuation');}
  for(const id of group.event_ids){
    const e=events.get(id),t=e.task;
    const batchNote=e.batch_ids.map(k=>{const b=batches.get(k);return `${k} ${b.title}（${b.produced_versions}个最终版本；同批不再累计）`;}).join('\n');
    rows.push([e.id,day(e.date),wall(e.time),e.event_type,e.project_label,e.purpose,e.operation+(batchNote?'\n所属图片批次：\n'+batchNote:''),e.status,t?`${t.id}\n${stamp(t.start)} → ${stamp(t.end)}`:'—',t?.execution_minutes??null,e.evidence+(e.request_id?'；'+e.request_id:'')]);kinds.push('event');
    for(const u of e.updates){
      const spans=u.task_ids.map(k=>{const x=tasks.get(k);return x?`${k} ${stamp(x.start)} → ${stamp(x.end)}`:k;}).join('\n');
      rows.push([`${e.id}／${u.id}`,day(e.date),wall(e.time),'关联成果（需求锚点）',e.project_label,`${u.module}\n目的：${u.purpose}`,u.change,`${u.status}\n${u.result}`,spans,u.shared_execution_minutes,`${u.evidence}\n需求：${u.request_ids.join('、')}`]);kinds.push('update');
    }
  }
}
const end=addTable(timeline,['时间线编号','日期（北京时间）','具体时间','事件类型','所属工程／工作流','目的／更新事项','具体操作／对应图片数量','截至报告的完成状态／限制','任务起止（完整日期时间）','共享运行等待分钟','核对依据／关联编号'],rows,[18,18,15,27,36,53,64,64,54,24,45],'ChronologicalReport',7);
timeline.getRange(`B8:B${end}`).setNumberFormat('yyyy-mm-dd');timeline.getRange(`C8:C${end}`).setNumberFormat('hh:mm:ss');timeline.getRange(`J8:J${end}`).setNumberFormat('0.00');
for(let i=0;i<rows.length;i++){
  const x=rows[i],lines=Math.max(Math.ceil(String(x[5]).length/34),Math.ceil(String(x[6]).length/44),Math.ceil(String(x[7]).length/43),String(x[8]).split('\n').length*3,Math.ceil(String(x[10]).length/30));
  timeline.getRange(`A${i+8}:K${i+8}`).format.rowHeight=Math.min(409,Math.max(55,lines*18+14));
  if(kinds[i]==='event'){timeline.getRange(`A${i+8}:F${i+8}`).format.font.bold=true;}
}
timeline.freezePanes.freezeColumns(3);

heading(images,'图片制作数量与多个工程并行记录','M');
images.getRange('A2:M3').merge();write(images,'A2',[['用户同时开启多个Codex工程／聊天，共用桌面正式工程和生产网站。下表按最终合格制作／发布版本统计；不含淘汰、失败、重试尝试，不把客户同步再次当生成。']]);images.getRange('A2:M3').format={font:{name:'Arial',size:11,color:muted},rowHeight:25,wrapText:true};
const imgStart=8,imgEnd=imgStart+d.image_batches.length;
write(images,'A4',[['场景主图美化']]);images.getRange('C4').formulas=[[`=SUMIF(B9:B${imgEnd},"场景主图美化",G9:G${imgEnd})+SUMIF(B9:B${imgEnd},"洗手液规格美化",G9:G${imgEnd})`]];
write(images,'E4',[['规格标注编辑']]);images.getRange('G4').formulas=[[`=SUMIF(B9:B${imgEnd},"规格标注编辑",G9:G${imgEnd})`]];
write(images,'I4',[['合格包材编辑版本']]);images.getRange('K4').formulas=[[`=SUM(G9:G${imgEnd})`]];
images.getRange('A5:M6').merge();write(images,'A5',[['526个场景美化版本另加6个规格标注编辑版本，共532个最终合格包材图片版本，来自529个来源。10-08批量快照为524美化版本／523源；该日同步530既有版本后客户有效图529张。快照与10-10新增2张不混为实时客户总数。']]);images.getRange('A5:M6').format={font:{name:'Arial',size:11,color:ink},rowHeight:27,wrapText:true};
addTable(images,['批次','图像类别','负责工程','关联任务开始','关联任务结束','时间依据（非逐张时长）','合格版本数','新增原图数','同源再编辑数','本批独立原图数','唯一产品记录数','图片关联数','上线、核验与数量依据'],d.image_batches.map(b=>[b.batch_id,b.batch_kind,b.project_label,wall(b.first_started_at),wall(b.last_finished_at),b.time_basis,b.produced_versions,b.new_unique_sources,b.reprocessed_sources,b.unique_sources_in_batch,b.unique_product_record_count,b.product_associations,`${b.status}\n核验时刻：${stamp(b.verification_time)}\n${b.number_basis}`]),[13,25,42,27,27,62,18,18,20,22,23,20,80],'ImageBatchCounts',imgStart);
images.getRange(`D9:E${imgEnd}`).setNumberFormat('yyyy-mm-dd hh:mm:ss');images.getRange(`G9:L${imgEnd}`).setNumberFormat('0');images.getRange(`A9:M${imgEnd}`).format.rowHeight=115;
const otherStart=imgEnd+4;
imageNotes(['操作编号','类型','工程','开始','结束','完成或核验时刻','操作量／结果说明（非主图美化）'],d.image_operations.map(b=>[b.batch_id,b.batch_kind,b.project_label,wall(b.first_started_at),wall(b.last_finished_at),wall(b.verification_time),`${b.title}\n${b.status}\n${b.time_basis}`]),otherStart);
images.getRange(`D${otherStart+1}:F${otherStart+d.image_operations.length}`).setNumberFormat('yyyy-mm-dd hh:mm:ss');images.getRange(`A${otherStart+1}:G${otherStart+d.image_operations.length}`).format.rowHeight=95;
const overlapStart=otherStart+d.image_operations.length+4;
const overlaps=d.parallel_windows.flatMap((p,i)=>p.intervals.map(x=>[`并行${i+1}`,p.batch_ids.join('／'),p.projects.join(' ↔ '),wall(x.start),wall(x.end),x.tasks.join('／'),p.note]));
imageNotes(['并行组','批次对','同时运行的工程','交叠开始','交叠结束','依据任务','数量说明：交叠期间逐张产量未统计'],overlaps,overlapStart);
images.getRange(`D${overlapStart+1}:E${overlapStart+overlaps.length}`).setNumberFormat('yyyy-mm-dd hh:mm:ss');images.getRange(`A${overlapStart+1}:G${overlapStart+overlaps.length}`).format.rowHeight=85;
images.freezePanes.freezeRows(8);
wb.recalculate();
const total=work.getRange('E4').values[0][0];if(typeof total!=='number'||Math.abs(total-d.totals.deduplicated_minutes)>.001)throw new Error('Duration mismatch');
await fs.writeFile(path.join(qaDir,'xlsx-inspection.json'),JSON.stringify(await wb.inspect({kind:'region',sheetId:'时间线汇报',range:'A1:J10',maxChars:3500}),null,2));
await fs.writeFile(path.join(qaDir,'xlsx-error-scan.json'),JSON.stringify(await wb.inspect({kind:'match',searchTerm:'#REF!|#DIV/0!|#VALUE!|#NAME\\?|#NUM!',options:{useRegex:true,maxResults:10},maxChars:2000}),null,2));
if(images.getRange('C4').values[0][0]!==526||images.getRange('G4').values[0][0]!==6||images.getRange('K4').values[0][0]!==532)throw new Error('Image count mismatch');
for(const [sheetName,range,name] of [['时间线汇报','A1:K12','timeline'],['图片批次与并行','A1:M17','images'],['每日与时段','A1:G12','daily']]){const p=await wb.render({sheetName,range,scale:1,format:'png'});await fs.writeFile(path.join(qaDir,name+'.png'),new Uint8Array(await p.arrayBuffer()));}
const file=path.join(outDir,'源泽包材库_时间线汇报_20260922-20261013.xlsx');await(await SpreadsheetFile.exportXlsx(wb)).save(file);
console.log(JSON.stringify({output:file,events:d.events.length,displayRows:rows.length,minutes:total}));
