import {recordUses,recordReferenceUses} from './catalog-taxonomy.js';
import {factRows,materialFact} from './product-detail-facts.js';
import {t,registerTranslations,getLanguage,onLanguageChange} from './i18n.js';
import {pricingData} from './product-pricing.js';
registerTranslations({
 '通常用于':'Typically used for','加工工艺':'Finishing options','参考费用 · 待补充':'Reference fees · to be provided','费用':'Fee','起订量':'MOQ','预计货期':'Lead time','裸瓶':'Bare container','见上方':'See above','基础项':'Base item','每色':'Per colour','每个':'Per unit','颜色数':'Colour count','现货情况':'Stock availability','未确认':'Unconfirmed','有现货':'In stock','无现货':'Out of stock','内部资料与原始报价':'Internal information & source quotation',
 '选配参考价':'Estimated configured price','选择工艺，预览参考价格':'Select finishes to preview a reference price',
 '所选工艺费用未填写，暂不能估算':'Selected finishing fees are missing; estimate unavailable',
 '裸瓶价格或币种未明确，暂不能估算':'Bare price or currency is not explicit; estimate unavailable',
 '颜色数量须为 1–9 的整数':'Colour count must be a whole number from 1 to 9',
 '费用单位为人民币。空白表示未录入；工艺可能改变 MOQ、货期及价格，须按本次需求确认。':'Fees are in CNY. Blank fields are not recorded. Finishing may change MOQ, lead time and price; confirm for each request.',
 '仅估算裸瓶与所选工艺，不含材质差价、配件及税费，不作为正式报价。MOQ 和货期需另行确认。':'Estimates include only the bare container and selected finishes. Material differences, components and tax are excluded. This is not a formal quotation; confirm MOQ and lead time separately.',
 '资料未录入':'Not recorded','工艺增量':'Finishing increment','历史询价':'Historical quote','其他规格与参数':'Additional specifications',
 '普通参考报价':'Standard reference quotation','定制参考报价':'Custom reference quotation','完整报价与费用条件':'Source quotation and fee conditions','配置与税费按原文核对':'Confirm configuration and taxes against the source',
});
export const defaultProcesses=[['silk','丝印','Screen printing','colour'],['foil','烫金 / 烫银','Gold / silver foil','colour'],['injection','注塑色','Moulded colour','unit'],['spray','喷涂','Spray coating','colour'],['frost','蒙砂','Frosting','unit'],['bodyPlate','电镀瓶身','Body plating','unit'],['capPlate','电镀盖子','Cap plating','unit'],['other','其他工艺','Other finish','unit']].map(([id,name,englishName,unit])=>({id,name,englishName,unit,price:null,moq:'',leadTime:''}));
export const esc=value=>String(value??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const clean=v=>{const s=v==null?'':String(v).trim();return /^(?:[/／—–\-]+|暂无|待补(?:充)?|待确认|待核对|未填写|未注明|null|N\/?A)$/i.test(s)?'':s;};
const values=rows=>[...new Set(rows.map(row=>clean(row.value)).filter(Boolean))].join('\n');
export function coreFacts(r={},spec=''){
 const p=pricingData(r),confirmed=recordUses(r),references=recordReferenceUses(r).filter(value=>!confirmed.includes(value));
 return {bare:values(p.bare),terms:values(p.terms),tax:values(p.tax),
  material:materialFact(r),
  spec:clean(spec)||clean(r.specificationRaw)||(r.capacityMl==null?'':`${r.capacityMl} mL`),
  moq:clean(r.moqRaw)||values(p.moq),lead:clean(r.leadTimeRaw)||values(p.lead),
  uses:confirmed.map(value=>t(value)).join(' / '),referenceUses:references.map(value=>t(value)).join(' / '),stock:['yes','no'].includes(r.stockStatus)?r.stockStatus:'unknown'};
}
// A single explicit CNY price can be estimated. Conditional, mixed-component,
// tiered or foreign-currency text stays visible but is never silently added.
export function bareAmount(value,currency){
 const text=clean(value);if(!text||currency&&!/^(CNY|RMB|人民币)$/i.test(currency))return null;
 const m=/^(?:(?:裸瓶|瓶身|瓶体)(?:价格|报价|单价|价)?\s*[:：]?\s*)?(?:[¥￥]\s*)?(\d+(?:\.\d{1,4})?)\s*(元|人民币|RMB|CNY)?(?:\s*\/(?:个|只|件))?$/i.exec(text);
 if(!m||(!m[2]&&!/[¥￥]/.test(text)&&!currency))return null;
 const n=Number(m[1]);return Number.isFinite(n)&&n<=1e8?n:null;
}
export function estimatePrice(base,processes,selected,counts={}){
 let units=0;const missing=[],invalid=[];
 for(const id of selected){const p=processes.find(p=>p.id===id);if(!p||p.price==null||typeof p.price!=='number'||!Number.isFinite(p.price)||p.price<0){missing.push(id);continue;}
  const count=p.unit==='colour'?Number(counts[id]??1):1;if(!Number.isInteger(count)||count<1||count>9){invalid.push(id);continue;}
  units+=Math.round(p.price*10000)*count;
 }
 return {missing,invalid,increment:units/10000,total:base!=null&&!missing.length&&!invalid.length?Math.round(base*10000+units)/10000:null};
}
const processName=p=>getLanguage()==='en'?(p.englishName||p.name):p.name;
function estimateMarkup(base,processes,selection,counts){
 const e=estimatePrice(base,processes,selection,counts);
 return `<section class="pd-estimate" aria-live="polite"><h3>${esc(t('选配参考价'))}</h3>${!selection.size?`<p>${esc(t('选择工艺，预览参考价格'))}</p>`:e.total==null?`<p class="pd-missing">${esc(t(base==null?'裸瓶价格或币种未明确，暂不能估算':e.invalid.length?'颜色数量须为 1–9 的整数':'所选工艺费用未填写，暂不能估算'))}</p>`:`<div class="pd-estimate-value">¥${e.total.toFixed(2)}<small> / ${esc(t('个'))}</small><span>${esc(t('工艺增量'))} + ¥${e.increment.toFixed(2)}</span></div>`}<small>${esc(t('仅估算裸瓶与所选工艺，不含材质差价、配件及税费，不作为正式报价。MOQ 和货期需另行确认。'))}</small></section>`;
}
export function processTable(processes=defaultProcesses,selection=new Set(),counts={}){
 return `<section class="pd-process"><div class="pd-section-head"><h3>${esc(t('加工工艺'))}</h3><small>${esc(t('参考费用 · 待补充'))}</small></div><div class="pd-table-wrap"><table><thead><tr>${['工艺','费用','起订量','预计货期'].map(s=>`<th>${esc(t(s))}</th>`).join('')}</tr></thead><tbody><tr class="pd-basis"><td>${esc(t('裸瓶'))}</td><td>${esc(t('见上方'))}</td><td colspan="2">${esc(t('基础项'))}</td></tr>${processes.map(p=>`<tr><td><label><input type="checkbox" data-pd-finish="${esc(p.id)}" ${selection.has(p.id)?'checked':''}><span data-i18n-skip>${esc(processName(p))}</span></label></td><td><span data-i18n-skip>${p.price==null?'':`¥${Number(p.price).toFixed(2)}`}</span>${p.price==null?'':`<small>${esc(t(p.unit==='colour'?'每色':'每个'))}</small>`}${p.unit==='colour'?`<label class="pd-colours" ${selection.has(p.id)?'':'hidden'}><input type="number" data-pd-count="${esc(p.id)}" value="${esc(counts[p.id]??1)}" min="1" max="9" step="1" aria-label="${esc(processName(p)+' '+t('颜色数'))}"></label>`:''}</td><td data-i18n-skip>${esc(p.moq)}</td><td data-i18n-skip>${esc(p.leadTime)}</td></tr>`).join('')}</tbody></table></div><p class="pd-note">${esc(t('费用单位为人民币。空白表示未录入；工艺可能改变 MOQ、货期及价格，须按本次需求确认。'))}</p></section>`;
}
export function referenceQuotes(record){
 const p=pricingData(record);
 // The user confirmed ordinary reference quotations are bare-container prices;
 // pricingData classifies them once, in the primary bare-price field.
 const blocks=[['定制参考报价',p.customPrice]].filter(([,rows])=>rows.some(row=>clean(row.value)));
 const sources=p.quoteOriginal.filter(([label])=>label!=='规格原文');
 if(!blocks.length&&!sources.length)return '';
 return `<section class="pd-reference-quotes">${blocks.map(([label,rows])=>`<div class="pd-reference-price"><h3>${esc(t(label))}</h3>${rows.map(row=>`<p data-i18n-skip>${esc(clean(row.value))}</p>`).join('')}<small>${esc(t('配置与税费按原文核对'))}</small></div>`).join('')}${sources.length?`<details class="pd-source-quote"><summary>${esc(t('完整报价与费用条件'))}</summary>${sources.map(([label,value])=>`<div><small>${esc(t(label))}</small><p data-i18n-skip>${esc(value)}</p></div>`).join('')}</details>`:''}</section>`;
}
export function compactDetail(r,settings={},spec=''){
 const f=coreFacts(r,spec),base=bareAmount(f.bare,r.currency),processes=Array.isArray(settings.processStandards)?settings.processStandards:defaultProcesses;
 const amount=base==null?esc(f.bare):`<span class="pd-currency">¥</span>${base.toFixed(2)}<small> / ${esc(t('个'))}</small>`;
 return `<section class="pd-info" data-pd-record="${esc(r.id)}"><p class="pd-code" data-i18n-skip>${esc(r.productCode||r.id)}</p><section class="pd-price"><div class="pd-price-head"><span>${esc(t('裸瓶价格'))}</span><small>${esc(t('历史询价'))}</small></div><div class="pd-price-value" data-i18n-skip>${amount||'<span class="pd-blank">—</span>'}</div><p class="pd-terms" data-i18n-skip>${esc(f.terms)}</p>${f.tax?`<details><summary>${esc(t('含税价格'))}</summary><div data-i18n-skip>${esc(f.tax)}</div></details>`:''}</section>${referenceQuotes(r)}<dl class="pd-facts">${factRows(f)}</dl>${processTable(processes)}${estimateMarkup(base,processes,new Set(),{})}<section class="pd-stock"><h3>${esc(t('现货情况'))}</h3><span>${esc(t(f.stock==='yes'?'有现货':f.stock==='no'?'无现货':'未确认'))}</span></section></section>`;
}
export function bindDetail(container,r,settings={}){
 const selection=new Set(),counts={},processes=Array.isArray(settings.processStandards)?settings.processStandards:defaultProcesses,base=bareAmount(coreFacts(r).bare,r.currency);
 const refresh=()=>{const node=container.querySelector('.pd-estimate');if(node)node.outerHTML=estimateMarkup(base,processes,selection,counts);};
 function change(e){const id=e.target.dataset.pdFinish;if(id){e.target.checked?selection.add(id):selection.delete(id);const row=e.target.closest('tr');const colours=row?.querySelector('.pd-colours');if(colours)colours.hidden=!e.target.checked;refresh();}else if(e.target.dataset.pdCount){counts[e.target.dataset.pdCount]=e.target.value;refresh();}}
 container.addEventListener('change',change);container.addEventListener('input',change);
 const stop=onLanguageChange(()=>{if(!container.querySelector('[data-pd-record]')||!container.isConnected){stop();return;}container.querySelector('.pd-process').outerHTML=processTable(processes,selection,counts);refresh();});
 return ()=>{container.removeEventListener('change',change);container.removeEventListener('input',change);stop();};
}
