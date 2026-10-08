const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const {JSDOM, VirtualConsole} = require('jsdom');
const {evaluateBrowserModule} = require('./module-loader.cjs');
const root = path.resolve(__dirname, '../../server-reference/public');
const shared = {path: 'media/shared.jpg', role: 'product', imageScope: 'same_style_variants'};
const family = [30, 50, 30, 50].map((capacityMl, n) => ({
  id: `group-${n}`, productCode: `YZ-BC-0000${14+n}`, kind: 'package', name: `香水喷雾瓶${capacityMl}ml`,
  capacityMl, materials: ['PET'], supplierRaw: n < 2 ? '供应商甲' : '供应商乙',
  quoteRaw: `独立报价-${n}，裸瓶单价${1.1+n/10}元`, source: {workbook: '报价表.xlsx', row: n+2},
  images: [shared, ...(n === 0 ? [shared, {path: 'media/30.jpg', role: 'product', imageScope: 'single_product'}] : []),
    ...(n === 1 ? [{path: 'media/50.jpg', role: 'product', imageScope: 'single_product'}] : [])]
}));
const other = Array.from({length: 23}, (_, n) => ({id: `other-${n}`, kind: 'package',
  name: `其他瓶${n}`, productCode: `YZ-BC-0010${String(n).padStart(2, '0')}`, materials: ['PP'], images: [shared]}));
const group = {id: 'reviewed-perfume', name: '香水喷雾瓶', recordIds: family.map(r => r.id),
  specs: [{label: '30 mL', recordIds: ['group-0', 'group-2']}, {label: '50 mL', recordIds: ['group-1', 'group-3']}],
  primaryImage: {path: 'uploads/labelled.jpg', role: 'product', imageScope: 'same_style_variants'}};
const sourceRecords = [...family, ...other];
const checks = [];
async function until(test, message) {
  const end = Date.now()+4000;
  while (!test()) {if(Date.now()>end) throw Error('Timeout: '+message); await new Promise(r=>setTimeout(r,5));}
}
async function open(search = '', reviewedGroup = group, fixtureRecords = sourceRecords) {
  const errors = [], posts = [], downloads = [], console = new VirtualConsole();
  console.on('jsdomError', error => errors.push(error.message));
  const dom = new JSDOM(fs.readFileSync(path.join(root, 'index.html'), 'utf8'), {
    url: 'https://catalog.test/'+search, runScripts: 'outside-only', pretendToBeVisual: true, virtualConsole: console
  });
  const w=dom.window, d=w.document;
  w.matchMedia=()=>({matches:true,addEventListener(){}}); w.scrollTo=()=>{};
  w.HTMLElement.prototype.scrollIntoView=function(){};
  w.HTMLDialogElement.prototype.showModal=function(){this.open=true};
  w.HTMLDialogElement.prototype.close=function(){this.open=false};
  w.URL.createObjectURL=blob=>{downloads.push(blob);return 'blob:fixture'};
  w.URL.revokeObjectURL=()=>{};
  w.HTMLAnchorElement.prototype.click=function(){};
  w.fetch=async (url, options={}) => {
    if(options.method==='POST') posts.push({path:url, body:JSON.parse(options.body)});
    const body=url==='/api/session'?{role:'employee',username:'test-employee',csrf:'fixture'}:
      url==='/api/catalog'?{records:fixtureRecords,settings:{}}:
      url==='/api/preferences'?{favorites:['group-3']}:
      url==='/api/image-search/status'?{available:true,indexed_records:27,indexed_images:3}:{ok:true};
    return new Response(JSON.stringify(body), {status:200,headers:{'Content-Type':'application/json'}});
  };
  // Import/evaluate the real module graph. Only fixture data and browser I/O are supplied.
  await evaluateBrowserModule(dom, path.join(root,'app.js'),
    `\nreviewedProductGroups.splice(0,reviewedProductGroups.length,...${JSON.stringify(Array.isArray(reviewedGroup)?reviewedGroup:[reviewedGroup])});\nwindow.groupTest={imageSearch, filtered, displayed, render, groupGalleryImages, createProductGroupIndex, groupProducts, imagePath, getIndex:()=>productGroupIndex, getRecords:()=>records};`);
  await until(()=>d.querySelector('#searchForm')&&d.querySelector('#favCount').textContent==='1','catalogue and preferences');
  return {dom,w,d,errors,posts,downloads};
}
function search(p, value) {
  p.d.querySelector('#query').value=value;
  p.d.querySelector('#searchForm').dispatchEvent(new p.w.Event('submit',{bubbles:true,cancelable:true}));
}
function reset(p){p.d.querySelector('[data-action=reset]').click();}
(async()=>{
  let p=await open();
  try {
    assert.equal(p.w.groupTest.displayed().length,24);
    assert.equal(p.d.querySelectorAll('.card').length,20);
    assert.equal(p.d.querySelectorAll('.card-title')[0].textContent,'香水喷雾瓶（多规格）');
    assert.match(p.d.querySelector('.results-top').textContent,/24.*27/s);
    assert.equal(p.d.querySelector('.photo img').getAttribute('src'),'/uploads/labelled.jpg');
    assert.equal(p.d.querySelector('.image-count').textContent,'4 张图');
    assert.equal(p.d.querySelectorAll('.group-image-mapping-note').length,0);
    assert.equal(p.w.groupTest.getIndex().get('group-0').imageMappingPending,false);
    assert.equal(p.d.querySelector('.favorite').dataset.favorite,'group-3');
    p.d.querySelector('[data-page-control=next]').click();
    assert.equal(p.d.querySelectorAll('.card').length,4);
    assert.match(p.d.querySelector('.page-range').textContent,/21–24.*2 \/ 2/);
    reset(p);
    p.d.querySelector('[data-action=layout]').click();
    assert.equal(p.d.querySelectorAll('#catalogPageContent tbody tr').length,20);
    assert.equal(p.d.querySelectorAll('#catalogPageContent [data-detail="group-1"]').length,0);
    p.d.querySelector('[data-action=layout]').click();
    checks.push('Reviewed families occupy one card/table row; shared-page products stay separate; pagination counts groups');

    search(p,'YZ-BC-000017');
    assert.equal(p.d.querySelectorAll('.card').length,1);
    assert.equal(p.d.querySelector('.card-title').dataset.detail,'group-3');
    p.d.querySelector('.card-title').click();
    assert.equal(p.d.querySelectorAll('.group-option').length,4);
    assert.equal(p.d.querySelector('.group-option.active').dataset.detail,'group-3');
    assert.match(p.d.querySelector('.pricing-section').textContent,/独立报价-3/);
    assert.doesNotMatch(p.d.querySelector('.pricing-section').textContent,/独立报价-0/);
    p.d.querySelector('.group-option[data-detail="group-0"]').click();
    assert.match(p.d.querySelector('.pricing-section').textContent,/独立报价-0/);
    assert.equal(p.d.querySelector('.detail-actions [data-favorite]').dataset.favorite,'group-0');
    assert.equal(p.d.querySelectorAll('.thumbnails button').length,4);
    p.d.querySelector('[data-image="/media/shared.jpg"]').click();
    assert.equal(p.d.querySelectorAll('#imageAssociations .group-image-source').length,4);
    assert.match(p.d.querySelector('#imageAssociations').textContent,/第 2 行/);
    assert.match(p.d.querySelector('#imageAssociations').textContent,/第 5 行/);
    p.d.querySelector('[data-language-switch]').click();
    await until(()=>p.d.querySelector('.group-selector h3').textContent==='Sizes and quotes','group translation');
    assert.match(p.d.querySelector('#modal .dialog-head h2').textContent,/香水喷雾瓶.*Multiple sizes/);
    assert.equal(p.d.querySelector('.group-option.active').dataset.detail,'group-0');
    assert.equal(p.d.querySelector('#detailPhoto img').getAttribute('src'),'/media/shared.jpg');
    p.d.querySelector('[data-language-switch]').click();
    await until(()=>p.d.querySelector('.group-selector h3').textContent==='同款规格与报价','group Chinese restored');
    checks.push('Exact SKU lookup and detail switching preserve individual IDs, quotes, favorites, and all deduplicated-image sources');
    p.d.querySelector('#modal').close();

    reset(p);
    p.d.querySelector('[data-filter="capacity"][value="50"]').click();
    assert.deepEqual(Array.from(p.w.groupTest.filtered(),r=>r.id),['group-1','group-3']);
    assert.equal(p.d.querySelector('.card-title').dataset.detail,'group-1');
    p.d.querySelector('[data-action=export]').click();
    const csv=await new Promise((resolve,reject)=>{const reader=new p.w.FileReader();reader.onload=()=>resolve(reader.result);reader.onerror=reject;reader.readAsText(p.downloads[0]);});
    assert.match(csv,/group-1/);assert.match(csv,/group-3/);assert.doesNotMatch(csv,/group-0/);
    assert.equal(csv.trim().split('\r\n').length,3);
    reset(p);search(p,'香水喷雾瓶 30ml');
    assert.deepEqual(Array.from(p.w.groupTest.filtered(),r=>r.id),['group-0','group-2']);
    assert.equal(p.d.querySelectorAll('.card').length,1);
    assert.equal(p.d.querySelector('.favorite').dataset.favorite,'group-0');
    checks.push('Name/capacity filters match SKUs before merging; CSV exports each matching underlying record');

    reset(p);
    p.w.groupTest.imageSearch.matches=new p.w.Map([['group-3',{rank:0,image_path:'media/shared.jpg'}],['group-0',{rank:2,image_path:'media/30.jpg'}]]);
    p.w.groupTest.render();
    assert.equal(p.d.querySelectorAll('.card').length,1);
    assert.equal(p.d.querySelector('.card-title').dataset.detail,'group-3');
    assert.equal(p.d.querySelector('.photo img').getAttribute('src'),'/media/shared.jpg');
    reset(p);
    p.d.querySelector('[data-view=favorites]').click();
    await until(()=>p.d.querySelector('.card-title')?.dataset.detail==='group-3','favorite filtered before grouping');
    assert.equal(p.d.querySelectorAll('.card').length,1);
    p.d.querySelector('.favorite').click();
    await until(()=>p.posts.length&&p.d.querySelectorAll('.card').length===0,'favorite removal');
    assert.deepEqual(p.posts.at(-1).body,{favorites:[]});
    checks.push('Image matching retains SKU rank and matched image; favorites show and modify original record IDs');

    const index=p.w.groupTest.getIndex(), all=p.w.groupTest.getRecords(), original=JSON.stringify(all);
    const images=p.w.groupTest.groupGalleryImages(all[0],index,p.w.groupTest.imagePath);
    assert.equal(images.length,4);
    assert.equal(images.find(i=>i.path==='media/shared.jpg')._groupSources.length,5);
    assert.equal(JSON.stringify(all),original);
    const duplicates=p.w.groupTest.createProductGroupIndex(all,[{recordIds:['group-0','group-2','missing'],name:'同规格资料'}]);
    assert.equal(duplicates.get('group-0').multiSpec,false);
    assert.equal(p.w.groupTest.groupProducts(all,duplicates).length,26);
    assert.equal(p.w.groupTest.createProductGroupIndex(all,[]).size,0);
    assert.deepEqual(p.errors,[]);
    checks.push('Same-size duplicates are distinct from multi-size families; missing IDs are ignored and original records/images never mutate');
  } finally {p.dom.window.close();}
  p=await open('?code=YZ-BC-000017');
  try {
    assert.equal(p.d.querySelectorAll('.card').length,1);
    assert.equal(p.d.querySelector('.card-title').dataset.detail,'group-3');
    p.d.querySelector('.card-title').click();
    assert.equal(p.d.querySelector('.group-option.active').dataset.detail,'group-3');
    assert.match(p.d.querySelector('.pricing-section').textContent,/独立报价-3/);
    checks.push('Code deep links keep the precise SKU visible and selected within its family');
  } finally {p.dom.window.close();}
  const pendingLabel='系列参考图 · 容量对应待确认';
  p=await open('', {...group,imageMappingPending:true,primaryImage:{...group.primaryImage,
    imageScope:'unresolved',label:pendingLabel}});
  try {
    assert.equal(p.d.querySelector('.photo .image-label').textContent,pendingLabel);
    assert.equal(p.d.querySelector('.card > .group-image-mapping-note').textContent,'规格见标签，图中对应待核对');
    assert.match(p.d.querySelector('.card .tags').textContent,/30 mL.*50 mL/);
    p.d.querySelector('.card-title').click();
    assert.equal(p.d.querySelector('#detailPhoto .image-label').textContent,pendingLabel);
    assert.equal(p.d.querySelector('#imageAssociations').textContent,pendingLabel);
    assert.equal(p.d.querySelector('.detail-visual > .group-image-mapping-note').textContent,'规格见标签，图中对应待核对');
    const thumbnail=p.d.querySelector('[data-image="/uploads/labelled.jpg"]');
    assert.match(thumbnail.closest('.thumbnails').previousElementSibling.textContent,/原图参考/);
    assert.equal(thumbnail.dataset.imageLabel,pendingLabel);
    p.d.querySelector('[data-language-switch]').click();
    await until(()=>p.d.querySelector('.group-image-mapping-note').textContent==='See size tags; image mapping needs verification','mapping-note translation');
    assert.equal(p.d.querySelector('#detailPhoto .image-label').textContent,'Series reference · Size mapping unconfirmed');
    p.d.querySelector('[data-language-switch]').click();
    await until(()=>p.d.querySelector('#detailPhoto .image-label').textContent===pendingLabel,'mapping label restored');
    checks.push('Explicit pending mappings keep accurate size tags, show a bilingual caution, and preserve custom unresolved-image labels and reference classification');

    const photo=p.d.querySelector('#detailPhoto img');
    photo.dispatchEvent(new p.w.Event('error'));
    assert.equal(photo.getAttribute('src'),'/media/shared.jpg');
    assert.equal(p.d.querySelector('#originalImageLink').getAttribute('href'),'/media/shared.jpg');
    assert.equal(p.d.querySelectorAll('#imageAssociations .group-image-source').length,4);
    assert.doesNotMatch(p.d.querySelector('#imageAssociations').textContent,/系列参考图/);
    photo.dispatchEvent(new p.w.Event('error'));
    assert.equal(photo.getAttribute('src'),'/media/30.jpg');
    assert.equal(p.d.querySelectorAll('#imageAssociations .group-image-source').length,1);
    assert.equal(p.d.querySelector('#imageAssociations [data-detail]').dataset.detail,'group-0');
    photo.dispatchEvent(new p.w.Event('error'));
    assert.equal(photo.getAttribute('src'),'/media/50.jpg');
    assert.equal(p.d.querySelector('#imageAssociations [data-detail]').dataset.detail,'group-1');
    photo.dispatchEvent(new p.w.Event('error'));
    assert.equal(photo.hidden,true);
    assert.equal(p.d.querySelector('#originalImageLink').hidden,true);
    assert.equal(p.d.querySelector('#imageAssociations').textContent,'');
    assert.equal(p.d.querySelector('.group-option.active').dataset.detail,'group-0');
    assert.match(p.d.querySelector('.pricing-section').textContent,/独立报价-0/);
    thumbnail.click();
    assert.equal(p.d.querySelector('#detailPhoto img').hidden,false);
    assert.equal(p.d.querySelector('#originalImageLink').hidden,false);
    assert.equal(p.d.querySelector('#imageAssociations').textContent,pendingLabel);
    assert.deepEqual(p.errors,[]);
    checks.push('Image failures update fallback labels, source associations and original links; exhausted galleries hide stale links without changing the selected SKU quote');
  } finally {p.dom.window.close();}
  p=await open('', {...group,imageAliases:{'uploads/labelled.jpg':'media/shared.jpg',
    'media/30.jpg':'media/shared.jpg','media/50.jpg':'media/missing.jpg'}});
  try {
    const all=p.w.groupTest.getRecords(),original=JSON.stringify(all),index=p.w.groupTest.getIndex();
    const images=p.w.groupTest.groupGalleryImages(all[0],index,p.w.groupTest.imagePath);
    assert.equal(images.length,2);
    assert.deepEqual(Array.from(images,i=>i.path),['media/shared.jpg','media/50.jpg']);
    assert.equal(images[0]._groupSources.length,6);
    assert.deepEqual(Array.from(images[0]._groupPaths),['/uploads/labelled.jpg','/media/shared.jpg','/media/30.jpg']);
    assert.equal(images[0]._groupSources.find(s=>s.image.path==='media/30.jpg').recordId,'group-0');
    assert.equal(images[0]._groupSources.find(s=>s.image.path==='media/30.jpg').image.imageScope,'single_product');
    assert.equal(p.d.querySelector('.photo img').getAttribute('src'),'/uploads/labelled.jpg');
    assert.equal(p.d.querySelector('.image-count').textContent,'2 张图');
    p.d.querySelector('.card-title').click();
    assert.equal(p.d.querySelectorAll('.thumbnails button').length,2);
    assert.equal(p.d.querySelectorAll('#imageAssociations .group-image-source').length,4);
    p.d.querySelector('#modal').close();
    p.w.groupTest.imageSearch.matches=new p.w.Map([['group-0',{rank:0,image_path:'media/30.jpg'}]]);
    p.w.groupTest.render();
    assert.equal(p.d.querySelector('.photo img').getAttribute('src'),'/media/30.jpg');
    p.d.querySelector('.card-title').click();
    assert.equal(p.d.querySelector('#detailPhoto img').getAttribute('src'),'/media/30.jpg');
    assert.equal(p.d.querySelector('#originalImageLink').getAttribute('href'),'/media/30.jpg');
    assert.equal(p.d.querySelector('#downloadImageLink').getAttribute('href'),'/media/30.jpg?download=YZ-BC-000014-1.jpg');
    assert.equal(p.d.querySelector('#downloadImageLink').download,'YZ-BC-000014-1.jpg');
    assert.equal(p.d.querySelectorAll('#imageAssociations .group-image-source').length,4);
    const external={id:'external-only',kind:'package',images:[{path:'media/outside.jpg'}]};
    const scoped=p.w.groupTest.createProductGroupIndex([...all,external],[{...group,imageAliases:{'media/50.jpg':'media/outside.jpg'}}]);
    assert.equal(p.w.groupTest.groupGalleryImages(all[0],scoped,p.w.groupTest.imagePath).length,4);
    const cyclic=p.w.groupTest.createProductGroupIndex(all,[{...group,imageAliases:{'media/30.jpg':'media/50.jpg','media/50.jpg':'media/30.jpg'}}]);
    assert.equal(p.w.groupTest.groupGalleryImages(all[0],cyclic,p.w.groupTest.imagePath).length,4);
    assert.equal(JSON.stringify(all),original);
    assert.deepEqual(p.errors,[]);
    checks.push('Reviewed image aliases deduplicate only within a group, preserve every original association and exact primary/search path, and retain images when targets are missing or cyclic');
  } finally {p.dom.window.close();}
  const polluted=family.map(r=>({...r,name:'同款喷雾瓶',searchText:'整页OCR：10ml、30ml、50ml、150ml',
    extraRaw:'10ml给客户报价0.6元；30ml给客户报价1.6元；50ml给客户报价1.7元'}));
  const weight=[30,50].map((n,i)=>({id:`weight-${i}`,kind:'package',name:'JJ-8003',
    specificationRaw:`${n}g`,quoteRaw:`克重报价-${n}`,searchText:'整页规格：30g、50g、150g'}));
  const compound=['50-15g','50-20g'].map((spec,i)=>({id:`compound-${i}`,kind:'package',name:'复合规格瓶',
    specificationRaw:spec,searchText:'整页规格：50-15g、50-20g'}));
  const litre=['800ml','1L'].map((spec,i)=>({id:`litre-${i}`,kind:'package',name:'Pe化工瓶',
    specificationRaw:spec,searchText:'整页规格：800ml、1L'}));
  const reviewed=[{...group,name:'同款喷雾瓶'},
    {id:'weight-family',name:'JJ-8003',recordIds:weight.map(r=>r.id),specs:weight.map((r,i)=>({label:`${[30,50][i]} g`,recordIds:[r.id]}))},
    {id:'compound-family',name:'复合规格瓶',recordIds:compound.map(r=>r.id),specs:compound.map(r=>({label:r.specificationRaw,recordIds:[r.id]}))},
    {id:'litre-family',name:'Pe化工瓶',recordIds:litre.map(r=>r.id),specs:litre.map(r=>({label:r.specificationRaw,recordIds:[r.id]}))}];
  // This ungrouped item intentionally retains full-text OCR search semantics.
  const unreviewed={id:'unreviewed',kind:'package',name:'未归并原始资料',searchText:'原文30ml与30g'};
  p=await open('',reviewed,[...polluted,...weight,...compound,...litre,unreviewed]);
  try {
    for(const query of ['30ml','30 mL','30毫升','３０ ＭＬ']){
      search(p,'同款喷雾瓶 '+query);
      assert.deepEqual(Array.from(p.w.groupTest.filtered(),r=>r.id),['group-0','group-2']);
      assert.equal(p.d.querySelectorAll('.card').length,1);
      assert.equal(p.d.querySelector('.card-title').dataset.detail,'group-0');
    }
    search(p,'同款喷雾瓶 50ml');
    assert.deepEqual(Array.from(p.w.groupTest.filtered(),r=>r.id),['group-1','group-3']);
    p.d.querySelector('.card-title').click();
    assert.equal(p.d.querySelector('.group-option.active').dataset.detail,'group-1');
    assert.match(p.d.querySelector('.pricing-section').textContent,/独立报价-1/);
    p.d.querySelector('#modal').close();
    p.d.querySelector('[data-action=export]').click();
    const csv=await new Promise((resolve,reject)=>{const reader=new p.w.FileReader();reader.onload=()=>resolve(reader.result);reader.onerror=reject;reader.readAsText(p.downloads[0]);});
    assert.match(csv,/group-1/);assert.match(csv,/group-3/);assert.doesNotMatch(csv,/group-0|group-2/);
    for(const query of ['10ml','150ml','30g']){
      search(p,'同款喷雾瓶 '+query);
      assert.equal(p.w.groupTest.displayed().length,0);
    }
    for(const query of ['30g','30 g','30克','３０ Ｇ']){
      search(p,'JJ-8003 '+query);
      assert.deepEqual(Array.from(p.w.groupTest.filtered(),r=>r.id),['weight-0']);
      assert.equal(p.d.querySelectorAll('.card').length,1);
    }
    search(p,'JJ-8003 50 g');assert.equal(p.d.querySelector('.card-title').dataset.detail,'weight-1');
    search(p,'JJ-8003 150g');assert.equal(p.w.groupTest.displayed().length,0);
    search(p,'复合规格瓶 50-20g');assert.deepEqual(Array.from(p.w.groupTest.filtered(),r=>r.id),['compound-1']);
    search(p,'Pe化工瓶 1L');assert.deepEqual(Array.from(p.w.groupTest.filtered(),r=>r.id),['litre-1']);
    search(p,'未归并原始资料 30ml');assert.deepEqual(Array.from(p.w.groupTest.filtered(),r=>r.id),['unreviewed']);
    search(p,'未归并原始资料 30 g');assert.deepEqual(Array.from(p.w.groupTest.filtered(),r=>r.id),['unreviewed']);
    reset(p);p.d.querySelector('[data-filter="capacity"][value="30"]').click();
    p.d.querySelector('[data-filter="capacity"][value="50"]').click();
    assert.equal(p.w.groupTest.displayed().length,1);
    assert.deepEqual(Array.from(p.w.groupTest.filtered(),r=>r.id),['group-0','group-1','group-2','group-3']);
    assert.deepEqual(p.errors,[]);
    checks.push('Each reviewed SKU matches only its own size labels despite mixed OCR/quote text; mL and g aliases, exact compound sizes, correct selected quotes/CSV, multi-size OR filters and ungrouped search remain intact');
  } finally {p.dom.window.close();}
  const revised = polluted.map((r,index)=>({...r,version:99,specificationRaw:index===2?'旧字段150ml':'旧字段30ml'}));
  revised[0]={...revised[0],capacityMl:80,specificationOverride:{label:'80 mL',sourceField:'capacityMl'}};
  revised[1]={...revised[1],specificationRaw:'80 g',specificationOverride:{label:'80 g',sourceField:'specificationRaw'}};
  revised[3]={...revised[3],specificationRaw:'',specificationOverride:{label:'规格待补充',sourceField:'specificationRaw'}};
  p=await open('',{...group,name:'同款喷雾瓶'},revised);
  try {
    const records=p.w.groupTest.getRecords(),before=JSON.stringify(records),manifest=JSON.stringify(group);
    const effective=p.w.groupTest.getIndex().get('group-0');
    assert.deepEqual(Array.from(effective.specs,s=>({label:s.label,recordIds:Array.from(s.recordIds)})),[
      {label:'30 mL',recordIds:['group-2']},{label:'80 mL',recordIds:['group-0']},
      {label:'80 g',recordIds:['group-1']},{label:'规格待补充',recordIds:['group-3']}
    ]);
    assert.match(p.d.querySelector('.card .tags').textContent,/30 mL.*80 mL.*80 g.*规格待补充/);
    for(const [query,ids] of [['80ml',['group-0']],['80g',['group-1']],['30ml',['group-2']],
                             ['50ml',[]],['150ml',[]],['10ml',[]]]) {
      search(p,'同款喷雾瓶 '+query);
      assert.deepEqual(Array.from(p.w.groupTest.filtered(),r=>r.id),ids,query);
    }
    search(p,'同款喷雾瓶 80ml');p.d.querySelector('.card-title').click();
    assert.equal(p.d.querySelector('.group-option.active strong').textContent,'80 mL');
    assert.match(p.d.querySelector('.pricing-section').textContent,/独立报价-0/);
    p.d.querySelector('.group-option[data-detail="group-1"]').click();
    assert.equal(p.d.querySelector('.group-option.active strong').textContent,'80 g');
    assert.match(p.d.querySelector('.pricing-section').textContent,/独立报价-1/);
    p.d.querySelector('.group-option[data-detail="group-3"]').click();
    assert.equal(p.d.querySelector('.group-option.active strong').textContent,'规格待补充');
    p.d.querySelector('#modal').close();
    p.d.querySelector('[data-action=export]').click();
    const csv=await new Promise((resolve,reject)=>{const reader=new p.w.FileReader();reader.onload=()=>resolve(reader.result);reader.onerror=reject;reader.readAsText(p.downloads[0]);});
    assert.match(csv,/group-0/);assert.doesNotMatch(csv,/group-1|group-2|group-3/);
    const merged=p.w.groupTest.createProductGroupIndex(records.map(r=>r.id==='group-0'?{...r,specificationOverride:{label:'30 mL',sourceField:'capacityMl'}}:r),[group]);
    assert.deepEqual(Array.from(merged.get('group-0').specs.find(s=>s.label==='30 mL').recordIds).sort(),['group-0','group-2']);
    for(const invalid of [null,'80 mL',{label:'80 mL',sourceField:'searchText'},{label:'',sourceField:'capacityMl'}]) {
      const index=p.w.groupTest.createProductGroupIndex([{...family[0],specificationOverride:invalid},...family.slice(1)],[group]);
      assert.deepEqual(Array.from(index.get('group-0').specs.find(s=>s.recordIds.includes('group-0')).recordIds),['group-0','group-2']);
    }
    assert.equal(JSON.stringify(records),before);assert.equal(JSON.stringify(group),manifest);
    assert.deepEqual(p.errors,[]);
    checks.push('Server-owned specification overrides update card tags, each SKU button and exact size search together, preserve siblings/quotes/CSV, and never use record version or OCR as an override');
  } finally {p.dom.window.close();}
  p=await open('',{...group,recordIds:['group-3'],specs:[{label:'30 mL',recordIds:['group-3']},{label:'50 mL',recordIds:['group-3']}]},[revised[3]]);
  try {
    assert.equal(p.w.groupTest.getIndex().has('group-3'),true);
    assert.match(p.d.querySelector('.card .tags').textContent,/规格待补充/);
    for(const query of ['30ml','50ml','150ml']) {search(p,query);assert.equal(p.w.groupTest.filtered().length,0);}
    reset(p);p.d.querySelector('.card-title').click();
    assert.equal(p.d.querySelector('.group-option.active strong').textContent,'规格待补充');
    assert.deepEqual(p.errors,[]);
    checks.push('Reloading a cleared single-SKU group keeps its explicit unknown specification and cannot fall back to old reviewed labels or mixed OCR');
  } finally {p.dom.window.close();}
  console.log(JSON.stringify({passed:true,checks,liveWebsiteRequests:0},null,2));
})().catch(error=>{console.error(error);process.exitCode=1;});
