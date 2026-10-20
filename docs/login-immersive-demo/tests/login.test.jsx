import test from 'node:test';
import assert from 'node:assert/strict';
import { JSDOM } from 'jsdom';
import React, { act } from 'react';
import { createRoot } from 'react-dom/client';
import App, { VIDEO_URL } from '../src/App.jsx';
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

test('React form prevents double submission, handles media failure, focus and real transport by default', async () => {
  const dom = new JSDOM('<div id="root"></div>', { url: 'http://localhost:8772/' });
  Object.assign(globalThis, { window: dom.window, document: dom.window.document, HTMLElement: dom.window.HTMLElement, IS_REACT_ACT_ENVIRONMENT: true });
  const listeners = new Set();
  const media = { matches: false, addEventListener: (_, fn) => listeners.add(fn), removeEventListener: (_, fn) => listeners.delete(fn) };
  window.matchMedia = () => media;
  window.HTMLMediaElement.prototype.play = async function () {};
  window.HTMLMediaElement.prototype.pause = function () {};
  const root = createRoot(document.querySelector('#root'));
  let posts = 0, finish;
  const destinations = [];
  const navigate = value => destinations.push(value);
  const pending = new Promise(resolve => { finish = resolve; });
  const transport = async path => {
    if (path === '/api/login') { posts++; await pending; }
    return { role: 'employee' };
  };
  await act(async () => root.render(<App transport={transport} navigate={navigate} />));
  assert.equal(document.querySelectorAll('input[type=email]').length, 0);
  assert.equal(document.querySelectorAll('a').length, 0);
  assert.equal(document.querySelector('#username').labels[0].textContent, '账号');
  assert.equal(document.querySelector('#password').autocomplete, 'current-password');
  assert.equal(document.querySelector('form').checkValidity(), false);
  assert.equal(document.querySelectorAll('video').length, 1);
  for (const video of document.querySelectorAll('video')) {
    assert.equal(video.getAttribute('src'), VIDEO_URL);
    assert.equal(video.muted, true);
    assert.equal(video.loop, true);
    assert.equal(video.playsInline, true);
  }
  await act(async () => { media.matches = true; for (const listener of listeners) listener(); });
  assert.equal(document.querySelector('video').autoplay, false);
  await act(async () => document.querySelector('video').dispatchEvent(new window.Event('loadedmetadata')));
  assert.equal(document.querySelector('[aria-label="播放背景视频"]').getAttribute('aria-pressed'), 'true');
  await act(async () => document.querySelector('video').dispatchEvent(new window.Event('error')));
  assert.match(document.body.textContent, /视频暂不可用/);
  assert.equal(document.querySelector('button[type=submit]').disabled, false);

  assert.doesNotMatch(document.body.textContent, /填入演示账号|不连接正式账号/);
  await act(async () => document.querySelector('[aria-controls=password]').click());
  assert.equal(document.querySelector('#password').type, 'text');
  await act(async () => document.querySelector('[aria-label="Switch to English"]').click());
  assert.equal(document.documentElement.lang, 'en');
  assert.equal(document.querySelector('#username').value, '');
  assert.equal(document.querySelector('#password').labels[0].textContent, 'Password');

  await act(async () => {
    const form = document.querySelector('form');
    form.dispatchEvent(new window.Event('submit', { bubbles: true, cancelable: true }));
    form.dispatchEvent(new window.Event('submit', { bubbles: true, cancelable: true }));
  });
  assert.equal(posts, 1);
  assert.equal(document.querySelector('button[type=submit]').disabled, true);
  assert.equal(document.querySelector('#password').type, 'password');
  await act(async () => { finish(); await pending; });
  assert.match(document.body.textContent, /Signed in/);
  assert.equal(document.activeElement.id, 'loginTitle');
  assert.deepEqual(destinations, ['/']);
  await act(async () => root.unmount());
  assert.equal(listeners.size, 0);

  media.matches = false;
  window.HTMLMediaElement.prototype.play = async function () { throw new window.DOMException('Autoplay blocked', 'NotAllowedError'); };
  const blockedRoot = createRoot(document.querySelector('#root'));
  await act(async () => blockedRoot.render(<App navigate={navigate} transport={async () => { throw Object.assign(new Error(), {code: 'timeout'}); }} />));
  await act(async () => document.querySelector('video').dispatchEvent(new window.Event('loadedmetadata')));
  assert.equal(document.querySelector('[aria-label="播放背景视频"]').getAttribute('aria-pressed'), 'true');
  assert.equal(document.querySelector('button[type=submit]').disabled, false);
  await act(async () => document.querySelector('form').dispatchEvent(new window.Event('submit', { bubbles: true, cancelable: true })));
  assert.match(document.querySelector('[role=alert]').textContent, /超时/);
  assert.equal(document.querySelector('button[type=submit]').disabled, false);
  await act(async () => blockedRoot.unmount());
  const originalFetch = globalThis.fetch;
  const requests = [];
  globalThis.fetch = async (route, options) => {
    requests.push({route, options});
    return new Response(JSON.stringify({role:'client'}), {status:200, headers:{'Content-Type':'application/json'}});
  };
  const liveRoot = createRoot(document.querySelector('#root'));
  try {
    // With no transport prop, the component must use the existing HTTP client,
    // not silently fall back to the old simulated login.
    await act(async () => liveRoot.render(<App navigate={navigate} />));
    await act(async () => document.querySelector('form').dispatchEvent(new window.Event('submit', { bubbles:true, cancelable:true })));
    assert.deepEqual(requests.map(r => r.route), ['/api/login', '/api/session']);
    assert.equal(requests[0].options.method, 'POST');
    assert.equal(requests[0].options.credentials, 'same-origin');
    assert.equal(requests[0].options.redirect, 'manual');
    assert.equal(destinations.at(-1), '/client');
  } finally {
    await act(async () => liveRoot.unmount());
    globalThis.fetch = originalFetch;
    dom.window.close();
  }
});
