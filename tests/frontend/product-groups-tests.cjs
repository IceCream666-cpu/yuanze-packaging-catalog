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
async function open(search = '', reviewedGroup = group) {
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
      url==='/api/catalog'?{records:sourceRecords,settings:{}}:
      url==='/api/preferences'?{favorites:['group-3']}:
      url==='/api/image-search/status'?{available:true,indexed_records:27,indexed_images:3}:{ok:true};
    return new Response(JSON.stringify(body), {status:200,headers:{'Content-Type':'application/json'}});
  };
  // Import/evaluate the real module graph. Only fixture data and browser I/O are supplied.
  await evaluateBrowserModule(dom, path.join(root,'app.js'),
    `\nreviewedProductGroups.splice(0,reviewedProductGroups.length,${JSON.stringify(reviewedGroup)});\nwindow.groupTest={imageSearch, filtered, displayed, render, groupGalleryImages, createProductGroupIndex, groupProducts, imagePath, getIndex:()=>productGroupIndex, getRecords:()=>records};`);
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
  console.log(JSON.stringify({passed:true,checks,liveWebsiteRequests:0},null,2));
})().catch(error=>{console.error(error);process.exitCode=1;});
