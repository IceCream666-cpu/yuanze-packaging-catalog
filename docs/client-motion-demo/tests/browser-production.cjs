// Exercise the real showroom-mode bundle with deterministic local session responses.
// This is a frontend integration check, not a claim about deployed authentication.
// No credentials or production network access are used. Requires Playwright + Chrome.
const {chromium}=require('playwright');
const assert=require('node:assert/strict');
const fs=require('node:fs');
const path=require('node:path');
const http=require('node:http');
const {createHash}=require('node:crypto');

const root=path.resolve(__dirname,'../../..');
const publicDir=path.resolve(process.env.QA_PUBLIC||path.join(root,'server-reference/public/showroom'));
const chrome=process.env.QA_CHROME||'/Applications/Google Chrome.app/Contents/MacOS/Google Chrome';
const output=process.env.QA_OUTPUT;
const manifest=JSON.parse(fs.readFileSync(path.join(publicDir,'bundle-manifest.json')));
const featured=JSON.parse(fs.readFileSync(path.join(__dirname,'../featured-manifest.json'))).files;
const report={version:'client1.2',mode:'showroom',scope:'local frontend integration with mocked session API',checks:[],runtimeErrors:[],unexpectedRequests:[]};
const csrf='local-browser-production-test-token';
const requests=[];
const logoutRequests=[];
let sessionMode='client',logoutStatus=200;
const sha=data=>createHash('sha256').update(data).digest('hex');
const record=(name,detail)=>{report.checks.push({name,ok:true,...(detail===undefined?{}:{detail})});console.log(`PASS ${name}`);};
const contentTypes={'.html':'text/html; charset=utf-8','.js':'text/javascript; charset=utf-8','.css':'text/css; charset=utf-8','.png':'image/png','.webp':'image/webp','.svg':'image/svg+xml'};
const csp="default-src 'self'; img-src 'self' data:; style-src 'self' 'unsafe-inline'; script-src 'self'; connect-src 'self'; frame-ancestors 'none'; base-uri 'self'; form-action 'self'; frame-src 'self'";

function send(res,status,body,type='application/json',headers={}) {
  res.writeHead(status,{'Content-Type':type,'Cache-Control':'no-store','Content-Security-Policy':csp,...headers});
  res.end(body);
}
const server=http.createServer((req,res)=>{
  const url=new URL(req.url,'http://localhost'),pathname=url.pathname;
  requests.push({pathname,method:req.method});
  if(pathname==='/api/session') {
    if(sessionMode==='expired') return send(res,401,'{"error":"expired fixture"}');
    if(sessionMode==='unavailable') return send(res,503,'{"error":"unavailable fixture"}');
    return send(res,200,JSON.stringify({role:sessionMode,csrf,username:'local-fixture'}));
  }
  if(pathname==='/api/logout') {
    let body=''; req.on('data',chunk=>body+=chunk);req.on('end',()=>{
      const valid=req.method==='POST'&&req.headers['x-csrf-token']===csrf&&body==='{}';
      logoutRequests.push({valid,method:req.method,status:logoutStatus});
      if(!valid) return send(res,403,'{"error":"fixture CSRF mismatch"}');
      send(res,logoutStatus,logoutStatus===200?'{}':'{"error":"fixture logout failure"}');
    });return;
  }
  if(pathname==='/login') return send(res,200,'<!doctype html><title>Local login fixture</title><h1>Local login fixture</h1>','text/html');
  if(pathname==='/favicon.ico') return send(res,204,'','image/x-icon');
  const relative=pathname==='/client'?'index.html':pathname.startsWith('/showroom/')?pathname.slice('/showroom/'.length):null;
  const allowed=relative&&(['index.html','preview.js','preview.css','company-content.js','product-posters.js'].includes(relative)||/^assets\/[A-Za-z0-9_./-]+\.(png|jpg|jpeg|webp|svg|pdf)$/.test(relative));
  if(!allowed||relative.split('/').includes('..')||!manifest.files[relative]) {
    report.unexpectedRequests.push(pathname);return send(res,404,'{"error":"not in production manifest"}');
  }
  const data=fs.readFileSync(path.join(publicDir,relative));
  if(sha(data)!==manifest.files[relative].sha256) return send(res,500,'{"error":"manifest checksum mismatch"}');
  const extra=url.searchParams.has('download')?{'Content-Disposition':`attachment; filename="${url.searchParams.get('download')}"`}:{};
  send(res,200,data,contentTypes[path.extname(relative)]||'application/octet-stream',extra);
});

async function openHome(page,origin) {
  await page.goto(origin+'/client',{waitUntil:'domcontentloaded'});
  await page.getByRole('heading',{name:'Care in colour.',exact:true}).waitFor();
  // A deliberate 503 may remain a retryable network request in Chrome; the
  // rendered recovery state is the completion condition for that failure case.
  if(sessionMode==='unavailable') await page.getByRole('alert').waitFor();
  else await page.waitForLoadState('networkidle');
}
async function waitEnabled(locator) {await locator.waitFor();await locator.evaluate(el=>new Promise((resolve,reject)=>{let attempts=0;const tick=()=>{if(!el.disabled)return resolve();if(++attempts>100)return reject(new Error('Button remained disabled'));setTimeout(tick,30);};tick();}));}

(async()=>{
  let browser;
  try {
    assert.equal(manifest.version,'client1.2');
    for(const name of ['index.html','preview.js','preview.css']) {
      assert.equal(fs.readFileSync(path.join(publicDir,name),'utf8'),fs.readFileSync(path.join(__dirname,'../release',name),'utf8'),`Published ${name} must equal the reviewed release`);
    }
    for(const item of featured) {
      assert.equal(item.productionTarget,`assets/featured/${item.posterId}.png`);
      assert.equal(manifest.files[item.productionTarget].sha256,item.sha256);
      assert.equal(sha(fs.readFileSync(path.join(publicDir,item.productionTarget))),item.sha256);
    }
    record('production entrypoints and all eight cutouts match the reviewed manifest');
    await new Promise(resolve=>server.listen(0,'127.0.0.1',resolve));
    const origin=`http://127.0.0.1:${server.address().port}`;
    browser=await chromium.launch({headless:true,executablePath:chrome});
    const context=await browser.newContext({viewport:{width:1440,height:900},reducedMotion:'reduce',acceptDownloads:true});
    await context.route('**/*',route=>new URL(route.request().url()).origin===origin?route.continue():(report.unexpectedRequests.push(route.request().url()),route.abort()));
    context.on('page',p=>p.on('pageerror',error=>report.runtimeErrors.push(error.message)));
    const page=await context.newPage();
    await openHome(page,origin);
    await waitEnabled(page.getByRole('button',{name:'退出登录',exact:true}));
    assert.match(await page.title(),/client1\.2/);assert.doesNotMatch(await page.title(),/预览/);
    assert.ok(requests.some(r=>r.pathname==='/api/session'));
    record('showroom-mode homepage verifies session and exposes enabled logout');

    const swatches=page.locator('.colour-swatches button');
    assert.equal(await swatches.count(),8);
    for(let i=0;i<8;i++) {
      await swatches.nth(i).click();
      await page.waitForFunction(id=>document.querySelector('.poster-plane.center')?.dataset.posterId===id,featured[i].posterId);
      await page.locator('.poster-plane.center img').waitFor();
      await page.waitForFunction(()=>{const image=document.querySelector('.poster-plane.center img');return image&&image.complete&&image.naturalWidth>0;});
      const src=new URL(await page.locator('.poster-plane.center img').getAttribute('src'),origin);
      assert.equal(src.pathname,`/showroom/${featured[i].productionTarget}`);
      assert.equal(await swatches.nth(i).getAttribute('aria-pressed'),'true');
    }
    record('all eight products render from protected assets/featured production paths');

    await page.getByRole('button',{name:'关于客户端',exact:true}).click();
    const info=await page.locator('dialog[open]').innerText();
    assert.match(info,/client1\.2/);assert.match(info,/38/);assert.doesNotMatch(info,/设计预览|尚未替换线上|design preview/i);
    await page.getByRole('button',{name:'关闭',exact:true}).click();
    await page.locator('.colour-language').click();
    await page.getByRole('button',{name:'About the client',exact:true}).click();
    assert.doesNotMatch(await page.locator('dialog[open]').innerText(),/design preview|has not replaced/i);
    await page.getByRole('button',{name:'Close',exact:true}).click();
    await page.locator('.colour-language').click();
    record('Chinese and English production information omit local-preview status');

    await swatches.first().click();
    await page.locator('.colour-poster').click();
    await page.getByRole('button',{name:'查看高清原图',exact:true}).click();
    await page.getByRole('button',{name:'已加载原图',exact:true}).waitFor();
    const downloadLink=page.getByRole('link',{name:'下载原图',exact:true});
    const href=new URL(await downloadLink.getAttribute('href'),origin);
    assert.equal(href.pathname,'/showroom/assets/posters/poster-012.webp');
    assert.equal(href.searchParams.get('download'),'poster-012.webp');
    const downloadPromise=page.waitForEvent('download');await downloadLink.click();
    const download=await downloadPromise;assert.equal(download.suggestedFilename(),'poster-012.webp');
    assert.equal(sha(fs.readFileSync(await download.path())),manifest.files['assets/posters/poster-012.webp'].sha256);
    await page.getByRole('button',{name:'关闭',exact:true}).click();
    record('HD image and download use the original protected poster and preserve its bytes');

    await page.locator('.browse-collection').click();
    await waitEnabled(page.getByRole('button',{name:'退出登录',exact:true}));
    assert.equal(await page.locator('.poster-grid article').count(),38);
    await page.waitForLoadState('networkidle');
    assert.doesNotMatch(await page.locator('footer').innerText(),/设计预览|Design preview/);
    record('full library retains 38 posters and production logout');

    sessionMode='unavailable';await openHome(page,origin);
    await page.getByRole('alert').waitFor();
    assert.equal(await page.getByRole('button',{name:'退出登录',exact:true}).isDisabled(),true);
    await page.locator('.browse-collection').click();assert.equal(await page.getByRole('alert').isVisible(),true);
    await page.getByRole('button',{name:'返回精选首页',exact:true}).click();assert.equal(await page.getByRole('alert').isVisible(),true);
    sessionMode='client';await page.getByRole('button',{name:'重新加载',exact:true}).click();
    await page.waitForLoadState('networkidle');await waitEnabled(page.getByRole('button',{name:'退出登录',exact:true}));
    assert.equal(await page.getByRole('alert').count(),0);
    record('session failure appears on homepage and library; reload recovers enabled controls');

    sessionMode='employee';await openHome(page,origin);await page.getByRole('alert').waitFor();
    assert.equal(await page.getByRole('button',{name:'退出登录',exact:true}).isDisabled(),true);
    sessionMode='admin';await page.evaluate(()=>window.dispatchEvent(new Event('focus')));
    await waitEnabled(page.getByRole('button',{name:'退出登录',exact:true}));
    assert.equal(await page.getByRole('alert').count(),0);
    record('unsupported session role is rejected and focus recheck accepts the administrator');

    logoutStatus=503;await page.getByRole('button',{name:'退出登录',exact:true}).click();
    await page.getByText('退出未完成，请重试。',{exact:true}).waitFor();
    await waitEnabled(page.getByRole('button',{name:'退出登录',exact:true}));
    assert.equal(new URL(page.url()).pathname,'/client');
    logoutStatus=200;await page.getByRole('button',{name:'退出登录',exact:true}).click();await page.waitForURL(origin+'/login');
    assert.equal(logoutRequests.length,2);assert.ok(logoutRequests.every(r=>r.valid));
    record('failed logout remains retryable; success posts the session CSRF token and returns to login');

    sessionMode='expired';await page.goto(origin+'/client');await page.waitForURL(origin+'/login');
    record('expired session redirects to the existing login route');

    sessionMode='client';await page.setViewportSize({width:390,height:844});await openHome(page,origin);
    const mobileLogout=page.getByRole('button',{name:'退出登录',exact:true});await waitEnabled(mobileLogout);
    await mobileLogout.scrollIntoViewIfNeeded();assert.equal(await mobileLogout.isVisible(),true);
    assert.ok(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1));
    await mobileLogout.click();await page.waitForURL(origin+'/login');
    assert.equal(logoutRequests.length,3);assert.ok(logoutRequests.every(r=>r.valid));
    record('390px production homepage fits the viewport and exposes working logout');

    await page.setViewportSize({width:1440,height:900});await openHome(page,origin);
    await page.locator('.browse-collection').click();
    await waitEnabled(page.getByRole('button',{name:'退出登录',exact:true}));
    await page.getByRole('button',{name:'退出登录',exact:true}).click();await page.waitForURL(origin+'/login');
    assert.equal(logoutRequests.length,4);assert.ok(logoutRequests.every(r=>r.valid));
    record('library logout also posts the protected session token and returns to login');

    assert.deepEqual(report.unexpectedRequests,[]);assert.deepEqual(report.runtimeErrors,[]);
    const fetched=new Set(requests.map(r=>r.pathname));
    for(const entry of featured)assert.ok(fetched.has('/showroom/'+entry.productionTarget));
    record('no runtime errors, external requests or unsupported resource paths');
    report.passed=true;
  } catch(error) {
    report.passed=false;report.error=error.stack;report.lastRequests=requests.slice(-20);console.error(error);process.exitCode=1;
    const failedPage=browser?.contexts()[0]?.pages()[0];
    if(failedPage){report.lastURL=failedPage.url();report.lastText=await failedPage.locator('body').innerText({timeout:2000}).catch(()=>'(unavailable)');}
  } finally {
    if(browser)await browser.close();
    await new Promise(resolve=>server.close(resolve));
    if(output){fs.mkdirSync(path.dirname(output),{recursive:true});fs.writeFileSync(output,JSON.stringify(report,null,2)+'\n');}
    console.log(JSON.stringify({passed:report.passed,checks:report.checks.length,scope:report.scope}));
  }
})();
