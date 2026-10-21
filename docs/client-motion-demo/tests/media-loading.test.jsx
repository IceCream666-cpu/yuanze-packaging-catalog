import test from 'node:test';
import assert from 'node:assert/strict';
import {JSDOM} from 'jsdom';
import React,{act} from 'react';
import {createRoot} from 'react-dom/client';
import FeaturedImage from '../src/FeaturedImage.jsx';

test('complete placeholder remains until decode; inactive media waits, errors release the queue',async()=>{
 const dom=new JSDOM('<div id="root"></div>',{url:'http://localhost',pretendToBeVisual:true});
 Object.assign(globalThis,{window:dom.window,document:dom.window.document,IS_REACT_ACT_ENVIRONMENT:true});
 const root=createRoot(document.getElementById('root'));let done=0,decode;
 const poster={displayImage:'/1024.webp',displayMobile:'/640.webp',placeholder:'data:image/webp;base64,AA',displayWidth:1200,displayHeight:1200};
 const render=enabled=><FeaturedImage poster={poster} active={enabled} enabled={enabled} onReady={()=>done++} alt="Product"/>;
 try{
  await act(async()=>root.render(render(false)));const image=document.querySelector('picture img');
  assert.equal(image.getAttribute('src'),null);assert.equal(document.querySelector('source').getAttribute('srcset'),null);
  assert.equal(document.querySelector('.featured-placeholder').style.opacity,'1');
  await act(async()=>root.render(render(true)));assert.equal(document.querySelector('picture img'),image);
  image.decode=()=>new Promise(r=>decode=r);await act(async()=>image.dispatchEvent(new window.Event('load')));
  assert.equal(image.style.opacity,'0');assert.equal(done,0);
  await act(async()=>decode());assert.equal(image.style.opacity,'1');assert.equal(done,1);
  assert.equal(document.querySelector('source').getAttribute('srcset'),'/640.webp');
  await act(async()=>image.dispatchEvent(new window.Event('error')));assert.equal(done,2);
 }finally{await act(async()=>root.unmount());dom.window.close();}
});
