import test from 'node:test';
import assert from 'node:assert/strict';
import {JSDOM} from 'jsdom';
import React, {act, Profiler, useState} from 'react';
import {createRoot} from 'react-dom/client';
import PosterStage from '../src/PosterStage.jsx';

// Deterministic DOM integration: drive the same WheelEvents React receives,
// count commits independently of the display clock and retain actual image nodes.
test('continuous wheel/reverse, rapid keys, pause and filtered pairs remain responsive without frame-rate React commits',async()=>{
 const dom=new JSDOM('<div id="root"></div>',{url:'http://localhost/',pretendToBeVisual:true});
 const mediaListeners=new Set(),media={matches:false,addEventListener:(_,fn)=>mediaListeners.add(fn),removeEventListener:(_,fn)=>mediaListeners.delete(fn)};
 let time=0,id=0,commits=0,selected,frameCount=0;const frames=new Map();
 Object.assign(globalThis,{window:dom.window,document:dom.window.document,HTMLElement:dom.window.HTMLElement,IS_REACT_ACT_ENVIRONMENT:true,matchMedia:()=>media,ResizeObserver:class{constructor(fn){this.fn=fn;}observe(){this.fn([{contentRect:{width:1200}}]);}disconnect(){}},requestAnimationFrame:fn=>{frames.set(++id,fn);return id;},cancelAnimationFrame:id=>frames.delete(id)});
 const items=Array.from({length:8},(_,i)=>({id:`p${i}`,title:{zh:`图${i}`,en:`Image ${i}`},width:1200,height:1000,displayImage:`/${i}.png`,image:`/${i}.png`}));
 const Image=props=><img {...props}/>;
 function Demo({list=items}){const [chosen,choose]=useState(list[0].id);selected=chosen;return <Profiler id="stage" onRender={()=>commits++}><PosterStage items={list} selectedId={chosen} onSelect={choose} onOpen={()=>{throw Error('Swipe must not open a modal');}} lang="zh" SafeImage={Image} presentation="products"/></Profiler>;}
 const root=createRoot(document.getElementById('root'));
 const frame=async()=>{await act(async()=>{time+=16.667;frameCount++;const jobs=[...frames.values()];frames.clear();jobs.forEach(fn=>fn(performance.now()+time));});};
 const finish=async()=>{await act(async()=>{await new Promise(resolve=>setTimeout(resolve,135));});for(let i=0;i<100&&frames.size;i++)await frame();assert.equal(frames.size,0);};
 try{
  await act(async()=>root.render(<Demo/>));
  const stage=document.querySelector('.gallery-stage'),images=[...stage.querySelectorAll('img')];const before=commits;
  for(let f=0;f<40;f++){
   await act(async()=>{for(let j=0;j<4;j++)stage.dispatchEvent(new window.WheelEvent('wheel',{deltaX:6,deltaY:0,bubbles:true,cancelable:true}));});
   await frame();
  }
  await finish();assert.equal(selected,'p3');assert.equal(document.querySelector('.center').dataset.posterId,'p3');
  assert.ok(commits-before<12,`React committed ${commits-before} times during ${frameCount} animation frames`);
  assert.deepEqual([...stage.querySelectorAll('img')],images,'featured images retain DOM identity and order');
  const afterForward=commits;
  for(let f=0;f<30;f++){
   await act(async()=>stage.dispatchEvent(new window.WheelEvent('wheel',{deltaX:-29.4,deltaY:0,bubbles:true,cancelable:true})));await frame();
  }
  await finish();assert.equal(selected,'p0');assert.ok(commits-afterForward<12);
  await act(async()=>{for(let i=0;i<5;i++)stage.dispatchEvent(new window.KeyboardEvent('keydown',{key:'ArrowRight',bubbles:true}));});
  await finish();assert.equal(selected,'p5');assert.equal(document.querySelector('.center').dataset.posterId,'p5');
  const vertical=new window.WheelEvent('wheel',{deltaX:2,deltaY:80,bubbles:true,cancelable:true});stage.dispatchEvent(vertical);assert.equal(vertical.defaultPrevented,false);
  const pinch=new window.WheelEvent('wheel',{deltaX:80,ctrlKey:true,bubbles:true,cancelable:true});stage.dispatchEvent(pinch);assert.equal(pinch.defaultPrevented,false);
  await act(async()=>{stage.dispatchEvent(new window.KeyboardEvent('keydown',{key:'ArrowRight',bubbles:true}));media.matches=true;mediaListeners.forEach(fn=>fn());});
  assert.equal(frames.size,0);assert.equal(document.querySelector('.center').dataset.posterId,'p6');
  await act(async()=>root.render(<Demo key="pair" list={items.slice(0,2)}/>));
  assert.equal(document.querySelectorAll('.poster-plane').length,2);
  assert.equal(document.querySelectorAll('.poster-plane[aria-hidden="false"]').length,1);
  console.log(JSON.stringify({integration:'continuous_input',frames:frameCount,commits,forwardCommits:afterForward-before,imagesRetained:images.length}));
 }finally{await act(async()=>root.unmount());dom.window.close();}
 assert.equal(frames.size,0);
});
