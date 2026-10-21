import test from 'node:test';
import assert from 'node:assert/strict';
import { JSDOM } from 'jsdom';
import React, { act } from 'react';
import { createRoot } from 'react-dom/client';
import App, { POSTER_URL, VIDEO_URL } from '../src/App.jsx';
import { authenticate, inputWarnings, loginDestination } from '../src/login-contract.js';

test('role destinations match the shared login and reject open redirects', () => {
  assert.equal(loginDestination('client', '?code=YZ-BC-000009'), '/client');
  assert.equal(loginDestination('admin'), '/admin');
  assert.equal(loginDestination('employee'), '/');
  assert.equal(loginDestination('admin', '?code=yz-bc-000009'), '/?code=YZ-BC-000009');
  for (const query of ['?next=https://example.org', '?code=//example.org', '?code=YZ-BC-12345', '?code=YZ-BC-000001%0A']) {
    assert.equal(loginDestination('admin', query), '/admin');
  }
  assert.throws(() => loginDestination('unknown'), /invalid_role/);
});

test('authentication submits exactly the original credentials and verifies cookie role', async () => {
  for (const role of ['client', 'employee', 'admin']) {
    const calls = [];
    const result = await authenticate(async (...args) => { calls.push(args); return { role }; },
      { username: 'fixture', password: '  exact password  ', role: 'admin' });
    assert.equal(result.role, role);
    assert.equal(calls[0][0], '/api/login');
    assert.equal(calls[0][1].method, 'POST');
    assert.deepEqual(JSON.parse(calls[0][1].body), { username: 'fixture', password: '  exact password  ' });
    assert.equal(calls[1][0], '/api/session');
  }
  await assert.rejects(authenticate(async path => {
    if (path === '/api/session') throw Object.assign(new Error(), { status: 401 });
    return { role: 'employee' };
  }, {}), /cookie_missing/);
  await assert.rejects(authenticate(async path => ({ role: path === '/api/login' ? 'employee' : 'admin' }), {}), /role_mismatch/);
});

test('failed authentication is not retried and never checks session', async () => {
  let count = 0;
  await assert.rejects(authenticate(async () => { count++; throw new Error('timeout'); }, {}), /timeout/);
  assert.equal(count, 1);
});

test('input hints keep whitespace and invisible-character protections', () => {
  assert.deepEqual(inputWarnings('Ａ\u200B', ' pass ', true), ['invisible', 'whitespace', 'fullwidth', 'caps']);
  assert.deepEqual(inputWarnings('employee', 'pass', false), []);
});


function setup({hidden=false, reduced=false, saveData=false, blocked=false}={}) {
  const dom=new JSDOM('<div id="root"></div>',{url:'http://localhost:8772/login',pretendToBeVisual:true});
  const frames=new Map(); let serial=0,starts=0,draws=0,intersect;
  Object.assign(globalThis,{window:dom.window,document:dom.window.document,HTMLElement:dom.window.HTMLElement,IS_REACT_ACT_ENVIRONMENT:true,
    requestAnimationFrame:fn=>{frames.set(++serial,fn);return serial;},cancelAnimationFrame:id=>frames.delete(id),
    IntersectionObserver:class{constructor(fn){intersect=fn;}observe(){}disconnect(){}}});
  Object.defineProperty(document,'hidden',{configurable:true,value:hidden});
  const listeners=new Set(),query={matches:reduced,addEventListener:(_,f)=>listeners.add(f),removeEventListener:(_,f)=>listeners.delete(f)};
  window.matchMedia=()=>query;
  const previous=Object.getOwnPropertyDescriptor(navigator,'connection');
  const connection={saveData,addEventListener:(_,f)=>listeners.add(f),removeEventListener:(_,f)=>listeners.delete(f)};
  Object.defineProperty(navigator,'connection',{configurable:true,value:connection});
  window.HTMLCanvasElement.prototype.getContext=()=>({drawImage(){draws++;}});
  const playing=new Set();
  window.HTMLMediaElement.prototype.play=async function(){starts++;if(blocked)throw new window.DOMException('Blocked','NotAllowedError');playing.add(this);};
  window.HTMLMediaElement.prototype.pause=function(){playing.delete(this);};
  const root=createRoot(document.getElementById('root'));
  return {root,frames,playing,listeners,query,connection,get starts(){return starts;},get draws(){return draws;},unblock(){blocked=false;},
    async preference(){await act(async()=>listeners.forEach(f=>f()));},
    async visible(value){Object.defineProperty(document,'hidden',{configurable:true,value:!value});await act(async()=>document.dispatchEvent(new window.Event('visibilitychange')));},
    async inView(value){await act(async()=>intersect([{isIntersecting:value}]));},
    async close(){await act(async()=>root.unmount());assert.equal(playing.size,0);assert.equal(frames.size,0);assert.equal(listeners.size,0);if(previous)Object.defineProperty(navigator,'connection',previous);else delete navigator.connection;dom.window.close();}
  };
}

test('one video supplies both surfaces without a pause button; real auth, focus and double-submit protections remain',async()=>{
 const env=setup();let posts=0,finish;const pending=new Promise(r=>finish=r),destinations=[];
 const transport=async path=>{if(path==='/api/login'){posts++;await pending;}return {role:'client'};};
 try {
  await act(async()=>env.root.render(<App transport={transport} navigate={p=>destinations.push(p)}/>));
  assert.equal(document.querySelectorAll('video').length,1);assert.equal(document.querySelectorAll('[data-login-backdrop]').length,1);
  assert.equal(document.querySelector('.motion-toggle'),null);assert.equal(document.querySelector('input[type=email]'),null);
  const video=document.querySelector('video');assert.equal(video.getAttribute('src'),VIDEO_URL);assert.equal(video.getAttribute('poster'),POSTER_URL);
  assert.equal(video.preload,'auto');assert.ok(video.muted&&video.loop&&video.playsInline);
  assert.equal(document.querySelector('#username').labels[0].textContent,'账号');assert.equal(document.querySelector('#password').autocomplete,'current-password');
  const starts=env.starts;
  await act(async()=>document.querySelector('[aria-controls=password]').click());assert.equal(env.starts,starts);assert.equal(document.querySelector('video'),video);
  Object.defineProperty(video,'readyState',{value:4});
  const frame=[...env.frames.values()][0];env.frames.clear();frame(100);assert.equal(env.draws,1);assert.equal(document.querySelector('canvas').style.opacity,'1');
  await act(async()=>video.dispatchEvent(new window.Event('error')));assert.match(document.body.textContent,/视频暂不可用/);assert.equal(document.querySelector('button[type=submit]').disabled,false);
  await act(async()=>document.querySelector('[aria-label="Switch to English"]').click());assert.equal(document.documentElement.lang,'en');
  await act(async()=>{for(let n=0;n<2;n++)document.querySelector('form').dispatchEvent(new window.Event('submit',{bubbles:true,cancelable:true}));});
  assert.equal(posts,1);assert.equal(document.querySelector('button[type=submit]').disabled,true);
  await act(async()=>{finish();await pending;});assert.deepEqual(destinations,['/client']);assert.equal(document.activeElement.id,'loginTitle');
 }finally{await env.close();}
});

test('hidden/out-of-view pages suspend decoding and reduced-motion/save-data do not fetch video',async()=>{
 const env=setup({hidden:true});
 try {
  await act(async()=>env.root.render(<App/>));assert.equal(env.playing.size,0);
  await env.visible(true);assert.equal(env.playing.size,1);
  await env.inView(false);assert.equal(env.playing.size,0);assert.equal(env.frames.size,0);
  await env.inView(true);assert.equal(env.playing.size,1);
  env.query.matches=true;await env.preference();assert.equal(env.playing.size,0);assert.equal(document.querySelector('video').getAttribute('src'),null);
  await env.visible(false);await env.visible(true);assert.equal(env.playing.size,0);
  env.query.matches=false;env.connection.saveData=true;await env.preference();assert.equal(document.querySelector('video').preload,'none');
  env.connection.saveData=false;await env.preference();assert.equal(env.playing.size,1);
 }finally{await env.close();}
});

test('autoplay denial preserves poster and login; genuine user gesture resumes, default transport remains real',async()=>{
 const env=setup({blocked:true});const originalFetch=globalThis.fetch,calls=[];let destination;
 globalThis.fetch=async(route,options)=>{calls.push({route,options});return new Response(JSON.stringify({role:'employee'}),{status:200});};
 try {
  await act(async()=>env.root.render(<App navigate={p=>destination=p}/>));assert.equal(env.playing.size,0);assert.equal(env.frames.size,0);
  assert.equal(document.querySelector('video').getAttribute('poster'),POSTER_URL);assert.equal(document.querySelector('button[type=submit]').disabled,false);
  const starts=env.starts;await env.visible(false);await env.visible(true);assert.equal(env.starts,starts,'Do not retry restricted playback without a gesture');
  env.unblock();await act(async()=>document.querySelector('#username').dispatchEvent(new window.Event('pointerdown',{bubbles:true})));assert.equal(env.playing.size,1);
  await act(async()=>document.querySelector('form').dispatchEvent(new window.Event('submit',{bubbles:true,cancelable:true})));
  assert.deepEqual(calls.map(c=>c.route),['/api/login','/api/session']);assert.equal(calls[0].options.credentials,'same-origin');assert.equal(destination,'/');
 }finally{globalThis.fetch=originalFetch;await env.close();}
});
