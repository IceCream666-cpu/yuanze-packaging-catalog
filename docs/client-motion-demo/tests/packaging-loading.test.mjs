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
    for (const name of product.parts.map(part=>part.node)) {
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
    assert.equal(geometryDisposals, 3); assert.equal(ready, 0); assert.equal(env.host.__packagingScene, undefined);
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

for (const id of ['poster-012','poster-071']) test(`${id} approved components expand and reset without changing original scales`, async()=>{
 const product=PACKAGING_PRODUCTS[id];let gltf;
 const env=harness({product,parse:()=>Promise.resolve(gltf=env.model())});
 try {
  const api=await env.mount(env.host,{product,modelRequest:env.request(Promise.resolve(new ArrayBuffer(12)))});
  const flush=()=>{const callbacks=[...env.frames.values()];env.frames.clear();callbacks.forEach(fn=>fn(16));};
  const nodes=Object.fromEntries(product.parts.map(part=>[part.key,gltf.scene.getObjectByName(part.node)]));
  assert.equal(product.parts.length,id==='poster-071'?5:3);
  api.setProgress(1);flush();
  if(id==='poster-071'){
   assert.equal(nodes.closure.position.y,.38);assert.equal(nodes.stem.position.y,.84);assert.equal(nodes.head.position.y,1.35);
   assert.deepEqual(api.getState().printOffset,[-.63,.10,.86]);assert.equal(nodes.print.scale.x,1.45);
  }else{
   assert.equal(nodes.cap.position.y,.100);assert.equal(nodes.liner.position.y,.047);assert.equal(api.getState().printOffset,null);
  }
  api.setProgress(0);flush();
  for(const n of Object.values(nodes)){assert.deepEqual(n.position.toArray(),[0,0,0]);assert.deepEqual(n.scale.toArray(),[1,1,1]);}
  api.dispose();assert.equal(env.host.querySelector('canvas'),null);
 }finally{env.close();}
});

for (const [id, lifts, printOffset] of [
  ['poster-039', {closure: 3.45, liner: 1.41}, null],
  ['poster-042', {closure: 2.8, liner: 1.35}, [-3.1, .18, 1.65]],
  ['poster-051', {closure:.9,stem:1.8,head:2.8}, [-3.4,.18,1.65]],
  ['poster-049', {closure: .85, stem: 1.75, head: 2.8}, [-2.65, .18, 1.65]],
]) test(`${id} mounted components preserve their full separation and restore their original transforms`, async () => {
  const product = PACKAGING_PRODUCTS[id]; let loaded;
  const env = harness({product, parse: () => Promise.resolve(loaded)});
  let api;
  try {
    loaded = env.model();
    const parts = Object.fromEntries(product.parts.map(part => [part.key, loaded.scene.getObjectByName(part.node)]));
    // Nonzero pivots and scales catch animations that overwrite the imported model's transforms.
    Object.values(parts).forEach((part, i) => {
      part.position.set(.13*i, .27*i, -.09*i);
      part.scale.set(1.7, 1.8, 1.9);
      part.quaternion.setFromEuler(new Three.Euler(.03, -.02, .01));
    });
    const rest = Object.fromEntries(Object.entries(parts).map(([key, part]) => [key, {
      position: part.position.clone(), scale: part.scale.clone(), quaternion: part.quaternion.clone(),
    }]));
    api = await env.mount(env.host, {product, modelRequest: env.request(Promise.resolve(new ArrayBuffer(12)))});
    const flush = () => {
      const callbacks = [...env.frames.values()]; env.frames.clear(); callbacks.forEach(fn => fn(16));
    };
    const near = (actual, expected, message) => assert.ok(Math.abs(actual-expected) < 1e-9, `${message}: ${actual} != ${expected}`);
    const sameVector = (actual, expected, message) => actual.toArray().forEach((value, i) => near(value, expected.toArray()[i], message));
    const unchanged = key => {
      sameVector(parts[key].position, rest[key].position, `${key} position`);
      sameVector(parts[key].scale, rest[key].scale, `${key} scale`);
      parts[key].quaternion.toArray().forEach((value, i) => near(value, rest[key].quaternion.toArray()[i], `${key} rotation`));
    };

    const checkSeparateLabel = progress => {
      assert.equal(product.parts.length, id === 'poster-042' ? 5 : id === 'poster-051' ? 7 : 6);
      assert.equal(product.parts.find(part => part.key === 'label').node, 'PaperLabel');
      const labelDisplacement = parts.label.position.clone().sub(rest.label.position);
      const printDisplacement = parts.print.position.clone().sub(rest.print.position);
      labelDisplacement.toArray().forEach((value,i)=>near(value,[id === 'poster-042' ? -1.5 : id === 'poster-051' ? -1.65 : -1.25,.08,.65][i]*progress,'paper displacement'));
      sameVector(parts.label.scale,rest.label.scale.clone().multiplyScalar(1+.15*progress),'paper scale');
      near(printDisplacement.z-labelDisplacement.z,progress,'text must move farther forward than the paper');
      if (id === 'poster-051') {
        parts.cord.position.clone().sub(rest.cord.position).toArray().forEach((v,i)=>near(v,[1.05,.30,.25][i]*progress,'cord separation'));
        if (progress === 0) near(parts.label.material.opacity,.05,'clear film leaves no paper patch at rest');
        if (progress === 1) near(parts.label.material.opacity,1,'separated film retains its translucent texture');
      }
    };

    for (let cycle = 0; cycle < 2; cycle++) {
      api.setProgress(.5); flush();
      if (id === 'poster-049' || id === 'poster-042' || id === 'poster-051') {
        for (const [key, lift] of Object.entries(lifts)) near(parts[key].position.y-rest[key].position.y, lift*.5, `${key} half lift`);
        parts.print.position.clone().sub(rest.print.position).toArray().forEach((value,i)=>near(value,printOffset[i]*.5,'half print displacement'));
        sameVector(parts.print.scale,rest.print.scale.clone().multiplyScalar(1.225),'half print scale');
        checkSeparateLabel(.5);
      }
      api.setProgress(1); flush();
      for (const [key, lift] of Object.entries(lifts)) {
        near(parts[key].position.y-rest[key].position.y, lift, `${key} full lift`);
        sameVector(parts[key].scale, rest[key].scale, `${key} scale`);
      }
      unchanged('jar');
      const displacement = parts.print.position.clone().sub(rest.print.position);
      if (printOffset) displacement.toArray().forEach((value, i) => near(value, printOffset[i], 'print displacement'));
      else {
        assert.ok(displacement.x < -1.5, 'PDRN print must visibly separate to the left of the wider jar.');
        assert.ok(displacement.z >= 1, 'PDRN print must lift forward from the glass surface.');
        assert.ok(Math.abs(parts.closure.quaternion.dot(rest.closure.quaternion)) < .99, 'The open lid must turn to reveal its interior.');
      }
      sameVector(parts.print.scale, rest.print.scale.clone().multiplyScalar(1.45), 'expanded print scale');
      if (id === 'poster-049' || id === 'poster-042' || id === 'poster-051') checkSeparateLabel(1);
      // Compare the visible distances after the Beach model's unit conversion, not its tiny source units.
      if (id === 'poster-012' || id === 'poster-039') {
        near((parts[id === 'poster-012' ? 'cap' : 'closure'].position.y-rest[id === 'poster-012' ? 'cap' : 'closure'].position.y)*product.scale, id === 'poster-039' ? 3.45 : 3, 'studio cap lift');
        near((parts.liner.position.y-rest.liner.position.y)*product.scale, 1.41, 'studio liner lift');
      }
      api.setProgress(0); flush();
      Object.keys(parts).forEach(unchanged);
      if (id === 'poster-049' || id === 'poster-042' || id === 'poster-051') checkSeparateLabel(0);
    }
  } finally {api?.dispose(); env.close();}
});

test('PDRN glass, silver and print materials use their approved settings while older models retain theirs', async () => {
 for (const id of ['poster-012','poster-071','poster-039','poster-049']) {
  const product=PACKAGING_PRODUCTS[id];let loaded;const env=harness({product,parse:()=>Promise.resolve(loaded)});let api;
  try {
   loaded=env.model();
   const body=loaded.scene.getObjectByName(product.parts.find(part=>part.key==='jar').node);
   body.material.transmission=1;body.material.roughness=.08;body.material.thickness=.2;
   const closure=loaded.scene.getObjectByName(product.parts.find(part=>['cap','closure'].includes(part.key)).node);
   closure.material.metalness=1;
   const print=loaded.scene.getObjectByName('LogoPrint');
   if (print) {print.material.map=new Three.Texture();print.material.transparent=true;}
   api=await env.mount(env.host,{product,modelRequest:env.request(Promise.resolve(new ArrayBuffer(12)))});
   const glass=body.material;
   if (id==='poster-039' || id==='poster-049') {
    assert.equal(glass.roughness,.012);assert.equal(glass.thickness,.08);assert.equal(glass.ior,1.48);
    assert.equal(glass.envMapIntensity,.3);assert.equal(glass.toneMapped,false);assert.equal(glass.specularIntensity,.7);
    assert.equal(body.castShadow,false);assert.equal(body.receiveShadow,false);
    assert.equal(closure.material.roughness,id==='poster-049'?.16:.075);assert.equal(closure.material.envMapIntensity,1);
    assert.equal(print.material.roughness,.7);assert.equal(print.material.specularIntensity,.05);
    assert.equal(print.material.depthWrite,false);assert.equal(print.renderOrder,2);
   } else if (id==='poster-012') {
    assert.equal(glass.roughness,.035);assert.equal(glass.thickness,.0024);assert.equal(glass.ior,1.47);
    assert.equal(glass.envMapIntensity,1.05);assert.equal(glass.toneMapped,true);assert.equal(closure.material.roughness,.34);
   } else {
    assert.equal(glass.roughness,.08);assert.equal(glass.thickness,.2);assert.equal(glass.envMapIntensity,.65);
    assert.equal(print.material.depthWrite,false);assert.equal(print.renderOrder,2);
   }
  } finally {api?.dispose();env.close();}
 }
});

test('Woodland uses amber absorption and preserves its nonmetal black closure and separate artwork', async () => {
 const product=PACKAGING_PRODUCTS['poster-042'];let loaded;const env=harness({product,parse:()=>Promise.resolve(loaded)});let api;
 try {
  loaded=env.model();
  const body=loaded.scene.getObjectByName('Body'),closure=loaded.scene.getObjectByName('Closure');
  body.material.name='Woodland amber glass';body.material.transmission=1;body.material.color.set('#ff9e42');
  const amber=body.material.color.clone();
  closure.material.metalness=0;closure.material.roughness=.06;closure.material.color.set('#080808');
  const originalCapColor=closure.material.color.clone();
  for(const name of ['PaperLabel','LogoPrint']){const part=loaded.scene.getObjectByName(name);part.material.map=new Three.Texture();part.material.transparent=true;}
  api=await env.mount(env.host,{product,modelRequest:env.request(Promise.resolve(new ArrayBuffer(12)))});
  assert.ok(body.material.attenuationColor.equals(amber));assert.equal(body.material.color.getHexString(),'ffffff');
  assert.equal(body.material.attenuationDistance,.85);assert.equal(body.material.thickness,.12);
  assert.equal(body.material.envMapIntensity,.65);assert.equal(body.material.roughness,.035);assert.equal(body.material.toneMapped,false);
  assert.equal(closure.material.metalness,0);assert.equal(closure.material.roughness,.06);assert.ok(closure.material.color.equals(originalCapColor));
  for(const name of ['PaperLabel','LogoPrint']){const part=loaded.scene.getObjectByName(name);assert.equal(part.material.depthWrite,false);assert.equal(part.renderOrder,2);assert.equal(part.material.envMapIntensity,.1);}
 } finally {api?.dispose();env.close();}
});

test('Pure Volume preserves matte ivory, brushed gold and translucent film without glass overrides', async () => {
 const product=PACKAGING_PRODUCTS['poster-051'];let loaded;const env=harness({product,parse:()=>Promise.resolve(loaded)});let api;
 try {
  loaded=env.model();
  const body=loaded.scene.getObjectByName('Body'),closure=loaded.scene.getObjectByName('Closure');
  body.material.color.set('#f3eee3');body.material.roughness=.48;body.material.transmission=0;
  closure.material.color.set('#a68c56');closure.material.metalness=1;closure.material.roughness=.24;
  for(const name of ['PaperLabel','LogoPrint']){const part=loaded.scene.getObjectByName(name);part.material.map=new Three.Texture();part.material.transparent=true;part.material.roughness=.23;}
  api=await env.mount(env.host,{product,modelRequest:env.request(Promise.resolve(new ArrayBuffer(12)))});
  assert.equal(body.material.color.getHexString(),'f3eee3');assert.equal(body.material.transmission,0);assert.equal(body.material.roughness,.48);
  assert.equal(closure.material.color.getHexString(),'a68c56');assert.equal(closure.material.metalness,1);assert.equal(closure.material.roughness,.24);
  for(const part of [body,closure]) {assert.equal(part.material.envMapIntensity,.65);assert.equal(part.castShadow,true);assert.equal(part.receiveShadow,true);}
  for(const name of ['PaperLabel','LogoPrint']){const part=loaded.scene.getObjectByName(name);assert.equal(part.material.roughness,.23);assert.equal(part.material.envMapIntensity,.65);assert.equal(part.material.depthWrite,false);assert.equal(part.renderOrder,2);assert.equal(part.castShadow,false);assert.equal(part.receiveShadow,false);}
 } finally {api?.dispose();env.close();}
});
