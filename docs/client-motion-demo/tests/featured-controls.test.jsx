import test from 'node:test';
import assert from 'node:assert/strict';
import {JSDOM} from 'jsdom';
import React, {act, useState} from 'react';
import {createRoot} from 'react-dom/client';
import FeaturedShowcase from '../src/FeaturedShowcase.jsx';

test('expanded collection controls report the actual count and reveal selection without scrolling the page', async()=>{
 const dom=new JSDOM('<div id="root"></div>',{url:'http://localhost/',pretendToBeVisual:true});
 const media={matches:true,addEventListener(){},removeEventListener(){}};
 Object.assign(globalThis,{window:dom.window,document:dom.window.document,IS_REACT_ACT_ENVIRONMENT:true,
  matchMedia:()=>media,ResizeObserver:class{constructor(fn){this.fn=fn;}observe(){this.fn([{contentRect:{width:1200}}]);}disconnect(){}},
  requestAnimationFrame:()=>1,cancelAnimationFrame(){}});
 const items=Array.from({length:23},(_,i)=>({id:`p${i}`,name:`Product ${i}`,title:{zh:`图${i}`,en:`Image ${i}`},
  category:i%2 ? 'body' : 'face', style:i%2 ? 'bold' : 'natural',
  kind:{zh:`产品类型${i}`,en:`Product kind ${i}`},description:{zh:`产品说明${i}`,en:`Product description ${i}`},swatch:['#ffffff','#000000'],
  width:1200,height:1000,displayImage:`/${i}.webp`}));
 let selected,opened;
 function Demo({lang='zh'}){
  const [id,choose]=useState(items[0].id);selected=id;
  return <FeaturedShowcase items={items} selectedId={id} onSelect={choose} lang={lang} favorites={[]}
   onOpen={item=>opened=item.id} onFavorite={()=>{}} onBrowse={()=>{}} onFavorites={()=>{}} onInfo={()=>{}}
   onLanguage={()=>{}} modalOpen={false} logo="/logo.webp" SafeImage={props=><img {...props}/>}/>;
 }
 const root=createRoot(document.getElementById('root'));
 try{
  await act(async()=>root.render(<Demo/>));
  const strip=document.querySelector('.colour-swatches'),buttons=[...strip.querySelectorAll('button')];
  assert.equal(buttons.length,23);assert.match(strip.getAttribute('aria-label'),/23 款/);
  assert.equal(document.querySelector('.arc-information h2').textContent,'Product 0');
  assert.match(document.querySelector('.arc-product-facts').textContent,/面部护理.*自然温润/);
  assert.equal(document.querySelector('.colour-position').textContent,'01 / 23');
  strip.scrollLeft=0;
  strip.getBoundingClientRect=()=>({left:20,right:270});
  buttons.forEach((button,i)=>{button.getBoundingClientRect=()=>({left:26+i*50-strip.scrollLeft,right:70+i*50-strip.scrollLeft});});
  window.scrollTo=()=>{throw new Error('Selection must not move the page');};
  await act(async()=>buttons[22].click());
  assert.equal(selected,'p22');assert.equal(document.querySelector('.colour-position').textContent,'23 / 23');
  assert.equal(document.querySelector('.colour-copy').dataset.productId,'p22');
  assert.equal(document.querySelector('.arc-information h2').textContent,'Product 22');
  assert.equal(document.querySelector('.colour-description').textContent,'产品说明22');
  assert.ok(strip.scrollLeft>0);
  assert.ok(buttons[22].getBoundingClientRect().right<=264);
  await act(async()=>document.querySelector('.colour-poster').click());assert.equal(opened,'p22');
  await act(async()=>document.querySelector('[aria-label="下一款"]').click());
  assert.equal(selected,'p0');assert.equal(strip.scrollLeft,0);
  await act(async()=>{document.querySelector('[aria-label="下一款"]').click();document.querySelector('[aria-label="下一款"]').click();document.querySelector('[aria-label="下一款"]').click();});
  assert.equal(selected,'p3');
  assert.equal(document.querySelector('.arc-information h2').textContent,'Product 3');
  assert.match(document.querySelector('.arc-product-facts').textContent,/身体护理.*鲜明个性/);
  await act(async()=>root.render(<Demo lang="en"/>));
  assert.equal(document.querySelector('.colour-description').textContent,'Product description 3');
  assert.match(document.querySelector('.arc-product-facts').textContent,/Body care.*Bold & expressive/);
  assert.equal(document.querySelector('.colour-swatches').getAttribute('aria-label'),'Choose from 23 featured products');
 }finally{await act(async()=>root.unmount());dom.window.close();}
});
