import {test} from 'node:test';
import assert from 'node:assert/strict';
import {loadSession, logoutSession} from '../src/session.js';

test('session errors and unauthorized roles cannot appear as authenticated', async()=>{
 for(const status of [401,403,500]) {
  await assert.rejects(loadSession(async()=>({ok:false,status})), error=>error.status===status);
 }
 await assert.rejects(loadSession(async()=>({ok:true,json:async()=>({role:'employee',csrf:'token'})})));
 await assert.rejects(loadSession(async()=>({ok:true,json:async()=>({role:'client'})})));
});

test('logout uses the existing CSRF-protected session and reports rejection', async()=>{
 const requests=[];
 const fetcher=async(url,options)=>{
  requests.push({url,options});
  return {ok:true,json:async()=>({role:'client',csrf:'test-csrf'})};
 };
 await logoutSession(null,fetcher);
 assert.deepEqual(requests.map(r=>r.url),['/api/session','/api/logout']);
 assert.equal(requests[1].options.headers['X-CSRF-Token'],'test-csrf');
 assert.equal(requests[1].options.credentials,'same-origin');
 assert.equal(requests[1].options.method,'POST');
 await assert.rejects(logoutSession({csrf:'token'},async()=>({ok:false,status:500})));
});
