import {referenceMode,referencePatch,automaticReferenceUses} from './admin-product-tools.js';
import {pricingData} from './product-pricing.js';
import {t, translateMessage, registerTranslations, onLanguageChange} from './i18n.js';
import {primaryImage, isProductImage, imageScope, imageScopeLabel} from './image-policy.js';

registerTranslations({'现货状态（yes / no / unknown）':'Stock status (yes / no / unknown)',
  '编辑当前规格':'Edit this specification','新增产品':'Add product','保存产品':'Save product',
  '只修改当前产品编号对应的资料，其他规格保持原样。':'Only this product code is edited. Other specifications keep their own details.',
  '保存后自动分配产品编号':'A product code is assigned when saved',
  '护理部位（可多选）':'Application areas (select multiple)','身体':'Body','头部':'Hair and scalp',
  '尚未标注护理部位，按实际用途选择。':'No application areas are set. Select those supported by the product uses.',
  '多个材质或用途用顿号、逗号或换行分隔。':'Separate materials or uses with commas or line breaks.',
  '基础资料':'Product information','采购与报价':'Purchasing and quotations','产品说明':'Description',
  '更多产品参数与历史原文':'More parameters and original quotations',
  '原始来源与保留字段（只读）':'Original source and preserved fields (read only)',
  '未修改的资料保持原样，产品编号和原始来源不会重写。':'Unedited data, the product code and original source are preserved.',
  '仅修改当前产品':'Editing this product only','产品图片':'Product images','尚未添加图片':'No images yet',
  '上传图片':'Upload images','JPEG、PNG、WebP；单张不超过 10 MB。':'JPEG, PNG or WebP; up to 10 MB each.',
  '优先展示':'Primary image','图片说明':'Image caption','图片用途':'Image role','设为首图':'Set as primary',
  '前移':'Move earlier','后移':'Move later','允许客户展示此图片':'Allow customers to view this image',
  '确认图片不含供应商、报价或联系方式。':'Check that the image contains no supplier, pricing or contact information.',
  '图片加载失败':'Image unavailable','图片 {number}':'Image {number}',
  '图片上传后还需保存产品；取消不会将图片关联至产品。':'Save the product after uploading. Cancelling does not attach uploaded images to the product.',
  '正在上传图片…':'Uploading images…','图片已上传，请保存产品。':'Images uploaded. Save the product to apply them.',
  '请选择不超过 10 MB 的 JPEG、PNG 或 WebP 图片。':'Choose JPEG, PNG or WebP images up to 10 MB each.',
  '图片尺寸不合适，请选择边长至少 16 像素、总像素不超过 2000 万的图片。':'Images must be at least 16 pixels on each side and no more than 20 megapixels.',
  '每个产品最多添加 30 张图片。':'A product can have up to 30 images.',
  '无法处理此图片，请换一张图片重试。':'This image could not be processed. Try another image.',
  '上传结果缺少图片路径，请重试。':'The upload returned no image path. Please retry.',
  '产品细则':'Product specifications','添加细则':'Add specification','项目':'Item','具体内容':'Value',
  '资料来源':'Source field','原文依据':'Source evidence','未指定／其他资料':'Unspecified / other evidence',
  '产品细则最多 60 项。':'A product can have up to 60 specifications.',
  '请填写每项细则的项目名称。':'Enter a label for each specification.',
  '资料已被其他操作更新。你的修改仍保留；请另开管理页面核对最新资料后再合并。':'This product was updated elsewhere. Your draft is kept. Review the latest product in another administration window before merging changes.',
  '登录已过期，草稿仍保留。请在新窗口登录后再保存。':'Your session expired. Your draft is kept. Sign in in another window before saving.',
  '无法读取产品资料，请重试。':'Unable to load this product. Please retry.',
  '保存结果尚未确认，草稿仍保留。请先核对最新资料，避免重复新建。':'The save result is unconfirmed and your draft is kept. Check the latest data before creating a duplicate.',
  '资料已保存，但列表未刷新。请重新打开产品查看。':'The product was saved, but the catalogue did not refresh. Reopen the product to view it.',
  '请填写产品名称。':'Enter a product name.',
  '数值须为有效的非负数，未知时请留空。':'Enter a valid non-negative number, or leave it blank if unknown.',
  '有尚未保存的修改，确定放弃这些修改吗？':'Discard your unsaved changes?',
  '正在保存或上传，请稍候。':'Saving or uploading. Please wait.',
  '修改内容后点击保存。':'Save when you have finished editing.',
  '当前资料已归档，保存不会自动恢复展示。':'This product is archived. Saving does not restore it to the catalogue.',
  '供应商图片':'Supplier image','询价图片':'Quotation image','参考图片':'Reference image',
  '浮动参考图':'Floating reference','其他原图':'Other original image','测试计划图片':'Test plan image',
  '待核对图片':'Unverified image','客户图片':'Customer image',
});

const esc = value => String(value ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const clone = value => JSON.parse(JSON.stringify(value));
const list = value => Array.isArray(value) ? value : [];
const text = value => value == null ? '' : typeof value === 'string' ? value : JSON.stringify(value);
const split = value => [...new Set(value.split(/[\n,，、;；]/).map(x => x.trim()).filter(Boolean))];
const rawLabels = {addressRaw:'供应商地址',extra2Raw:'其他补充',requirementsRaw:'需求说明',testPlanRaw:'测试计划',materialRaw:'材质说明',specificationRaw:'规格说明',quoteRaw:'采购单价／普通报价',moqRaw:'普通起订量 MOQ',leadTimeRaw:'普通货期',customQuoteRaw:'定制报价',customMoqRaw:'定制起订量',customLeadTimeRaw:'定制货期',supplierRaw:'供应商名称',contactRaw:'供应商联系方式／联系人',processRaw:'工艺说明（历史原文）',remarksRaw:'备注',customerRaw:'客户／需求来源',sampleFeeRaw:'样品费用',moldFeeRaw:'开模费用',dateOrNotesRaw:'询价日期与原备注',extraRaw:'其他信息'};
const labels = {bareBottlePrice:'裸瓶价格',stockStatus:'现货状态（yes / no / unknown）',name:'产品名称',kind:'资料类型',category:'包材分类',bottleType:'瓶型',materials:'标准材质',capacityMl:'容量（mL）',uses:'资料标注用途',series:'系列名称',model:'款式／型号',description:'产品说明',quoteHeader:'报价口径',currency:'币种（可选）',unitPrice:'确认单价（可选）',validUntil:'报价有效期（可选）',sourceNote:'来源补充说明',uncertainties:'待确认事项',...rawLabels};
const kinds = {package:'包材',source_page:'图册与图片线索',process_rule:'工艺与价格参考',semi_finished:'料体与半成品',service:'检测与服务',requirement:'需求资料',uncertain:'待分类'};
const roles = {product:'产品图片',supplier:'供应商图片',inquiry:'询价图片',reference:'参考图片','floating-reference':'浮动参考图',other:'其他原图','test-plan':'测试计划图片',uncertain:'待核对图片',customer:'客户图片'};
const areas = {face:'面部',body:'身体',head:'头部'};
const sourceFields = ['name','kind','category','bottleType','series','model','description','quoteHeader','sourceNote',...Object.keys(rawLabels)];
const ui = (key,params) => `<span data-editor-text="${esc(key)}"${params ? ` data-editor-params="${esc(JSON.stringify(params))}"` : ''}>${esc(t(key,params))}</span>`;
const button = (action,label,extra='') => `<button type="button" class="btn" data-editor-action="${action}" ${extra}>${ui(label)}</button>`;
function imageURL(image) {
  const path = String(image?.path || image?.file || '').replace(/\\/g,'/').replace(/^\/+/, '');
  const parts = path.split('/');
  if (!['media','uploads'].includes(parts[0]) || parts.length < 2 || parts.some(part => !part || part === '.' || part === '..')) return '';
  return '/' + parts.map(encodeURIComponent).join('/');
}

// The caller supplies the existing authenticated API wrapper (path, data?).
// Only changed, supported fields are sent: AdminStore merges them with the
// current record, preserving unknown legacy fields and immutable source data.
export function createCatalogEditor({container,api,onSaved = () => {},onCancel = () => {}}) {
  if (!container || typeof api !== 'function') throw new TypeError('Editor container and API are required');
  let record = null, images = [], details = [], initialFields = new Map(), changed = new Set(), referenceManual = '';
  let opened = false, busy = false, dirty = false, destroyed = false, sequence = 0, loadedId = null;
  let statusKey = '', statusParams = {}, statusError = false;
  const $ = selector => container.querySelector(selector);
  const all = selector => [...container.querySelectorAll(selector)];
  function localize() {
    all('[data-editor-text]').forEach(el => {el.textContent=t(el.dataset.editorText,el.dataset.editorParams ? JSON.parse(el.dataset.editorParams) : {});});
    all('[data-editor-label]').forEach(el => el.setAttribute('aria-label',t(el.dataset.editorLabel)));
    all('[data-editor-image-number]').forEach(el => el.alt=t('图片 {number}',{number:el.dataset.editorImageNumber}));
    const status=$('[data-editor-status]');if(status){status.textContent=Object.keys(statusParams).length?t(statusKey,statusParams):translateMessage(statusKey);status.classList.toggle('is-error',statusError);}
  }
  const unsubscribe = onLanguageChange(localize);
  function status(key,error=false,params={}) {statusKey=key;statusError=error;statusParams=params;localize();}
  function setBusy(value) {
    busy=value;
    all('button,input,select,textarea').forEach(el => {
      if (value) {if(el.dataset.editorDisabled===undefined)el.dataset.editorDisabled=String(el.disabled);el.disabled=true;}
      else if (el.dataset.editorDisabled!==undefined) {el.disabled=el.dataset.editorDisabled==='true';delete el.dataset.editorDisabled;}
    });
    $('[data-editor-form]')?.setAttribute('aria-busy',String(value));
  }
  function markDirty() {dirty=true;}
  function field(key,{wide=false,textarea=false,type='text',required=false,options=null}={}) {
    const value=key==='bareBottlePrice'&&!Object.hasOwn(record,key)?pricingData(record).bare.map(row=>row.value).join('\n'):['materials','uses'].includes(key)?list(record[key]).join('、'):key==='uncertainties'?list(record[key]).join('\n'):text(record[key]);
    initialFields.set(key,value);
    const attrs=`data-editor-field="${key}" ${required?'required':''}`;
    const choices=options ? {...options,...(value && !Object.hasOwn(options,value)?{[value]:value}:{})} : null;
    const control=choices ? `<select ${attrs}>${Object.entries(choices).map(([k,v])=>`<option value="${esc(k)}" ${k===value?'selected':''} data-editor-text="${esc(v)}">${esc(t(v))}</option>`).join('')}</select>` : textarea ? `<textarea ${attrs} rows="3">${esc(value)}</textarea>` : `<input ${attrs} type="${type}" value="${esc(value)}" ${type==='number'?'min="0" max="1000000000000" step="any"':''}>`;
    return `<label class="catalog-editor-field ${wide?'wide':''}"><span>${ui(labels[key]||key)}${required?' *':''}</span>${control}</label>`;
  }
  function referenceControls(){
    const mode=referenceMode(record),suggested=automaticReferenceUses(record).join('、');referenceManual=mode==='manual'?record.referenceUses.join('、'):suggested;
    return `<fieldset class="catalog-editor-reference wide"><legend>${ui('结构参考用途')}</legend><label class="catalog-editor-field"><span>${ui('参考用途模式')}</span><select data-editor-reference-mode>${[['automatic','自动／恢复自动'],['manual','人工填写参考用途'],['disabled','关闭参考用途']].map(([value,label])=>`<option value="${value}" ${mode===value?'selected':''} data-editor-text="${esc(label)}">${esc(t(label))}</option>`).join('')}</select></label><label class="catalog-editor-field"><span>${ui('结构参考用途')}</span><input data-editor-reference-tags value="${esc(mode==='disabled'?'':referenceManual)}" ${mode==='manual'?'':'disabled'}></label><small>${ui('多个参考用途用顿号、逗号或换行分隔。')}</small><small>${ui('根据包材结构整理，具体适配请与业务员确认。')}</small></fieldset>`;
  }
  function updateReferenceMode(){const mode=$('[data-editor-reference-mode]').value,input=$('[data-editor-reference-tags]');if(!input.disabled)referenceManual=input.value;input.disabled=mode!=='manual';input.value=mode==='manual'?referenceManual:mode==='automatic'?automaticReferenceUses(record).join('、'):'';markDirty();}
  function render() {
    initialFields = new Map();
    const primaryRaw = ['specificationRaw','quoteRaw','moqRaw','leadTimeRaw','supplierRaw'];
    const advanced = ['kind','category','bottleType','capacityMl','series','model','unitPrice','currency','validUntil','quoteHeader','sourceNote','uncertainties',...Object.keys(rawLabels).filter(k=>!primaryRaw.includes(k))];
    const mainKeys=['name','materials','uses','referenceUses','description',...primaryRaw];
    const preserved=Object.fromEntries(Object.entries(record).filter(([key])=>![...mainKeys,...advanced,'images','bodyAreas','productDetails','id','productCode','version','archived','created','updated','searchText'].includes(key)));
    const body=list(record.bodyAreas);
    container.innerHTML=`<section class="catalog-editor" data-i18n-skip><header class="catalog-editor-head"><div><p class="catalog-editor-code">${esc(record.productCode||t('保存后自动分配产品编号'))}${record.id?` · ${esc(record.specificationRaw||'')}`:''}</p><h2>${ui(record.id?'编辑当前规格':'新增产品')}</h2><p>${ui('只修改当前产品编号对应的资料，其他规格保持原样。')}</p></div>${button('cancel','取消')}</header>${record.archived?`<p class="catalog-editor-notice">${ui('当前资料已归档，保存不会自动恢复展示。')}</p>`:''}<form data-editor-form novalidate><div class="catalog-editor-layout"><section class="catalog-editor-media"><h3>${ui('产品图片')}</h3><div data-editor-primary></div><div class="catalog-editor-upload"><label class="btn">${ui('上传图片')}<input type="file" data-editor-upload accept="image/jpeg,image/png,image/webp" multiple hidden></label><small>${ui('JPEG、PNG、WebP；单张不超过 10 MB。')}</small></div><div data-editor-images></div><p class="catalog-editor-help">${ui('图片上传后还需保存产品；取消不会将图片关联至产品。')}</p></section><section class="catalog-editor-fields"><h3>${ui('基础资料')}</h3><div class="catalog-editor-grid">${field('name',{wide:true,required:true})}${field('materials')}${field('specificationRaw')}${field('uses',{wide:true})}${referenceControls()}<fieldset class="catalog-editor-areas wide"><legend>${ui('护理部位（可多选）')}</legend>${Object.entries(areas).map(([key,label])=>`<label><input type="checkbox" data-editor-area="${key}" ${body.includes(key)?'checked':''}>${ui(label)}</label>`).join('')}${!body.length?`<small>${ui('尚未标注护理部位，按实际用途选择。')}</small>`:''}</fieldset></div><p class="catalog-editor-help">${ui('多个材质或用途用顿号、逗号或换行分隔。')}</p><h3>${ui('采购与报价')}</h3><div class="catalog-editor-grid">${field('bareBottlePrice')}${field('stockStatus')}${field('quoteRaw',{wide:true,textarea:true})}${field('supplierRaw')}${field('moqRaw')}${field('leadTimeRaw')}${field('description',{wide:true,textarea:true})}</div><details class="catalog-editor-advanced"><summary>${ui('更多产品参数与历史原文')}</summary><div class="catalog-editor-grid">${advanced.map(key=>field(key,{wide:['quoteHeader','sourceNote','uncertainties'].includes(key),textarea:key.endsWith('Raw')||['quoteHeader','sourceNote','uncertainties'].includes(key),type:['capacityMl','unitPrice'].includes(key)?'number':key==='validUntil'?'date':'text',options:key==='kind'?kinds:null})).join('')}</div></details><details class="catalog-editor-advanced"><summary>${ui('产品细则')}</summary><div data-editor-details></div>${button('add-detail','添加细则')}</details><details class="catalog-editor-advanced"><summary>${ui('原始来源与保留字段（只读）')}</summary><pre>${esc(JSON.stringify(preserved,null,2))}</pre></details></section></div><footer class="catalog-editor-foot"><div><p data-editor-status role="status" aria-live="polite"></p><small>${ui('未修改的资料保持原样，产品编号和原始来源不会重写。')}</small></div><div>${button('cancel','取消')}<button type="submit" class="btn primary" data-editor-action="save">${ui('保存产品')}</button></div></footer></form></section>`;
    if(!record.productCode)$('.catalog-editor-code').innerHTML=ui(record.id?'原始资料无需产品编号':'保存后自动分配产品编号');
    // Use the browser's displayed values as the comparison baseline. Legacy
    // date/number strings that a control cannot display must not be cleared by
    // saving an unrelated field.
    all('[data-editor-field]').forEach(el=>initialFields.set(el.dataset.editorField,el.value));
    renderImages();renderDetails();status('修改内容后点击保存。');
  }
  function renderImages() {
    if (!record) return;
    const imageRecord={...record,images},main=primaryImage(imageRecord)||images.find(i=>!i.missing&&imageURL(i));
    $('[data-editor-primary]').innerHTML=main?`<div class="catalog-editor-preview"><img src="${esc(imageURL(main))}" alt="${esc(record.name||'')}" data-editor-image><p>${ui(imageScopeLabel(main,imageRecord))}</p></div>`:`<div class="catalog-editor-empty">${ui('尚未添加图片')}</div>`;
    $('[data-editor-images]').innerHTML=images.map((image,index)=>{
      const url=imageURL(image),canFirst=index>0&&isProductImage(image)&&!(imageScope(image)==='same_style_variants'&&images.some(i=>isProductImage(i)&&imageScope(i)==='single_product'));
      return `<article class="catalog-editor-image"><div class="catalog-editor-image-top">${url&&!image.missing?`<img src="${esc(url)}" alt="${esc(t('图片 {number}',{number:index+1}))}" data-editor-image data-editor-image-number="${index+1}" loading="lazy">`:`<span>${ui('图片加载失败')}</span>`}<span>${ui(imageScopeLabel(image,imageRecord))}</span>${image===primaryImage(imageRecord)?`<strong>${ui('优先展示')}</strong>`:''}</div><label class="catalog-editor-field">${ui('图片说明')}<input data-editor-image-field="caption" data-editor-index="${index}" value="${esc(image.caption||'')}" maxlength="500"></label><label class="catalog-editor-field">${ui('图片用途')}<select data-editor-image-field="role" data-editor-index="${index}">${Object.entries(roles).map(([key,label])=>`<option value="${key}" ${key===(image.role||'reference')?'selected':''} data-editor-text="${esc(label)}">${esc(t(label))}</option>`).join('')}</select></label><label class="catalog-editor-approval"><input type="checkbox" data-editor-image-field="clientVisible" data-editor-index="${index}" ${image.clientVisible===true?'checked':''}>${ui('允许客户展示此图片')}</label><small>${ui('确认图片不含供应商、报价或联系方式。')}</small><div class="catalog-editor-image-actions">${button('first-image','设为首图',`data-editor-index="${index}" ${canFirst?'':'disabled'}`)}${button('up-image','前移',`data-editor-index="${index}" ${index?'':'disabled'}`)}${button('down-image','后移',`data-editor-index="${index}" ${index<images.length-1?'':'disabled'}`)}${button('remove-image','移除',`data-editor-index="${index}"`)}</div></article>`;
    }).join('');
    localize();
  }
  function renderDetails() {
    $('[data-editor-details]').innerHTML=details.map((item,index)=>`<div class="catalog-editor-detail"><div class="catalog-editor-grid">${['label','value','sourceField','evidence'].map(key=>{const label={label:'项目',value:'具体内容',sourceField:'资料来源',evidence:'原文依据'}[key];return `<label class="catalog-editor-field">${ui(label)}${key==='sourceField'?`<select data-editor-detail-field="${key}" data-editor-index="${index}"><option value="" data-editor-text="未指定／其他资料">${esc(t('未指定／其他资料'))}</option>${[...new Set([...sourceFields,item.sourceField].filter(Boolean))].map(value=>`<option value="${esc(value)}" ${value===item[key]?'selected':''} data-editor-text="${esc(labels[value]||value)}">${esc(t(labels[value]||value))}</option>`).join('')}</select>`:key==='label'?`<input data-editor-detail-field="${key}" data-editor-index="${index}" value="${esc(item[key]||'')}" maxlength="80" required>`:`<textarea data-editor-detail-field="${key}" data-editor-index="${index}" maxlength="2000">${esc(item[key]||'')}</textarea>`}</label>`;}).join('')}</div>${button('remove-detail','移除',`data-editor-index="${index}"`)}</div>`).join('');
    $('[data-editor-action="add-detail"]').disabled=details.length>=60;localize();
  }
  function updateField(el) {
    if(!record||busy)return;
    const key=el.dataset.editorField;
    if(key){if(el.value!==initialFields.get(key))changed.add(key);else changed.delete(key);markDirty();}
    else if(el.dataset.editorArea){changed.add('bodyAreas');markDirty();}
    else if(el.dataset.editorImageField){const item=images[Number(el.dataset.editorIndex)],field=el.dataset.editorImageField;if(!item||!['caption','role','clientVisible'].includes(field))return;item[field]=field==='clientVisible'?el.checked:el.value;changed.add('images');markDirty();if(field==='role')renderImages();}
    else if(el.dataset.editorDetailField){const item=details[Number(el.dataset.editorIndex)];if(!item)return;item[el.dataset.editorDetailField]=el.value;changed.add('productDetails');markDirty();}
  }
  function patch() {
    const result={};
    all('[data-editor-field]').forEach(el=>{const key=el.dataset.editorField;if(el.value===initialFields.get(key))return;let value=el.value;if(['materials','uses'].includes(key))value=split(value);else if(key==='uncertainties')value=value.split('\n').map(x=>x.trim()).filter(Boolean);else if(['capacityMl','unitPrice'].includes(key)){value=value.trim()===''?null:Number(value);if(value!==null&&(!Number.isFinite(value)||value<0||value>1e12)){el.closest('details')?.setAttribute('open','');el.focus();throw Error('数值须为有效的非负数，未知时请留空。');}}result[key]=value;});
    const mode=$('[data-editor-reference-mode]').value,initial=referenceMode(record);
    if(mode!==initial||(mode==='manual'&&JSON.stringify(split($('[data-editor-reference-tags]').value))!==JSON.stringify(record.referenceUses)))result.referenceUses=referencePatch(mode,$('[data-editor-reference-tags]').value);
    if(!record.id){result.name=$('[data-editor-field="name"]').value.trim();result.kind=result.kind||'package';}
    if(changed.has('bodyAreas'))result.bodyAreas=all('[data-editor-area]:checked').map(el=>el.dataset.editorArea);
    if(changed.has('images'))result.images=clone(images);
    if(changed.has('productDetails')){
      if(details.some(item=>!String(item.label||'').trim())){$('[data-editor-details]').closest('details').open=true;throw Error('请填写每项细则的项目名称。');}
      result.productDetails=clone(details);
    }
    return result;
  }
  async function save() {
    if(!opened||!record||busy)return;
    const name=$('[data-editor-field="name"]');if(!name.value.trim()){status('请填写产品名称。',true);name.focus();return;}
    let changes;try{changes=patch();}catch(error){status(error.message,true);return;}
    const token=sequence;setBusy(true);status('正在保存…');let saved;
    try {
      saved=await api('/api/admin/records',{action:'save',...(record.id?{id:record.id}:{}),version:record.version||0,record:changes});
      if(!saved||typeof saved.id!=='string'||!Number.isInteger(saved.version))throw Error('保存结果尚未确认，草稿仍保留。请先核对最新资料，避免重复新建。');
    } catch(error) {
      if(token!==sequence||destroyed)return;
      status(error.status===409?'资料已被其他操作更新。你的修改仍保留；请另开管理页面核对最新资料后再合并。':error.status===401?'登录已过期，草稿仍保留。请在新窗口登录后再保存。':error.message,true);
      setBusy(false);return;
    }
    if(token!==sequence||destroyed)return;
    record=clone(saved);dirty=false;opened=false;setBusy(false);
    try{await onSaved(saved);}catch{status('资料已保存，但列表未刷新。请重新打开产品查看。',true);}
  }
  async function upload(files) {
    if(!opened||!record||busy||!files.length)return;
    if(images.length+files.length>30){status('每个产品最多添加 30 张图片。',true);return;}
    const token=sequence;setBusy(true);status('正在上传图片…');
    try {
      for(const file of files){
        if(!['image/jpeg','image/png','image/webp'].includes(file.type)||!file.size||file.size>10*1024*1024)throw Error('请选择不超过 10 MB 的 JPEG、PNG 或 WebP 图片。');
        let bitmap;try{bitmap=await createImageBitmap(file);}catch{throw Error('无法处理此图片，请换一张图片重试。');}
        try {
          if(bitmap.width<16||bitmap.height<16||bitmap.width*bitmap.height>20000000||Math.max(bitmap.width,bitmap.height)>10000)throw Error('图片尺寸不合适，请选择边长至少 16 像素、总像素不超过 2000 万的图片。');
          if(token!==sequence||destroyed)return;
          const scale=Math.min(1,1600/Math.max(bitmap.width,bitmap.height)),canvas=document.createElement('canvas');canvas.width=Math.round(bitmap.width*scale);canvas.height=Math.round(bitmap.height*scale);
          const ctx=canvas.getContext('2d');if(!ctx)throw Error('无法处理此图片，请换一张图片重试。');
          ctx.fillStyle='#fff';ctx.fillRect(0,0,canvas.width,canvas.height);ctx.drawImage(bitmap,0,0,canvas.width,canvas.height);
          const result=await api('/api/admin/uploads',{image:canvas.toDataURL('image/jpeg',.9)});
          if(token!==sequence||destroyed)return;
          if(!result.image?.path||!imageURL(result.image))throw Error('上传结果缺少图片路径，请重试。');
          images.push({...clone(result.image),role:'product',clientVisible:false,caption:file.name.replace(/\.[^.]+$/,'')});changed.add('images');markDirty();renderImages();setBusy(true);
        } finally {bitmap.close();}
      }
      status('图片已上传，请保存产品。');
    } catch(error){if(token===sequence&&!destroyed)status(error.message,true);}
    finally{if(token===sequence&&!destroyed){setBusy(false);const input=$('[data-editor-upload]');if(input)input.value='';}}
  }
  function canClose(){if(!opened)return true;if(busy){status('正在保存或上传，请稍候。',true);return false;}return !dirty||window.confirm(t('有尚未保存的修改，确定放弃这些修改吗？'));}
  function cancel(){if(!canClose())return;opened=false;dirty=false;sequence++;onCancel();}
  function click(event) {
    const el=event.target.closest('button');if(!el||!container.contains(el)||!el.dataset.editorAction)return;
    event.preventDefault();event.stopPropagation();const action=el.dataset.editorAction;if(busy)return;
    if(action==='save'){save();return;}if(action==='cancel'){cancel();return;}if(action==='retry'){open(loadedId);return;}
    if(!record)return;
    const index=Number(el.dataset.editorIndex);
    if(action==='add-detail'){if(details.length>=60){status('产品细则最多 60 项。',true);return;}details.push({label:'',value:'',sourceField:'',evidence:''});changed.add('productDetails');markDirty();renderDetails();return;}
    if(action==='remove-detail'){if(!Number.isInteger(index)||!details[index])return;details.splice(index,1);changed.add('productDetails');markDirty();renderDetails();return;}
    if(!Number.isInteger(index)||!images[index])return;
    if(action==='remove-image')images.splice(index,1);
    else if(action==='up-image'&&index>0)[images[index-1],images[index]]=[images[index],images[index-1]];
    else if(action==='down-image'&&index<images.length-1)[images[index+1],images[index]]=[images[index],images[index+1]];
    else if(action==='first-image'&&isProductImage(images[index])&&!(imageScope(images[index])==='same_style_variants'&&images.some(i=>isProductImage(i)&&imageScope(i)==='single_product')))images.unshift(images.splice(index,1)[0]);
    else return;
    changed.add('images');markDirty();renderImages();
  }
  function input(event){if(event.target.matches('[data-editor-reference-mode],[data-editor-reference-tags]')){event.stopPropagation();if(event.target.matches('[data-editor-reference-mode]'))updateReferenceMode();else{referenceManual=event.target.value;markDirty();}return;}if(!event.target.matches('[data-editor-field],[data-editor-area],[data-editor-image-field],[data-editor-detail-field]'))return;event.stopPropagation();updateField(event.target);}
  function change(event){if(event.target.matches('[data-editor-upload]')){event.stopPropagation();upload([...event.target.files||[]]);}else input(event);}
  function submit(event){if(event.target.matches('[data-editor-form]')){event.preventDefault();event.stopPropagation();save();}}
  function imageError(event){const image=event.target;if(!image.matches?.('img[data-editor-image]'))return;image.hidden=true;const note=document.createElement('span');note.dataset.editorText='图片加载失败';note.textContent=t('图片加载失败');image.replaceWith(note);}
  container.addEventListener('click',click);container.addEventListener('input',input);container.addEventListener('change',change);container.addEventListener('submit',submit);container.addEventListener('error',imageError,true);
  async function open(id=null) {
    if(destroyed||!canClose())return false;
    const token=++sequence;opened=true;busy=true;dirty=false;record=null;loadedId=id;changed=new Set();statusKey='正在读取资料…';statusError=false;
    container.innerHTML=`<section class="catalog-editor" data-i18n-skip><p data-editor-status role="status"></p></section>`;localize();
    try {
      const response=id==null?null:await api('/api/admin/records?id='+encodeURIComponent(id));
      if(token!==sequence||destroyed)return false;
      if(id!=null&&(!response?.item||response.item.id!==id||!Number.isInteger(response.item.version)))throw Error('无法读取产品资料，请重试。');
      record=id==null?{name:'',kind:'package',images:[],materials:[],uses:[],productDetails:[],version:0}:clone(response.item);
      images=clone(list(record.images));details=clone(list(record.productDetails));busy=false;render();return true;
    } catch(error) {
      if(token!==sequence||destroyed)return false;
      busy=false;container.innerHTML=`<section class="catalog-editor" data-i18n-skip><p data-editor-status role="alert"></p><div class="catalog-editor-image-actions">${button('retry','重试')}${button('cancel','取消')}</div></section>`;status(error.message,true);return false;
    }
  }
  function destroy(){sequence++;destroyed=true;opened=false;record=null;images=[];details=[];unsubscribe();container.removeEventListener('click',click);container.removeEventListener('input',input);container.removeEventListener('change',change);container.removeEventListener('submit',submit);container.removeEventListener('error',imageError,true);}
  return {open,canClose,destroy,isOpen:()=>opened,hasUnsavedChanges:()=>opened&&(dirty||busy)};
}
