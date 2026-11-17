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
    setPixelRatio(value) {events.push(['pixelRatio',value]);} setClearColor() {} setSize() {}
    render(scene, camera) {events.push('render'); if (renderError) throw renderError; onRender?.(scene, camera);}
    dispose() {rendererDisposals++;}
  }
  class PMREM {
    fromScene() {events.push('pmrem'); return {texture: new Three.Texture(), dispose() {envDisposals++;}};}
    dispose() {}
  }
  function model() {
    const scenes = (product.finishes || [{scene: 'default'}]).map(finish => {
      const scene = new Three.Group(); scene.name = finish.scene;
      for (const name of product.parts.map(part => part.node)) {
        const part = new Three.Mesh(new Three.BoxGeometry(), new Three.MeshPhysicalMaterial());
        part.name = name; part.userData.partKey = name; scene.add(part);
      }
      return scene;
    });
    return {scene: scenes[0], scenes};
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
      assert.equal(cover.material.transmission,1);assert.equal(cover.material.thickness,.02);assert.equal(cover.material.side,Three.FrontSide);
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
          const sidewaysSpread=product.review.explosion.offsets.label[0]-product.review.explosion.offsets.print[0];
          assert.ok(sidewaysSpread>=.7,'authored lettering must have a substantial sideways separation');
          assert.ok(label.x-print.x>=sidewaysSpread*value-1e-9,'lettering must follow its approved sideways separation');
          assert.ok(Math.abs(parts.print.scale.x/rest.print.s.x-(1+((product.review.explosion.scales?.print??1)-1)*value))<1e-9,'lettering retains its approved scale');
          } else assert.ok(print.length()>.5*value,'direct printing must separate from the container');
          const capKey=parts.closure?'closure':parts.pump?'pump':'cap';
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
        if(product.review.appearance.clearLabel && value!==.5) { const opacity=product.review.appearance.carrierOpacity||[.05,1]; assert.equal(parts.label.material.opacity,opacity[value===0?0:1]); }
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
      assert.equal(body.material.transmission,id==='poster-067'?.94:.62);
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
  ['poster-066','Overcap',.012,false],
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
    assert.equal(geometryDisposals, PACKAGING_PRODUCTS['poster-012'].parts.length); assert.equal(ready, 0); assert.equal(env.host.__packagingScene, undefined);
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
  ['poster-051', {pump:2.3}, [-3.4,.18,1.65]],
  ['poster-057', {dropper:1.95}, [-3.1,.10,1.65]],
  ['poster-044', {overcap:3.15,pump:2.15}, [-2.65,.50,1.65]],
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
      assert.equal(product.parts.length, id === 'poster-047' || id === 'poster-042' || id === 'poster-051' || id === 'poster-057' ? 4 : id === 'poster-044' || id === 'poster-056' ? 5 : 6);
      assert.equal(product.parts.find(part => part.key === 'label').node, 'PaperLabel');
      const labelDisplacement = parts.label.position.clone().sub(rest.label.position);
      const printDisplacement = parts.print.position.clone().sub(rest.print.position);
      labelDisplacement.toArray().forEach((value,i)=>near(value,[id === 'poster-057' ? -1.4 : id === 'poster-056' ? -1.85 : id === 'poster-042' || id === 'poster-047' ? -1.5 : id === 'poster-051' ? -1.65 : -1.25,.08,.65][i]*progress,'paper displacement'));
      sameVector(parts.label.scale,rest.label.scale.clone().multiplyScalar(1+.15*progress),'paper scale');
      near(printDisplacement.z-labelDisplacement.z,progress,'text must move farther forward than the paper');


      if (id === 'poster-051' || id === 'poster-056' || id === 'poster-057') {
        if (progress === 0) near(parts.label.material.opacity,.05,'clear film leaves no paper patch at rest');
        if (progress === 1) near(parts.label.material.opacity,1,'separated film retains its translucent texture');
      }
    };

    for (let cycle = 0; cycle < 2; cycle++) {
      api.setProgress(.5); flush();
      if (id === 'poster-042' || id === 'poster-051' || id === 'poster-044' || id === 'poster-047' || id === 'poster-056' || id === 'poster-057') {
        for (const [key, lift] of Object.entries(lifts)) near(parts[key].position.y-rest[key].position.y, lift*.5, `${key} half lift`);
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
      if (id === 'poster-042' || id === 'poster-051' || id === 'poster-044' || id === 'poster-047' || id === 'poster-056' || id === 'poster-057') checkSeparateLabel(1);
      // Compare the visible distances after the Beach model's unit conversion, not its tiny source units.
      if (id === 'poster-012' || id === 'poster-039') {
        near((parts[id === 'poster-012' ? 'cap' : 'closure'].position.y-rest[id === 'poster-012' ? 'cap' : 'closure'].position.y)*product.scale, id === 'poster-039' ? 3.45 : 3, 'studio cap lift');
        near((parts.liner.position.y-rest.liner.position.y)*product.scale, 1.41, 'studio liner lift');
      }
      api.setProgress(0); flush();
      Object.keys(parts).forEach(unchanged);
      if (id === 'poster-042' || id === 'poster-051' || id === 'poster-044' || id === 'poster-047' || id === 'poster-056' || id === 'poster-057') checkSeparateLabel(0);
    }
  } finally {api?.dispose(); env.close();}
});


test('Golden keeps its olive cover tinted while only the neutral bottle stays frosted', async () => {
  const product=PACKAGING_PRODUCTS['poster-056']; let loaded;
  const env=harness({product,parse:()=>Promise.resolve(loaded)});let api;
  try {
    loaded=env.model();
    const cover=loaded.scene.getObjectByName('Overcap'),body=loaded.scene.getObjectByName('Body');
    cover.material.name='olive translucent cover';cover.material.color.set('#3d4822');cover.material.transmission=.9;
    body.material.name='Golden neutral frosted thick glass';body.material.color.set('#eeeeee');body.material.transmission=1;body.material.roughness=.28;
    const secondPanel=new Three.Mesh(new Three.BoxGeometry(),cover.material);cover.add(secondPanel);
    const olive=cover.material.color.clone();
    api=await env.mount(env.host,{product,modelRequest:env.request(Promise.resolve(new ArrayBuffer(12)))});
    assert.ok(cover.material.attenuationColor.equals(olive));
    assert.ok(secondPanel.material.attenuationColor.equals(olive),'every panel retains the original tint even when the GLB shares one material');
    assert.ok(body.material.color.equals(new Three.Color('#eeeeee')));
    assert.equal(body.material.transmission,.94);
    assert.equal(body.material.roughness,.28);
    assert.equal(cover.material.roughness,.13,'the olive cover must retain its own smooth finish');
    assert.equal(body.castShadow,false);
  } finally {api?.dispose();env.close();}
});


test('B5 keeps the exported dropper complete and white base attached with four readable layers', async () => {
  const product=PACKAGING_PRODUCTS['poster-057'];
  const bytes=readFileSync(new URL('../packaging-assets/poster-057.glb',import.meta.url));
  const jsonLength=bytes.readUInt32LE(12),gltf=JSON.parse(bytes.toString('utf8',20,20+jsonLength));
  const tubeName='Hollow clear pipette with open tapered tip',bodyName='Hollow rounded flat B5 glass bottle';
  for(const [width,height] of [[1200,800],[393,520]]) {
    // Use actual exported positions, materials and parent transforms; no new production inspection API.
    const nodes=gltf.nodes.map(node=>{
      let object=new Three.Group();
      if('mesh' in node) {
        const primitive=gltf.meshes[node.mesh].primitives[0],accessor=gltf.accessors[primitive.attributes.POSITION];
        const view=gltf.bufferViews[accessor.bufferView],offset=28+jsonLength+(view.byteOffset??0)+(accessor.byteOffset??0);
        assert.equal(accessor.componentType,5126);assert.equal(accessor.type,'VEC3');
        const coordinates=new Float32Array(accessor.count*3);
        for(let i=0;i<accessor.count;i++)for(let axis=0;axis<3;axis++)coordinates[i*3+axis]=bytes.readFloatLE(offset+i*(view.byteStride??12)+axis*4);
        const geometry=new Three.BufferGeometry();geometry.setAttribute('position',new Three.BufferAttribute(coordinates,3));
        const source=gltf.materials[primitive.material],pbr=source.pbrMetallicRoughness,material=new Three.MeshPhysicalMaterial();
        material.name=source.name;material.color.fromArray(pbr.baseColorFactor??[1,1,1,1]);
        material.roughness=pbr.roughnessFactor;material.metalness=pbr.metallicFactor??1;
        material.transmission=source.extensions?.KHR_materials_transmission?.transmissionFactor??0;
        material.ior=source.extensions?.KHR_materials_ior?.ior??1.5;
        material.transparent=source.alphaMode==='BLEND';material.opacity=pbr.baseColorFactor?.[3]??1;
        if(pbr.baseColorTexture)material.map=new Three.Texture();
        object=new Three.Mesh(geometry,material);
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
    const loaded={scene:new Three.Group()};gltf.scenes[gltf.scene??0].nodes.forEach(i=>loaded.scene.add(nodes[i]));
    let camera,api;
    const env=harness({product,parse:()=>Promise.resolve(loaded),onRender:(_,value)=>{camera=value;}});
    try {
      Object.defineProperties(env.host,{clientWidth:{value:width},clientHeight:{value:height}});
      api=await env.mount(env.host,{product,modelRequest:env.request(Promise.resolve(new ArrayBuffer(12)))});
      const flush=()=>{const callbacks=[...env.frames.values()];env.frames.clear();callbacks.forEach(fn=>fn(16));loaded.scene.updateWorldMatrix(true,true);camera.updateMatrixWorld(true);};
      flush();
      const parts=Object.fromEntries(product.parts.map(part=>[part.key,loaded.scene.getObjectByName(part.node)]));
      assert.deepEqual(Object.keys(parts).sort(),['dropper','jar','label','print']);
      assert.equal(product.review,undefined,'retain the approved B5 material and lighting path');
      const tube=loaded.scene.getObjectByName(tubeName),body=loaded.scene.getObjectByName(bodyName);
      const print=loaded.scene.getObjectByName('Complete white B5 bottle printing'),relief=loaded.scene.getObjectByName('Raised liaose base lettering');
      assert.equal(tube.material.transmission,0);assert.equal(tube.material.transparent,true);assert.equal(tube.material.opacity,.38);assert.equal(tube.material.depthWrite,false);
      assert.equal(body.material.transmission,1);assert.equal(body.material.depthWrite,false);assert.ok(body.material.color.equals(new Three.Color('#ffffff')));
      assert.equal(print.renderOrder,3);assert.ok(print.material.color.equals(new Three.Color('#ffffff')));assert.equal(print.material.toneMapped,false);
      assert.equal(print.parent,parts.print);assert.equal(relief.parent,parts.print);
      const rest=Object.fromEntries(Object.entries(parts).map(([key,part])=>[key,{position:part.position.clone(),scale:part.scale.clone(),quaternion:part.quaternion.clone(),world:part.getWorldPosition(new Three.Vector3())}]));
      const fitted=[['dropper',['Closure','DropperBulb','Pipette']],['jar',['Body','Base']]].flatMap(([key,names])=>names.map(name=>{
        const part=loaded.scene.getObjectByName(name);assert.equal(part.parent,parts[key]);
        return {key,part,matrix:part.matrix.toArray(),world:part.getWorldPosition(new Three.Vector3())};
      }));
      const film=loaded.scene.getObjectByName('Transparent unprinted B5 label film');
      for(const progress of [0,.25,.5,.75,1,.5,0]) {
        api.setProgress(progress);flush();
        assert.equal(api.getState().renderedProgress,progress);
        assert.ok(parts.dropper.position.clone().sub(rest.dropper.position).distanceTo(new Three.Vector3(0,1.95*progress,0))<1e-9);
        for(const {key,part,matrix,world} of fitted) {
          const displacement=parts[key].getWorldPosition(new Three.Vector3()).sub(rest[key].world);
          assert.deepEqual(part.matrix.toArray(),matrix,'fitted dropper pieces and base keep their local transforms');
          assert.ok(part.getWorldPosition(new Three.Vector3()).sub(world).distanceTo(displacement)<1e-9);
        }
        assert.ok(Math.abs(camera.position.y-1.05-(1.45+.75*progress))<1e-9);
        const viewHeight=Math.max(4.2+2.1*progress,(3.8+2*progress)/(width/height));
        assert.ok(Math.abs(camera.top-camera.bottom-viewHeight)<1e-9);
        assert.ok(Math.abs(camera.position.x+1.65*progress)<1e-9);
        for(const [key,offset,growth] of [['label',[-1.4,.08,.65],.15],['print',[-3.1,.10,1.65],.95]]) {
          assert.ok(parts[key].position.clone().sub(rest[key].position).distanceTo(new Three.Vector3(...offset).multiplyScalar(progress))<1e-9);
          assert.ok(parts[key].scale.distanceTo(rest[key].scale.clone().multiplyScalar(1+growth*progress))<1e-9);
        }
        assert.ok(Math.abs((parts.print.position.z-rest.print.position.z)-(parts.label.position.z-rest.label.position.z)-progress)<1e-9);
        if(progress===0)assert.equal(film.material.opacity,.05);
        if(progress===1) {
          assert.equal(film.material.opacity,1);
          assert.ok(new Three.Box3().setFromObject(tube).min.y-new Three.Box3().setFromObject(body).max.y>.33,'the complete pipette fully clears the bottle neck');
        }
        for(const mesh of nodes.filter(node=>node.isMesh)) {
          mesh.geometry.computeBoundingBox();const {min,max}=mesh.geometry.boundingBox;
          for(const x of [min.x,max.x])for(const y of [min.y,max.y])for(const z of [min.z,max.z]) {
            const projected=new Three.Vector3(x,y,z).applyMatrix4(mesh.matrixWorld).project(camera);
            assert.ok(Math.abs(projected.x)<.98&&Math.abs(projected.y)<.98,`${mesh.name} stays in ${width}x${height} frame at ${progress}`);
          }
        }
        for(const key of progress===0?Object.keys(parts):['jar']) {
          assert.ok(parts[key].position.distanceTo(rest[key].position)<1e-9);
          assert.ok(parts[key].scale.distanceTo(rest[key].scale)<1e-9);
          assert.ok(1-Math.abs(parts[key].quaternion.dot(rest[key].quaternion))<1e-9);
        }
      }
    } finally {api?.dispose();env.close();}
  }
});

test('new clear overcaps retain neutral transmission without changing prior finishes', async () => {
  for(const toneMapped of [false,true]) {
    const base=PACKAGING_PRODUCTS['poster-066'];
    const product={...base,review:{...base.review,appearance:{...base.review.appearance,clearOvercap:false,overcapToneMapped:toneMapped}}};let loaded,api;
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

test('Pure Volume lifts one complete pump while the fitted cord stays on the bottle',async()=>{
  const product=PACKAGING_PRODUCTS['poster-051'];
  const bytes=readFileSync(new URL('../packaging-assets/poster-051.glb',import.meta.url));
  const gltf=JSON.parse(bytes.toString('utf8',20,20+bytes.readUInt32LE(12)));
  const tubeName='Hollow clear pump dip tube';
  let exportedTubeMaterial;
  const nodes=gltf.nodes.map(node=>{
    let object=new Three.Group();
    if('mesh' in node) {
      const accessor=gltf.accessors[gltf.meshes[node.mesh].primitives[0].attributes.POSITION];
      const low=new Three.Vector3(...accessor.min),high=new Three.Vector3(...accessor.max);
      const size=high.clone().sub(low),center=high.clone().add(low).multiplyScalar(.5);
      object=new Three.Mesh(new Three.BoxGeometry(...size.toArray()).translate(...center.toArray()),new Three.MeshPhysicalMaterial());
      if(node.name===tubeName) {
        exportedTubeMaterial=gltf.materials[gltf.meshes[node.mesh].primitives[0].material];
        const pbr=exportedTubeMaterial.pbrMetallicRoughness,extensions=exportedTubeMaterial.extensions;
        object.material.name=exportedTubeMaterial.name;
        object.material.color.fromArray(pbr.baseColorFactor??[1,1,1,1]);
        object.material.metalness=pbr.metallicFactor??1;
        object.material.roughness=pbr.roughnessFactor??1;
        object.material.transmission=extensions.KHR_materials_transmission.transmissionFactor;
        object.material.ior=extensions.KHR_materials_ior.ior;
        object.material.side=exportedTubeMaterial.doubleSided?Three.DoubleSide:Three.FrontSide;
      }
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
    assert.deepEqual(Object.keys(parts).sort(),['jar','label','print','pump']);
    assert.equal(product.review,undefined,'keep the original matte body, gold line and green artwork treatment');
    const tube=loaded.scene.getObjectByName(tubeName);
    assert.equal(tube.material.toneMapped,false,'the transparent wall must match the untonemapped backdrop');
    assert.equal(tube.castShadow,false);
    assert.equal(tube.receiveShadow,false);
    assert.equal(tube.material.transmission,exportedTubeMaterial.extensions.KHR_materials_transmission.transmissionFactor);
    assert.equal(tube.material.roughness,exportedTubeMaterial.pbrMetallicRoughness.roughnessFactor);
    assert.equal(tube.material.ior,exportedTubeMaterial.extensions.KHR_materials_ior.ior);
    assert.equal(tube.material.thickness,.0155,'transmission uses the thin plastic wall rather than a solid rod');
    assert.equal(tube.material.side,Three.FrontSide);
    assert.equal(loaded.scene.getObjectByName('Hollow ivory pouch body with soft gathered folds').material.toneMapped,true,'only the clear tube receives the backdrop correction');
    for(const mesh of nodes.filter(node=>node.isMesh)) {
      const fragmentShader='void main() {\n#include <dithering_fragment>\n}',shader={fragmentShader};
      mesh.material.onBeforeCompile(shader);
      if(mesh===tube) {
        assert.match(shader.fragmentShader,/float wallEdge = pow\([^\n]+, 9\.0\);/,'the transparent tube retains a readable thin rim');
        assert.match(shader.fragmentShader,/gl_FragColor\.rgb \*= 1\.0 - 0\.18 \* wallEdge/);
      } else assert.equal(shader.fragmentShader,fragmentShader,`${mesh.name} keeps its original shading`);
    }
    const rest=Object.fromEntries(Object.entries(parts).map(([key,part])=>[key,{position:part.position.clone(),scale:part.scale.clone(),quaternion:part.quaternion.clone(),world:part.getWorldPosition(new Three.Vector3())}]));
    const fitted=['Closure','PumpStem','Actuator',tubeName,'Body','Cord'].map(name=>{
      const part=loaded.scene.getObjectByName(name),key=['Body','Cord'].includes(name)?'jar':'pump';
      assert.equal(part.parent,name===tubeName ? loaded.scene.getObjectByName('Closure') : parts[key]);
      return {part,key,matrix:part.matrix.toArray(),world:part.getWorldPosition(new Three.Vector3())};
    });
    const film=loaded.scene.getObjectByName('Illustrative transparent curved label carrier');
    for(const progress of [0,.25,.5,.75,1,.5,0]) {
      api.setProgress(progress);flush();
      assert.equal(api.getState().renderedProgress,progress);
      assert.ok(parts.pump.position.clone().sub(rest.pump.position).distanceTo(new Three.Vector3(0,2.3*progress,0))<1e-9);
      for(const {part,key,matrix,world} of fitted) {
        assert.deepEqual(part.matrix.toArray(),matrix,'the fitted pump and cord retain their local transforms');
        const displacement=parts[key].getWorldPosition(new Three.Vector3()).sub(rest[key].world);
        assert.ok(part.getWorldPosition(new Three.Vector3()).sub(world).distanceTo(displacement)<1e-9);
        if(key==='jar')assert.ok(displacement.length()<1e-9,'the cord remains fixed to the stationary bottle');
      }
      assert.ok(Math.abs(camera.position.y-1.05-(1.45+1.15*progress))<1e-9);
      assert.ok(Math.abs(camera.top-camera.bottom-(4.2+2.3*progress))<1e-9);
      assert.ok(Math.abs(camera.position.x+.75*progress)<1e-9);
      for(const [key,offset,growth] of [['label',[-1.65,.08,.65],.15],['print',[-3.4,.18,1.65],.45]]) {
        assert.ok(parts[key].position.clone().sub(rest[key].position).distanceTo(new Three.Vector3(...offset).multiplyScalar(progress))<1e-9);
        assert.ok(parts[key].scale.distanceTo(rest[key].scale.clone().multiplyScalar(1+growth*progress))<1e-9);
      }
      if(progress===0)assert.equal(film.material.opacity,.05,'the clear carrier leaves no visible patch when closed');
      if(progress===1) {
        assert.equal(film.material.opacity,1,'the translucent carrier is visible separately when open');
        const tubeBounds=new Three.Box3().setFromObject(tube),bottleBounds=new Three.Box3().setFromObject(parts.jar);
        assert.ok(tubeBounds.min.y-bottleBounds.max.y>.4,'the inlet fully clears the bottle opening');
      }
      for(const mesh of nodes.filter(node=>node.isMesh)) {
        mesh.geometry.computeBoundingBox();
        const {min,max}=mesh.geometry.boundingBox;
        for(const x of [min.x,max.x])for(const y of [min.y,max.y])for(const z of [min.z,max.z]) {
          const projected=new Three.Vector3(x,y,z).applyMatrix4(mesh.matrixWorld).project(camera);
          assert.ok(Math.abs(projected.x)<.98 && Math.abs(projected.y)<.98,`${mesh.name} stays in frame at ${progress}`);
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

test('Gentle lifts its complete pump and hollow tube beneath the separate protective cover',async()=>{
  const product=PACKAGING_PRODUCTS['poster-044'];
  const bytes=readFileSync(new URL('../packaging-assets/poster-044.glb',import.meta.url));
  const gltf=JSON.parse(bytes.toString('utf8',20,20+bytes.readUInt32LE(12)));
  const tubeName='Hollow clear Gentle pump dip tube';
  const nodes=gltf.nodes.map(node=>{
    let object=new Three.Group();
    if('mesh' in node) {
      const primitive=gltf.meshes[node.mesh].primitives[0],accessor=gltf.accessors[primitive.attributes.POSITION];
      const low=new Three.Vector3(...accessor.min),high=new Three.Vector3(...accessor.max);
      const size=high.clone().sub(low),center=high.clone().add(low).multiplyScalar(.5);
      object=new Three.Mesh(new Three.BoxGeometry(...size.toArray()).translate(...center.toArray()),new Three.MeshPhysicalMaterial());
      if(node.name===tubeName) {
        const material=gltf.materials[primitive.material];
        object.material.name=material.name;
        object.material.transmission=material.extensions.KHR_materials_transmission.transmissionFactor;
        object.material.roughness=material.pbrMetallicRoughness.roughnessFactor;
        object.material.ior=material.extensions.KHR_materials_ior.ior;
      }
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
    assert.deepEqual(Object.keys(parts).sort(),['jar','label','overcap','print','pump']);
    assert.equal(product.review,undefined,'retain the approved clear bottle and frosted oval treatment');
    const tube=loaded.scene.getObjectByName(tubeName),head=loaded.scene.getObjectByName('Actuator');
    assert.equal(tube.parent,loaded.scene.getObjectByName('Closure'));
    assert.equal(tube.material.transmission,.98);
    assert.equal(tube.material.roughness,.06);
    assert.equal(tube.material.ior,1.46);
    assert.equal(tube.material.thickness,.0076);
    assert.equal(tube.material.side,Three.FrontSide);
    assert.equal(Boolean(tube.material.toneMapped),false,'the production legacy falsy flag keeps tube tone mapping disabled');
    assert.equal(tube.castShadow,false);
    assert.equal(tube.receiveShadow,false);
    const rest=Object.fromEntries(Object.entries(parts).map(([key,part])=>[key,{position:part.position.clone(),scale:part.scale.clone(),quaternion:part.quaternion.clone(),world:part.getWorldPosition(new Three.Vector3())}]));
    const fitted=['Closure','PumpStem','Actuator',tubeName].map(name=>{
      const part=loaded.scene.getObjectByName(name);
      if(name!==tubeName)assert.equal(part.parent,parts.pump);
      return {part,matrix:part.matrix.toArray(),world:part.getWorldPosition(new Three.Vector3())};
    });
    const diameter=new Three.Box3().setFromObject(parts.jar).getSize(new Three.Vector3()).x;
    for(const progress of [0,.25,.5,.75,1,.5,0]) {
      api.setProgress(progress);flush();
      assert.equal(api.getState().renderedProgress,progress);
      for(const [key,lift] of [['pump',2.15],['overcap',3.15]])
        assert.ok(parts[key].position.clone().sub(rest[key].position).distanceTo(new Three.Vector3(0,lift*progress,0))<1e-9);
      const displacement=parts.pump.getWorldPosition(new Three.Vector3()).sub(rest.pump.world);
      for(const {part,matrix,world} of fitted) {
        assert.deepEqual(part.matrix.toArray(),matrix,'all fitted pump pieces retain their local transforms');
        assert.ok(part.getWorldPosition(new Three.Vector3()).sub(world).distanceTo(displacement)<1e-9);
      }
      assert.ok(Math.abs(camera.position.y-1.05-(1.45+1.575*progress))<1e-9);
      assert.ok(Math.abs(camera.top-camera.bottom-(4.2+3*progress))<1e-9);
      assert.ok(Math.abs(camera.position.x+.65*progress)<1e-9);
      for(const [key,offset,growth] of [['label',[-1.25,.08,.65],.15],['print',[-2.65,.5,1.65],.95]]) {
        assert.ok(parts[key].position.clone().sub(rest[key].position).distanceTo(new Three.Vector3(...offset).multiplyScalar(progress))<1e-9);
        assert.ok(parts[key].scale.distanceTo(rest[key].scale.clone().multiplyScalar(1+growth*progress))<1e-9);
      }
      const coverBounds=new Three.Box3().setFromObject(parts.overcap),headBounds=new Three.Box3().setFromObject(head);
      assert.ok(coverBounds.max.y-.03*diameter>headBounds.max.y,'the cover ceiling never crosses the fitted pump head');
      if(progress===1) {
        const tubeBounds=new Three.Box3().setFromObject(tube),bottleBounds=new Three.Box3().setFromObject(parts.jar);
        assert.ok(tubeBounds.min.y-bottleBounds.max.y>.35,'the tube inlet fully clears the bottle');
        assert.ok(coverBounds.min.y-headBounds.max.y>.3,'the cover fully clears the intact pump');
      }
      for(const mesh of nodes.filter(node=>node.isMesh)) {
        mesh.geometry.computeBoundingBox();
        const {min,max}=mesh.geometry.boundingBox;
        for(const x of [min.x,max.x])for(const y of [min.y,max.y])for(const z of [min.z,max.z]) {
          const projected=new Three.Vector3(x,y,z).applyMatrix4(mesh.matrixWorld).project(camera);
          assert.ok(Math.abs(projected.x)<.98 && Math.abs(projected.y)<.98,`${mesh.name} stays in frame at ${progress}`);
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

test('Golden lifts its complete pump and hollow tube beneath the intact long-skirt cover',async()=>{
  const product=PACKAGING_PRODUCTS['poster-056'];
  const bytes=readFileSync(new URL('../packaging-assets/'+product.file,import.meta.url));
  const gltf=JSON.parse(bytes.toString('utf8',20,20+bytes.readUInt32LE(12)));
  const tubeName='Hollow clear Golden pump dip tube';
  const bodyName='Hollow rounded rectangular bottle with thick clear base';
  const nodes=gltf.nodes.map(node=>{
    let object=new Three.Group();
    if('mesh' in node) {
      const primitive=gltf.meshes[node.mesh].primitives[0],accessor=gltf.accessors[primitive.attributes.POSITION];
      const low=new Three.Vector3(...accessor.min),high=new Three.Vector3(...accessor.max);
      const size=high.clone().sub(low),center=high.clone().add(low).multiplyScalar(.5);
      object=new Three.Mesh(new Three.BoxGeometry(...size.toArray()).translate(...center.toArray()),new Three.MeshPhysicalMaterial());
      if(node.name===tubeName || node.name===bodyName) {
        const material=gltf.materials[primitive.material];
        object.material.name=material.name;
        object.material.transmission=material.extensions.KHR_materials_transmission.transmissionFactor;
        object.material.roughness=material.pbrMetallicRoughness.roughnessFactor;
        object.material.ior=material.extensions.KHR_materials_ior.ior;
      }
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
    assert.deepEqual(Object.keys(parts).sort(),['body','label','name','overcap','print','pump']);
    assert.equal(product.review.appearance.labelShadows,true);
    const tube=loaded.scene.getObjectByName(tubeName),head=loaded.scene.getObjectByName('Tall cylindrical press actuator');
    assert.equal(tube.parent,parts.pump);
    assert.equal(tube.material.transmission,0);
    assert.equal(tube.material.depthWrite,false);
    assert.equal(tube.material.roughness,.06);
    assert.ok(Math.abs(tube.material.ior-1.48)<1e-6);
    assert.equal(tube.material.side,Three.FrontSide);
    assert.equal(tube.castShadow,false);
    assert.equal(tube.receiveShadow,false);
    const body=loaded.scene.getObjectByName(bodyName);
    assert.ok(Math.abs(body.material.roughness-.255)<1e-6,'the real frosted bottle must not be overwritten by the generic polished-glass branch');
    assert.equal(body.material.transmission,.94,'frosting retains light transmission rather than becoming opaque white plastic');
    const rest=Object.fromEntries(Object.entries(parts).map(([key,part])=>[key,{position:part.position.clone(),scale:part.scale.clone(),quaternion:part.quaternion.clone(),world:part.getWorldPosition(new Three.Vector3())}]));
    const fitted=parts.pump.children.map(part=>{
      assert.equal(part.parent,parts.pump);
      return {part,matrix:part.matrix.toArray(),world:part.getWorldPosition(new Three.Vector3())};
    });
    const diameter=new Three.Box3().setFromObject(parts.body).getSize(new Three.Vector3()).x;
    for(const progress of [0,.25,.5,.75,1,.5,0]) {
      api.setProgress(progress);flush();
      assert.equal(api.getState().renderedProgress,progress);
      for(const key of ['pump','overcap']) {
        const t=key==='overcap'?Math.min(1,progress/.72):progress;
        const amount=key==='overcap'?t*t*(3-2*t):t;
        assert.ok(parts[key].position.clone().sub(rest[key].position).distanceTo(new Three.Vector3(...product.review.explosion.offsets[key]).multiplyScalar(amount))<1e-9);
      }
      const displacement=parts.pump.getWorldPosition(new Three.Vector3()).sub(rest.pump.world);
      for(const {part,matrix,world} of fitted) {
        assert.deepEqual(part.matrix.toArray(),matrix,'all fitted pump pieces retain their local transforms');
        assert.ok(part.getWorldPosition(new Three.Vector3()).sub(world).distanceTo(displacement)<1e-9);
      }
      for(const key of ['label','print','name']) {
        const offset=product.review.explosion.offsets[key],growth=product.review.explosion.scales[key]-1;
        assert.ok(parts[key].position.clone().sub(rest[key].position).distanceTo(new Three.Vector3(...offset).multiplyScalar(progress))<1e-9);
        assert.ok(parts[key].scale.distanceTo(rest[key].scale.clone().multiplyScalar(1+growth*progress))<1e-9);
      }
      const coverBounds=new Three.Box3().setFromObject(parts.overcap),headBounds=new Three.Box3().setFromObject(head);
      assert.ok(coverBounds.max.y-.03*diameter>headBounds.max.y,'the cover ceiling never crosses the fitted pump head');
      if(progress===1) {
        const tubeBounds=new Three.Box3().setFromObject(tube),bottleBounds=new Three.Box3().setFromObject(parts.body);
        assert.ok(tubeBounds.min.y-bottleBounds.max.y>.32,'the tube inlet fully clears the bottle');
        assert.ok(coverBounds.min.y-headBounds.max.y>.34,'the cover fully clears the intact pump');
      }
      for(const mesh of nodes.filter(node=>node.isMesh)) {
        mesh.geometry.computeBoundingBox();
        const {min,max}=mesh.geometry.boundingBox;
        for(const x of [min.x,max.x])for(const y of [min.y,max.y])for(const z of [min.z,max.z]) {
          const projected=new Three.Vector3(x,y,z).applyMatrix4(mesh.matrixWorld).project(camera);
          assert.ok(Math.abs(projected.x)<.98 && Math.abs(projected.y)<.98,`${mesh.name} stays in frame at ${progress}`);
        }
      }
      for(const key of progress===0 ? Object.keys(parts) : []) {
        assert.ok(parts[key].position.distanceTo(rest[key].position)<1e-9);
        assert.ok(parts[key].scale.distanceTo(rest[key].scale)<1e-9);
        assert.ok(1-Math.abs(parts[key].quaternion.dot(rest[key].quaternion))<1e-9);
      }
    }
  } finally {api?.dispose();env.close();}
});

test('Luminous keeps its actual long dropper intact and frames all four review layers on desktop and phone',async()=>{
  const product=PACKAGING_PRODUCTS['poster-058'];
  const bytes=readFileSync(new URL('../packaging-assets/poster-058.glb',import.meta.url));
  const jsonLength=bytes.readUInt32LE(12),gltf=JSON.parse(bytes.toString('utf8',20,20+jsonLength));
  const pipeName='Long hollow clear pipette without suspended formula';
  for(const [width,height] of [[1200,800],[393,520]]) {
    const nodes=gltf.nodes.map(node=>{
      let object=new Three.Group();
      if('mesh' in node) {
        const primitive=gltf.meshes[node.mesh].primitives[0],accessor=gltf.accessors[primitive.attributes.POSITION];
        const view=gltf.bufferViews[accessor.bufferView],offset=28+jsonLength+(view.byteOffset??0)+(accessor.byteOffset??0);
        assert.equal(accessor.componentType,5126);assert.equal(accessor.type,'VEC3');
        const coordinates=new Float32Array(accessor.count*3);
        for(let i=0;i<accessor.count;i++)for(let axis=0;axis<3;axis++)coordinates[i*3+axis]=bytes.readFloatLE(offset+i*(view.byteStride??12)+axis*4);
        const geometry=new Three.BufferGeometry();geometry.setAttribute('position',new Three.BufferAttribute(coordinates,3));
        const source=gltf.materials[primitive.material],pbr=source.pbrMetallicRoughness,material=new Three.MeshPhysicalMaterial();
        material.name=source.name;material.color.fromArray(pbr.baseColorFactor??[1,1,1,1]);
        material.roughness=pbr.roughnessFactor;material.metalness=pbr.metallicFactor??1;
        material.transmission=source.extensions?.KHR_materials_transmission?.transmissionFactor??0;
        material.ior=source.extensions?.KHR_materials_ior?.ior??1.5;
        material.transparent=source.alphaMode==='BLEND';material.opacity=pbr.baseColorFactor?.[3]??1;
        if(pbr.baseColorTexture)material.map=new Three.Texture();
        object=new Three.Mesh(geometry,material);
      }
      object.name=node.name;
      if(node.matrix)object.applyMatrix4(new Three.Matrix4().fromArray(node.matrix));
      else {
        object.position.fromArray(node.translation??[0,0,0]);object.quaternion.fromArray(node.rotation??[0,0,0,1]);object.scale.fromArray(node.scale??[1,1,1]);
      }
      return object;
    });
    gltf.nodes.forEach((node,i)=>node.children?.forEach(child=>nodes[i].add(nodes[child])));
    const loaded={scene:new Three.Group()};gltf.scenes[gltf.scene??0].nodes.forEach(i=>loaded.scene.add(nodes[i]));
    let camera,api;
    const env=harness({product,parse:()=>Promise.resolve(loaded),onRender:(_,value)=>{camera=value;}});
    try {
      Object.defineProperties(env.host,{clientWidth:{value:width},clientHeight:{value:height}});
      api=await env.mount(env.host,{product,modelRequest:env.request(Promise.resolve(new ArrayBuffer(12)))});
      const flush=()=>{const callbacks=[...env.frames.values()];env.frames.clear();callbacks.forEach(fn=>fn(16));loaded.scene.updateWorldMatrix(true,true);camera.updateMatrixWorld(true);};
      flush();
      const parts=Object.fromEntries(product.parts.map(part=>[part.key,loaded.scene.getObjectByName(part.node)]));
      assert.deepEqual(Object.keys(parts).sort(),['body','closure','label','print']);
      assert.equal(parts.closure.name,'DropperAssembly');
      assert.deepEqual(product.review.explosion.offsets.closure,[0,2.4,0]);
      const pipe=loaded.scene.getObjectByName(pipeName),body=loaded.scene.getObjectByName('Hollow slender flat Luminous glass bottle');
      const silver=loaded.scene.getObjectByName('Mirror silver hollow cylindrical collar');
      assert.equal(body.material.transmission,1);assert.ok(Math.abs(body.material.roughness-.024)<1e-6);assert.ok(body.material.color.equals(new Three.Color('#ffffff')));
      assert.equal(silver.material.metalness,1);assert.ok(Math.abs(silver.material.roughness-.075)<1e-6);
      assert.equal(pipe.material.transmission,0);assert.equal(pipe.material.opacity,.38);assert.equal(pipe.material.depthWrite,false);
      const rest=Object.fromEntries(Object.entries(parts).map(([key,part])=>[key,{position:part.position.clone(),scale:part.scale.clone(),quaternion:part.quaternion.clone(),world:part.getWorldPosition(new Three.Vector3())}]));
      const fitted=['Closure','DropperBulb','Pipette'].map(name=>{
        const part=loaded.scene.getObjectByName(name);assert.equal(part.parent,parts.closure);
        return {part,matrix:part.matrix.toArray(),world:part.getWorldPosition(new Three.Vector3())};
      });
      for(const progress of [0,.25,.5,.75,1,.5,0]) {
        api.setProgress(progress);flush();assert.equal(api.getState().renderedProgress,progress);
        const displacement=parts.closure.getWorldPosition(new Three.Vector3()).sub(rest.closure.world);
        assert.ok(displacement.distanceTo(new Three.Vector3(0,2.4*progress,0))<1e-9);
        for(const {part,matrix,world} of fitted) {
          assert.deepEqual(part.matrix.toArray(),matrix,'bulb, silver collar and long pipette keep their fitted transforms');
          assert.ok(part.getWorldPosition(new Three.Vector3()).sub(world).distanceTo(displacement)<1e-9);
        }
        for(const [key,offset,growth] of [['label',[-1.2,.08,.65],.15],['print',[-2.85,.15,1.65],.95]]) {
          const travel=new Three.Vector3(...offset);if(width<768)travel.x*=.5;
          assert.ok(parts[key].position.clone().sub(rest[key].position).distanceTo(travel.multiplyScalar(progress))<1e-9);
          assert.ok(parts[key].scale.distanceTo(rest[key].scale.clone().multiplyScalar(1+growth*progress))<1e-9);
        }
        assert.ok(Math.abs(parts.print.position.z-rest.print.position.z-(parts.label.position.z-rest.label.position.z)-progress)<1e-9);
        if(width>=768) {
          assert.ok(Math.abs(camera.position.y-1.05-(1.45+progress))<1e-9);
          assert.ok(Math.abs(camera.top-camera.bottom-(4.2+2.6*progress))<1e-9);
          assert.ok(Math.abs(camera.position.x+1.6*progress)<1e-9);
        }
        if(progress===1)assert.ok(new Three.Box3().setFromObject(pipe).min.y-new Three.Box3().setFromObject(body).max.y>.38,'the complete long dropper clears the bottle mouth');
        for(const mesh of nodes.filter(node=>node.isMesh)) {
          mesh.geometry.computeBoundingBox();const {min,max}=mesh.geometry.boundingBox;
          for(const x of [min.x,max.x])for(const y of [min.y,max.y])for(const z of [min.z,max.z]) {
            const projected=new Three.Vector3(x,y,z).applyMatrix4(mesh.matrixWorld).project(camera);
            assert.ok(Math.abs(projected.x)<.98&&Math.abs(projected.y)<.98,`${mesh.name} stays in ${width}x${height} frame at ${progress}`);
          }
        }
        for(const key of progress===0?Object.keys(parts):['body']) {
          assert.ok(parts[key].position.distanceTo(rest[key].position)<1e-9);assert.ok(parts[key].scale.distanceTo(rest[key].scale)<1e-9);
          assert.ok(1-Math.abs(parts[key].quaternion.dot(rest[key].quaternion))<1e-9);
        }
      }
    }finally{api?.dispose();env.close();}
  }
});

test('Essence Duo keeps both fitted droppers intact throughout desktop and phone motion',async()=>{
  const product=PACKAGING_PRODUCTS['poster-059'];
  const bytes=readFileSync(new URL('../packaging-assets/poster-059.glb',import.meta.url));
  const gltf=JSON.parse(bytes.toString('utf8',20,20+bytes.readUInt32LE(12)));
  for(const width of [1200,393]) {
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
  const env=harness({product,parse:()=>Promise.resolve(loaded)});let api;
  try {
    Object.defineProperties(env.host,{clientWidth:{value:width},clientHeight:{value:700}});
    api=await env.mount(env.host,{product,modelRequest:env.request(Promise.resolve(new ArrayBuffer(12)))});
    const flush=()=>{const callbacks=[...env.frames.values()];env.frames.clear();callbacks.forEach(fn=>fn(16));loaded.scene.updateWorldMatrix(true,true);};
    flush();const assembly=loaded.scene.getObjectByName('DropperAssembly');
    const fitted=['Closure','DropperBulb','Pipette'].map(name=>{const part=loaded.scene.getObjectByName(name);assert.equal(part.parent,assembly);return {part,matrix:part.matrix.toArray(),world:part.getWorldPosition(new Three.Vector3())};});
    const printed=loaded.scene.getObjectByName('LogoPrint'),label=loaded.scene.getObjectByName('PaperLabel');
    const printedRest=printed.position.clone(),labelRest=label.position.clone();
    const rest=api.getState().components;
    for(const value of [0,.25,.5,.75,1,.5,0]) {
      api.setProgress(value);flush();const state=api.getState();assert.equal(state.renderedProgress,value);
      for(const {part,matrix,world} of fitted) {
        assert.deepEqual(part.matrix.toArray(),matrix);
        assert.ok(part.getWorldPosition(new Three.Vector3()).sub(world).distanceTo(new Three.Vector3(0,1.75*value,0))<1e-8);
      }
      assert.ok(Math.abs((printed.position.z-printedRest.z)-(label.position.z-labelRest.z)-value)<1e-8);
      if(!value){assert.deepEqual(printed.position.toArray(),printedRest.toArray());assert.deepEqual(label.position.toArray(),labelRest.toArray());}
    }
    assert.deepEqual(rest.sort(),['body','closure','label','print']);
  }finally{api?.dispose();env.close();}
  }
});

for (const [id,lift] of [['poster-060',2.65],['poster-061',2.2],['poster-064',2.45],['poster-065',2.45],['poster-066',2.1]]) {
test(`${id} keeps its complete pumps and clear tubes intact throughout desktop and phone motion`,async()=>{
  const product=PACKAGING_PRODUCTS[id];
  const bytes=readFileSync(new URL(`../packaging-assets/${id}.glb`,import.meta.url));
  const gltf=JSON.parse(bytes.toString('utf8',20,20+bytes.readUInt32LE(12)));
  for(const width of [1200,393]) {
  const nodes=gltf.nodes.map(node=>{
    const object='mesh' in node ? new Three.Mesh(new Three.BoxGeometry(),new Three.MeshPhysicalMaterial()) : new Three.Group();
    object.name=node.name;
    if ('mesh' in node && (id==='poster-061' || id==='poster-064' || id==='poster-065' || id==='poster-066')) {
      const exported=gltf.materials[gltf.meshes[node.mesh].primitives[0].material];
      object.material.name=exported.name;
      object.material.transmission=exported.extensions?.KHR_materials_transmission?.transmissionFactor??0;
      object.material.roughness=exported.pbrMetallicRoughness.roughnessFactor;
      object.material.color.fromArray(exported.pbrMetallicRoughness.baseColorFactor??[1,1,1,1]);
    }
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
  const env=harness({product,parse:()=>Promise.resolve(loaded)});let api;
  try {
    Object.defineProperties(env.host,{clientWidth:{value:width},clientHeight:{value:700}});
    api=await env.mount(env.host,{product,modelRequest:env.request(Promise.resolve(new ArrayBuffer(12)))});
    const flush=()=>{const callbacks=[...env.frames.values()];env.frames.clear();callbacks.forEach(fn=>fn(16));loaded.scene.updateWorldMatrix(true,true);};
    flush();const assembly=loaded.scene.getObjectByName('PumpAssembly');
    const fitted=['Closure','PumpStem','Actuator'].map(name=>{const part=loaded.scene.getObjectByName(name);assert.equal(part.parent,assembly);return {part,matrix:part.matrix.toArray(),world:part.getWorldPosition(new Three.Vector3())};});
    if (id==='poster-061') {
      const body=loaded.scene.getObjectByName('Taller hollow frosted round-bottom bottle').material;
      assert.ok(Math.abs(body.transmission-.62)<.001 && Math.abs(body.roughness-.39)<.001);
      for (const prefix of ['Smaller','Taller']) {
        const tube=loaded.scene.getObjectByName(prefix+' hollow clear dip tube').material;
        assert.notEqual(tube,body);
        assert.equal(tube.transmission,1);assert.equal(tube.roughness,.06);
        assert.equal(tube.ior,1.46);assert.equal(tube.thickness,.0225);assert.equal(tube.side,Three.FrontSide);
        assert.equal(tube.specularIntensity,1);assert.equal(tube.envMapIntensity,1.2);
        const shader={fragmentShader:'#include <dithering_fragment>'};tube.onBeforeCompile(shader);
        assert.match(shader.fragmentShader,/float tubeEdge = pow\([^\n]+, 3\.0\);/);
        const bodyShader={fragmentShader:'#include <dithering_fragment>'};body.onBeforeCompile(bodyShader);
        assert.match(bodyShader.fragmentShader,/float wallEdge = pow\([^\n]+, 9\.0\);/);
      }
    }
    const printed=loaded.scene.getObjectByName('LogoPrint'),label=loaded.scene.getObjectByName('PaperLabel');
    const printedRest=printed.position.clone(),labelRest=label.position.clone();
    const tied = id==='poster-064' ? ['Body','Cord'].map(name=>{
      const part=loaded.scene.getObjectByName(name);assert.equal(part.parent,loaded.scene.getObjectByName('BottleAssembly'));
      return {part,matrix:part.matrix.toArray(),world:part.getWorldPosition(new Three.Vector3())};
    }) : [];
    if(id==='poster-064') {
      const tube=loaded.scene.getObjectByName('Hollow clear Aromatic dip tube').material;
      const body=loaded.scene.getObjectByName('Hollow matte yellow stepped rectangular bottle').material;
      assert.equal(body.transmission,0);assert.ok(Math.abs(body.roughness-.48)<.001);
      assert.equal(tube.transmission,1);assert.equal(tube.roughness,.06);assert.equal(tube.thickness,.02918);assert.equal(tube.side,Three.FrontSide);
      const shader={fragmentShader:'#include <dithering_fragment>'};tube.onBeforeCompile(shader);assert.match(shader.fragmentShader,/float tubeEdge/);
    }
    if(id==='poster-065') {
      for(const name of ['Front thin refill pouch skin','Rear thin refill pouch skin','Wide top heat seal']) {
        const film=loaded.scene.getObjectByName(name).material;
        assert.ok(film.transmission<.3,'Tinted pouch film must not become clear glass.');
        assert.ok(film.color.r>film.color.g && film.color.g>film.color.b && film.color.r-film.color.b>.25,'Keep the warm pouch substrate colour in the renderer.');
        assert.ok(film.roughness>.18 && film.roughness<.35);
      }
      const tube=loaded.scene.getObjectByName('Open hollow dip tube').material;
      const body=loaded.scene.getObjectByName('Hollow round shampoo bottle with sloping shoulder').material;
      assert.equal(body.transmission,1);assert.ok(Math.abs(body.roughness-.027)<.001);
      assert.equal(tube.transmission,1);assert.equal(tube.roughness,.06);assert.equal(tube.thickness,.01868);assert.equal(tube.side,Three.FrontSide);
      const shader={fragmentShader:'#include <dithering_fragment>'};tube.onBeforeCompile(shader);assert.match(shader.fragmentShader,/float tubeEdge/);
    }
    if(id==='poster-066') {
      const tube=loaded.scene.getObjectByName('Hollow clear Rose dip tube').material;
      const body=loaded.scene.getObjectByName('Hollow flat rectangular rose bottle with thick base').material;
      const gold=loaded.scene.getObjectByName('Gold base ring and tapered pump housing').material;
      const head=loaded.scene.getObjectByName('White cylindrical press head').material;
      assert.ok(Math.abs(gold.roughness-.30)<.001);assert.equal(gold.envMapIntensity,.65);
      assert.ok(Math.abs(head.roughness-.32)<.001);assert.equal(head.envMapIntensity,.3);assert.equal(head.specularIntensity,.3);
      assert.equal(body.transmission,1);assert.ok(Math.abs(body.roughness-.024)<.001);
      assert.equal(tube.transmission,1);assert.equal(tube.roughness,.06);assert.equal(tube.thickness,.02949);assert.equal(tube.side,Three.FrontSide);
      const shader={fragmentShader:'#include <dithering_fragment>'};tube.onBeforeCompile(shader);assert.match(shader.fragmentShader,/float tubeEdge/);
    }
    const overcap=loaded.scene.getObjectByName('Overcap');const overcapRest=overcap?.position.clone(),assemblyRest=assembly.position.clone();
    const rest=api.getState().components;
    for(const value of [0,.25,.5,.75,1,.5,0]) {
      api.setProgress(value);flush();const state=api.getState();assert.equal(state.renderedProgress,value);
      const pumpTime=id==='poster-066' ? Math.max(0,Math.min(1,(value-.1)/.9)) : value;
      const pumpProgress=id==='poster-066' ? pumpTime*pumpTime*(3-2*pumpTime) : value;
      if(id==='poster-066') assert.ok(overcap.position.y-overcapRest.y>=assembly.position.y-assemblyRest.y,'cover leads complete pump');
      for(const {part,matrix,world} of fitted) {
        assert.deepEqual(part.matrix.toArray(),matrix);
        assert.ok(part.getWorldPosition(new Three.Vector3()).sub(world).distanceTo(new Three.Vector3(0,lift*pumpProgress,0))<1e-8);
      }
      for(const {part,matrix,world} of tied) {assert.deepEqual(part.matrix.toArray(),matrix);assert.ok(part.getWorldPosition(new Three.Vector3()).distanceTo(world)<1e-8,'cord remains tied to bottle');}
      assert.ok(Math.abs((printed.position.z-printedRest.z)-(label.position.z-labelRest.z)-value)<1e-8);
      if(!value){assert.deepEqual(printed.position.toArray(),printedRest.toArray());assert.deepEqual(label.position.toArray(),labelRest.toArray());}
    }
    assert.deepEqual(rest.sort(),id==='poster-066' ? ['closure','jar','label','overcap','print'] : id==='poster-065' ? ['closure','jar','label','print','refill'] : id==='poster-064' ? ['closure','jar','label','print'] : ['body','closure','label','print']);
  }finally{api?.dispose();env.close();}
  }
});

}
 test('reference glass reflection tuning is limited to the explicitly approved bottles',async()=>{
  for(const enabled of [true,false]){
    const product=structuredClone(PACKAGING_PRODUCTS['poster-072']);product.review.appearance.referenceGlass=enabled;let loaded,api;
    const env=harness({product,parse:()=>Promise.resolve(loaded)});
    try{loaded=env.model();const body=loaded.scene.getObjectByName('Body');body.material.transmission=1;api=await env.mount(env.host,{product,modelRequest:env.request(Promise.resolve(new ArrayBuffer(12)))});assert.equal(body.material.envMapIntensity,enabled?.75:.3);assert.equal(body.material.specularIntensity,enabled?.8:.35);assert.equal(body.material.thickness,enabled?.045:.08);}finally{api?.dispose();env.close();}
  }
  assert.deepEqual(Object.entries(PACKAGING_PRODUCTS).filter(([,p])=>p.review?.appearance.referenceGlass).map(([id])=>id).sort(),['poster-012','poster-067','poster-068','poster-072','poster-073','poster-081','poster-084']);
 });

 test('Body Oil glass refinement stays on the hollow bottle and preserves shared cap material',async()=>{
  const product=PACKAGING_PRODUCTS['poster-073'];let loaded,api;
  const env=harness({product,parse:()=>Promise.resolve(loaded)});
  try{
    loaded=env.model();const body=loaded.scene.getObjectByName('Body'),cap=loaded.scene.getObjectByName('Closure');
    body.material.transmission=1;cap.material=body.material;
    api=await env.mount(env.host,{product,modelRequest:env.request(Promise.resolve(new ArrayBuffer(12)))});
    assert.notEqual(body.material,cap.material);assert.equal(body.material.side,Three.DoubleSide);
    assert.equal(body.material.transmission,1);assert.equal(body.material.ior,1.52);
    assert.equal(body.material.roughness,.018);assert.equal(body.material.thickness,.12);
    assert.equal(cap.material.ior,1.48);assert.equal(cap.material.envMapIntensity,.75);
    const shader={fragmentShader:'#include <dithering_fragment>'};body.material.onBeforeCompile(shader);
    assert.ok(shader.fragmentShader.includes('1.0 - .08 * wallEdge'));
    assert.deepEqual(api.getState().components.sort(),['body','closure','label','name','print']);
  }finally{api?.dispose();env.close();}
 });

test('Rose uses native 2x detail without increasing other model rendering budgets',async()=>{
  for(const id of ['poster-066','poster-065']) {
    const product=PACKAGING_PRODUCTS[id],h=harness({product});
    Object.defineProperty(h.dom.window,'devicePixelRatio',{value:2});
    try {
      const api=await h.mount(h.host,{product,modelRequest:h.request(Promise.resolve(new ArrayBuffer(8)))});
      assert.deepEqual(h.events.find(e=>Array.isArray(e)&&e[0]==='pixelRatio'),['pixelRatio',id==='poster-066'?2:1.75]);
      api.dispose();
    } finally {h.close();}
  }
});

test('Hand Gel keeps the opaque woven sleeve in refraction and composites its nested clear tube only for 081',async()=>{
  const template=JSON.parse(readFileSync(new URL('../model-source/collection/poster-081/review-product.json',import.meta.url),'utf8'));
  for(const file of ['poster-081-v1.glb','unrelated-review.glb']) {
    const product={...template,file};let loaded,api;
    const env=harness({product,parse:()=>Promise.resolve(loaded)});
    try {
      loaded={scene:new Three.Group()};
      const groups=Object.fromEntries(product.parts.map(part=>{const group=new Three.Group();group.name=part.node;loaded.scene.add(group);return [part.key,group];}));
      const mesh=(key,name,values)=>{const m=new Three.MeshPhysicalMaterial(values);m.name=name;const o=new Three.Mesh(new Three.BoxGeometry(.2,.2,.2),m);groups[key].add(o);return o;};
      const body=mesh('body','Crystal clear glass | thick heel',{transmission:1,roughness:.02});
      const tube=mesh('pump','Transparent polyethylene dip tube',{transmission:.83,roughness:.12});
      const sleeve=mesh('label','Warm ivory woven label',{map:new Three.Texture(),transparent:true});
      const flag=mesh('label','Black woven side flag',{map:new Three.Texture(),transparent:true});
      const sideInk=mesh('label','Ivory wordmark attached to black side flag',{map:new Three.Texture(),transparent:true});
      api=await env.mount(env.host,{product,modelRequest:env.request(Promise.resolve(new ArrayBuffer(12)))});
      const target=file==='poster-081-v1.glb';
      assert.equal(body.material.transmission,1,'the hollow glass remains physically transmissive');
      assert.equal(body.material.side,target?Three.FrontSide:Three.DoubleSide);
      assert.equal(body.material.depthWrite,!target);
      for(const cloth of [sleeve,flag]) {assert.equal(cloth.material.transparent,!target);assert.equal(cloth.material.depthWrite,target);}
      assert.equal(sideInk.material.transparent,true,'the wordmark carrier keeps its transparent background');
      assert.equal(tube.material.transmission,target?0:.83);
      assert.equal(tube.material.transparent,target);
      assert.equal(tube.material.depthWrite,!target);
      if(target) {
        assert.equal(tube.material.opacity,.55);assert.equal(tube.renderOrder,1);
        const shader={fragmentShader:'#include <dithering_fragment>'};tube.material.onBeforeCompile(shader);
        assert.match(shader.fragmentShader,/gl_FragColor\.a \*= mix\(\.35, 1\.0, tubeEdge\)/);
      }
    } finally {api?.dispose();env.close();}
  }
});

test('Body Care Duo has one lid signature, independent of the bare paper lid', () => {
  const bytes = readFileSync(new URL('../packaging-assets/poster-079-v2.glb', import.meta.url));
  const gltf = JSON.parse(bytes.toString('utf8', 20, 20 + bytes.readUInt32LE(12)));
  const children = name => gltf.nodes.find(n => n.name === name).children.map(i => gltf.nodes[i].name);
  assert.deepEqual(children('Lid'), ['Lid profile']);
  assert.deepEqual(children('LidInk'), ['Lid signature']);
  assert.equal(gltf.nodes.filter(n => n.name === 'Lid signature').length, 1);
  const {lidInk, lid} = PACKAGING_PRODUCTS['poster-079'].review.explosion.offsets;
  assert.ok(lidInk[1] - lid[1] > 1.5 && lidInk[2] - lid[2] > 1);
});

for (const width of [393,850]) test(`Bath Trio retains its exploded pose and clear print layers at ${width}px`,async()=>{
  const product=JSON.parse(readFileSync(new URL('../model-source/collection/poster-080/review-product.json',import.meta.url),'utf8'));
  const bytes=readFileSync(new URL('../packaging-assets/'+product.file,import.meta.url));
  const gltf=JSON.parse(bytes.toString('utf8',20,20+bytes.readUInt32LE(12)));
  assert.equal(product.finishes[0].scene,'soap','review starts on the approved white bottle');
  assert.equal(gltf.scenes[gltf.scene].name,'soap','standalone GLB also opens the white bottle');
  const models=gltf.scenes.map(scene=>{
    const group=new Three.Group();group.name=scene.name;
    for(const index of scene.nodes) {
      const node=gltf.nodes[index],part=new Three.Group();
      part.userData={...node.extras};part.position.fromArray(node.translation);
      part.name=node.name;group.add(part);
      const material=new Three.MeshPhysicalMaterial();
      if(node.extras.partKey==='Label') {material.transparent=true;material.opacity=.014;}
      part.add(new Three.Mesh(new Three.BoxGeometry(.1,.1,.1),material));
    }
    return group;
  });
  const loaded={scene:models[gltf.scene],scenes:models};
  const env=harness({product,parse:()=>Promise.resolve(loaded)});let api;
  try {
    Object.defineProperties(env.host,{clientWidth:{value:width},clientHeight:{value:800}});
    api=await env.mount(env.host,{product,modelRequest:env.request(Promise.resolve(bytes))});
    const flush=()=>{const callbacks=[...env.frames.values()];env.frames.clear();callbacks.forEach(fn=>fn(16));};
    const part=(model,key)=>model.children.find(child=>child.userData.partKey===key);
    const tubeY=part(models[0],'Pump').position.y, labelZ=part(models[0],'Label').position.z;
    api.rotate();api.setProgress(1);flush();
    for (const scene of ['soap','baby','after']) {
      api.setFinish(scene);flush();
      const active=models.find(m=>m.name===scene);
      assert.deepEqual(models.filter(m=>m.parent),[active]);
      assert.equal(api.getState().renderedProgress,1);
      assert.equal(api.getState().yaw,Math.PI/2);
      assert.equal(api.getState().finish,scene);
      assert.ok(Math.abs(part(active,'Pump').position.y-(tubeY+product.review.explosion.offsets.pump[1]))<1e-8);
      assert.ok(part(active,'Label').position.z>labelZ);
      assert.ok(part(active,'NameInk').position.z>part(active,'LogoInk').position.z);
      assert.ok(part(active,'LogoInk').position.z>part(active,'Label').position.z);
      for(const key of ['label','logo','print']) {
        const layer=part(active,product.parts.find(p=>p.key===key).node);
        assert.equal(layer.children[0].castShadow,false);
        assert.equal(layer.children[0].receiveShadow,false);
        const x=product.review.explosion.offsets[key][0]*(width<768?.9:1);
        assert.ok(Math.abs(layer.position.x-x)<1e-8);
      }
      assert.equal(part(active,'Body').children[0].castShadow,true);
      assert.equal(part(active,'Label').children[0].material.opacity,.17);
    }
    api.setFinish(product.finishes[0].scene);api.setProgress(0);flush();
    assert.equal(part(models[0],'Pump').position.y,tubeY);
    assert.equal(part(models[0],'Label').children[0].material.opacity,.014);
    assert.equal(env.events.filter(e=>e==='parse').length,1);
  } finally {api?.dispose();env.close();}
});

for (const width of [393,1200]) test(`Soap Duo moves complete assemblies and distinct print layers at ${width}px`,async()=>{
  const product=JSON.parse(readFileSync(new URL('../model-source/collection/poster-082/review-product.json',import.meta.url),'utf8'));
  const bytes=readFileSync(new URL('../packaging-assets/'+product.file,import.meta.url));
  const gltf=JSON.parse(bytes.toString('utf8',20,20+bytes.readUInt32LE(12)));
  const nodes=gltf.nodes.map(node=>{
    const object='mesh' in node ? new Three.Mesh(new Three.BoxGeometry(.1,.1,.1),new Three.MeshPhysicalMaterial()) : new Three.Group();
    object.name=node.name;object.userData={...node.extras};
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
    Object.defineProperties(env.host,{clientWidth:{value:width},clientHeight:{value:800}});
    api=await env.mount(env.host,{product,modelRequest:env.request(Promise.resolve(bytes))});
    const parts=Object.fromEntries(product.parts.map(p=>[p.key,loaded.scene.getObjectByName(p.node)]));
    assert.equal(Object.keys(parts).length,6);
    const rest=Object.fromEntries(Object.entries(parts).map(([key,part])=>[key,part.position.clone()]));
    const pumpChildren=parts.pump.children.map(child=>child.position.toArray());
    const flush=()=>{const frames=[...env.frames.values()];env.frames.clear();frames.forEach(fn=>fn(16));};
    for(const progress of [.5,1,0]) {
      api.setProgress(progress);flush();
      assert.equal(api.getState().renderedProgress,progress);
      for(const [key,offset] of Object.entries(product.review.explosion.offsets)) {
        const expected=new Three.Vector3(...offset).multiplyScalar(progress);
        if(width<768&&['label','logo','print'].includes(key))expected.x*=product.review.explosion.mobilePrintSpread;
        assert.ok(parts[key].position.clone().sub(rest[key]).distanceTo(expected)<1e-8,`${key} movement`);
      }
      assert.deepEqual(parts.pump.children.map(child=>child.position.toArray()),pumpChildren,'dip tube and actuator remain a complete pump');
      if(progress) {
        const travel=key=>parts[key].position.z-rest[key].z;
        assert.ok(travel('print')>travel('logo')&&travel('logo')>travel('label'),'names, logos and base printing occupy distinct depths');
        assert.ok(parts.cap.position.y<rest.cap.y&&parts.pump.position.y>rest.pump.y);
      }
    }
  } finally {api?.dispose();env.close();}
});


for(const id of ['085','086']) test(`poster-${id} preserves physical label shadows without opaque ink quads`,async()=>{
 const product=JSON.parse(readFileSync(new URL(`../model-source/collection/poster-${id}/review-product.json`,import.meta.url),'utf8'));
 const bytes=readFileSync(new URL('../packaging-assets/'+product.file,import.meta.url));
 const gltf=JSON.parse(bytes.toString('utf8',20,20+bytes.readUInt32LE(12)));
 const model=new Three.Group(); const meshes={};
 for(const part of product.parts){
  const group=new Three.Group();group.name=part.node;model.add(group);
  const node=gltf.nodes.find(n=>n.name===part.node);assert.ok(node);
  if(node.translation)group.position.fromArray(node.translation);
  const material=new Three.MeshPhysicalMaterial();
  if(['label','logo','print'].includes(part.key))material.map=new Three.Texture();
  if(['logo','print'].includes(part.key))material.transparent=true;
  const mesh=new Three.Mesh(new Three.BoxGeometry(.1,.1,.1),material);group.add(mesh);meshes[part.key]=mesh;
 }
 const env=harness({product,parse:()=>Promise.resolve({scene:model})});let api;
 try{
  api=await env.mount(env.host,{product,modelRequest:env.request(Promise.resolve(bytes))});
  assert.equal(meshes.label.castShadow,true,'opaque image-textured physical label casts');
  assert.equal(meshes.body.receiveShadow,true,'bottle receives label shadow');
  assert.equal(meshes.logo.castShadow,false);assert.equal(meshes.print.castShadow,false);
 }finally{api?.dispose();env.close();}
});

test('Amber Ginger v2 keeps pump fitted, separates ink and preserves weak film shadows',async()=>{
 const product=JSON.parse(readFileSync(new URL('../model-source/collection/poster-067/v2/review-product.json',import.meta.url),'utf8'));
 const bytes=readFileSync(new URL('../packaging-assets/'+product.file,import.meta.url));
 const gltf=JSON.parse(bytes.toString('utf8',20,20+bytes.readUInt32LE(12)));
 const nodes=gltf.nodes.map(n=>{
  const m=new Three.MeshPhysicalMaterial();m.name=gltf.materials?.[gltf.meshes?.[n.mesh]?.primitives[0]?.material]?.name??'';
  if(/carrier|print|label/i.test(n.name)){m.map=new Three.Texture();m.transparent=true;}
  const o='mesh' in n?new Three.Mesh(new Three.BoxGeometry(.1,.1,.1),m):new Three.Group();o.name=n.name;
  if(n.matrix)o.applyMatrix4(new Three.Matrix4().fromArray(n.matrix));else{o.position.fromArray(n.translation??[0,0,0]);o.quaternion.fromArray(n.rotation??[0,0,0,1]);o.scale.fromArray(n.scale??[1,1,1]);}return o;
 });
 gltf.nodes.forEach((n,i)=>n.children?.forEach(j=>nodes[i].add(nodes[j])));
 const model=new Three.Group();gltf.scenes[gltf.scene??0].nodes.forEach(i=>model.add(nodes[i]));
 const parts=Object.fromEntries(product.parts.map(p=>[p.key,model.getObjectByName(p.node)]));
 assert.deepEqual(model.children.map(o=>o.name).sort(),product.parts.map(p=>p.node).sort());
 const tube=model.getObjectByName('Long transparent hollow suction tube');assert.equal(tube.parent,parts.pump);
 const pumpPieces=[...parts.pump.children];assert.ok(pumpPieces.length>=4);
 const cord=parts.body.children.filter(o=>/cord|braid/i.test(o.name));assert.ok(cord.length>0);
 const env=harness({product,parse:()=>Promise.resolve({scene:model})});let api;
 try{
  api=await env.mount(env.host,{product,modelRequest:env.request(Promise.resolve(bytes))});
  const flush=()=>{const fs=[...env.frames.values()];env.frames.clear();fs.forEach(fn=>fn(16));model.updateWorldMatrix(true,true);};flush();
  const rest=Object.fromEntries(Object.entries(parts).map(([k,p])=>[k,p.position.clone()]));
  const fitted=pumpPieces.concat(cord).map(o=>o.matrix.toArray());
  const label=parts.label.children.find(o=>o.isMesh);assert.equal(label.castShadow,true);assert.equal(label.customDepthMaterial.alphaHash,true);
  assert.equal(label.customDepthMaterial.map,label.material.map);
  for(const p of [0,.5,1,.5,0]){
   api.setProgress(p);flush();
   pumpPieces.concat(cord).forEach((o,i)=>assert.deepEqual(o.matrix.toArray(),fitted[i]));
   assert.ok(Math.abs(parts.pump.position.y-rest.pump.y-2.25*p)<1e-8);
   const z=k=>parts[k].position.z-rest[k].z;
   if(p>0){assert.ok(z('print')>z('logo'));assert.ok(z('logo')>z('label'));}
   assert.equal(label.customDepthMaterial.opacity,label.material.opacity);
  }
  for(const k of ['logo','print'])parts[k].traverse(o=>{if(o.isMesh)assert.equal(o.castShadow,false);});
  let disposed=0;label.customDepthMaterial.addEventListener('dispose',()=>disposed++);api.dispose();api=null;assert.equal(disposed,1);
 }finally{api?.dispose();env.close();}
 assert.equal(PACKAGING_PRODUCTS['poster-067'].file,product.file,'approved registry selects the reviewed version');
});

test('Essence Water v2 keeps cap fitted, separates ink and preserves weak film shadows',async()=>{
 const product=JSON.parse(readFileSync(new URL('../model-source/collection/poster-068/v2/review-product.json',import.meta.url),'utf8'));
 const bytes=readFileSync(new URL('../packaging-assets/'+product.file,import.meta.url));
 const gltf=JSON.parse(bytes.toString('utf8',20,20+bytes.readUInt32LE(12)));
 const nodes=gltf.nodes.map(n=>{
  const m=new Three.MeshPhysicalMaterial();m.name=gltf.materials?.[gltf.meshes?.[n.mesh]?.primitives[0]?.material]?.name??'';
  if(/carrier|print|label/i.test(n.name)){m.map=new Three.Texture();m.transparent=true;}
  const o='mesh' in n?new Three.Mesh(new Three.BoxGeometry(.1,.1,.1),m):new Three.Group();o.name=n.name;
  if(n.matrix)o.applyMatrix4(new Three.Matrix4().fromArray(n.matrix));else{o.position.fromArray(n.translation??[0,0,0]);o.quaternion.fromArray(n.rotation??[0,0,0,1]);o.scale.fromArray(n.scale??[1,1,1]);}return o;
 });
 gltf.nodes.forEach((n,i)=>n.children?.forEach(j=>nodes[i].add(nodes[j])));
 const model=new Three.Group();gltf.scenes[gltf.scene??0].nodes.forEach(i=>model.add(nodes[i]));
 const parts=Object.fromEntries(product.parts.map(p=>[p.key,model.getObjectByName(p.node)]));
 assert.deepEqual(model.children.map(o=>o.name).sort(),product.parts.map(p=>p.node).sort());
 const capPieces=[...parts.cap.children];assert.equal(capPieces.length,3);
 assert.ok(capPieces.some(o=>/Silver neck/.test(o.name)));
 assert.ok(capPieces.some(o=>/concealed/i.test(o.name)));
 assert.ok(capPieces.some(o=>/Lavender cap/.test(o.name)));
 const env=harness({product,parse:()=>Promise.resolve({scene:model})});let api;
 try{
  api=await env.mount(env.host,{product,modelRequest:env.request(Promise.resolve(bytes))});
  const flush=()=>{const fs=[...env.frames.values()];env.frames.clear();fs.forEach(fn=>fn(16));model.updateWorldMatrix(true,true);};flush();
  const rest=Object.fromEntries(Object.entries(parts).map(([k,p])=>[k,p.position.clone()]));
  const fitted=capPieces.map(o=>o.matrix.toArray());
  const label=parts.label.children.find(o=>o.isMesh);assert.equal(label.castShadow,true);assert.equal(label.customDepthMaterial.alphaHash,true);
  assert.equal(label.customDepthMaterial.map,label.material.map);
  for(const p of [0,.5,1,.5,0]){
   api.setProgress(p);flush();
   capPieces.forEach((o,i)=>assert.deepEqual(o.matrix.toArray(),fitted[i]));
   assert.ok(Math.abs(parts.cap.position.y-rest.cap.y-1.4*p)<1e-8);
   const z=k=>parts[k].position.z-rest[k].z;
   if(p>0){assert.ok(z('print')>z('logo'));assert.ok(z('logo')>z('label'));}
   assert.equal(label.customDepthMaterial.opacity,label.material.opacity);
  }
  for(const k of ['logo','print'])parts[k].traverse(o=>{if(o.isMesh)assert.equal(o.castShadow,false);});
  let disposed=0;label.customDepthMaterial.addEventListener('dispose',()=>disposed++);api.dispose();api=null;assert.equal(disposed,1);
 }finally{api?.dispose();env.close();}
 assert.notEqual(PACKAGING_PRODUCTS['poster-068'].file,product.file,'historical v2 is not the approved version');
});

test('Essence Water v3 keeps the collar on the bottle and opens the complete cap and reducer',async()=>{
 const product=JSON.parse(readFileSync(new URL('../model-source/collection/poster-068/v3/review-product.json',import.meta.url),'utf8'));
 const bytes=readFileSync(new URL('../packaging-assets/'+product.file,import.meta.url));
 const gltf=JSON.parse(bytes.toString('utf8',20,20+bytes.readUInt32LE(12)));
 const nodes=gltf.nodes.map(n=>{
  const m=new Three.MeshPhysicalMaterial();m.name=gltf.materials?.[gltf.meshes?.[n.mesh]?.primitives[0]?.material]?.name??'';
  if(/carrier|print|label/i.test(n.name)){m.map=new Three.Texture();m.transparent=true;}
  const o='mesh' in n?new Three.Mesh(new Three.BoxGeometry(.1,.1,.1),m):new Three.Group();o.name=n.name;
  if(n.matrix)o.applyMatrix4(new Three.Matrix4().fromArray(n.matrix));else{o.position.fromArray(n.translation??[0,0,0]);o.quaternion.fromArray(n.rotation??[0,0,0,1]);o.scale.fromArray(n.scale??[1,1,1]);}return o;
 });
 gltf.nodes.forEach((n,i)=>n.children?.forEach(j=>nodes[i].add(nodes[j])));
 const model=new Three.Group();gltf.scenes[gltf.scene??0].nodes.forEach(i=>model.add(nodes[i]));
 const parts=Object.fromEntries(product.parts.map(p=>[p.key,model.getObjectByName(p.node)]));
 assert.deepEqual(model.children.map(o=>o.name).sort(),product.parts.map(p=>p.node).sort());
 const capPieces=[...parts.cap.children];assert.equal(capPieces.length,5);
 assert.equal(model.getObjectByName('Silver neck ring').parent,parts.body);
 assert.ok(model.getObjectByName('Glass external neck thread'));
 assert.equal(parts.reducer.children.length,1);
 assert.ok(capPieces.some(o=>/inner cap cup/.test(o.name)));
 assert.ok(capPieces.some(o=>/internal mating screw/.test(o.name)));
 assert.ok(capPieces.some(o=>/sealing pin/.test(o.name)));

 assert.ok(capPieces.some(o=>/Lavender cap/.test(o.name)));
 const env=harness({product,parse:()=>Promise.resolve({scene:model})});let api;
 try{
  api=await env.mount(env.host,{product,modelRequest:env.request(Promise.resolve(bytes))});
  const flush=()=>{const fs=[...env.frames.values()];env.frames.clear();fs.forEach(fn=>fn(16));model.updateWorldMatrix(true,true);};flush();
  const rest=Object.fromEntries(Object.entries(parts).map(([k,p])=>[k,p.position.clone()]));
  const fitted=capPieces.map(o=>o.matrix.toArray());
  const collar=model.getObjectByName('Silver neck ring'),collarFit=collar.matrix.toArray();
  const label=parts.label.children.find(o=>o.isMesh);assert.equal(label.castShadow,true);assert.equal(label.customDepthMaterial.alphaHash,true);
  assert.equal(label.customDepthMaterial.map,label.material.map);
  for(const p of [0,.5,1,.5,0]){
   api.setProgress(p);flush();
   capPieces.forEach((o,i)=>assert.deepEqual(o.matrix.toArray(),fitted[i]));
   assert.ok(Math.abs(parts.cap.position.y-rest.cap.y-1.4*p)<1e-8);
   assert.ok(Math.abs(parts.reducer.position.y-rest.reducer.y-.57*p)<1e-8);
   assert.deepEqual(collar.matrix.toArray(),collarFit);
   if(p===1)assert.ok(parts.cap.position.y-rest.cap.y>parts.reducer.position.y-rest.reducer.y);
   const z=k=>parts[k].position.z-rest[k].z;
   if(p>0){assert.ok(z('print')>z('logo'));assert.ok(z('logo')>z('label'));}
   assert.equal(label.customDepthMaterial.opacity,label.material.opacity);
  }
  for(const k of ['logo','print'])parts[k].traverse(o=>{if(o.isMesh)assert.equal(o.castShadow,false);});
  let disposed=0;label.customDepthMaterial.addEventListener('dispose',()=>disposed++);api.dispose();api=null;assert.equal(disposed,1);
 }finally{api?.dispose();env.close();}
 assert.equal(PACKAGING_PRODUCTS['poster-068'].file,product.file,'approved v3 is registered for publication');
});

test('Sculptural Pump v2 keeps all pump pieces and long hollow tube fitted through expansion',async()=>{
 const product=JSON.parse(readFileSync(new URL('../model-source/collection/poster-071/v2/review-product.json',import.meta.url),'utf8'));
 const bytes=readFileSync(new URL('../packaging-assets/'+product.file,import.meta.url));
 const gltf=JSON.parse(bytes.toString('utf8',20,20+bytes.readUInt32LE(12)));
 const nodes=gltf.nodes.map(n=>{
  const m=new Three.MeshPhysicalMaterial();m.name=gltf.materials?.[gltf.meshes?.[n.mesh]?.primitives[0]?.material]?.name??'';
  if(/print/i.test(n.name)){m.map=new Three.Texture();m.transparent=true;}
  const o='mesh' in n?new Three.Mesh(new Three.BoxGeometry(.1,.1,.1),m):new Three.Group();o.name=n.name;
  if(n.matrix)o.applyMatrix4(new Three.Matrix4().fromArray(n.matrix));else{o.position.fromArray(n.translation??[0,0,0]);o.quaternion.fromArray(n.rotation??[0,0,0,1]);o.scale.fromArray(n.scale??[1,1,1]);}return o;
 });
 gltf.nodes.forEach((n,i)=>n.children?.forEach(j=>nodes[i].add(nodes[j])));
 const model=new Three.Group();gltf.scenes[gltf.scene??0].nodes.forEach(i=>model.add(nodes[i]));
 const parts=Object.fromEntries(product.parts.map(p=>[p.key,model.getObjectByName(p.node)]));
 assert.deepEqual(model.children.map(o=>o.name).sort(),product.parts.map(p=>p.node).sort());
 const tube=model.getObjectByName('Long thick clear dip tube, open lower end');assert.equal(tube.parent,parts.pump);
 assert.ok(parts.pump.children.length>70);assert.ok(model.getObjectByName('Curved dispensing spout'));assert.ok(model.getObjectByName('Nozzle lip'));
 const node=gltf.nodes.find(n=>n.name===tube.name),accessor=gltf.accessors[gltf.meshes[node.mesh].primitives[0].attributes.POSITION];
 assert.ok(Math.max(...accessor.max.map((v,i)=>v-accessor.min[i]))>1.9,'tube must reach near the bottle floor');
 let api;const env=harness({product,parse:()=>Promise.resolve({scene:model})});
 try{
  api=await env.mount(env.host,{product,modelRequest:env.request(Promise.resolve(new ArrayBuffer(12)))});
  const flush=()=>{const f=[...env.frames.values()];env.frames.clear();f.forEach(fn=>fn(16));};
  const rest=Object.fromEntries(Object.entries(parts).map(([k,o])=>[k,o.position.clone()]));
  const fitted=parts.pump.children.map(o=>o.matrix.toArray());const film=parts.label.children[0];
  assert.equal(film.castShadow,true);assert.equal(film.customDepthMaterial.alphaHash,true);assert.equal(parts.print.children[0].castShadow,false);
  for(const p of [0,.5,1,.5,0]){
   api.setProgress(p);flush();parts.pump.children.forEach((o,i)=>assert.deepEqual(o.matrix.toArray(),fitted[i]));
   assert.ok(Math.abs(parts.pump.position.y-rest.pump.y-2.1*p)<1e-8);
   if(p===0 || p===1)assert.ok(Math.abs(film.material.opacity-(p===0?.035:.28))<1e-8);else assert.ok(film.material.opacity>.035 && film.material.opacity<.28);assert.equal(film.customDepthMaterial.opacity,film.material.opacity);
   if(p)assert.ok(parts.print.position.z-rest.print.z>parts.label.position.z-rest.label.z);
   else for(const [k,o] of Object.entries(parts))assert.ok(o.position.distanceTo(rest[k])<1e-8);
  }
 }finally{api?.dispose();env.close();}
 assert.deepEqual(PACKAGING_PRODUCTS['poster-071'],product,'approved v2 is registered without changing the reviewed configuration');
});

test('Moisture v2 retains the complete pump with a long hollow tube, separates ink and receives label shadows',async()=>{
 const product=JSON.parse(readFileSync(new URL('../model-source/collection/poster-049/v2/review-product.json',import.meta.url),'utf8'));
 const bytes=readFileSync(new URL('../packaging-assets/'+product.file,import.meta.url));
 const gltf=JSON.parse(bytes.toString('utf8',20,20+bytes.readUInt32LE(12)));
 const nodes=gltf.nodes.map(n=>{
  const spec=gltf.materials?.[gltf.meshes?.[n.mesh]?.primitives[0]?.material];
  const m=new Three.MeshPhysicalMaterial();m.name=spec?.name??'';m.transmission=spec?.extensions?.KHR_materials_transmission?.transmissionFactor??0;
  m.transparent=spec?.alphaMode==='BLEND';
  if(spec?.pbrMetallicRoughness?.baseColorTexture)m.map=new Three.Texture();
  const o='mesh' in n?new Three.Mesh(new Three.BoxGeometry(.1,.1,.1),m):new Three.Group();o.name=n.name;
  if(n.matrix)o.applyMatrix4(new Three.Matrix4().fromArray(n.matrix));else{o.position.fromArray(n.translation??[0,0,0]);o.quaternion.fromArray(n.rotation??[0,0,0,1]);o.scale.fromArray(n.scale??[1,1,1]);}return o;
 });
 gltf.nodes.forEach((n,i)=>n.children?.forEach(j=>nodes[i].add(nodes[j])));
 const model=new Three.Group();gltf.scenes[gltf.scene??0].nodes.forEach(i=>model.add(nodes[i]));
 const parts=Object.fromEntries(product.parts.map(p=>[p.key,model.getObjectByName(p.node)]));
 assert.deepEqual(model.children.map(o=>o.name).sort(),product.parts.map(p=>p.node).sort());
 const tube=model.getObjectByName('Long hollow dip tube with open inlet');assert.equal(tube.parent,parts.pump);
 for(const name of ['Closure','PumpStem','Actuator'])assert.equal(model.getObjectByName(name).parent,parts.pump);
 const node=gltf.nodes.find(n=>n.name===tube.name),accessor=gltf.accessors[gltf.meshes[node.mesh].primitives[0].attributes.POSITION];
 assert.ok(Math.max(...accessor.max.map((v,i)=>v-accessor.min[i]))>1.8,'long inlet reaches the bottle floor');
 let api;const env=harness({product,parse:()=>Promise.resolve({scene:model})});
 try{
  api=await env.mount(env.host,{product,modelRequest:env.request(Promise.resolve(new ArrayBuffer(12)))});
  const flush=()=>{const f=[...env.frames.values()];env.frames.clear();f.forEach(fn=>fn(16));};
  const rest=Object.fromEntries(Object.entries(parts).map(([k,o])=>[k,o.position.clone()]));
  const fitted=parts.pump.children.map(o=>o.matrix.toArray());
  const paper=parts.label.children[0];assert.equal(paper.castShadow,true);assert.equal(paper.receiveShadow,true);
  parts.body.traverse(o=>{if(o.isMesh){
   assert.equal(o.receiveShadow,true);
   const shader={fragmentShader:'#include <shadowmap_pars_fragment>\n#include <dithering_fragment>'};o.material.onBeforeCompile(shader);
   assert.ok(shader.fragmentShader.includes('getShadowMask()'),'actual label depth map must shade glass');
   assert.ok(shader.fragmentShader.includes('wallEdge'),'keep the original glass edge treatment');
  }});
  for(const k of ['logo','print'])parts[k].traverse(o=>{if(o.isMesh)assert.equal(o.castShadow,false,'transparent ink carrier must not cast a rectangle');});
  assert.equal(tube.material.transmission,0);assert.equal(tube.material.depthWrite,false);
  for(const p of [0,.5,1,.5,0]){
   api.setProgress(p);flush();parts.pump.children.forEach((o,i)=>assert.deepEqual(o.matrix.toArray(),fitted[i]));
   assert.ok(Math.abs(parts.pump.position.y-rest.pump.y-2.05*p)<1e-8);
   if(p)assert.ok(parts.print.position.z-rest.print.z>parts.label.position.z-rest.label.z);
   else for(const [k,o] of Object.entries(parts))assert.ok(o.position.distanceTo(rest[k])<1e-8);
  }
 }finally{api?.dispose();env.close();}
 assert.deepEqual(PACKAGING_PRODUCTS['poster-049'],product,'approved v2 is registered for publication');
});

for (const [id, tubeName, minimumLength] of [['072','Daily long hollow dip tube with open inlet',1.8],['056','Hollow clear Golden pump dip tube',1.5]]) test(`${id} v2 preserves the fitted pump and cover, separates ink and casts a thin-film shadow`,async()=>{
 const product=JSON.parse(readFileSync(new URL(`../model-source/collection/poster-${id}/v2/review-product.json`,import.meta.url),'utf8'));
 const bytes=readFileSync(new URL('../packaging-assets/'+product.file,import.meta.url));
 const gltf=JSON.parse(bytes.toString('utf8',20,20+bytes.readUInt32LE(12)));
 const nodes=gltf.nodes.map(n=>{
  const spec=gltf.materials?.[gltf.meshes?.[n.mesh]?.primitives[0]?.material];
  const m=new Three.MeshPhysicalMaterial();m.name=spec?.name??'';m.transmission=spec?.extensions?.KHR_materials_transmission?.transmissionFactor??0;
  m.transparent=spec?.alphaMode==='BLEND';
  if(spec?.pbrMetallicRoughness?.baseColorTexture)m.map=new Three.Texture();
  const o='mesh' in n?new Three.Mesh(new Three.BoxGeometry(.1,.1,.1),m):new Three.Group();o.name=n.name;
  if(n.matrix)o.applyMatrix4(new Three.Matrix4().fromArray(n.matrix));else{o.position.fromArray(n.translation??[0,0,0]);o.quaternion.fromArray(n.rotation??[0,0,0,1]);o.scale.fromArray(n.scale??[1,1,1]);}return o;
 });
 gltf.nodes.forEach((n,i)=>n.children?.forEach(j=>nodes[i].add(nodes[j])));
 const model=new Three.Group();gltf.scenes[gltf.scene??0].nodes.forEach(i=>model.add(nodes[i]));
 const parts=Object.fromEntries(product.parts.map(p=>[p.key,model.getObjectByName(p.node)]));
 assert.deepEqual(model.children.map(o=>o.name).sort(),product.parts.map(p=>p.node).sort());
 const tube=model.getObjectByName(tubeName);assert.equal(tube.parent,parts.pump);
 if(id==='072')for(const name of ['Closure','PumpStem','Actuator'])assert.equal(model.getObjectByName(name).parent,parts.pump);
 assert.ok(parts.pump.children.length>=4,'complete pump contains more than a cosmetic nozzle');
 const node=gltf.nodes.find(n=>n.name===tube.name),accessor=gltf.accessors[gltf.meshes[node.mesh].primitives[0].attributes.POSITION];
 assert.ok(Math.max(...accessor.max.map((v,i)=>v-accessor.min[i]))>minimumLength,'long inlet reaches the bottle floor');
 let api;const env=harness({product,parse:()=>Promise.resolve({scene:model})});
 try{
  api=await env.mount(env.host,{product,modelRequest:env.request(Promise.resolve(new ArrayBuffer(12)))});
  const flush=()=>{const f=[...env.frames.values()];env.frames.clear();f.forEach(fn=>fn(16));};
  const rest=Object.fromEntries(Object.entries(parts).map(([k,o])=>[k,o.position.clone()]));
  const fitted=parts.pump.children.map(o=>o.matrix.toArray());
  const paper=parts.label.children[0];assert.equal(paper.castShadow,true);assert.equal(paper.customDepthMaterial.alphaHash,true);assert.ok(paper.customDepthMaterial.opacity<.3);
  assert.equal(parts.overcap.children[0].material.side,Three.FrontSide);
  parts.body.traverse(o=>{if(o.isMesh){
   assert.equal(o.receiveShadow,true);
   const shader={fragmentShader:'#include <shadowmap_pars_fragment>\n#include <dithering_fragment>'};o.material.onBeforeCompile(shader);
   assert.ok(shader.fragmentShader.includes('getShadowMask()'),'actual label depth map must shade glass');
   assert.ok(shader.fragmentShader.includes('wallEdge'),'keep the original glass edge treatment');
  }});
  for(const k of ['print','name'])parts[k].traverse(o=>{if(o.isMesh)assert.equal(o.castShadow,false,'transparent ink carrier must not cast a rectangle');});
  assert.equal(tube.material.transmission,0);assert.equal(tube.material.depthWrite,false);
  for(const p of [0,.5,1,.5,0]){
   api.setProgress(p);flush();parts.pump.children.forEach((o,i)=>assert.deepEqual(o.matrix.toArray(),fitted[i]));
   assert.ok(Math.abs(parts.pump.position.y-rest.pump.y-2.05*p)<1e-8);
   if(p)assert.ok(parts.print.position.z-rest.print.z>parts.label.position.z-rest.label.z);
   else for(const [k,o] of Object.entries(parts))assert.ok(o.position.distanceTo(rest[k])<1e-8);
  }
 }finally{api?.dispose();env.close();}
 if(id==='056')assert.deepEqual(PACKAGING_PRODUCTS['poster-056'],product,'approved 056 v2 configuration is published');
 else assert.equal(PACKAGING_PRODUCTS['poster-072'].file,'poster-072.glb','072 remains local review only');
});

test('Beach Magic v2 publishes six fitted layers and casts only its physical paper shadow',async()=>{
 const product=PACKAGING_PRODUCTS['poster-012'];
 assert.deepEqual(product,JSON.parse(readFileSync(new URL('../model-source/collection/poster-012/v2/review-product.json',import.meta.url),'utf8')));
 const bytes=readFileSync(new URL('../packaging-assets/'+product.file,import.meta.url));
 const gltf=JSON.parse(bytes.toString('utf8',20,20+bytes.readUInt32LE(12)));
 const nodes=gltf.nodes.map(n=>{
  const spec=gltf.materials?.[gltf.meshes?.[n.mesh]?.primitives[0]?.material];
  const m=new Three.MeshPhysicalMaterial();m.name=spec?.name??'';m.transmission=spec?.extensions?.KHR_materials_transmission?.transmissionFactor??0;
  m.transparent=spec?.alphaMode==='BLEND';if(spec?.pbrMetallicRoughness?.baseColorTexture)m.map=new Three.Texture();
  const o='mesh' in n?new Three.Mesh(new Three.BoxGeometry(.1,.1,.1),m):new Three.Group();o.name=n.name;
  if(n.matrix)o.applyMatrix4(new Three.Matrix4().fromArray(n.matrix));else{o.position.fromArray(n.translation??[0,0,0]);o.quaternion.fromArray(n.rotation??[0,0,0,1]);o.scale.fromArray(n.scale??[1,1,1]);}return o;
 });
 gltf.nodes.forEach((n,i)=>n.children?.forEach(j=>nodes[i].add(nodes[j])));
 const model=new Three.Group();gltf.scenes[gltf.scene??0].nodes.forEach(i=>model.add(nodes[i]));
 const parts=Object.fromEntries(product.parts.map(p=>[p.key,model.getObjectByName(p.node)]));
 assert.deepEqual(model.children.map(o=>o.name).sort(),product.parts.map(p=>p.node).sort());
 assert.equal(parts.cap.children.length,3);assert.equal(parts.liner.children.length,2);assert.equal(parts.body.children.length,3);
 assert.ok(parts.print.isMesh && parts.name.isMesh,'root ink meshes must be checked too');
 let api;const env=harness({product,parse:()=>Promise.resolve({scene:model})});
 try {
  api=await env.mount(env.host,{product,modelRequest:env.request(Promise.resolve(new ArrayBuffer(12)))});
  const flush=()=>{const f=[...env.frames.values()];env.frames.clear();f.forEach(fn=>fn(16));};
  const rest=Object.fromEntries(Object.entries(parts).map(([k,o])=>[k,o.position.clone()]));
  const fitted=parts.cap.children.map(o=>o.matrix.toArray());
  const paper=parts.label.children[0];assert.equal(paper.castShadow,true);assert.equal(paper.material.transparent,false);
  for(const k of ['print','name'])assert.equal(parts[k].castShadow,false,'transparent ink carrier must not cast a rectangle');
  parts.body.traverse(o=>{if(o.isMesh){assert.equal(o.receiveShadow,true);const shader={fragmentShader:'#include <shadowmap_pars_fragment>\n#include <dithering_fragment>'};o.material.onBeforeCompile(shader);assert.ok(shader.fragmentShader.includes('getShadowMask()'));}});
  for(const p of [0,.5,1,.5,0]){
   api.setProgress(p);flush();parts.cap.children.forEach((o,i)=>assert.deepEqual(o.matrix.toArray(),fitted[i]));
   for(const [key,offset] of Object.entries(product.review.explosion.offsets))assert.ok(parts[key].position.clone().sub(rest[key]).distanceTo(new Three.Vector3(...offset).multiplyScalar(p))<1e-8);
   if(p){assert.ok(parts.print.position.z-rest.print.z>parts.label.position.z-rest.label.z);assert.ok(parts.name.position.z-rest.name.z>parts.print.position.z-rest.print.z);}
  }
 }finally{api?.dispose();env.close();}
});

// Soft Body Duo v3 quality regression: reuse the scene harness with the shipped GLTF loader.
for (const [width,height] of [[1200,800],[393,520]]) test(`Soft Body v3 keeps its real fitted pump, shadows and all 12 meshes in the ${width}px viewport`,async()=>{
  const product=JSON.parse(readFileSync(new URL('../model-source/collection/poster-084/v3/review-product.json',import.meta.url),'utf8'));
  const bytes=readFileSync(new URL('../packaging-assets/'+product.file,import.meta.url));
  const loaded=await loadTexturedPackagingGlb(bytes);
  const model=loaded.scene,meshes=[];model.traverse(o=>{if(o.isMesh)meshes.push(o);});
  const parts=Object.fromEntries(product.parts.map(p=>[p.key,model.getObjectByName(p.node)]));
  assert.deepEqual(model.children.map(o=>o.name).sort(),['Body','Label','LogoInk','NameInk','Pump']);
  const gltf=JSON.parse(bytes.toString('utf8',20,20+bytes.readUInt32LE(12)));
  assert.ok(gltf.meshes.length<=12,'identical pump geometry may share a mesh definition');
  assert.equal(gltf.nodes.filter(node=>Number.isInteger(node.mesh)).length,12,'buffer sharing preserves all twelve logical mesh instances');
  assert.equal(meshes.length,14,'both sides of the two physical labels keep their exported material primitives');
  assert.ok(meshes.every(o=>o.geometry.attributes.position.count>4),'use actual exported geometry, not bounding-box stand-ins');
  const pumpPieces=parts.pump.children;
  assert.equal(pumpPieces.length,4,'two complete white pumps and their two long hollow tubes stay in one movable group');
  const whitePumps=pumpPieces.filter(o=>/complete white pump/i.test(o.userData.name??o.name));
  assert.equal(whitePumps.length,2);assert.notEqual(whitePumps[0],whitePumps[1]);
  assert.ok(whitePumps.every(o=>o.isMesh&&o.geometry.attributes.position.count>4),'both pump instances retain actual geometry when buffers are shared');
  const tubes=pumpPieces.filter(o=>/hollow dip tube/i.test(o.userData.name??o.name));
  assert.equal(tubes.length,2);
  model.updateMatrixWorld(true);
  const bottleBounds=new Three.Box3().setFromObject(parts.body),bottleHeight=bottleBounds.getSize(new Three.Vector3()).y;
  for(const tube of tubes){
    assert.equal(tube.parent,parts.pump);
    assert.ok(new Three.Box3().setFromObject(tube).getSize(new Three.Vector3()).y>bottleHeight*.6,'each tube reaches down through most of its bottle');
  }
  let api,camera;
  const env=harness({product,parse:()=>Promise.resolve(loaded),onRender:(_,value)=>{camera=value;}});
  try{
    Object.defineProperties(env.host,{clientWidth:{value:width},clientHeight:{value:height}});
    api=await env.mount(env.host,{product,modelRequest:env.request(Promise.resolve(bytes.buffer))});
    const flush=()=>{const callbacks=[...env.frames.values()];env.frames.clear();callbacks.forEach(fn=>fn(16));model.updateWorldMatrix(true,true);camera.updateMatrixWorld(true);};
    flush();
    const rest=Object.fromEntries(Object.entries(parts).map(([key,o])=>[key,{p:o.position.clone(),s:o.scale.clone(),q:o.quaternion.clone()}]));
    const fitted=pumpPieces.map(o=>o.matrix.toArray());
    assert.equal(product.review.appearance.labelShadows,true);
    assert.equal(parts.label.children.length,2);
    parts.label.traverse(o=>{if(o.isMesh){assert.equal(o.castShadow,true);assert.equal(o.material.transparent,false,'white wrap labels remain physical opaque paper');}});
    parts.body.traverse(o=>{if(o.isMesh){
      assert.equal(o.receiveShadow,true);
      const shader={fragmentShader:'#include <shadowmap_pars_fragment>\n#include <dithering_fragment>'};o.material.onBeforeCompile(shader);
      assert.match(shader.fragmentShader,/getShadowMask\(\)/,'the glass receives the separated label shadow map');
    }});
    for(const key of ['logo','print'])parts[key].traverse(o=>{if(o.isMesh){
      assert.ok(o.material.map?.image?.width>0,'each ink layer keeps its embedded artwork texture');
      assert.equal(o.castShadow,false,'transparent ink carriers must not produce rectangular shadows');
    }});
    const inFrame=state=>{
      for(const mesh of meshes){
        mesh.geometry.computeBoundingBox();const {min,max}=mesh.geometry.boundingBox;
        for(const x of [min.x,max.x])for(const y of [min.y,max.y])for(const z of [min.z,max.z]){
          const point=new Three.Vector3(x,y,z).applyMatrix4(mesh.matrixWorld).project(camera);
          assert.ok(Math.abs(point.x)<.98&&Math.abs(point.y)<.98&&Math.abs(point.z)<1,`${mesh.userData.name??mesh.name} clips at ${state}: ${point.toArray()}`);
        }
      }
    };
    for(const progress of [0,.5,1]){
      api.resetView();api.setProgress(progress);flush();
      assert.equal(api.getState().renderedProgress,progress);
      const pumpOffset=new Three.Vector3(...product.review.explosion.offsets.pump).multiplyScalar(progress);
      assert.ok(parts.pump.position.clone().sub(rest.pump.p).distanceTo(pumpOffset)<1e-8);
      for(const key of ['logo','print'])if(progress)assert.ok(parts[key].position.z-rest[key].p.z>parts.label.position.z-rest.label.p.z,'ink separates farther than its physical label');
      if(progress===1)for(const tube of tubes)assert.ok(new Three.Box3().setFromObject(tube).min.y-new Three.Box3().setFromObject(parts.body).max.y>.1,'the long tube inlet clears the bottle mouth');
      for(let quarter=0;quarter<4;quarter++){
        pumpPieces.forEach((piece,i)=>assert.deepEqual(piece.matrix.toArray(),fitted[i],'all merged pump pieces and both tubes retain their fitted local transforms'));
        inFrame(`progress ${progress}, quarter turn ${quarter}`);api.rotate();flush();
      }
      api.viewBottom();flush();inFrame(`progress ${progress}, bottom view`);
    }
    api.setProgress(0);api.resetView();flush();inFrame('reset');
    assert.equal(api.getState().yaw,0);assert.equal(api.getState().pitch,0);
    for(const [key,part] of Object.entries(parts)){
      assert.ok(part.position.distanceTo(rest[key].p)<1e-8);
      assert.ok(part.scale.distanceTo(rest[key].s)<1e-8);
      assert.ok(1-Math.abs(part.quaternion.dot(rest[key].q))<1e-8);
    }
  }finally{api?.dispose();env.close();}
});

test('Soft Body v3 and Hand Gel v2 are approved while pending 072 stays unchanged',()=>{
  assert.deepEqual(PACKAGING_PRODUCTS['poster-084'],JSON.parse(readFileSync(new URL('../model-source/collection/poster-084/v3/review-product.json',import.meta.url),'utf8')));
  assert.equal(PACKAGING_PRODUCTS['poster-081'].file,'poster-081-v2.glb');
  assert.equal(PACKAGING_PRODUCTS['poster-072'].file,'poster-072.glb');
});

async function loadTexturedPackagingGlb(bytes) {
  const {GLTFLoader}=await import('../src/structure/vendor/GLTFLoader.js');
  const loader=new GLTFLoader();
  loader.register(parser=>{
    // Node has no image decoder; keep the production loader for geometry, hierarchy and materials.
    parser.loadImageSource=async index=>{
      const image=parser.json.images[index];
      assert.equal(image.mimeType,'image/png');assert.ok(Number.isInteger(image.bufferView));
      const png=Buffer.from(await parser.getDependency('bufferView',image.bufferView));
      assert.deepEqual([...png.subarray(0,8)],[137,80,78,71,13,10,26,10]);
      const width=png.readUInt32BE(16),height=png.readUInt32BE(20);
      assert.ok(width>0&&height>0&&png.length>32);
      return new Three.Texture({width,height});
    };
    return {name:'node_embedded_png_fixture'};
  });
  return loader.parseAsync(bytes.buffer.slice(bytes.byteOffset,bytes.byteOffset+bytes.byteLength),'');
}

for (const [width,height] of [[1200,800],[393,520]]) test(`Hand Gel v2 retains cloth UVs, fitted pump and real shadows in the ${width}px viewport`,async()=>{
  const product=JSON.parse(readFileSync(new URL('../model-source/collection/poster-081/v2/review-product.json',import.meta.url),'utf8'));
  const bytes=readFileSync(new URL('../packaging-assets/'+product.file,import.meta.url));
  const loaded=await loadTexturedPackagingGlb(bytes),model=loaded.scene,meshes=[];
  model.traverse(o=>{if(o.isMesh)meshes.push(o);});
  const parts=Object.fromEntries(product.parts.map(p=>[p.key,model.getObjectByName(p.node)]));
  assert.deepEqual(model.children.map(o=>o.name).sort(),['Body','Label','LogoInk','NameInk','Pump']);
  assert.equal(meshes.length,11);
  assert.equal(parts.pump.children.length,5,'the collar, actuator, spout, stem and long tube stay assembled');
  const tube=parts.pump.children.find(o=>/long clear hollow dip tube/i.test(o.userData.name??o.name));
  assert.ok(tube);assert.equal(tube.parent,parts.pump);
  model.updateMatrixWorld(true);
  assert.ok(new Three.Box3().setFromObject(tube).getSize(new Three.Vector3()).y>new Three.Box3().setFromObject(parts.body).getSize(new Three.Vector3()).y*.6,'the actual hollow tube reaches down through most of the bottle');
  const fabrics=meshes.filter(o=>['Warm ivory woven label','Black woven side flag'].includes(o.material.name));
  assert.equal(fabrics.length,2);
  const fabricRest=fabrics.map(o=>{
    assert.ok(o.geometry.attributes.uv,'woven surfaces retain authored UV coordinates');
    assert.equal(o.material.normalMap?.image?.width,512);assert.equal(o.material.normalMap.image.height,512);
    assert.equal(o.material.map?.image?.width,512);assert.equal(o.material.map.image.height,512);
    return {uv:Array.from(o.geometry.attributes.uv.array),normalMap:o.material.normalMap,normalScale:o.material.normalScale.toArray()};
  });
  const sideInk=parts.label.children.find(o=>/liaose on black side flag/i.test(o.userData.name??o.name));
  assert.ok(sideInk?.material.map,'the attached side-flag lettering keeps its artwork');
  let api,camera;
  const env=harness({product,parse:()=>Promise.resolve(loaded),onRender:(_,value)=>{camera=value;}});
  try{
    Object.defineProperties(env.host,{clientWidth:{value:width},clientHeight:{value:height}});
    api=await env.mount(env.host,{product,modelRequest:env.request(Promise.resolve(bytes.buffer))});
    const flush=()=>{const callbacks=[...env.frames.values()];env.frames.clear();callbacks.forEach(fn=>fn(16));model.updateWorldMatrix(true,true);camera.updateMatrixWorld(true);};flush();
    const rest=Object.fromEntries(Object.entries(parts).map(([key,o])=>[key,{p:o.position.clone(),s:o.scale.clone(),q:o.quaternion.clone()}]));
    const fitted=parts.pump.children.map(o=>o.matrix.toArray()),sideInkRest=sideInk.matrix.toArray();
    assert.equal(product.review.appearance.labelShadows,true);
    fabrics.forEach((o,i)=>{
      assert.equal(o.material.transparent,false);assert.equal(o.castShadow,true);
      assert.deepEqual(Array.from(o.geometry.attributes.uv.array),fabricRest[i].uv);
      assert.equal(o.material.normalMap,fabricRest[i].normalMap);assert.deepEqual(o.material.normalScale.toArray(),fabricRest[i].normalScale);
    });
    parts.body.traverse(o=>{if(o.isMesh){
      assert.equal(o.receiveShadow,true);
      const shader={fragmentShader:'#include <shadowmap_pars_fragment>\n#include <dithering_fragment>'};o.material.onBeforeCompile(shader);
      assert.match(shader.fragmentShader,/getShadowMask\(\)/,'the glass receives the fabric label shadow');
    }});
    assert.equal(sideInk.material.transparent,true);assert.equal(sideInk.castShadow,false,'side-flag lettering cannot cast an opaque carrier rectangle');
    for(const key of ['logo','print'])parts[key].traverse(o=>{if(o.isMesh){assert.ok(o.material.map?.image?.width>0);assert.equal(o.castShadow,false);}});
    assert.equal(tube.material.depthWrite,false);assert.equal(tube.castShadow,false);
    const inFrame=state=>{for(const mesh of meshes){
      mesh.geometry.computeBoundingBox();const {min,max}=mesh.geometry.boundingBox;
      for(const x of [min.x,max.x])for(const y of [min.y,max.y])for(const z of [min.z,max.z]){
        const point=new Three.Vector3(x,y,z).applyMatrix4(mesh.matrixWorld).project(camera);
        assert.ok(Math.abs(point.x)<.98&&Math.abs(point.y)<.98&&Math.abs(point.z)<1,`${mesh.userData.name??mesh.name} clips at ${state}: ${point.toArray()}`);
      }
    }};
    const radialEnvelope=group=>{
      const points=[];group.traverse(o=>{if(o.isMesh){const vertices=o.geometry.attributes.position;for(let i=0;i<vertices.count;i++)points.push(new Three.Vector3().fromBufferAttribute(vertices,i).applyMatrix4(o.matrixWorld));}});
      const center=new Three.Box3().setFromPoints(points).getCenter(new Three.Vector3());
      return {center,radius:Math.max(...points.map(p=>Math.hypot(p.x-center.x,p.z-center.z)))};
    };
    for(const progress of [0,.5,1]){
      api.resetView();api.setProgress(progress);flush();
      assert.equal(api.getState().renderedProgress,progress);
      assert.ok(parts.pump.position.clone().sub(rest.pump.p).distanceTo(new Three.Vector3(...product.review.explosion.offsets.pump).multiplyScalar(progress))<1e-8);
      for(const key of ['logo','print'])if(progress)assert.ok(parts[key].position.z-rest[key].p.z>parts.label.position.z-rest.label.p.z,'front ink separates beyond the fabric label');
      if(progress===1){
        assert.ok(new Three.Box3().setFromObject(tube).min.y-new Three.Box3().setFromObject(parts.body).max.y>.1,'the long tube inlet clears the bottle mouth');
        const bottle=radialEnvelope(parts.body),sleeve=radialEnvelope(fabrics.find(o=>o.material.name==='Warm ivory woven label'));
        const gap=Math.hypot(bottle.center.x-sleeve.center.x,bottle.center.z-sleeve.center.z)-bottle.radius-sleeve.radius;
        assert.ok(gap>0,`the expanded full fabric ring must clear the bottle radially in XZ; gap=${gap}, viewport=${width}`);
      }
      for(let quarter=0;quarter<4;quarter++){
        parts.pump.children.forEach((piece,i)=>assert.deepEqual(piece.matrix.toArray(),fitted[i]));
        assert.equal(sideInk.parent,parts.label);assert.deepEqual(sideInk.matrix.toArray(),sideInkRest,'the side wordmark stays fitted to its moving flag');
        inFrame(`progress ${progress}, quarter turn ${quarter}`);api.rotate();flush();
      }
      api.viewBottom();flush();inFrame(`progress ${progress}, bottom view`);
    }
    api.setProgress(0);api.resetView();flush();inFrame('reset');
    assert.equal(api.getState().yaw,0);assert.equal(api.getState().pitch,0);
    for(const [key,part] of Object.entries(parts)){
      assert.ok(part.position.distanceTo(rest[key].p)<1e-8);assert.ok(part.scale.distanceTo(rest[key].s)<1e-8);assert.ok(1-Math.abs(part.quaternion.dot(rest[key].q))<1e-8);
    }
  }finally{api?.dispose();env.close();}
  assert.deepEqual(PACKAGING_PRODUCTS['poster-081'],product,'approved 081 v2 configuration is registered');
  assert.equal(PACKAGING_PRODUCTS['poster-072'].file,'poster-072.glb');
});

for (const [width,height] of [[1200,800],[393,520]]) test(`Soap Clean v2 keeps its complete closures and direct-print shadows in the ${width}px viewport`,async()=>{
  const product=JSON.parse(readFileSync(new URL('../model-source/collection/poster-082/v2/review-product.json',import.meta.url),'utf8'));
  const bytes=readFileSync(new URL('../packaging-assets/'+product.file,import.meta.url));
  const loaded=await loadTexturedPackagingGlb(bytes),model=loaded.scene,meshes=[];
  model.traverse(o=>{if(o.isMesh)meshes.push(o);});
  const parts=Object.fromEntries(product.parts.map(p=>[p.key,model.getObjectByName(p.node)]));
  assert.deepEqual(model.children.map(o=>o.name).sort(),['Body','Label','LogoInk','NameInk','Pump','TubeCap']);
  assert.equal(meshes.length,20);assert.equal(parts.pump.children.length,6);assert.equal(parts.cap.children.length,3);
  const name=o=>o.userData.name??o.name;
  const dipTube=parts.pump.children.find(o=>/long clear hollow dip tube/i.test(name(o)));
  const bottle=parts.body.children.find(o=>/empty ivory cylinder/i.test(name(o)));
  const softTube=parts.body.children.find(o=>/flexible thin-wall tube/i.test(name(o)));
  const stripes=parts.label.children.find(o=>/pale blue pinstripes/i.test(name(o)));
  assert.ok(dipTube&&bottle&&softTube&&stripes);
  model.updateMatrixWorld(true);
  assert.ok(new Three.Box3().setFromObject(dipTube).getSize(new Three.Vector3()).y>new Three.Box3().setFromObject(bottle).getSize(new Three.Vector3()).y*.6,'the fitted hollow suction tube spans most of the bottle');
  const artwork=meshes.filter(o=>o.material.map).map(o=>({mesh:o,map:o.material.map,uv:Array.from(o.geometry.attributes.uv.array)}));
  let api,camera;
  const env=harness({product,parse:()=>Promise.resolve(loaded),onRender:(_,value)=>{camera=value;}});
  try{
    Object.defineProperties(env.host,{clientWidth:{value:width},clientHeight:{value:height}});
    api=await env.mount(env.host,{product,modelRequest:env.request(Promise.resolve(bytes.buffer))});
    const flush=()=>{const callbacks=[...env.frames.values()];env.frames.clear();callbacks.forEach(fn=>fn(16));model.updateWorldMatrix(true,true);camera.updateMatrixWorld(true);};flush();
    const rest=Object.fromEntries(Object.entries(parts).map(([key,o])=>[key,{p:o.position.clone(),s:o.scale.clone(),q:o.quaternion.clone()}]));
    const assemblies=[...parts.pump.children,...parts.cap.children].map(o=>({mesh:o,parent:o.parent,matrix:o.matrix.toArray()}));
    assert.equal(product.review.appearance.labelShadows,true);assert.equal(product.review.appearance.glass,false);
    assert.equal(stripes.material.transparent,false);assert.equal(stripes.castShadow,true,'solid direct-print stripes must cast their own shaped shadow');
    assert.equal(parts.label.children.filter(o=>o.castShadow).length,1,'transparent print carriers must not cast opaque rectangular shadows');
    for(const carrier of parts.label.children.filter(o=>o!==stripes)){assert.equal(carrier.material.transparent,true);assert.equal(carrier.castShadow,false);}
    for(const key of ['logo','print'])parts[key].traverse(o=>{if(o.isMesh){assert.equal(o.material.transparent,true);assert.equal(o.castShadow,false);assert.ok(o.material.map?.image?.width>0);}});
    for(const body of [bottle,softTube]){assert.equal(body.receiveShadow,true);assert.equal(body.material.transparent,false);}
    for(const {mesh,map,uv} of artwork){assert.equal(mesh.material.map,map);assert.deepEqual(Array.from(mesh.geometry.attributes.uv.array),uv);}
    const inFrame=state=>{for(const mesh of meshes){
      mesh.geometry.computeBoundingBox();const {min,max}=mesh.geometry.boundingBox;
      for(const x of [min.x,max.x])for(const y of [min.y,max.y])for(const z of [min.z,max.z]){
        const point=new Three.Vector3(x,y,z).applyMatrix4(mesh.matrixWorld).project(camera);
        assert.ok(Math.abs(point.x)<.98&&Math.abs(point.y)<.98&&Math.abs(point.z)<1,`${name(mesh)} clips at ${state}: ${point.toArray()}`);
      }
    }};
    for(const progress of [0,.5,1]){
      api.resetView();api.setProgress(progress);flush();assert.equal(api.getState().renderedProgress,progress);
      for(const key of ['body','pump','cap','label','logo','print'])assert.ok(parts[key].position.clone().sub(rest[key].p).distanceTo(new Three.Vector3(...product.review.explosion.offsets[key]).multiplyScalar(progress))<1e-8,`${key} follows its authored group motion`);
      for(const key of ['logo','print'])if(progress)assert.ok(parts[key].position.z-rest[key].p.z>parts.label.position.z-rest.label.p.z,'lettering separates beyond its direct-print carrier');
      if(progress===1){
        assert.ok(new Three.Box3().setFromObject(dipTube).min.y>new Three.Box3().setFromObject(bottle).max.y,'the long suction tube clears the bottle mouth');
        assert.ok(new Three.Box3().setFromObject(parts.cap).max.y<new Three.Box3().setFromObject(softTube).min.y,'the complete flip-top cap clears the tube nozzle');
      }
      for(let quarter=0;quarter<4;quarter++){
        for(const {mesh,parent,matrix} of assemblies){assert.equal(mesh.parent,parent);assert.deepEqual(mesh.matrix.toArray(),matrix,'pump and flip-top pieces remain fitted together');}
        inFrame(`progress ${progress}, quarter turn ${quarter}`);api.rotate();flush();
      }
      api.viewBottom();flush();inFrame(`progress ${progress}, bottom view`);
    }
    api.setProgress(0);api.resetView();flush();inFrame('reset');
    assert.equal(api.getState().yaw,0);assert.equal(api.getState().pitch,0);
    for(const [key,part] of Object.entries(parts)){assert.ok(part.position.distanceTo(rest[key].p)<1e-8);assert.ok(part.scale.distanceTo(rest[key].s)<1e-8);assert.ok(1-Math.abs(part.quaternion.dot(rest[key].q))<1e-8);}
  }finally{api?.dispose();env.close();}
  assert.deepEqual(PACKAGING_PRODUCTS['poster-082'],product,'approved 082 v2 configuration is registered');
  assert.equal(PACKAGING_PRODUCTS['poster-085'].file,'poster-085-v2.glb','next 085 v3 stays local only');
  assert.equal(PACKAGING_PRODUCTS['poster-072'].file,'poster-072.glb');
});

for (const [width,height] of [[1200,800],[393,520]]) test(`Daily Hair v3 preserves its textured finishes and complete assemblies in the ${width}px viewport`,async()=>{
  const product=JSON.parse(readFileSync(new URL('../model-source/collection/poster-085/v3/review-product.json',import.meta.url),'utf8'));
  const bytes=readFileSync(new URL('../packaging-assets/'+product.file,import.meta.url));
  const loaded=await loadTexturedPackagingGlb(bytes),model=loaded.scene,meshes=[];
  model.traverse(o=>{if(o.isMesh)meshes.push(o);});
  const parts=Object.fromEntries(product.parts.map(p=>[p.key,model.getObjectByName(p.node)]));
  assert.deepEqual(model.children.map(o=>o.name).sort(),['Body','Label','LogoInk','NameInk','Pump','TubeCap']);
  assert.equal(parts.pump.children.length,6);assert.equal(parts.cap.children.length,3);assert.equal(parts.label.children.length,2);
  assert.equal(parts.logo.children.length,2);assert.equal(parts.print.children.length,2);
  const name=o=>o.userData.name??o.name;
  const dipTube=parts.pump.children.find(o=>/long clear hollow dip tube/i.test(name(o)));
  const bottle=parts.body.children.find(o=>/empty tall cylinder/i.test(name(o)));
  const softTube=parts.body.children.find(o=>/empty flexible tube/i.test(name(o)));
  assert.ok(dipTube&&bottle&&softTube);model.updateMatrixWorld(true);
  assert.ok(new Three.Box3().setFromObject(dipTube).getSize(new Three.Vector3()).y>new Three.Box3().setFromObject(bottle).getSize(new Three.Vector3()).y*.6);
  const finishes=[bottle,softTube,...parts.label.children].map(mesh=>{
    assert.ok(mesh.geometry.attributes.uv,'the authored material UVs are required');
    assert.ok(mesh.material.normalMap?.image?.width>=128,'real embedded normal texture is required');
    assert.ok(mesh.material.roughnessMap?.image?.width>=128,'real embedded roughness texture is required');
    return {mesh,normalMap:mesh.material.normalMap,roughnessMap:mesh.material.roughnessMap,normalScale:mesh.material.normalScale.toArray(),uv:Array.from(mesh.geometry.attributes.uv.array)};
  });
  let api,camera;const env=harness({product,parse:()=>Promise.resolve(loaded),onRender:(_,value)=>{camera=value;}});
  try{
    Object.defineProperties(env.host,{clientWidth:{value:width},clientHeight:{value:height}});
    api=await env.mount(env.host,{product,modelRequest:env.request(Promise.resolve(bytes.buffer))});
    const flush=()=>{const callbacks=[...env.frames.values()];env.frames.clear();callbacks.forEach(fn=>fn(16));model.updateWorldMatrix(true,true);camera.updateMatrixWorld(true);};flush();
    const rest=Object.fromEntries(Object.entries(parts).map(([key,o])=>[key,{p:o.position.clone(),s:o.scale.clone(),q:o.quaternion.clone()}]));
    const assemblies=[...parts.pump.children,...parts.cap.children].map(mesh=>({mesh,parent:mesh.parent,matrix:mesh.matrix.toArray()}));
    assert.equal(product.review.appearance.labelShadows,true);assert.equal(product.review.appearance.glass,false);
    for(const wrap of parts.label.children){assert.equal(wrap.material.transparent,false);assert.equal(wrap.castShadow,true,'both solid curved decorative wraps must cast their shaped shadows');}
    for(const body of [bottle,softTube]){assert.equal(body.receiveShadow,true);assert.equal(body.material.transparent,false);}
    for(const key of ['logo','print'])parts[key].traverse(o=>{if(o.isMesh){assert.ok(o.material.map?.image?.width>0);assert.equal(o.material.transparent,true);assert.equal(o.castShadow,false,'transparent lettering must not cast an opaque carrier rectangle');}});
    for(const {mesh,normalMap,roughnessMap,normalScale,uv} of finishes){assert.equal(mesh.material.normalMap,normalMap);assert.equal(mesh.material.roughnessMap,roughnessMap);assert.deepEqual(mesh.material.normalScale.toArray(),normalScale);assert.deepEqual(Array.from(mesh.geometry.attributes.uv.array),uv);}
    const inFrame=state=>{for(const mesh of meshes){
      mesh.geometry.computeBoundingBox();const {min,max}=mesh.geometry.boundingBox;
      for(const x of [min.x,max.x])for(const y of [min.y,max.y])for(const z of [min.z,max.z]){
        const point=new Three.Vector3(x,y,z).applyMatrix4(mesh.matrixWorld).project(camera);
        assert.ok(Math.abs(point.x)<.98&&Math.abs(point.y)<.98&&Math.abs(point.z)<1,`${name(mesh)} clips at ${state}: ${point.toArray()}`);
      }
    }};
    for(const progress of [0,.5,1]){
      api.resetView();api.setProgress(progress);flush();assert.equal(api.getState().renderedProgress,progress);
      for(const key of ['body','pump','cap','label','logo','print'])assert.ok(parts[key].position.clone().sub(rest[key].p).distanceTo(new Three.Vector3(...product.review.explosion.offsets[key]).multiplyScalar(progress))<1e-8,`${key} follows its authored group motion`);
      for(const key of ['logo','print'])if(progress)assert.ok(parts[key].position.z-rest[key].p.z>parts.label.position.z-rest.label.p.z,'lettering moves beyond the solid decoration');
      if(progress===1){assert.ok(new Three.Box3().setFromObject(dipTube).min.y>new Three.Box3().setFromObject(bottle).max.y,'the entire dip tube clears the bottle mouth');assert.ok(new Three.Box3().setFromObject(parts.cap).max.y<new Three.Box3().setFromObject(softTube).min.y,'the complete flip-top cap clears the tube nozzle');}
      for(let quarter=0;quarter<4;quarter++){
        for(const {mesh,parent,matrix} of assemblies){assert.equal(mesh.parent,parent);assert.deepEqual(mesh.matrix.toArray(),matrix);}
        inFrame(`progress ${progress}, quarter turn ${quarter}`);api.rotate();flush();
      }
      api.viewBottom();flush();inFrame(`progress ${progress}, bottom view`);
    }
    api.setProgress(0);api.resetView();flush();inFrame('reset');assert.equal(api.getState().yaw,0);assert.equal(api.getState().pitch,0);
    for(const [key,part] of Object.entries(parts)){assert.ok(part.position.distanceTo(rest[key].p)<1e-8);assert.ok(part.scale.distanceTo(rest[key].s)<1e-8);assert.ok(1-Math.abs(part.quaternion.dot(rest[key].q))<1e-8);}
  }finally{api?.dispose();env.close();}
  assert.equal(PACKAGING_PRODUCTS['poster-085'].file,'poster-085-v2.glb','085 v3 is isolated from the approved production registry');
  assert.equal(PACKAGING_PRODUCTS['poster-072'].file,'poster-072.glb');
});
