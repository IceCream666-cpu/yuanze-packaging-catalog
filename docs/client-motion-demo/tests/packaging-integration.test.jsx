import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {createRequire} from 'node:module';
import {JSDOM} from 'jsdom';
import React, {act, useEffect} from 'react';
import {createRoot} from 'react-dom/client';

// Compile the real component source with the already-installed tsx transformer.
// Only CSS and asynchronous module boundaries are substituted: lifecycle, event
// handlers, state, fallback UI and the App's routing run unchanged in React.
const require = createRequire(import.meta.url);
const {transformSync} = createRequire(require.resolve('tsx/package.json'))('esbuild');
function component(name, {deps = {}, mocks = {}, main = false, allExports = false} = {}) {
  const url = new URL(`../src/${name}`, import.meta.url);
  let source = readFileSync(url, 'utf8').replace(/^import ['"][^'"]+\.css['"];?\s*$/gm, '');
  source = source.replace("import('./PackagingDetail.jsx')", '__deps.loadDetail()')
    .replace("import('./packaging-scene.js')", '__deps.loadScene()');
  if (main) source = source.replace(/createRoot\(document\.getElementById\('root'\)\)\.render\(<App\/>\);/, 'export {App};');
  const {code} = transformSync(source, {loader: 'jsx', format: 'cjs', jsx: 'transform',
    define: {'import.meta.env.MODE': '"test"', 'import.meta.env.BASE_URL': '"/"'}});
  const module = {exports: {}}, localRequire = createRequire(url);
  new Function('require', 'module', 'exports', '__deps', code)(id => id in mocks ? mocks[id] : localRequire(id), module, module.exports, {loadScene: async () => ({}), ...deps});
  return allExports ? module.exports : main ? module.exports.App : module.exports.default;
}
function deferred() {
  let resolve, reject;
  const promise = new Promise((yes, no) => {resolve = yes; reject = no;});
  return {promise, resolve, reject};
}
function setup({reduced = true} = {}) {
  const dom = new JSDOM('<div id="root"></div>', {url: 'http://localhost/', pretendToBeVisual: true});
  const media = {matches: reduced, addEventListener() {}, removeEventListener() {}};
  const frames = new Map(); let id = 0;
  const originalFetch = globalThis.fetch;
  globalThis.fetch = async () => ({ok: true, arrayBuffer: async () => new ArrayBuffer(12)});
  Object.assign(globalThis, {window: dom.window, document: dom.window.document, IS_REACT_ACT_ENVIRONMENT: true,
    matchMedia: () => media, requestAnimationFrame: fn => {frames.set(++id, fn); return id;},
    cancelAnimationFrame: key => frames.delete(key)});
  window.matchMedia = () => media;
  window.scrollTo = () => {};
  window.HTMLElement.prototype.scrollTo = function(options) {this.scrollTop = options?.top || 0;};
  window.HTMLDialogElement.prototype.showModal = function() {
    if (!this.open) {this.open = true; this.querySelector('button')?.focus();}
  };
  window.HTMLDialogElement.prototype.close = function() {this.open = false;};
  const root = createRoot(document.getElementById('root'));
  return {root, dom, frames, async close() {await act(async () => root.unmount()); dom.window.close(); globalThis.fetch = originalFetch;}};
}
const item = {id: 'poster-012', title: {zh: 'Beach Magic 原海报', en: 'Beach Magic poster'}, image: '/poster-012.webp', original: '/poster-012-original.webp'};
const defaultProps = {item, lang: 'zh', logo: '/logo.webp', saved: false, onClose() {}, onOriginal() {}, onFavorite() {}};
const byText = text => [...document.querySelectorAll('button')].find(button => button.textContent.trim() === text);
const click = async node => {assert.ok(node, 'expected an actionable button'); await act(async () => node.click());};

test('lazy detail loading keeps original and close available, and a late module cannot mount after close', async () => {
  const env = setup(), pending = deferred(); let loads = 0, mounts = 0, originals = 0, closes = 0;
  const Loader = component('structure/PackagingDetailLoader.jsx', {deps: {loadDetail: () => {loads++; return pending.promise;}}});
  function Detail() {useEffect(() => {mounts++;}, []); return <div>Loaded detail</div>;}
  try {
    await act(async () => env.root.render(<Loader {...defaultProps} onOriginal={() => originals++} onClose={() => closes++}/>));
    assert.equal(loads, 1); assert.equal(document.querySelector('.packaging-shell').getAttribute('aria-busy'), 'true');
    await click(byText('查看原海报')); await click(byText('返回产品'));
    assert.equal(originals, 1); assert.equal(closes, 1);
    await act(async () => env.root.render(<div>Collection</div>));
    await act(async () => pending.resolve({default: Detail}));
    assert.equal(mounts, 0); assert.equal(document.querySelector('.packaging-shell'), null);
    assert.equal(document.getElementById('root').textContent, 'Collection');
  } finally {await env.close();}
});

test('chunk failure shows retry and original-poster escape; retry forwards current product and favorite props', async () => {
  const env = setup(); let loads = 0, originals = 0, favorites = 0, received;
  function Detail(props) {received = props; return <button onClick={props.onFavorite}>Detail favorite</button>;}
  const Loader = component('structure/PackagingDetailLoader.jsx', {deps: {loadDetail: () => ++loads === 1 ? Promise.reject(new Error('Network')) : Promise.resolve({default: Detail})}});
  try {
    await act(async () => env.root.render(<Loader {...defaultProps} saved onOriginal={() => originals++} onFavorite={() => favorites++}/>));
    assert.match(document.querySelector('[role="status"]').textContent, /暂时无法加载/);
    assert.equal(document.querySelector('.packaging-shell').getAttribute('aria-busy'), 'false');
    await click(byText('查看原海报')); assert.equal(originals, 1);
    await click(byText('重新加载'));
    assert.equal(loads, 2); assert.equal(received.item, item); assert.equal(received.saved, true);
    await click(byText('Detail favorite')); assert.equal(favorites, 1);
  } finally {await env.close();}
});

test('scene failure keeps the real poster, favorite and close controls usable and allows another loading attempt', async () => {
  const env = setup(), priorError = console.error; let mounts = 0, originals = 0, favorites = 0, closes = 0;
  console.error = () => {};
  const Detail = component('structure/PackagingDetail.jsx', {deps: {loadScene: async () => ({mountPackagingScene: async () => {mounts++; throw new Error('WebGL unavailable');}})}});
  try {
    await act(async () => env.root.render(<Detail {...defaultProps} onOriginal={() => originals++} onFavorite={() => favorites++} onClose={() => closes++}/>));
    assert.equal(document.activeElement, document.querySelector('.packaging-back'), 'the lazy-loaded detail moves focus into its own controls');
    assert.match(document.querySelector('.packaging-error').textContent, /模型暂时无法显示/);
    assert.equal(document.querySelector('.packaging-error img').getAttribute('src'), item.image);
    assert.equal(document.querySelector('#packaging-opening').disabled, true);
    await click(document.querySelector('.packaging-header [aria-label="查看原海报"]'));
    await click(document.querySelector('[aria-label="收藏产品"]'));
    await click(document.querySelector('.packaging-back'));
    assert.deepEqual([originals, favorites, closes], [1, 1, 1]);
    await click(byText('重新加载')); assert.equal(mounts, 2);
  } finally {console.error = priorError; await env.close();}
});

test('late scene completion is disposed after leaving; mounted scenes release once and never stay attached', async () => {
  const env = setup(), pending = deferred(); let mounts = 0, disposals = 0;
  const api = {dispose() {disposals++;}, setProgress() {}, focusPart() {}, resetView() {}, rotate() {}, viewBottom() {}};
  const Detail = component('structure/PackagingDetail.jsx', {deps: {loadScene: async () => ({mountPackagingScene: async (host, {onReady}) => {mounts++; const result = await pending.promise; onReady(); return result;}})}});
  try {
    await act(async () => env.root.render(<Detail {...defaultProps}/>));
    assert.equal(mounts, 1);
    await act(async () => env.root.render(<div>Original poster</div>));
    await act(async () => pending.resolve(api));
    assert.equal(disposals, 1);
    assert.equal(document.querySelector('.packaging-detail'), null);
    assert.equal(env.frames.size, 0);
    await act(async () => env.root.render(<Detail {...defaultProps}/>));
    assert.equal(document.querySelector('#packaging-opening').disabled, false);
    await act(async () => env.root.render(<div>Collection</div>));
    assert.equal(disposals, 2); assert.equal(env.frames.size, 0);
  } finally {await env.close();}
});

test('runtime scene failure releases the renderer and switches to an original-poster fallback', async () => {
  const env = setup(), priorError = console.error; let failScene, disposals = 0;
  console.error = () => {};
  const api = {dispose() {disposals++;}, setProgress() {}, focusPart() {}, resetView() {}, rotate() {}, viewBottom() {}};
  const Detail = component('structure/PackagingDetail.jsx', {deps: {loadScene: async () => ({mountPackagingScene: async (host, {onError, onReady}) => {failScene = onError; onReady(); return api;}})}});
  try {
    await act(async () => env.root.render(<Detail {...defaultProps}/>));
    assert.equal(document.querySelector('#packaging-opening').disabled, false);
    await act(async () => failScene(new Error('Context lost')));
    assert.equal(disposals, 1); assert.ok(document.querySelector('.packaging-error'));
    assert.ok(document.querySelector('.packaging-header [aria-label="查看原海报"]'));
    await act(async () => env.root.render(<div>Collection</div>));
    assert.equal(disposals, 1, 'failure and later unmount must not release the same scene twice');
  } finally {console.error = priorError; await env.close();}
});

test('animation-script failure retains a usable 3D scene with manual stages and original-poster access', async () => {
  const env = setup({reduced: false}); let progress = -1, originals = 0;
  const append = document.head.append.bind(document.head);
  document.head.append = node => {append(node); if (node.tagName === 'SCRIPT') queueMicrotask(() => node.onerror?.());};
  const api = {dispose() {}, setProgress(value) {progress = value;}, focusPart() {}, resetView() {}, rotate() {}, viewBottom() {}};
  const Detail = component('structure/PackagingDetail.jsx', {deps: {loadScene: async () => ({mountPackagingScene: async (host, {onReady}) => {onReady(); return api;}})}});
  try {
    await act(async () => env.root.render(<Detail {...defaultProps} onOriginal={() => originals++}/>));
    assert.ok(document.querySelector('.packaging-detail--manual'));
    assert.equal(document.querySelector('.packaging-error'), null);
    assert.equal(document.querySelector('#packaging-opening').disabled, false);
    await click(byText('完全展开'));
    assert.equal(progress, 1); assert.equal(document.querySelector('#packaging-opening').value, '100');
    await click(byText('合拢')); assert.equal(progress, 0);
    await click(document.querySelector('.packaging-header [aria-label="查看原海报"]'));
    assert.equal(originals, 1);
  } finally {await env.close();}
});

test('loader starts one authenticated model request beside both modules and aborts it immediately on close', async () => {
  const env = setup(), detail = deferred(), scene = deferred(), bytes = deferred();
  let received, calls = 0, sceneCalls = 0, signal;
  globalThis.fetch = (url, options) => {
    calls++; signal = options.signal;
    assert.equal(url, '/assets/packaging/beach-magic-packaging.glb');
    assert.equal(options.credentials, 'same-origin'); assert.equal(options.cache, 'no-cache');
    signal.addEventListener('abort', () => bytes.reject(signal.reason), {once: true});
    return bytes.promise;
  };
  function Detail(props) {received = props; return <div>Detail</div>;}
  const Loader = component('structure/PackagingDetailLoader.jsx', {deps: {
    loadDetail: () => detail.promise, loadScene: () => {sceneCalls++; return scene.promise;},
  }});
  try {
    await act(async () => env.root.render(<Loader {...defaultProps}/>));
    assert.equal(calls, 1); assert.equal(sceneCalls, 1);
    await act(async () => detail.resolve({default: Detail}));
    assert.equal(received.getModelRequest(), received.getModelRequest());
    assert.equal(received.getSceneModule(), scene.promise);
    assert.equal(calls, 1); assert.equal(sceneCalls, 1, 'the prefetched scene module is reused');
    await act(async () => env.root.render(<div>Collection</div>));
    assert.equal(signal.aborted, true);
    await act(async () => scene.resolve({}));
    assert.equal(document.getElementById('root').textContent, 'Collection');
  } finally {await env.close();}
});

test('a detail module arriving after 45 seconds still mounts without retrying the model', async t => {
  const env = setup(), detail = deferred(); let mounts = 0, calls = 0, signal;
  t.mock.timers.enable({apis: ['setTimeout']});
  globalThis.fetch = async (url, options) => {
    calls++; signal = options.signal;
    return {ok: true, arrayBuffer: async () => new ArrayBuffer(12)};
  };
  function Detail() {useEffect(() => {mounts++;}, []); return <div>Loaded detail</div>;}
  const Loader = component('structure/PackagingDetailLoader.jsx', {deps: {loadDetail: () => detail.promise}});
  try {
    await act(async () => env.root.render(<Loader {...defaultProps}/>));
    await act(async () => t.mock.timers.tick(45000));
    assert.equal(signal.aborted, false); assert.equal(calls, 1);
    assert.equal(document.querySelector('.packaging-shell').getAttribute('aria-busy'), 'true');
    assert.equal(byText('重新加载'), undefined);
    await act(async () => detail.resolve({default: Detail}));
    assert.equal(mounts, 1); assert.equal(document.getElementById('root').textContent, 'Loaded detail');
    await act(async () => t.mock.timers.tick(300000));
    assert.equal(signal.aborted, false); assert.equal(calls, 1);
    assert.equal(document.getElementById('root').textContent, 'Loaded detail');
  } finally {await env.close(); t.mock.timers.reset();}
});

test('a model body arriving after 90 seconds reaches a ready scene without retry or stale deadline', async t => {
  const env = setup(), bytes = deferred(); let fetches = 0, mounts = 0, signal, sceneSignal, disposals = 0;
  t.mock.timers.enable({apis: ['setTimeout']});
  globalThis.fetch = async (url, options) => {
    fetches++; signal = options.signal;
    signal.addEventListener('abort', () => bytes.reject(signal.reason), {once: true});
    return {ok: true, arrayBuffer: () => bytes.promise};
  };
  const api = {dispose() {disposals++;}, setProgress() {}, focusPart() {}, resetView() {}, rotate() {}, viewBottom() {}};
  const scene = {mountPackagingScene: async (host, {modelRequest, signal, onReady}) => {
    mounts++; sceneSignal = signal;
    assert.equal((await modelRequest.promise).byteLength, 20);
    onReady(); return api;
  }};
  const Detail = component('structure/PackagingDetail.jsx');
  const Loader = component('structure/PackagingDetailLoader.jsx', {deps: {
    loadDetail: async () => ({default: Detail}), loadScene: async () => scene,
  }});
  try {
    await act(async () => env.root.render(<Loader {...defaultProps}/>));
    await act(async () => t.mock.timers.tick(90000));
    assert.equal(signal.aborted, false); assert.equal(sceneSignal.aborted, false);
    assert.equal(document.querySelector('.packaging-error'), null);
    assert.equal(document.querySelector('#packaging-opening').disabled, true);
    await act(async () => bytes.resolve(new ArrayBuffer(20)));
    assert.equal(document.querySelector('#packaging-opening').disabled, false);
    await act(async () => t.mock.timers.tick(300000));
    assert.equal(signal.aborted, false); assert.equal(sceneSignal.aborted, false);
    assert.equal(document.querySelector('#packaging-opening').disabled, false);
    assert.equal(fetches, 1); assert.equal(mounts, 1); assert.equal(disposals, 0);
  } finally {await env.close(); t.mock.timers.reset();}
});

test('two-minute module timeout cancels the pending model, keeps poster escape and ignores a late module', async t => {
  const env = setup(), detail = deferred(), response = deferred(); let signal;
  t.mock.timers.enable({apis: ['setTimeout']});
  globalThis.fetch = (url, options) => {
    signal = options.signal;
    signal.addEventListener('abort', () => response.reject(signal.reason), {once: true});
    return response.promise;
  };
  const Loader = component('structure/PackagingDetailLoader.jsx', {deps: {loadDetail: () => detail.promise}});
  try {
    await act(async () => env.root.render(<Loader {...defaultProps}/>));
    await act(async () => t.mock.timers.tick(119999));
    assert.equal(signal.aborted, false);
    assert.equal(document.querySelector('.packaging-shell').getAttribute('aria-busy'), 'true');
    await act(async () => t.mock.timers.tick(1));
    assert.equal(signal.aborted, true); assert.equal(signal.reason.name, 'TimeoutError');
    assert.ok(byText('重新加载')); assert.ok(byText('查看原海报'));
    await act(async () => detail.resolve({default: () => <div>Stale detail</div>}));
    assert.equal(document.getElementById('root').textContent.includes('Stale detail'), false);
  } finally {await env.close(); t.mock.timers.reset();}
});

test('five-minute model deadline aborts its own request and a later attempt can fetch fresh bytes', async t => {
  const env = setup(); t.mock.timers.enable({apis: ['setTimeout']});
  const {startPackagingModelRequest} = component('structure/PackagingDetailLoader.jsx', {allExports: true});
  let calls = 0;
  globalThis.fetch = (url, {signal}) => {
    calls++;
    return calls === 1 ? new Promise((resolve, reject) => signal.addEventListener('abort', () => reject(signal.reason), {once: true}))
      : Promise.resolve({ok: true, arrayBuffer: async () => new ArrayBuffer(20)});
  };
  try {
    const first = startPackagingModelRequest();
    await act(async () => t.mock.timers.tick(299999));
    assert.equal(first.signal.aborted, false); assert.equal(calls, 1);
    await act(async () => t.mock.timers.tick(1));
    await assert.rejects(first.promise, error => error.name === 'TimeoutError');
    assert.equal(first.signal.aborted, true); assert.equal(calls, 1, 'timeout does not retry automatically');
    const second = startPackagingModelRequest();
    assert.equal((await second.promise).byteLength, 20); assert.equal(calls, 2);
    assert.ok('fetchEnd' in second.timings); second.abort();
  } finally {await env.close(); t.mock.timers.reset();}
});

test('a rejected protected model response is never parsed or reused for another opening', async () => {
  const env = setup(); let calls = 0, bodyReads = 0;
  const {startPackagingModelRequest} = component('structure/PackagingDetailLoader.jsx', {allExports: true});
  globalThis.fetch = async () => ({ok: ++calls > 1, status: calls === 1 ? 403 : 200,
    arrayBuffer: async () => {bodyReads++; return new ArrayBuffer(16);}});
  try {
    const denied = startPackagingModelRequest();
    await assert.rejects(denied.promise, /403/); assert.equal(bodyReads, 0); denied.abort();
    const fresh = startPackagingModelRequest();
    assert.equal((await fresh.promise).byteLength, 16); assert.equal(calls, 2); assert.equal(bodyReads, 1); fresh.abort();
  } finally {await env.close();}
});

test('five-minute scene initialization deadline aborts both scene work and the prefetched request', async t => {
  const env = setup(), pending = deferred(), previousError = console.error; let signal, requestAborts = 0;
  console.error = () => {}; t.mock.timers.enable({apis: ['setTimeout']});
  const modelRequest = {mark() {}, abort() {requestAborts++;}};
  const getModelRequest = () => modelRequest;
  const Detail = component('structure/PackagingDetail.jsx', {deps: {loadScene: async () => ({mountPackagingScene: (host, options) => {
    signal = options.signal; return pending.promise;
  }})}});
  try {
    await act(async () => env.root.render(<Detail {...defaultProps} getModelRequest={getModelRequest}/>));
    await act(async () => t.mock.timers.tick(299999));
    assert.equal(signal.aborted, false); assert.equal(requestAborts, 0);
    assert.equal(document.querySelector('.packaging-error'), null);
    await act(async () => t.mock.timers.tick(1));
    assert.equal(signal.aborted, true); assert.equal(signal.reason.name, 'TimeoutError'); assert.equal(requestAborts, 1);
    assert.ok(document.querySelector('.packaging-error')); assert.ok(byText('重新加载'));
    let disposed = 0; await act(async () => pending.resolve({dispose() {disposed++;}}));
    assert.equal(disposed, 1); assert.equal(document.querySelector('#packaging-opening').disabled, true);
  } finally {await env.close(); t.mock.timers.reset(); console.error = previousError;}
});

test('pending animation never blocks the scene, and late animation preserves a manual stage with a full 0-to-1 range', async () => {
  const env = setup({reduced: false}); let mountCount = 0, onReady, progress = -1, clock, config, reverted = 0;
  const api = {dispose() {}, setProgress(value) {progress = value;}, focusPart() {}, resetView() {}, rotate() {}, viewBottom() {}};
  const Detail = component('structure/PackagingDetail.jsx', {deps: {loadScene: async () => ({mountPackagingScene: async (host, options) => {
    mountCount++; onReady = options.onReady; return api;
  }})}});
  const trigger = {start: 0, end: 1000, refresh() {config.scrollTrigger.onRefreshInit(); config.scrollTrigger.onRefresh(trigger);},
    update() {}, getTween: () => null, animation: {progress(value) {clock.progress = value; config.onUpdate();}}};
  try {
    await act(async () => env.root.render(<Detail {...defaultProps}/>));
    assert.equal(mountCount, 1, 'scene starts while the animation request remains pending');
    assert.equal(document.querySelector('#packaging-opening').disabled, true, 'mount resolution alone is not a first frame');
    await act(async () => onReady());
    await click(byText('半展开')); assert.equal(progress, .5);
    const core = document.querySelector('script[src$="gsap.min.js"]'); assert.ok(core);
    window.gsap = {registerPlugin() {}, context(run) {run(); return {revert() {reverted++;}};},
      to(value, options) {clock = value; config = options; assert.equal(clock.progress, 0); assert.equal(options.progress, 1); return {scrollTrigger: trigger};}};
    await act(async () => core.onload());
    const plugin = document.querySelector('script[src$="ScrollTrigger.min.js"]'); assert.ok(plugin);
    window.ScrollTrigger = {};
    await act(async () => plugin.onload());
    await act(async () => {const callbacks = [...env.frames.values()]; env.frames.clear(); callbacks.forEach(fn => fn());});
    assert.equal(progress, .5); assert.equal(document.querySelector('.packaging-scroll').scrollTop, 500);
    await act(async () => {clock.progress = 0; config.onUpdate();}); assert.equal(progress, 0);
    await act(async () => {clock.progress = 1; config.onUpdate();}); assert.equal(progress, 1);
  } finally {await env.close(); assert.equal(reverted, 1);}
});

test('animation timeout enters manual mode and a later opening retries its script', async t => {
  const env = setup({reduced: false}); t.mock.timers.enable({apis: ['setTimeout']});
  const api = {dispose() {}, setProgress() {}, focusPart() {}, resetView() {}, rotate() {}, viewBottom() {}};
  const Detail = component('structure/PackagingDetail.jsx', {deps: {loadScene: async () => ({mountPackagingScene: async (host, {onReady}) => {onReady(); return api;}})}});
  try {
    await act(async () => env.root.render(<Detail {...defaultProps}/>));
    const first = document.querySelector('script[src$="gsap.min.js"]'); assert.ok(first);
    assert.equal(document.querySelector('#packaging-opening').disabled, false);
    await act(async () => t.mock.timers.tick(15000));
    assert.ok(document.querySelector('.packaging-detail--manual')); assert.equal(first.isConnected, false);
    assert.equal(first.onload, null); assert.equal(first.onerror, null);
    await act(async () => env.root.render(<div>Collection</div>));
    await act(async () => env.root.render(<Detail {...defaultProps}/>));
    const second = document.querySelector('script[src$="gsap.min.js"]'); assert.ok(second); assert.notEqual(second, first);
  } finally {await env.close(); t.mock.timers.reset();}
});

function appHarness({loader} = {}) {
  let mounts = 0, unmounts = 0;
  function Showcase(props) {return <div data-testid="showcase" data-selected={props.selectedId} data-modal={String(props.modalOpen)}>
    {props.items.map(p => <button key={p.id} data-open={p.id} onClick={() => {props.onSelect(p.id); props.onOpen(p);}}>{p.id}</button>)}
    <button data-testid="browse-all" onClick={props.onBrowse}>Browse all</button>
    <button data-testid="favorite-other" onClick={() => props.onFavorite('poster-013')}>Favorite other</button>
    <span data-testid="favorites">{props.favorites.join(',')}</span>
  </div>;}
  function Detail(props) {
    useEffect(() => {mounts++; return () => {unmounts++;};}, []);
    return <div className="test-packaging" data-id={props.item.id}>
      <button onClick={props.onClose}>Close structure</button>
      <button onClick={props.onOriginal}>Original poster</button>
      <button onClick={props.onFavorite} aria-pressed={props.saved}>Save structure</button>
    </div>;
  }
  const App = component('main.jsx', {main: true, mocks: {'./FeaturedShowcase.jsx': Showcase, './structure/PackagingDetailLoader.jsx': loader || Detail}});
  return {App, counts: () => ({mounts, unmounts})};
}

test('the real App loads a model only after opening one of the featured products', async () => {
  const env = setup(); let requests = 0, details = 0, scenes = 0;
  globalThis.fetch = async () => {requests++; return {ok: true, arrayBuffer: async () => new ArrayBuffer(12)};};
  const Loader = component('structure/PackagingDetailLoader.jsx', {deps: {
    loadDetail: async () => {details++; return {default: () => <div>Beach detail</div>};},
    loadScene: async () => {scenes++; return {};},
  }});
  const {App} = appHarness({loader: Loader});
  try {
    await act(async () => env.root.render(<App/>));
    assert.deepEqual([requests, details, scenes], [0, 0, 0]);
    await click(document.querySelector('[data-open="poster-013"]'));
    assert.deepEqual([requests, details, scenes], [1, 1, 1]);
  } finally {await env.close();}
});

test('App opens featured models and preserves poster HD/download/favorites and return focus', async () => {
  const env = setup();
  const {App, counts} = appHarness();
  try {
    await act(async () => env.root.render(<App/>));
    assert.equal(document.querySelectorAll('[data-open]').length, 24);
    assert.equal(counts().mounts, 0, 'collection first paint must not mount the 3D detail');
    const other = document.querySelector('[data-open="poster-013"]'); other.focus(); await click(other);
    assert.equal(document.querySelector('.test-packaging').dataset.id, 'poster-013');
    await click(byText('Original poster'));
    assert.equal(document.querySelector('.test-packaging'), null);
    assert.ok(document.querySelector('dialog.image-modal'));
    const download = document.querySelector('a[download="poster-013.webp"]'); assert.ok(download);
    await click(byText('查看高清原图'));
    const img = document.querySelector('.lightbox-image img');
    assert.equal(img.getAttribute('src'), download.getAttribute('href'));
    img.decode = () => Promise.resolve(); await act(async () => img.dispatchEvent(new window.Event('load')));
    assert.equal(byText('已加载原图').disabled, true);
    await click(document.querySelector('[aria-label="关闭"]'));
    assert.equal(document.activeElement, other); assert.equal(document.querySelector('dialog').open, false);
    await click(document.querySelector('[data-testid="favorite-other"]'));
    assert.match(document.querySelector('[data-testid="favorites"]').textContent, /poster-013/);
    assert.ok(Object.values(window.localStorage).some(value => value.includes('poster-013')));
    const beach = document.querySelector('[data-open="poster-012"]'); beach.focus(); await click(beach);
    assert.equal(document.querySelector('.test-packaging').dataset.id, 'poster-012');
    assert.equal(document.activeElement, byText('Close structure'));
    assert.equal(document.querySelector('[data-testid="showcase"]').dataset.modal, 'true');
    await click(byText('Save structure'));
    assert.equal(byText('Save structure').getAttribute('aria-pressed'), 'true');
    assert.match(document.querySelector('[data-testid="favorites"]').textContent, /poster-013/);
    await act(async () => document.querySelector('dialog').dispatchEvent(new window.Event('cancel', {bubbles: true, cancelable: true})));
    assert.equal(document.querySelector('.test-packaging'), null);
    assert.equal(document.activeElement, beach);
    assert.equal(document.querySelector('[data-testid="showcase"]').dataset.selected, 'poster-012');
    assert.equal(document.querySelector('[data-testid="showcase"]').dataset.modal, 'false');
    assert.deepEqual(counts(), {mounts: 2, unmounts: 2});
  } finally {await env.close();}
});

test('App original-poster round trip unmounts 3D and resets HD status without losing product or favorite state', async () => {
  const env = setup();
  const {App, counts} = appHarness();
  try {
    await act(async () => env.root.render(<App/>));
    const beach = document.querySelector('[data-open="poster-012"]'); beach.focus(); await click(beach);
    await click(byText('Save structure')); await click(byText('Original poster'));
    assert.equal(document.querySelector('.test-packaging'), null); assert.equal(counts().unmounts, 1);
    assert.equal(document.activeElement, byText('返回结构展示'), 'switching an open dialog to the poster preserves keyboard focus inside it');
    assert.ok(document.querySelector('a[download="poster-012.webp"]'));
    await click(byText('查看高清原图'));
    let img = document.querySelector('.lightbox-image img'); img.decode = () => Promise.resolve();
    await act(async () => img.dispatchEvent(new window.Event('load')));
    assert.equal(byText('已加载原图').disabled, true);
    await click(byText('返回结构展示'));
    assert.equal(document.querySelector('.test-packaging').dataset.id, 'poster-012');
    assert.equal(document.activeElement, byText('Close structure'), 'returning to structure focuses its first control');
    assert.equal(byText('Save structure').getAttribute('aria-pressed'), 'true');
    await click(byText('Original poster'));
    assert.equal(byText('查看高清原图').disabled, false);
    assert.equal(byText('已加载原图'), undefined);
    await click(document.querySelector('[aria-label="关闭"]'));
    assert.equal(document.activeElement, beach);
    assert.deepEqual(counts(), {mounts: 2, unmounts: 2});
  } finally {await env.close();}
});

test('pump fetches its own model and has five separate layers with its own heading', async () => {
  const env = setup(); let url, mounted;
  const pump = {...item,id:'poster-071',title:{zh:'长颈泵瓶',en:'Sculptural Pump'}};
  globalThis.fetch = async value => {url=value; return {ok:true,arrayBuffer:async()=>new ArrayBuffer(12)};};
  const {startPackagingModelRequest} = component('structure/PackagingDetailLoader.jsx',{allExports:true});
  const api = {setProgress(){},dispose(){}};
  const Detail = component('structure/PackagingDetail.jsx',{deps:{loadScene:async()=>({mountPackagingScene:async(host,options)=>{mounted=options;options.onReady();return api;}})}});
  try {
    const request=startPackagingModelRequest(pump.id); await request.promise; request.abort();
    assert.equal(url,'/assets/packaging/liaose-pump.glb');
    assert.throws(()=>startPackagingModelRequest('../../private'),/Unsupported/);
    await act(async()=>env.root.render(<Detail {...defaultProps} item={pump}/>));
    assert.match(document.querySelector('h1').textContent,/Sculptural Pump/);
    assert.deepEqual(mounted.product.parts.map(p=>p.node),['PumpHead','PumpStem','Closure','BottleAssembly','LogoPrint']);
    assert.equal(document.querySelectorAll('.packaging-part').length,5);
  } finally {await env.close();}
});

test('Moisture Shampoo exposes one complete pump and four independent layer controls', async () => {
  const env=setup();let mounted,focused,url;
  const moisture={...item,id:'poster-049',title:{zh:'保湿洗发露',en:'Moisture Shampoo'}};
  globalThis.fetch=async value=>{url=value;return {ok:true,arrayBuffer:async()=>new ArrayBuffer(12)};};
  const {startPackagingModelRequest}=component('structure/PackagingDetailLoader.jsx',{allExports:true});
  const Detail=component('structure/PackagingDetail.jsx',{deps:{loadScene:async()=>({mountPackagingScene:async(host,options)=>{
    mounted=options;options.onReady();return {setProgress(){},focusPart(key){focused=key;},dispose(){}};
  }})}});
  try {
    const request=startPackagingModelRequest(moisture.id);await request.promise;request.abort();
    assert.equal(url,'/assets/packaging/poster-049.glb');
    await act(async()=>env.root.render(<Detail {...defaultProps} item={moisture}/>));
    assert.equal(document.querySelector('h1').textContent,'Moisture Shampoo');
    assert.deepEqual(mounted.product.parts.map(p=>p.node),['PumpAssembly','Body','PaperLabel','LogoPrint']);
    assert.deepEqual(mounted.product.parts.map(p=>p.key),['pump','jar','label','print']);
    assert.equal(mounted.product.review,undefined,'the established material branch remains in use');
    for(const selector of ['.packaging-part','.packaging-mobile-parts button']) {
      const buttons=[...document.querySelectorAll(selector)];
      assert.equal(buttons.length,4);
      for(const [i,key] of ['pump','jar','label','print'].entries()) {
        await click(buttons[i]);assert.equal(focused,key);
      }
    }
  } finally {await env.close();}
});

test('Woodland keeps ivory print readable against its separate warm studio and exposes its complete cap and four layers', async () => {
  const env=setup(); let mounted,focused;
  const Detail=component('structure/PackagingDetail.jsx',{deps:{loadScene:async()=>({mountPackagingScene:async(host,options)=>{mounted=options;options.onReady();return {setProgress(){},focusPart(key){focused=key;},dispose(){}};}})}});
  try {
    await act(async()=>env.root.render(<Detail {...defaultProps} item={{...item,id:'poster-042'}}/>));
    assert.deepEqual(mounted.product.parts.map(p=>p.node),['CapAssembly','Body','PaperLabel','LogoPrint']);
    assert.deepEqual(mounted.product.parts.map(p=>p.key),['closure','jar','label','print']);
    for(const selector of ['.packaging-part','.packaging-mobile-parts button']) {
      const buttons=[...document.querySelectorAll(selector)];
      assert.equal(buttons.length,4);
      for(const [i,key] of ['closure','jar','label','print'].entries()) {
        await click(buttons[i]);assert.equal(focused,key);
      }
    }
    const luminance=hex=>{const c=hex.match(/[a-f\d]{2}/gi).map(v=>parseInt(v,16)/255).map(v=>v<=.04045?v/12.92:((v+.055)/1.055)**2.4);return c[0]*.2126+c[1]*.7152+c[2]*.0722;};
    assert.ok((luminance('#ede7dc')+.05)/(luminance(mounted.design.background)+.05)>4.5,'original ivory lettering must remain visible away from the black substrate');
    assert.equal(document.querySelector('.packaging-detail').style.getPropertyValue('--pack-paper'),mounted.design.background);
  } finally {await env.close();}
});

test('Pure Volume exposes the complete pump, bottle with cord, clear label and full print', async () => {
  const env=setup(); let mounted,focused;
  const Detail=component('structure/PackagingDetail.jsx',{deps:{loadScene:async()=>({mountPackagingScene:async(host,options)=>{mounted=options;options.onReady();return {setProgress(){},focusPart(key){focused=key;},dispose(){}};}})}});
  try {
    await act(async()=>env.root.render(<Detail {...defaultProps} item={{...item,id:'poster-051'}}/>));
    assert.deepEqual(mounted.product.parts.map(p=>p.node),['PumpAssembly','BottleAssembly','PaperLabel','LogoPrint']);
    assert.deepEqual(mounted.product.parts.map(p=>p.key),['pump','jar','label','print']);
    for(const selector of ['.packaging-part','.packaging-mobile-parts button']) {
      const buttons=[...document.querySelectorAll(selector)];
      assert.equal(buttons.length,4);
      for(const [i,key] of ['pump','jar','label','print'].entries()) {
        await click(buttons[i]);assert.equal(focused,key);
      }
    }
    assert.equal(mounted.product.parts.some(part=>['head','stem','closure','cord'].includes(part.key)),false);
    assert.match(document.querySelector('h1').textContent,/Pure Volume/);
    assert.equal(document.querySelector('.packaging-detail').style.getPropertyValue('--pack-paper'),'#dce4cf');
  } finally {await env.close();}
});

test('Gentle Cleansing exposes its cover, complete pump, frosted oval and printing independently', async () => {
  const env=setup(); let mounted,focused;
  const Detail=component('structure/PackagingDetail.jsx',{deps:{loadScene:async()=>({mountPackagingScene:async(host,options)=>{mounted=options;options.onReady();return {setProgress(){},focusPart(key){focused=key;},dispose(){}};}})}});
  try {
    await act(async()=>env.root.render(<Detail {...defaultProps} item={{...item,id:'poster-044'}}/>));
    assert.equal(document.querySelectorAll('.packaging-part').length,5);
    assert.equal(document.querySelectorAll('.packaging-mobile-parts button').length,5);
    assert.deepEqual(mounted.product.parts.map(p=>p.node),['Overcap','PumpAssembly','Body','PaperLabel','LogoPrint']);
    assert.equal(mounted.product.parts.some(part=>['head','stem','closure'].includes(part.key)),false);
    await click(document.querySelectorAll('.packaging-mobile-parts button')[1]);assert.equal(focused,'pump');
    await click(document.querySelectorAll('.packaging-mobile-parts button')[3]);assert.equal(focused,'label');
    assert.match(document.querySelector('h1').textContent,/Gentle Cleansing/);
    assert.equal(document.querySelector('.packaging-detail').style.getPropertyValue('--pack-paper'),'#e8d6d3');
  } finally {await env.close();}
});


test('Coastal exposes the cork, glass, paper and complete lettering independently', async () => {
  const env=setup(); let mounted,focused;
  const Detail=component('structure/PackagingDetail.jsx',{deps:{loadScene:async()=>({mountPackagingScene:async(host,options)=>{mounted=options;options.onReady();return {setProgress(){},focusPart(key){focused=key;},dispose(){}};}})}});
  try {
    await act(async()=>env.root.render(<Detail {...defaultProps} item={{...item,id:'poster-047'}}/>));
    assert.equal(document.querySelectorAll('.packaging-part').length,4);
    assert.equal(document.querySelectorAll('.packaging-mobile-parts button').length,4);
    assert.deepEqual(mounted.product.parts.map(p=>p.node),['Closure','Body','PaperLabel','LogoPrint']);
    await click(document.querySelectorAll('.packaging-mobile-parts button')[2]);assert.equal(focused,'label');
    assert.match(document.querySelector('h1').textContent,/Coastal/);
  } finally {await env.close();}
});


test('Golden Face Oil exposes the long cover, complete pump, clear film and lettering independently', async () => {
  const env=setup();let mounted,focused;
  const Detail=component('structure/PackagingDetail.jsx',{deps:{loadScene:async()=>({mountPackagingScene:async(host,options)=>{mounted=options;options.onReady();return {setProgress(){},focusPart(key){focused=key;},dispose(){}};}})}});
  try {
    await act(async()=>env.root.render(<Detail {...defaultProps} item={{...item,id:'poster-056'}}/>));
    assert.equal(document.querySelectorAll('.packaging-part').length,5);
    assert.equal(document.querySelectorAll('.packaging-mobile-parts button').length,5);
    assert.deepEqual(mounted.product.parts.map(p=>p.node),['Overcap','PumpAssembly','Body','PaperLabel','LogoPrint']);
    assert.equal(mounted.product.parts.some(part=>['head','stem','closure'].includes(part.key)),false);
    await click(document.querySelectorAll('.packaging-mobile-parts button')[1]);assert.equal(focused,'pump');
    await click(document.querySelectorAll('.packaging-mobile-parts button')[3]);assert.equal(focused,'label');
    assert.match(document.querySelector('h1').textContent,/Golden Face Oil/);
  } finally {await env.close();}
});


test('B5 Serum exposes the separate white base and keeps white lettering readable', async () => {
  const env=setup();let mounted,focused;
  const Detail=component('structure/PackagingDetail.jsx',{deps:{loadScene:async()=>({mountPackagingScene:async(host,options)=>{mounted=options;options.onReady();return {setProgress(){},focusPart(key){focused=key;},dispose(){}};}})}});
  try {
    await act(async()=>env.root.render(<Detail {...defaultProps} item={{...item,id:'poster-057'}}/>));
    assert.equal(document.querySelectorAll('.packaging-part').length,7);assert.equal(document.querySelectorAll('.packaging-mobile-parts button').length,7);
    assert.deepEqual(mounted.product.parts.map(p=>p.node),['DropperBulb','Pipette','Closure','Body','Base','PaperLabel','LogoPrint']);
    await click(document.querySelectorAll('.packaging-mobile-parts button')[4]);assert.equal(focused,'base');
    assert.match(document.querySelector('h1').textContent,/B5/);
    const c=mounted.design.background.match(/[a-f\d]{2}/gi).map(v=>parseInt(v,16)/255).map(v=>v<=.04045?v/12.92:((v+.055)/1.055)**2.4);
    assert.ok(1.05/(c[0]*.2126+c[1]*.7152+c[2]*.0722+.05)>4.5,'original white printing must remain legible away from the bottle');
  } finally {await env.close();}
});


test('Body Oil opens from the poster library without joining featured and returns from the original poster', async () => {
  const env=setup(); const {App,counts}=appHarness();
  try {
    await act(async()=>env.root.render(<App/>));
    assert.equal(document.querySelectorAll('[data-open]').length,24);
    assert.equal(document.querySelector('[data-open="poster-073"]'),null);
    await click(document.querySelector('[data-testid="browse-all"]'));
    await click(document.querySelector('.view-toggle button:nth-child(2)'));
    assert.equal(document.querySelectorAll('.grid-image').length,61);
    const trigger=[...document.querySelectorAll('.grid-image')].find(button=>button.querySelector('img')?.getAttribute('src').includes('poster-073'));
    trigger.focus(); await click(trigger);
    assert.equal(document.querySelector('.test-packaging').dataset.id,'poster-073');
    await click(byText('Save structure'));
    await click(byText('Original poster'));
    assert.equal(document.querySelector('.test-packaging'),null);
    assert.ok(document.querySelector('a[download="poster-073.webp"]'));
    assert.equal(document.activeElement,byText('返回结构展示'));
    await click(byText('返回结构展示'));
    assert.equal(document.querySelector('.test-packaging').dataset.id,'poster-073');
    assert.equal(byText('Save structure').getAttribute('aria-pressed'),'true');
    await click(byText('Close structure'));
    assert.equal(document.activeElement,trigger);
    assert.deepEqual(counts(),{mounts:2,unmounts:2});
  } finally {await env.close();}
});

test('non-featured Body Oil uses its complete design fallback and all five independent controls', async () => {
  const env=setup(); let mounted,focused,url;
  const bodyOil={...item,id:'poster-073',title:{zh:'身体油系列',en:'Body Oil Collection'}};
  globalThis.fetch=async value=>{url=value;return {ok:true,arrayBuffer:async()=>new ArrayBuffer(12)};};
  const {startPackagingModelRequest}=component('structure/PackagingDetailLoader.jsx',{allExports:true});
  const Detail=component('structure/PackagingDetail.jsx',{deps:{loadScene:async()=>({mountPackagingScene:async(host,options)=>{
    mounted=options; options.onReady(); return {setProgress(){},focusPart(key){focused=key;},dispose(){}};
  }})}});
  try {
    assert.equal(JSON.parse(readFileSync(new URL('../src/featured.json',import.meta.url),'utf8')).some(p=>p.id==='poster-073'),false);
    const request=startPackagingModelRequest(bodyOil.id);await request.promise;request.abort();
    assert.equal(url,'/assets/packaging/poster-073.glb');
    await act(async()=>env.root.render(<Detail {...defaultProps} item={bodyOil}/>));
    assert.equal(document.querySelector('h1').textContent,'Body Oil Collection');
    assert.equal(document.querySelector('.packaging-intro').textContent,'身体护理 · 单瓶身体油空包材');
    assert.deepEqual(mounted.product.parts.map(p=>p.node),['Closure','Body','PaperLabel','LogoPrint','ProductPrint']);
    assert.equal(document.querySelectorAll('.packaging-part').length,5);
    assert.equal(document.querySelectorAll('.packaging-mobile-parts button').length,5);
    assert.equal(document.querySelector('.packaging-detail').style.getPropertyValue('--pack-paper'),'#eadbc5');
    assert.equal(document.querySelector('.packaging-detail').style.getPropertyValue('--pack-ink'),'#3e2b1d');
    assert.equal(document.querySelector('.packaging-detail').style.getPropertyValue('--pack-accent'),'#eee3d1');
    assert.equal(Object.hasOwn(mounted.product.review.appearance,'liquid'),false);
    await click(document.querySelectorAll('.packaging-mobile-parts button')[4]);
    assert.equal(focused,'name');
    await act(async()=>env.root.render(<Detail {...defaultProps} item={bodyOil} lang="en"/>));
    const english=document.querySelector('.packaging-intro').textContent;
    assert.equal(english,mounted.design.kind.en);
    assert.ok(/[A-Za-z]/.test(english));
    assert.equal(document.querySelector('h1').textContent,'Body Oil Collection');
  } finally {await env.close();}
});

test('a non-featured design retains its title and copy when appearance supplies studio colours', async () => {
  const env=setup();let mounted;
  const collection=JSON.parse(readFileSync(new URL('../src/structure/collection-products.json',import.meta.url),'utf8'));
  const original=collection['poster-073'];
  const product={...original,review:{...original.review,appearance:{...original.review.appearance,studio:{background:'#786047',ink:'#fff2db'}}}};
  const Detail=component('structure/PackagingDetail.jsx',{
    mocks:{'./packaging-products.js':{PACKAGING_PRODUCTS:{'poster-073':product}}},
    deps:{loadScene:async()=>({mountPackagingScene:async(host,options)=>{mounted=options;options.onReady();return {setProgress(){},dispose(){}};}})}
  });
  try {
    await act(async()=>env.root.render(<Detail {...defaultProps} item={{...item,id:'poster-073'}}/>));
    assert.equal(document.querySelector('h1').textContent,'Body Oil Collection');
    assert.equal(document.querySelector('.packaging-intro').textContent,original.design.kind.zh);
    assert.equal(mounted.design.background,'#786047');
    assert.equal(mounted.design.ink,'#fff2db');
    assert.deepEqual(mounted.design.swatch,['#eee3d1','#25180f']);
    assert.equal(document.querySelector('.packaging-detail').style.getPropertyValue('--pack-paper'),'#786047');
    assert.equal(document.querySelector('.packaging-detail').style.getPropertyValue('--pack-ink'),'#fff2db');
  } finally {await env.close();}
});

test('Daily Emulsion opens from the unchanged poster library and returns from its original poster', async () => {
  const env=setup();const {App,counts}=appHarness();
  try {
    await act(async()=>env.root.render(<App/>));
    assert.equal(document.querySelectorAll('[data-open]').length,24);
    assert.equal(document.querySelector('[data-open="poster-072"]'),null);
    await click(document.querySelector('[data-testid="browse-all"]'));
    await click(document.querySelector('.view-toggle button:nth-child(2)'));
    assert.equal(document.querySelectorAll('.grid-image').length,61);
    const trigger=[...document.querySelectorAll('.grid-image')].find(button=>button.querySelector('img')?.getAttribute('src').includes('poster-072'));
    trigger.focus();await click(trigger);
    assert.equal(document.querySelector('.test-packaging').dataset.id,'poster-072');
    await click(byText('Save structure'));await click(byText('Original poster'));
    assert.equal(document.querySelector('.test-packaging'),null);
    assert.ok(document.querySelector('a[download="poster-072.webp"]'));
    await click(byText('返回结构展示'));
    assert.equal(document.querySelector('.test-packaging').dataset.id,'poster-072');
    assert.equal(byText('Save structure').getAttribute('aria-pressed'),'true');
    await click(byText('Close structure'));assert.equal(document.activeElement,trigger);
    assert.deepEqual(counts(),{mounts:2,unmounts:2});
  } finally {await env.close();}
});

test('Daily Emulsion exposes one complete pump and all six independent layer controls', async () => {
  const env=setup();let mounted,focused,url;
  const daily={...item,id:'poster-072',title:{zh:'日常乳液',en:'Daily Emulsion'}};
  globalThis.fetch=async value=>{url=value;return {ok:true,arrayBuffer:async()=>new ArrayBuffer(12)};};
  const {startPackagingModelRequest}=component('structure/PackagingDetailLoader.jsx',{allExports:true});
  const Detail=component('structure/PackagingDetail.jsx',{deps:{loadScene:async()=>({mountPackagingScene:async(host,options)=>{
    mounted=options;options.onReady();return {setProgress(){},focusPart(key){focused=key;},dispose(){}};
  }})}});
  try {
    const request=startPackagingModelRequest(daily.id);await request.promise;request.abort();
    assert.equal(url,'/assets/packaging/poster-072.glb');
    await act(async()=>env.root.render(<Detail {...defaultProps} item={daily}/>));
    assert.equal(document.querySelector('h1').textContent,'Daily Emulsion');
    assert.equal(document.querySelector('.packaging-intro').textContent,'面部护理 · 单瓶乳液空包材');
    assert.deepEqual(mounted.product.parts.map(p=>p.node),['Overcap','PumpAssembly','Body','PaperLabel','LogoPrint','ProductPrint']);
    assert.equal(document.querySelectorAll('.packaging-part').length,6);
    assert.equal(document.querySelectorAll('.packaging-mobile-parts button').length,6);
    assert.equal(mounted.product.parts.some(p=>['head','stem','closure'].includes(p.key)),false);
    assert.equal(mounted.product.review.appearance.clearOvercap,true);
    assert.equal(document.querySelector('.packaging-detail').style.getPropertyValue('--pack-paper'),'#e9e5d8');
    assert.equal(document.querySelector('.packaging-detail').style.getPropertyValue('--pack-ink'),'#34372e');
    assert.equal(document.querySelector('.packaging-detail').style.getPropertyValue('--pack-accent'),'#efeee6');
    await click(document.querySelectorAll('.packaging-mobile-parts button')[1]);assert.equal(focused,'pump');
    await click(document.querySelectorAll('.packaging-mobile-parts button')[5]);assert.equal(focused,'name');
    await act(async()=>env.root.render(<Detail {...defaultProps} item={daily} lang="en"/>));
    assert.equal(document.querySelector('.packaging-intro').textContent,'Face care · empty emulsion bottle');
    assert.equal(document.querySelector('h1').textContent,'Daily Emulsion');
  } finally {await env.close();}
});

test('all seven added posters stay outside featured and the five unapproved models stay inactive', async () => {
  const env = setup(); let requests = 0;
  globalThis.fetch = async () => {requests++; throw new Error('3D must not load');};
  const {App, counts} = appHarness();
  try {
    await act(async () => env.root.render(<App/>));
    assert.equal(document.querySelectorAll('[data-open]').length,24);
    for (let n=72;n<=78;n++) assert.equal(document.querySelector(`[data-open="poster-${String(n).padStart(3,'0')}"]`),null);
    await click(document.querySelector('[data-testid="browse-all"]'));
    await click(document.querySelector('.view-toggle button:nth-child(2)'));
    assert.equal(document.querySelectorAll('.grid-image').length,61);
    for (const n of [74,75,76,77,78]) {
      const id=`poster-${n.toString().padStart(3,'0')}`;
      const trigger=[...document.querySelectorAll(".grid-image")].find(button=>button.querySelector("img")?.getAttribute("src").includes(id));trigger.focus();await click(trigger);
      assert.equal(document.querySelector('.test-packaging'),null);
      assert.ok(document.querySelector('dialog.image-modal').open);
      assert.ok(document.querySelector(`a[download="${id}.webp"]`));
      await click(document.querySelector('[aria-label="关闭"]'));
      assert.equal(document.activeElement,trigger);
    }
    assert.deepEqual(counts(),{mounts:0,unmounts:0});
    assert.equal(requests,0);
  } finally {await env.close();}
});
