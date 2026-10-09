import {translateValue} from './i18n.js';
import {recordUses,recordReferenceUses,recordSearchUses,usageSearchTerms,recordBodySections,usageOptions} from './catalog-taxonomy.js';
import {createProductGroupIndex,groupProducts} from './product-groups.js';
import {productImageStatus} from './image-policy.js';
export const text=v=>typeof v==='string'?v:(v==null?'':JSON.stringify(v));
export const raw=r=>[r.name,r.materialRaw,r.specificationRaw,r.processRaw,r.remarksRaw].map(text).join(' ');
export const quote=r=>[["确认单价",r.unitPrice==null?'':String(r.unitPrice)+(r.currency?' '+r.currency:'')],["普通报价",r.quoteRaw],["定制报价",r.customQuoteRaw]].filter(([,v])=>text(v)).map(([k,v])=>k+'：'+text(v)).join('\n');
export const supplier=r=>text(r.supplierRaw)||'供应商待补';
const kindNames={package:'包材',source_page:'图册与图片线索',process_rule:'工艺与价格参考',semi_finished:'料体与半成品',service:'检测与服务',requirement:'需求资料',uncertain:'待分类'};
const sectionNames={face:'面部',body:'身体',head:'头部'};
export function category(r){if(r.category)return r.category;if(r.kind!=='package')return kindNames[r.kind]||'待分类';const n=r.name||'';for(const [re,v] of [[/喷雾泵|乳液泵|泵头|喷头|泡沫泵/,'泵头与喷头'],[/滴管/,'滴管与滴管瓶'],[/软管/,'软管'],[/袋|膜袋/,'袋类'],[/彩盒|纸盒|包装盒|礼盒|内托/,'外包装'],[/瓶/,'瓶类'],[/罐|膏霜盒/,'罐与广口盒'],[/盖|内塞|垫片/,'盖与其他配件'],[/标签|标贴/,'标签辅材']])if(re.test(n))return v;return '待细分';}
export function materials(r){if(r.materials?.length)return r.materials;const n=(text(r.materialRaw)+' '+text(r.name)).toUpperCase(),a=[];if(/玻璃/.test(n))a.push('玻璃');for(const m of ['PETG','PET','HDPE','LDPE','PP','PE','PMMA','ABS','AS'])if(new RegExp('(?:^|[^A-Z])'+m+'(?:[^A-Z]|$)').test(n))a.push(m);if(!a.length&&/塑料|塑胶/.test(n))a.push('塑料（待细分）');if(/铝/.test(n))a.push('铝');if(/纸/.test(n))a.push('纸');return a;}
export function capacities(r){const override=r.specificationOverride,hasOverride=override&&typeof override.label==='string'&&['capacityMl','specificationRaw'].includes(override.sourceField);if(!hasOverride&&r.capacityMl!==null&&r.capacityMl!==undefined&&String(r.capacityMl).trim()!==''&&Number.isFinite(+r.capacityMl)&&+r.capacityMl>0)return [+r.capacityMl];const spec=text(hasOverride?override.label:r.specificationRaw).normalize('NFKC');if(/\d\s*(?:ml|毫升)?\s*[-~～至–—\/+×x]\s*\d/i.test(spec))return [];const found=[...new Set([...spec.matchAll(/(\d+(?:\.\d+)?)\s*(?:ml|毫升)/gi)].map(m=>+m[1]).filter(n=>n>0))];return found.length===1?found:[];}
export function normalizeSearch(value){return String(value??'').normalize('NFKC').toLowerCase().replace(/(\d+(?:\.\d+)?)\s*(?:毫升|ml)/g,'$1ml').replace(/(\d+(?:\.\d+)?)\s*(?:克|g(?![a-z]))/g,'$1g');}
export function codeKey(value){return normalizeSearch(value).replace(/[\s\u200b\uFEFF\-‐‑‒–—−_]/g,'').toUpperCase();}
export function searchTerms(value){const chunks=normalizeSearch(value).match(/[\p{L}\p{N}]+(?:[._-][\p{L}\p{N}]+)*/gu)||[];const segmenter=typeof Intl.Segmenter==='function'?new Intl.Segmenter('zh',{granularity:'word'}):null;return chunks.flatMap(chunk=>segmenter&&/[\u3400-\u9fff]/u.test(chunk)?[...segmenter.segment(chunk)].map(x=>x.segment).filter(x=>/[\p{L}\p{N}]/u.test(x)):[chunk]);}
export function searchMatchers(value){return searchTerms(value).map(word=>/^[a-z0-9][a-z0-9._-]*$/.test(word)?{word,spec:/^\d+(?:[._-]\d+)*(?:ml|g|l)$/.test(word),re:new RegExp('(?:^|[^a-z0-9])'+word.replace(/[.*+?^${}()|[\]\\]/g,'\\$&')+'(?![a-z0-9])')}:{word});}
export function matchesText(record,matchers){return matchers.every(({word,re,spec})=>{const haystack=spec&&record._groupSpecSearch!==undefined?record._groupSpecSearch:record._search;return re?re.test(haystack):haystack.includes(word);});}
export function inBand(value,band){if(!band)return true;const edges={'lt50':[0,50],'50-150':[50,150],'150-250':[150,250],'250-350':[250,350],'350-500':[350,500],'500-1000':[500,1000],'gte1000':[1000,Infinity]};const range=edges[band];return range&&value>=range[0]&&value<range[1];}
export function prepareRecords(catalog, reviewedProductGroups){const records=catalog.records.map(r=>{const item={...r,name:text(r.name)||'名称待补'};item._uses=recordUses(item);item._referenceUses=recordReferenceUses(item).filter(value=>!item._uses.includes(value));item._searchUses=recordSearchUses(item);item._sections=recordBodySections(item);item._sourceFile=text(r.source?.workbook||'');item._category=category(item);item._materials=materials(item);item._capacities=capacities(item);item._search=[item.productCode,item.id,item.name,item.searchText,item._sourceFile,item.bottleType,item.series,item.model,item.description,...(item.productDetails||[]).flatMap(d=>[d.label,d.value]),...usageSearchTerms(item),...item._sections.map(k=>sectionNames[k]),...Object.entries(item).filter(([k])=>k.endsWith('Raw')).map(([,v])=>text(v)),raw(item),supplier(item),quote(item),item._category,...item._materials,...item._capacities.map(v=>v+'ml')].map(text).join(' ');item._search=normalizeSearch(item._search+' '+[item._category,item.bottleType,...item._materials,...usageSearchTerms(item),...item._sections.map(k=>sectionNames[k])].map(value=>translateValue(value,'en')).join(' '));return item;});const productGroupIndex=createProductGroupIndex(records,reviewedProductGroups);for(const r of records){const group=productGroupIndex.get(r.id);if(!group)continue;
// A page's OCR or a historical quote may mention other sizes. Only this SKU's
// reviewed labels determine its size matches, before the results are grouped.
const labels=group.specs.filter(spec=>spec.recordIds.includes(r.id)).map(spec=>spec.label);
// Explicit, visually reviewed type hints fill gaps only; administrator edits
// always take precedence, and the stored source record is never rewritten.
if(group.classification){
  if(!r.category || r.category==='待细分')r._category=group.classification.category;
  if(!r.bottleType)r.bottleType=group.classification.bottleType;
}
r._referenceUses=recordReferenceUses(r).filter(value=>!r._uses.includes(value));r._searchUses=recordSearchUses(r);
r._search+=' '+normalizeSearch([...usageSearchTerms(r),...r._searchUses.map(value=>translateValue(value,'en'))].join(' '));
if(labels.length)r._groupSpecSearch=normalizeSearch(labels.join(' '));
else if(r._capacities.length)r._groupSpecSearch=normalizeSearch(r._capacities.map(value=>value+'ml').join(' '));
r._search+=' '+normalizeSearch(group.name+' '+labels.join(' ')+' '+r._category+' '+r.bottleType+' '+translateValue(r.bottleType,'en'));}
const productCodeIndex=new Map(records.filter(r=>r.productCode).map(r=>[codeKey(r.productCode),r]));const recordIdIndex=new Map(records.map(r=>[normalizeSearch(r.id).trim(),r]));return {records,productGroupIndex,productCodeIndex,recordIdIndex};}

export const facetKeys=['kind','section','category','material','capacity','capacityBand','bottle','use','quote','source','imageStatus'];
export function matchRecords(index, options={}) {
  const selected=key=>options.filters?.[key]||[];
  const any=(key,values)=>!selected(key).length||selected(key).some(value=>values.map(String).includes(String(value)));
  const query=String(options.q||'').trim(),key=codeKey(query),number=/^YZBC\d{6,}$/.test(key);
  const idRecord=index.recordIdIndex.get(normalizeSearch(query)),lookup=number?index.productCodeIndex.get(key):idRecord;
  const matchers=searchMatchers(query),words=matchers.map(m=>m.word);
  const favorite=options.favorites ? new Set(options.favoriteIds||[]) : null;
  const ranks=Array.isArray(options.imageIds)?new Map(options.imageIds.map((id,rank)=>[id,rank])):null;
  let rows=index.records.filter(r=>(!favorite||favorite.has(r.id))&&(!ranks||ranks.has(r.id))&&
    any('kind',[r.kind])&&any('section',r._sections)&&any('category',[r._category])&&any('material',r._materials)&&any('capacity',r._capacities)&&
    (!selected('capacityBand').length||r._capacities.some(v=>selected('capacityBand').some(b=>inBand(v,b))))&&
    any('bottle',[r.bottleType])&&any('use',r._searchUses)&&any('quote',[quote(r)?'yes':'no'])&&any('source',[r._sourceFile])&&
    (!selected('imageStatus').length||(r.kind==='package'&&any('imageStatus',[productImageStatus(r)])))&&
    (number||idRecord?r.id===lookup?.id:matchesText(r,matchers)));
  if(ranks)rows.sort((a,b)=>ranks.get(a.id)-ranks.get(b.id));
  else if(words.length||selected('use').length){const confirmed=r=>selected('use').some(value=>r._uses.includes(value))?1:0;const score=r=>words.reduce((v,w)=>v+(text(r.model).toLowerCase()===w?12:0)+(r.id.toLowerCase()===w?16:0)+(r.name.toLowerCase().includes(w)?3:0),0);rows=rows.map(r=>({r,score:score(r)})).sort((a,b)=>confirmed(b.r)-confirmed(a.r)||b.score-a.score).map(x=>x.r);}
  return rows;
}
export function catalogFacets(records) {
  const strings=values=>[...new Set(values.filter(Boolean))].sort();
  return {categories:strings(records.map(r=>r._category)),materials:strings(records.flatMap(r=>r._materials)),
    capacities:[...new Set(records.filter(r=>r.kind==='package').flatMap(r=>r._capacities))].filter(v=>v>0).sort((a,b)=>a-b),
    bottles:strings(records.map(r=>r.bottleType)),uses:usageOptions(records),sources:strings(records.map(r=>r._sourceFile))};
}
export function queryPage(index, options={}) {
  const matching=matchRecords(index,options),grouped=groupProducts(matching,index.productGroupIndex);
  const size=[20,40,80].includes(options.pageSize)?options.pageSize:20,pages=Math.max(1,Math.ceil(grouped.length/size));
  const page=Math.min(pages,Math.max(1,options.page||1)),shown=grouped.slice((page-1)*size,page*size);
  const ids=new Set(shown.flatMap(r=>index.productGroupIndex.get(r.id)?.records.map(x=>x.id)||[r.id]));
  if(page===1&&!options.q)for(const id of ['MAT-OCR-PDF11-P0004-H2-1','MAT-OCR-PDF11-P0004-H3-1','MAT-OCR-PDF11-P0004-H5-1'])if(index.recordIdIndex.has(normalizeSearch(id)))ids.add(id);
  const records=index.records.filter(r=>ids.has(r.id)).map(r=>Object.fromEntries(Object.entries(r).filter(([key])=>!key.startsWith('_'))));
  return {records,pageRecordIds:shown.map(r=>r.id),matchedIds:matching.filter(r=>ids.has(r.id)).map(r=>r.id),
    page,pages,total:grouped.length,matchingRecords:matching.length};
}
