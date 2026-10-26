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
function harness({parse, renderError, onRender, product = PACKAGING_PRODUCTS['poster-012']} = {}) {
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
    render(scene, camera) {events.push('render'); if (renderError) throw renderError; onRender?.(scene, camera);}
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

test('published Body Oil keeps its seal inside the complete cap and restores five independent parts',async()=>{
  const product=PACKAGING_PRODUCTS['poster-073'];
  const bytes=readFileSync(new URL('../packaging-assets/poster-073.glb',import.meta.url));
  const gltf=JSON.parse(bytes.toString('utf8',20,20+bytes.readUInt32LE(12)));
  const nodes=gltf.nodes.map(node=>{
    const object='mesh' in node ? new Three.Mesh(new Three.BoxGeometry(),new Three.MeshPhysicalMaterial()) : new Three.Group();
    object.name=node.name;
    if(node.matrix)object.applyMatrix4(new Three.Matrix4().fromArray(node.matrix));
    else {
      object.position.fromArray(node.translation??[0,0,0]);
      object.quaternion.fromArray(node.rotation??[0,0,0,1]);
      object.scale.fromArray(node.scale??[1,1,1]);
    }
    return object;
  });
  gltf.nodes.forEach((node,i)=>node.children?.forEach(child=>nodes[i].add(nodes[child])));
  const loaded={scene:new Three.Group()};
  gltf.scenes[gltf.scene??0].nodes.forEach(i=>loaded.scene.add(nodes[i]));
  const env=harness({product,parse:()=>Promise.resolve(loaded)});let api;
  try {
    Object.defineProperties(env.host,{clientWidth:{value:1200},clientHeight:{value:800}});
    api=await env.mount(env.host,{product,modelRequest:env.request(Promise.resolve(new ArrayBuffer(12)))});
    const flush=()=>{const frames=[...env.frames.values()];env.frames.clear();frames.forEach(fn=>fn(16));loaded.scene.updateWorldMatrix(true,true);};
    flush();
    const parts=Object.fromEntries(product.parts.map(p=>[p.key,loaded.scene.getObjectByName(p.node)]));
    const rest=Object.fromEntries(Object.entries(parts).map(([key,p])=>[key,{position:p.position.clone(),scale:p.scale.clone(),quaternion:p.quaternion.clone()}]));
    const seal=loaded.scene.getObjectByName('InnerSeal'),shell=loaded.scene.getObjectByName('Body Oil 02 hollow satin ivory cap');
    assert.equal(seal.parent,parts.closure);
    const pieces=[shell,seal],closureRest=parts.closure.getWorldPosition(new Three.Vector3());
    const pieceRest=pieces.map(piece=>({matrix:piece.matrix.toArray(),position:piece.getWorldPosition(new Three.Vector3())}));
    for(const value of [0,.1,.25,.5,.75,1,.5,0]){
      api.setProgress(value);flush();
      assert.equal(api.getState().renderedProgress,value);
      const offset=key=>parts[key].position.clone().sub(rest[key].position);
      assert.ok(offset('closure').distanceTo(new Three.Vector3(0,1.4*value,0))<1e-9);
      const displacement=parts.closure.getWorldPosition(new Three.Vector3()).sub(closureRest);
      pieces.forEach((piece,i)=>{
        assert.deepEqual(piece.matrix.toArray(),pieceRest[i].matrix,'the shell and seal keep their fitted local transforms');
        assert.ok(piece.getWorldPosition(new Three.Vector3()).sub(pieceRest[i].position).distanceTo(displacement)<1e-9,'the seal travels with the cap');
      });
      for(const key of ['print','name']){
        assert.ok(offset(key).z-offset('label').z>=1.14*value);
        assert.ok(Math.abs(offset(key).y-product.review.explosion.offsets[key][1]*value)<1e-9);
        assert.ok(Math.abs(parts[key].scale.x/rest[key].scale.x-(1+.3*value))<1e-9);
      }
      if(!value)for(const [key,p] of Object.entries(parts)){
        assert.ok(p.position.distanceTo(rest[key].position)<1e-9);
        assert.ok(p.scale.distanceTo(rest[key].scale)<1e-9);
        assert.ok(1-Math.abs(p.quaternion.dot(rest[key].quaternion))<1e-9);
      }
    }
    assert.deepEqual(Object.keys(parts).sort(),['body','closure','label','name','print']);
    assert.equal(Object.hasOwn(product.review.appearance,'liquid'),false);
    assert.equal(loaded.scene.getObjectByName('Liquid'),undefined);
  }finally{api?.dispose();env.close();}
});

test('Daily Emulsion moves the complete pump without changing its internal fitted transforms',async()=>{
  const product=PACKAGING_PRODUCTS['poster-072'];let loaded,api;
  const env=harness({product,parse:()=>Promise.resolve(loaded)});
  try {
    Object.defineProperties(env.host,{clientWidth:{value:1200},clientHeight:{value:800}});
    loaded=env.model();
    const placeholder=loaded.scene.getObjectByName('PumpAssembly');loaded.scene.remove(placeholder);
    const pump=new Three.Group();pump.name='PumpAssembly';pump.position.set(.10,1.89,.02);loaded.scene.add(pump);
    for(const [i,name] of ['Closure','PumpStem','Actuator'].entries()) {
      const child=new Three.Mesh(new Three.BoxGeometry(.2,.2,.2),new Three.MeshPhysicalMaterial());child.name=name;
      child.position.set(.03*i,.21*i,-.02*i);child.quaternion.setFromEuler(new Three.Euler(.02*i,-.01*i,.03*i));child.scale.set(1+.1*i,1+.05*i,1);
      pump.add(child);
    }
    const rest=Object.fromEntries(pump.children.map(child=>[child.name,{p:child.position.clone(),q:child.quaternion.clone(),s:child.scale.clone()}]));
    const pumpRest={p:pump.position.clone(),s:pump.scale.clone()};
    api=await env.mount(env.host,{product,modelRequest:env.request(Promise.resolve(new ArrayBuffer(12)))});
    const flush=()=>{const frames=[...env.frames.values()];env.frames.clear();frames.forEach(fn=>fn(16));};
    for(const progress of [.25,.5,1,0,1,0]) {
      api.setProgress(progress);flush();loaded.scene.updateMatrixWorld(true);
      assert.ok(pump.position.distanceTo(pumpRest.p.clone().add(new Three.Vector3(0,1.05*progress,0)))<1e-9);
      assert.ok(pump.scale.distanceTo(pumpRest.s)<1e-9);
      for(const child of pump.children) {
        assert.equal(child.parent,pump);
        assert.ok(child.position.distanceTo(rest[child.name].p)<1e-9);
        assert.ok(child.scale.distanceTo(rest[child.name].s)<1e-9);
        assert.ok(1-Math.abs(child.quaternion.dot(rest[child.name].q))<1e-9);
        const relative=child.getWorldPosition(new Three.Vector3()).sub(pump.getWorldPosition(new Three.Vector3()));
        assert.ok(relative.distanceTo(rest[child.name].p)<1e-9,'the actual Three hierarchy keeps fitted pump pieces together');
      }
      assert.ok(Math.abs(loaded.scene.getObjectByName('Overcap').position.y-2.35*progress)<1e-9);
    }
    assert.deepEqual(product.parts.map(p=>p.node),['Overcap','PumpAssembly','Body','PaperLabel','LogoPrint','ProductPrint']);
    assert.equal(loaded.scene.getObjectByName('Liquid'),undefined);
  } finally {api?.dispose();env.close();}
});

test('Daily phone layout compacts brand and product name together without reducing depth separation',async()=>{
  const product=PACKAGING_PRODUCTS['poster-072'];let loaded,api;
  const env=harness({product,parse:()=>Promise.resolve(loaded)});
  try {
    Object.defineProperties(env.host,{clientWidth:{value:393},clientHeight:{value:450}});loaded=env.model();
    api=await env.mount(env.host,{product,modelRequest:env.request(Promise.resolve(new ArrayBuffer(12)))});
    const flush=()=>{const frames=[...env.frames.values()];env.frames.clear();frames.forEach(fn=>fn(16));};
    for(const progress of [.5,1,0]) {
      api.setProgress(progress);flush();
      for(const key of ['label','print','name']) {
        const part=loaded.scene.getObjectByName(product.parts.find(p=>p.key===key).node),offset=product.review.explosion.offsets[key];
        assert.ok(Math.abs(part.position.x-offset[0]*.5*progress)<1e-9);
        assert.ok(Math.abs(part.position.z-offset[2]*progress)<1e-9);
        assert.ok(Math.abs(part.scale.x-(1+(product.review.explosion.scales[key]-1)*progress))<1e-9);
      }
      assert.equal(loaded.scene.getObjectByName('LogoPrint').position.x,loaded.scene.getObjectByName('ProductPrint').position.x);
    }
  } finally {api?.dispose();env.close();}
});

test('the Daily clear-cover flag preserves smooth transparent cover and leaves default frosted covers unchanged',async()=>{
  for(const [clearOvercap,overcapToneMapped] of [[true,undefined],[false,undefined],[undefined,undefined],[undefined,false]]) {
    const product=structuredClone(PACKAGING_PRODUCTS['poster-072']);let loaded,api;
    if(clearOvercap===undefined)delete product.review.appearance.clearOvercap;else product.review.appearance.clearOvercap=clearOvercap;
    if(overcapToneMapped!==undefined)product.review.appearance.overcapToneMapped=overcapToneMapped;
    const env=harness({product,parse:()=>Promise.resolve(loaded)});
    try {
      loaded=env.model();const body=loaded.scene.getObjectByName('Body'),cover=loaded.scene.getObjectByName('Overcap');
      for(const mesh of [body,cover]){mesh.material.transmission=1;mesh.material.roughness=.035;}
      api=await env.mount(env.host,{product,modelRequest:env.request(Promise.resolve(new ArrayBuffer(12)))});
      assert.equal(body.material.roughness,.24);assert.equal(body.material.toneMapped,false);
      assert.equal(cover.material.roughness,clearOvercap===true?.035:.24);
      assert.equal(cover.material.toneMapped,clearOvercap!==true&&overcapToneMapped!==false);
      assert.equal(cover.material.transmission,1);assert.equal(cover.material.thickness,.012);assert.equal(cover.material.side,Three.FrontSide);
    } finally {api?.dispose();env.close();}
  }
});

for (const [id, product] of Object.entries(PACKAGING_PRODUCTS).filter(([,p])=>p.review)) {
  test(`${id} separates all printing and restores imported transforms`, async () => {
    let loaded, api;
    const env=harness({product,parse:()=>Promise.resolve(loaded)});
    try {
      loaded=env.model();
      const parts=Object.fromEntries(product.parts.map(p=>[p.key,loaded.scene.getObjectByName(p.node)]));
      Object.values(parts).forEach((p,i)=>{p.position.set(.12*i,.23*i,-.07*i);p.scale.set(1.4,1.5,1.6);p.quaternion.setFromEuler(new Three.Euler(.02,-.03,.01));});
      const rest=Object.fromEntries(Object.entries(parts).map(([k,p])=>[k,{p:p.position.clone(),s:p.scale.clone(),q:p.quaternion.clone()}]));
      api=await env.mount(env.host,{product,modelRequest:env.request(Promise.resolve(new ArrayBuffer(12)))});
      const flush=()=>{const callbacks=[...env.frames.values()];env.frames.clear();callbacks.forEach(fn=>fn(16));};
      for (const value of [.5,1,0,1,0]) {
        api.setProgress(value);flush();
        const print=parts.print.position.clone().sub(rest.print.p);
        const label=parts.label?.position.clone().sub(rest.label.p);
        if(value) {
          if(label) {
          assert.ok(print.z-label.z>.45*value,'lettering must sit visibly in front of its label');
          assert.ok(print.x<label.x-.8*value,'lettering must also move farther sideways');
          assert.ok(parts.print.scale.x/rest.print.s.x>parts.label.scale.x/rest.label.s.x);
          } else assert.ok(print.length()>.5*value,'direct printing must separate from the container');
          const capKey=parts.closure?'closure':'pump';
          assert.ok(parts[capKey].position.y-rest[capKey].p.y>.7*value,'cap or complete pump separation must remain substantial');
          for(const [key,offset] of Object.entries(product.review.explosion.offsets)) {
            if(value===1) parts[key].position.clone().sub(rest[key].p).toArray().forEach((n,i)=>assert.ok(Math.abs(n-offset[i])<1e-9));
          }
        } else {
          for(const [key,p] of Object.entries(parts)) {
            assert.ok(p.position.distanceTo(rest[key].p)<1e-9);
            assert.ok(p.scale.distanceTo(rest[key].s)<1e-9);
            assert.ok(1-Math.abs(p.quaternion.dot(rest[key].q))<1e-9);
          }
        }
        if(product.review.appearance.clearLabel && value!==.5) assert.equal(parts.label.material.opacity,value===0?.05:1);
      }
    } finally {api?.dispose();env.close();}
  });
}

test('reviewed models preserve frosted glass, brushed metal and original glass tint', async () => {
  const product=PACKAGING_PRODUCTS['poster-063'];let loaded,api;
  const env=harness({product,parse:()=>Promise.resolve(loaded)});
  try {
    loaded=env.model();const body=loaded.scene.getObjectByName('Body'),cap=loaded.scene.getObjectByName('Closure'),label=loaded.scene.getObjectByName('PaperLabel');
    body.material.transmission=1;body.material.roughness=.3;body.material.color.set('#c5a978');
    const tint=body.material.color.clone();cap.material.metalness=1;cap.material.roughness=.27;
    label.material.map=new Three.Texture();label.material.metalness=1;label.material.roughness=.31;
    api=await env.mount(env.host,{product,modelRequest:env.request(Promise.resolve(new ArrayBuffer(12)))});
    assert.equal(body.material.roughness,.3);assert.ok(body.material.color.equals(tint));
    assert.equal(cap.material.roughness,.27);assert.equal(label.material.roughness,.31);
  } finally {api?.dispose();env.close();}
});

test('phone framing preserves depth separation while compacting wide print pairs', async () => {
  const product=PACKAGING_PRODUCTS['poster-059'];let loaded,api;
  const env=harness({product,parse:()=>Promise.resolve(loaded)});
  try {
    Object.defineProperties(env.host,{clientWidth:{value:393},clientHeight:{value:450}});
    loaded=env.model();
    api=await env.mount(env.host,{product,modelRequest:env.request(Promise.resolve(new ArrayBuffer(12)))});
    api.setProgress(1);const frames=[...env.frames.values()];env.frames.clear();frames.forEach(fn=>fn(16));
    for(const key of ['label','print']) {
      const part=loaded.scene.getObjectByName(product.parts.find(p=>p.key===key).node),offset=product.review.explosion.offsets[key];
      assert.equal(part.position.x,offset[0]*.5);assert.equal(part.position.z,offset[2]);
    }
    api.setProgress(0);[...env.frames.values()].forEach(fn=>fn(32));
    assert.deepEqual(api.getState().printOffset,[0,0,0]);
  } finally {api?.dispose();env.close();}
});

test('reviewed tinted glass uses absorption and frosted glass retains its original transmission', async () => {
  for(const id of ['poster-067','poster-061']) {
    const product=PACKAGING_PRODUCTS[id];let loaded,api;
    const env=harness({product,parse:()=>Promise.resolve(loaded)});
    try {
      loaded=env.model();const body=loaded.scene.getObjectByName('Body');
      body.material.transmission=.62;body.material.color.set('#b08040');const tint=body.material.color.clone();
      const other=new Three.Mesh(new Three.BoxGeometry(),body.material);body.add(other);
      api=await env.mount(env.host,{product,modelRequest:env.request(Promise.resolve(new ArrayBuffer(12)))});
      assert.equal(body.material.transmission,.62);
      if(id==='poster-067') for(const mesh of [body,other]) {
        assert.ok(mesh.material.attenuationColor.equals(tint));assert.equal(mesh.material.attenuationDistance,.3);
        assert.ok(mesh.material.color.equals(new Three.Color('#ffffff')));
      }
    } finally {api?.dispose();env.close();}
  }
});

test('the refill pouch keeps a thin transparent film instead of a thick coloured wall', async () => {
  const product=PACKAGING_PRODUCTS['poster-065'];let loaded,api;
  const env=harness({product,parse:()=>Promise.resolve(loaded)});
  try {
    loaded=env.model();const film=loaded.scene.getObjectByName('RefillPouch');
    film.material.transmission=.92;film.material.color.set('#ead4a3');
    api=await env.mount(env.host,{product,modelRequest:env.request(Promise.resolve(new ArrayBuffer(12)))});
    assert.equal(film.material.transmission,.92);assert.equal(film.material.thickness,.005);
    assert.equal(film.material.side,Three.FrontSide);assert.ok(film.material.color.equals(new Three.Color('#ffffff')));
  } finally {api?.dispose();env.close();}
});

for (const [id, node, thickness, toneMapped] of [
  ['poster-066','Overcap',.012,true],
  ['poster-065','RefillPouch',.005,false],
]) test(`${id} isolates cover or film settings from shared bottle glass in either traversal order`, async () => {
  for (const bodyFirst of [true,false]) {
    const product=PACKAGING_PRODUCTS[id];let loaded,api;
    const env=harness({product,parse:()=>Promise.resolve(loaded)});
    try {
      loaded=env.model();
      const body=loaded.scene.getObjectByName('Body'),part=loaded.scene.getObjectByName(node);
      body.material.transmission=.92;body.material.color.set('#d3c4a0');
      const tint=body.material.color.clone();part.material=body.material;
      const panel=new Three.Mesh(new Three.BoxGeometry(),body.material);part.add(panel);
      // The real Rose GLB visits Body before Overcap; neither order may share mutations.
      loaded.scene.children.sort((a,b)=>(a===body?(bodyFirst?-1:1):0)-(b===body?(bodyFirst?-1:1):0));
      api=await env.mount(env.host,{product,modelRequest:env.request(Promise.resolve(new ArrayBuffer(12)))});
      assert.equal(body.material.thickness,.08);assert.equal(body.material.side,Three.DoubleSide);
      assert.equal(body.material.toneMapped,false);assert.ok(body.material.color.equals(tint));
      for (const mesh of [part,panel]) {
        assert.notEqual(mesh.material,body.material);
        assert.equal(mesh.material.thickness,thickness);assert.equal(mesh.material.side,Three.FrontSide);
        assert.equal(mesh.material.toneMapped,toneMapped);
        assert.ok(mesh.material.color.equals(node==='RefillPouch'?new Three.Color('#ffffff'):tint));
      }
      const disposals=new Map([body.material,part.material,panel.material].map(material=>[material,0]));
      disposals.forEach((_,material)=>material.addEventListener('dispose',()=>disposals.set(material,disposals.get(material)+1)));
      api.dispose();api.dispose();
      assert.deepEqual([...disposals.values()],[1,1,1]);
    } finally {api?.dispose();env.close();}
  }
});

test('Gentle lettering renders above the translucent oval without tinting its black print', async () => {
  const product=PACKAGING_PRODUCTS['poster-044']; let loaded;
  const env=harness({product,parse:()=>Promise.resolve(loaded)});
  let api;
  try {
    loaded=env.model();
    const label=loaded.scene.getObjectByName('PaperLabel'),print=loaded.scene.getObjectByName('LogoPrint');
    for (const part of [label,print]) {part.material.map=new Three.Texture();part.material.transparent=true;}
    print.material.color.set('#111714');const original=print.material.color.clone();
    api=await env.mount(env.host,{product,modelRequest:env.request(Promise.resolve(new ArrayBuffer(12)))});
    assert.ok(print.renderOrder>label.renderOrder);
    assert.equal(print.material.depthWrite,false);assert.equal(label.material.depthWrite,false);
    assert.ok(print.material.color.equals(original));
  } finally {api?.dispose();env.close();}
});

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

for (const [id, lifts, printOffset] of [
  ['poster-039', {closure: 3.45, liner: 1.41}, null],
  ['poster-042', {closure: 1.2}, [-3.1, .18, 1.65]],
  ['poster-047', {closure:2.8}, [-3.1,.18,1.65]],
  ['poster-051', {closure:.9,stem:1.8,head:2.8}, [-3.4,.18,1.65]],
  ['poster-057', {head:4.1,stem:3.45,closure:.95}, [-3.1,.10,1.65]],
  ['poster-056', {overcap:4.85,head:2.6,stem:1.5,closure:.75}, [-3.8,.18,1.65]],
  ['poster-044', {overcap:3.6,head:2.5,stem:1.5,closure:.75}, [-2.65,.50,1.65]],
  ['poster-049', {pump: 1.25}, [-2.65, .18, 1.65]],
  ['poster-012', {cap: .100, liner: .047}, [-.025, .004, .035]],
  ['poster-071', {closure: .38, stem: .84, head: 1.35}, [-.63, .10, .86]],
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
      assert.equal(product.parts.length, id === 'poster-047' || id === 'poster-049' || id === 'poster-042' ? 4 : id === 'poster-051' || id === 'poster-044' || id === 'poster-056' || id === 'poster-057' ? 7 : 6);
      assert.equal(product.parts.find(part => part.key === 'label').node, 'PaperLabel');
      const labelDisplacement = parts.label.position.clone().sub(rest.label.position);
      const printDisplacement = parts.print.position.clone().sub(rest.print.position);
      labelDisplacement.toArray().forEach((value,i)=>near(value,[id === 'poster-057' ? -1.4 : id === 'poster-056' ? -1.85 : id === 'poster-042' || id === 'poster-047' ? -1.5 : id === 'poster-051' ? -1.65 : -1.25,.08,.65][i]*progress,'paper displacement'));
      sameVector(parts.label.scale,rest.label.scale.clone().multiplyScalar(1+.15*progress),'paper scale');
      near(printDisplacement.z-labelDisplacement.z,progress,'text must move farther forward than the paper');
      if (id === 'poster-057') {
        const t=Math.max(0,Math.min(1,(progress-.3)/.7)), drop=Math.max(0,Math.min(1,progress/.3));
        const offset=[1.7*t*t*(3-2*t),-.8*drop*drop*(3-2*drop),.35*t*t*(3-2*t)];
        parts.base.position.clone().sub(rest.base.position).toArray().forEach((v,i)=>near(v,offset[i],'base clears the sleeve before moving sideways'));
      }
      if (id === 'poster-051') {
        parts.cord.position.clone().sub(rest.cord.position).toArray().forEach((v,i)=>near(v,[1.05,.30,.25][i]*progress,'cord separation'));
      }
      if (id === 'poster-051' || id === 'poster-056' || id === 'poster-057') {
        if (progress === 0) near(parts.label.material.opacity,.05,'clear film leaves no paper patch at rest');
        if (progress === 1) near(parts.label.material.opacity,1,'separated film retains its translucent texture');
      }
    };

    for (let cycle = 0; cycle < 2; cycle++) {
      api.setProgress(.5); flush();
      if (id === 'poster-049' || id === 'poster-042' || id === 'poster-051' || id === 'poster-044' || id === 'poster-047' || id === 'poster-056' || id === 'poster-057') {
        for (const [key, lift] of Object.entries(lifts)) near(parts[key].position.y-rest[key].position.y, lift*(key==='overcap' && id==='poster-044' ? 3100/4913 : key==='overcap' && id==='poster-056' ? 1900/2197 : .5), `${key} half lift`);
        parts.print.position.clone().sub(rest.print.position).toArray().forEach((value,i)=>near(value,printOffset[i]*.5,'half print displacement'));
        sameVector(parts.print.scale,rest.print.scale.clone().multiplyScalar(id==='poster-044' || id==='poster-056' || id==='poster-057' ? 1.475 : 1.225),'half print scale');
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
      sameVector(parts.print.scale, rest.print.scale.clone().multiplyScalar(id==='poster-044' || id==='poster-056' || id==='poster-057' ? 1.95 : 1.45), 'expanded print scale');
      if (id === 'poster-049' || id === 'poster-042' || id === 'poster-051' || id === 'poster-044' || id === 'poster-047' || id === 'poster-056' || id === 'poster-057') checkSeparateLabel(1);
      // Compare the visible distances after the Beach model's unit conversion, not its tiny source units.
      if (id === 'poster-012' || id === 'poster-039') {
        near((parts[id === 'poster-012' ? 'cap' : 'closure'].position.y-rest[id === 'poster-012' ? 'cap' : 'closure'].position.y)*product.scale, id === 'poster-039' ? 3.45 : 3, 'studio cap lift');
        near((parts.liner.position.y-rest.liner.position.y)*product.scale, 1.41, 'studio liner lift');
      }
      api.setProgress(0); flush();
      Object.keys(parts).forEach(unchanged);
      if (id === 'poster-049' || id === 'poster-042' || id === 'poster-051' || id === 'poster-044' || id === 'poster-047' || id === 'poster-056' || id === 'poster-057') checkSeparateLabel(0);
    }
  } finally {api?.dispose(); env.close();}
});


test('Golden keeps its olive cover tinted while the empty glass stays neutral', async () => {
  const product=PACKAGING_PRODUCTS['poster-056']; let loaded;
  const env=harness({product,parse:()=>Promise.resolve(loaded)});let api;
  try {
    loaded=env.model();
    const cover=loaded.scene.getObjectByName('Overcap'),body=loaded.scene.getObjectByName('Body');
    cover.material.name='olive translucent cover';cover.material.color.set('#3d4822');cover.material.transmission=.9;
    body.material.name='clear glass';body.material.color.set('#eeeeee');body.material.transmission=1;
    const secondPanel=new Three.Mesh(new Three.BoxGeometry(),cover.material);cover.add(secondPanel);
    const olive=cover.material.color.clone();
    api=await env.mount(env.host,{product,modelRequest:env.request(Promise.resolve(new ArrayBuffer(12)))});
    assert.ok(cover.material.attenuationColor.equals(olive));
    assert.ok(secondPanel.material.attenuationColor.equals(olive),'every panel retains the original tint even when the GLB shares one material');
    assert.ok(body.material.color.equals(new Three.Color('#ffffff')));
    assert.equal(body.material.transmission,1);
    assert.equal(body.castShadow,false);
  } finally {api?.dispose();env.close();}
});


test('B5 pipette remains visible through the empty bottle and preserves the original white print', async () => {
  const product=PACKAGING_PRODUCTS['poster-057'];let loaded;
  const env=harness({product,parse:()=>Promise.resolve(loaded)});let api;
  try {
    loaded=env.model();
    const pipe=loaded.scene.getObjectByName('Pipette'),body=loaded.scene.getObjectByName('Body'),print=loaded.scene.getObjectByName('LogoPrint');
    pipe.material.name='B5 clear glass pipette';pipe.material.transmission=1;
    body.material.transmission=1;print.material.map=new Three.Texture();print.material.transparent=true;print.material.color.set('#ffffff');
    api=await env.mount(env.host,{product,modelRequest:env.request(Promise.resolve(new ArrayBuffer(12)))});
    assert.equal(pipe.material.transmission,0);assert.equal(pipe.material.transparent,true);assert.equal(pipe.material.opacity,.38);assert.equal(pipe.material.depthWrite,false);
    assert.equal(body.material.transmission,1);assert.equal(body.material.depthWrite,false);assert.ok(body.material.color.equals(new Three.Color('#ffffff')));
    assert.equal(print.renderOrder,3);assert.ok(print.material.color.equals(new Three.Color('#ffffff')));assert.equal(print.material.toneMapped,false);
  } finally {api?.dispose();env.close();}
});


test('new clear overcaps retain neutral transmission without changing prior finishes', async () => {
  for(const toneMapped of [false,true]) {
    const base=PACKAGING_PRODUCTS['poster-066'];
    const product={...base,review:{...base.review,appearance:{...base.review.appearance,overcapToneMapped:toneMapped}}};let loaded,api;
    const env=harness({product,parse:()=>Promise.resolve(loaded)});
    try {
      loaded=env.model();const cap=loaded.scene.getObjectByName(product.parts.find(p=>p.key==='overcap').node);
      cap.material.transmission=1;cap.material.roughness=.035;
      api=await env.mount(env.host,{product,modelRequest:env.request(Promise.resolve(new ArrayBuffer(12)))});
      assert.equal(cap.material.toneMapped,toneMapped);
      assert.equal(cap.material.transmission,1);
    } finally {api?.dispose();env.close();}
  }
});

test('Moisture Shampoo moves its exported pump as one unit and preserves independent paper and print', async () => {
  const product=PACKAGING_PRODUCTS['poster-049'];
  assert.equal(product.review,undefined,'Moisture retains its existing material and lighting branch');
  const bytes=readFileSync(new URL('../packaging-assets/poster-049.glb',import.meta.url));
  const gltf=JSON.parse(bytes.toString('utf8',20,20+bytes.readUInt32LE(12)));
  const nodes=gltf.nodes.map(node=>{
    const object='mesh' in node ? new Three.Mesh(new Three.BoxGeometry(),new Three.MeshPhysicalMaterial()) : new Three.Group();
    object.name=node.name;
    if(node.matrix) object.applyMatrix4(new Three.Matrix4().fromArray(node.matrix));
    else {
      object.position.fromArray(node.translation??[0,0,0]);
      object.quaternion.fromArray(node.rotation??[0,0,0,1]);
      object.scale.fromArray(node.scale??[1,1,1]);
    }
    return object;
  });
  gltf.nodes.forEach((node,i)=>node.children?.forEach(child=>nodes[i].add(nodes[child])));
  const loaded={scene:new Three.Group()};
  gltf.scenes[gltf.scene??0].nodes.forEach(i=>loaded.scene.add(nodes[i]));
  let camera;
  const env=harness({product,parse:()=>Promise.resolve(loaded),onRender:(_,value)=>{camera=value;}});let api;
  try {
    Object.defineProperties(env.host,{clientWidth:{value:1200},clientHeight:{value:800}});
    api=await env.mount(env.host,{product,modelRequest:env.request(Promise.resolve(new ArrayBuffer(12)))});
    const flush=()=>{const callbacks=[...env.frames.values()];env.frames.clear();callbacks.forEach(fn=>fn(16));loaded.scene.updateWorldMatrix(true,true);};
    flush();
    const pump=loaded.scene.getObjectByName('PumpAssembly');
    const pieces=['Closure','PumpStem','Actuator'].map(name=>loaded.scene.getObjectByName(name));
    pieces.forEach(piece=>assert.equal(piece.parent,pump));
    const parts=Object.fromEntries(product.parts.map(part=>[part.key,loaded.scene.getObjectByName(part.node)]));
    const rest=Object.fromEntries(Object.entries(parts).map(([key,part])=>[key,{position:part.position.clone(),scale:part.scale.clone(),quaternion:part.quaternion.clone()}]));
    assert.deepEqual(Object.keys(parts).sort(),['jar','label','print','pump']);
    const restPump=pump.getWorldPosition(new Three.Vector3());
    const restPieces=pieces.map(piece=>({position:piece.getWorldPosition(new Three.Vector3()),matrix:piece.matrix.toArray()}));
    for(const progress of [0,.25,.5,.75,1,.5,0]) {
      api.setProgress(progress);flush();
      const state=api.getState();
      assert.equal(state.renderedProgress,progress);
      assert.ok(Math.abs(camera.position.y-1.05-(1.45+.625*progress))<1e-9,'camera follows the compact pump assembly center');
      assert.ok(Math.abs(camera.top-camera.bottom-(4.2+.85*progress))<1e-9,'desktop framing reaches a 5.05-unit full-open height');
      assert.ok(Math.abs(camera.position.x+.65*progress)<1e-9,'camera preserves the approved horizontal framing');
      assert.ok(parts.pump.position.clone().sub(rest.pump.position).distanceTo(new Three.Vector3(0,1.25*progress,0))<1e-9);
      const displacement=pump.getWorldPosition(new Three.Vector3()).sub(restPump);
      pieces.forEach((piece,i)=>{
        assert.deepEqual(piece.matrix.toArray(),restPieces[i].matrix,'the three pump parts retain their assembled transforms');
        assert.ok(piece.getWorldPosition(new Three.Vector3()).sub(restPieces[i].position).distanceTo(displacement)<1e-9,'every pump part moves with the assembly');
      });
      for(const [key,offset,scale] of [['label',[-1.25,.08,.65],1.15],['print',[-2.65,.18,1.65],1.45]]) {
        assert.ok(parts[key].position.clone().sub(rest[key].position).distanceTo(new Three.Vector3(...offset).multiplyScalar(progress))<1e-9);
        assert.ok(parts[key].scale.distanceTo(rest[key].scale.clone().multiplyScalar(1+(scale-1)*progress))<1e-9);
      }
      for(const key of progress===0 ? Object.keys(parts) : ['jar']) {
        assert.ok(parts[key].position.distanceTo(rest[key].position)<1e-9);
        assert.ok(parts[key].scale.distanceTo(rest[key].scale)<1e-9);
        assert.ok(1-Math.abs(parts[key].quaternion.dot(rest[key].quaternion))<1e-9);
      }
    }
  } finally {api?.dispose();env.close();}
});

for(const [id,lift,centerDelta,heightDelta] of [
  ['poster-042',1.2,.60,.90],
  ['poster-047',2.8,1.4,2.3],
]) test(`${id} keeps its fitted cap intact, restores all layers and frames the real model bounds`,async()=>{
  const product=PACKAGING_PRODUCTS[id];
  assert.equal(product.review,undefined,'retain the established material and lighting branch');
  const bytes=readFileSync(new URL(`../packaging-assets/${id}.glb`,import.meta.url));
  const gltf=JSON.parse(bytes.toString('utf8',20,20+bytes.readUInt32LE(12)));
  const nodes=gltf.nodes.map(node=>{
    let object=new Three.Group();
    if('mesh' in node) {
      const accessor=gltf.accessors[gltf.meshes[node.mesh].primitives[0].attributes.POSITION];
      const low=new Three.Vector3(...accessor.min),high=new Three.Vector3(...accessor.max);
      const size=high.clone().sub(low),center=high.clone().add(low).multiplyScalar(.5);
      object=new Three.Mesh(new Three.BoxGeometry(...size.toArray()).translate(...center.toArray()),new Three.MeshPhysicalMaterial());
    }
    object.name=node.name;
    if(node.matrix)object.applyMatrix4(new Three.Matrix4().fromArray(node.matrix));
    else {
      object.position.fromArray(node.translation??[0,0,0]);
      object.quaternion.fromArray(node.rotation??[0,0,0,1]);
      object.scale.fromArray(node.scale??[1,1,1]);
    }
    return object;
  });
  gltf.nodes.forEach((node,i)=>node.children?.forEach(child=>nodes[i].add(nodes[child])));
  const loaded={scene:new Three.Group()};
  gltf.scenes[gltf.scene??0].nodes.forEach(i=>loaded.scene.add(nodes[i]));
  let camera,api;
  const env=harness({product,parse:()=>Promise.resolve(loaded),onRender:(_,value)=>{camera=value;}});
  try {
    Object.defineProperties(env.host,{clientWidth:{value:1200},clientHeight:{value:800}});
    api=await env.mount(env.host,{product,modelRequest:env.request(Promise.resolve(new ArrayBuffer(12)))});
    const flush=()=>{const callbacks=[...env.frames.values()];env.frames.clear();callbacks.forEach(fn=>fn(16));loaded.scene.updateWorldMatrix(true,true);camera.updateMatrixWorld(true);};
    flush();
    const parts=Object.fromEntries(product.parts.map(part=>[part.key,loaded.scene.getObjectByName(part.node)]));
    assert.deepEqual(Object.keys(parts).sort(),['closure','jar','label','print']);
    const rest=Object.fromEntries(Object.entries(parts).map(([key,part])=>[key,{position:part.position.clone(),scale:part.scale.clone(),quaternion:part.quaternion.clone()}]));
    const pieces=id==='poster-042' ? ['Closure','StopperInsert'].map(name=>loaded.scene.getObjectByName(name)) : [...parts.closure.children];
    pieces.forEach(piece=>assert.equal(piece.parent,parts.closure));
    const restCap=parts.closure.getWorldPosition(new Three.Vector3());
    const fitted=pieces.map(piece=>({position:piece.getWorldPosition(new Three.Vector3()),matrix:piece.matrix.toArray()}));
    for(const progress of [0,.25,.5,.75,1,.5,0]) {
      api.setProgress(progress);flush();
      assert.equal(api.getState().renderedProgress,progress);
      assert.ok(parts.closure.position.clone().sub(rest.closure.position).distanceTo(new Three.Vector3(0,lift*progress,0))<1e-9);
      const displacement=parts.closure.getWorldPosition(new Three.Vector3()).sub(restCap);
      pieces.forEach((piece,i)=>{
        assert.deepEqual(piece.matrix.toArray(),fitted[i].matrix,'fitted cap parts retain their local transforms');
        assert.ok(piece.getWorldPosition(new Three.Vector3()).sub(fitted[i].position).distanceTo(displacement)<1e-9,'the insert moves rigidly with the shell');
      });
      assert.ok(Math.abs(camera.position.y-1.05-(1.45+centerDelta*progress))<1e-9);
      assert.ok(Math.abs(camera.top-camera.bottom-(4.2+heightDelta*progress))<1e-9);
      for(const [key,offset,growth] of [['label',[-1.5,.08,.65],.15],['print',[-3.1,.18,1.65],.45]]) {
        assert.ok(parts[key].position.clone().sub(rest[key].position).distanceTo(new Three.Vector3(...offset).multiplyScalar(progress))<1e-9);
        assert.ok(parts[key].scale.distanceTo(rest[key].scale.clone().multiplyScalar(1+growth*progress))<1e-9);
      }
      // Imported mesh bounds must stay inside the viewport, including the raised cap and complete print.
      for(const mesh of nodes.filter(node=>node.isMesh)) {
        mesh.geometry.computeBoundingBox();
        const {min,max}=mesh.geometry.boundingBox;
        for(const x of [min.x,max.x])for(const y of [min.y,max.y])for(const z of [min.z,max.z]) {
          const projected=new Three.Vector3(x,y,z).applyMatrix4(mesh.matrixWorld).project(camera);
          assert.ok(Math.abs(projected.x)<.98 && Math.abs(projected.y)<.98,`${id} ${mesh.name} remains in frame at ${progress}`);
        }
      }
      for(const key of progress===0 ? Object.keys(parts) : ['jar']) {
        assert.ok(parts[key].position.distanceTo(rest[key].position)<1e-9);
        assert.ok(parts[key].scale.distanceTo(rest[key].scale)<1e-9);
        assert.ok(1-Math.abs(parts[key].quaternion.dot(rest[key].quaternion))<1e-9);
      }
    }
  } finally {api?.dispose();env.close();}
});
