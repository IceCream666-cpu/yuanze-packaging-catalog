import test from 'node:test';
import assert from 'node:assert/strict';
import {createFeaturedLoadQueue} from '../src/featured-loading.js';

const ids=['a','b','c','d','e','f','g','h'];
const loading=queue=>Object.entries(queue.snapshot()).filter(([,value])=>value.status==='loading').map(([id])=>id);

test('selection starts at most two images and gives a new current item the next slot',()=>{
 const queue=createFeaturedLoadQueue({ids});
 queue.select('a');assert.deepEqual(loading(queue),['a','b']);
 queue.select('e');queue.select('g');
 assert.deepEqual(loading(queue),['a','b']);
 assert.equal(queue.snapshot().a.enabled,true);
 queue.finish('a',1,'loaded');assert.deepEqual(loading(queue),['b','g']);
 queue.finish('b',1,'loaded');assert.deepEqual(loading(queue),['g','h']);
 assert.equal(queue.snapshot().e.enabled,false);
 queue.finish('g',1,'loaded');assert.deepEqual(loading(queue),['f','h']);
 queue.finish('h',1,'loaded');queue.finish('f',1,'loaded');queue.finish('e',1,'loaded');
 assert.deepEqual(loading(queue),[]);assert.equal(queue.snapshot().d.enabled,false);
});

test('first-image failure does not block its neighbour and manual retry creates a fresh token',()=>{
 const queue=createFeaturedLoadQueue({ids});queue.select('a');
 queue.finish('a',1,'error');assert.deepEqual(loading(queue),['b','h']);
 queue.retry('a');assert.deepEqual(loading(queue),['b','h']);
 queue.finish('b',1,'loaded');assert.deepEqual(loading(queue),['a','h']);
 assert.equal(queue.snapshot().a.token,2);
 queue.finish('a',1,'loaded');assert.equal(queue.snapshot().a.status,'loading');
 queue.finish('a',2,'loaded');assert.equal(queue.snapshot().a.status,'loaded');
});

test('completed image sources remain enabled across fast changes without duplicate loads',()=>{
 const queue=createFeaturedLoadQueue({ids});queue.select('a');queue.finish('a',1,'loaded');
 for(const id of ['b','c','d','e','a'])queue.select(id);
 assert.equal(queue.snapshot().a.enabled,true);assert.equal(queue.snapshot().a.status,'loaded');
 assert.equal(queue.snapshot().a.token,1);assert.ok(loading(queue).length<=2);
 const prior=queue.snapshot();queue.dispose();queue.finish('b',1,'loaded');queue.select('e');
 assert.deepEqual(queue.snapshot(),prior);
});

test('both visible neighbours on each side eventually load without preloading distant products',()=>{
 const queue=createFeaturedLoadQueue({ids});queue.select('a');
 while(loading(queue).length){const id=loading(queue)[0];queue.finish(id,queue.snapshot()[id].token,'loaded');}
 assert.deepEqual(Object.entries(queue.snapshot()).filter(([,state])=>state.enabled).map(([id])=>id),['a','b','c','g','h']);
});

test('a 23-product collection still loads only five initial neighbours with at most two in flight',()=>{
 const expanded=Array.from({length:23},(_,i)=>`p${i}`);
 const queue=createFeaturedLoadQueue({ids:expanded});queue.select('p0');
 assert.deepEqual(loading(queue),['p0','p1']);
 while(loading(queue).length){
  assert.ok(loading(queue).length<=2);
  const id=loading(queue)[0];queue.finish(id,queue.snapshot()[id].token,'loaded');
 }
 assert.deepEqual(Object.entries(queue.snapshot()).filter(([,state])=>state.enabled).map(([id])=>id),['p0','p1','p2','p21','p22']);
 queue.select('p12');assert.deepEqual(loading(queue),['p12','p13']);
 queue.select('p19');queue.finish('p12',1,'loaded');
 assert.deepEqual(loading(queue),['p13','p19']);
 assert.equal(queue.snapshot().p0.token,1);assert.equal(queue.snapshot().p0.status,'loaded');
});
