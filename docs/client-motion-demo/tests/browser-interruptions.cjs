// Run separately from the pure Node tests against an already-running local preview.
// Requires the existing Playwright installation and a local Chrome executable.
const {chromium}=require('playwright');
const assert=require('node:assert/strict');
const fs=require('node:fs');
const path=require('node:path');
const URL=process.env.QA_URL||'http://127.0.0.1:8784/';
const CHROME=process.env.QA_CHROME||'/Applications/Google Chrome.app/Contents/MacOS/Google Chrome';
const posters=JSON.parse(fs.readFileSync(path.join(__dirname,'../src/posters.json')));
const report={url:URL,checks:[],runtimeErrors:[]};

function result(name,detail){report.checks.push({name,ok:true,detail});console.log(`PASS ${name}`);}
async function snapshot(page){
 return page.evaluate(()=>{
  const stage=document.querySelector('.gallery-stage'),center=stage?.querySelector('.poster-plane.center');
  const a=stage?.getBoundingClientRect(),b=center?.getBoundingClientRect();
  return {id:center?.dataset.posterId,selectedTitle:document.querySelector('.filmstrip [aria-pressed="true"]')?.getAttribute('aria-label'),transform:center?.style.transform,centerError:a&&b?Math.abs((b.left+b.width/2)-(a.left+a.width/2)):null};
 });
}

(async()=>{
 const browser=await chromium.launch({headless:true,executablePath:CHROME});
 try{
  const page=await browser.newPage({viewport:{width:1440,height:1000}});
  page.on('pageerror',error=>report.runtimeErrors.push(error.message));
  await page.goto(URL,{waitUntil:'networkidle'});await page.waitForTimeout(500);
  await page.getByRole('button',{name:'下一张海报',exact:true}).click();await page.waitForTimeout(60);
  const box=await page.locator('.gallery-stage').boundingBox();
  await page.mouse.click(box.x+box.width/2,box.y+box.height-8);await page.waitForTimeout(850);
  let state=await snapshot(page);
  assert.equal(state.id,posters[1].id);assert.ok(state.centerError<1,JSON.stringify(state));
  assert.equal(state.selectedTitle,posters[1].title.zh);
  result('blank stage tap during animation still reaches its centered target',state);

  await page.reload({waitUntil:'networkidle'});await page.waitForTimeout(500);
  await page.locator('.filmstrip button').nth(4).click();await page.waitForTimeout(30);
  await page.emulateMedia({reducedMotion:'reduce'});await page.waitForTimeout(850);
  state=await snapshot(page);
  assert.equal(state.id,posters[4].id);assert.equal(state.selectedTitle,posters[4].title.zh);
  assert.ok(state.centerError<1,JSON.stringify(state));
  assert.equal(await page.evaluate(()=>document.getAnimations().filter(a=>a.playState==='running').length),0);
  result('reduced motion during travel aligns poster, selection and title',state);

  await page.emulateMedia({reducedMotion:'no-preference'});await page.reload({waitUntil:'networkidle'});await page.waitForTimeout(500);
  await page.getByRole('button',{name:'下一张海报',exact:true}).click();await page.waitForTimeout(50);
  const drag=await page.locator('.gallery-stage').boundingBox();
  await page.mouse.move(drag.x+drag.width*.65,drag.y+drag.height*.5);await page.mouse.down();await page.waitForTimeout(70);
  await page.mouse.move(drag.x+drag.width*.65-310,drag.y+drag.height*.5,{steps:20});await page.waitForTimeout(130);await page.mouse.up();await page.waitForTimeout(850);
  state=await snapshot(page);
  assert.ok(state.centerError<1,JSON.stringify(state));assert.equal(state.selectedTitle,posters.find(p=>p.id===state.id).title.zh);
  assert.equal(await page.locator('dialog').evaluate(d=>d.open),false);
  result('drag can take over a running animation and finish centered',state);

  await page.reload({waitUntil:'networkidle'});await page.waitForTimeout(500);
  async function rapidKeys(key,expectedIndex,name){
   await page.locator('.gallery-stage').focus();
   for(let i=0;i<5;i++){await page.keyboard.press(key);await page.waitForTimeout(30);}
   await page.waitForTimeout(900);
   const actual=await snapshot(page);
   assert.equal(actual.id,posters[expectedIndex].id,JSON.stringify(actual));
   assert.equal(actual.selectedTitle,posters[expectedIndex].title.zh);
   assert.ok(actual.centerError<1,JSON.stringify(actual));
   result(name,actual);
  }
  await rapidKeys('ArrowRight',5,'five rapid right arrows advance five posters');
  await rapidKeys('ArrowLeft',0,'five rapid left arrows return five posters');
  await rapidKeys('ArrowLeft',posters.length-5,'five rapid left arrows wrap across the first poster');
  await rapidKeys('ArrowRight',0,'five rapid right arrows wrap across the final poster');

  await page.locator('.search-box input').fill('Body scrub ·');await page.waitForTimeout(750);
  const pair=posters.filter(p=>p.title.en.includes('Body scrub ·'));
  assert.equal(pair.length,2);
  async function pairState(expected,name){
   const planes=await page.locator('.poster-plane').evaluateAll(es=>es.map(e=>({id:e.dataset.posterId,center:e.classList.contains('center'),opacity:Number(getComputedStyle(e).opacity),hidden:e.getAttribute('aria-hidden'),pointerEvents:getComputedStyle(e).pointerEvents})));
   assert.equal(planes.length,2);assert.equal(new Set(planes.map(x=>x.id)).size,2);
   const center=planes.find(x=>x.center),side=planes.find(x=>!x.center);
   assert.equal(center.id,pair[expected].id);assert.equal(center.opacity,1);
   assert.equal(side.opacity,0);assert.equal(side.hidden,'true');assert.equal(side.pointerEvents,'none');
   result(name,planes);
  }
  await pairState(0,'two-result filter keeps one visible center and one inaccessible hidden side');
  await page.getByRole('button',{name:'下一张海报',exact:true}).click();await page.waitForTimeout(750);
  await pairState(1,'two-result next transition ends without a visible seam duplicate');
  await page.getByRole('button',{name:'下一张海报',exact:true}).click();await page.waitForTimeout(750);
  await pairState(0,'two-result wrap transition keeps unique identities and a hidden seam');

  assert.deepEqual(report.runtimeErrors,[]);result('no runtime exceptions',[]);
 }catch(error){report.checks.push({name:'interruption regression',ok:false,error:error.stack});throw error;}
 finally{
  if(process.env.QA_OUTPUT){fs.mkdirSync(process.env.QA_OUTPUT,{recursive:true});fs.writeFileSync(path.join(process.env.QA_OUTPUT,'browser-interruptions-results.json'),JSON.stringify(report,null,2));}
  await browser.close();
 }
})().catch(error=>{console.error(error);process.exitCode=1;});
