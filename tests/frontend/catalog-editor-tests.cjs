const assert = require('node:assert/strict');
const path = require('node:path');
const {JSDOM,VirtualConsole} = require('jsdom');
const {evaluateBrowserModule} = require('./module-loader.cjs');
const entry = path.resolve(__dirname,'../../server-reference/public/catalog-editor.js');
const clone = value => JSON.parse(JSON.stringify(value));
const checks=[];
const fixture = (id='series/30',code='YZ-BC-000030') => ({
  id,productCode:code,version:7,kind:'package',name:'沐浴露瓶',materials:['PET'],uses:['沐浴露'],
  specificationRaw:'30 mL',capacityMl:30,quoteRaw:'1000只起，每只2元',unitPrice:null,
  source:{workbook:'原始供应商资料.xlsx',sheet:'Sheet1',row:9},rawCells:{A:'ORIGINAL-EVIDENCE'},
  provenance:{verified:'unchanged'},formulaCachedValues:{F4:28},legacyPrivate:{keep:['UNKNOWN-FIELD']},
  extraLegacyRaw:'OLD UNKNOWN RAW',validUntil:'legacy unknown date',
  productDetails:[{label:'口径',value:'24 mm',sourceField:'specificationRaw',evidence:'原页第9行'}],
  images:[{path:'media/first.jpg',role:'product',imageScope:'single_product',caption:'原图',clientVisible:true,cell:'C9',mapping:'original'},
    {path:'media/reference.jpg',role:'reference',imageScope:'source_page',uncertain:true,clientVisible:false,sourceCell:'D9'}],
});
async function until(fn,label) {for(let i=0;i<500;i++){if(fn())return;await new Promise(resolve=>setTimeout(resolve,4));}throw Error('Timeout: '+label);}
async function setup(records=[fixture()]) {
  const errors=[],calls=[],saved=[],cancelled=[],confirmations=[],canvasSizes=[],bitmaps=[];
  const virtual=new VirtualConsole();virtual.on('jsdomError',error=>errors.push(error.message));
  const dom=new JSDOM('<main><div id="host"></div></main>',{url:'https://catalog.test/catalog',runScripts:'outside-only',pretendToBeVisual:true,virtualConsole:virtual});
  const w=dom.window,d=w.document,db=new Map(records.map(r=>[r.id,clone(r)]));let saveError=null,saveWait=null,uploadError=null,answer=true;
  w.confirm=message=>{confirmations.push(message);return answer;};
  w.createImageBitmap=async()=>{const bitmap={width:2400,height:1600,closed:false,close(){this.closed=true;}};bitmaps.push(bitmap);return bitmap;};
  w.HTMLCanvasElement.prototype.getContext=function(){return {fillStyle:'',fillRect(){},drawImage(){}};};
  w.HTMLCanvasElement.prototype.toDataURL=function(type,quality){canvasSizes.push({width:this.width,height:this.height,type,quality});return 'data:image/jpeg;base64,TEST';};
  const api=async(url,data)=>{
    calls.push({url,data:clone(data??null)});
    if(url.startsWith('/api/admin/records?id='))return {item:clone(db.get(decodeURIComponent(url.split('id=')[1])))};
    if(url==='/api/admin/uploads'){if(uploadError)throw uploadError;return {image:{path:'uploads/abcdef0123456789.jpg',role:'product',imageScope:'single_product',width:1600,height:1067}};}
    if(url==='/api/admin/records'&&data){if(saveWait)await saveWait;if(saveError)throw saveError;const id=data.id||'new-record',old=db.get(id)||{id,version:0,productCode:'YZ-BC-000999',source:{workbook:'管理员录入'}};assert.equal(data.version,old.version);const value={...clone(old),...clone(data.record),id,version:old.version+1};if(data.record.referenceUses===null)delete value.referenceUses;db.set(id,value);return clone(value);}
    throw Error('Unexpected request '+url);
  };
  await evaluateBrowserModule(dom,entry,"\nimport {setLanguage} from './i18n.js';globalThis.__create=createCatalogEditor;globalThis.__setLanguage=setLanguage;");
  const editor=w.__create({container:d.querySelector('#host'),api,onSaved:r=>saved.push(clone(r)),onCancel:()=>cancelled.push(true)});
  const field=(key,value)=>{const el=d.querySelector(`[data-editor-field="${key}"]`);el.value=value;el.dispatchEvent(new w.Event('input',{bubbles:true}));return el;};
  const change=(selector,value)=>{const el=d.querySelector(selector);if(el.type==='checkbox')el.checked=value;else el.value=value;el.dispatchEvent(new w.Event('change',{bubbles:true}));return el;};
  const click=action=>{const el=d.querySelector(`[data-editor-action="${action}"]`);assert.ok(el,action);el.click();};
  const cleanup=()=>{assert.deepEqual(errors,[]);editor.destroy();w.close();};
  return {dom,w,d,db,calls,saved,cancelled,confirmations,canvasSizes,bitmaps,editor,field,change,click,cleanup,setSaveError:e=>saveError=e,setUploadError:e=>uploadError=e,setSaveWait:p=>saveWait=p,setAnswer:v=>answer=v};
}
async function main(){
  let p=await setup();let escapedClicks=0;p.d.addEventListener('click',()=>escapedClicks++);
  assert.equal(p.editor.hasUnsavedChanges(),false);
  assert.equal(await p.editor.open('series/30'),true);assert.equal(p.editor.isOpen(),true);
  assert.equal(p.editor.hasUnsavedChanges(),false);
  assert.equal(p.calls[0].url,'/api/admin/records?id=series%2F30');
  assert.equal(p.d.querySelectorAll('[data-editor-area]:checked').length,0,'Inferred uses must not become explicit application areas');
  const original=clone(p.db.get('series/30'));p.field('name','更新名称');assert.equal(p.editor.hasUnsavedChanges(),true);assert.equal(p.confirmations.length,0);p.click('save');await until(()=>p.saved.length===1,'save');
  const write=p.calls.find(x=>x.data?.action==='save');assert.deepEqual(write.data,{action:'save',id:'series/30',version:7,record:{name:'更新名称'}});
  const current=p.saved[0];for(const key of ['source','rawCells','provenance','formulaCachedValues','legacyPrivate','extraLegacyRaw','images','productDetails','validUntil','productCode'])assert.deepEqual(current[key],original[key],key);
  assert.equal(current.version,8);assert.equal(p.editor.isOpen(),false);assert.equal(p.editor.hasUnsavedChanges(),false);assert.equal(escapedClicks,0);p.cleanup();
  checks.push('A single record is fetched by encoded id; sparse versioned saves preserve legacy fields, immutable evidence, image metadata, detail rows and stable product codes');

  p=await setup();await p.editor.open('series/30');const name=p.field('name','保留草稿');
  p.setSaveError(Object.assign(new Error('Conflict'),{status:409}));p.click('save');await until(()=>p.d.querySelector('[data-editor-status]').classList.contains('is-error'),'conflict');
  assert.equal(p.d.querySelector('[data-editor-field="name"]'),name);assert.equal(name.value,'保留草稿');assert.equal(p.saved.length,0);assert.match(p.d.querySelector('[data-editor-status]').textContent,/修改仍保留/);assert.equal(p.calls.filter(c=>c.data?.action==='save').length,1);assert.equal(p.editor.hasUnsavedChanges(),true);assert.equal(p.confirmations.length,0);
  p.setAnswer(false);p.click('cancel');assert.equal(p.cancelled.length,0);assert.equal(p.editor.isOpen(),true);
  p.w.__setLanguage('en');assert.equal(p.d.querySelector('[data-editor-field="name"]'),name);assert.equal(name.value,'保留草稿');assert.match(p.d.querySelector('[data-editor-status]').textContent,/draft is kept/);assert.match(p.d.querySelector('.catalog-editor-areas').textContent,/Application areas/);
  assert.deepEqual([...p.d.querySelectorAll('[data-editor-text]')].filter(el=>/[\u3400-\u9fff]/.test(el.textContent)).map(el=>el.dataset.editorText),[],'All editor controls have English labels');
  p.setAnswer(true);p.click('cancel');assert.equal(p.cancelled.length,1);assert.equal(p.editor.isOpen(),false);assert.equal(p.editor.hasUnsavedChanges(),false);assert.equal(p.db.get('series/30').name,'沐浴露瓶');p.cleanup();
  checks.push('Version conflicts preserve the draft and do not replay writes; cancellation is guarded and switching language preserves exact input nodes and values');

  p=await setup();await p.editor.open('series/30');p.field('quoteRaw','改价原文');let release;p.setSaveWait(new Promise(resolve=>release=resolve));p.click('save');
  assert.equal(p.editor.hasUnsavedChanges(),true);assert.equal(p.confirmations.length,0);
  assert.equal(p.editor.canClose(),false);assert.equal(p.d.querySelector('[data-editor-action="cancel"]').disabled,true);p.click('save');
  p.setSaveError(Object.assign(new Error('暂时无法连接系统，请检查网络后重试。'),{code:'network'}));release();await until(()=>!p.d.querySelector('[data-editor-action="save"]').disabled,'network failure');
  assert.equal(p.calls.filter(c=>c.data?.action==='save').length,1);assert.equal(p.d.querySelector('[data-editor-field="quoteRaw"]').value,'改价原文');assert.equal(p.editor.isOpen(),true);p.cleanup();
  checks.push('Busy editors block closing and duplicate saves; network failure leaves the original draft editable without automatic retries');

  p=await setup();await p.editor.open(null);assert.equal(p.calls.length,0);p.click('save');assert.match(p.d.querySelector('[data-editor-status]').textContent,/产品名称/);assert.equal(p.calls.length,0);
  p.w.__setLanguage('en');assert.match(p.d.querySelector('.catalog-editor-code').textContent,/assigned when saved/);p.w.__setLanguage('zh');
  p.field('name','新增瓶');p.field('materials','PET、PP');p.field('uses','洗发水，沐浴露');p.change('[data-editor-area="head"]',true);p.change('[data-editor-area="body"]',true);p.click('save');await until(()=>p.saved.length,'new product');
  assert.equal(p.calls[0].data.id,undefined);assert.equal(p.calls[0].data.version,0);assert.equal(p.calls[0].data.record.productCode,undefined);assert.deepEqual(p.calls[0].data.record.bodyAreas,['body','head']);assert.deepEqual(p.calls[0].data.record.materials,['PET','PP']);assert.equal(p.saved[0].productCode,'YZ-BC-000999');p.cleanup();
  checks.push('New products validate names, submit explicit multiple application areas and tags, and use only the server-assigned product code');

  const r30=fixture(),r50={...fixture('series/50','YZ-BC-000050'),specificationRaw:'50 mL',capacityMl:50,quoteRaw:'50mL报价'};
  p=await setup([r30,r50]);await p.editor.open('series/50');p.field('quoteRaw','50mL新报价');p.click('save');await until(()=>p.saved.length,'specific variant');assert.equal(p.calls.at(-1).data.id,'series/50');assert.deepEqual(p.db.get('series/30'),r30);assert.equal(p.saved[0].productCode,'YZ-BC-000050');p.cleanup();
  checks.push('Editing a chosen specification writes only its original record id and version, leaving all other specifications unchanged');

  p=await setup();await p.editor.open('series/30');
  assert.equal(p.d.querySelector('[data-editor-action="first-image"][data-editor-index="1"]').disabled,true);
  p.change('[data-editor-image-field="clientVisible"][data-editor-index="0"]',false);
  const files=p.d.querySelector('[data-editor-upload]');Object.defineProperty(files,'files',{value:[new p.w.File(['sample'],'new-image.png',{type:'image/png'})]});files.dispatchEvent(new p.w.Event('change',{bubbles:true}));
  await until(()=>p.d.querySelectorAll('[data-editor-image-field="clientVisible"]').length===3&&!p.d.querySelector('[data-editor-action="save"]').disabled,'upload');
  assert.equal(p.d.querySelector('[data-editor-image-field="clientVisible"][data-editor-index="2"]').checked,false);assert.deepEqual(p.canvasSizes,[{width:1600,height:1067,type:'image/jpeg',quality:.9}]);assert.equal(p.bitmaps[0].closed,true);
  p.change('[data-editor-image-field="clientVisible"][data-editor-index="2"]',true);p.d.querySelector('[data-editor-action="first-image"][data-editor-index="2"]').click();p.click('save');await until(()=>p.saved.length,'image save');
  const imgs=p.saved[0].images;assert.equal(imgs[0].path,'uploads/abcdef0123456789.jpg');assert.equal(imgs[0].clientVisible,true);assert.equal(imgs[1].clientVisible,false);assert.equal(imgs[1].cell,'C9');assert.equal(imgs[1].mapping,'original');assert.equal(imgs[2].sourceCell,'D9');assert.equal(imgs[2].uncertain,true);assert.equal(imgs[2].clientVisible,false);p.cleanup();
  checks.push('Uploads are compressed to bounded JPEGs, start unapproved, and support explicit per-image approval and ordering without promoting source-page evidence');

  p=await setup();await p.editor.open('series/30');p.click('add-detail');p.change('[data-editor-detail-field="label"][data-editor-index="1"]','高度');p.change('[data-editor-detail-field="value"][data-editor-index="1"]','100 mm');p.change('[data-editor-detail-field="sourceField"][data-editor-index="1"]','specificationRaw');p.change('[data-editor-detail-field="evidence"][data-editor-index="1"]','已确认原文');p.click('save');await until(()=>p.saved.length,'detail save');
  assert.deepEqual(p.saved[0].productDetails[0],fixture().productDetails[0]);assert.equal(p.saved[0].productDetails[1].evidence,'已确认原文');assert.deepEqual(Object.keys(p.calls.at(-1).data.record),['productDetails']);p.cleanup();
  checks.push('Specification rows retain existing labels and evidence while adding editable source-backed details');

  p=await setup();await p.editor.open(null);p.field('name','不保存的新产品');p.setAnswer(true);p.click('cancel');assert.equal(p.saved.length,0);assert.equal(p.calls.length,0);assert.equal(p.db.size,1);assert.equal(p.cancelled.length,1);p.cleanup();
  checks.push('Cancelling a new product performs no write and leaves the catalogue unchanged');
  p=await setup([{...fixture(),bottleType:'膏霜罐'}]);await p.editor.open('series/30');
  assert.equal(p.d.querySelector('[data-editor-reference-mode]').value,'automatic');assert.equal(p.d.querySelector('[data-editor-reference-tags]').disabled,true);
  p.change('[data-editor-reference-mode]','disabled');p.click('save');await until(()=>p.saved.length,'disable reference');
  assert.deepEqual(p.calls.at(-1).data.record,{referenceUses:[]});assert.deepEqual(p.saved[0].uses,['沐浴露']);assert.deepEqual(p.saved[0].productDetails,fixture().productDetails);p.cleanup();
  p=await setup([{...fixture(),referenceUses:[]}]);await p.editor.open('series/30');p.change('[data-editor-reference-mode]','manual');
  assert.equal(p.d.querySelector('[data-editor-reference-tags]').disabled,false);p.change('[data-editor-reference-tags]','面霜、眼霜，面霜');p.click('save');await until(()=>p.saved.length,'manual reference');
  assert.deepEqual(p.calls.at(-1).data.record,{referenceUses:['面霜','眼霜']});p.cleanup();
  p=await setup([{...fixture(),referenceUses:['面霜','眼霜']}]);await p.editor.open('series/30');p.change('[data-editor-reference-mode]','automatic');p.click('save');await until(()=>p.saved.length,'restore automatic reference');
  assert.deepEqual(p.calls.at(-1).data.record,{referenceUses:null});assert.equal(Object.hasOwn(p.saved[0],'referenceUses'),false);p.cleanup();
  checks.push('Reference uses have automatic, manual and disabled modes; versioned sparse saves preserve record evidence and restore automatic with an explicit null');
  console.log(JSON.stringify({passed:true,checks,liveWebsiteRequests:0},null,2));
}
main().catch(error=>{console.error(error);process.exitCode=1;});
