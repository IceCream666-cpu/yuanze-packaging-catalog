import test from 'node:test';
import assert from 'node:assert/strict';
import {JSDOM} from 'jsdom';
import React,{act} from 'react';
import {createRoot} from 'react-dom/client';
import FeaturedImage from '../src/FeaturedImage.jsx';

const poster={displayImage:'/1024.webp',displaySrcSet:'/640.webp 427w, /1024.webp 683w',displaySizes:'290px',placeholder:'data:image/webp;base64,AA',displayWidth:1024,displayHeight:1536};
const wait=ms=>new Promise(resolve=>setTimeout(resolve,ms));

async function setup(run){
 const dom=new JSDOM('<div id="root"></div>',{url:'http://localhost',pretendToBeVisual:true});
 Object.assign(globalThis,{window:dom.window,document:dom.window.document,IS_REACT_ACT_ENVIRONMENT:true});
 const root=createRoot(document.getElementById('root'));
 try{await run(root);}finally{await act(async()=>root.unmount());dom.window.close();}
}

test('no low-resolution product is shown; a complete responsive image appears after decode',async()=>setup(async root=>{
 let done=[],decode;
 const render=(enabled,active=true)=><FeaturedImage poster={poster} active={active} enabled={enabled} requestKey={1} onSettled={value=>done.push(value)} alt="Product"/>;
  await act(async()=>root.render(render(false)));
  assert.equal(document.querySelector('picture img').getAttribute('src'),null);
  assert.equal(document.querySelector('img[src^="data:"]'),null);
  assert.ok(document.querySelector('.featured-loading-shape'));
  const waitingImage=document.querySelector('picture img');
  await act(async()=>root.render(render(true)));const image=document.querySelector('picture img');
  assert.equal(image,waitingImage);
  assert.equal(image.getAttribute('srcset'),poster.displaySrcSet);assert.equal(image.getAttribute('sizes'),'290px');
  image.decode=()=>new Promise(r=>decode=r);await act(async()=>image.dispatchEvent(new window.Event('load')));
  assert.equal(image.style.opacity,'0');assert.deepEqual(done,[]);
  await act(async()=>root.render(render(true,false)));
  assert.equal(document.querySelector('picture img'),image);assert.equal(image.getAttribute('src'),'/1024.webp');
  assert.equal(image.getAttribute('fetchpriority'),'low');
  await act(async()=>decode());assert.equal(image.style.opacity,'1');assert.deepEqual(done,['loaded']);
  assert.equal(document.querySelector('.featured-loading'),null);
}));

test('failed media retries once, releases the queue and offers a recoverable failure instead of a mosaic',async()=>setup(async root=>{
 const done=[];
 const render=token=><FeaturedImage poster={poster} active enabled requestKey={token} retryDelay={0} onSettled={value=>done.push(value)} alt="Product" lang="zh"/>;
 await act(async()=>root.render(render(1)));
 const original=document.querySelector('picture img');
 await act(async()=>original.dispatchEvent(new window.Event('error')));
 await act(async()=>wait(5));
 const retry=document.querySelector('picture img');
 assert.notEqual(retry,original);assert.match(retry.getAttribute('src'),/media_retry=1-1/);
 assert.equal(retry.getAttribute('srcset'),null);
 await act(async()=>retry.dispatchEvent(new window.Event('error')));
 assert.deepEqual(done,['error']);
 assert.equal(document.querySelector('.featured-media').dataset.failed,'true');
 assert.equal(document.querySelector('picture img').getAttribute('src'),null);
 assert.match(document.querySelector('.featured-loading-label').textContent,/点击重试/);
 assert.equal(document.querySelector('img[src^="data:"]'),null);
 await act(async()=>root.render(render(2)));
 const recovered=document.querySelector('picture img');recovered.decode=()=>Promise.resolve();
 await act(async()=>recovered.dispatchEvent(new window.Event('load')));
 assert.deepEqual(done,['error','loaded']);assert.equal(document.querySelector('.featured-media').dataset.ready,'true');
}));

test('a stalled request has a bounded lifetime and cannot hold the loading queue forever',async()=>setup(async root=>{
 const done=[];
 await act(async()=>root.render(<FeaturedImage poster={poster} active enabled requestKey={1} retryDelay={0} timeoutMs={10} onSettled={value=>done.push(value)} alt="Product"/>));
 await act(async()=>wait(20));
 await act(async()=>wait(20));
 assert.deepEqual(done,['error']);assert.equal(document.querySelector('.featured-media').dataset.failed,'true');
}));

test('an old decode result cannot replace the state of a manual retry',async()=>setup(async root=>{
 const done=[];let decode;
 const render=token=><FeaturedImage poster={poster} active enabled requestKey={token} onSettled={value=>done.push(value)} alt="Product"/>;
 await act(async()=>root.render(render(1)));
 const original=document.querySelector('picture img');original.decode=()=>new Promise(resolve=>decode=resolve);
 await act(async()=>original.dispatchEvent(new window.Event('load')));
 await act(async()=>root.render(render(2)));
 await act(async()=>decode());
 assert.deepEqual(done,[]);assert.equal(document.querySelector('.featured-media').dataset.ready,'false');
}));

test('download completion releases a slot while the image is still decoding',async()=>setup(async root=>{
 const events=[];let decode;
 await act(async()=>root.render(<FeaturedImage poster={poster} active enabled
   onTransferred={()=>events.push('downloaded')} onSettled={()=>events.push('loaded')} alt="Product"/>));
 const img=document.querySelector('picture img');img.decode=()=>new Promise(resolve=>decode=resolve);
 await act(async()=>img.dispatchEvent(new window.Event('load')));
 assert.deepEqual(events,['downloaded']);assert.equal(img.style.opacity,'0');
 await act(async()=>decode());assert.deepEqual(events,['downloaded','loaded']);assert.equal(img.style.opacity,'1');
}));

test('neighbours use the light image, retain it during a selected upgrade, and cancel unfinished upgrades',async()=>setup(async root=>{
 const media={...poster,displayMobile:'/640.webp'};
 const render=active=><FeaturedImage poster={media} active={active} enabled alt="Product"/>;
 await act(async()=>root.render(render(false)));
 const base=document.querySelector('picture img');assert.equal(base.getAttribute('src'),'/640.webp');
 assert.equal(base.getAttribute('srcset'),null);base.decode=()=>Promise.resolve();
 await act(async()=>base.dispatchEvent(new window.Event('load')));
 await act(async()=>root.render(render(true)));
 await act(async()=>wait(230));
 const detail=document.querySelector('.featured-detail');assert.ok(detail);assert.equal(base.style.opacity,'1');
 assert.equal(detail.style.opacity,'0');assert.equal(detail.getAttribute('srcset'),poster.displaySrcSet);
 await act(async()=>root.render(render(false)));
 assert.equal(document.querySelector('.featured-detail'),null);assert.equal(document.querySelector('picture img'),base);
 await act(async()=>root.render(render(true)));await act(async()=>wait(230));
 const finished=document.querySelector('.featured-detail');finished.decode=()=>Promise.resolve();
 await act(async()=>finished.dispatchEvent(new window.Event('load')));
 await act(async()=>root.render(render(false)));
 assert.equal(document.querySelector('.featured-detail'),finished);assert.equal(finished.style.opacity,'1');
}));

test('mobile failure retries the approved light derivative instead of forcing a 1024 download',async()=>setup(async root=>{
 await act(async()=>root.render(<FeaturedImage poster={{...poster,displayMobile:'/640.webp'}} active enabled
   retryDelay={0} alt="Product"/>));
 await act(async()=>document.querySelector('picture img').dispatchEvent(new window.Event('error')));
 await act(async()=>wait(5));
 assert.match(document.querySelector('picture img').getAttribute('src'),/^\/640.webp\?media_retry=/);
}));

test('an intermediate visual center does not upgrade ahead of the explicit target',async()=>setup(async root=>{
 await act(async()=>root.render(<FeaturedImage poster={{...poster,displayMobile:'/640.webp'}} active urgent={false} enabled alt="Product"/>));
 const base=document.querySelector('picture img');base.decode=()=>Promise.resolve();
 await act(async()=>base.dispatchEvent(new window.Event('load')));await act(async()=>wait(230));
 assert.equal(document.querySelector('.featured-detail'),null);assert.equal(base.getAttribute('fetchpriority'),'low');
}));

test('decode failure after transfer does not launch an uncounted retry; a hung valid image has a bounded fallback',async()=>setup(async root=>{
 let transferred=0,done=[];
 const render=key=><FeaturedImage poster={poster} active enabled requestKey={key} decodeTimeoutMs={10}
   onTransferred={()=>transferred++} onSettled={state=>done.push(state)} alt="Product"/>;
 await act(async()=>root.render(render(1)));
 const broken=document.querySelector('picture img');broken.decode=()=>Promise.reject(new Error('bad decode'));
 await act(async()=>broken.dispatchEvent(new window.Event('load')));
 assert.deepEqual(done,['error']);assert.equal(broken.getAttribute('src'),null);assert.equal(transferred,1);
 await act(async()=>root.render(render(2)));
 const valid=document.querySelector('picture img');valid.decode=()=>new Promise(()=>{});
 Object.defineProperties(valid,{complete:{value:true},naturalWidth:{value:640}});
 await act(async()=>valid.dispatchEvent(new window.Event('load')));await act(async()=>wait(20));
 assert.deepEqual(done,['error','loaded']);assert.equal(valid.style.opacity,'1');
}));
