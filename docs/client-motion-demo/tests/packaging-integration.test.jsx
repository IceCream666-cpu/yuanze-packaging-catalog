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
function component(name, {deps = {}, mocks = {}, main = false} = {}) {
  const url = new URL(`../src/${name}`, import.meta.url);
  let source = readFileSync(url, 'utf8').replace(/^import ['"][^'"]+\.css['"];?\s*$/gm, '');
  source = source.replace("import('./PackagingDetail.jsx')", '__deps.loadDetail()')
    .replace("import('./packaging-scene.js')", '__deps.loadScene()');
  if (main) source = source.replace(/createRoot\(document\.getElementById\('root'\)\)\.render\(<App\/>\);/, 'export {App};');
  const {code} = transformSync(source, {loader: 'jsx', format: 'cjs', jsx: 'transform',
    define: {'import.meta.env.MODE': '"test"', 'import.meta.env.BASE_URL': '"/"'}});
  const module = {exports: {}}, localRequire = createRequire(url);
  new Function('require', 'module', 'exports', '__deps', code)(id => id in mocks ? mocks[id] : localRequire(id), module, module.exports, deps);
  return main ? module.exports.App : module.exports.default;
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
  return {root, dom, frames, async close() {await act(async () => root.unmount()); dom.window.close();}};
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
  const Detail = component('structure/PackagingDetail.jsx', {deps: {loadScene: async () => ({mountPackagingScene: () => {mounts++; return pending.promise;}})}});
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
  const Detail = component('structure/PackagingDetail.jsx', {deps: {loadScene: async () => ({mountPackagingScene: async (host, {onError}) => {failScene = onError; return api;}})}});
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
  const Detail = component('structure/PackagingDetail.jsx', {deps: {loadScene: async () => ({mountPackagingScene: async () => api})}});
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

function appHarness() {
  let mounts = 0, unmounts = 0;
  function Showcase(props) {return <div data-testid="showcase" data-selected={props.selectedId} data-modal={String(props.modalOpen)}>
    {props.items.map(p => <button key={p.id} data-open={p.id} onClick={() => {props.onSelect(p.id); props.onOpen(p);}}>{p.id}</button>)}
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
  const App = component('main.jsx', {main: true, mocks: {'./FeaturedShowcase.jsx': Showcase, './structure/PackagingDetailLoader.jsx': Detail}});
  return {App, counts: () => ({mounts, unmounts})};
}

test('App opens only Beach Magic as 3D and preserves another product HD/download/favorites and return focus', async () => {
  const env = setup();
  const {App, counts} = appHarness();
  try {
    await act(async () => env.root.render(<App/>));
    assert.equal(document.querySelectorAll('[data-open]').length, 23);
    assert.equal(counts().mounts, 0, 'collection first paint must not mount the 3D detail');
    const other = document.querySelector('[data-open="poster-013"]'); other.focus(); await click(other);
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
    assert.deepEqual(counts(), {mounts: 1, unmounts: 1});
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
