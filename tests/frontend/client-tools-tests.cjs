const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const {JSDOM,VirtualConsole} = require('jsdom');
const {evaluateBrowserModule} = require('./module-loader.cjs');
const root = path.resolve(__dirname,'../../server-reference/public');
const checks = [];
const facets = {categories:['瓶类','软管'],sections:['face','body-head'],materials:['PET','玻璃'],capacities:['100 mL','200 mL'],bottleTypes:['圆瓶','喷雾瓶'],uses:['精华液','洗手液']};
const fixture = number => ({id:`opaque${number}`,productCode:`YZ-BC-${String(number).padStart(6,'0')}`,capacity:'100 mL',category:'瓶类',bottleType:'圆瓶',materials:['PET'],uses:['精华液'],sections:['face'],specifications:[{label:'口径',value:'24 mm'},{label:'供应商',value:'DO_NOT_SHOW_SUPPLIER'}],supplier:'DO_NOT_SHOW_SUPPLIER',price:'DO_NOT_SHOW_PRICE',name:'DO_NOT_SHOW_NAME',source:'DO_NOT_SHOW_SOURCE',images:[{url:`/client-media/item${number}.jpg`,original:'DO_NOT_SHOW_ORIGINAL'}]});
const response = (value,status=200) => new Response(JSON.stringify(value),{status,headers:{'Content-Type':'application/json'}});
async function until(fn,label) {for(let n=0;n<600;n++){if(fn())return;await new Promise(resolve=>setTimeout(resolve,5));}throw Error('Timeout: '+label);}
function create({embedded=false,mobile=false}={}) {
  const errors=[],calls=[],messages=[],downloads=[];
  const console=new VirtualConsole();console.on('jsdomError',error=>{if(!error.message.includes('Not implemented: navigation'))errors.push(error.message);});
  const dom=new JSDOM(fs.readFileSync(path.join(root,'client.html'),'utf8'),{url:`https://catalog.test/client${embedded?'?showroom=1':''}`,runScripts:'outside-only',pretendToBeVisual:true,virtualConsole:console});
  const w=dom.window,d=w.document;
  w.AbortController=AbortController;w.DOMException=DOMException;w.TypeError=TypeError;w.Blob=Blob;
  w.matchMedia=query=>({matches:query.includes('reduced-motion') || mobile && query === '(max-width: 760px)',addEventListener(){}});
  w.HTMLElement.prototype.scrollIntoView=function(){};
  w.HTMLDialogElement.prototype.showModal=function(){this.open=true;};
  w.HTMLDialogElement.prototype.close=function(){this.open=false;this.dispatchEvent(new w.Event('close'));};
  w.URL.createObjectURL=blob=>{downloads.push(blob);return 'blob:fixture';};w.URL.revokeObjectURL=()=>{};
  w.HTMLAnchorElement.prototype.click=function(){};
  const parent={postMessage:(message,origin)=>messages.push({message,origin})};
  if(embedded)Object.defineProperty(w,'parent',{value:parent});
  let imageResponse = async()=>response({items:[fixture(88)],facets});
  w.fetch=async(url,options)=>{
    calls.push({url,options});
    if(url==='/api/session')return response({role:'client',csrf:'fixture-csrf'});
    if(url==='/api/client/image-search')return imageResponse(url,options);
    if(url.startsWith('/api/client/catalog?')){const page=Number(new URL(url,'https://catalog.test').searchParams.get('page'));return response({items:Array.from({length:5},(_,i)=>fixture((page-1)*5+i+1)),page,pages:2,total:10,facets});}
    throw Error('Unexpected API '+url);
  };
  const start=async()=>{await evaluateBrowserModule(dom,path.join(root,'client.js'));await until(()=>d.querySelectorAll('.gallery-card').length===5&&d.querySelector('#gallery').getAttribute('aria-busy')==='false','initial catalogue');};
  const clickAction=(action,index)=>d.querySelector(`[data-item-action="${action}"][data-item-index="${index}"]`).click();
  const submit=id=>d.querySelector('#'+id).dispatchEvent(new w.Event('submit',{bubbles:true,cancelable:true}));
  return{dom,w,d,calls,messages,parent,downloads,errors,start,clickAction,submit,setImageResponse:fn=>{imageResponse=fn;}};
}
async function main(){
  let p=create();await p.start();
  assert.deepEqual([...p.d.querySelectorAll('.multi-filter')].map(el=>el.dataset.facet),['category','section','material','capacity','bottle','use']);
  assert.equal(p.d.querySelector('#filterToggle').hidden,true);assert.equal(p.d.querySelector('#filterGrid').hidden,false);
  p.d.querySelector('#pageSize').value='48';p.d.querySelector('#pageSize').dispatchEvent(new p.w.Event('change',{bubbles:true}));
  await until(()=>new URL(p.calls.at(-1).url,'https://catalog.test').searchParams.get('pageSize')==='48','page size');
  p.d.querySelector('#listView').click();assert.ok(p.d.querySelector('#gallery').classList.contains('list-mode'));assert.equal(p.d.querySelector('#listView').getAttribute('aria-pressed'),'true');
  p.d.querySelector('#gridView').click();assert.ok(!p.d.querySelector('#gallery').classList.contains('list-mode'));
  checks.push('All public taxonomy facets are multiselect; grid/list and page-size controls operate on the customer catalogue');

  await until(()=>p.d.querySelector('#gallery').getAttribute('aria-busy')==='false','page-size fetch');
  p.clickAction('favourite',0);p.clickAction('shortlist',0);
  p.d.querySelector('#next').click();await until(()=>p.d.querySelector('#pageStatus').textContent==='2 / 2'&&!p.d.querySelector('#previous').disabled,'page two');
  p.clickAction('favourite',0);p.clickAction('shortlist',0);
  const before=p.calls.length;p.d.querySelector('#favoritesView').click();
  assert.equal(p.calls.length,before);assert.equal(p.d.querySelectorAll('.gallery-card').length,2);assert.equal(p.d.querySelector('#favoriteCount').textContent,'2');
  assert.match(p.d.querySelector('#gallery').textContent,/YZ-BC-000001/);assert.match(p.d.querySelector('#gallery').textContent,/YZ-BC-000006/);
  p.clickAction('favourite',0);assert.equal(p.d.querySelectorAll('.gallery-card').length,1);assert.equal(p.d.querySelector('#favoriteCount').textContent,'1');
  p.d.querySelector('#shortlistView').click();assert.equal(p.d.querySelectorAll('.gallery-card').length,2);
  assert.equal(p.w.localStorage.length,0);assert.equal(p.w.sessionStorage.length,0);
  checks.push('Favourites and shortlist retain safe items across catalogue pages, removal updates views, and selections never enter shared storage');

  for(const [view,count] of [['favoritesView',1],['shortlistView',2]]){
    p.d.querySelector('#'+view).click();
    for(const [query,expected] of [['100ml PET',count],['１００ 毫升，ＰＥＴ',count],['round bottle serum 100 mL',count],['face Neck diameter 24 mm',count],['100ml Glass',0],['200ml PET',0],['100ml PETG',0]]){
      p.d.querySelector('#query').value=query;p.submit('searchForm');assert.equal(p.d.querySelectorAll('.gallery-card').length,expected,`${view}: ${query}`);
    }
    p.d.querySelector('#reset').click();
  }
  p.d.querySelector('[data-language-switch]').click();p.d.querySelector('#query').value='100ml 精华液 PET';p.submit('searchForm');assert.equal(p.d.querySelectorAll('.gallery-card').length,2);p.d.querySelector('#reset').click();p.d.querySelector('[data-language-switch]').click();
  checks.push('Local favourites and shortlist match separated capacity/material terms, bilingual aliases and dimensions in either UI language, without partial material matches');

  p.d.querySelector('#exportShortlist').click();const csv=await p.downloads.at(-1).text();
  assert.match(csv,/YZ-BC-000001/);assert.match(csv,/YZ-BC-000006/);assert.match(csv,/24 mm/);
  assert.doesNotMatch(csv,/DO_NOT_SHOW|供应商|价格|报价|opaque|client-media/);
  p.d.querySelector('#consultShortlist').click();assert.equal(p.d.querySelector('#consultDialog').open,true);assert.match(p.d.querySelector('#consultText').value,/YZ-BC-000006/);assert.doesNotMatch(p.d.querySelector('#consultText').value,/DO_NOT_SHOW/);p.d.querySelector('#consultClose').click();
  checks.push('Shortlist CSV and enquiry contain only public product codes, taxonomy and specifications');

  p.d.querySelector('#allCatalog').click();await until(()=>p.d.querySelectorAll('.gallery-card').length===5&&p.d.querySelector('#gallery').getAttribute('aria-busy')==='false','all catalogue');
  for(let index=0;index<5;index++)p.clickAction('compare',index);
  assert.equal(p.d.querySelector('#compareCount').textContent,'4 / 4');assert.match(p.d.querySelector('#notice').textContent,/最多可同时对比四款/);
  p.d.querySelector('#compareOpen').click();assert.equal(p.d.querySelector('#compareDialog').open,true);assert.equal(p.d.querySelectorAll('#compareTable thead th').length,5);
  assert.match(p.d.querySelector('#compareTable').textContent,/YZ-BC-000004/);assert.doesNotMatch(p.d.querySelector('#compareTable').textContent,/YZ-BC-000005|DO_NOT_SHOW|供应商|价格|报价/);
  p.d.querySelector('[data-language-switch]').click();assert.match(p.d.querySelector('#compareTable').textContent,/Neck diameter/);assert.doesNotMatch(p.d.body.textContent.replace(p.d.querySelector('[data-language-switch]').textContent,''),/[\u3400-\u9fff]/);
  assert.doesNotMatch(p.d.documentElement.outerHTML,/DO_NOT_SHOW/);assert.deepEqual(p.errors,[]);p.dom.window.close();
  checks.push('Comparison enforces a four-item limit and all added controls/details translate without disclosing raw supplier or price fields');

  p=create({embedded:true});await p.start();assert.ok(p.d.documentElement.classList.contains('embedded-showroom'));assert.equal(p.d.querySelector('#showroomHero').hidden,true);
  p.w.dispatchEvent(new p.w.MessageEvent('message',{origin:'https://evil.test',source:p.parent,data:{type:'yuanze-language',language:'en'}}));assert.equal(p.d.documentElement.lang,'zh-CN');
  p.w.dispatchEvent(new p.w.MessageEvent('message',{origin:'https://catalog.test',source:{},data:{type:'yuanze-language',language:'en'}}));assert.equal(p.d.documentElement.lang,'zh-CN');
  p.w.dispatchEvent(new p.w.MessageEvent('message',{origin:'https://catalog.test',source:p.parent,data:{type:'yuanze-language',language:'en'}}));assert.equal(p.d.documentElement.lang,'en');
  p.clickAction('shortlist',0);const last=p.messages.at(-1);assert.equal(last.origin,'https://catalog.test');assert.deepEqual(JSON.parse(JSON.stringify(last.message)),{type:'yuanze-shortlist',items:[{productCode:'YZ-BC-000001',capacity:'100 mL'}]});
  p.d.querySelector('#shortlistView').click();p.d.querySelector('#consultShortlist').click();assert.equal(p.messages.at(-1).message.type,'yuanze-contact');
  assert.ok(p.messages.every(message=>message.origin==='https://catalog.test'));assert.doesNotMatch(JSON.stringify(p.messages),/DO_NOT_SHOW|opaque|client-media/);
  p.dom.window.close();checks.push('Embedded catalogue validates parent origin and source for language sync and emits only safe shortlist fields and contact navigation');

  p=create({embedded:true,mobile:true});await p.start();
  assert.equal(p.d.querySelector('#filterToggle').hidden,false);assert.equal(p.d.querySelector('#filterToggle').getAttribute('aria-expanded'),'false');assert.equal(p.d.querySelector('#filterGrid').hidden,true);assert.equal(p.d.querySelector('#filterHelp').hidden,true);
  assert.equal(p.d.querySelector('#searchForm').hidden,false);assert.equal(p.d.querySelector('#imageSearchOpen').hidden,false);
  p.d.querySelector('#filterToggle').click();assert.equal(p.d.querySelector('#filterGrid').hidden,false);
  for(const value of ['PET','玻璃']){const input=[...p.d.querySelectorAll('[data-filter="material"]')].find(input=>input.value===value);input.checked=true;input.dispatchEvent(new p.w.Event('change',{bubbles:true}));await until(()=>p.d.querySelector('#gallery').getAttribute('aria-busy')==='false','compact multiselect');}
  assert.equal(p.d.querySelector('#filterToggleCount').textContent,'2');p.d.querySelector('#filterToggle').click();assert.equal(p.d.querySelector('#filterGrid').hidden,true);assert.equal(p.d.querySelector('#activeFilters').hidden,false);assert.equal(p.d.querySelectorAll('[data-filter="material"]:checked').length,2);
  p.w.dispatchEvent(new p.w.MessageEvent('message',{origin:'https://catalog.test',source:p.parent,data:{type:'yuanze-language',language:'en'}}));assert.match(p.d.querySelector('#filterToggle').textContent,/Filters/);assert.equal(p.d.querySelector('#filterGrid').hidden,true);
  p.d.querySelector('#filterToggle').click();assert.equal(p.d.querySelectorAll('[data-filter="material"]:checked').length,2);assert.equal(p.d.querySelector('#filterToggle').getAttribute('aria-expanded'),'true');
  const brandClick=new p.w.MouseEvent('click',{bubbles:true,cancelable:true});p.d.querySelector('.brand').dispatchEvent(brandClick);assert.equal(brandClick.defaultPrevented,true);await until(()=>p.d.querySelector('#gallery').getAttribute('aria-busy')==='false','brand reset');assert.equal(p.d.querySelectorAll('[data-filter]:checked').length,0);assert.equal(p.w.location.search,'?showroom=1');assert.equal(p.d.querySelector('#filterToggleCount').hidden,true);
  p.dom.window.close();checks.push('Embedded mobile filters collapse initially, preserve multiselections and visible chips across toggle/language changes, and sidebar brand remains inside showroom');

  p=create();await p.start();p.d.querySelector('#imageSearchOpen').click();
  Object.defineProperty(p.d.querySelector('#imageSearchFile'),'files',{configurable:true,value:[new p.w.File(['svg'],'bottle.svg',{type:'image/svg+xml'})]});p.submit('imageSearchForm');assert.equal(p.d.querySelector('#imageSearchError').hidden,false);assert.equal(p.calls.filter(call=>call.url==='/api/client/image-search').length,0);
  const oversized=new p.w.File(['oversized'],'large.png',{type:'image/png'});Object.defineProperty(oversized,'size',{value:6*1024*1024+1});Object.defineProperty(p.d.querySelector('#imageSearchFile'),'files',{configurable:true,value:[oversized]});p.submit('imageSearchForm');assert.match(p.d.querySelector('#imageSearchError').textContent,/6 MB/);assert.equal(p.calls.filter(call=>call.url==='/api/client/image-search').length,0);
  Object.defineProperty(p.d.querySelector('#imageSearchFile'),'files',{configurable:true,value:[new p.w.File(['image-fixture'],'bottle.png',{type:'image/png'})]});p.submit('imageSearchForm');await until(()=>p.d.querySelector('#collectionLabel').textContent==='图片相似结果','image search');
  const call=p.calls.find(call=>call.url==='/api/client/image-search');assert.equal(call.options.method,'POST');assert.equal(call.options.headers['X-CSRF-Token'],'fixture-csrf');assert.match(JSON.parse(call.options.body).image,/^data:image\/png;base64,/);
  assert.equal(p.d.querySelectorAll('.gallery-card').length,1);assert.match(p.d.querySelector('#gallery').textContent,/YZ-BC-000088/);assert.equal(p.d.querySelector('#imageSearchDialog').open,false);assert.doesNotMatch(p.d.documentElement.outerHTML,/DO_NOT_SHOW/);
  p.d.querySelector('#query').value='100ml PET Serum';p.submit('searchForm');assert.equal(p.d.querySelectorAll('.gallery-card').length,1);p.d.querySelector('#query').value='100ml Glass';p.submit('searchForm');assert.equal(p.d.querySelectorAll('.gallery-card').length,0);p.d.querySelector('#reset').click();
  assert.ok(p.calls.every(call=>call.url==='/api/session'||call.url==='/api/client/image-search'||call.url.startsWith('/api/client/catalog?')));
  checks.push('Image upload validates type, sends CSRF to the customer-only endpoint, and renders only allowlisted image-search results');

  let resolveSearch;p.setImageResponse(()=>new Promise(resolve=>{resolveSearch=resolve;}));p.d.querySelector('#imageSearchOpen').click();p.submit('imageSearchForm');await until(()=>resolveSearch,'pending image search');p.d.querySelector('#imageSearchClose').click();resolveSearch(response({items:[fixture(99)]}));await new Promise(resolve=>setTimeout(resolve,30));assert.doesNotMatch(p.d.querySelector('#gallery').textContent,/YZ-BC-000099/);assert.equal(p.d.querySelector('#imageSearchSubmit').disabled,false);
  p.setImageResponse(async()=>response({error:'DO_NOT_SHOW_SERVER_ERROR'},400));p.d.querySelector('#imageSearchOpen').click();p.submit('imageSearchForm');await until(()=>!p.d.querySelector('#imageSearchError').hidden,'image failure');assert.doesNotMatch(p.d.body.textContent,/DO_NOT_SHOW_SERVER_ERROR/);
  assert.deepEqual(p.errors,[]);p.dom.window.close();checks.push('Cancelled image searches cannot replace current results, and server error details remain private');

  p=create();await p.start();p.clickAction('favourite',0);p.clickAction('shortlist',0);
  p.setImageResponse(async()=>response({items:[{...fixture(88),materials:['玻璃']}],facets:{...facets,materials:['玻璃']}}));
  Object.defineProperty(p.d.querySelector('#imageSearchFile'),'files',{value:[new p.w.File(['fixture'],'glass.png',{type:'image/png'})]});
  p.d.querySelector('#imageSearchOpen').click();p.submit('imageSearchForm');await until(()=>p.d.querySelector('#collectionLabel').textContent==='图片相似结果','glass-only search');
  assert.deepEqual([...p.d.querySelectorAll('[data-filter="material"]')].map(input=>input.value),['玻璃']);
  for(const view of ['favoritesView','shortlistView']){
    p.d.querySelector('#'+view).click();assert.deepEqual([...p.d.querySelectorAll('[data-filter="material"]')].map(input=>input.value),['PET']);
    const input=p.d.querySelector('[data-filter="material"][value="PET"]');if(!input.checked){input.checked=true;input.dispatchEvent(new p.w.Event('change',{bubbles:true}));}
    assert.equal(p.d.querySelectorAll('.gallery-card').length,1);assert.match(p.d.querySelector('#gallery').textContent,/YZ-BC-000001/);assert.equal(p.d.querySelector('[data-filter="material"][value="PET"]').checked,true);
  }
  assert.deepEqual(p.errors,[]);p.dom.window.close();checks.push('Each local collection rebuilds facets from its safe items, so glass-only image results cannot remove saved PET filters');
  console.log(JSON.stringify({passed:true,checks,liveWebsiteRequests:0},null,2));
}
main().catch(error=>{console.error(error);process.exitCode=1;});
