import test from 'node:test';
import assert from 'node:assert/strict';
import {JSDOM} from 'jsdom';
import React, {act, useState} from 'react';
import {createRoot} from 'react-dom/client';
import PosterStage from '../src/PosterStage.jsx';

test('failed active products retry through the existing parent button without a nested control',async()=>{
 const dom=new JSDOM('<div id="root"></div>',{url:'http://localhost/',pretendToBeVisual:true});
 const media={matches:true,addEventListener(){},removeEventListener(){}};
 Object.assign(globalThis,{window:dom.window,document:dom.window.document,IS_REACT_ACT_ENVIRONMENT:true,
  matchMedia:()=>media,ResizeObserver:class{constructor(fn){this.fn=fn;}observe(){this.fn([{contentRect:{width:1200}}]);}disconnect(){}},
  requestAnimationFrame:()=>1,cancelAnimationFrame(){}});
 const items=Array.from({length:8},(_,i)=>({id:`p${i}`,title:{zh:`图${i}`,en:`Image ${i}`},width:1200,height:1000,
  displayImage:`/${i}.webp`,displaySrcSet:`/${i}.webp 1024w`,displaySizes:'460px'}));
 let opened=0;
 function Demo(){const [selected,choose]=useState('p0');return <PosterStage items={items} selectedId={selected} onSelect={choose}
  onOpen={()=>opened++} lang="zh" presentation="products" SafeImage={props=><img {...props}/>}/>;}
 const root=createRoot(document.getElementById('root'));
 try{
  await act(async()=>root.render(<Demo/>));
  const button=document.querySelector('[data-poster-id="p0"]');
  assert.equal(document.querySelectorAll('.poster-plane picture img[src]').length,1);
  await act(async()=>button.querySelector('img').dispatchEvent(new window.Event('error')));
  await act(async()=>new Promise(resolve=>setTimeout(resolve,375)));
  await act(async()=>button.querySelector('img').dispatchEvent(new window.Event('error')));
  assert.match(button.getAttribute('aria-label'),/^重试图片/);
  assert.equal(button.querySelector('button'),null);
  await act(async()=>button.click());
  assert.equal(opened,0,'Retry must not open the poster modal');
  // Both neighbour slots were occupied; retry replaces the lower-priority
  // unfinished source immediately rather than waiting for a neighbour.
  assert.equal(document.querySelector('[data-poster-id="p7"] img').getAttribute('src'),null);
  const retry=button.querySelector('img');assert.equal(retry.getAttribute('src'),'/0.webp');retry.decode=()=>Promise.resolve();
  await act(async()=>retry.dispatchEvent(new window.Event('load')));
  assert.match(button.getAttribute('aria-label'),/^查看海报/);
  await act(async()=>button.click());assert.equal(opened,1);
 }finally{await act(async()=>root.unmount());dom.window.close();}
});
