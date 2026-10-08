const assert=require('node:assert/strict');
const fs=require('node:fs');const path=require('node:path');
const {JSDOM}=require('jsdom');const {evaluateBrowserModule}=require('./module-loader.cjs');
const root=path.resolve(__dirname,'../../server-reference/public');
const fixture=Array.from({length:65},(_,i)=>({id:'paged-'+i,productCode:'YZ-BC-'+String(i+1).padStart(6,'0'),kind:'package',version:1,name:'精华玻璃瓶'+i,capacityMl:30,materials:[i%2?'玻璃':'PET'],uses:['精华液'],bodyAreas:['face'],quoteRaw:'quote-'+i,images:[{path:'media/test-'+i+'.jpg',role:'product',imageScope:'single_product'}]}));
const family={id:'paged-family',name:'精华系列',recordIds:['paged-0','paged-1'],specs:[{label:'30 mL',recordIds:['paged-0']},{label:'50 mL',recordIds:['paged-1']}]};fixture[1].capacityMl=50;
const delay=ms=>new Promise(r=>setTimeout(r,ms));
async function until(f,label){for(let i=0;i<800;i++){if(f())return;await delay(5);}throw Error(label);}
(async()=>{
 const dom=new JSDOM(fs.readFileSync(path.join(root,'index.html'),'utf8'),{url:'https://catalog.test/',runScripts:'outside-only',pretendToBeVisual:true});
 const w=dom.window,d=w.document;w.matchMedia=()=>({matches:false,addEventListener(){}});w.scrollTo=()=>{};w.HTMLElement.prototype.scrollIntoView=()=>{};
 w.HTMLDialogElement.prototype.showModal=function(){this.open=true};w.HTMLDialogElement.prototype.close=function(){this.open=false};
 const module=await evaluateBrowserModule(dom,path.join(root,'catalog-query.js'));const engine=module.namespace;
 const index=engine.prepareRecords({records:fixture},[family]),facets=engine.catalogFacets(index.records);let favorites=[];const calls=[];
 const meta={recordCount:fixture.length},settings={catalogTitle:'包材选型库',showBusinessDemo:false};let held=null;
 w.fetch=async(url,options={})=>{
  calls.push(String(url));const parsed=new URL(url,'https://catalog.test'),p=parsed.searchParams;
  const response=x=>new Response(JSON.stringify(x),{headers:{'Content-Type':'application/json'}});
  if(url==='/api/session')return response({username:'employee',role:'employee',csrf:'test',catalogPaging:true});
  if(url==='/api/preferences'){if(options.method==='POST')favorites=JSON.parse(options.body).favorites;return response({favorites});}
  if(url==='/api/image-search/status')return response({available:false});
  if(parsed.pathname==='/api/catalog/page'){
   const q={q:p.get('q'),page:+p.get('page'),pageSize:+p.get('pageSize'),filters:Object.fromEntries(engine.facetKeys.map(k=>[k,p.getAll(k)])),favorites:p.get('favorites')==='1',favoriteIds:favorites};
   const result={...engine.queryPage(index,q),facets,meta,settings};
   if(p.get('q')==='held'){await new Promise(r=>held=r);}return response(result);
  }
  if(parsed.pathname==='/api/catalog/records')return response({records:fixture.filter(r=>p.getAll('id').includes(r.id)),meta,settings});
  throw Error('Unexpected request '+url);
 };
 await evaluateBrowserModule(dom,path.join(root,'app.js'),`\nreviewedProductGroups.splice(0,reviewedProductGroups.length,${JSON.stringify(family)});window.pagingTest={state,render,loadRemotePage,recordCache,remoteParams};`);
 await until(()=>d.querySelectorAll('.card').length===20,'page1');
 assert(!calls.includes('/api/catalog'),'Startup never downloads the full catalogue');
 assert.equal(d.querySelector('.photo img').getAttribute('src'),'/media/test-0.jpg?thumb=1');
 d.querySelector('.card [data-select]').click();
 d.querySelector('[data-page-control="next"]').click();await until(()=>d.querySelector('[data-record-id="paged-21"]'),'page2');
 d.querySelector('.card [data-select]').click();d.querySelector('[data-action="compare"]').click();
 assert(d.querySelector('#modal').textContent.includes('quote-0'));assert(d.querySelector('#modal').textContent.includes('quote-21'));d.querySelector('#modal').close();
 const query=d.querySelector('#query');query.value='YZ-BC-000002';d.querySelector('#searchForm').dispatchEvent(new w.Event('submit',{bubbles:true,cancelable:true}));
 await until(()=>d.querySelectorAll('.card').length===1&&d.querySelector('[data-record-id="paged-1"]'),'exact-code');
 d.querySelector('[data-detail="paged-1"]').click();assert(d.querySelector('#modal').textContent.includes('quote-1'));assert(d.querySelector('#modal [data-detail="paged-0"]'));
 assert.equal(d.querySelector('#detailPhoto img').getAttribute('src'),'/media/test-1.jpg');d.querySelector('#modal [data-detail="paged-0"]').click();assert(d.querySelector('#modal').textContent.includes('quote-0'));d.querySelector('#modal').close();
 w.pagingTest.state.query='50毫升';w.pagingTest.render();await until(()=>d.querySelector('#query').value==='50毫升'&&d.querySelector('[data-record-id="paged-1"]'),'size alias');
 w.pagingTest.state.query='';w.pagingTest.state.material=['PET'];w.pagingTest.render();await until(()=>d.querySelectorAll('.card .quote-preview').length===20&&d.querySelector('[data-record-id="paged-2"]'),'material-page');
 w.pagingTest.state.query='held';w.pagingTest.render();await until(()=>held,'held request');w.pagingTest.state.query='YZ-BC-000040';w.pagingTest.state.material=[];w.pagingTest.render();await until(()=>d.querySelector('[data-record-id="paged-39"]'),'new request');held();await delay(30);
 assert(d.querySelector('[data-record-id="paged-39"]'),'Older response cannot replace newer search');
 const favorite=d.querySelector('.favorite');favorite.click();await until(()=>favorites.length===1,'save favorite');d.querySelector('[data-view="favorites"]').click();await until(()=>d.querySelector('h1').textContent==='我的收藏','favorites');
 d.querySelector('.favorite').click();await until(()=>d.querySelectorAll('.card').length===0,'remove favorite');
 assert(w.pagingTest.recordCache.size<=300);dom.window.close();console.log('Paged catalogue: startup, pagination, groups, cross-page comparison, multilingual size, latest-response wins and favorites passed.');
})().catch(e=>{console.error(e);process.exitCode=1;});
