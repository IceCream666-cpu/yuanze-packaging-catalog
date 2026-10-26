import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {createRequire} from 'node:module';
import {JSDOM} from 'jsdom';

const require = createRequire(import.meta.url);
const {transformSync} = createRequire(require.resolve('tsx/package.json'))('esbuild');
const sourceDirectory = new URL('../review-source/body-oil-collection/', import.meta.url);
const html = readFileSync(new URL('index.html', sourceDirectory), 'utf8');
const source = readFileSync(new URL('main.js', sourceDirectory), 'utf8')
  .replace(/\nconst root = typeof document[\s\S]*$/, '');
const {code} = transformSync(source, {loader: 'js', format: 'cjs'});
const config = {
  product: {file: 'body-oil-collection.glb', parts: [
    {key:'closure', node:'Closure'}, {key:'liner', node:'InnerSeal'}, {key:'body', node:'Body'},
    {key:'label', node:'PaperLabel'}, {key:'print', node:'LogoPrint'}, {key:'name', node:'ProductPrint'},
  ]},
  design: {name: 'Body Oil Collection', background: '#e9dfcf', ink: '#30251f'},
};
const settle = () => new Promise(resolve => setImmediate(resolve));
function deferred() {
  let resolve, reject;
  const promise = new Promise((yes, no) => {resolve = yes; reject = no;});
  return {promise, resolve, reject};
}
function sceneApi() {
  const calls = {progress: [], zoom: [], rotations: 0, resets: 0, disposals: 0};
  return {calls, setProgress: value => calls.progress.push(value),
    setZoom: value => calls.zoom.push(value),
    rotate: () => calls.rotations++, resetView: () => calls.resets++, dispose: () => calls.disposals++};
}
function setup({fetchImpl, mountScene} = {}) {
  const dom = new JSDOM(html, {url: 'http://localhost/body-oil-collection/', pretendToBeVisual: true});
  const root = dom.window.document.querySelector('.review-app');
  const requests = [], mounts = [], timers = new Map();
  const api = sceneApi();
  let nextTimer = 0;
  const module = {exports: {}};
  new Function('require', 'module', 'exports', 'window', 'document', 'setTimeout', 'clearTimeout', 'DOMException', code)(
    id => {
      assert.equal(id, '../../src/structure/packaging-scene.js');
      return {mountPackagingScene() {throw new Error('WebGL must be explicitly substituted');}};
    }, module, module.exports, dom.window, dom.window.document,
    (callback, delay) => {timers.set(++nextTimer, {callback, delay}); return nextTimer;},
    id => timers.delete(id), dom.window.DOMException,
  );
  const review = module.exports.mountReview(root, {
    fetchImpl: (url, options) => {
      requests.push({url, ...options});
      return fetchImpl ? fetchImpl(url, options) : Promise.resolve({ok: true,
        json: async () => structuredClone(config), arrayBuffer: async () => new ArrayBuffer(12)});
    },
    mountScene: async (host, options) => {
      mounts.push({host, ...options});
      if (mountScene) return mountScene(host, options);
      await options.modelRequest.promise;
      return api;
    },
  });
  const $ = selector => root.querySelector(selector);
  return {dom, root, $, review, api, requests, mounts, timers,
    input(selector, value) {const node = $(selector); node.value = String(value); node.dispatchEvent(new dom.window.Event('input', {bubbles: true}));},
    wheel(deltaY, options = {}) {
      const event = new dom.window.WheelEvent('wheel', {deltaY, bubbles: true, cancelable: true, ...options});
      $('.review-stage').dispatchEvent(event); return event;
    },
    close() {review.destroy(); assert.equal(timers.size, 0, 'destroy clears the loading deadline'); dom.window.close();},
  };
}

test('single empty body oil bottle supports opening, slider, wheel, bounded zoom, rotation and reset', async () => {
  const env = setup();
  try {
    assert.equal(env.$('#controls').disabled, true);
    await settle();
    assert.deepEqual(env.requests.map(request => request.url), ['./review-config.json', './body-oil-collection.glb']);
    assert.equal(env.$('#controls').disabled, false);
    assert.equal(env.$('#model').getAttribute('aria-busy'), 'false');
    assert.equal(env.$('#load-status').hidden, true);
    assert.equal(env.timers.size, 0);
    assert.equal(env.$('#show-liquid'), null);
    assert.match(env.$('.subtitle').textContent, /单瓶身体油空瓶/);
    assert.deepEqual(env.mounts[0].product.parts.map(part => part.node), ['Closure','InnerSeal','Body','PaperLabel','LogoPrint','ProductPrint']);
    env.$('#open-model').click();
    assert.equal(env.api.calls.progress.at(-1), 1);
    assert.equal(env.$('#opening-value').value, '100%');
    assert.equal(env.$('#open-model').getAttribute('aria-pressed'), 'true');
    assert.equal(env.$('#opening').getAttribute('aria-valuetext'), '完全展开，100%');
    env.$('#close-model').click();
    assert.equal(env.api.calls.progress.at(-1), 0);
    assert.equal(env.$('#close-model').getAttribute('aria-pressed'), 'true');
    env.input('#opening', 35);
    assert.equal(env.api.calls.progress.at(-1), .35);
    assert.equal(env.$('#opening-value').value, '35%');
    assert.equal(env.wheel(140).defaultPrevented, true);
    assert.ok(Math.abs(env.api.calls.progress.at(-1) - .45) < 1e-12);
    env.wheel(10, {deltaMode: 1});
    assert.ok(Math.abs(env.api.calls.progress.at(-1) - (.45 + 160 / 1400)) < 1e-12);
    Object.defineProperty(env.$('.review-stage'), 'clientHeight', {value: 700});
    env.input('#opening', 0); env.wheel(1, {deltaMode: 2});
    assert.equal(env.api.calls.progress.at(-1), .5);
    env.wheel(100000); assert.equal(env.api.calls.progress.at(-1), 1);
    env.wheel(-100000); assert.equal(env.api.calls.progress.at(-1), 0);
    const calls = env.api.calls.progress.length;
    assert.equal(env.wheel(700, {ctrlKey: true}).defaultPrevented, false);
    assert.equal(env.wheel(700, {metaKey: true}).defaultPrevented, false);
    assert.equal(env.api.calls.progress.length, calls);
    env.input('#zoom', .7); assert.equal(env.api.calls.zoom.at(-1), .7);
    assert.equal(env.$('#zoom-value').value, '70%');
    assert.equal(env.$('#zoom').getAttribute('aria-valuetext'), '70%');
    env.input('#zoom', 1.7); assert.equal(env.api.calls.zoom.at(-1), 1.7);
    assert.equal(env.$('#zoom-value').value, '170%');
    assert.equal(env.$('#zoom').getAttribute('aria-valuetext'), '170%');
    env.$('#rotate-model').click(); assert.equal(env.api.calls.rotations, 1);
    assert.equal(env.$('#rotate-model').getAttribute('aria-label'), '顺时针旋转90度');
    env.$('#open-model').click(); env.$('#reset-model').click();
    assert.equal(env.api.calls.resets, 1);
    assert.equal(env.api.calls.progress.at(-1), 0);
    assert.equal(env.api.calls.zoom.at(-1), 1);
    assert.equal(env.$('#zoom').getAttribute('aria-valuetext'), '100%');
  } finally {env.close();}
});

test('original-poster mode preserves the mounted scene, opening and zoom, and Escape returns to it', async () => {
  const env = setup();
  try {
    await settle(); env.input('#opening', 62); env.input('#zoom', 1.35);
    const calls = env.api.calls.progress.length;
    env.$('#reference-toggle').click();
    assert.equal(env.$('#reference-view').hidden, false);
    assert.equal(env.$('#controls').disabled, true);
    assert.equal(env.$('#model').getAttribute('aria-hidden'), 'true');
    assert.equal(env.$('#reference-toggle').getAttribute('aria-pressed'), 'true');
    assert.equal(env.wheel(1400).defaultPrevented, false);
    env.$('#open-model').click();
    env.$('#rotate-model').click(); assert.equal(env.api.calls.rotations, 0);
    assert.equal(env.api.calls.progress.length, calls);
    assert.equal(env.api.calls.disposals, 0);
    env.root.dispatchEvent(new env.dom.window.KeyboardEvent('keydown', {key: 'Escape', bubbles: true}));
    assert.equal(env.$('#reference-view').hidden, true);
    assert.equal(env.$('#controls').disabled, false);
    assert.equal(env.$('#model').getAttribute('aria-hidden'), 'false');
    assert.equal(env.$('#opening').value, '62');
    assert.equal(env.$('#zoom').value, '1.35');
    assert.equal(env.api.calls.progress.at(-1), .62);
    assert.equal(env.mounts.length, 1);
    assert.equal(env.requests.length, 2);
  } finally {env.close();}
});

test('a failed request stops at one attempt and only the manual retry starts another load', async () => {
  let configRequests = 0;
  const env = setup({fetchImpl: async url => {
    if (url.endsWith('.json') && ++configRequests === 1) throw new Error('offline');
    return {ok: true, json: async () => structuredClone(config), arrayBuffer: async () => new ArrayBuffer(12)};
  }});
  try {
    await settle(); await settle();
    assert.equal(env.requests.length, 1);
    assert.equal(env.mounts.length, 0);
    assert.equal(env.timers.size, 0, 'failure schedules no automatic retry');
    assert.equal(env.$('#retry').hidden, false);
    assert.equal(env.$('#controls').disabled, true);
    assert.equal(env.$('#model').getAttribute('aria-busy'), 'false');
    assert.match(env.$('#load-message').textContent, /暂时无法加载/);
    env.$('#reference-toggle').click();
    assert.equal(env.$('#reference-view').hidden, false, 'poster remains available after a load failure');
    env.$('#reference-toggle').click(); env.$('#retry').click(); await settle();
    assert.equal(configRequests, 2);
    assert.equal(env.requests.length, 3);
    assert.equal(env.mounts.length, 1);
    assert.equal(env.$('#load-status').hidden, true);
    assert.equal(env.$('#controls').disabled, false);
  } finally {env.close();}
});

test('invalid configuration cannot fetch arbitrary model paths, and model HTTP failure exposes retry', async () => {
  for (const badConfig of [
    {...config, product: {...config.product, file: '../private.glb'}},
    {...config, product: {...config.product, parts: null}},
    {...config, design: {}},
  ]) {
    const env = setup({fetchImpl: async () => ({ok: true, json: async () => badConfig})});
    try {
      await settle(); assert.equal(env.requests.length, 1); assert.equal(env.mounts.length, 0);
      assert.equal(env.$('#retry').hidden, false); assert.equal(env.timers.size, 0);
    } finally {env.close();}
  }
  const env = setup({fetchImpl: async url => url.endsWith('.json')
    ? {ok: true, json: async () => structuredClone(config)} : {ok: false, status: 503}});
  try {
    await settle(); assert.equal(env.requests.length, 2); assert.equal(env.mounts.length, 1);
    assert.equal(env.$('#retry').hidden, false); assert.equal(env.$('#controls').disabled, true);
    assert.equal(env.requests[1].signal.aborted, true); assert.equal(env.timers.size, 0);
  } finally {env.close();}
});

test('the bounded loading deadline aborts pending work and disposes a late scene without enabling controls', async () => {
  const pending = deferred(), lateApi = sceneApi();
  const env = setup({mountScene: () => pending.promise});
  try {
    await settle();
    const [timer] = env.timers.values(); assert.equal(timer.delay, 300000);
    timer.callback();
    assert.equal(env.requests[0].signal.aborted, true);
    assert.equal(env.$('#retry').hidden, false);
    assert.match(env.$('#load-message').textContent, /加载超时/);
    assert.equal(env.timers.size, 0);
    pending.resolve(lateApi); await settle();
    assert.equal(lateApi.calls.disposals, 1);
    assert.equal(lateApi.calls.progress.length, 0);
    assert.equal(env.$('#controls').disabled, true);
    assert.equal(env.requests.length, 2, 'deadline does not retry automatically');
  } finally {env.close();}
});

test('destroy aborts pending fetch, removes handlers, and disposes a scene that resolves after exit', async () => {
  const pending = deferred(), lateApi = sceneApi();
  const env = setup({mountScene: () => pending.promise});
  try {
    await settle(); env.review.destroy(); env.review.destroy();
    assert.ok(env.requests.every(request => request.signal.aborted));
    assert.equal(env.timers.size, 0);
    pending.resolve(lateApi); await settle();
    assert.equal(lateApi.calls.disposals, 1);
    env.$('#retry').click(); await env.review.load();
    env.$('#reference-toggle').click(); env.$('#open-model').click();
    assert.equal(env.requests.length, 2);
    assert.equal(env.$('#reference-view').hidden, true);
    assert.equal(lateApi.calls.progress.length, 0);
  } finally {env.close();}
});

test('a newer load supersedes the old attempt, and pagehide disposes the live scene exactly once', async () => {
  const pending = deferred(), obsoleteApi = sceneApi(), currentApi = sceneApi(); let attempts = 0;
  const env = setup({mountScene: async (_, options) => {
    await options.modelRequest.promise;
    return ++attempts === 1 ? pending.promise : currentApi;
  }});
  try {
    await settle(); const originalSignal = env.mounts[0].signal;
    await env.review.load();
    assert.equal(originalSignal.aborted, true);
    assert.equal(env.requests.length, 4);
    assert.equal(env.$('#controls').disabled, false);
    pending.resolve(obsoleteApi); await settle();
    assert.equal(obsoleteApi.calls.disposals, 1);
    assert.equal(obsoleteApi.calls.progress.length, 0);
    env.$('#open-model').click(); assert.equal(currentApi.calls.progress.at(-1), 1);
    env.dom.window.dispatchEvent(new env.dom.window.Event('pagehide'));
    env.review.destroy(); env.dom.window.dispatchEvent(new env.dom.window.Event('pagehide'));
    assert.equal(currentApi.calls.disposals, 1);
    assert.equal(env.mounts[1].signal.aborted, true);
    assert.equal(env.timers.size, 0);
    const count = currentApi.calls.progress.length;
    env.$('#close-model').click(); assert.equal(currentApi.calls.progress.length, count);
  } finally {env.close();}
});
