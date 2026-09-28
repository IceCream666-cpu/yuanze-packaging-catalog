import assert from 'node:assert/strict';
import fs from 'node:fs/promises';
import http from 'node:http';
const source=await fs.readFile(new URL('../../server-reference/public/api-client.js',import.meta.url),'utf8');
const {requestJSON}=await import('data:text/javascript;base64,'+Buffer.from(source).toString('base64'));
const counts=new Map(), observed=[];
const server=http.createServer((req,res)=>{
  const path=req.url,count=(counts.get(path)||0)+1;counts.set(path,count);observed.push({path,method:req.method,at:Date.now()});
  const send=(status,body,headers={})=>{res.writeHead(status,{'Content-Type':'application/json',...headers});res.end(typeof body==='string'?body:JSON.stringify(body));};
  if(path==='/flaky'&&count<3)return send(502,'<html>proxy failure</html>',{'Content-Type':'text/html'});
  if(path==='/limited'&&count===1)return send(429,'<html>busy</html>',{'Retry-After':'1','Content-Type':'text/html'});
  if(path==='/long-limit')return send(429,{error:'请等待后重试'},{'Retry-After':'30'});
  if(path==='/login-limit')return send(429,{error:'登录尝试过于频繁',code:'LOGIN_RATE_LIMITED'},{'Retry-After':'42','X-Request-ID':'test-login-limit-01'});
  if(path==='/storage-failure')return send(503,{error:'登录服务暂时繁忙，请稍后重试',code:'AUTH_STORAGE_UNAVAILABLE'},{'Retry-After':'2','X-Request-ID':'test-auth-storage-01'});
  if(path==='/denied')return send(403,{error:'没有权限'});
  if(path==='/expired')return send(401,{error:'请先登录'});
  if(path==='/invalid')return send(200,'<html>login page</html>',{'Content-Type':'text/html'});
  if(path==='/redirect'){res.writeHead(302,{Location:'/invalid'});return res.end();}
  if(path==='/offline-once'&&count===1)return req.socket.destroy();
  if(path==='/slow'||path==='/slow-post'){const timer=setTimeout(()=>send(200,{ok:true}),1000);res.on('close',()=>clearTimeout(timer));return;}
  if(path==='/save-failure')return send(503,'<html>unavailable</html>',{'Content-Type':'text/html'});
  if(path==='/bad-password')return send(401,{error:'账号或密码不正确',code:'INVALID_CREDENTIALS'});
  if(path==='/always-busy')return send(503,{error:'服务繁忙'});
  send(200,{ok:true});
});
await new Promise(resolve=>server.listen(0,'127.0.0.1',resolve));
const base=`http://127.0.0.1:${server.address().port}`;
const checks=[];
try{
  assert.equal((await requestJSON(base+'/flaky')).ok,true);assert.equal(counts.get('/flaky'),3);checks.push('HTML 502 retries twice then recovers');
  assert.equal((await requestJSON(base+'/limited')).ok,true);assert.equal(counts.get('/limited'),2);const times=observed.filter(x=>x.path==='/limited');assert.ok(times[1].at-times[0].at>=950);checks.push('HTML 429 retains status and respects Retry-After');
  await assert.rejects(requestJSON(base+'/long-limit'),e=>e.status===429&&e.retryAfter===30000);assert.equal(counts.get('/long-limit'),1);checks.push('Long Retry-After stops automatic retries');
  await assert.rejects(requestJSON(base+'/login-limit',{method:'POST',body:'{}'}),e=>e.code==='LOGIN_RATE_LIMITED'&&e.requestId==='test-login-limit-01'&&e.retryAfter===42000&&/等待 42 秒/.test(e.message));assert.equal(counts.get('/login-limit'),1);checks.push('Login rate limit exposes wait seconds and request reference without retrying POST');
  await assert.rejects(requestJSON(base+'/storage-failure',{method:'POST',body:'{}'}),e=>e.code==='AUTH_STORAGE_UNAVAILABLE'&&e.requestId==='test-auth-storage-01'&&/参考编号：test-auth-storage-01/.test(e.message));assert.equal(counts.get('/storage-failure'),1);checks.push('Service error preserves backend code and X-Request-ID for diagnostics');
  for(const [path,status] of [['/denied',403],['/expired',401]]){await assert.rejects(requestJSON(base+path),e=>e.status===status);assert.equal(counts.get(path),1);}checks.push('401 and 403 are not retried or relabelled network');
  await assert.rejects(requestJSON(base+'/invalid'),e=>e.code==='invalid_response');assert.equal(counts.get('/invalid'),1);checks.push('Successful HTML response is not accepted as data');
  await assert.rejects(requestJSON(base+'/redirect'),e=>e.code==='unexpected_redirect');assert.equal(counts.get('/redirect'),1);checks.push('API redirect is diagnosed instead of login loop');
  assert.equal((await requestJSON(base+'/offline-once')).ok,true);assert.equal(counts.get('/offline-once'),2);checks.push('Temporary read connection failure recovers');
  await assert.rejects(requestJSON(base+'/slow',{timeoutMs:25}),e=>e.code==='timeout');assert.equal(counts.get('/slow'),3);checks.push('Read timeout aborts and has at most two retries');
  await assert.rejects(requestJSON(base+'/slow-post',{method:'POST',body:'{}',timeoutMs:25}),e=>e.code==='timeout'&&/结果尚未确认/.test(e.message));assert.equal(counts.get('/slow-post'),1);checks.push('Timed-out mutation is never replayed and outcome is marked unknown');
  await assert.rejects(requestJSON(base+'/save-failure',{method:'POST',body:'{}'}),e=>e.status===503);assert.equal(counts.get('/save-failure'),1);checks.push('Gateway mutation failure is never replayed');
  await assert.rejects(requestJSON(base+'/bad-password',{method:'POST',body:'{}'}),e=>e.status===401&&e.message==='账号或密码不正确');assert.equal(counts.get('/bad-password'),1);checks.push('Credential rejection remains specific');
  await assert.rejects(requestJSON(base+'/always-busy'),e=>e.status===503);assert.equal(counts.get('/always-busy'),3);checks.push('Unavailable GET never retries indefinitely');
  const controller=new AbortController();const p=requestJSON(base+'/always-busy',{signal:controller.signal});setTimeout(()=>controller.abort(),50);await assert.rejects(p,e=>e.name==='AbortError');assert.equal(counts.get('/always-busy'),4);checks.push('User cancellation also interrupts retry delay');
  console.log(JSON.stringify({passed:true,checks},null,2));
}finally{server.closeAllConnections();await new Promise(resolve=>server.close(resolve));}
