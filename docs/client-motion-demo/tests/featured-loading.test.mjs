import test from 'node:test';
import assert from 'node:assert/strict';
import {createFeaturedLoadQueue} from '../src/featured-loading.js';

const ids=['a','b','c','d','e','f','g','h'];
const loading=queue=>Object.entries(queue.snapshot()).filter(([,value])=>value.status==='loading').map(([id])=>id);
const finish=(queue,id,status='loaded')=>queue.finish(id,queue.snapshot()[id].token,status);

test('the first center downloads alone, then decoding releases both network slots for neighbours',()=>{
 const queue=createFeaturedLoadQueue({ids});
 queue.select('a');assert.deepEqual(loading(queue),['a']);
 finish(queue,'a','downloaded');
 assert.equal(queue.snapshot().a.status,'decoding');
 assert.deepEqual(loading(queue),['b','h']);
 finish(queue,'b','downloaded');assert.deepEqual(loading(queue),['c','h']);
 assert.equal(queue.snapshot().a.enabled,true);
 finish(queue,'a');assert.equal(queue.snapshot().a.status,'loaded');
});

test('two stalled old neighbours cannot block a newly chosen center and cancelled callbacks are ignored',()=>{
 const queue=createFeaturedLoadQueue({ids});queue.select('a');finish(queue,'a');
 assert.deepEqual(loading(queue),['b','h']);
 const before=queue.snapshot();queue.select('e');
 assert.deepEqual(loading(queue),['e']);
 for(const id of ['b','h']){
  assert.equal(queue.snapshot()[id].enabled,false);
  assert.equal(queue.snapshot()[id].status,'idle');
  assert.ok(queue.snapshot()[id].token>before[id].token);
  queue.finish(id,before[id].token,'downloaded');queue.finish(id,before[id].token,'loaded');
  assert.equal(queue.snapshot()[id].status,'idle');
 }
 assert.equal(queue.snapshot().e.enabled,true);
 assert.equal(queue.snapshot().a.token,before.a.token);
 assert.equal(queue.snapshot().a.status,'loaded');
});

test('retrying the active image preempts a lower-priority neighbour immediately',()=>{
 const queue=createFeaturedLoadQueue({ids});queue.select('a');finish(queue,'a','error');
 assert.deepEqual(loading(queue),['b','h']);
 const oldToken=queue.snapshot().a.token;queue.retry('a');
 assert.deepEqual(loading(queue),['a','b']);
 assert.equal(queue.snapshot().h.enabled,false);
 assert.equal(queue.snapshot().a.token,oldToken+1);
 queue.finish('a',oldToken,'loaded');assert.equal(queue.snapshot().a.status,'loading');
 finish(queue,'a');assert.equal(queue.snapshot().a.status,'loaded');
});

test('fully downloaded and decoded images retain their source and token across rapid selections',()=>{
 const queue=createFeaturedLoadQueue({ids});queue.select('a');finish(queue,'a','downloaded');
 const a=queue.snapshot().a;queue.select('e');
 assert.equal(queue.snapshot().a.status,'decoding');assert.equal(queue.snapshot().a.enabled,true);
 finish(queue,'a');
 for(const id of ['b','g','d','e','a']){
  queue.select(id);assert.ok(loading(queue).length<=2);
  assert.equal(queue.snapshot().a.enabled,true);assert.equal(queue.snapshot().a.token,a.token);
 }
 assert.equal(queue.snapshot().a.status,'loaded');
 const prior=queue.snapshot();queue.dispose();queue.select('e');finish(queue,'b');
 assert.deepEqual(queue.snapshot(),prior);
});

test('a cancelled unfinished image can restart with a new token while stale results remain ineffective',()=>{
 const queue=createFeaturedLoadQueue({ids});queue.select('a');
 const oldToken=queue.snapshot().a.token;queue.select('e');queue.select('a');
 const newToken=queue.snapshot().a.token;
 assert.ok(newToken>oldToken);assert.equal(queue.snapshot().a.status,'loading');
 queue.finish('a',oldToken,'error');queue.finish('a',oldToken,'loaded');
 assert.equal(queue.snapshot().a.status,'loading');
 finish(queue,'a','downloaded');finish(queue,'a');
 assert.equal(queue.snapshot().a.status,'loaded');assert.equal(queue.snapshot().a.token,newToken);
});

test('a 23-product collection loads only the five visible neighbours and never exceeds its network bound',()=>{
 const expanded=Array.from({length:23},(_,i)=>`p${i}`);
 for(const concurrency of [2,3]){
  const queue=createFeaturedLoadQueue({ids:expanded,concurrency});queue.select('p0');
  assert.deepEqual(loading(queue),['p0']);
  while(loading(queue).length){
   assert.ok(loading(queue).length<=concurrency);
   const id=loading(queue)[0];finish(queue,id,'downloaded');finish(queue,id);
  }
  assert.deepEqual(Object.entries(queue.snapshot()).filter(([,state])=>state.enabled).map(([id])=>id),['p0','p1','p2','p21','p22']);
  for(const id of ['p12','p19','p6','p7','p8','p9','p0']){
   queue.select(id);assert.equal(queue.snapshot()[id].enabled,true);
   assert.ok(loading(queue).length<=concurrency);
  }
  assert.equal(queue.snapshot().p0.token,1);assert.equal(queue.snapshot().p0.status,'loaded');
 }
});
