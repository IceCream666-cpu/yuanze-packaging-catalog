// Real-browser regression for the client1.2 featured homepage and retained library.
// Run against an existing preview. QA_ALLOW_PENDING_ASSETS=1 permits in-progress cutouts only.
const {chromium}=require('playwright');
const fs=require('node:fs'),path=require('node:path'),crypto=require('node:crypto');
const URL=process.env.QA_URL||'http://127.0.0.1:8784/';
const CHROME=process.env.QA_CHROME||'/Applications/Google Chrome.app/Contents/MacOS/Google Chrome';
const out=process.env.QA_OUTPUT;
const phase=process.env.QA_PHASE||'all';
const featured=JSON.parse(fs.readFileSync(path.join(__dirname,'../src/featured.json')));
const posters=JSON.parse(fs.readFileSync(path.join(__dirname,'../src/posters.json')));
const report={url:URL,phase,checks:[],pendingAssets:[],runtimeErrors:[],apiRequests:[]};
function check(name,ok,detail){report.checks.push({name,ok,detail});console.log(`${ok?'PASS':'FAIL'} ${name}${detail?' '+JSON.stringify(detail):''}`);}
const settle=p=>p.waitForTimeout(780);
const selected=p=>p.locator('.poster-plane.center').getAttribute('data-poster-id');
const chosen=p=>p.locator('.colour-swatches [aria-pressed="true"]').getAttribute('aria-label');
async function choose(p,index){await p.locator('.colour-swatches button').nth(index).click();await settle(p);}
async function library(p){await p.locator('.browse-collection').click();await settle(p);}
async function home(p){await p.locator('.brand').click();await settle(p);}
async function fresh(p){await p.goto(URL,{waitUntil:'networkidle'});await settle(p);}
async function swipe(page,cdp,x0,y0,x1,y1){
 await cdp.send('Input.dispatchTouchEvent',{type:'touchStart',touchPoints:[{x:x0,y:y0}]});
 for(let i=1;i<=12;i++){await cdp.send('Input.dispatchTouchEvent',{type:'touchMove',touchPoints:[{x:x0+(x1-x0)*i/12,y:y0+(y1-y0)*i/12}]});await page.waitForTimeout(24);}
 await page.waitForTimeout(130);await cdp.send('Input.dispatchTouchEvent',{type:'touchEnd',touchPoints:[]});await settle(page);
}

(async()=>{
 if(out)fs.mkdirSync(out,{recursive:true});
 const browser=await chromium.launch({headless:true,executablePath:CHROME});
 try{
  const context=await browser.newContext({viewport:{width:1440,height:1000},acceptDownloads:true});
  const p=await context.newPage();p.setDefaultTimeout(10000);
  p.setDefaultNavigationTimeout(45000);
  p.on('pageerror',e=>report.runtimeErrors.push(e.message));
  p.on('request',r=>{if(r.url().includes('/api/'))report.apiRequests.push(r.url());});
  if(phase!=='mobile'){
  await fresh(p);
  check('homepage opens the pink featured design with eight swatches',await p.locator('.colour-intro h1').textContent()==='Care in colour.'&&await p.locator('.colour-swatches button').count()===8&&await p.locator('.showroom').evaluate(e=>e.style.getPropertyValue('--scene'))===featured[0].background);
  check('homepage uses display serif and floating product presentation',await p.locator('.colour-intro h1').evaluate(e=>/Bodoni|Didot|Times New Roman/.test(getComputedStyle(e).fontFamily))&&await p.locator('.product-stage-shell').count()===1);
  check('autoplay starts off',await p.locator('.colour-play').getAttribute('aria-pressed')==='false');
  await p.mouse.move(5,5);await p.waitForTimeout(4500);
  check('homepage stays on its first product without opting into autoplay',await chosen(p)===featured[0].name);

  const mappings=[];
  for(let i=0;i<featured.length;i++){
   await choose(p,i);
   const row={id:featured[i].id,center:await selected(p),name:await p.locator('.colour-copy h2').textContent(),dot:await chosen(p),scene:await p.locator('.showroom').evaluate(e=>e.style.getPropertyValue('--scene'))};
   const decoded=await p.locator('.poster-plane.center').evaluate(e=>{const img=e.querySelector('img');return !!img&&img.complete&&img.naturalWidth>0;});
   if(!decoded)report.pendingAssets.push(featured[i].id);
   await p.locator('.colour-poster').click();await p.waitForTimeout(180);
   const source=posters.find(item=>item.id===featured[i].id);
   row.poster=await p.locator('.lightbox-image img').getAttribute('src');
   row.posterMatches=row.poster.endsWith(source.image)&&await p.locator('.modal-toolbar strong').textContent()===source.title.zh;
   mappings.push(row);
   await p.keyboard.press('Escape');
  }
  check('all eight swatches synchronize product title background and approved poster',mappings.every((r,i)=>r.center===featured[i].id&&r.name===featured[i].name&&r.dot===featured[i].name&&r.scene===featured[i].background&&r.posterMatches),mappings);
  check('poster close returns focus to the featured action',await p.locator('.colour-poster').evaluate(e=>e===document.activeElement));
  if(report.pendingAssets.length&&process.env.QA_ALLOW_PENDING_ASSETS==='1')console.log('PENDING cutout assets '+report.pendingAssets.join(', '));
  else check('all eight featured product images decode',report.pendingAssets.length===0,report.pendingAssets);

  await choose(p,0);await p.getByRole('button',{name:'上一款',exact:true}).click();await settle(p);
  check('featured previous wraps to the eighth product',await selected(p)===featured[7].id&&await chosen(p)===featured[7].name);
  await p.getByRole('button',{name:'下一款',exact:true}).click();await settle(p);
  check('featured next wraps back to first',await selected(p)===featured[0].id);
  await p.locator('.gallery-stage').focus();
  for(let i=0;i<5;i++){await p.keyboard.press('ArrowLeft');await p.waitForTimeout(30);}await settle(p);
  check('five rapid featured keyboard steps accumulate across the seam',await selected(p)===featured[3].id&&await chosen(p)===featured[3].name);
  await choose(p,0);
  for(let i=0;i<5;i++){await p.getByRole('button',{name:'下一款',exact:true}).click();await p.waitForTimeout(30);}await settle(p);
  check('five rapid featured arrow clicks retain all selections',await selected(p)===featured[5].id&&await chosen(p)===featured[5].name);
  await choose(p,0);let box=await p.locator('.gallery-stage').boundingBox();
  await p.mouse.move(box.width*.6,box.y+box.height*.5);await p.mouse.down();await p.mouse.move(box.width*.6-360,box.y+box.height*.5,{steps:22});await p.waitForTimeout(130);await p.mouse.up();await settle(p);
  check('featured mouse drag snaps to next product without opening a modal',await selected(p)===featured[1].id&&!await p.locator('dialog').evaluate(d=>d.open));
  await choose(p,0);await p.mouse.move(box.width/2,box.y+box.height*.5);
  for(const delta of [70,50,25,10,4,1]){await p.mouse.wheel(delta,0);await p.waitForTimeout(20);}await settle(p);
  check('featured horizontal wheel inertia advances exactly once',await selected(p)===featured[1].id);
  await p.mouse.wheel(80,0);await settle(p);
  check('featured new wheel stroke advances again',await selected(p)===featured[2].id);

  await choose(p,0);await p.locator('.colour-play').click();await p.mouse.move(5,5);const started=Date.now();
  await p.waitForTimeout(3900);check('autoplay does not advance before its 4200 ms interval',await chosen(p)===featured[0].name);
  await p.waitForFunction(name=>document.querySelector('.colour-swatches [aria-pressed="true"]')?.getAttribute('aria-label')!==name,featured[0].name,{timeout:1800});
  const elapsed=Date.now()-started;await settle(p);
  check('autoplay advances at approximately 4200 ms',await selected(p)===featured[1].id&&elapsed>=4000&&elapsed<5400,{elapsedMs:elapsed});
  box=await p.locator('.gallery-stage').boundingBox();await p.mouse.move(box.width/2,box.y+box.height*.5);let paused=await chosen(p);await p.waitForTimeout(4500);
  check('autoplay pauses while the stage is hovered',await chosen(p)===paused);
  await p.mouse.move(5,5);await p.locator('.gallery-stage').focus();paused=await chosen(p);await p.waitForTimeout(4500);
  check('autoplay pauses while the stage has keyboard focus',await chosen(p)===paused);
  await p.locator('.colour-poster').click();paused=await chosen(p);await p.waitForTimeout(4500);
  check('autoplay pauses while an original poster modal is open',await chosen(p)===paused&&await p.locator('dialog').evaluate(d=>d.open));
  await p.keyboard.press('Escape');await p.locator('.colour-play').click();await p.mouse.move(5,5);paused=await chosen(p);await p.waitForTimeout(4500);
  check('explicit pause stops future automatic changes',await p.locator('.colour-play').getAttribute('aria-pressed')==='false'&&await chosen(p)===paused);

  await p.locator('.colour-play').click();await p.mouse.move(5,5);await p.waitForTimeout(1000);const beforeLibrary=await chosen(p);await library(p);await p.waitForTimeout(4500);await home(p);
  check('entering the library cancels the homepage timer and returning preserves its selection',await chosen(p)===beforeLibrary&&await p.locator('.colour-play').getAttribute('aria-pressed')==='false');
  await p.locator('.colour-play').click();await p.mouse.move(5,5);await p.emulateMedia({reducedMotion:'reduce'});paused=await chosen(p);await p.waitForTimeout(4500);
  check('reduced motion stops autoplay and all floating animations',await chosen(p)===paused&&await p.locator('.colour-play').isDisabled()&&await p.locator('.colour-play').getAttribute('aria-pressed')==='false'&&await p.evaluate(()=>document.getAnimations().filter(a=>a.playState==='running').length)===0);
  await p.emulateMedia({reducedMotion:'no-preference'});await settle(p);
  check('removing reduced motion does not silently restart autoplay',await p.locator('.colour-play').getAttribute('aria-pressed')==='false'&&!await p.locator('.colour-play').isDisabled());

  await choose(p,4);await p.locator('.colour-language').click();
  check('homepage language switch retains featured identity and translates copy',await chosen(p)===featured[4].name&&await p.locator('.colour-kind').textContent()===featured[4].kind.en&&await p.locator('html').getAttribute('lang')==='en');
  await p.locator('.colour-language').click();await choose(p,0);await p.locator('.colour-save').click();
  await library(p);check('browse all opens the full 38-poster library in overview mode',await p.locator('.poster-grid article').count()===38&&await p.locator('.view-toggle button').nth(1).getAttribute('aria-pressed')==='true');
  await p.locator('.main-nav button').nth(1).click();await settle(p);
  check('featured save is shared with the library favorites',await p.locator('.poster-grid article').count()===1&&await p.locator('.grid-image img').getAttribute('src').then(src=>src.endsWith('/assets/'+featured[0].id+'.webp')));
  await p.reload({waitUntil:'networkidle'});await settle(p);
  check('featured favorite survives a reload',await p.locator('.colour-save').getAttribute('aria-pressed')==='true');
  await p.locator('.colour-favorites').click();await settle(p);await p.locator('.grid-caption button').click();await settle(p);
  check('removing the last library favorite produces the empty state',await p.locator('.empty-state').isVisible());
  await home(p);check('removing in the library updates the homepage favorite',await p.locator('.colour-save').getAttribute('aria-pressed')==='false');
  await library(p);await p.locator('.main-nav button').first().click();await settle(p);
  await p.locator('.search-box input').fill('  WOODLAND  ');await settle(p);
  check('library English search returns the approved Woodland poster',await p.locator('.poster-grid article').count()===1&&await p.locator('.grid-image img').getAttribute('src').then(src=>src.endsWith('/assets/poster-042.webp')));
  await p.getByRole('button',{name:'Switch to English',exact:true}).click();
  check('library language toggle preserves its query and result',await p.locator('.search-box input').inputValue()==='  WOODLAND  '&&await p.locator('.poster-grid article').count()===1);
  await p.locator('.search-box input').fill('蓬松');await settle(p);
  check('library Chinese search works in English UI',await p.locator('.grid-image img').getAttribute('src').then(src=>src.endsWith('/assets/poster-051.webp')));
  await p.getByRole('button',{name:'切换为中文',exact:true}).click();await p.locator('.main-nav button').first().click();
  await p.locator('.category-tabs button').filter({hasText:'洗发护发'}).click();await p.locator('select').selectOption('natural');await p.locator('.search-box input').fill('shampoo');await settle(p);
  check('library category style and query intersect',await p.locator('.poster-grid article').count()===2);
  await home(p);await library(p);
  check('leaving and returning to the library preserves filters',await p.locator('.search-box input').inputValue()==='shampoo'&&await p.locator('select').inputValue()==='natural'&&await p.locator('.poster-grid article').count()===2);
  await p.locator('.search-box input').fill('no-result-987');await settle(p);
  check('library no-result state is actionable',await p.locator('.empty-state button').isVisible());await p.locator('.empty-state button').click();await settle(p);
  check('clearing filters restores all 38 posters',await p.locator('.poster-grid article').count()===38);
  await p.locator('.grid-image').first().click();await settle(p);await p.getByRole('button',{name:'200%',exact:true}).click();
  check('library original viewer retains zoom',await p.locator('.lightbox-image').evaluate(e=>e.classList.contains('zoomed')));
  let failedOnce=false;await p.route('**/*-original.webp',async r=>{if(!failedOnce){failedOnce=true;await r.abort();}else await r.continue();});
  await p.getByRole('button',{name:'查看高清原图',exact:true}).click();await p.waitForTimeout(500);
  check('library HD failure offers a retry',await p.getByRole('button',{name:'重试加载原图',exact:true}).isVisible());await p.getByRole('button',{name:'重试加载原图',exact:true}).click();await p.waitForTimeout(900);
  check('library HD retry displays original pixel dimensions',await p.locator('.lightbox-image img').evaluate(e=>e.naturalWidth===1448&&e.naturalHeight===1086)&&await p.locator('.lightbox-controls').innerText().then(t=>t.includes('1448 × 1086')));
  const downloading=p.waitForEvent('download');await p.getByRole('link',{name:'下载原图',exact:true}).click();const download=await downloading;
  const downloadPath=await download.path();const hash=file=>crypto.createHash('sha256').update(fs.readFileSync(file)).digest('hex');
  check('library original download is byte-identical to the approved source',hash(downloadPath)===hash(path.join(__dirname,'../public',posters[0].original)));
  if(out)await download.saveAs(path.join(out,'downloaded-original.webp'));
  await p.keyboard.press('Escape');check('library modal restores focus to its card',await p.locator('.grid-image').first().evaluate(e=>e===document.activeElement));
  await p.locator('.view-toggle button').first().click();await settle(p);await p.locator('.search-box input').focus();await p.keyboard.press('ArrowLeft');await settle(p);
  check('arrow keys in search do not change the library carousel',await selected(p)===posters[0].id);
  await p.locator('.category-tabs button').filter({hasText:'口腔护理'}).click();await settle(p);
  check('single-result library category keeps one item and disabled controls',await p.locator('.poster-plane').count()===1&&await p.locator('.gallery-navigation button:disabled').count()===2);
  }

  for(const width of [390,360]){
   const mc=await browser.newContext({viewport:{width,height:844},deviceScaleFactor:2,isMobile:true,hasTouch:true});const m=await mc.newPage();m.setDefaultTimeout(10000);m.on('pageerror',e=>report.runtimeErrors.push(e.message));
   m.setDefaultNavigationTimeout(45000);m.on('request',r=>{if(r.url().includes('/api/'))report.apiRequests.push(r.url());});
   await fresh(m);await m.locator('.gallery-stage').scrollIntoViewIfNeeded();const cdp=await mc.newCDPSession(m);let mb=await m.locator('.gallery-stage').boundingBox();const y=mb.y+mb.height*.5;
   // The same intentional 240 px swipe at both widths; longer gestures may legitimately skip two products.
   await swipe(m,cdp,width/2+120,y,width/2-120,y);
   check(`${width}px featured touch swipe changes product and avoids accidental poster open`,await selected(m)===featured[1].id&&!await m.locator('dialog').evaluate(d=>d.open),{selected:await selected(m)});
   const scrollBefore=await m.evaluate(()=>scrollY);await swipe(m,cdp,width/2,Math.min(y,650),width/2,Math.min(y,650)-140);
   check(`${width}px vertical touch scrolls while preserving featured selection`,await chosen(m)===featured[1].name&&await m.evaluate(()=>scrollY)>scrollBefore);
   check(`${width}px homepage has no horizontal overflow`,await m.evaluate(()=>document.documentElement.scrollWidth===innerWidth));
   await m.locator('.colour-poster').tap();await settle(m);check(`${width}px featured original poster modal fits viewport`,await m.locator('dialog').evaluate(d=>{const r=d.getBoundingClientRect();return r.width<=innerWidth&&r.height<=innerHeight;}));await m.keyboard.press('Escape');
   await m.locator('.browse-collection').tap();await settle(m);
   check(`${width}px library remains usable with all 38 posters`,await m.locator('.poster-grid article').count()===38&&await m.evaluate(()=>document.documentElement.scrollWidth===innerWidth));
   await home(m);await m.locator('.colour-play').tap();await m.waitForTimeout(4700);
   check(`${width}px touch autoplay starts after returning home`,await chosen(m)===featured[2].name);await m.locator('.colour-play').tap();
   if(out)await m.screenshot({path:path.join(out,`featured-mobile-${width}.png`),fullPage:true});await mc.close();
  }
  check('local preview has no authenticated API calls',report.apiRequests.length===0,report.apiRequests);
  check('featured and library flows have no JavaScript exceptions',report.runtimeErrors.length===0,report.runtimeErrors);
 }catch(error){report.checks.push({name:'browser execution',ok:false,error:error.stack});console.error(error);}
 finally{
  if(out)fs.writeFileSync(path.join(out,phase==='all'?'browser-featured-results.json':`browser-featured-${phase}-results.json`),JSON.stringify(report,null,2));
  await browser.close();
  if(report.checks.some(c=>!c.ok))process.exitCode=1;
 }
})();
