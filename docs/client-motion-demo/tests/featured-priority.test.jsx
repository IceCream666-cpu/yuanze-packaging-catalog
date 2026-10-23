import test from 'node:test';
import assert from 'node:assert/strict';
import {JSDOM} from 'jsdom';
import React, {act, useState} from 'react';
import {createRoot} from 'react-dom/client';
import PosterStage from '../src/PosterStage.jsx';

test('target requests win during spring travel, direct input follows the visual center, and loaded nodes survive both', async () => {
  const dom = new JSDOM('<div id="root"></div>',{url:'http://localhost/',pretendToBeVisual:true});
  const media = {matches:false,addEventListener(){},removeEventListener(){}};
  const frames = new Map(), selected = [];
  let sequence = 0, elapsed = 0, choose;
  Object.assign(globalThis, {
    window:dom.window,document:dom.window.document,IS_REACT_ACT_ENVIRONMENT:true,matchMedia:()=>media,
    ResizeObserver:class {constructor(fn){this.fn=fn;}observe(){this.fn([{contentRect:{width:1200}}]);}disconnect(){}},
    requestAnimationFrame:fn=>{frames.set(++sequence,fn);return sequence;},cancelAnimationFrame:id=>frames.delete(id),
  });
  const items=Array.from({length:23},(_,i)=>({id:`p${i}`,title:{zh:`产品${i}`,en:`Product ${i}`},
    width:1200,height:1000,displayImage:`/${i}.webp`}));
  function Demo(){
    const [target,setTarget]=useState('p0');choose=setTarget;
    return <PosterStage items={items} selectedId={target} presentation="products" lang="zh"
      onSelect={id=>{selected.push(id);setTarget(id);}} onOpen={()=>{throw Error('Swipe must not open a modal');}}/>;
  }
  const root=createRoot(document.getElementById('root'));
  const image=id=>document.querySelector(`[data-poster-id="${id}"] img`);
  const advance=async()=>act(async()=>{
    elapsed+=16.667;
    const jobs=[...frames.values()];frames.clear();jobs.forEach(fn=>fn(performance.now()+elapsed));
  });
  try{
    await act(async()=>root.render(<Demo/>));
    const first=image('p0');first.decode=()=>Promise.resolve();
    await act(async()=>first.dispatchEvent(new window.Event('load')));
    assert.equal(document.querySelector('[data-poster-id="p0"] .featured-media').dataset.ready,'true');
    assert.equal(image('p1').getAttribute('src'),'/1.webp');
    assert.equal(image('p22').getAttribute('src'),'/22.webp');
    await act(async()=>choose('p8'));
    assert.equal(image('p8').getAttribute('src'),'/8.webp','A distant chosen target starts while old neighbours are stalled');
    assert.equal(image('p1').getAttribute('src'),null);assert.equal(image('p22').getAttribute('src'),null);
    const requestedTarget=image('p8');
    for(let i=0;i<100&&frames.size;i++){
      await advance();
      assert.equal(image('p8'),requestedTarget,'Intermediate spring anchors must not cancel or replace the target request');
      assert.equal(image('p8').getAttribute('src'),'/8.webp');
    }
    assert.equal(document.querySelector('.center').dataset.posterId,'p8');
    const stage=document.querySelector('.gallery-stage');
    for(const id of ['p9','p10']){
      await act(async()=>stage.dispatchEvent(new window.WheelEvent('wheel',{deltaX:294,deltaY:0,bubbles:true,cancelable:true})));
      await advance();
      assert.equal(document.querySelector('.center').dataset.posterId,id);
      assert.equal(image(id).getAttribute('src'),`/${id.slice(1)}.webp`,'Direct input starts its visual center before release');
      assert.deepEqual(selected,[]);
    }
    await act(async()=>new Promise(resolve=>setTimeout(resolve,135)));
    assert.deepEqual(selected,['p10']);
    for(let i=0;i<100&&frames.size;i++)await advance();
    await act(async()=>choose('p0'));
    assert.equal(image('p0'),first,'The fully loaded source is never remounted or requested again');
    assert.equal(document.querySelector('[data-poster-id="p0"] .featured-media').dataset.ready,'true');
  }finally{await act(async()=>root.unmount());dom.window.close();}
  assert.equal(frames.size,0);
});
