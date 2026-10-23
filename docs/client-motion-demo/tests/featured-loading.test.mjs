import test from 'node:test';
import assert from 'node:assert/strict';
import {createFeaturedLoadQueue} from '../src/featured-loading.js';

const ids=['a','b','c','d','e','f','g','h'];
const loading=queue=>Object.entries(queue.snapshot()).filter(([,value])=>value.status==='loading').map(([id])=>id);
const finish=(queue,id,status='loaded')=>queue.finish(id,queue.snapshot()[id].token,status);

test('first entry gives the center the network, then downloads ahead while the first image decodes',()=>{
 const queue=createFeaturedLoadQueue({ids});queue.select('a');
 assert.deepEqual(loading(queue),['a']);finish(queue,'a','downloaded');
 assert.equal(queue.snapshot().a.status,'decoding');assert.deepEqual(loading(queue),['b','c']);
 finish(queue,'b','downloaded');assert.deepEqual(loading(queue),['c','h']);
 finish(queue,'a');assert.equal(queue.snapshot().a.status,'loaded');
});

test('a newly chosen center gets a reserved slot without destroying progress on its neighbours',()=>{
 const queue=createFeaturedLoadQueue({ids});queue.select('a');finish(queue,'a');
 assert.deepEqual(loading(queue),['b','c']);const before=queue.snapshot();queue.select('f');
 assert.deepEqual(loading(queue),['b','c','f']);
 for(const id of ['b','c'])assert.deepEqual(queue.snapshot()[id],before[id]);
 assert.equal(queue.snapshot().f.enabled,true);
});

test('rapid forward and reverse input keeps started requests and gives the next free slot to the latest center',()=>{
 const queue=createFeaturedLoadQueue({ids});queue.select('a');finish(queue,'a');queue.select('f');
 const started=queue.snapshot();
 for(const id of ['g','h','e','d','h']){
  queue.select(id);assert.equal(loading(queue).length,3);
  for(const prior of ['b','c','f'])assert.deepEqual(queue.snapshot()[prior],started[prior]);
 }
 assert.equal(queue.snapshot().h.status,'idle');finish(queue,'b','downloaded');
 assert.equal(queue.snapshot().h.status,'loading','The latest center, not an obsolete intermediate target, wins');
 assert.deepEqual(loading(queue),['c','f','h']);
 assert.equal(queue.snapshot().g.token,0);assert.equal(queue.snapshot().e.token,0);
 finish(queue,'b');queue.select('b');
 assert.equal(queue.snapshot().b.token,started.b.token);assert.equal(queue.snapshot().b.status,'loaded');
});

test('downloaded images retain their identity through reversals and late callbacks cannot revive a disposed queue',()=>{
 const queue=createFeaturedLoadQueue({ids});queue.select('a');finish(queue,'a','downloaded');
 const original=queue.snapshot().a;
 for(const id of ['e','g','c','h','a'])queue.select(id);
 assert.deepEqual(queue.snapshot().a,original);finish(queue,'a');
 assert.equal(queue.snapshot().a.status,'loaded');assert.equal(queue.snapshot().a.token,original.token);
 const before=queue.snapshot();queue.dispose();queue.select('e');finish(queue,'b');
 assert.deepEqual(queue.snapshot(),before);
});

test('manual retry waits safely when all three slots are busy and stale results cannot complete the retry',()=>{
 const queue=createFeaturedLoadQueue({ids});queue.select('a');finish(queue,'a','error');
 queue.select('f');assert.equal(loading(queue).length,3);
 const oldToken=queue.snapshot().a.token;queue.retry('a');
 assert.equal(queue.snapshot().a.status,'error');assert.equal(loading(queue).length,3);
 finish(queue,'b','downloaded');
 assert.equal(queue.snapshot().a.status,'loading');assert.equal(queue.snapshot().a.token,oldToken+1);
 queue.finish('a',oldToken,'loaded');queue.finish('a',oldToken,'error');
 assert.equal(queue.snapshot().a.status,'loading');finish(queue,'a');
 assert.equal(queue.snapshot().a.status,'loaded');
});

test('all 23 small images warm with bounded concurrency and no duplicate starts despite rapid selection',()=>{
 const expanded=Array.from({length:23},(_,i)=>`p${i}`);
 for(const concurrency of [1,2,3]){
  const queue=createFeaturedLoadQueue({ids:expanded,concurrency});queue.select('p0');
  assert.deepEqual(loading(queue),['p0']);finish(queue,'p0','downloaded');finish(queue,'p0');
  for(const id of ['p12','p19','p6','p7','p8','p9','p0']){
   queue.select(id);assert.ok(loading(queue).length<=concurrency+1);
  }
  let completions=0;
  while(loading(queue).length){
   assert.ok(loading(queue).length<=concurrency+1);
   const id=loading(queue)[0];finish(queue,id,'downloaded');finish(queue,id);
   assert.ok(++completions<=22,'Warming must finish without a request loop');
  }
  for(const state of Object.values(queue.snapshot())){
   assert.equal(state.status,'loaded');assert.equal(state.enabled,true);assert.equal(state.token,1);
  }
 }
});

test('data-saving mode loads only the visible neighbourhood and retained requests survive leaving it',()=>{
 const expanded=Array.from({length:23},(_,i)=>`p${i}`);
 const queue=createFeaturedLoadQueue({ids:expanded,warmCollection:false});queue.select('p0');
 while(loading(queue).length)finish(queue,loading(queue)[0]);
 assert.deepEqual(Object.entries(queue.snapshot()).filter(([,s])=>s.enabled).map(([id])=>id),['p0','p1','p2','p21','p22']);
 queue.select('p12');const target=queue.snapshot().p12;queue.select('p7');queue.select('p18');
 assert.deepEqual(queue.snapshot().p12,target);
 while(loading(queue).length)finish(queue,loading(queue)[0]);
 assert.equal(queue.snapshot().p18.status,'loaded');assert.equal(queue.snapshot().p17.status,'loaded');
 assert.equal(queue.snapshot().p3.status,'idle','Far-away collection images are not warmed in data-saving mode');
});
