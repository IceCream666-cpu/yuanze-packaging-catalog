const {test}=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs');
const path=require('node:path');
const {JSDOM,VirtualConsole}=require('jsdom');
const {evaluateBrowserModule}=require('./module-loader.cjs');
const base=path.resolve(__dirname,'../../server-reference/public');
const fixture={id:'approved',productCode:'YZ-BC-000001',capacity:'100 mL',category:'瓶类',bottleType:'喷雾瓶',materials:['玻璃'],uses:['爽肤水'],referenceUses:[],sections:['face'],specifications:[],images:[{url:'/client-media/approved_1.jpg'},{url:'/client-media/approved_2.jpg'}]};
const reply=value=>new Response(JSON.stringify(value),{headers:{'Content-Type':'application/json'}});
async function setup(){
  const errors=[],console=new VirtualConsole();console.on('jsdomError',error=>{if(!error.message.includes('Not implemented: navigation'))errors.push(error.message);});
  const dom=new JSDOM(fs.readFileSync(path.join(base,'client.html'),'utf8'),{url:'https://catalog.test/client/products',runScripts:'outside-only',pretendToBeVisual:true,virtualConsole:console});
  const w=dom.window,d=w.document,pending=[],calls=[],timers=new Map();let id=0;
  w.AbortController=AbortController;w.DOMException=DOMException;w.TypeError=TypeError;
  w.matchMedia=()=>({matches:false,addEventListener(){}});w.scrollTo=()=>{};w.HTMLElement.prototype.scrollIntoView=function(){};
  w.HTMLDialogElement.prototype.showModal=function(){this.open=true;};w.HTMLDialogElement.prototype.close=function(){this.open=false;this.dispatchEvent(new w.Event('close'));};
  w.Image=function(){const image=d.createElement('img');pending.push(image);return image;};
  w.setTimeout=(fn,ms)=>{const key=++id;timers.set(key,{fn,ms});return key;};w.clearTimeout=key=>timers.delete(key);
  w.fetch=async(url)=>{calls.push(url);if(url==='/api/session')return reply({role:'client',csrf:'fixture'});if(url.startsWith('/api/client/catalog'))return reply({items:[fixture],facets:{categories:['瓶类']},page:1,pages:1,total:1});throw Error('Unexpected fetch '+url);};
  await evaluateBrowserModule(dom,path.join(base,'client.js'));
  for(let i=0;i<100&&!d.querySelector('.gallery-card');i++)await new Promise(resolve=>setImmediate(resolve));
  assert(d.querySelector('.gallery-card'));d.querySelector('.photo-button').click();
  return{dom,w,d,pending,calls,timers,errors};
}
function dimensions(image,width=2400,height=1800){Object.defineProperties(image,{naturalWidth:{value:width},naturalHeight:{value:height}});}

test('customer HD only loads approved opaque URL on demand and preserves natural dimensions across language',async()=>{
  const p=await setup(),{d,pending}=p;
  assert.equal(pending.length,0);assert.equal(d.getElementById('previewImage').getAttribute('src'),'/client-media/approved_1.jpg');
  d.getElementById('imageOriginal').click();assert.equal(pending.length,1);assert.equal(pending[0].getAttribute('src'),'/client-media/approved_1.jpg?size=original');
  assert.equal(d.getElementById('imageOriginal').textContent,'取消高清加载');dimensions(pending[0]);pending[0].onload();
  assert.equal(d.getElementById('previewImage').getAttribute('src'),'/client-media/approved_1.jpg?size=original');
  assert.match(d.getElementById('imageOriginalStatus').textContent,/2400 × 1800/);
  d.querySelector('[data-language-switch]').click();assert.equal(pending.length,1);assert.match(d.getElementById('imageOriginalStatus').textContent,/HD original.*2400 × 1800 pixels/);
  assert.equal(d.getElementById('imageOriginal').textContent,'Back to preview');
  assert.equal(d.getElementById('imageDownload').getAttribute('href'),'/client-media/approved_1.jpg?size=original&download=YZ-BC-000001-1.jpg');
  d.getElementById('imageOriginal').click();assert.equal(d.getElementById('previewImage').getAttribute('src'),'/client-media/approved_1.jpg');
  assert.equal(p.calls.length,2);assert.deepEqual(p.errors,[]);p.dom.window.close();
});

test('customer HD errors, cancel, switch and close keep previews and ignore stale completions',async()=>{
  const p=await setup(),{d,pending}=p,button=d.getElementById('imageOriginal');
  button.click();pending[0].onerror();assert.equal(button.textContent,'重试高清原图');assert.equal(d.getElementById('previewImage').hidden,false);
  button.click();const cancelled=pending[1];dimensions(cancelled);button.click();assert.equal(cancelled.hasAttribute('src'),false);cancelled.onload();
  assert.equal(d.getElementById('previewImage').getAttribute('src'),'/client-media/approved_1.jpg');
  button.click();const old=pending[2];dimensions(old);d.getElementById('imageNext').click();old.onload();
  assert.equal(d.getElementById('previewImage').getAttribute('src'),'/client-media/approved_2.jpg');
  assert.equal(button.textContent,'查看高清原图');assert.equal(d.getElementById('imageOriginalStatus').hidden,true);
  button.click();const closed=pending[3];dimensions(closed);d.getElementById('closePreview').click();closed.onload();
  assert.equal(d.getElementById('previewImage').hasAttribute('src'),false);assert.equal(d.getElementById('imageOriginalStatus').hidden,true);
  assert.deepEqual(p.errors,[]);p.dom.window.close();
});

test('customer attachment is native, immediately announces request, prevents duplicate clicks and resets on switch',async()=>{
  const p=await setup(),{d,w,calls,timers}=p,link=d.getElementById('imageDownload');
  const first=new w.MouseEvent('click',{bubbles:true,cancelable:true});link.dispatchEvent(first);assert.equal(first.defaultPrevented,false);
  assert.match(d.getElementById('imageDownloadStatus').textContent,/已发起下载/);assert.doesNotMatch(d.getElementById('imageDownloadStatus').textContent,/完成|成功/);
  const duplicate=new w.MouseEvent('click',{bubbles:true,cancelable:true});link.dispatchEvent(duplicate);assert.equal(duplicate.defaultPrevented,true);
  d.querySelector('[data-language-switch]').click();assert.match(d.getElementById('imageDownloadStatus').textContent,/Download requested/);
  const cooldown=[...timers].find(([,timer])=>timer.ms===2000);timers.delete(cooldown[0]);cooldown[1].fn();
  const again=new w.MouseEvent('click',{bubbles:true,cancelable:true});link.dispatchEvent(again);assert.equal(again.defaultPrevented,false);
  d.getElementById('imageNext').click();assert.equal(d.getElementById('imageDownloadStatus').hidden,true);assert.match(link.href,/approved_2.jpg\?size=original&download=/);
  assert.equal(calls.length,2,'download should never wait for a JS fetch/blob');assert.deepEqual(p.errors,[]);p.dom.window.close();
});

test('customer HD timeout shows translated retry and zero-dimension image never claims HD success',async()=>{
  const p=await setup(),{d,timers,pending}=p,button=d.getElementById('imageOriginal');
  button.click();const timeout=[...timers].find(([,timer])=>timer.ms===60000);timers.delete(timeout[0]);timeout[1].fn();
  assert.equal(button.textContent,'重试高清原图');assert.equal(d.getElementById('previewImage').getAttribute('src'),'/client-media/approved_1.jpg');
  button.click();pending.at(-1).onload();assert.equal(button.textContent,'重试高清原图');assert.doesNotMatch(d.getElementById('imageOriginalStatus').textContent,/0 × 0/);
  assert.deepEqual(p.errors,[]);p.dom.window.close();
});
