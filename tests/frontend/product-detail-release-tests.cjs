const {test}=require('node:test');
const assert=require('node:assert/strict');
const path=require('node:path');
const {JSDOM}=require('jsdom');
const {evaluateBrowserModule}=require('./module-loader.cjs');
const root=path.resolve(__dirname,'../../server-reference/public');
async function setup(){const dom=new JSDOM('<body><main id="detail"></main></body>',{url:'https://synthetic.test/',runScripts:'outside-only'});const view=(await evaluateBrowserModule(dom,path.join(root,'product-detail-view.js'))).namespace;return {dom,doc:dom.window.document,view,close:()=>dom.window.close()};}
const record={id:'synthetic',productCode:'YZ-BC-990001',kind:'package',quoteRaw:'裸瓶价格1.8元',specificationRaw:'50g',moqRaw:'5000',leadTimeRaw:'20天',uses:['面霜'],supplierRaw:'PRIVATE SUPPLIER',contactRaw:'PRIVATE CONTACT',productDetails:[{label:'裸瓶报价',value:'1.8元'}]};
test('production detail matches compact prototype and keeps source-private data outside main fields',async()=>{const e=await setup();try{e.doc.querySelector('main').innerHTML=e.view.compactDetail(record);const d=e.doc;assert.match(d.querySelector('.pd-price-value').textContent,/1\.80/);assert.deepEqual([...d.querySelectorAll('.pd-facts dt')].map(n=>n.textContent),['材质','规格','MOQ · 起订量','货期','通常用于']);assert.equal(d.querySelector('.pd-facts dd').textContent,'');assert.equal(d.querySelectorAll('tbody tr').length,9);assert.doesNotMatch(d.querySelector('main').textContent,/PRIVATE|0\.10|0\.20|0\.50/);assert.equal(d.querySelector('.pd-facts').textContent.match(/5000/g).length,1);}finally{e.close();}});
test('explicit cleared bare price suppresses historical fallbacks',async()=>{const e=await setup();try{assert.equal(e.view.coreFacts({...record,bareBottlePrice:''}).bare,'');assert.equal(e.view.coreFacts({...record,bareBottlePrice:'2.5元'}).bare,'2.5元');}finally{e.close();}});
test('all source quotations remain available in the price section without treating an ordinary quote as bare',async()=>{
 const e=await setup();try{
  const input={...record,quoteRaw:'1.35',bareBottlePrice:'',customQuoteRaw:'定制盖含泵头2.30元/套'};
  e.doc.querySelector('main').innerHTML=e.view.compactDetail(input);
  assert.equal(e.doc.querySelector('.pd-price-value').textContent,'—');
  assert.doesNotMatch(e.doc.querySelector('.pd-reference-quotes').textContent,/普通参考报价/);
  assert.match(e.doc.querySelector('.pd-source-quote').textContent,/1.35/);
  assert.match(e.doc.querySelector('.pd-source-quote').textContent,/2.30元\/套/);
  assert.equal(e.doc.querySelector('.pd-estimate-value'),null);
  assert.ok(e.doc.querySelector('.pd-reference-quotes').compareDocumentPosition(e.doc.querySelector('.pd-facts'))&4);
  assert.doesNotMatch(e.doc.querySelector('.pd-reference-quotes').textContent,/PRIVATE/);
  const normalized={...input,bareBottlePrice:'1.35元',customQuoteRaw:''};
  e.doc.querySelector('main').innerHTML=e.view.compactDetail(normalized);
  assert.equal(e.doc.querySelector('.pd-reference-price'),null,'Do not repeat the identical already-confirmed bare amount as ordinary');
  assert.match(e.doc.querySelector('.pd-source-quote').textContent,/1.35/,'Original evidence remains available');
 }finally{e.close();}
});
test('material facts use explicit materials and do not mistake a mixed source printing fee for material',async()=>{
 const e=await setup();try{
  for(const [materialRaw,expected] of [['丝印单色单面0.1',''],['PET','PET'],['PET瓶，丝印单色单面0.1','PET'],['丝印0.1；PET + PP','PET / PP'],['PETG+烫金0.2','PETG'],['贴纸0.1，电镀铝色0.2',''],['待确认',''],['/','']]){
   const input={...record,name:'PET洗手液瓶',materials:[],materialRaw},before=JSON.stringify(input);
   assert.equal(e.view.coreFacts(input).material,expected,materialRaw);
   e.doc.querySelector('main').innerHTML=e.view.compactDetail(input);
   assert.equal(e.doc.querySelector('.pd-facts dd').textContent,expected,materialRaw+' actual rendered fact');
   assert.equal(JSON.stringify(input),before,'Raw source must remain available unchanged');
  }
  assert.equal(e.view.coreFacts({...record,materials:['玻璃','PP'],materialRaw:'PET+丝印0.1'}).material,'玻璃 / PP','Standard material values take precedence');
  assert.equal(e.view.coreFacts({...record,materials:['铝塑复合'],materialRaw:'丝印单色单面0.1'}).material,'铝塑复合');
  assert.equal(e.view.coreFacts({...record,name:'PET瓶',materialRaw:''}).material,'','The product name is not a material source');
  assert.equal(e.view.coreFacts({...record,materialRaw:'丝印单色单面0.1',productDetails:[{label:'材质',value:'玻璃'}]}).material,'玻璃','An explicitly labelled material detail remains a valid source');
  assert.equal(e.view.coreFacts({...record,productDetails:[{label:'材料',value:'丝印单色单面0.1'}]}).material,'','Material detail labels cannot bypass validation');
  assert.equal(e.view.coreFacts({...record,materialRaw:'PET+丝印0.1',productDetails:[{label:'材质',value:'玻璃'}]}).material,'PET','Explicit raw material precedes material details');
  assert.equal(e.view.coreFacts({...record,productDetails:[{label:'备注',value:'PET'}]}).material,'','Unrelated detail text is not a material source');
 }finally{e.close();}
});
test('conditional/component/tiered/foreign quotes cannot produce a misleading estimate',async()=>{const e=await setup();try{for(const [v,c] of [['裸瓶0.82，内塞0.06，旋盖0.48',null],['5000个1.8元，10000个1.6元',null],['1.8 USD','USD'],['1.8',null],['裸瓶价格1.8元含运不含税',null]])assert.equal(e.view.bareAmount(v,c),null,v);assert.equal(e.view.bareAmount('裸瓶价格1.8元',null),1.8);assert.equal(e.view.bareAmount('2.00','CNY'),2);}finally{e.close();}});
test('missing rates and invalid quantities block complete totals; zero is a deliberate rate',async()=>{const e=await setup();try{const processes=[{id:'silk',price:.1,unit:'colour'},{id:'foil',price:.2,unit:'colour'},{id:'unknown',price:null,unit:'unit'},{id:'free',price:0,unit:'unit'}];assert.equal(e.view.estimatePrice(1.8,processes,new Set(['silk','foil']),{silk:2}).total,2.2);assert.equal(e.view.estimatePrice(1.8,processes,new Set(['silk','unknown'])).total,null);assert.equal(e.view.estimatePrice(null,processes,new Set(['silk'])).total,null);assert.equal(e.view.estimatePrice(1.8,processes,new Set(['free'])).total,1.8);for(const silk of [0,10,1.5,''])assert.equal(e.view.estimatePrice(1.8,processes,new Set(['silk']),{silk}).total,null);}finally{e.close();}});
test('real controls update immediately without replacing focused colour input',async()=>{const e=await setup();try{const settings={processStandards:[{id:'silk',name:'丝印',englishName:'Screen printing',price:.1,unit:'colour',moq:'',leadTime:''}]};const container=e.doc.querySelector('main');container.innerHTML=e.view.compactDetail(record,settings);const dispose=e.view.bindDetail(container,record,settings);const check=e.doc.querySelector('[data-pd-finish]');check.checked=true;check.dispatchEvent(new e.dom.window.Event('change',{bubbles:true}));const input=e.doc.querySelector('[data-pd-count]');input.focus();input.value='2';input.dispatchEvent(new e.dom.window.Event('input',{bubbles:true}));assert.match(e.doc.querySelector('.pd-estimate-value').textContent,/2\.00/);assert.equal(e.doc.activeElement,input);assert.equal(e.doc.querySelector('[data-pd-count]'),input);dispose();}finally{e.close();}});
test('public facts use only explicitly supplied safe values with no pricing module dependency',async()=>{const e=await setup();try{const m=(await evaluateBrowserModule(e.dom,path.join(root,'product-detail-facts.js'))).namespace;const html=m.factRows({material:'PET',spec:'50 mL',uses:'面霜',supplierRaw:'SECRET',quoteRaw:'1.80元'},{client:true});assert.doesNotMatch(html,/SECRET|1\.80|供应商|报价|裸瓶/);assert.match(html,/50 mL/);}finally{e.close();}});
test('administrator bulk controls preserve unchecked fields and deliberately clear checked blanks',async()=>{const e=await setup();try{const m=(await evaluateBrowserModule(e.dom,path.join(root,'admin-product-tools.js'))).namespace;e.doc.querySelector('main').innerHTML=m.bulkPanel(2);const form=e.doc.querySelector('form');form.querySelector('[data-bulk-enable="materials"]').checked=true;form.querySelector('[data-bulk-enable="bareBottlePrice"]').checked=true;const patch=JSON.parse(JSON.stringify(m.bulkPatch(form)));assert.deepEqual(patch,{materials:[],materialRaw:'',bareBottlePrice:''});assert.ok(!('moqRaw' in patch));}finally{e.close();}});
test('structured standard editor round-trips unknown fees and custom additions',async()=>{const e=await setup();try{const m=(await evaluateBrowserModule(e.dom,path.join(root,'admin-product-tools.js'))).namespace;const form=e.doc.createElement('form');form.innerHTML=m.processEditor({});e.doc.querySelector('main').append(form);let rows=m.readProcesses(form);assert.equal(rows.length,8);assert.ok(rows.every(r=>r.price===null));form.querySelector('[data-process-key="price"]').value='.15';form.querySelector('#processRows').insertAdjacentHTML('beforeend',m.processRow({id:'new',name:'新工艺',englishName:'New',price:null,unit:'unit',moq:'1000',leadTime:'7天'}));rows=m.readProcesses(form);assert.equal(rows[0].price,.15);assert.equal(rows[8].moq,'1000');}finally{e.close();}});
test('actual admin selection, confirmation, POST and conflict keep draft with no retry',async()=>{
 const fs=require('node:fs');const dom=new JSDOM(fs.readFileSync(path.join(root,'admin.html'),'utf8'),{url:'https://synthetic.test/admin/tools',runScripts:'outside-only',pretendToBeVisual:true});
 const w=dom.window,d=w.document,posts=[];let conflict=false;const records=[1,2].map(n=>({...record,id:'row-'+n,productCode:'YZ-BC-99000'+n,version:1,images:[]}));
 w.matchMedia=()=>({matches:true,addEventListener(){}});w.confirm=()=>true;w.HTMLDialogElement.prototype.showModal=function(){this.open=true;};w.HTMLDialogElement.prototype.close=function(){this.open=false;};w.HTMLElement.prototype.scrollIntoView=function(){};
 w.fetch=async(url,options={})=>{const body=options.body?JSON.parse(options.body):undefined;if(body)posts.push({url,body});let out={};let status=200;
  if(url==='/api/session')out={role:'admin',username:'qa',csrf:'qa-csrf'};
  else if(url==='/api/admin/records'&&body){if(conflict){status=409;out={error:'conflict'};}else{for(const item of body.items){const r=records.find(r=>r.id===item.id);Object.assign(r,body.patch);r.version++;}out={count:body.items.length,items:records};}}
  else if(url==='/api/admin/records')out={items:records};else if(url==='/api/admin/taxonomy')out={value:{},version:1};
  else if(url==='/api/admin/search-status')out={available:false};
  return new Response(JSON.stringify(out),{status,headers:{'Content-Type':'application/json'}});
 };
 const wait=async(fn)=>{for(let n=0;n<200;n++){if(fn())return;await new Promise(r=>setTimeout(r,5));}throw Error('Admin did not reach expected state');};
 const change=(selector,value)=>{const el=d.querySelector(selector);if(el.type==='checkbox')el.checked=value;else el.value=value;el.dispatchEvent(new w.Event('change',{bubbles:true}));};
 try{await evaluateBrowserModule(dom,path.join(root,'admin.js'));await wait(()=>d.querySelector('[data-select-record]'));
  change('[data-select-page]',true);assert.equal(d.querySelector('#bulkCount').textContent,'2');change('[data-bulk-enable="bareBottlePrice"]',true);change('[data-bulk-value="bareBottlePrice"]','2.40元');
  d.querySelector('#bulkRecordsForm').dispatchEvent(new w.Event('submit',{bubbles:true,cancelable:true}));await wait(()=>posts.length===1&&d.querySelector('#bulkCount').textContent==='0');assert.equal(posts[0].body.action,'bulk');assert.deepEqual(posts[0].body.patch,{bareBottlePrice:'2.40元'});assert.equal(posts[0].body.items.length,2);assert.deepEqual(posts[0].body.items.map(x=>x.version),[1,1]);
  conflict=true;change('[data-select-page]',true);change('[data-bulk-enable="moqRaw"]',true);change('[data-bulk-value="moqRaw"]','1000');d.querySelector('#bulkRecordsForm').dispatchEvent(new w.Event('submit',{bubbles:true,cancelable:true}));await wait(()=>d.querySelector('#bulkRecordsForm [data-form-status]').classList.contains('error'));assert.equal(posts.length,2);assert.equal(d.querySelector('#bulkCount').textContent,'2');assert.equal(d.querySelector('[data-bulk-value="moqRaw"]').value,'1000');assert.equal(d.querySelector('#bulkRecordsForm button[type="submit"]').disabled,false);
 }finally{dom.window.close();}
});
