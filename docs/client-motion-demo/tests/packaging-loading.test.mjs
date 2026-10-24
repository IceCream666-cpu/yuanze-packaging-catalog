import {PACKAGING_PRODUCTS} from '../src/structure/packaging-products.js';
import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {createRequire} from 'node:module';
import {JSDOM} from 'jsdom';
import * as Three from '../src/structure/vendor/three.module.js';

const require = createRequire(import.meta.url);
const {transformSync} = createRequire(require.resolve('tsx/package.json'))('esbuild');
const source = readFileSync(new URL('../src/structure/packaging-scene.js', import.meta.url), 'utf8');
const {code} = transformSync(source, {format: 'cjs', loader: 'js'});
function deferred() {
  let resolve, reject;
  const promise = new Promise((yes, no) => {resolve = yes; reject = no;});
  return {promise, resolve, reject};
}
function harness({parse, renderError, product = PACKAGING_PRODUCTS['poster-012']} = {}) {
  const dom = new JSDOM('<div id="host"></div>', {pretendToBeVisual: true});
  const events = [], frames = new Map(); let frameId = 0, rendererDisposals = 0, envDisposals = 0, observers = 0;
  Object.assign(globalThis, {window: dom.window, document: dom.window.document,
    matchMedia: () => ({matches: true}), requestAnimationFrame: callback => {frames.set(++frameId, callback); return frameId;},
    cancelAnimationFrame: id => frames.delete(id), ResizeObserver: class {
      observe() {observers++;} disconnect() {observers--;}
    }});
  dom.window.HTMLCanvasElement.prototype.getContext = () => ({
    createRadialGradient: () => ({addColorStop() {}}), fillRect() {},
  });
  class Renderer {
    constructor() {events.push('renderer'); this.domElement = document.createElement('canvas'); this.shadowMap = {}; this.capabilities = {getMaxAnisotropy: () => 8}; this.info = {render: {calls: 1, triangles: 12}};}
    setPixelRatio() {} setClearColor() {} setSize() {}
    render() {events.push('render'); if (renderError) throw renderError;}
    dispose() {rendererDisposals++;}
  }
  class PMREM {
    fromScene() {events.push('pmrem'); return {texture: new Three.Texture(), dispose() {envDisposals++;}};}
    dispose() {}
  }
  function model() {
    const scene = new Three.Group();
    for (const name of product.parts.map(part => part.node)) {
      const part = new Three.Mesh(new Three.BoxGeometry(), new Three.MeshPhysicalMaterial());
      part.name = name; scene.add(part);
    }
    return {scene};
  }
  const module = {exports: {}};
  new Function('require', 'module', 'exports', code)(id => id.includes('packaging-products') ? {PACKAGING_PRODUCTS} : id.includes('GLTFLoader')
    ? {GLTFLoader: class {parseAsync(bytes) {events.push('parse'); return parse ? parse(bytes) : Promise.resolve(model());}}}
    : {...Three, WebGLRenderer: Renderer, PMREMGenerator: PMREM}, module, module.exports);
  const host = document.getElementById('host');
  const controller = new AbortController();
  const request = promise => ({promise, signal: controller.signal, mark: value => events.push(value)});
  return {dom, host, events, frames, controller, request, model, mount: module.exports.mountPackagingScene,
    counts: () => ({rendererDisposals, envDisposals, observers}), close: () => dom.window.close()};
}

test('scene consumes the already-started model request and reports ready only after the first render', async () => {
  const env = harness(); let ready = 0;
  try {
    const bytes = new ArrayBuffer(12);
    env.events.push('fetchStart');
    const api = await env.mount(env.host, {modelRequest: env.request(Promise.resolve(bytes)), onReady() {
      ready++; assert.equal(env.events.at(-1), 'firstFrame'); assert.ok(env.events.includes('render'));
    }});
    assert.equal(ready, 1); assert.ok(env.events.indexOf('fetchStart') < env.events.indexOf('pmrem'));
    assert.ok(env.events.indexOf('parseEnd') < env.events.indexOf('firstFrame'));
    assert.equal(env.events.filter(value => value === 'parse').length, 1);
    assert.equal(env.host.querySelectorAll('canvas').length, 1);
    api.setProgress(.5); api.dispose(); api.dispose();
    assert.deepEqual(env.counts(), {rendererDisposals: 1, envDisposals: 1, observers: 0});
    assert.equal(env.host.querySelector('canvas'), null); assert.equal(env.frames.size, 0);
    assert.equal(env.host.__packagingScene, undefined);
  } finally {env.close();}
});

test('closing before model bytes arrive releases allocated GPU resources without waiting for the network', async () => {
  const env = harness(), pending = deferred(); let ready = 0;
  try {
    const mounting = env.mount(env.host, {modelRequest: env.request(pending.promise), onReady: () => ready++});
    assert.ok(env.host.querySelector('canvas')); assert.ok(env.events.includes('pmrem'));
    env.controller.abort(new DOMException('Closed', 'AbortError'));
    assert.deepEqual(env.counts(), {rendererDisposals: 1, envDisposals: 1, observers: 0});
    assert.equal(env.host.querySelector('canvas'), null);
    await assert.rejects(mounting, error => error.name === 'AbortError');
    pending.resolve(new ArrayBuffer(12)); await Promise.resolve(); await Promise.resolve();
    assert.equal(env.events.includes('parse'), false); assert.equal(ready, 0);
  } finally {env.close();}
});

test('closing while parsing disposes a late model and never displays it', async () => {
  const parsing = deferred(), env = harness({parse: () => parsing.promise}); let ready = 0, geometryDisposals = 0;
  try {
    const mounting = env.mount(env.host, {modelRequest: env.request(Promise.resolve(new ArrayBuffer(12))), onReady: () => ready++});
    await Promise.resolve(); assert.ok(env.events.includes('parse'));
    env.controller.abort(); await assert.rejects(mounting);
    const gltf = env.model(); gltf.scene.traverse(object => object.geometry?.addEventListener('dispose', () => geometryDisposals++));
    parsing.resolve(gltf); await Promise.resolve(); await Promise.resolve();
    assert.equal(geometryDisposals, 4); assert.equal(ready, 0); assert.equal(env.host.__packagingScene, undefined);
    assert.deepEqual(env.counts(), {rendererDisposals: 1, envDisposals: 1, observers: 0});
  } finally {env.close();}
});

test('a first-render failure never reports ready and releases the whole mounted scene', async () => {
  const env = harness({renderError: new Error('Shader failure')}); let ready = 0;
  try {
    await assert.rejects(env.mount(env.host, {modelRequest: env.request(Promise.resolve(new ArrayBuffer(12))), onReady: () => ready++}), /Shader failure/);
    assert.equal(ready, 0); assert.equal(env.events.includes('firstFrame'), false);
    assert.deepEqual(env.counts(), {rendererDisposals: 1, envDisposals: 1, observers: 0});
    assert.equal(env.host.querySelector('canvas'), null); assert.equal(env.frames.size, 0);
  } finally {env.close();}
});

// Exercise the real pose branches for every product; the renderer alone is stubbed.
for (const [id,product] of Object.entries(PACKAGING_PRODUCTS)) test(`${id} print moves outward, clamps, resets and disposes`,async()=>{
 const env=harness({product});
 try{
  const api=await env.mount(env.host,{product,modelRequest:env.request(Promise.resolve(new ArrayBuffer(12)))});
  const flush=()=>{const callbacks=[...env.frames.values()];env.frames.clear();callbacks.forEach(fn=>fn(16));};
  api.setProgress(2);flush();assert.equal(api.getState().renderedProgress,1);assert.ok(api.getState().printOffset[2]>0);
  assert.deepEqual(api.getState().components,product.parts.map(p=>p.key));
  api.setProgress(-1);flush();assert.deepEqual(api.getState().printOffset,[0,0,0]);
  api.dispose();assert.equal(env.host.querySelector('canvas'),null);
 }finally{env.close();}
});
