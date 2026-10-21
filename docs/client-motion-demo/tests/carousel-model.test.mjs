import test from 'node:test';
import assert from 'node:assert/strict';
import {wrapIndex,shortestDelta,visibleItems,snapTarget} from '../src/carousel-model.js';

const near=(actual,expected,message)=>assert.ok(Math.abs(actual-expected)<1e-9,message||`${actual} ≈ ${expected}`);
const items=length=>Array.from({length},(_,index)=>({id:`poster-${index}`}));

test('wrap supports long travel, reverse travel, fractions and empty sets',()=>{
 for(const [index,length,expected] of [[0,0,0],[-5,0,0],[99,1,0],[38,38,0],[77,38,1],[-1,38,37],[-77,38,37],[-.25,8,7.75],[16.25,8,.25]]) near(wrapIndex(index,length),expected);
});

test('shortest movement crosses both seams and resolves half-turns consistently',()=>{
 for(const [index,current,length,expected] of [[0,37,38,1],[37,0,38,-1],[0,37.75,38,.25],[37,.25,38,-1.25],[4,0,8,4],[0,4,8,4],[0,0,0,0],[0,0,1,0]]) near(shortestDelta(index,current,length),expected);
});

test('one- and two-result filters never clone a poster to fill the stage',()=>{
 assert.deepEqual(visibleItems([],0),[]);
 const single=items(1);let output=visibleItems(single,0);
 assert.equal(output.length,1);assert.equal(output[0].poster,single[0]);assert.equal(output[0].index,0);near(output[0].offset,0);
 const pair=items(2);output=visibleItems(pair,0);
 assert.deepEqual(output.map(x=>[x.poster.id,x.index,x.offset]),[['poster-0',0,0],['poster-1',1,1]]);
 output=visibleItems(pair,1);
 assert.deepEqual(output.map(x=>[x.poster.id,x.index,x.offset]),[['poster-1',1,0],['poster-0',0,1]]);
});

test('visible window preserves identities while crossing the final-to-first seam',()=>{
 const list=items(8);
 const before=visibleItems(list,7.75,3), after=visibleItems(list,8.25,3);
 assert.deepEqual(before.map(x=>x.poster.id),['poster-7','poster-0','poster-1']);
 assert.deepEqual(after.map(x=>x.poster.id),['poster-7','poster-0','poster-1']);
 before.forEach((entry,i)=>near(after[i].offset-entry.offset,-.5));
 near(before.find(x=>x.poster.id==='poster-0').offset,.25);
 near(after.find(x=>x.poster.id==='poster-0').offset,-.25);
});

test('windows remain unique, ordered and centered for all filter sizes',()=>{
 for(const length of [1,2,3,4,5,6,7,8,38]){
  const list=items(length),snapshot=JSON.stringify(list);
  for(const position of [0,.49,.51,-.4,length-0.3,length+0.2]){
   const output=visibleItems(list,position);
   assert.equal(output.length,Math.min(7,length));
   assert.equal(new Set(output.map(x=>x.poster.id)).size,output.length);
   for(let i=0;i<output.length;i++){
    const entry=output[i];assert.equal(entry.poster,list[entry.index]);assert.ok(Number.isFinite(entry.offset));
    assert.ok(Math.abs(entry.offset)<=length/2+1e-9);
    if(i)assert.ok(entry.offset>=output[i-1].offset);
   }
   assert.ok(output.some(x=>Math.abs(x.offset)<=.5+1e-9));
  }
  assert.equal(JSON.stringify(list),snapshot);
 }
});

test('explicit visible limit keeps the nearest posters and accepts zero',()=>{
 assert.deepEqual(visibleItems(items(8),0,0),[]);
 assert.deepEqual(visibleItems(items(38),0,3).map(x=>x.index),[37,0,1]);
 assert.deepEqual(visibleItems(items(8),2.2,1).map(x=>x.index),[2]);
 assert.equal(visibleItems(items(3),.4,99).length,3);
});

test('release snap respects drag distance, flick direction and unwrapped seam travel',()=>{
 for(const [position,velocity,length,expected] of [[.49,0,8,0],[.51,0,8,1],[.15,.003,8,1],[.85,-.003,8,0],[7.8,.003,8,8],[-.2,-.003,8,-1],[3.2,100,8,4],[3.2,-100,8,2],[100,.1,0,0],[100,.1,1,0]]){
  assert.equal(snapTarget(position,velocity,length),expected,`${position}, ${velocity}, ${length}`);
 }
});
