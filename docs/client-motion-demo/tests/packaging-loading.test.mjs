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
  ['poster-051', {pump:2.3}, [-3.4,.18,1.65]],
  ['poster-057', {dropper:1.95}, [-3.1,.10,1.65]],
  ['poster-056', {overcap:3.95,pump:1.85}, [-3.8,.18,1.65]],
  ['poster-044', {overcap:3.15,pump:2.15}, [-2.65,.50,1.65]],
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
      assert.equal(product.parts.length, id === 'poster-047' || id === 'poster-049' || id === 'poster-042' || id === 'poster-051' || id === 'poster-057' ? 4 : id === 'poster-044' || id === 'poster-056' ? 5 : 6);
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
      if (id === 'poster-049' || id === 'poster-042' || id === 'poster-051' || id === 'poster-044' || id === 'poster-047' || id === 'poster-056' || id === 'poster-057') {
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
    assert.ok(body.material.color.equals(new Three.Color('#ffffff')));
    assert.equal(body.material.transmission,1);
    assert.equal(body.material.roughness,.28);
    assert.equal(cover.material.roughness,.035,'the olive cover must retain its own smooth finish');
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
  const bytes=readFileSync(new URL('../packaging-assets/poster-056.glb',import.meta.url));
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
    assert.deepEqual(Object.keys(parts).sort(),['jar','label','overcap','print','pump']);
    assert.equal(product.review,undefined,'retain the approved empty glass, olive cover and complete printing');
    const tube=loaded.scene.getObjectByName(tubeName),head=loaded.scene.getObjectByName('Actuator');
    assert.equal(tube.parent,loaded.scene.getObjectByName('Closure'));
    assert.equal(tube.material.transmission,.98);
    assert.equal(tube.material.roughness,.06);
    assert.equal(tube.material.ior,1.46);
    assert.equal(tube.material.thickness,.0165);
    assert.equal(tube.material.side,Three.FrontSide);
    assert.equal(Boolean(tube.material.toneMapped),false,'the production legacy falsy flag keeps tube tone mapping disabled');
    assert.equal(tube.castShadow,false);
    assert.equal(tube.receiveShadow,false);
    const body=loaded.scene.getObjectByName(bodyName);
    assert.equal(body.material.roughness,.28,'the real frosted bottle must not be overwritten by the generic polished-glass branch');
    assert.equal(body.material.transmission,1,'frosting retains light transmission rather than becoming opaque white plastic');
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
      for(const [key,lift] of [['pump',1.85],['overcap',3.95]])
        assert.ok(parts[key].position.clone().sub(rest[key].position).distanceTo(new Three.Vector3(0,lift*progress,0))<1e-9);
      const displacement=parts.pump.getWorldPosition(new Three.Vector3()).sub(rest.pump.world);
      for(const {part,matrix,world} of fitted) {
        assert.deepEqual(part.matrix.toArray(),matrix,'all fitted pump pieces retain their local transforms');
        assert.ok(part.getWorldPosition(new Three.Vector3()).sub(world).distanceTo(displacement)<1e-9);
      }
      assert.ok(Math.abs(camera.position.y-1.05-(1.45+1.9775*progress))<1e-9);
      assert.ok(Math.abs(camera.top-camera.bottom-(4.2+3.8*progress))<1e-9);
      assert.ok(Math.abs(camera.position.x+1.45*progress)<1e-9);
      for(const [key,offset,growth] of [['label',[-1.85,.08,.65],.15],['print',[-3.8,.18,1.65],.95]]) {
        assert.ok(parts[key].position.clone().sub(rest[key].position).distanceTo(new Three.Vector3(...offset).multiplyScalar(progress))<1e-9);
        assert.ok(parts[key].scale.distanceTo(rest[key].scale.clone().multiplyScalar(1+growth*progress))<1e-9);
      }
      const coverBounds=new Three.Box3().setFromObject(parts.overcap),headBounds=new Three.Box3().setFromObject(head);
      assert.ok(coverBounds.max.y-.03*diameter>headBounds.max.y,'the cover ceiling never crosses the fitted pump head');
      if(progress===1) {
        const tubeBounds=new Three.Box3().setFromObject(tube),bottleBounds=new Three.Box3().setFromObject(parts.jar);
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
      for(const key of progress===0 ? Object.keys(parts) : ['jar']) {
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
  assert.deepEqual(Object.entries(PACKAGING_PRODUCTS).filter(([,p])=>p.review?.appearance.referenceGlass).map(([id])=>id).sort(),['poster-067','poster-072','poster-073','poster-081','poster-084']);
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
