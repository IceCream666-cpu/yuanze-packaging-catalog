const {test}=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs');
const path=require('node:path');
const {JSDOM,VirtualConsole}=require('jsdom');
const {evaluateBrowserModule}=require('./module-loader.cjs');
const root=path.resolve(__dirname,'../../server-reference/public');
const image=(name,extra={})=>({path:'uploads/'+name+'.png',role:'product',imageScope:'single_product',...extra});
const crop={x:0,y:0,width:.5,height:1,sourceWidth:800,sourceHeight:800};
const records=[
  {id:'small',productCode:'YZ-BC-990001',kind:'package',name:'洗手液圆瓶250ml',capacityMl:250,materials:['PET'],bareBottlePrice:'1.40元/个',images:[image('small'),image('source',{displayCrop:crop}),image('source',{role:'reference',imageScope:'source_page'})]},
  {id:'large',productCode:'YZ-BC-990002',kind:'package',name:'洗手液圆瓶500ml',capacityMl:500,materials:['PET'],bareBottlePrice:'1.60元/个',images:[image('large'),image('large-side')]},
  {id:'single',productCode:'YZ-BC-990003',kind:'package',name:'单图瓶',images:[image('single')]},
];
const reviewedGroup={id:'handwash',name:'洗手液圆瓶',galleryScope:'record',recordIds:['small','large'],specs:[{label:'250 mL',recordIds:['small']},{label:'500 mL',recordIds:['large']}]};
test('selected customer size remains readable with the production stylesheet cascade',()=>{
  const page=fs.readFileSync(path.join(root,'client.html'),'utf8'),dom=new JSDOM(page);
  try{
    const d=dom.window.document;
    for(const file of [...page.matchAll(/<link[^>]+href="([^"?]+)(?:\?[^"]*)?"/g)].map(m=>m[1]).filter(name=>name.endsWith('.css'))){
      const style=d.createElement('style');style.textContent=fs.readFileSync(path.join(root,file.replace(/^\//,'')),'utf8');d.head.append(style);
    }
    d.querySelector('#detailVariants').innerHTML='<button class="button active" aria-pressed="true">500 mL</button>';
    const css=dom.window.getComputedStyle(d.querySelector('#detailVariants button'));
    const luminance=value=>value.match(/\d+/g).slice(0,3).map(n=>{const s=Number(n)/255;return s<=.04045?s/12.92:((s+.055)/1.055)**2.4;}).reduce((s,v,i)=>s+v*[.2126,.7152,.0722][i],0);
    const a=luminance(css.color),b=luminance(css.backgroundColor);
    assert.ok((Math.max(a,b)+.05)/(Math.min(a,b)+.05)>=4.5,'selected size needs AA text contrast');
  }finally{dom.window.close();}
});
const response=body=>new Response(JSON.stringify(body),{status:200,headers:{'Content-Type':'application/json'}});
async function until(fn,label){for(let n=0;n<400;n++){if(fn())return;await new Promise(resolve=>setTimeout(resolve,5));}throw Error('Timeout: '+label);}
function browser(filename){
  const errors=[],console=new VirtualConsole();console.on('jsdomError',e=>errors.push(e.message));
  const dom=new JSDOM(fs.readFileSync(path.join(root,filename),'utf8'),{url:'https://catalog.test/',runScripts:'outside-only',pretendToBeVisual:true,virtualConsole:console});
  const w=dom.window,d=w.document;w.matchMedia=()=>({matches:false,addEventListener(){}});w.scrollTo=()=>{};w.HTMLElement.prototype.scrollIntoView=function(){};
  w.HTMLDialogElement.prototype.showModal=function(){this.open=true;};w.HTMLDialogElement.prototype.close=function(){this.open=false;this.dispatchEvent(new w.Event('close'));};
  return {dom,w,d,errors};
}
async function employee({group=reviewedGroup,items=records}={}){
  const p=browser('index.html');p.w.fetch=async url=>response(url==='/api/session'?{role:'employee',username:'qa',csrf:'fixture'}:url==='/api/catalog'?{records:items,settings:{processStandards:[{id:'silk',name:'丝印',englishName:'Screen printing',price:.1,unit:'colour'}]}}:url==='/api/preferences'?{favorites:[]}:url==='/api/image-search/status'?{available:false}:{});
  await evaluateBrowserModule(p.dom,path.join(root,'app.js'),`\nreviewedProductGroups.splice(0,reviewedProductGroups.length,...${JSON.stringify(group?[group]:[])});`);
  await until(()=>p.d.querySelector('.card-title'),'employee catalogue');return p;
}
const show=(p,id)=>p.d.querySelector(`[data-detail="${id}"]`).click();
const src=p=>p.d.querySelector('#detailPhoto img').getAttribute('src');
const step=(p,n)=>p.d.querySelector(`[data-detail-image-step="${n}"]`);
test('employee arrows and thumbnails track cropped views, downloads, position, boundaries and focus',async()=>{
  const p=await employee();try{
    show(p,'small');assert.equal(src(p),'/uploads/small.png');assert.equal(p.d.querySelector('#detailImageStatus').textContent,'1 / 3');assert.equal(step(p,-1).disabled,true);assert.match(step(p,1).textContent,/下一张/);
    const next=step(p,1);assert.equal(p.d.querySelector('#detailPhoto').contains(next),true);assert.equal(p.d.querySelector('#detailPhoto').contains(p.d.querySelector('#detailImageStatus')),false);next.focus();next.click();assert.equal(step(p,1),next);assert.equal(p.d.activeElement,next);assert.equal(src(p),'/uploads/source.png');assert.ok(p.d.querySelector('#detailPhoto .image-viewport'));assert.equal(p.d.querySelector('#detailImageStatus').textContent,'2 / 3');assert.match(p.d.querySelector('#downloadImageLink').getAttribute('href'),/^\/uploads\/source.png\?download=YZ-BC-990001-/);
    next.click();assert.equal(p.d.querySelector('#detailPhoto .image-viewport'),null);assert.equal(p.d.querySelector('#detailImageStatus').textContent,'3 / 3');assert.equal(next.disabled,true);
    const thumb=p.d.querySelector('.detail-visual [data-image="/uploads/small.png"]');thumb.focus();thumb.click();assert.equal(p.d.activeElement,thumb);assert.equal(src(p),'/uploads/small.png');assert.equal(thumb.getAttribute('aria-current'),'true');assert.equal(p.d.querySelectorAll('.detail-visual button[aria-current=true]').length,1);assert.equal(p.d.querySelector('#originalImageLink').getAttribute('href'),src(p));assert.deepEqual(p.errors,[]);
  }finally{p.dom.window.close();}
});
test('employee specification selection rebuilds only that record gallery and quote, resetting downloads',async()=>{
  const p=await employee();try{
    show(p,'small');const selector=p.d.querySelector('.group-selector'),price=p.d.querySelector('.pd-price');assert.equal(selector.parentElement,price.closest('.pd-info').parentElement);assert.equal(selector.nextElementSibling,price.closest('.pd-info'));assert.equal(p.d.querySelector('.detail-visual').contains(selector),false);assert.equal(p.d.querySelectorAll('.pd-price').length,1);assert.equal(p.d.querySelectorAll('.pd-facts').length,1);step(p,1).click();const previousImage=p.d.querySelector('#detailPhoto img');
    p.d.querySelector('.group-option[data-detail="large"]').focus();p.d.querySelector('.group-option[data-detail="large"]').click();assert.equal(p.d.activeElement,p.d.querySelector('.group-option.active'));assert.equal(src(p),'/uploads/large.png');assert.equal(p.d.querySelector('#detailImageStatus').textContent,'1 / 2');assert.equal(p.d.querySelector('[data-detail-record]').dataset.detailRecord,'large');assert.match(p.d.querySelector('.pd-price-value').textContent,/1.60/);assert.doesNotMatch(p.d.querySelector('.pd-price-value').textContent,/1.40/);assert.equal(p.d.querySelector('[data-image="/uploads/small.png"]'),null);assert.match(p.d.querySelector('#downloadImageLink').getAttribute('href'),/large.png\?download=YZ-BC-990002-1/);
    previousImage.dispatchEvent(new p.w.Event('error'));assert.equal(src(p),'/uploads/large.png');step(p,1).click();assert.equal(src(p),'/uploads/large-side.png');
    show(p,'single');assert.equal(p.d.querySelector('.pd-gallery-controls'),null);assert.equal(src(p),'/uploads/single.png');assert.match(p.d.querySelector('#downloadImageLink').download,/990003-1/);assert.deepEqual(p.errors,[]);
  }finally{p.dom.window.close();}
});
test('employee keyboard navigation leaves editable pricing input keys alone and failed-image fallback updates position',async()=>{
  const p=await employee();try{
    show(p,'small');const modal=p.d.querySelector('#modal');modal.dispatchEvent(new p.w.KeyboardEvent('keydown',{key:'ArrowRight',bubbles:true,cancelable:true}));assert.equal(p.d.querySelector('#detailImageStatus').textContent,'2 / 3');
    const input=p.d.querySelector('[data-pd-count]'),event=new p.w.KeyboardEvent('keydown',{key:'ArrowRight',bubbles:true,cancelable:true});input.dispatchEvent(event);assert.equal(event.defaultPrevented,false);assert.equal(p.d.querySelector('#detailImageStatus').textContent,'2 / 3');
    p.d.querySelector('[data-image="/uploads/small.png"]').click();p.d.querySelector('#detailPhoto img').dispatchEvent(new p.w.Event('error'));assert.equal(src(p),'/uploads/source.png');assert.equal(p.d.querySelector('#detailImageStatus').textContent,'2 / 3');assert.equal(p.d.querySelector('#downloadImageLink').hidden,false);p.d.querySelector('#detailPhoto img').dispatchEvent(new p.w.Event('error'));assert.equal(p.d.querySelector('#downloadImageLink').hidden,true);assert.deepEqual(p.errors,[]);
  }finally{p.dom.window.close();}
});
test('employee language change keeps selected gallery position and translates visible controls',async()=>{
  const p=await employee();try{
    show(p,'small');step(p,1).click();p.d.querySelector('[data-language-switch]').click();await until(()=>step(p,1).textContent.includes('Next'),'translated gallery');assert.equal(src(p),'/uploads/source.png');assert.equal(p.d.querySelector('#detailImageStatus').textContent,'2 / 3');assert.equal(p.d.querySelector('#detailImageStatus').getAttribute('aria-label'),'Image 2 of 3');assert.equal(step(p,1).getAttribute('aria-label'),'Next image');assert.deepEqual(p.errors,[]);
  }finally{p.dom.window.close();}
});
test('employee alias source remains navigable when its presentation thumbnail uses a retained image',async()=>{
  const group={...reviewedGroup,galleryScope:undefined,imageAliases:{'uploads/small.png':'uploads/large.png'}};
  const p=await employee({group});try{show(p,'small');assert.equal(src(p),'/uploads/small.png');assert.equal(step(p,1).disabled,false);assert.equal(p.d.querySelector('.detail-visual [data-image="/uploads/large.png"]').getAttribute('aria-current'),'true');step(p,1).click();assert.equal(p.d.querySelector('#detailImageStatus').textContent,'2 / 4');assert.deepEqual(p.errors,[]);}finally{p.dom.window.close();}
});
const publicItems=[1,2].map(n=>({id:'opaque'+n,productCode:'YZ-BC-99000'+n,capacity:n===1?'250 mL':'500 mL',category:'瓶类',bottleType:'圆瓶',materials:['PET'],uses:['洗手液'],sections:['body-head'],specifications:[],supplierRaw:'SECRET SUPPLIER',quoteRaw:'SECRET PRICE',images:(n===1?[1,2,3]:[1]).map(i=>({url:`/client-media/item${n}-${i}.jpg`})).concat(n===1?[{url:'/uploads/secret.png'}]:[])}));
async function customer({items=publicItems,imageItems=[]}={}){const p=browser('client.html');p.w.fetch=async url=>response(url==='/api/session'?{role:'client',csrf:'fixture'}:url==='/api/client/image-search'?{items:imageItems}:{items,facets:{},page:1,pages:1,total:items.length});await evaluateBrowserModule(p.dom,path.join(root,'client.js'));await until(()=>p.d.querySelector('.gallery-card'),'client catalogue');return p;}
test('customer visible arrows and thumbnails preserve focus, safe image URLs, downloads and i18n',async()=>{
  const p=await customer();try{
    p.d.querySelector('.photo-button').click();assert.equal(p.d.querySelector('.preview-controls').hidden,false);assert.equal(p.d.querySelector('.preview-image-wrap').contains(p.d.querySelector('#imageNext')),true);assert.equal(p.d.querySelector('.preview-image-wrap .pd-gallery-controls').hidden,false);assert.equal(p.d.querySelector('.preview-image-wrap').contains(p.d.querySelector('#imageStatus')),false);assert.match(p.d.querySelector('#imageNext').textContent,/下一张/);assert.equal(p.d.querySelector('#imageStatus').textContent,'1 / 3');assert.equal(p.d.querySelector('#imagePrevious').disabled,true);
    const thumb=p.d.querySelector('[data-image-index="1"]');thumb.focus();thumb.click();assert.equal(p.d.activeElement,thumb);assert.equal(p.d.querySelector('[data-image-index="1"]'),thumb);assert.equal(thumb.getAttribute('aria-current'),'true');assert.equal(p.d.querySelector('#previewImage').getAttribute('src'),'/client-media/item1-2.jpg');assert.equal(p.d.querySelector('#imageStatus').textContent,'2 / 3');assert.match(p.d.querySelector('#imageDownload').getAttribute('href'),/^\/client-media\/item1-2.jpg\?download=YZ-BC-990001-2.jpg$/);
    p.d.querySelector('[data-language-switch]').click();assert.match(p.d.querySelector('#imageNext').textContent,/Next/);assert.equal(p.d.querySelector('#imageStatus').getAttribute('aria-label'),'Image 2 of 3');assert.equal(p.d.querySelector('#previewImage').getAttribute('src'),'/client-media/item1-2.jpg');assert.doesNotMatch(p.d.querySelector('#preview').outerHTML,/SECRET|\/uploads\//);assert.deepEqual(p.errors,[]);
  }finally{p.dom.window.close();}
});
test('customer single-image record hides navigation and discards delayed errors from the prior record',async()=>{
  const p=await customer();try{
    p.d.querySelector('.photo-button').click();p.d.querySelector('#imageNext').click();const old=p.d.querySelector('#previewImage');p.d.querySelector('#closePreview').click();assert.equal(p.d.activeElement,p.d.querySelector('.photo-button'));p.d.querySelectorAll('.photo-button')[1].click();assert.equal(p.d.querySelector('.preview-controls').hidden,true);assert.equal(p.d.querySelector('#imageThumbnails').hidden,true);assert.equal(p.d.querySelector('#previewImage').getAttribute('src'),'/client-media/item2-1.jpg');assert.match(p.d.querySelector('#imageDownload').download,/990002-1/);
    assert.equal(p.d.querySelector('.preview-image-wrap .pd-gallery-controls').hidden,true);for(let n=0;n<4;n++)old.dispatchEvent(new p.w.Event('error'));assert.equal(p.d.querySelector('#previewError').hidden,true);assert.equal(p.d.querySelector('#previewImage').hidden,false);assert.equal(p.d.querySelector('#previewImage').getAttribute('src'),'/client-media/item2-1.jpg');const event=new p.w.KeyboardEvent('keydown',{key:'ArrowRight',bubbles:true,cancelable:true});p.d.querySelector('#preview').dispatchEvent(event);assert.equal(event.defaultPrevented,false);assert.deepEqual(p.errors,[]);
  }finally{p.dom.window.close();}
});
test('customer same-bottle card switches each safe specification gallery and keeps selected-spec collections distinct',async()=>{
  const small={...publicItems[0],specifications:[{label:'口径',value:'24 mm'}]},large={...publicItems[1],specifications:[{label:'口径',value:'28 mm'}],variants:[{url:'/uploads/nested-secret.png',supplierRaw:'SECRET NESTED'}]};
  const p=await customer({items:[{...small,variants:[small,large]}]});try{
    assert.equal(p.d.querySelectorAll('.gallery-card').length,1);assert.match(p.d.querySelector('.card-title').textContent,/250 mL \/ 500 mL/);assert.match(p.d.querySelector('.capacity').textContent,/250 mL \/ 500 mL/);p.d.querySelector('.photo-button').click();p.d.querySelector('#imageNext').click();
    const button=p.d.querySelector('[data-client-variant="opaque2"]');button.focus();button.click();assert.equal(p.d.activeElement,button);assert.equal(button.getAttribute('aria-pressed'),'true');assert.equal(p.d.querySelector('#detailCode').textContent,'YZ-BC-990002');assert.match(p.d.querySelector('#detailFacts').textContent,/500 mL/);assert.match(p.d.querySelector('#detailSpecifications').textContent,/28 mm/);assert.equal(p.d.querySelector('#previewImage').getAttribute('src'),'/client-media/item2-1.jpg');assert.equal(p.d.querySelector('#imageStatus').textContent,'1 / 1');assert.equal(p.d.querySelector('.preview-controls').hidden,true);assert.match(p.d.querySelector('#imageDownload').getAttribute('href'),/item2-1.jpg\?download=YZ-BC-990002-1.jpg/);
    p.d.querySelector('#detailActions [data-item-action="shortlist"]').click();p.d.querySelector('#detailActions [data-item-action="favourite"]').click();p.d.querySelector('[data-client-variant="opaque1"]').click();assert.equal(p.d.querySelector('#previewImage').getAttribute('src'),'/client-media/item1-1.jpg');assert.equal(p.d.querySelector('#imageStatus').textContent,'1 / 3');assert.equal(p.d.querySelector('.preview-controls').hidden,false);assert.match(p.d.querySelector('#detailSpecifications').textContent,/24 mm/);
    p.d.querySelector('#detailActions [data-item-action="shortlist"]').click();p.d.querySelector('#detailActions [data-item-action="favourite"]').click();assert.equal(p.d.querySelector('#shortlistCount').textContent,'2');assert.equal(p.d.querySelector('#favoriteCount').textContent,'2');assert.match(p.d.querySelector('#consultText').value,/990001.*250 mL/);assert.match(p.d.querySelector('#consultText').value,/990002.*500 mL/);assert.doesNotMatch(p.d.querySelector('#preview').outerHTML,/SECRET|\/uploads\//);p.d.querySelector('[data-client-variant="opaque2"]').click();p.d.querySelector('[data-language-switch]').click();p.d.querySelector('#closePreview').click();assert.equal(p.d.activeElement,p.d.querySelector('.photo-button'));assert.deepEqual(p.errors,[]);
  }finally{p.dom.window.close();}
});
test('customer searched representative starts on its own specification and malformed variants cannot create selector entries',async()=>{
  const p=await customer({items:[{...publicItems[1],variants:publicItems}]});try{p.d.querySelector('.photo-button').click();assert.equal(p.d.querySelector('[data-client-variant="opaque2"]').getAttribute('aria-pressed'),'true');assert.equal(p.d.querySelector('#previewImage').getAttribute('src'),'/client-media/item2-1.jpg');assert.equal(p.d.querySelector('#detailCode').textContent,'YZ-BC-990002');assert.deepEqual(p.errors,[]);}finally{p.dom.window.close();}
  const q=await customer({items:[{...publicItems[0],variants:[publicItems[0],publicItems[0],{...publicItems[1],images:[{url:'/uploads/secret.png'}]},{...publicItems[1],id:'<script>secret</script>'}]}]});try{q.d.querySelector('.photo-button').click();assert.equal(q.d.querySelector('#detailVariants').hidden,true);assert.equal(q.d.querySelectorAll('[data-client-variant]').length,0);assert.doesNotMatch(q.d.querySelector('#preview').outerHTML,/secret|\/uploads\//);assert.deepEqual(q.errors,[]);}finally{q.dom.window.close();}
});
test('customer image-search capacity filter selects the matching safe variant while saved collections keep the chosen specification',async()=>{
  const family={...publicItems[0],variants:[publicItems[1],publicItems[0]]},p=await customer({items:[family],imageItems:[family]});try{
    const submit=id=>p.d.querySelector('#'+id).dispatchEvent(new p.w.Event('submit',{bubbles:true,cancelable:true}));
    const capacity=checked=>{const input=p.d.querySelector('[data-filter="capacity"][value="500 mL"]');assert.ok(input);input.checked=checked;input.dispatchEvent(new p.w.Event('change',{bubbles:true}));};
    p.d.querySelector('.photo-button').click();p.d.querySelector('#detailActions [data-item-action="shortlist"]').click();p.d.querySelector('#detailActions [data-item-action="favourite"]').click();p.d.querySelector('#closePreview').click();
    p.d.querySelector('#imageSearchOpen').click();Object.defineProperty(p.d.querySelector('#imageSearchFile'),'files',{value:[new p.w.File(['fixture'],'bottle.png',{type:'image/png'})]});submit('imageSearchForm');await until(()=>p.d.querySelector('#collectionLabel').textContent==='图片相似结果','grouped image results');
    assert.equal(p.d.querySelectorAll('.gallery-card').length,1);assert.equal(p.d.querySelector('.record-code').textContent,'YZ-BC-990001');assert.equal(p.d.querySelector('.photo-button img').getAttribute('src'),'/client-media/item1-1.jpg?thumb=1');assert.ok(p.d.querySelector('[data-filter="capacity"][value="500 mL"]'));
    capacity(true);assert.equal(p.d.querySelectorAll('.gallery-card').length,1);assert.equal(p.d.querySelector('.record-code').textContent,'YZ-BC-990002');assert.equal(p.d.querySelector('.photo-button img').getAttribute('src'),'/client-media/item2-1.jpg?thumb=1');p.d.querySelector('.photo-button').click();assert.equal(p.d.querySelector('#detailCode').textContent,'YZ-BC-990002');assert.equal(p.d.querySelector('[data-client-variant="opaque2"]').getAttribute('aria-pressed'),'true');assert.equal(p.d.querySelector('#previewImage').getAttribute('src'),'/client-media/item2-1.jpg');assert.match(p.d.querySelector('#imageDownload').download,/990002-1/);assert.equal(p.d.querySelectorAll('[data-client-variant]').length,2);p.d.querySelector('#closePreview').click();
    p.d.querySelector('#query').value='YZ-BC-990001';submit('searchForm');assert.equal(p.d.querySelectorAll('.gallery-card').length,0,'Code250 combined with capacity500 cannot match a series by combining sibling facts');p.d.querySelector('#query').value='SECRET SUPPLIER';submit('searchForm');assert.equal(p.d.querySelectorAll('.gallery-card').length,0);p.d.querySelector('#query').value='';submit('searchForm');assert.equal(p.d.querySelectorAll('.gallery-card').length,1);
    p.d.querySelector('#shortlistView').click();assert.equal(p.d.querySelectorAll('.gallery-card').length,0,'Selected250 shortlist does not become500 when filtering');p.d.querySelector('#favoritesView').click();assert.equal(p.d.querySelectorAll('.gallery-card').length,0,'Selected250 favourite does not become500 when filtering');capacity(false);assert.equal(p.d.querySelector('.record-code').textContent,'YZ-BC-990001');assert.equal(p.d.querySelector('#shortlistCount').textContent,'1');assert.equal(p.d.querySelector('#favoriteCount').textContent,'1');assert.match(p.d.querySelector('#consultText').value,/990001.*250 mL/);assert.doesNotMatch(p.d.querySelector('#consultText').value,/990002|500 mL/);assert.doesNotMatch(p.d.querySelector('#gallery').outerHTML,/SECRET|\/uploads\//);assert.deepEqual(p.errors,[]);
  }finally{p.dom.window.close();}
});
