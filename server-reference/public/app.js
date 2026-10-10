import {prepareRecords,category,materials,capacities,normalizeSearch,codeKey,searchTerms,searchMatchers,matchesText,inBand,text,raw,quote,supplier} from './catalog-query.js';
import {t,translateMessage,translateValue,getLanguage,onLanguageChange,startLocalization,localize,registerTranslations} from './i18n.js';
import {closeMobileSidebar} from './sidebar.js';
import {requestJSON} from './api-client.js';
import {prepareImageQuery, bindImageQueryCrop, rotateImageQuery, boundedImageMatches, IMAGE_QUERY_COPY} from './image-query.js';
registerTranslations(IMAGE_QUERY_COPY);
import {recordUses,recordReferenceUses,recordSearchUses,recordBodySections,usageOptions} from './catalog-taxonomy.js';
import {renderPricing} from './product-pricing.js';
import {compactDetail,bindDetail} from './product-detail-view.js';
let disposeDetailView=null;
import {csvCell} from './csv-guard.js';
import {createCatalogEditor} from './catalog-editor.js';
import {imageScopeLabel,isProductImage,primaryImage,matchedImage as sourceMatchedImage,displayImage,productImageStatus} from './image-policy.js';
import {reviewedProductGroups} from './product-group-data.js';
import {createProductGroupIndex,groupProducts,groupRecordSpec,groupGalleryImages} from './product-groups.js';
import {renderImageViewport,imageViewKey,validImageCrop} from './image-viewport.js';
registerTranslations({'（多规格）':' (Multiple sizes)','（资料已归并）':' (Consolidated records)','同款规格与报价':'Sizes and quotes','选择规格或来源记录，查看对应报价。':'Select a size or source record to view its quote.','当前记录':'Current record','同款图片关联来源':'Image source records','标注规格主图':'Labelled size overview','系列参考图 · 容量对应待确认':'Series reference · Size mapping unconfirmed','规格见标签，图中对应待核对':'See size tags; image mapping needs verification','查看各规格报价':'View quotes by size','款资料':'catalogue items','条原始记录':'source records','水乳瓶系列 · 规格见标签':'Bottle series · See size tags','精华水瓶系列 · 规格见标签':'Toner bottle series · See size tags','膏霜罐系列 · 规格见标签':'Cream jar series · See size tags'});
startLocalization({container:document.querySelector('header > div')});
registerTranslations({'上一张图片':'Previous image','下一张图片':'Next image','上一张':'Previous','下一张':'Next','第 {number} 张图片，共 {count} 张':'Image {number} of {count}'});
const $=s=>document.querySelector(s),esc=v=>String(v??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
function sourceText(value,fallback=''){return value==null||value===''?`<span data-i18n-ui>${esc(fallback)}</span>`:`<span data-i18n-skip>${esc(value)}</span>`;}
let catalog={records:[]},records=[],session={},prefs={favorites:[]},plans=[],sampleData={samples:[],events:[]};
let productGroupIndex=new Map();
let catalogEditor=null,editorRecordId=null;
const facetKeys=['kind','section','category','material','capacity','capacityBand','bottle','use','quote','source','imageStatus'];
const sectionNames={face:'面部',body:'身体',head:'头部'};
const imageStatusNames={single_product:'单品图',same_style_variants:'同款系列参考',unresolved:'待整理／原图参考'};
const state={view:'catalog',query:'',...Object.fromEntries(facetKeys.map(k=>[k,[]])),kind:['package'],page:1,pageSize:20,selected:[],table:false,filtersOpen:false,staffPreview:false};
let remotePage=null,remoteKey='',remoteSequence=0,remoteController=null,remoteLoading=false;
const recordCache=new Map(),imageRecordPins=new Set();
function remoteParams(){const params=new URLSearchParams({q:state.query,page:String(state.page),pageSize:String(state.pageSize)});for(const key of facetKeys)for(const value of picked(key))params.append(key,value);if(state.view==='favorites')params.set('favorites','1');if(imageSearch.matches){params.set('imageSearch','1');for(const id of imageSearch.matches.keys())params.append('imageIds',id);}return params;}
function rememberRecords(items){for(const item of items)recordCache.set(item.id,item);const keep=new Set([...(remotePage?.records||[]).map(r=>r.id),...state.selected,...imageRecordPins]);for(const id of state.selected){const group=productGroupIndex.get(id);for(const r of group?.records||[])keep.add(r.id);}for(const id of recordCache.keys()){if(recordCache.size<=300)break;if(!keep.has(id))recordCache.delete(id);}catalog.records=[...recordCache.values()];prepareCatalogRecords();}
async function loadRemotePage(){
  const sequence=++remoteSequence;remoteController?.abort();remoteController=new AbortController();remoteLoading=true;
  const key=remoteParams().toString();$('#catalogResults')?.setAttribute('aria-busy','true');
  if(imageSearch.matches&&!imageSearch.matches.size&&remotePage){
    // An empty image result is not an unrestricted catalogue query.
    remotePage={...remotePage,records:[],pageRecordIds:[],matchedIds:[],total:0,matchingRecords:0,pages:1,page:1};
    state.page=1;remoteKey=remoteParams().toString();remoteLoading=false;render();return;
  }
  try{const data=await api('/api/catalog/page?'+key,undefined,{signal:remoteController.signal});if(sequence!==remoteSequence)return;
    if(!Array.isArray(data.records)||!Array.isArray(data.pageRecordIds)||!Number.isInteger(data.total)||!Number.isInteger(data.pages)||!Number.isInteger(data.page))throw Error('包材数据格式异常，请稍后重试。');
    remotePage=data;state.page=data.page;catalog={...data,records:catalog.records};remoteKey=remoteParams().toString();rememberRecords(data.records);applySiteSettings();render();
  }catch(error){if(sequence!==remoteSequence||error.name==='AbortError')return;$('#catalogResults')?.removeAttribute('aria-busy');const region=$('#catalogResults')||$('#main');const note=document.createElement('div');note.className='panel load-error';note.innerHTML=`<p role="alert">${esc(error.message)}</p><button class="btn" data-action="retry-page">重试加载</button>`;region.querySelector('.load-error')?.remove();region.prepend(note);if(!remotePage)throw error;
  }finally{if(sequence===remoteSequence){remoteLoading=false;$('#catalogResults')?.removeAttribute('aria-busy');}}
}
async function ensureRecords(ids,{signal}={}){if(!session.catalogPaging)return;for(let start=0;start<ids.length;start+=100){if(signal?.aborted)throw new DOMException('Request cancelled','AbortError');const params=new URLSearchParams();for(const id of ids.slice(start,start+100))params.append('id',id);const data=await api('/api/catalog/records?'+params,undefined,{signal});if(signal?.aborted)throw new DOMException('Request cancelled','AbortError');rememberRecords(data.records);}}
const picked=key=>state[key]||[];
const anySelected=(key,values)=>!picked(key).length||picked(key).some(v=>values.map(String).includes(v));
function toggleFacet(key,value){state[key]=picked(key).includes(value)?picked(key).filter(v=>v!==value):[...picked(key),value];state.page=1;}

const imageSearch={matches:null,preview:'',status:null,statusError:'',busy:false,sequence:0,controller:null};
let imageDraft=null,imageDraftSequence=0,imageDraftController=null,imageDraftPreparing=false;
const kindNames={package:'包材',source_page:'图册与图片线索',process_rule:'工艺与价格参考',semi_finished:'料体与半成品',service:'检测与服务',requirement:'需求资料',uncertain:'待分类'};
const statusNames={available:'在库可借',lent:'已借出',consumed:'测试耗用',sent:'已寄给客户'};
const viewNames={catalog:'包材选型库',favorites:'我的收藏',plans:'选型方案',samples:'实物样品借还',sources:'素材与导入概况',face:'面部',wash:'洗护',mask:'面膜','mask-cloth':'面膜 / 膜布','mask-bag':'面膜 / 膜袋'};
const imagePath=i=>{const p=String(typeof i==='string'?i:i.path||i.file||'').replace(/\\/g,'/').replace(/^\/+/,'');const upload=p.startsWith('uploads/');const parts=p.replace(/^uploads\//,'').replace(/^media\//,'').split('/').filter(x=>x&&x!=='.'&&x!=='..');return (upload?'/uploads/':'/media/')+parts.map(encodeURIComponent).join('/');};
function imageLabel(i,r){const primary=productGroupIndex.get(r.id)?.primaryImage;if(primary&&imageViewKey(i,imagePath(i))===imageViewKey(primary,imagePath(primary))){const label=typeof primary.label==='string'?primary.label.trim():'';return t(label||(!primary.uncertain&&['single_product','same_style_variants'].includes(primary.imageScope)?'标注规格主图':imageScopeLabel(primary,r)));}return imageScopeLabel(i,r);}
const opt=(value,current)=>`<option value="${esc(value)}" ${String(value)===String(current)?'selected':''}>${esc(value)}</option>`;
function quoteDetails(r){return `${r.unitPrice==null?'':facts([['确认单价',String(r.unitPrice)],['币种',r.currency],['报价有效期',r.validUntil]])}<div class="section-label">报价口径（原表列名）</div><div class="raw">${esc(text(r.quoteHeader)||'未注明，待确认')}</div><div class="section-label">普通报价原文</div><div class="panel raw">${sourceText(text(r.quoteRaw),'未填写')}</div>${facts([['普通起订／数量原文',r.moqRaw],['普通交期原文',r.leadTimeRaw]])}${r.customQuoteRaw||r.customMoqRaw||r.customLeadTimeRaw?`<div class="section-label">定制报价原文</div><div class="panel raw">${esc(text(r.customQuoteRaw)||'未填写')}</div>${facts([['定制起订／数量原文',r.customMoqRaw],['定制交期原文',r.customLeadTimeRaw]])}`:''}`;}
function extraDetails(r){return [['备注',r.remarksRaw],['需求',r.requirementsRaw],['日期／补充说明',r.dateOrNotesRaw],['样品费',r.sampleFeeRaw],['开模费',r.moldFeeRaw],['检测计划',r.testPlanRaw],['其他说明',r.extraRaw],['其他补充',r.extra2Raw]].filter(([,v])=>text(v)).map(([k,v])=>`<div class="section-label">${k}原文</div><div class="raw">${esc(text(v))}</div>`).join('');}

function source(r){if(r.sourceNote)return r.sourceNote;if(!r.source)return '管理员维护';const file=text(r.source.workbook);return r.source.page?`${file} · 第 ${r.source.page} 页`:`${file?file+' · ':''}${r.source.sheet||'原始表格'} · 第 ${r.source.row??'?'} 行`;}
function galleryImages(r){return groupGalleryImages(r,productGroupIndex,imagePath);}
function matchedImage(r,path){return sourceMatchedImage(r,path)||galleryImages(r).find(image=>isProductImage(image)&&String(image.path||image.file||'')===path);}
function galleryImage(r){return matchedImage(r,imageSearch.matches?.get(r.id)?.image_path)||productGroupIndex.get(r.id)?.primaryImage||primaryImage(r)||galleryImages(r)[0];}
function imageDownload(r,path){
  const extension=path.match(/\.(jpg|jpeg|png|webp|gif|svg)$/i)?.[1]?.toLowerCase()||'jpg';
  const number=Math.max(0,galleryImages(r).findIndex(i=>imagePath(i)===path))+1;
  const code=/^YZ-BC-\d{6,}$/.test(r.productCode)?r.productCode:'yuanze-image';
  const filename=`${code}-${number}.${extension}`;
  return {filename,url:`${path}?download=${encodeURIComponent(filename)}`};
}
function updateImageDownload(r,path){
  const link=$('#downloadImageLink');if(!link)return;
  link.hidden=!path;if(path){const data=imageDownload(r,path);link.href=data.url;link.download=data.filename;}
}
function imageCount(r){const count=galleryImages(r).length;return count>1?`<span class="image-count">${count} 张图</span>`:'';}
const thumbnailURL=url=>url+(url.includes('?')?'&':'?')+'thumb=1';
function galleryImageURL(i,small){return small ? (validImageCrop(i)&&i.previewPath?imagePath(i.previewPath):thumbnailURL(imagePath(i))) : imagePath(i);}
function imageVisual(r,i,cl='',small=true){return renderImageViewport(i,`<img class="${cl}" src="${esc(galleryImageURL(i,small))}" data-gallery-record="${esc(r.id)}" data-image-view="${esc(imageViewKey(i,imagePath(i)))}" data-source-alt alt="${esc(r.name||'原表图片')}" loading="lazy" decoding="async">`);}
function image(r,cl='',small=true){const i=galleryImage(r),match=matchedImage(r,imageSearch.matches?.get(r.id)?.image_path);return i?`${imageVisual(r,i,cl,small)}<span class="image-label">${esc((match?'本次匹配图 · ':'')+imageLabel(i,r))}</span>${imageCount(r)}`:'<div class="no-image">原表暂无可显示图片</div>';}
function imageThumbnails(r){const valid=galleryImages(r),product=valid.filter(isProductImage),reference=valid.filter(i=>!isProductImage(i));const group=(items,label)=>items.length?`<div class="section-label">${label} · ${items.length} 张</div><div class="thumbnails">${items.map((i,n)=>`<button data-image="${esc(imagePath(i))}" data-image-record="${esc(r.id)}" data-image-view="${esc(imageViewKey(i,imagePath(i)))}" data-image-label="${esc(imageLabel(i,r))}" aria-label="查看${esc(label)}第 ${n+1} 张：${esc(imageLabel(i,r))}" title="${esc(imageLabel(i,r))}">${renderImageViewport(i,`<img src="${esc(galleryImageURL(i,true))}" loading="lazy" decoding="async" alt="${esc(imageLabel(i,r))}">`)}</button>`).join('')}</div>`:'';return group(product,'包材图片')+group(reference,'原图参考 / 待整理');}
function detailGalleryControls(r){return galleryImages(r).length>1?`<div class="pd-gallery-controls"><button type="button" class="btn pd-image-step" data-detail-image-step="-1" aria-label="${esc(t('上一张图片'))}" aria-controls="detailImageContent"><span aria-hidden="true">‹</span><span class="pd-image-caption">${t('上一张')}</span></button><button type="button" class="btn pd-image-step" data-detail-image-step="1" aria-label="${esc(t('下一张图片'))}" aria-controls="detailImageContent"><span class="pd-image-caption">${t('下一张')}</span><span aria-hidden="true">›</span></button></div>`:'';}
function detailGalleryStatus(r){return galleryImages(r).length>1?'<div class="pd-gallery-status"><span id="detailImageStatus" aria-live="polite" aria-atomic="true" data-i18n-skip></span></div>':'';}
function detailGalleryIndex(images,key,path){return images.findIndex(i=>imageViewKey(i,imagePath(i))===key||(!key.includes('#view=')&&!validImageCrop(i)&&i._groupPaths?.includes(path)));}
function updateDetailGalleryState(r,shown){
  const container=$('#modalBody [data-detail-record]');if(!container||container.dataset.detailRecord!==r.id)return;
  const images=galleryImages(r),path=shown?imagePath(shown):'',index=detailGalleryIndex(images,shown?imageViewKey(shown,path):'',path),key=index<0?'':imageViewKey(images[index],imagePath(images[index]));
  const status=container.querySelector('#detailImageStatus');if(status){status.textContent=`${Math.max(0,index)+1} / ${images.length}`;status.setAttribute('aria-label',t('第 {number} 张图片，共 {count} 张',{number:Math.max(0,index)+1,count:images.length}));}
  container.querySelectorAll('[data-detail-image-step]').forEach(button=>{button.disabled=index<0||(Number(button.dataset.detailImageStep)<0?index===0:index===images.length-1);});
  container.querySelectorAll('[data-image-view]').forEach(button=>{if(button.tagName==='BUTTON')button.setAttribute('aria-current',String(button.dataset.imageView===key));});
}
function showDetailImage(r,selected){
  const container=$('#modalBody [data-detail-record]');if(!container||container.dataset.detailRecord!==r.id)return;
  const path=imagePath(selected);$('#detailImageContent').innerHTML=`${imageVisual(r,selected,'',false)}<span class="image-label">${esc(imageLabel(selected,r))}</span>${imageCount(r)}`;
  const original=$('#originalImageLink');if(original){original.href=path;original.hidden=false;}
  updateImageDownload(r,path);if($('#imageAssociations'))$('#imageAssociations').innerHTML=imageAssociations(r,path,imageViewKey(selected,path));
  updateDetailGalleryState(r,selected);
}
function moveDetailImage(delta){
  const container=$('#modalBody [data-detail-record]'),r=records.find(record=>record.id===container?.dataset.detailRecord);if(!r)return;
  const images=galleryImages(r),photo=container.querySelector('#detailPhoto img'),index=detailGalleryIndex(images,photo?.dataset.imageView||'',photo?.getAttribute('src')||'');
  if(index<0||!images[index+delta])return;showDetailImage(r,images[index+delta]);
}
document.addEventListener('error',e=>{
  const el=e.target;if(!el.matches?.('img[data-gallery-record]'))return;
  const r=records.find(r=>r.id===el.dataset.galleryRecord);if(!r)return;
  const failed=new Set(JSON.parse(el.dataset.failedImages||'[]'));failed.add(el.getAttribute('src'));const detailContainer=el.closest('#detailPhoto');const small=!detailContainer;
  const next=galleryImages(r).find(i=>!failed.has(galleryImageURL(i,small))),label=(detailContainer||el.closest('.photo')||el.parentElement).querySelector('.image-label');
  el.dataset.failedImages=JSON.stringify([...failed]);
  if(next){
    const path=imagePath(next);const viewport=el.closest('.image-viewport');if(viewport)viewport.replaceWith(el);if(validImageCrop(next)){const frame=document.createElement('template');frame.innerHTML=renderImageViewport(next,'');const wrapper=frame.content.firstElementChild;el.replaceWith(wrapper);wrapper.append(el);}el.src=galleryImageURL(next,small);el.dataset.imageView=imageViewKey(next,path);if(label)label.textContent=imageLabel(next,r);
    if(detailContainer){
      updateImageDownload(r,path);
      const link=$('#originalImageLink');if(link){link.href=path;link.hidden=false;}
      if($('#imageAssociations'))$('#imageAssociations').innerHTML=imageAssociations(r,path,el.dataset.imageView);
      updateDetailGalleryState(r,next);
    }
  }else{
    el.hidden=true;if(label)label.textContent='图片暂未加载，请刷新重试';
    if(detailContainer){
      if($('#originalImageLink'))$('#originalImageLink').hidden=true;
      updateImageDownload(r,'');
      if($('#imageAssociations'))$('#imageAssociations').innerHTML='';
    }
  }
},true);
function toast(msg){$('#toast').textContent=msg;$('#toast').style.display='block';clearTimeout(toast.timer);toast.timer=setTimeout(()=>$('#toast').style.display='none',3000);}
async function api(path,data,options={}){
  const {redirectOn401=true,...requestOptions}=options;
  const request={timeoutMs:path==='/api/catalog'?60000:30000,...requestOptions,...(data===undefined?{}:{method:'POST',headers:{'Content-Type':'application/json','X-CSRF-Token':session.csrf||''},body:JSON.stringify(data)})};
  try{return await requestJSON(path,request);}catch(error){
    if(error.status===401&&redirectOn401)location.href='/login';
    throw error;
  }
}
let preferencesReady=false,preferencesLoading=null,preferencesError='';
function preferencesNotice(){return preferencesError?`<div class="note" role="status">收藏暂未载入，包材检索仍可使用。${esc(preferencesError)} <button type="button" class="btn small" data-action="retry-preferences">重试收藏</button></div>`:'';}
function syncPreferences(){
  $('#favCount').textContent=preferencesReady?prefs.favorites.length:'…';
  const notice=$('#preferencesStatus');if(notice)notice.innerHTML=preferencesNotice();
  document.querySelectorAll('button[data-favorite]').forEach(button=>{
    if(!preferencesReady)return;
    if(button.dataset.favoriteCandidates){const candidates=JSON.parse(button.dataset.favoriteCandidates);button.dataset.favorite=candidates.find(id=>prefs.favorites.includes(id))||candidates[0];}
    const selected=prefs.favorites.includes(button.dataset.favorite);
    if(button.classList.contains('favorite')){button.classList.toggle('on',selected);button.textContent=selected?'★':'☆';button.setAttribute('aria-label',(selected?'取消收藏':'收藏')+(records.find(r=>r.id===button.dataset.favorite)?.name||''));}
    else button.textContent=selected?'取消收藏':'收藏此记录';
  });
}
async function loadPreferences(){
  if(preferencesLoading)return preferencesLoading;
  preferencesReady=false;
  preferencesLoading=(async()=>{
    try{const value=await api('/api/preferences');if(!Array.isArray(value.favorites))throw Error('收藏数据格式异常，请稍后重试。');prefs=value;preferencesReady=true;preferencesError='';}
    catch(error){preferencesError=error.message;throw error;}
    finally{syncPreferences();preferencesLoading=null;}
  })();
  return preferencesLoading;
}

let productCodeIndex=new Map(),recordIdIndex=new Map();
function numberLookup(value){const key=codeKey(value);if(/^YZBC\d{6,}$/.test(key))return {active:true,record:productCodeIndex.get(key)};const record=recordIdIndex.get(normalizeSearch(value).trim());return {active:!!record,record};}
function setCatalogQuery(value){state.query=String(value??'').trim();state.page=1;const lookup=numberLookup(state.query);if(lookup.active){clearImageSearch();resetProductFilters();state.view='catalog';state.kind=session.catalogPaging?[]:[lookup.record?.kind||'package'];}}
function productLabel(r){return r.productCode||r.id;}

function displayed(){if(session.catalogPaging&&remotePage){const allowed=new Set(remotePage.matchedIds);return remotePage.pageRecordIds.map(id=>records.find(r=>r.id===id)).filter(Boolean).map(r=>{const group=productGroupIndex.get(r.id);return group?{...r,_group:group,_matchedRecords:group.records.filter(x=>allowed.has(x.id))}:r;});}return groupProducts(filtered(),productGroupIndex);}
function groupTitle(r){const group=productGroupIndex.get(r.id);return group?group.name+t(group.multiSpec?'（多规格）':'（资料已归并）'):r.name;}
function groupTitleHTML(r){const group=productGroupIndex.get(r.id);return group?sourceText(group.name)+`<span>${esc(t(group.multiSpec?'（多规格）':'（资料已归并）'))}</span>`:sourceText(r.name,'名称待补');}
function imageMappingNote(r){return productGroupIndex.get(r.id)?.imageMappingPending?`<p class="group-image-mapping-note">${t('规格见标签，图中对应待核对')}</p>`:'';}
function groupSummary(r){const group=productGroupIndex.get(r.id);return group?`<div class="group-summary"><span>${group.records.length}</span> <span>${t('条原始记录')}</span> · <span>${t('查看各规格报价')}</span></div>`:'';}
function groupCapacityTags(r){const group=productGroupIndex.get(r.id),labels=group?.specs.length?[...new Set(group.specs.map(s=>s.label))]:(group?.capacities||r._capacities).map(n=>n+'mL');return labels.map(label=>`<span class="tag" data-i18n-skip>${esc(label)}</span>`).join('');}
function filtered(){
  if(session.catalogPaging&&remotePage){const ids=new Set(remotePage.matchedIds);return records.filter(r=>ids.has(r.id));}
  let arr=state.view==='favorites'?records.filter(r=>prefs.favorites.includes(r.id)):records;
  const lookup=numberLookup(state.query),matchers=searchMatchers(state.query),words=matchers.map(m=>m.word);
  arr=arr.filter(r=>(!imageSearch.matches||imageSearch.matches.has(r.id))&&
    anySelected('kind',[r.kind])&&anySelected('section',r._sections)&&anySelected('category',[r._category])&&
    anySelected('material',r._materials)&&anySelected('capacity',r._capacities)&&
    (!picked('capacityBand').length||r._capacities.some(v=>picked('capacityBand').some(b=>inBand(v,b))))&&
    anySelected('bottle',[r.bottleType])&&anySelected('use',recordSearchUses(r))&&anySelected('quote',[quote(r)?'yes':'no'])&&
    anySelected('source',[r._sourceFile])&&(!picked('imageStatus').length||(r.kind==='package'&&anySelected('imageStatus',[productImageStatus(r)])))&&
    (lookup.active?r.id===lookup.record?.id:matchesText(r,matchers)));
  if(imageSearch.matches)return arr.sort((a,b)=>imageSearch.matches.get(a.id).rank-imageSearch.matches.get(b.id).rank);
  if(words.length){const score=r=>words.reduce((v,w)=>v+(text(r.model).toLowerCase()===w?12:0)+(r.id.toLowerCase()===w?16:0)+(r.name.toLowerCase().includes(w)?3:0),0);return arr.map(r=>({r,score:score(r)})).sort((a,b)=>b.score-a.score).map(x=>x.r);}return arr;
}
function imageSearchScope(){const s=imageSearch.status;return s?.available?`搜图范围：当前库内已索引 ${s.indexed_records||0} 条记录、${s.indexed_images||0} 张图片。`:(imageSearch.statusError||s?.message||(s?'图片索引暂不可用，可继续使用文字检索。':'正在检查库内图片索引…'));}
function imageSearchHasFilters(){return Boolean(state.query||state.view==='favorites'||facetKeys.some(key=>picked(key).length));}
function clearImageSearchFilters(){resetProductFilters();state.kind=[];state.query='';state.view='catalog';state.page=1;render();}
function imageSearchContext(){return imageSearch.matches?`<div class="image-search-context"><img src="${esc(imageSearch.preview)}" alt="本次搜图使用的图片"><div><strong>相似图片排序</strong><p>瓶型与结构优先，颜色与印刷次之。相似结果仅供选款，需核对规格与实物。</p>${imageSearchHasFilters()?'<span>当前文字和筛选仍会限制搜图结果。</span><button class="btn small" type="button" data-image-search="filters-clear">清除文字和筛选</button>':''}</div><button class="btn small" type="button" data-image-search="clear">清除搜图</button></div>`:'';}
function syncImageSearchUI(){const scope=$('#imageSearchScope');if(scope)scope.textContent=imageSearchScope();const status=$('#imageSearchStatus');if(status)status.textContent=imageSearchScope();const submit=$('#imageSearchSubmit');if(submit){submit.disabled=!imageDraft||imageSearch.busy||imageDraftPreparing||!imageSearch.status?.available;submit.textContent=t(imageSearch.busy?'正在查找相似包材…':'查找相似包材');}const busy=$('#imageSearchProgress');if(busy)busy.textContent=t(imageDraftPreparing?'正在准备图片…':imageSearch.busy?'正在查找相似包材…':'');$('#imageCropCanvas')?.toggleAttribute('inert',imageSearch.busy);for(const button of document.querySelectorAll('[data-image-search="crop-reset"],[data-image-search="crop-centre"],[data-image-search="rotate"]'))button.disabled=imageSearch.busy||imageDraftPreparing;}
async function loadImageSearchStatus(){try{imageSearch.status=await api('/api/image-search/status');imageSearch.statusError='';}catch(err){imageSearch.status=null;imageSearch.statusError='搜图服务暂不可用，可继续使用文字检索。';}syncImageSearchUI();}
function cancelImageRequest(){imageSearch.sequence++;imageSearch.controller?.abort();imageSearch.controller=null;imageSearch.busy=false;}
function clearImageSearch(){cancelImageRequest();imageRecordPins.clear();const had=imageSearch.matches!==null;imageSearch.matches=null;imageSearch.preview='';if(had&&!picked('kind').length)state.kind=['package'];state.page=1;}
function closeImageSearch(){cancelImageRequest();imageDraftSequence++;imageDraftController?.abort();imageDraftController=null;imageDraftPreparing=false;imageDraft?.selection?.dispose();imageDraft=null;$('#imageSearchModal').close();$('#imageSearchModal').innerHTML='';}
function imageSearchError(message){const el=$('#imageSearchError');if(el)el.textContent=message;}
function openImageSearch(){
  const d=$('#imageSearchModal');if($('#query'))state.query=$('#query').value;imageDraftSequence++;imageDraftController?.abort();imageDraftPreparing=false;imageDraft?.selection?.dispose();imageDraft=null;
  d.innerHTML=`<div class="dialog-head"><h2 id="imageSearchTitle">上传图片找相似</h2><button class="close" data-image-search="close" aria-label="关闭搜图">×</button></div><div class="dialog-content"><p class="sub image-search-intro">优先查找瓶型和结构相近的包材。图片中有多款产品时，可拖动框选其中一款。</p><div id="imageDropzone" class="image-dropzone"><input id="imageSearchFile" type="file" accept="image/jpeg,image/png,image/webp" hidden><button class="btn" type="button" data-image-search="choose">选择图片</button><span>或拖放到此处、直接粘贴截图</span><small>JPEG、PNG、WebP · 手机照片自动压缩 · 最大 20 MB</small></div><div id="imageCropArea" class="image-crop-area" hidden><div class="image-crop-toolbar"><span id="imageCropHint" aria-live="polite">拖动框选单个包材；不框选则使用整张图片。</span><div class="image-crop-actions"><button type="button" class="quiet" data-image-search="crop-reset">使用整张图片</button><button type="button" class="quiet" data-image-search="crop-centre">框选中间包材</button><button type="button" class="quiet" data-image-search="rotate">旋转 90°</button></div></div><div class="image-canvas-stage"><canvas id="imageCropCanvas" tabindex="0" aria-describedby="imageCropHint" aria-label="图片预览，可用鼠标、手指或方向键框选目标包材"></canvas></div></div><p id="imageSearchError" class="form-error" role="alert"></p><p id="imageSearchProgress" class="image-search-progress" role="status" aria-live="polite"></p><p id="imageSearchStatus" class="image-search-scope">${esc(imageSearchScope())}</p><p class="image-search-footnote">只检索已入库并建立索引的图片；相似结果不代表同款或尺寸相同。</p></div><div class="dialog-foot"><button class="btn" type="button" data-image-search="close">取消</button><button id="imageSearchSubmit" class="btn primary" type="button" data-image-search="submit" disabled>查找相似包材</button></div>`;
  if(!d.open)d.showModal();
  const zone=$('#imageDropzone');
  $('#imageSearchFile').addEventListener('change',e=>{const file=e.target.files?.[0];if(file)prepareImageSearchFile(file);});
  zone.addEventListener('dragover',e=>{e.preventDefault();zone.classList.add('dragging');});
  zone.addEventListener('dragleave',()=>zone.classList.remove('dragging'));
  syncImageSearchUI();loadImageSearchStatus();
}
function dropImageSearchFile(e){e.preventDefault();$('#imageDropzone')?.classList.remove('dragging');const files=e.dataTransfer?.files;if(files?.length===1)prepareImageSearchFile(files[0]);else imageSearchError('请每次选择一张图片。');}
function setImageSearchDraft(base){
  imageDraft?.selection?.dispose();const draft={base,crop:null,selection:null};imageDraft=draft;
  draft.selection=bindImageQueryCrop($('#imageCropCanvas'),base,{onChange:crop=>{
    if(imageDraft!==draft)return;draft.crop=crop;const hint=$('#imageCropHint');
    if(hint)hint.textContent=t(crop?'已框选目标包材；可重新拖动调整范围。':'不框选则使用整张图片；可用方向键调整选框，Shift＋方向键调整大小。');
  }});
  $('#imageCropArea').hidden=false;
}
async function prepareImageSearchFile(file){
  clearImageSearch();render();const seq=++imageDraftSequence;imageDraftController?.abort();imageDraftController=new AbortController();
  imageDraft?.selection?.dispose();imageDraft=null;imageDraftPreparing=true;imageSearchError('');$('#imageCropArea').hidden=true;syncImageSearchUI();
  try{
    const base=await prepareImageQuery(file,{signal:imageDraftController.signal});
    if(seq!==imageDraftSequence||!$('#imageSearchModal').open)return;
    setImageSearchDraft(base);
  }catch(err){if(seq===imageDraftSequence&&err.name!=='AbortError')imageSearchError(t(err.message||'图片准备失败，请重新选择图片。'));}
  finally{if(seq===imageDraftSequence){imageDraftPreparing=false;imageDraftController=null;syncImageSearchUI();}}
}
async function submitImageSearch(){
  if(!imageDraft||imageSearch.busy||!imageSearch.status?.available)return;
  let queryImage;try{queryImage=imageDraft.selection.dataURL();}catch(error){imageSearchError(t(error.message));return;}
  clearImageSearch();imageSearch.busy=true;imageSearch.controller=new AbortController();const seq=imageSearch.sequence;imageSearchError('');syncImageSearchUI();render();
  try{
    const result=await api('/api/image-search',{image:queryImage},{signal:imageSearch.controller.signal,timeoutMs:60000});
    if(seq!==imageSearch.sequence)return;
    if(!Array.isArray(result.matches))throw Error('搜图结果暂不可用，请重试。');
    const candidates=boundedImageMatches(result.matches);
    for(const item of candidates)imageRecordPins.add(item.record_id);
    if(session.catalogPaging)await ensureRecords(candidates.map(m=>m.record_id),{signal:imageSearch.controller.signal});if(seq!==imageSearch.sequence)return;const known=new Map(records.map(r=>[r.id,r])),matches=new Map();
    candidates.forEach((m,rank)=>{if(known.has(m.record_id)&&!matches.has(m.record_id)&&typeof m.image_path==='string'&&matchedImage(known.get(m.record_id),m.image_path))matches.set(m.record_id,{...m,rank});});
    imageSearch.matches=matches;imageSearch.preview=queryImage;state.kind=[];imageSearch.status={available:true,indexed_images:result.indexed_images,indexed_records:result.indexed_records};state.page=1;closeImageSearch();render();
    toast(matches.size?'已按图片相似程度排列，可继续筛选。':t('未找到相似图片，请框选目标包材或调整拍摄角度后重试。'));
  }catch(err){if(seq===imageSearch.sequence&&err.name!=='AbortError'){imageRecordPins.clear();imageSearch.matches=null;imageSearch.preview='';imageSearchError(err.code==='timeout'?t('搜图请求超时，请稍后重试或框选目标包材。'):err.status===429?t('搜图服务繁忙，请稍后重试。'):err.message||'搜图失败，请稍后重试。');render();}}
  finally{if(seq===imageSearch.sequence){imageSearch.busy=false;imageSearch.controller=null;syncImageSearchUI();}}
}
document.addEventListener('click',e=>{const b=e.target.closest('[data-image-search]');if(!b)return;switch(b.dataset.imageSearch){case 'open':openImageSearch();break;case 'close':closeImageSearch();break;case 'choose':$('#imageSearchFile').value='';$('#imageSearchFile').click();break;case 'clear':clearImageSearch();render();break;case 'filters-clear':clearImageSearchFilters();break;case 'crop-reset':if(imageDraft&&!imageSearch.busy){imageDraft.selection.reset();imageSearchError('');}break;case 'crop-centre':if(imageDraft&&!imageSearch.busy){imageDraft.selection.centre();imageSearchError('');}break;case 'rotate':if(imageDraft&&!imageSearch.busy){setImageSearchDraft(rotateImageQuery(imageDraft.base));imageSearchError('');}break;case 'submit':submitImageSearch();break;}});
$('#imageSearchModal').addEventListener('cancel',e=>{e.preventDefault();closeImageSearch();});
$('#imageSearchModal').addEventListener('dragover',e=>e.preventDefault());
$('#imageSearchModal').addEventListener('drop',dropImageSearchFile);
document.addEventListener('paste',e=>{if(!$('#imageSearchModal').open)return;const files=[...(e.clipboardData?.items||[])].filter(i=>i.kind==='file').map(i=>i.getAsFile()).filter(Boolean);if(files.length){e.preventDefault();if(files.length===1)prepareImageSearchFile(files[0]);else imageSearchError('请每次粘贴一张图片。');}});
function title(name,sub,actions=''){return `<div class="head"><div><div class="eyebrow">${esc(catalog.settings?.englishName||'YUANZE MATERIAL LIBRARY')}</div><h1>${name}</h1><p class="sub">${sub}</p></div><div class="toolbar">${actions}</div></div>`;}
const revealSeen=new Set();let revealObserver=null;const revealAnimations=new Set();
const reduceMotion=window.matchMedia?.('(prefers-reduced-motion: reduce)');
reduceMotion?.addEventListener?.('change',()=>{if(reduceMotion.matches){revealObserver?.disconnect();for(const animation of revealAnimations)animation.cancel();revealAnimations.clear();}});
function setupReveal(){
  revealObserver?.disconnect();
  if(reduceMotion?.matches||typeof IntersectionObserver==='undefined')return;
  revealObserver=new IntersectionObserver(entries=>{
    let order=0;
    for(const entry of entries){if(!entry.isIntersecting)continue;const el=entry.target;revealObserver.unobserve(el);const key=el.dataset.revealKey;
      if(revealSeen.has(key)||typeof el.animate!=='function')continue;revealSeen.add(key);
      const animation=el.animate([{opacity:.45,transform:'translateY(15px)'},{opacity:1,transform:'translateY(0)'}],{duration:520,delay:Math.min(order++*45,180),easing:'cubic-bezier(.2,.7,.2,1)'});
      revealAnimations.add(animation);animation.finished.then(()=>revealAnimations.delete(animation),()=>revealAnimations.delete(animation));
    }
  },{threshold:.08});
  document.querySelectorAll('#main .showroom-hero,#main .stat,#main .filters,#main .card,#main .section-choice,#main .section-empty').forEach((el,n)=>{
    const id=el.querySelector('[data-record-id]')?.dataset.recordId;
    el.dataset.revealKey=id?'product:'+id:state.view+':'+el.className+':'+n;
    el.classList.add('reveal');revealObserver.observe(el);
  });
}
let scrollFrame=0;
window.addEventListener('scroll',()=>{if(scrollFrame)return;scrollFrame=requestAnimationFrame(()=>{document.body.classList.toggle('has-scrolled',window.scrollY>20);scrollFrame=0;});},{passive:true});
function showroomHero(){
  if(state.view!=='catalog'||state.query||picked('kind').length!==1||!picked('kind').includes('package')||picked('section').length||imageSearch.matches)return '';
  const preferred=['MAT-OCR-PDF11-P0004-H2-1','MAT-OCR-PDF11-P0004-H3-1','MAT-OCR-PDF11-P0004-H5-1'];
  const chosen=preferred.map(id=>records.find(r=>r.id===id&&primaryImage(r))).filter(Boolean);
  return `<section class="showroom-hero" aria-label="源泽包材展示厅"><div class="showroom-copy"><span class="showroom-kicker">YUANZE · PACKAGING COLLECTION</span><h2 class="showroom-title">为每一种配方，<br>找到合适的包装。</h2><p class="showroom-description">按材质、容量与瓶型，浏览公司包材资料。</p><div class="showroom-actions"><button type="button" class="btn primary" data-action="browse-materials">开始选型 ↓</button><button type="button" class="btn" data-section="body-head">身体/头部选型 ↗</button></div></div><div class="showroom-visual">${chosen.map(r=>`<button type="button" class="showroom-object" data-detail="${esc(r.id)}" aria-label="查看${esc(r.name)}"><img src="${esc(thumbnailURL(imagePath(primaryImage(r))))}" data-source-alt alt="${esc(r.name)}"><span><span data-i18n-skip>${esc(r.productCode||r.name)}</span></span></button>`).join('')}<span class="showroom-visual-note">FROM OUR MATERIAL LIBRARY</span></div></section>`;
}
function render(){
  if(session.catalogPaging&&['catalog','favorites'].includes(state.view)&&remoteKey!==remoteParams().toString()){loadRemotePage().catch(()=>{});return;}
  const filterMemory=new Map([...document.querySelectorAll('.multi-filter')].map(el=>[el.dataset.facet,{open:el.open,search:el.querySelector('.multi-option-search').value,scroll:el.querySelector('.multi-options').scrollTop}]));const active=document.activeElement,focusFacet=active?.closest('.multi-filter')?.dataset.facet,focusValue=active?.dataset.filter?active.value:null,focusSearch=active?.matches('.multi-option-search');
  closeMobileSidebar();
  $('#crumb').textContent='工作空间 / '+viewNames[state.view];
  document.querySelectorAll('[data-view]').forEach(b=>b.classList.toggle('active',b.dataset.view===state.view));
  document.querySelectorAll('nav [data-view]').forEach(b=>{if(b.dataset.view===state.view)b.setAttribute('aria-current','page');else b.removeAttribute('aria-current');});
  document.querySelectorAll('[data-section]').forEach(b=>{const active=picked('section').includes(b.dataset.section);b.classList.toggle('active',active);b.setAttribute('aria-pressed',String(active));});
  $('#main').innerHTML='<div id="preferencesStatus">'+preferencesNotice()+'</div>'+({catalog:catalogView,favorites:catalogView,plans:plansView,samples:samplesView,sources:sourcesView}[state.view]||catalogView)();
  for(const el of document.querySelectorAll('.multi-filter')){const previous=filterMemory.get(el.dataset.facet);if(previous){el.open=previous.open;el.querySelector('.multi-option-search').value=previous.search;filterOptions(el.querySelector('.multi-option-search'));el.querySelector('.multi-options').scrollTop=previous.scroll;}}if(focusFacet){const panel=[...document.querySelectorAll('.multi-filter')].find(el=>el.dataset.facet===focusFacet);const target=focusSearch?panel?.querySelector('.multi-option-search'):focusValue!==null?[...(panel?.querySelectorAll('[data-filter]')||[])].find(el=>el.value===focusValue):panel?.querySelector('summary');target?.focus({preventScroll:true});}
  syncPreferences();
  syncManagementUI();
  setupReveal();
}
const capacityBands=[['lt50','不足 50mL'],['50-150','50 至不足 150mL'],['150-250','150 至不足 250mL'],['250-350','250 至不足 350mL'],['350-500','350 至不足 500mL'],['500-1000','500 至不足 1000mL'],['gte1000','1000mL 及以上']];
function facetButton(key,value,label,count,selected){return `<button type="button" data-side-${key}="${esc(value)}" class="side-facet ${selected?'active':''}" aria-pressed="${selected?'true':'false'}" title="${esc(label)}"><span>${esc(label)}</span><small>${count}</small></button>`;}

function resetProductFilters(){for(const key of facetKeys)if(key!=='kind')state[key]=[];state.page=1;}
function switchKind(kind){clearImageSearch();resetProductFilters();state.kind=kind?[kind]:[];state.page=1;}
function beginProductFacet(){state.view='catalog';state.kind=['package'];}
function facetLabel(key,value){if(key==='kind')return kindNames[value]||value;if(key==='section')return sectionNames[value]||value;if(key==='capacity')return value+' mL';if(key==='capacityBand')return capacityBands.find(([k])=>k===value)?.[1]||value;if(key==='quote')return value==='yes'?'有报价原文':'待补报价';if(key==='imageStatus')return imageStatusNames[value]||value;return value;}
function activeFilters(){const labels={kind:'资料',section:'分区',category:'类别',material:'材质',capacity:'规格',capacityBand:'容量区间',bottle:'瓶型',use:'用途',quote:'报价',source:'来源',imageStatus:'图片状态'};const active=Object.entries(labels).flatMap(([key,label])=>picked(key).map(value=>({key,label,value})));return active.length?`<div class="active-filters" aria-label="已选筛选">${active.map(({key,label,value})=>`<button type="button" class="filter-chip" data-clear-filter="${key}" data-filter-value="${esc(value)}" title="移除${esc(label)}：${esc(facetLabel(key,value))}">${esc(label)}：${esc(facetLabel(key,value))} <span aria-hidden="true">×</span></button>`).join('')}</div>`:'';}
function multiFilter(key,label,options,placeholder){
  const values=[...new Set([...options.map(v=>String(Array.isArray(v)?v[0]:v)),...picked(key)])];
  const names=new Map(options.map(v=>Array.isArray(v)?[String(v[0]),v[1]]:[String(v),String(v)]));
  const selected=picked(key),summary=selected.length?selected.map(v=>names.get(v)||facetLabel(key,v)).join('、'):placeholder;
  return `<div class="filter-field"><span class="filter-field-label" id="facet-label-${key}">${esc(label)}</span><details class="multi-filter" data-facet="${key}"><summary aria-labelledby="facet-label-${key} facet-summary-${key}"><span class="multi-summary" id="facet-summary-${key}" title="${esc(summary)}">${esc(summary)}</span>${selected.length?`<span class="multi-count">${selected.length}</span>`:''}</summary><div class="multi-menu"><input class="multi-option-search" type="search" aria-label="筛选${esc(label)}选项" placeholder="查找${esc(label)}…"><button type="button" class="quiet" data-clear-facet="${key}">清空本项</button><div class="multi-options" role="group" aria-label="${esc(label)}，可多选">${values.map(v=>`<label class="multi-option"><input type="checkbox" data-filter="${key}" value="${esc(v)}" ${selected.includes(v)?'checked':''}><span class="label">${esc(names.get(v)||facetLabel(key,v))}</span></label>`).join('')}</div><p class="multi-empty" hidden>没有匹配的选项</p></div></details></div>`;
}
function refreshFacet(key,value){
  const old=[...document.querySelectorAll('.multi-filter')].find(el=>el.dataset.facet===key),search=old?.querySelector('.multi-option-search')?.value||'',scroll=old?.querySelector('.multi-options')?.scrollTop||0;
  render();const panel=[...document.querySelectorAll('.multi-filter')].find(el=>el.dataset.facet===key);if(!panel)return;
  panel.open=true;const input=panel.querySelector('.multi-option-search');input.value=search;filterOptions(input);panel.querySelector('.multi-options').scrollTop=scroll;
  const focus=[...panel.querySelectorAll('[data-filter]')].find(el=>el.value===value)||panel.querySelector('[data-clear-facet]');focus?.focus({preventScroll:true});
}
function filterOptions(input){const panel=input.closest('.multi-filter'),q=normalizeSearch(input.value);let count=0;for(const option of panel.querySelectorAll('.multi-option')){option.hidden=!normalizeSearch(option.textContent).includes(q);if(!option.hidden)count++;}panel.querySelector('.multi-empty').hidden=count>0;}
document.addEventListener('input',e=>{if(e.target.id==='query')state.query=e.target.value;if(e.target.matches('.multi-option-search'))filterOptions(e.target);});
document.addEventListener('click',e=>{const summary=e.target.closest('.multi-filter summary');for(const panel of document.querySelectorAll('.multi-filter[open]'))if((summary&&panel!==summary.parentElement)||!e.target.closest('.multi-filter'))panel.open=false;});
document.addEventListener('keydown',e=>{if(e.key==='Escape'){const panel=e.target.closest('.multi-filter[open]');if(panel){panel.open=false;panel.querySelector('summary').focus();e.stopPropagation();}}});

const pageSizes=[20,40,80];
function paginationItems(page,total){const visible=new Set([1,total]);for(let n=Math.max(1,page-1);n<=Math.min(total,page+1);n++)visible.add(n);if(page<=3)for(let n=1;n<=Math.min(5,total);n++)visible.add(n);if(page>=total-2)for(let n=Math.max(1,total-4);n<=total;n++)visible.add(n);const items=[];for(const n of [...visible].sort((a,b)=>a-b)){const previous=items.at(-1);if(typeof previous==='number'&&n-previous===2)items.push(previous+1);else if(typeof previous==='number'&&n-previous>2)items.push('gap');items.push(n);}return items;}
function catalogPagination(count){const total=Math.max(1,Math.ceil(count/state.pageSize)),page=state.page;return `<div class="pagination" role="navigation" aria-label="产品列表分页"><div class="page-primary"><button type="button" class="btn small page-step" data-page="${page-1}" data-page-control="prev" ${page===1?'disabled':''} aria-label="上一页">‹ 上一页</button><form id="pageJumpForm" class="page-jump" novalidate><label for="pageJump">页码</label><input id="pageJump" name="page" type="number" inputmode="numeric" min="1" max="${total}" step="1" value="${page}" aria-label="输入要跳转的页码" ${total===1?'disabled':''}><span class="page-total">/ ${total}</span><button class="btn small" type="submit" ${total===1?'disabled':''}>跳转</button></form><button type="button" class="btn small page-step" data-page="${page+1}" data-page-control="next" ${page===total?'disabled':''} aria-label="下一页">下一页 ›</button></div><div class="page-secondary"><div class="page-buttons">${paginationItems(page,total).map(n=>n==='gap'?'<span class="page-gap" aria-hidden="true">…</span>':`<button type="button" class="btn small page-number ${n===page?'current':''}" data-page="${n}" aria-label="第 ${n} 页" ${n===page?'aria-current="page"':''}>${n}</button>`).join('')}</div><label class="page-size-label">每页 <select id="pageSize" aria-label="每页显示条数" ${!count?'disabled':''}>${pageSizes.map(n=>`<option value="${n}" ${n===state.pageSize?'selected':''}>${n} 条</option>`).join('')}</select></label></div></div>`;}
function catalogResults(a){const count=session.catalogPaging?remotePage.total:a.length,total=Math.max(1,Math.ceil(count/state.pageSize));state.page=Math.max(1,Math.min(state.page,total));const start=(state.page-1)*state.pageSize,rows=session.catalogPaging?a:a.slice(start,start+state.pageSize);return `<div class="results-top"><div><span>找到 <b>${count}</b> <span>${t('款资料')}</span> <span class="muted group-record-count">（${session.catalogPaging?remotePage.matchingRecords:a.reduce((n,r)=>n+(r._matchedRecords?.length||1),0)} <span>${t('条原始记录')}</span>）</span> <span class="muted"> · ${picked('kind').length?picked('kind').map(k=>kindNames[k]).join('、'):'全部资料'}${imageSearch.matches?' · 相似图片排序':''}</span></span><span class="page-range" role="status" aria-live="polite" aria-atomic="true">${a.length?`第 ${start+1}–${Math.min(start+state.pageSize,count)} 条 · 第 ${state.page} / ${total} 页`:'暂无记录'}</span></div><div class="toolbar"><span class="tag orange">来源资料，规格与报价需复核</span><button class="quiet" data-action="layout">${state.table?'切换图库':'切换表格'}</button></div></div><div id="catalogPageContent">${a.length?(state.table?table(rows):`<div class="catalog">${rows.map(card).join('')}</div>`):'<div class="empty">没有符合这些条件的记录。可清空或减少筛选条件。</div>'}</div>${catalogPagination(count)}`;}
function updateCatalogPage(value,{size=state.pageSize,focus='current'}={}){const input=String(value??'').trim();if(!/^\d+$/.test(input)||!Number.isSafeInteger(Number(input))){toast('请输入有效的整数页码');$('#pageJump')?.focus({preventScroll:true});return;}if(!pageSizes.includes(size))return;const a=displayed(),total=Math.max(1,Math.ceil((session.catalogPaging?remotePage.total:a.length)/size)),page=Math.max(1,Math.min(Number(input),total)),oldPage=state.page,oldSize=state.pageSize,region=$('#catalogResults');if(!region)return;const headerOffset=(document.querySelector('header')?.getBoundingClientRect().height||0)+20,scrollTop=window.scrollY+region.getBoundingClientRect().top-headerOffset,shouldScroll=region.getBoundingClientRect().top<headerOffset;if(Number(input)!==page)toast(`页码已调整到第 ${page} 页`);if(oldPage===page&&oldSize===size){if($('#pageJump'))$('#pageJump').value=page;return;}state.pageSize=size;state.page=page;if(session.catalogPaging){loadRemotePage().then(()=>{const current=$('#catalogResults');if(!current)return;const reduced=reduceMotion?.matches;const content=$('#catalogPageContent');if(content&&!reduced){content.classList.add('page-enter');content.style.setProperty('--page-shift',page<oldPage?'-7px':'7px');}const target=focus==='size'?$('#pageSize'):focus==='jump'?$('#pageJump'):current.querySelector(`[data-page-control="${focus}"]:not(:disabled)`)||current.querySelector('[aria-current="page"]');target?.focus({preventScroll:true});if(shouldScroll)window.scrollTo({top:Math.max(0,scrollTop),behavior:reduced?'auto':'smooth'});}).catch(()=>{});return;}region.innerHTML=catalogResults(a);setupReveal();const reduced=window.matchMedia?.('(prefers-reduced-motion: reduce)').matches;if(!reduced){const content=$('#catalogPageContent');content.classList.add('page-enter');content.style.setProperty('--page-shift',page<oldPage?'-7px':'7px');}const target=focus==='size'?$('#pageSize'):focus==='jump'?$('#pageJump'):region.querySelector(`[data-page-control="${focus}"]:not(:disabled)`)||region.querySelector('[aria-current="page"]');target?.focus({preventScroll:true});if(shouldScroll)window.scrollTo({top:Math.max(0,scrollTop),behavior:reduced?'auto':'smooth'});}

function catalogView(){
  const a=displayed();state.page=Math.max(1,Math.min(state.page,Math.ceil((session.catalogPaging?remotePage.total:a.length)/state.pageSize)||1));
  const categories=session.catalogPaging?remotePage.facets.categories:[...new Set(records.map(r=>r._category))].sort(),mats=session.catalogPaging?remotePage.facets.materials:[...new Set(records.flatMap(r=>r._materials))].sort();
  const caps=session.catalogPaging?remotePage.facets.capacities:[...new Set(records.filter(r=>r.kind==='package').flatMap(r=>r._capacities))].filter(v=>v>0).sort((a,b)=>a-b);
  const actions=`<button class="btn" data-action="export">导出当前列表</button>${canManage()?'<button type="button" class="btn primary" data-action="new-product">＋ 新增产品</button>':''}`;
  return title(state.view==='favorites'?'我的收藏':esc(catalog.settings?.catalogTitle||'包材选型库'),esc(catalog.settings?.catalogSubtitle||'搜索产品名称、用途或规格，查找合适的包材。'),actions)
    +(catalog.settings?.announcement?`<div class="note" style="margin-bottom:16px" data-i18n-skip>${esc(catalog.settings.announcement)}</div>`:'')
    +`<section class="filters" aria-label="检索条件"><form id="searchForm"><div class="search-row"><div class="search-box"><span>⌕</span><input id="query" name="query" aria-label="检索包材" placeholder="搜索产品编号（如 YZ-BC-000001）、名称、材质或规格" value="${esc(state.query)}"></div><button class="btn primary" type="submit">搜索</button><button class="btn image-search-launch" type="button" data-image-search="open">上传图片找相似</button><button class="btn" type="button" data-action="toggle-filters" aria-expanded="${state.filtersOpen}" aria-controls="catalogFilterDetails">筛选条件</button><button class="btn" type="button" data-action="reset">重置</button></div></form><p id="imageSearchScope" class="image-search-scope">${esc(imageSearchScope())}</p>${imageSearchContext()}
      <div id="catalogFilterDetails" ${state.filtersOpen?'':'hidden'}><p class="filter-help">筛选项均可多选：同一项满足任一条件，不同项同时满足。用途包含资料标注与单独标明的结构参考，同一包材可匹配多个用途；未明确用途的包材可在全部资料中查找。</p><div class="filter-grid">
      ${multiFilter('kind','资料类型',Object.entries(kindNames),'全部资料')}${multiFilter('section','护理部位',Object.entries(sectionNames),'不限部位')}${multiFilter('category','包材类型',categories,'全部类型')}${multiFilter('material','材质',mats,'不限材质')}${multiFilter('capacity','规格',caps.map(v=>[String(v),v+' mL']),'不限规格')}${multiFilter('capacityBand','容量区间',capacityBands,'不限容量区间')}${multiFilter('bottle','瓶型',(session.catalogPaging?remotePage.facets.bottles:[...new Set(records.map(r=>r.bottleType).filter(Boolean))].sort()),'不限瓶型')}${multiFilter('use','用途',session.catalogPaging?remotePage.facets.uses:usageOptions(records),'不限用途')}${multiFilter('quote','报价资料',[['yes','有报价原文'],['no','待补报价']],'全部状态')}${multiFilter('imageStatus','图片状态',Object.entries(imageStatusNames),'全部图片状态')}${multiFilter('source','来源图册',(session.catalogPaging?remotePage.facets.sources:[...new Set(records.map(r=>r._sourceFile).filter(Boolean))].sort()),'全部来源')}
      </div></div>${activeFilters()}</section><section id="catalogResults" aria-label="筛选结果">${catalogResults(a)}</section>${selectionBar()}`;
}
function referenceUseTag(r){const confirmed=recordUses(r),labels=recordReferenceUses(r).filter(value=>!confirmed.includes(value));return labels.length?`<span class="reference-use-tag" title="${esc(labels.map(value=>t(value)).join(' / '))}">${esc(t('参考用途'))} · ${esc(labels.slice(0,2).map(value=>t(value)).join(' / '))}${labels.length>2?' +'+(labels.length-2):''}</span>`:'';}
function card(r){return `<article class="card ${r.kind==='source_page'?'source-card':''}"><button class="photo" data-detail="${esc(r.id)}" aria-label="查看${esc(r.name)}">${image(r)}</button>${imageMappingNote(r)}<div class="card-body"><span class="record-code" data-record-id="${esc(r.id)}" data-product-code="${esc(r.productCode||'')}">${r.productCode?'产品编号 · ':'来源编号 · '}${esc(productLabel(r))}</span><button class="card-title" data-detail="${esc(r.id)}">${groupTitleHTML(r)}</button>${groupSummary(r)}<div class="tags"><span class="tag blue">${esc(r._category)}</span>${r.provenance?.extraction==='ocr'?'<span class="tag orange">OCR待核对</span>':''}${r._materials.slice(0,2).map(x=>`<span class="tag">${esc(x)}</span>`).join('')}${groupCapacityTags(r)}${referenceUseTag(r)}</div>${r._group?`<div class="group-current-record"><span>${t('当前记录')}</span> · <span data-i18n-skip>${esc(groupRecordSpec(r,productGroupIndex)||productLabel(r))}</span></div>`:''}<div class="quote-preview" data-i18n-skip>${esc(r.kind==='source_page'?'原页图片与识别文字，具体产品待核对':r.kind==='process_rule'?(quote(r)||'通用参考规则，未绑定具体产品'):(quote(r)||'报价待补'))}</div><span class="muted" style="font-size:12px" data-i18n-skip>${esc((r.kind==='source_page'?r._sourceFile:supplier(r)).slice(0,70))}</span></div><div class="card-foot">${canManage()?`<button type="button" class="quiet catalog-card-edit" data-edit-record="${esc(r.id)}">编辑资料</button>`:''}<label class="select-label"><input type="checkbox" data-select="${esc(r.id)}" ${state.selected.includes(r.id)?'checked':''}>加入对比</label><button class="favorite ${prefs.favorites.includes(r.id)?'on':''}" aria-label="${prefs.favorites.includes(r.id)?'取消收藏':'收藏'}${esc(r.name)}" data-favorite-candidates="${esc(JSON.stringify((r._matchedRecords||[r]).map(member=>member.id)))}" data-favorite="${esc(r.id)}">${prefs.favorites.includes(r.id)?'★':'☆'}</button></div></article>`;}
function table(a){return `<div class="panel table-wrap"><table><thead><tr><th>选择</th><th>产品编号／名称与来源</th><th>类型／材质</th><th>报价原文</th><th>供应商</th><th></th></tr></thead><tbody>${a.map(r=>`<tr><td><input aria-label="选择${esc(r.name)}" type="checkbox" data-select="${esc(r.id)}" ${state.selected.includes(r.id)?'checked':''}></td><td><div class="record-code">${esc(productLabel(r))}</div><button class="quiet" data-detail="${esc(r.id)}">${groupTitleHTML(r)}</button>${groupSummary(r)}<div class="source-line">${esc(source(r))}</div></td><td>${esc(r._category)}<br>${esc(r._materials.join(' / ')||'待补')}</td><td class="raw" style="max-width:320px">${esc(quote(r)||'待询价')}</td><td data-i18n-skip>${esc(supplier(r))}</td><td><button class="quiet" data-detail="${esc(r.id)}">详情</button>${canManage()?`<button type="button" class="quiet" data-edit-record="${esc(r.id)}">编辑资料</button>`:''}</td></tr>`).join('')}</tbody></table></div>`;}
function selectionBar(){return state.selected.length?`<div class="selection-bar"><span>已选 <b>${state.selected.length}</b> 项</span><div><button class="btn" data-action="clear-selected">清空</button><button class="btn" data-action="save-plan">保存方案</button><button class="btn primary" data-action="compare">查看对比</button></div></div>`:'';}
function modal(title,body,foot=''){if(catalogEditor?.isOpen()){if(!catalogEditor.canClose())return;disposeCatalogEditor();}const d=$('#modal');$('#modalBody').innerHTML=`<div class="dialog-head"><h2${records.some(r=>r.name===title)||plans.some(p=>p.title===title)?' data-i18n-skip':''}>${esc(title)}</h2><button class="close" data-close aria-label="关闭对话框">×</button></div><div class="dialog-content">${body}</div>${foot?`<div class="dialog-foot">${foot}</div>`:''}`;if(!d.open)d.showModal();}
function facts(rows){return `<dl class="facts">${rows.map(([k,v])=>`<div class="fact"><dt>${esc(k)}</dt><dd>${v?(['材质','瓶型','用途','类别','类型'].includes(k)?esc(text(v)):`<span data-i18n-skip>${esc(text(v))}</span>`):'待补'}</dd></div>`).join('')}</dl>`;}
function linkedProducts(r){if(r.kind!=='source_page'||!Array.isArray(r.rawCells?.linkedRecordIds))return '';const ids=new Set(r.rawCells.linkedRecordIds),linked=records.filter(item=>ids.has(item.id));return linked.length?`<div class="section-label">本页已整理产品（${linked.length}）</div><div class="linked-products">${linked.map(item=>`<button class="btn small" data-detail="${esc(item.id)}"><span data-i18n-skip>${esc(item.name||item.id)}</span></button>`).join('')}</div>`:'<p class="note">本页暂无可展示的独立产品记录，可先参考原图并核对型号与规格。</p>';}
function meaningful(value){const v=text(value).trim();return /^(?:[/／—–-]+|暂无|无|待补|待确认|未填写|未注明)$/.test(v)?'':v;}
function specificationDetails(r){
  const seenDetails=new Set();const allRows=(r.productDetails||[]).filter(d=>{if(!d?.label||!meaningful(d.value))return false;const key=d.label+'|'+d.value;if(seenDetails.has(key))return false;seenDetails.add(key);return true;});
  const pricedLabels=new Set(['历史工艺费用及条件','税运条件','打样费用及退款条件','裸瓶报价','泵头报价','瓶身报价','模具费用及条件','内塞报价','盖子报价','旋盖报价']);
  const rows=allRows.filter(d=>!pricedLabels.has(d.label));
  const evidence=allRows.filter(d=>d.evidence);
  return `<section class="product-specs"><h3 class="spec-section-title">产品细则</h3>${facts([['产品编号',r.productCode],['型号',r.model],['材质',(r.materials||[]).join(' / ')],['标称容量',r.specificationOverride?capacities(r).map(v=>v+' mL').join(' / '):(r.capacityMl==null?'':r.capacityMl+' mL')],['瓶型',r.bottleType],['系列',r.series],['资料标注用途',recordUses(r).join(' / ')],['产品说明',r.description]])}${rows.length?`<h3 class="spec-section-title">补充规格</h3><dl class="spec-detail-grid">${rows.map(d=>`<div><dt>${esc(d.label)}</dt><dd><span data-i18n-skip>${esc(d.value)}</span></dd></div>`).join('')}</dl>`:''}<p class="spec-price-note">历史询价资料，使用前请复核数量、税运与报价有效期。</p>${facts([['供应商',r.supplierRaw],['联系方式',r.contactRaw]])}${evidence.length?`<details class="source-disclosure"><summary>查看细则整理依据</summary>${evidence.map(d=>`<div class="spec-evidence"><strong>${esc(d.label)}</strong><p class="raw"><span data-i18n-skip>${esc(d.evidence)}</span></p></div>`).join('')}</details>`:''}</section>`;
}
function groupSelector(r){const group=productGroupIndex.get(r.id);if(!group)return '';return `<section class="group-selector" aria-label="${esc(t('同款规格与报价'))}"><h3>${t('同款规格与报价')}</h3><p>${t('选择规格或来源记录，查看对应报价。')}</p><div class="group-options">${group.records.map(member=>`<button type="button" class="group-option ${member.id===r.id?'active':''}" data-detail="${esc(member.id)}" aria-pressed="${member.id===r.id}"><strong data-i18n-skip>${esc(groupRecordSpec(member,productGroupIndex)||member.name)}</strong><span data-i18n-skip>${esc(productLabel(member))}</span><small data-i18n-skip>${esc(supplier(member))}</small></button>`).join('')}</div></section>`;}
function imageAssociations(r,path,viewKey){const group=productGroupIndex.get(r.id);if(!group)return '';const chosen=galleryImages(r).find(i=>viewKey?(imageViewKey(i,imagePath(i))===viewKey||(!viewKey.includes('#view=')&&!validImageCrop(i)&&i._groupPaths?.includes(path))):(imagePath(i)===path||i._groupPaths?.includes(path)));if(!chosen)return '';if(!chosen._groupSources.length)return `<span>${esc(imageLabel(chosen,r))}</span>`;const owners=[...new Set(chosen._groupSources.map(s=>s.recordId))].map(id=>records.find(record=>record.id===id)).filter(Boolean);return `<details><summary>${t('同款图片关联来源')} · ${owners.length}</summary>${owners.map(owner=>`<div class="group-image-source"><button type="button" class="quiet" data-detail="${esc(owner.id)}"><span data-i18n-skip>${esc(productLabel(owner))} · ${esc(groupRecordSpec(owner,productGroupIndex)||owner.name)}</span></button><span data-i18n-skip>${esc(source(owner))}</span></div>`).join('')}</details>`;}
function detail(id){
  const focusedSpec=document.activeElement?.closest('.group-option')?.dataset.detail;
  disposeDetailView?.();disposeDetailView=null;
  if(catalogEditor?.isOpen()&&!catalogEditor.canClose())return;
  disposeCatalogEditor();
  const r=records.find(r=>r.id===id);if(!r)return;const shown=galleryImage(r);
  const nonPackageFacts=facts([['资料编号',r.id],['系列',r.series],['型号',r.model],['瓶型',r.bottleType],['材质',(r.materials||[]).join(' / ')],['标称容量',r.specificationOverride?capacities(r).map(v=>v+' mL').join(' / '):(r.capacityMl==null?'':r.capacityMl+' mL')],['资料标注用途',recordUses(r).join(' / ')],['产品说明',r.description],['供应商',r.supplierRaw],['联系方式',r.contactRaw]]);
  const original=`${facts([['材料原文',r.materialRaw],['规格原文',r.specificationRaw],['供应商地址',r.addressRaw],['工艺原文',r.processRaw]])}${quoteDetails(r)}${extraDetails(r)}`;
  modal(groupTitle(r)||'询价记录',`<div class="detail-grid ${r.kind==='package'?'pd-layout':''}" data-detail-record="${esc(r.id)}"><div class="detail-visual"><div class="detail-photo" id="detailPhoto"><div id="detailImageContent" class="detail-image-content">${image(r,'',false)}</div>${detailGalleryControls(r)}</div>${detailGalleryStatus(r)}${imageMappingNote(r)}<a id="originalImageLink" class="quiet original-image-link" ${shown?`href="${esc(imagePath(shown))}"`:'hidden'} target="_blank" rel="noopener">查看当前原图 ↗</a><a id="downloadImageLink" class="btn image-download" ${shown?`href="${esc(imageDownload(r,imagePath(shown)).url)}" download="${esc(imageDownload(r,imagePath(shown)).filename)}"`:'hidden'}>下载图片</a><div id="imageAssociations" class="group-image-associations">${shown?imageAssociations(r,imagePath(shown),imageViewKey(shown,imagePath(shown))):''}</div>${imageThumbnails(r)}<div class="source-line">${esc(source(r))}<br><span data-i18n-skip>${esc(r.id)}</span></div></div><div><div class="tags"><span class="tag blue">${esc(kindNames[r.kind]||'待分类')}</span><span class="tag orange">${esc(r.kind==='source_page'?'原页线索 · 请对照型号与规格':r.provenance?.extraction==='ocr'?'OCR 提取 · 待人工核对':r.kind==='process_rule'?'独立参考规则':'历史资料 · 有效性待复核')}</span></div>${groupSelector(r)}${r.kind==='package'?compactDetail(r,catalog.settings,groupRecordSpec(r,productGroupIndex)):`${renderPricing(r)}${nonPackageFacts}${original}`}${r.kind==='package'?`<details class="source-disclosure"><summary>内部资料与原始报价</summary>${facts([['供应商',r.supplierRaw],['联系方式',r.contactRaw],['型号',r.model],['系列',r.series],['产品说明',r.description]])}${renderPricing(r)}${original}${(r.productDetails||[]).length?`<dl class="spec-detail-grid">${r.productDetails.map(d=>`<div><dt>${esc(d.label)}</dt><dd data-i18n-skip>${esc(d.value)}</dd></div>`).join('')}</dl>`:''}${catalog.settings?.processReference?`<p class="raw" data-i18n-skip>${esc(catalog.settings.processReference)}</p>`:''}</details>`:''}${r.uncertainties?.length?`<details class="source-disclosure"><summary>待确认事项</summary><div class="note" data-i18n-skip>${esc(r.uncertainties.map(text).join('；'))}</div></details>`:''}${linkedProducts(r)}<div class="detail-actions"><button class="btn" data-favorite="${esc(r.id)}">${prefs.favorites.includes(r.id)?'取消收藏':'收藏此记录'}</button>${canManage()?`<button type="button" class="btn primary" data-edit-record="${esc(r.id)}">编辑资料</button>`:''}</div></div></div><details class="source-disclosure"><summary>查看原始来源字段</summary><div class="table-wrap"><table><tbody>${Object.entries(r.rawCells||{}).map(([k,v])=>`<tr><th>${esc(k)}</th><td class="raw">${esc(text(v))}</td></tr>`).join('')}</tbody></table></div></details>`);
  updateDetailGalleryState(r,shown);
  if(r.kind==='package')disposeDetailView=bindDetail($('#modalBody'),r,catalog.settings);
  if(productGroupIndex.has(r.id))$('#modal .dialog-head h2').innerHTML=groupTitleHTML(r);
  if(focusedSpec===r.id)[...$('#modalBody').querySelectorAll('.group-option')].find(button=>button.dataset.detail===r.id)?.focus({preventScroll:true});
}
function compare(){if(state.selected.length<2)return toast('至少选择2条记录进行对比');const a=state.selected.map(id=>records.find(r=>r.id===id));const rows=[['图片',r=>image(r)],['名称',r=>esc(r.name)],['类型',r=>esc(r._category)],['规格原文',r=>esc(text(r.specificationRaw)||'待补')],['材料原文',r=>esc(text(r.materialRaw)||'待补')],['资料标注用途',r=>esc(recordUses(r).map(value=>t(value)).join(' / '))],['结构参考用途',r=>esc(recordReferenceUses(r).map(value=>t(value)).join(' / '))],['供应商',r=>esc(supplier(r))],['报价口径',r=>esc(text(r.quoteHeader)||'未注明')],['确认单价',r=>esc(r.unitPrice==null?'待确认':String(r.unitPrice)+(r.currency?' '+r.currency:''))],['普通报价',r=>esc(text(r.quoteRaw)||'待询价')],['普通起订／数量',r=>esc(text(r.moqRaw)||'待补')],['普通交期',r=>esc(text(r.leadTimeRaw)||'待补')],['定制报价',r=>esc(text(r.customQuoteRaw)||'待询价')],['定制起订／数量',r=>esc(text(r.customMoqRaw)||'待补')],['定制交期',r=>esc(text(r.customLeadTimeRaw)||'待补')],['样品费',r=>esc(text(r.sampleFeeRaw)||'待补')],['开模费',r=>esc(text(r.moldFeeRaw)||'待补')],['来源',r=>esc(source(r))]];modal('包材与询价对比',`<div class="note">不同数量、币种、税运条件与套装范围的报价不能直接比低价。以下完整保留各条原文。</div><div class="table-wrap" style="margin-top:18px"><table class="compare-grid"><tbody>${rows.map(([k,fn])=>`<tr><th>${k}</th>${a.map(r=>`<td${['图片','类型'].includes(k)?'':' data-i18n-skip'}>${fn(r)}</td>`).join('')}</tr>`).join('')}</tbody></table></div>`,`<button class="btn primary" data-action="save-plan">保存为选型方案</button>`);}
function plansView(){return title('选型方案','保存当时选中的记录与报价原文，后续资料更新不覆盖原方案。')+(plans.length?plans.map(p=>`<section class="panel"><div class="panel-title"><div><h2><span data-i18n-skip>${esc(p.title)}</span></h2><p class="sub">${esc(p.id)} · ${esc(p.created.slice(0,10))} · ${p.snapshot.length}项</p></div><button class="btn small" data-plan="${esc(p.id)}">查看快照</button></div><div class="raw">${sourceText(p.note,'未填写项目说明')}</div></section>`).join(''):'<div class="empty">还没有选型方案。在图库中勾选候选包材，然后选择“保存方案”。</div>');}
function samplesView(){const rows=sampleData.samples;return title('实物样品借还','只登记实际收到的样品；原表询价记录不代表公司已持有实物。')+`<div class="note" style="margin-bottom:20px">管理员从包材详情登记实物样品并维护编号和位置。借出与归还、测试耗用、寄给客户分别记账。</div>${rows.length?`<section class="panel table-wrap"><table><thead><tr><th>实物编号／包材</th><th>当前所在</th><th>状态</th><th>借用人／归还日期</th><th>操作</th></tr></thead><tbody>${rows.map(s=>`<tr><td><b><span data-i18n-skip>${esc(s.id)}</span></b><div class="sub"><span data-i18n-skip>${esc(records.find(r=>r.id===s.record_id)?.name||s.record_id)}</span></div></td><td><span data-i18n-skip>${esc(s.location)}</span><div class="sub"><span data-i18n-skip>${esc(s.condition)}</span></div></td><td><span class="tag ${s.status==='available'?'green':'orange'}">${esc(statusNames[s.status]||s.status)}</span></td><td>${sourceText(s.borrower,'—')}<br>${esc(s.due||'—')}${s.status==='lent'&&s.due<new Date().toLocaleDateString('sv-SE')?'<span class="tag orange">已逾期</span>':''}</td><td>${session.role==='admin'&&s.status==='available'?`<button class="quiet" data-sample="${esc(s.id)}" data-op="lend">借出</button>`:''}${session.role==='admin'&&s.status==='lent'?`<button class="quiet" data-sample="${esc(s.id)}" data-op="return">归还</button>`:''}${session.role==='admin'&&['available','lent'].includes(s.status)?`<button class="quiet" data-sample="${esc(s.id)}" data-op="consumed">耗用</button><button class="quiet" data-sample="${esc(s.id)}" data-op="sent">寄出</button>`:''}<button class="quiet" data-history="${esc(s.id)}">记录</button></td></tr>`).join('')}</tbody></table></section>`:'<div class="empty">尚未登记实物样品。没有从询价表自动生成库存。</div>'}`;}
function sourcesView(){const counts=new Map();for(const r of records){const name=r._sourceFile;if(!name)continue;let item=counts.get(name);if(!item){item={product:0,pages:0,rules:0};counts.set(name,item);}if(r.kind==='package')item.product++;else if(r.kind==='source_page')item.pages++;else if(r.kind==='process_rule')item.rules++;}const kinds=Object.entries(kindNames).map(([k,n])=>[n,records.filter(r=>r.kind===k).length]);return title('素材与导入概况','原始来源分开登记，图册页线索与产品条目分别计数。')+`<div class="panel"><h2>当前资料</h2>${facts([['在线记录',String(records.length)],['产品来源条目',String(records.filter(r=>r.kind==='package').length)],['图册与图片线索',String(records.filter(r=>r.kind==='source_page').length)],['独立工艺与价格参考',String(records.filter(r=>r.kind==='process_rule').length)],['实物库存','仅以实际登记为准']])}<div class="note">新图册记录包含OCR提取线索，显示来源和待核对提示。缺失参数保持空白；整页预览不是单品图。历史报价使用前应复核数量、税运、币种和有效期。</div></div><div class="panel table-wrap"><h2>来源文件</h2><table><thead><tr><th>来源</th><th>产品条目</th><th>图页／图片线索</th><th>独立参考规则</th></tr></thead><tbody>${[...counts].sort((a,b)=>a[0].localeCompare(b[0],'zh')).map(([name,v])=>`<tr><td data-i18n-skip>${esc(name)}</td><td>${v.product}</td><td>${v.pages}</td><td>${v.rules}</td></tr>`).join('')}</tbody></table></div><div class="panel"><h2>分类方式</h2><p class="sub">左侧按面部、身体、头部定位；搜索区可组合筛选类型、材质、容量区间、瓶型、报价与来源。每个明确规格独立一条，未拆开的图片与图册页在“图册与图片线索”中查看。</p><p class="sub">印刷工艺价格作为独立参考规则保留，不自动套到产品上；业务员结合客户要求判断起订量、货期和最终报价。</p></div>`;}
function inputField(label,name,type='text',value='',required=true){return `<label class="field">${label}${required?' *':''}<input name="${name}" type="${type}" value="${esc(value)}" ${required?'required':''}></label>`;}
function sampleForm(id,op){const s=sampleData.samples.find(v=>v.id===id);if(!s)return;const title={lend:'登记借出',return:'登记归还',consumed:'登记测试耗用',sent:'登记寄给客户'}[op];let fields=op==='lend'?inputField('借用人','borrower')+inputField('预计归还日期','due','date'):op==='return'?inputField('归还位置','location')+inputField('样品状况','condition'):'';fields+=`<label class="field full">${['consumed','sent'].includes(op)?'用途或去向 *':'备注'}<textarea name="note" ${['consumed','sent'].includes(op)?'required':''}></textarea></label>`;modal(title,`<p class="sub">${esc(id)}</p><form id="sampleActionForm" data-id="${esc(id)}" data-op="${op}"><div class="form-grid">${fields}</div><p class="form-error" role="alert"></p><div class="dialog-foot"><button class="btn" type="button" data-close>取消</button><button class="btn primary">确认登记</button></div></form>`);}
function exportRows(rows){const escape=v=>csvCell(text(v));const cells=[['产品编号','内部记录ID','名称','类型','材料原文','规格原文','供应商原文','报价口径','普通报价原文','普通起订数量','普通交期','定制报价原文','定制起订数量','定制交期','样品费原文','开模费原文','来源','资料标注用途','结构参考用途'],...rows.map(r=>[r.productCode||'',r.id,r.name,kindNames[r.kind],r.materialRaw,r.specificationRaw,r.supplierRaw,r.quoteHeader,r.quoteRaw,r.moqRaw,r.leadTimeRaw,r.customQuoteRaw,r.customMoqRaw,r.customLeadTimeRaw,r.sampleFeeRaw,r.moldFeeRaw,source(r),recordUses(r).join('、'),recordReferenceUses(r).filter(value=>!recordUses(r).includes(value)).join('、')])];const blob=new Blob(['\ufeff'+cells.map(row=>row.map(escape).join(',')).join('\r\n')],{type:'text/csv;charset=utf-8'});const a=document.createElement('a');a.href=URL.createObjectURL(blob);a.download='源泽包材-内部选型列表.csv';a.click();setTimeout(()=>URL.revokeObjectURL(a.href),1000);}
document.addEventListener('click',async e=>{const b=e.target.closest('button,a');if(!b||b.closest('.catalog-editor'))return;try{if(b.dataset.editRecord){await openCatalogEditor(b.dataset.editRecord);return;}if(b.dataset.clearFacet){state[b.dataset.clearFacet]=[];state.page=1;refreshFacet(b.dataset.clearFacet);}
else if(b.dataset.clearFilter){const key=b.dataset.clearFilter;if(facetKeys.includes(key)){state[key]=picked(key).filter(v=>v!==b.dataset.filterValue);state.page=1;render();}}
else if(b.dataset.section){beginProductFacet();toggleFacet('section',b.dataset.section);render();$('#searchForm')?.scrollIntoView({behavior:reduceMotion?.matches?'auto':'smooth',block:'start'});}
else if(b.dataset.sideKind!==undefined){state.view='catalog';toggleFacet('kind',b.dataset.sideKind);render();}
else if(b.dataset.sideCategory!==undefined){beginProductFacet();toggleFacet('category',b.dataset.sideCategory);render();}
else if(b.dataset.sideMaterial!==undefined){beginProductFacet();toggleFacet('material',b.dataset.sideMaterial);render();}
else if(b.dataset.sideCapacity!==undefined){beginProductFacet();toggleFacet('capacityBand',b.dataset.sideCapacity);state.capacity=[];render();}
else if(b.dataset.sideSource!==undefined){state.view='catalog';toggleFacet('source',b.dataset.sideSource);render();}
else if(b.dataset.view){if(b.dataset.view==='favorites'&&!preferencesReady)await loadPreferences();if(b.dataset.view==='plans')plans=await api('/api/plans');if(b.dataset.view==='samples')sampleData=await api('/api/samples');state.view=b.dataset.view;state.page=1;if(state.view==='favorites')state.kind=[];if(state.view==='catalog')switchKind('package');render();}else if(b.dataset.detail)detail(b.dataset.detail);else if(b.hasAttribute('data-close'))closeCatalogModal();else if(b.dataset.detailImageStep){moveDetailImage(Number(b.dataset.detailImageStep));}else if(b.dataset.image){const selectedRecord=records.find(r=>r.id===b.dataset.imageRecord);if(selectedRecord){const selectedImage=galleryImages(selectedRecord).find(i=>imageViewKey(i,imagePath(i))===b.dataset.imageView);if(selectedImage)showDetailImage(selectedRecord,selectedImage);}}else if(b.dataset.favorite){if(!preferencesReady)await loadPreferences();const id=b.dataset.favorite;const next=prefs.favorites.includes(id)?prefs.favorites.filter(v=>v!==id):[...prefs.favorites,id];await api('/api/preferences',{favorites:next});prefs.favorites=next;if(session.catalogPaging&&state.view==='favorites')remoteKey='';render();if($('#modal').open)detail(id);toast(next.includes(id)?'已收藏':'已取消收藏');}else if(b.dataset.page&&!b.disabled){updateCatalogPage(b.dataset.page,{focus:b.dataset.pageControl||'current'});}else if(b.dataset.register){const id=b.dataset.register;modal('登记实物样品',`<div class="note">仅在实际收到样品后登记。每件需要独立借还的实物使用一个编号。</div><form id="registerForm" data-id="${esc(id)}"><div class="form-grid" style="margin-top:20px">${inputField('实物样品编号','id')}${inputField('存放位置（柜／层／格）','location')}${inputField('样品状况','condition','text','完好')}</div><p class="form-error" role="alert"></p><div class="dialog-foot"><button type="button" class="btn" data-close>取消</button><button class="btn primary">保存实物档案</button></div></form>`);}else if(b.dataset.sample)sampleForm(b.dataset.sample,b.dataset.op);else if(b.dataset.history){const history=await api('/api/samples/'+encodeURIComponent(b.dataset.history)+'/history');modal('实物流转记录',history.map(v=>`<div class="link-item"><b>${esc({register:'登记实物',lend:'借出',return:'归还',consumed:'测试耗用',sent:'寄给客户'}[v.action]||v.action)}</b><p class="sub">${esc(v.created)} · ${esc(v.actor)}</p><div class="raw">${esc(Object.entries(JSON.parse(v.details)).map(([k,value])=>`${({borrower:'借用人',due:'预计归还',location:'位置',condition:'状况',note:'说明',id:'编号',record_id:'资料编号'}[k]||k)}：${value}`).join('\n'))}</div></div>`).join('')||'暂无记录');}else if(b.dataset.plan){const p=plans.find(v=>v.id===b.dataset.plan);modal(p.title,`<p class="sub">以下为方案保存时的资料快照。</p>${p.snapshot.map(r=>`<div class="panel"><h3><span data-i18n-skip>${esc(r.name)}</span></h3><div class="source-line">${esc(source(r))}</div>${quoteDetails(r)}${extraDetails(r)}</div>`).join('')}`);}else if(b.id==='logout'){await api('/api/logout',{});location.href='/login';}else{switch(b.dataset.action){case 'new-product':await openCatalogEditor();break;case 'staff-preview':if(session.role!=='admin')return;if(!closeCatalogModal())return;state.staffPreview=!state.staffPreview;render();break;case 'toggle-filters':state.filtersOpen=!state.filtersOpen;render();break;case 'retry-catalog':await init();break;case 'retry-preferences':await loadPreferences();break;case 'browse-materials':$('#searchForm')?.scrollIntoView({behavior:reduceMotion?.matches?'auto':'smooth',block:'start'});$('#query')?.focus({preventScroll:true});break;case 'reset':clearImageSearch();resetProductFilters();state.query='';state.kind=state.view==='favorites'?[]:['package'];render();break;case 'layout':state.table=!state.table;render();break;case 'compare':compare();break;case 'clear-selected':state.selected=[];render();break;case 'retry-page':loadRemotePage().catch(()=>{});break;case 'export':if(imageSearch.matches&&!imageSearch.matches.size){toast('没有符合这些条件的记录。可清空或减少筛选条件。');break;}if(session.catalogPaging){const a=document.createElement('a');a.href='/api/catalog/export?'+remoteParams();a.download='源泽包材-内部选型列表.csv';a.click();}else exportRows(filtered());break;case 'save-plan':if(!state.selected.length)return toast('请先选择候选包材');modal('保存选型方案',`<form id="planForm"><div class="form-grid">${inputField('方案名称（客户／项目）','title')}<label class="field full">需求、数量与待确认事项<textarea name="note"></textarea></label></div><p class="sub">保存 ${state.selected.length} 条记录的当前快照。</p><p class="form-error" role="alert"></p><div class="dialog-foot"><button type="button" class="btn" data-close>取消</button><button class="btn primary">保存方案</button></div></form>`);break;}}}catch(err){toast(err.message);}});
document.addEventListener('change',e=>{const el=e.target;if(el.id==='pageSize'){const size=Number(el.value);updateCatalogPage(Math.floor((state.page-1)*state.pageSize/size)+1,{size,focus:'size'});}else if(el.dataset.filter&&facetKeys.includes(el.dataset.filter)){toggleFacet(el.dataset.filter,el.value);if(el.dataset.filter==='capacity')state.capacityBand=[];refreshFacet(el.dataset.filter,el.value);}else if(el.dataset.select){const id=el.dataset.select;if(el.checked){if(state.selected.length>=4){el.checked=false;return toast('一次最多对比4条记录');}state.selected.push(id);}else state.selected=state.selected.filter(v=>v!==id);render();}});
document.addEventListener('submit',async e=>{const f=e.target;if(f.id==='pageJumpForm'){e.preventDefault();updateCatalogPage(f.elements.page.value,{focus:'jump'});return;}if(!['searchForm','registerForm','sampleActionForm','planForm'].includes(f.id))return;e.preventDefault();const d=Object.fromEntries(new FormData(f));if(f.id==='searchForm'){if(session.catalogPaging&&/^[a-z0-9][a-z0-9_-]{2,}$/i.test(d.query)&&!/^YZBC\d{6,}$/.test(codeKey(d.query)))await ensureRecords([d.query]);setCatalogQuery(d.query);render();return;}const btn=f.querySelector('button[type="submit"],button:not([type])');if(btn)btn.disabled=true;try{if(f.id==='registerForm'){d.record_id=f.dataset.id;await api('/api/samples',d);sampleData=await api('/api/samples');toast('实物样品已登记');}if(f.id==='sampleActionForm'){await api('/api/samples/'+encodeURIComponent(f.dataset.id)+'/'+f.dataset.op,d);sampleData=await api('/api/samples');toast('流转记录已保存');}if(f.id==='planForm'){await api('/api/plans',{...d,ids:state.selected});plans=await api('/api/plans');state.view='plans';toast('选型快照已保存');}$('#modal').close();render();}catch(err){f.querySelector('.form-error').textContent=err.message;}finally{if(btn)btn.disabled=false;}});
function applySiteSettings(){const v=catalog.settings||{};document.title=getLanguage()==='en'?'Yuanze Packaging Library · Internal selection':v.siteTitle||'源泽包材库 · 内部选型';$('#brandName').textContent=v.brandName||'源泽';$('#brandEnglish').textContent=v.englishName||'YUANZE PACKAGING';$('#companyName').textContent=v.companyName||'广州源泽药业有限公司';$('#footerCompany').textContent=v.companyName||'广州源泽药业有限公司';$('#footerNote').textContent=v.footerNote||'';$('#businessLink').hidden=v.showBusinessDemo===false;viewNames.catalog=v.catalogTitle||'包材选型库';$('#catalogNavLabel').textContent=viewNames.catalog;}

registerTranslations({'请使用原管理员账号重新登录后保存，当前草稿仍保留。':'Sign in with the original administrator account before saving. Your draft is kept.','身体':'Body','头部':'Head','按护理部位':'By care area','护理部位':'Care area','不限部位':'All care areas','不限容量区间':'All capacity ranges','筛选条件':'Filters','管理工具':'Management tools','业务员视角':'Staff view','返回管理员':'Return to administrator','＋ 新增产品':'＋ Add product','具体用途、材质与规格可在搜索区查找':'Find uses, materials and sizes in search','搜索产品名称、用途或规格，查找合适的包材。':'Search names, uses or sizes to find packaging.','已保存，业务员刷新页面后可查看最新资料。':'Saved. Staff can refresh to see the updated product.','已保存，此产品不符合当前筛选条件。':'Saved. This product no longer matches the current filters.','读取产品资料':'Loading product','正在读取最新产品资料…':'Loading the latest product details…'});
function canManage(){return session.role==='admin'&&!state.staffPreview;}
function syncManagementUI(){
  $('#adminLink').hidden=!canManage();
  const preview=$('#staffPreview');if(preview){preview.hidden=session.role!=='admin';preview.textContent=t(state.staffPreview?'返回管理员':'业务员视角');}
  document.body.dataset.workspaceRole=canManage()?'admin':'employee';
}
function disposeCatalogEditor(){const previous=catalogEditor;catalogEditor=null;previous?.destroy();$('#modal').classList.remove('is-editing-product');}
function closeCatalogModal(){if(catalogEditor?.isOpen()&&!catalogEditor.canClose())return false;disposeCatalogEditor();$('#modal').close();return true;}
async function acceptSavedRecord(saved){
  if(!saved?.id)throw Error('保存结果缺少产品编号，请刷新后核对。');
  if(session.catalogPaging){recordCache.delete(saved.id);if(!saved.archived)recordCache.set(saved.id,saved);remoteKey='';disposeCatalogEditor();await loadRemotePage();if(!saved.archived){await ensureRecords([saved.id]);detail(saved.id);}else $('#modal').close();toast('已保存，业务员刷新页面后可查看最新资料。');return;}
  const index=catalog.records.findIndex(r=>r.id===saved.id);
  if(saved.archived){if(index>=0)catalog.records.splice(index,1);}
  else if(index<0)catalog.records.unshift(saved);else catalog.records[index]=saved;
  prepareCatalogRecords();disposeCatalogEditor();render();
  if(!saved.archived)detail(saved.id);else $('#modal').close();
  toast(filtered().some(r=>r.id===saved.id)?'已保存，业务员刷新页面后可查看最新资料。':'已保存，此产品不符合当前筛选条件。');
}
async function editorAPI(path,data){
  if(data!==undefined){
    const current=await api('/api/session',undefined,{redirectOn401:false});
    if(current.role!=='admin'||current.username!==session.username)throw Error(t('请使用原管理员账号重新登录后保存，当前草稿仍保留。'));
    session=current;
  }
  return api(path,data,{redirectOn401:false});
}
async function openCatalogEditor(id=null){
  if(!canManage())return;
  if(catalogEditor?.isOpen()&&!catalogEditor.canClose())return;
  disposeCatalogEditor();editorRecordId=id;
  modal(id?'读取产品资料':'新增产品','<div class="empty" role="status">正在读取最新产品资料…</div>');
  $('#modal').classList.add('is-editing-product');
  const editor=createCatalogEditor({container:$('#modalBody'),api:editorAPI,onSaved:acceptSavedRecord,onCancel:()=>{const previous=editorRecordId;disposeCatalogEditor();if(previous&&records.some(r=>r.id===previous))detail(previous);else $('#modal').close();}});
  catalogEditor=editor;
  try{await editor.open(id);}catch(error){if(catalogEditor!==editor)return;disposeCatalogEditor();modal('无法打开产品资料',`<p role="alert">${esc(error.message)}</p><button type="button" class="btn" data-close>关闭</button>`);}
}
$('#modal').addEventListener('keydown',event=>{
  if(!$('#modal').open||!['ArrowLeft','ArrowRight'].includes(event.key)||event.target.closest('input,textarea,select,[contenteditable=true],[role=textbox]'))return;
  if(galleryImages(records.find(record=>record.id===$('#modalBody [data-detail-record]')?.dataset.detailRecord)||{}).length<=1)return;
  event.preventDefault();moveDetailImage(event.key==='ArrowLeft'?-1:1);
});
$('#modal').addEventListener('cancel',event=>{if(catalogEditor?.isOpen()&&!catalogEditor.canClose()){event.preventDefault();return;}disposeCatalogEditor();});
$('#modal').addEventListener('close',()=>disposeCatalogEditor());
window.addEventListener('beforeunload',event=>{if(catalogEditor?.hasUnsavedChanges()){event.preventDefault();event.returnValue='';}});
function prepareCatalogRecords(){({records,productGroupIndex,productCodeIndex,recordIdIndex}=prepareRecords(catalog,reviewedProductGroups));}


let catalogLoading=false;
async function init(){if(catalogLoading)return;catalogLoading=true;$('#main').innerHTML='<div class="empty" role="status">正在读取包材资料…</div>';try{session=await api('/api/session');if(session.catalogPaging){const requestedCode=new URLSearchParams(location.search).get('code');if(requestedCode){state.query=requestedCode;state.kind=[];}await loadRemotePage();}else catalog=await api('/api/catalog');if(!Array.isArray(catalog.records))throw Error('包材数据格式异常，请稍后重试。');prepareCatalogRecords();applySiteSettings();syncManagementUI();$('#account').dataset.i18nSkip='';$('#account').textContent=session.local?t('本机预览'):session.username;$('#logout').hidden=session.local;const requestedCode=new URLSearchParams(location.search).get('code');if(requestedCode)setCatalogQuery(requestedCode);render();loadPreferences().catch(()=>{});loadImageSearchStatus();if(session.role==='admin'&&location.hash.startsWith('#records/')){try{await openCatalogEditor(decodeURIComponent(location.hash.slice(9)));}catch(error){toast(error.message);}}}catch(err){$('#main').innerHTML=`<div class="panel load-error"><h2>暂时无法读取包材资料</h2><p role="alert">${esc(err.message)}</p><button type="button" class="btn primary" data-action="retry-catalog">重试加载</button>${err.status===401?' <a class="btn" href="/login">重新登录</a>':''}</div>`;}finally{catalogLoading=false;}}
init();
if(document.modelContext?.registerTool){const life=new AbortController();window.addEventListener('pagehide',()=>life.abort(),{once:true});for(const tool of [{name:'search_packaging_catalog',description:'在已登录的内部包材库中查询名称、编号和规格原文，不修改业务数据。',inputSchema:{type:'object',properties:{query:{type:'string'}},required:['query'],additionalProperties:false},annotations:{readOnlyHint:true},async execute(input){if(!input||typeof input.query!=='string'||Object.keys(input).some(k=>k!=='query'))throw Error('请提供查询文字');if(session.catalogPaging){const data=await api('/api/catalog/page?'+new URLSearchParams({q:input.query,page:'1',pageSize:'20'}));return data.records.filter(r=>data.matchedIds.includes(r.id)).slice(0,20).map(r=>({id:r.id,productCode:r.productCode||'',name:r.name,source:source(r),quoteStatus:quote(r)?'有历史报价原文':'待询价'}));}const lookup=numberLookup(input.query),matchers=searchMatchers(input.query);return records.filter(r=>lookup.active?r.id===lookup.record?.id:matchesText(r,matchers)).slice(0,20).map(r=>({id:r.id,productCode:r.productCode||'',name:r.name,source:source(r),quoteStatus:quote(r)?'有历史报价原文':'待询价'}));}},{name:'open_packaging_record',description:'在已登录页面打开指定包材询价记录的详情，仅改变页面。',inputSchema:{type:'object',properties:{id:{type:'string'}},required:['id'],additionalProperties:false},annotations:{readOnlyHint:false},async execute(input){if(!input||typeof input.id!=='string'||Object.keys(input).some(k=>k!=='id'))throw Error('记录不存在');if(session.catalogPaging)await ensureRecords([input.id]);if(!records.some(r=>r.id===input.id))throw Error('记录不存在');detail(input.id);return {opened:input.id};}}]){try{Promise.resolve(document.modelContext.registerTool(tool,{signal:life.signal})).catch(()=>{});}catch{}}}

onLanguageChange(()=>{syncImageSearchUI();imageDraft?.selection?.draw();const r=records.find(record=>record.id===$('#modalBody [data-detail-record]')?.dataset.detailRecord),photo=$('#detailPhoto img');if(r){const images=galleryImages(r);updateDetailGalleryState(r,images[detailGalleryIndex(images,photo?.dataset.imageView||'',photo?.getAttribute('src')||'')]);}if(session.local)$('#account').textContent=t('本机预览');document.title=getLanguage()==='en'?'Yuanze Packaging Library · Internal selection':catalog.settings?.siteTitle||'源泽包材库 · 内部选型';});
