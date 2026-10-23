import test from 'node:test';
import assert from 'node:assert/strict';
import {JSDOM} from 'jsdom';
import React, {act, useState} from 'react';
import {createRoot} from 'react-dom/client';
import PosterStage from '../src/PosterStage.jsx';

const wait=ms=>new Promise(resolve=>setTimeout(resolve,ms));
async function setup(run){
 const dom=new JSDOM('<div id="root"></div>',{url:'http://localhost/',pretendToBeVisual:true});
 const media={matches:false,addEventListener(){},removeEventListener(){}};
 const frames=new Map(),selected=[];let sequence=0,elapsed=0,choose;
 Object.assign(globalThis,{window:dom.window,document:dom.window.document,IS_REACT_ACT_ENVIRONMENT:true,matchMedia:()=>media,
  ResizeObserver:class{constructor(fn){this.fn=fn;}observe(){this.fn([{contentRect:{width:1200}}]);}disconnect(){}},
  requestAnimationFrame:fn=>{frames.set(++sequence,fn);return sequence;},cancelAnimationFrame:id=>frames.delete(id)});
 const items=Array.from({length:23},(_,i)=>({id:`p${i}`,title:{zh:`产品${i}`,en:`Product ${i}`},width:1200,height:1000,
  displayImage:`/${i}-1024.webp`,displayMobile:`/${i}-640.webp`,displaySrcSet:`/${i}-1024.webp 1024w`,displaySizes:'310px'}));
 function Demo(){const[target,setTarget]=useState('p0');choose=setTarget;return <PosterStage items={items} selectedId={target}
  presentation="products" lang="zh" onSelect={id=>{selected.push(id);setTarget(id);}}
  onOpen={()=>{throw Error('Swipe must not open a modal');}}/>;}
 const root=createRoot(document.getElementById('root'));
 const image=id=>document.querySelector(`[data-poster-id="${id}"] picture img`);
 const advance=async()=>act(async()=>{elapsed+=16.667;const jobs=[...frames.values()];frames.clear();jobs.forEach(fn=>fn(performance.now()+elapsed));});
 const load=async id=>{const img=image(id);img.decode=()=>Promise.resolve();await act(async()=>img.dispatchEvent(new window.Event('load')));};
 const wheel=async dx=>{await act(async()=>document.querySelector('.gallery-stage').dispatchEvent(new window.WheelEvent('wheel',{
  deltaX:dx,deltaY:0,bubbles:true,cancelable:true})));await advance();};
 try{await act(async()=>root.render(<Demo/>));await run({image,advance,load,wheel,frames,selected,choose:id=>act(async()=>choose(id))});}
 finally{await act(async()=>root.unmount());dom.window.close();}
 assert.equal(frames.size,0);
}

test('distant targets and rapid reversals retain started image nodes while the latest target receives the next slot',async()=>setup(async({image,advance,load,wheel,frames,selected,choose})=>{
 const first=image('p0');assert.equal(first.getAttribute('src'),'/0-640.webp');assert.equal(first.getAttribute('srcset'),null);
 await load('p0');const neighbours=[image('p1'),image('p2')];
 assert.equal(neighbours[0].getAttribute('src'),'/1-640.webp');assert.equal(neighbours[1].getAttribute('src'),'/2-640.webp');
 await choose('p8');const requestedTarget=image('p8');assert.equal(requestedTarget.getAttribute('src'),'/8-640.webp');
 for(let i=0;i<100&&frames.size;i++){
  await advance();assert.equal(image('p8'),requestedTarget,'Spring anchors cannot restart the target');
 }
 assert.equal(document.querySelector('.center').dataset.posterId,'p8');
 for(const id of ['p9','p10']){
  await wheel(294);assert.equal(document.querySelector('.center').dataset.posterId,id);
  assert.equal(image(id).getAttribute('src'),null,'Further centers wait for a slot without restarting unfinished work');
 }
 assert.deepEqual(selected,[]);assert.equal(image('p1'),neighbours[0]);assert.equal(image('p2'),neighbours[1]);
 assert.equal(image('p8'),requestedTarget);await load('p1');
 assert.equal(image('p10').getAttribute('src'),'/10-640.webp');assert.equal(image('p9').getAttribute('src'),null);
 await wheel(-294);await load('p2');
 assert.equal(document.querySelector('.center').dataset.posterId,'p9');assert.equal(image('p9').getAttribute('src'),'/9-640.webp');
 assert.equal(image('p10').getAttribute('src'),'/10-640.webp','Changing direction retains the former target request');
 await act(async()=>wait(135));assert.deepEqual(selected,['p9']);
 for(let i=0;i<100&&frames.size;i++)await advance();await choose('p0');
 assert.equal(image('p0'),first);assert.equal(document.querySelector('[data-poster-id="p0"] .featured-media').dataset.ready,'true');
}));

test('detail downloads wait for base coverage and a real settled gesture, even when a center stays selected over 220ms',async()=>setup(async({image,advance,load,wheel,frames})=>{
 await load('p0');await act(async()=>wait(240));
 assert.equal(document.querySelector('.featured-detail'),null,'A selected ready image must not compete with unfinished base downloads');
 let loaded=1;
 while(loaded<23){
  const next=[...document.querySelectorAll('.poster-plane')].find(node=>node.querySelector('picture img').getAttribute('src')&&node.querySelector('.featured-media').dataset.ready!=='true');
  assert.ok(next,'The collection should continue warming after the visible five');await load(next.dataset.posterId);loaded++;
 }
 await act(async()=>wait(240));assert.ok(document.querySelector('[data-poster-id="p0"] .featured-detail'));
 await wheel(294);assert.equal(document.querySelector('.center').dataset.posterId,'p1');
 for(let i=0;i<4;i++){await act(async()=>wait(80));await wheel(.2);}
 assert.equal(document.querySelector('.center').dataset.posterId,'p1');
 assert.ok(document.querySelector('.gallery-stage').classList.contains('is-moving'));
 assert.equal(document.querySelector('.featured-detail'),null,'A center held during direct input cannot start a detail request');
 assert.equal(image('p1').style.opacity,'1','The decoded base remains visible throughout the gesture');
 await act(async()=>wait(135));for(let i=0;i<100&&frames.size;i++)await advance();
 assert.equal(document.querySelector('.gallery-stage').classList.contains('is-moving'),false);
 await act(async()=>wait(240));assert.ok(document.querySelector('[data-poster-id="p1"] .featured-detail'));
 assert.equal(image('p1').style.opacity,'1');
}));
