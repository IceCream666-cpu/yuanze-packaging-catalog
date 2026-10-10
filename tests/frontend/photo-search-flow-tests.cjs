const {test}=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs');const path=require('node:path');
const {JSDOM,VirtualConsole}=require('jsdom');
const {evaluateBrowserModule}=require('./module-loader.cjs');
const {pictureFile,installImageBrowser}=require('./image-browser-fixture.cjs');
const root=path.resolve(__dirname,'../../server-reference/public');
const response=(body,status=200)=>new Response(JSON.stringify(body),{status,headers:{'Content-Type':'application/json'}});
async function until(fn,label){for(let n=0;n<600;n++){if(fn())return;await new Promise(resolve=>setTimeout(resolve,5));}throw Error('Timeout: '+label);}
function browser(filename,options={}){
  const errors=[],console=new VirtualConsole();console.on('jsdomError',error=>errors.push(error.message));
  const dom=new JSDOM(fs.readFileSync(path.join(root,filename),'utf8'),{url:'https://catalog.test/',runScripts:'outside-only',pretendToBeVisual:true,virtualConsole:console});
  const w=dom.window,d=w.document,operations=installImageBrowser(w,options);
  w.matchMedia=()=>({matches:false,addEventListener(){}});w.scrollTo=()=>{};w.HTMLElement.prototype.scrollIntoView=function(){};
  w.HTMLDialogElement.prototype.showModal=function(){this.open=true;};w.HTMLDialogElement.prototype.close=function(){this.open=false;this.dispatchEvent(new w.Event('close'));};
  return {dom,w,d,operations,errors};
}
const records=Array.from({length:620},(_,i)=>({id:'record-'+i,productCode:'YZ-BC-'+String(i+1).padStart(6,'0'),name:'精华瓶'+i,kind:'package',materials:[i%2?'玻璃':'PET'],capacityMl:30,uses:['精华液'],version:1,images:[{path:'media/p'+i+'.jpg',role:'product',imageScope:'single_product'}]}));
async function staff({paged=true,rows=records,groups=[],search=()=>({matches:records.map(row=>({record_id:row.id,image_path:row.images[0].path})),indexed_images:620,indexed_records:620}),decodeDelay=0}={}){
  const p=browser('index.html',{decodeDelay}),calls=[];
  const engine=(await evaluateBrowserModule(p.dom,path.join(root,'catalog-query.js'))).namespace,index=engine.prepareRecords({records:rows},groups),facets=engine.catalogFacets(index.records);
  p.w.fetch=async(url,options={})=>{
    calls.push({url:String(url),options});const parsed=new URL(url,'https://catalog.test'),params=parsed.searchParams;
    if(url==='/api/session')return response({role:'employee',username:'photo-test',csrf:'csrf',catalogPaging:paged});
    if(url==='/api/preferences')return response({favorites:[]});
    if(url==='/api/image-search/status')return response({available:true,indexed_images:620,indexed_records:620});
    if(url==='/api/image-search')return response(await search());
    if(url==='/api/catalog')return response({records:rows,settings:{}});
    if(parsed.pathname==='/api/catalog/records')return response({records:rows.filter(row=>params.getAll('id').includes(row.id))});
    if(parsed.pathname==='/api/catalog/page'){
      const options={q:params.get('q'),page:Number(params.get('page')),pageSize:Number(params.get('pageSize')),filters:Object.fromEntries(engine.facetKeys.map(key=>[key,params.getAll(key)]))};
      if(params.has('imageIds'))options.imageIds=params.getAll('imageIds');
      return response({...engine.queryPage(index,options),facets,settings:{},meta:{}});
    }
    throw Error('Unexpected request '+url);
  };
  await evaluateBrowserModule(p.dom,path.join(root,'app.js'),`\nreviewedProductGroups.splice(0,reviewedProductGroups.length,...${JSON.stringify(groups)});window.photoTest={imageSearch,state,recordCache,imageRecordPins};`);
  await until(()=>p.d.querySelector('.card-title'),'staff catalogue');return {...p,calls};
}
async function staffDraft(p,{large=false}={}){
  p.d.querySelector('[data-image-search="open"]').click();await until(()=>p.d.querySelector('#imageSearchStatus').textContent.includes('620'),'search status');
  const input=p.d.querySelector('#imageSearchFile');Object.defineProperty(input,'files',{configurable:true,value:[pictureFile(p.w,'camera.png',large?{width:4032,height:3024,type:''}:{})]});input.dispatchEvent(new p.w.Event('change',{bubbles:true}));
  await until(()=>!p.d.querySelector('#imageSearchSubmit').disabled,'staff camera preparation');
}
test('staff camera workflow caps 620 matches before loading records, pins candidates, preserves ranking and clears active filters explicitly',async()=>{
  const p=await staff();try{
    const input=p.d.querySelector('#query');input.value='does-not-match';p.d.querySelector('#searchForm').dispatchEvent(new p.w.Event('submit',{bubbles:true,cancelable:true}));
    await until(()=>p.d.querySelectorAll('.card').length===0,'keyword empty');
    for(const value of ['PET','玻璃'])p.d.querySelector(`[data-filter="material"][value="${value}"]`).click();
    await until(()=>p.w.photoTest.state.material.length===2,'multiselect');
    await staffDraft(p,{large:true});
    assert.deepEqual([p.d.querySelector('#imageCropCanvas').width,p.d.querySelector('#imageCropCanvas').height],[1280,960]);
    const beforeSearch=p.calls.length;p.d.querySelector('#imageSearchSubmit').click();await until(()=>!p.d.querySelector('#imageSearchModal').open&&p.d.querySelector('[data-image-search="filters-clear"]'),'completed bounded search');
    const fetches=p.calls.slice(beforeSearch).filter(call=>new URL(call.url,'https://catalog.test').pathname==='/api/catalog/records');
    assert.equal(fetches.length,2);assert.deepEqual(fetches.map(call=>new URL(call.url,'https://catalog.test').searchParams.getAll('id').length),[100,20]);
    assert.equal(p.w.photoTest.imageSearch.matches.size,120);assert.equal(p.w.photoTest.imageRecordPins.size,120);
    assert.ok([...p.w.photoTest.imageSearch.matches.keys()].every(id=>p.w.photoTest.recordCache.has(id)));
    assert.equal(p.w.photoTest.state.query,'does-not-match');assert.deepEqual(Array.from(p.w.photoTest.state.material),['PET','玻璃']);
    assert.equal(p.d.querySelectorAll('.card').length,0);assert.match(p.d.querySelector('.image-search-context').textContent,/筛选仍会限制/);
    p.d.querySelector('[data-image-search="filters-clear"]').click();await until(()=>p.d.querySelector('[data-record-id="record-0"]'),'clear filters keeps image matches');
    assert.equal(p.w.photoTest.imageSearch.matches.size,120);assert.deepEqual(Array.from(p.w.photoTest.state.material),[]);
    const pageCalls=p.calls.filter(call=>new URL(call.url,'https://catalog.test').pathname==='/api/catalog/page');
    assert.ok(pageCalls.every(call=>new URL(call.url,'https://catalog.test').searchParams.getAll('imageIds').length<=120));
    assert.equal(p.d.querySelector('.card .record-code').dataset.recordId,'record-0');
    assert.ok(!p.calls.some(call=>call.url==='/api/catalog'));assert.deepEqual(p.errors,[]);
  }finally{p.dom.window.close();}
});
test('empty staff image results never expand to an unrestricted catalogue or CSV download',async()=>{
  const p=await staff({search:()=>({matches:[],indexed_images:620,indexed_records:620})});try{
    await staffDraft(p);const pagesBefore=p.calls.filter(call=>call.url.startsWith('/api/catalog/page')).length;
    p.d.querySelector('#imageSearchSubmit').click();await until(()=>p.w.photoTest.imageSearch.matches?.size===0&&!p.d.querySelector('#imageSearchModal').open,'empty image result');
    assert.equal(p.d.querySelectorAll('.card').length,0);assert.equal(p.calls.filter(call=>call.url.startsWith('/api/catalog/page')).length,pagesBefore);
    p.d.querySelector('[data-action="export"]').click();assert.ok(!p.calls.some(call=>call.url.startsWith('/api/catalog/export')));
    p.d.querySelector('[data-image-search="clear"]').click();await until(()=>p.d.querySelector('.card-title'),'return to catalogue');assert.equal(p.w.photoTest.imageRecordPins.size,0);
    assert.deepEqual(p.errors,[]);
  }finally{p.dom.window.close();}
});
test('reviewed type-family preview images can be matched while arbitrary paths cannot become gallery images',async()=>{
  const preview='media/type-views/bottle-reviewed.jpg',group={id:'type-bottle',recordIds:['record-0','record-1'],name:'精华水瓶系列',primaryImage:{path:preview,role:'product',imageScope:'same_style_variants',displayCrop:{x:0,y:0,width:.5,height:1,sourceWidth:800,sourceHeight:600}},specs:[{label:'30 mL',recordIds:['record-0']},{label:'50 mL',recordIds:['record-1']}]};
  const p=await staff({paged:false,rows:records.slice(0,4),groups:[group],search:()=>({matches:[{record_id:'record-0',image_path:preview},{record_id:'record-2',image_path:'media/arbitrary.jpg'}]})});try{
    await staffDraft(p);p.d.querySelector('#imageSearchSubmit').click();await until(()=>!p.d.querySelector('#imageSearchModal').open,'type-family image match');
    assert.equal(p.w.photoTest.imageSearch.matches.size,1);assert.equal(p.d.querySelector('.photo img').getAttribute('src'),'/media/type-views/bottle-reviewed.jpg?thumb=1');
    assert.ok(p.d.querySelector('.photo .image-viewport'));assert.deepEqual(p.errors,[]);
  }finally{p.dom.window.close();}
});
test('cancelled staff inference cannot overwrite later catalogue results',async()=>{
  let resolve;const p=await staff({search:()=>new Promise(r=>resolve=r)});try{
    await staffDraft(p);p.d.querySelector('#imageSearchSubmit').click();await until(()=>resolve,'inference started');
    p.d.querySelector('[data-image-search="close"]').click();resolve({matches:[{record_id:'record-10',image_path:'media/p10.jpg'}]});
    await new Promise(r=>setTimeout(r,30));assert.equal(p.w.photoTest.imageSearch.matches,null);assert.equal(p.d.querySelector('.card .record-code').dataset.recordId,'record-0');assert.equal(p.w.photoTest.imageRecordPins.size,0);
    assert.deepEqual(p.errors,[]);
  }finally{p.dom.window.close();}
});
const publicItem=(i,material='PET')=>({id:'opaque-'+i,productCode:'YZ-BC-'+String(i+1).padStart(6,'0'),category:'瓶类',bottleType:'圆瓶',capacity:'100 mL',capacityMl:100,materials:[material],uses:['精华液'],referenceUses:[],sections:['face'],specifications:[],images:[{url:'/client-media/item'+i+'.jpg'}],supplier:'DO_NOT_SHOW',price:'DO_NOT_SHOW'});
async function customer({decodeDelay=0,search=()=>({items:[publicItem(88,'玻璃')]})}={}){
  const p=browser('client.html',{decodeDelay}),calls=[];
  p.w.fetch=async(url,options={})=>{calls.push({url,options});if(url==='/api/session')return response({role:'client',csrf:'customer-csrf'});if(url==='/api/client/image-search')return response(await search());if(url.startsWith('/api/client/catalog?'))return response({items:[publicItem(0)],facets:{materials:['PET','玻璃'],capacities:['100 mL'],categories:['瓶类'],uses:['精华液']},page:1,pages:1,total:1});throw Error('Unexpected request '+url);};
  await evaluateBrowserModule(p.dom,path.join(root,'client.js'));await until(()=>p.d.querySelector('.gallery-card'),'customer catalogue');return {...p,calls};
}
test('customer camera preview rotates/crops before upload, uses only client endpoint and lets the user clear filters without losing image results',async()=>{
  const p=await customer();try{
    p.d.querySelector('[data-filter="material"][value="PET"]').click();await until(()=>p.d.querySelector('[data-clear-filter="material"]'),'selected material');
    p.d.querySelector('#imageSearchOpen').click();const input=p.d.querySelector('#imageSearchFile');Object.defineProperty(input,'files',{value:[pictureFile(p.w,'camera',{width:4032,height:3024,type:''})]});input.dispatchEvent(new p.w.Event('change',{bubbles:true}));
    await until(()=>!p.d.querySelector('#imageSearchSubmit').disabled,'customer prepared');
    p.d.querySelector('#clientImageRotate').click();assert.deepEqual([p.d.querySelector('#clientImageCropCanvas').width,p.d.querySelector('#clientImageCropCanvas').height],[960,1280]);
    p.d.querySelector('#clientImageCropCentre').click();p.d.querySelector('#imageSearchSubmit').click();await until(()=>!p.d.querySelector('#imageSearchDialog').open&&p.d.querySelector('#collectionLabel').textContent==='图片相似结果','customer search');
    assert.deepEqual(p.operations.filter(op=>op.type==='encode').map(op=>[op.width,op.height]),[[576,1024]]);
    const call=p.calls.find(call=>call.url==='/api/client/image-search');assert.equal(call.options.headers['X-CSRF-Token'],'customer-csrf');assert.deepEqual(Object.keys(JSON.parse(call.options.body)),['image']);assert.match(JSON.parse(call.options.body).image,/^data:image\/jpeg;base64,/);
    assert.equal(p.d.querySelectorAll('.gallery-card').length,0);assert.equal(p.d.querySelector('#imageFilterNotice').hidden,false);
    p.d.querySelector('#clearImageFilters').click();assert.equal(p.d.querySelectorAll('.gallery-card').length,1);assert.match(p.d.querySelector('#gallery').textContent,/YZ-BC-000089/);
    assert.equal(p.d.querySelector('#collectionLabel').textContent,'图片相似结果');assert.doesNotMatch(p.d.body.textContent,/DO_NOT_SHOW/);
    p.d.querySelector('[data-language-switch]').click();assert.match(p.d.querySelector('#clientImageRotate').textContent,/Rotate/);assert.deepEqual(p.errors,[]);
    assert.ok(p.calls.every(call=>call.url==='/api/session'||call.url==='/api/client/image-search'||call.url.startsWith('/api/client/catalog?')));
  }finally{p.dom.window.close();}
});
test('closing customer dialog cancels a pending photo decode before upload and ignores a completed cancelled search',async()=>{
  const p=await customer({decodeDelay:40});try{
    p.d.querySelector('#imageSearchOpen').click();const input=p.d.querySelector('#imageSearchFile');Object.defineProperty(input,'files',{value:[pictureFile(p.w)]});input.dispatchEvent(new p.w.Event('change',{bubbles:true}));p.d.querySelector('#imageSearchClose').click();
    await new Promise(r=>setTimeout(r,70));assert.ok(!p.calls.some(call=>call.url==='/api/client/image-search'));assert.equal(p.d.querySelector('#clientImageCropArea').hidden,true);assert.deepEqual(p.errors,[]);
  }finally{p.dom.window.close();}
  let resolve;const q=await customer({search:()=>new Promise(r=>resolve=r)});try{
    q.d.querySelector('#imageSearchOpen').click();Object.defineProperty(q.d.querySelector('#imageSearchFile'),'files',{value:[pictureFile(q.w)]});q.d.querySelector('#imageSearchForm').dispatchEvent(new q.w.Event('submit',{bubbles:true,cancelable:true}));await until(()=>resolve,'pending client inference');q.d.querySelector('#imageSearchClose').click();resolve({items:[publicItem(99)]});await new Promise(r=>setTimeout(r,30));
    assert.match(q.d.querySelector('#gallery').textContent,/YZ-BC-000001/);assert.doesNotMatch(q.d.querySelector('#gallery').textContent,/YZ-BC-000100/);assert.deepEqual(q.errors,[]);
  }finally{q.dom.window.close();}
});
