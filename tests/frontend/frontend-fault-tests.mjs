import assert from 'node:assert/strict';
import fs from 'node:fs';
import http from 'node:http';
import vm from 'node:vm';
import {fileURLToPath} from 'node:url';
import {createRequire} from 'node:module';
import {evaluateLogin} from './login-module-harness.mjs';
const require=createRequire(import.meta.url);
const {JSDOM,VirtualConsole}=require('jsdom');
const {evaluateBrowserModule}=require('./module-loader.cjs');
const root=fileURLToPath(new URL('../../server-reference/public/',import.meta.url)),checks=[];
const fixture={records:[{id:'fixture-existing',productCode:'YZ-BC-000001',name:'精华液瓶',kind:'package',materials:['PET'],images:[]},{id:'fixture-new',productCode:'YZ-BC-000002',name:'洗手液瓶',kind:'package',materials:['PET'],images:[]}],settings:{}};
let mode='normal',counts=new Map(),posts=[];
const server=http.createServer(async(req,res)=>{
  const key=req.method+' '+req.url;counts.set(key,(counts.get(key)||0)+1);
  let content='';for await(const chunk of req)content+=chunk;if(content)posts.push({path:req.url,body:JSON.parse(content)});
  const send=(status,body,headers={})=>{res.writeHead(status,{'Content-Type':'application/json',...headers});res.end(typeof body==='string'?body:JSON.stringify(body));};
  if(req.url==='/api/login'){
    if(mode==='login-limit')return send(429,{error:'登录尝试过于频繁',code:'LOGIN_RATE_LIMITED'},{'Retry-After':'37','X-Request-ID':'login-limit-fixture'});
    if(mode==='login-storage')return send(503,{error:'登录服务暂时繁忙',code:'AUTH_STORAGE_UNAVAILABLE'},{'Retry-After':'2','X-Request-ID':'login-storage-fixture'});
    if(mode==='login-gateway')return send(502,'<html>proxy</html>',{'Content-Type':'text/html'});
    if(mode==='login-timeout')return;
    return send(200,{ok:true,role:'employee'},{'Set-Cookie':'fixture_session=ok; Path=/; HttpOnly'});
  }
  if(req.url==='/api/session'){
    if(mode.startsWith('cookie-')&&!req.headers.cookie?.includes('fixture_session=ok'))return send(401,{error:'请先登录'});
    if(mode==='session-fails')return send(500,{error:'读取会话暂时失败'});
    return send(200,{role:mode.startsWith('admin')?'admin':'employee',username:'fixture_employee',csrf:'fixture-csrf'});
  }
  if(req.url==='/api/catalog')return mode==='catalog-fails'?send(500,{error:'目录暂时不可用'}):send(200,fixture);
  if(req.url==='/api/preferences'){
    if(mode==='preferences-fails')return send(500,{error:'收藏暂时不可用'});
    if(req.method==='POST')return send(200,{ok:true});
    return send(200,{favorites:['fixture-existing']});
  }
  if(req.url==='/api/plans'||req.url==='/api/samples')return send(500,{error:'Unused auxiliary service unavailable'});
  if(req.url==='/api/image-search/status')return send(200,{available:false});
  if(req.url==='/api/admin/records'){
    if(req.method==='POST')return send(503,'<html>unknown save result</html>',{'Content-Type':'text/html'});
    return send(200,{items:fixture.records.map(r=>({...r,version:1}))});
  }
  if(req.url==='/api/admin/taxonomy')return send(200,{value:{},version:0});
  if(req.url==='/api/admin/search-status')return send(200,{available:false});
  send(404,{error:'not found'});
});
await new Promise(resolve=>server.listen(0,'127.0.0.1',resolve));
const base=`http://127.0.0.1:${server.address().port}`;
function reset(next){mode=next;counts=new Map();posts=[];}
function makeDOM(html){const errors=[],vc=new VirtualConsole();vc.on('jsdomError',e=>errors.push(e.message));const dom=new JSDOM(fs.readFileSync(root+html,'utf8'),{url:'https://catalog.test/',runScripts:'outside-only',pretendToBeVisual:true,virtualConsole:vc});const w=dom.window;w.AbortController=AbortController;w.DOMException=DOMException;w.TypeError=TypeError;w.matchMedia=()=>({matches:true,addEventListener(){}});w.scrollTo=()=>{};w.HTMLElement.prototype.scrollIntoView=function(){};w.HTMLDialogElement.prototype.showModal=function(){this.open=true};w.HTMLDialogElement.prototype.close=function(){this.open=false};w.confirm=()=>true;return {dom,w,d:w.document,errors};}
function connect(cookie=false){let jar='';return async(url,options={})=>{const response=await fetch(base+url,{...options,headers:{...options.headers,...(jar?{Cookie:jar}:{})}});if(cookie&&response.headers.get('set-cookie'))jar=response.headers.get('set-cookie').split(';')[0];return response;};}
async function until(condition,label,ms=4000){const deadline=Date.now()+ms;while(!condition()){if(Date.now()>deadline)throw Error('Timeout: '+label);await new Promise(resolve=>setTimeout(resolve,5));}}
async function login({cookie=true,timer=false}={}){const p=makeDOM('login.html'),nav=[];const context=vm.createContext({document:p.d,location:{search:'',set href(url){nav.push(url);}},URLSearchParams,TypeError,SyntaxError,FormData:p.w.FormData,fetch:connect(cookie)});await evaluateLogin(context);if(timer)context.setTimeout=(fn,ms)=>setTimeout(fn,ms===30000?30:ms);const form=p.d.querySelector('#loginForm');form.elements.username.value='fixture_employee';form.elements.password.value='Fake-Only-Password';form.dispatchEvent(new p.w.Event('submit',{bubbles:true,cancelable:true}));await until(()=>!form.querySelector('[type=submit]').disabled,'login settled');return {...p,nav,form,error:p.d.querySelector('#error').textContent};}
try{
  reset('cookie-good');let p=await login();assert.deepEqual(p.nav,['/']);assert.equal(counts.get('POST /api/login'),1);assert.equal(counts.get('GET /api/session'),1);p.dom.window.close();checks.push('Login verifies an HTTP cookie session before navigation');
  reset('cookie-rejected');p=await login({cookie:false});assert.equal(p.nav.length,0);assert.match(p.error,/Cookie/);assert.doesNotMatch(p.error,/账号或密码不正确/);assert.equal(counts.get('POST /api/login'),1);p.dom.window.close();checks.push('Rejected cookie stays on form and is not called a wrong password');
  reset('login-limit');p=await login();assert.match(p.error,/等待 37 秒/);assert.match(p.error,/参考编号：login-limit-fixture/);assert.equal(counts.get('POST /api/login'),1);assert.equal(p.nav.length,0);p.dom.window.close();checks.push('Login displays rate-limit waiting seconds and request reference without replay');
  reset('login-storage');p=await login();assert.match(p.error,/参考编号：login-storage-fixture/);assert.doesNotMatch(p.error,/账号或密码不正确/);assert.equal(counts.get('POST /api/login'),1);p.dom.window.close();checks.push('Login service failure displays support reference and preserves error meaning');
  reset('login-gateway');p=await login();assert.equal(p.nav.length,0);assert.match(p.error,/服务暂时不可用/);assert.equal(counts.get('POST /api/login'),1);assert.equal(counts.get('GET /api/session'),undefined);p.dom.window.close();checks.push('HTML gateway login failure is actionable and POST is never replayed');
  reset('login-timeout');p=await login({timer:true});assert.equal(p.nav.length,0);assert.match(p.error,/登录响应超时/);assert.equal(counts.get('POST /api/login'),1);assert.equal(p.form.elements.password.value,'Fake-Only-Password');assert.equal(p.form.hasAttribute('aria-busy'),false);p.dom.window.close();checks.push('Login timeout restores form and preserves input for deliberate retry');
  reset('preferences-fails');p=makeDOM('index.html');p.w.fetch=connect();await evaluateBrowserModule(p.dom,root+'app.js');await until(()=>p.d.querySelector('#searchForm'),'catalog rendered').catch(e=>{console.log(p.d.querySelector('#main').textContent,p.errors);throw e;});await until(()=>p.d.querySelector('[data-action=retry-preferences]'),'preference failure rendered');assert.equal(p.d.querySelectorAll('.card').length,2);assert.equal(counts.get('GET /api/plans'),undefined);assert.equal(counts.get('GET /api/samples'),undefined);p.d.querySelector('[data-favorite="fixture-new"]').click();await new Promise(r=>setTimeout(r,60));assert.equal(counts.get('POST /api/preferences'),undefined);checks.push('Optional service failure does not block catalogue or overwrite unloaded favorites');
  mode='normal';p.d.querySelector('[data-action=retry-preferences]').click();await until(()=>p.d.querySelector('#favCount').textContent==='1','preferences recovered');p.d.querySelector('[data-favorite="fixture-new"]').click();await until(()=>posts.some(x=>x.path==='/api/preferences'),'favorite save');assert.deepEqual(posts.find(x=>x.path==='/api/preferences').body.favorites,['fixture-existing','fixture-new']);assert.equal(p.d.querySelectorAll('.card').length,2);assert.deepEqual(p.errors,[]);p.dom.window.close();checks.push('Optional retry keeps catalogue visible and preserves existing favorites when adding');
  reset('catalog-fails');p=makeDOM('index.html');p.w.fetch=connect();await evaluateBrowserModule(p.dom,root+'app.js');await until(()=>p.d.querySelector('[data-action=retry-catalog]'),'catalog retry available');assert.match(p.d.querySelector('#main').textContent,/目录暂时不可用/);mode='normal';const retry=p.d.querySelector('[data-action=retry-catalog]');retry.click();retry.click();await until(()=>p.d.querySelector('#searchForm'),'catalog retry succeeded');assert.equal(counts.get('GET /api/catalog'),2);assert.equal(counts.get('POST /api/login'),undefined);p.dom.window.close();checks.push('Core load error has bounded manual retry without another login or duplicate concurrent fetch');
  reset('admin');p=makeDOM('admin.html');p.w.fetch=connect();await evaluateBrowserModule(p.dom,root+'admin.js');await until(()=>p.d.querySelector('[data-edit-record]'),'admin records');p.d.querySelector('[data-edit-record]').click();await until(()=>p.d.querySelector('#recordForm'),'admin editor');const form=p.d.querySelector('#recordForm');form.elements.name.value='Unsaved fixture edit';form.elements.name.dispatchEvent(new p.w.Event('input',{bubbles:true}));form.dispatchEvent(new p.w.Event('submit',{bubbles:true,cancelable:true}));await until(()=>p.d.querySelector('#recordForm [data-form-status]').classList.contains('error'),'save error');assert.equal(counts.get('POST /api/admin/records'),1);assert.equal(form.elements.name.value,'Unsaved fixture edit');assert.equal(p.d.querySelector('#adminDialog').open,true);assert.match(p.d.querySelector('#recordForm [data-form-status]').textContent,/服务暂时不可用/);p.dom.window.close();checks.push('Admin HTML gateway write error is never retried and keeps editor draft');
  console.log(JSON.stringify({passed:true,checks,liveWebsiteRequests:0},null,2));
}finally{server.closeAllConnections();await new Promise(resolve=>server.close(resolve));}
