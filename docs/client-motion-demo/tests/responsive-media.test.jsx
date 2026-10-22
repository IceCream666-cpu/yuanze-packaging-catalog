import test from 'node:test';
import assert from 'node:assert/strict';
import {JSDOM} from 'jsdom';
import React, {act} from 'react';
import {createRoot} from 'react-dom/client';
import SafeImage from '../src/SafeImage.jsx';
import {imageCandidates} from '../src/media-policy.js';

test('responsive candidates use real portrait widths, not longest-edge labels', () => {
  assert.equal(imageCandidates([['/large',683],['/small',427]]), '/small 427w, /large 683w');
});

test('a stale decode cannot reveal a retried source or fail its replacement request', async () => {
  const dom = new JSDOM('<div id="root"></div>', {url:'http://localhost',pretendToBeVisual:true});
  Object.assign(globalThis,{window:dom.window,document:dom.window.document,IS_REACT_ACT_ENVIRONMENT:true});
  const root=createRoot(document.getElementById('root'));let resolveOld,rejectOld,loads=0,errors=0;
  const render=src=><SafeImage src={src} alt="Poster" onLoad={()=>loads++} onError={()=>errors++}/>;
  try {
    await act(async()=>root.render(render('/original.webp')));
    const img=document.querySelector('img');img.decode=()=>new Promise(resolve=>resolveOld=resolve);
    await act(async()=>img.dispatchEvent(new window.Event('load')));
    await act(async()=>img.dispatchEvent(new window.Event('error')));
    assert.equal(img.getAttribute('src'),'/original.webp?retry=1');
    await act(async()=>resolveOld());
    assert.equal(document.querySelector('.responsive-media').dataset.ready,'false');assert.equal(loads,0);
    // The pending retry now gets replaced by a different source on the same node.
    img.decode=()=>new Promise((resolve,reject)=>rejectOld=reject);
    await act(async()=>img.dispatchEvent(new window.Event('load')));
    await act(async()=>root.render(render('/replacement.webp')));
    assert.equal(document.querySelector('img'),img);
    await act(async()=>rejectOld(new Error('Old decode aborted')));
    assert.equal(img.getAttribute('src'),'/replacement.webp');assert.equal(errors,0);
    assert.equal(document.querySelector('.responsive-media').dataset.ready,'false');
    img.decode=()=>Promise.resolve();await act(async()=>img.dispatchEvent(new window.Event('load')));
    assert.equal(loads,1);assert.equal(img.style.opacity,'1');
  } finally {await act(async()=>root.unmount());dom.window.close();}
});

test('decode rejection after unmount cannot report an error into the next lightbox', async () => {
  const dom = new JSDOM('<div id="root"></div>', {url:'http://localhost',pretendToBeVisual:true});
  Object.assign(globalThis,{window:dom.window,document:dom.window.document,IS_REACT_ACT_ENVIRONMENT:true});
  const root=createRoot(document.getElementById('root'));let rejectOld,errors=0;
  try {
    await act(async()=>root.render(<SafeImage src="/original.webp" alt="Poster" onError={()=>errors++}/>));
    const img=document.querySelector('img');
    await act(async()=>img.dispatchEvent(new window.Event('error')));
    img.decode=()=>new Promise((resolve,reject)=>rejectOld=reject);
    await act(async()=>img.dispatchEvent(new window.Event('load')));
    await act(async()=>root.render(<div>Next lightbox</div>));
    await act(async()=>rejectOld(new Error('Old decode aborted')));
    assert.equal(errors,0);
  } finally {await act(async()=>root.unmount());dom.window.close();}
});

test('offscreen media waits; started requests survive leaving the visible window; decode is atomic; errors can recover', async () => {
  const dom = new JSDOM('<div id="root"></div>', {url:'http://localhost',pretendToBeVisual:true});
  let observed, done = 0, errors = 0, finishDecode;
  Object.assign(globalThis,{window:dom.window,document:dom.window.document,IS_REACT_ACT_ENVIRONMENT:true,
    IntersectionObserver:class {constructor(fn){observed=fn;}observe(){}disconnect(){}}});
  const root = createRoot(document.getElementById('root'));
  const render = enabled => <SafeImage src="/large.webp" srcSet="/small.webp 512w, /large.webp 1280w" sizes="85vw" loading="lazy" enabled={enabled} alt="Poster" onLoad={()=>done++} onError={()=>errors++}/>;
  try {
    await act(async()=>root.render(render(true)));
    const img=document.querySelector('img');assert.equal(img.getAttribute('src'),null);
    await act(async()=>observed([{isIntersecting:true}]));
    assert.equal(img.getAttribute('src'),'/large.webp');
    await act(async()=>root.render(render(false)));
    assert.equal(img.getAttribute('src'),'/large.webp');assert.equal(document.querySelector('img'),img);
    img.decode=()=>new Promise(resolve=>finishDecode=resolve);
    await act(async()=>img.dispatchEvent(new window.Event('load')));
    assert.equal(img.style.opacity,'0');assert.equal(done,0);
    await act(async()=>finishDecode());assert.equal(img.style.opacity,'1');assert.equal(done,1);
    await act(async()=>img.dispatchEvent(new window.Event('error')));
    assert.equal(img.getAttribute('src'),'/large.webp?retry=1');assert.equal(img.getAttribute('srcset'),null);
    await act(async()=>img.dispatchEvent(new window.Event('error')));
    assert.equal(errors,1);assert.match(document.querySelector('.media-status').textContent,/重试/);
    await act(async()=>document.querySelector('.media-status').click());
    assert.equal(img.getAttribute('src'),'/large.webp?retry=2');
    img.decode=()=>Promise.resolve();await act(async()=>img.dispatchEvent(new window.Event('load')));
    assert.equal(img.style.opacity,'1');assert.equal(document.querySelector('.media-status'),null);
  } finally {await act(async()=>root.unmount());dom.window.close();delete globalThis.IntersectionObserver;}
});
