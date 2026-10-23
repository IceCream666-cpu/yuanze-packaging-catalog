import * as T from './vendor/three.module.js';
import { GLTFLoader } from './vendor/GLTFLoader.js';

const clamp = T.MathUtils.clamp;
const smooth = (a, b, x) => { const t = clamp((x-a)/(b-a), 0, 1); return t*t*(3-2*t); };

function disposeObjects(...objects) {
  const geometries = new Set(), materials = new Set(), textures = new Set();
  objects.forEach(object => object?.traverse(o => {
    if (o.geometry) geometries.add(o.geometry);
    if (o.material) (Array.isArray(o.material) ? o.material : [o.material]).forEach(m => materials.add(m));
  }));
  materials.forEach(m => {Object.values(m).forEach(v => {if (v?.isTexture) textures.add(v);}); m.dispose();});
  geometries.forEach(g => g.dispose()); textures.forEach(t => t.dispose());
}

export async function mountPackagingScene(host, { onError, onReady, modelRequest, signal } = {}) {
  let disposed = false, frame = 0, lastTime = 0;
  let renderer, canvas, scene, envTarget, key, observer, api, studio;
  let down, move, up, lost, visible;
  const mark = phase => modelRequest?.mark(phase);
  const signals = [signal, modelRequest?.signal].filter(Boolean);
  const abortReason = () => signals.find(value => value.aborted)?.reason || new DOMException('Packaging view closed', 'AbortError');
  let rejectAbort;
  const aborted = new Promise((resolve, reject) => {rejectAbort = reject;});
  aborted.catch(() => {});
  const cancelled = () => {dispose(); rejectAbort(abortReason());};
  function dispose() {
    if (disposed) return;
    disposed = true; cancelAnimationFrame(frame); observer?.disconnect();
    signals.forEach(value => value.removeEventListener('abort', cancelled));
    canvas?.removeEventListener('pointerdown', down); canvas?.removeEventListener('pointermove', move);
    canvas?.removeEventListener('pointerup', up); canvas?.removeEventListener('pointercancel', up);
    canvas?.removeEventListener('lostpointercapture', up); canvas?.removeEventListener('webglcontextlost', lost);
    document.removeEventListener('visibilitychange', visible);
    disposeObjects(scene, studio);
    envTarget?.dispose(); key?.shadow.map?.dispose(); key?.shadow.mapPass?.dispose();
    renderer?.dispose(); canvas?.remove();
    if (host.__packagingScene === api) delete host.__packagingScene;
  }
  signals.forEach(value => value.addEventListener('abort', cancelled, {once: true}));
  try {
  if (signals.some(value => value.aborted)) throw abortReason();
  if (!modelRequest) throw new Error('A packaging model request is required.');
  // The authenticated request already started in the lightweight detail loader.
  // Prepare the unchanged studio while its bytes travel over the network.
  renderer = new T.WebGLRenderer({ antialias: true, alpha: true, powerPreference: 'high-performance' });
  renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 1.75));
  renderer.toneMapping = T.ACESFilmicToneMapping;
  renderer.toneMappingExposure = .92;
  renderer.shadowMap.enabled = true;
  renderer.shadowMap.type = T.PCFSoftShadowMap;
  renderer.setClearColor(0xf4c8d6, 1);
  host.append(renderer.domElement);
  canvas = renderer.domElement;
  canvas.setAttribute('aria-label', 'Beach Magic 三部件空罐模型，可拖拽旋转');
  canvas.setAttribute('role', 'img');
  canvas.style.touchAction = 'pan-y';
  scene = new T.Scene();
  scene.background = new T.Color(0xf4c8d6);
  const camera = new T.OrthographicCamera(-3, 3, 3, -3, .01, 100);
  const root = new T.Group();
  scene.add(root);
  // Neutral studio reflections keep the clear wall legible even at grazing angles.
  // Reflection cards live only in the environment map and never obstruct the product.
  studio = new T.Scene();
  studio.background = new T.Color('#858480');
  const cardGeometry = new T.PlaneGeometry(1, 1);
  const cardMaterials = [];
  const reflectionCard = (position, scale, color, strength) => {
    const material = new T.MeshBasicMaterial({ color, side: T.DoubleSide });
    material.color.multiplyScalar(strength); cardMaterials.push(material);
    const card = new T.Mesh(cardGeometry, material);
    card.position.set(...position); card.scale.set(...scale, 1); card.lookAt(0, 0, 0);
    studio.add(card);
  };
  reflectionCard([-5, 3, 4], [2.3, 7], '#fff8eb', 3.2);
  reflectionCard([5, 1, 1], [1.4, 6], '#edf4ff', 2.1);
  reflectionCard([0, 7, -1], [5, 3], '#ffffff', 1.7);
  reflectionCard([-3, 0, -5], [2.3, 5], '#faf4e9', 1.1);
  reflectionCard([0, 0, 7], [2.8, 7], '#4f5052', 1);
  const pmrem = new T.PMREMGenerator(renderer);
  mark('pmremStart');
  try {envTarget = pmrem.fromScene(studio, .025);} finally {pmrem.dispose();}
  mark('pmremEnd');
  scene.environment = envTarget.texture;
  cardGeometry.dispose(); cardMaterials.forEach(m => m.dispose()); studio = null;
  scene.add(new T.HemisphereLight(0xf5f2ed, 0x716961, .32));
  key = new T.DirectionalLight(0xfff6e9, 2.3); key.position.set(-4, 6, 4);
  key.target.position.set(0, 2.5, 0); scene.add(key, key.target);
  key.castShadow = true; key.shadow.mapSize.set(2048, 2048);
  Object.assign(key.shadow.camera, { left: -4, right: 4, top: 5, bottom: -4, near: .1, far: 18 });
  key.shadow.camera.updateProjectionMatrix();
  key.shadow.normalBias = .004; key.shadow.bias = -.00015; key.shadow.radius = 3;
  const rim = new T.DirectionalLight(0xf2f5ff, 1.1); rim.position.set(4, 4, -3); scene.add(rim);
  const fill = new T.DirectionalLight(0xfff9ef, .16); fill.position.set(1, 1, 7); scene.add(fill);
  const bounce = new T.DirectionalLight(0xf3f0ea, 1.25); bounce.position.set(0, -3, 6); scene.add(bounce);

  const parsed = modelRequest.promise.then(bytes => {
    if (disposed) throw abortReason();
    mark('parseStart');
    return new GLTFLoader().parseAsync(bytes, '');
  }).then(gltf => {
    if (disposed) {disposeObjects(gltf.scene); throw abortReason();}
    mark('parseEnd');
    return gltf.scene;
  });
  const model = await Promise.race([parsed, aborted]);
  root.add(model);
  model.scale.setScalar(30);
  const parts = { jar: model.getObjectByName('Jar'), cap: model.getObjectByName('OuterCap'), liner: model.getObjectByName('InnerLid') };
  if (Object.values(parts).some(v => !v)) {
    throw new Error('The three packaging components are required.');
  }
  const rest = Object.fromEntries(Object.entries(parts).map(([key, value]) => [key, { p: value.position.clone(), q: value.quaternion.clone() }]));
  model.traverse(o => {
    if (!o.isMesh) return;
    o.frustumCulled = false;
    // GLTFLoader replaces spaces in object names; userData retains the source name.
    const isPullTongue = (o.userData.name || o.name).replaceAll('_', ' ').includes('short flexible pull tongue');
    // The small pull tongue needs its own satin material to remain legible at UI scale.
    if (isPullTongue) o.material = o.material.clone();
    const m = o.material;
    if (isPullTongue) m.color.multiplyScalar(.9);
    if (m.map) { m.map.anisotropy = Math.min(8, renderer.capabilities.getMaxAnisotropy()); }
    if (m.transmission > .5) {
      m.transmission = 1; m.roughness = .035; m.thickness = .0024;
      m.ior = 1.47; m.envMapIntensity = 1.05; m.color.set('#ffffff');
      m.transparent = false; m.opacity = 1; m.depthWrite = true; m.side = T.DoubleSide;
      m.clearcoat = .12; m.clearcoatRoughness = .08;
      // Web transmission does not resolve the nested inner/outer wall bounces.
      // Keep a restrained rim correction; stronger values make the jar look smoky.
      m.onBeforeCompile = shader => {
        shader.fragmentShader = shader.fragmentShader.replace('#include <dithering_fragment>', `#include <dithering_fragment>
          float wallEdge = pow(1.0 - abs(dot(normalize(normal), normalize(vViewPosition))), 9.0);
          gl_FragColor.rgb *= 1.0 - 0.18 * wallEdge;
        `);
      };
      o.castShadow = false; o.receiveShadow = false;
    } else {
      // Preserve the original Blender materials: slightly warmer lid interior,
      // satin shell and a cooler inner cover, instead of flattening all to white.
      m.envMapIntensity = .5;
      // Only the pull tongue occludes light on its shallow inner cover.
      o.castShadow = isPullTongue; // taste-skill-ignore: physical contact shadow.
      o.receiveShadow = !m.map;
      if (!m.map) {
        m.roughness = m.name === 'WarmWhiteInnerLid' ? .38 : .34;
      } else {
        m.roughness = .62; m.alphaTest = .35; m.depthWrite = true; m.transparent = false;
      }
    }
    m.needsUpdate = true;
  });
  const shadowCanvas = document.createElement('canvas'); shadowCanvas.width = shadowCanvas.height = 256;
  const context = shadowCanvas.getContext('2d');
  const gradient = context.createRadialGradient(128, 128, 4, 128, 128, 124);
  gradient.addColorStop(0, 'rgba(57,49,42,.30)'); gradient.addColorStop(.45, 'rgba(57,49,42,.13)'); gradient.addColorStop(1, 'rgba(71,53,44,0)');
  context.fillStyle = gradient; context.fillRect(0, 0, 256, 256);
  const shadowTexture = new T.CanvasTexture(shadowCanvas); // taste-skill-ignore: physical grounding texture.
  const shadow = new T.Mesh(new T.PlaneGeometry(4.6, 4.6), new T.MeshBasicMaterial({map: shadowTexture, transparent: true, depthWrite: false})); // taste-skill-ignore: physical grounding under the model.
  shadow.rotation.x = -Math.PI/2; shadow.position.y = -.025; scene.add(shadow);
  const reduced = matchMedia('(prefers-reduced-motion: reduce)').matches;
  let target = 0, current = 0, yaw = 0, pitch = 0, desiredYaw = 0, desiredPitch = 0, selected = null, focus = 0, width = 1, height = 1;
  const capTilt = new T.Quaternion(), linerTilt = new T.Quaternion();
  const rotationEuler = new T.Euler();
  let pointer = null;
  function pose() {
    const capOpen = smooth(.02, .65, current), linerOpen = smooth(.27, 1, current);
    parts.cap.position.copy(rest.cap.p); parts.cap.position.y += .100 * capOpen;
    parts.cap.position.x -= .006 * capOpen;
    rotationEuler.set(-.75*capOpen, -Math.PI*1.25*capOpen, -.12*capOpen);
    capTilt.setFromEuler(rotationEuler); parts.cap.quaternion.copy(rest.cap.q).multiply(capTilt);
    parts.liner.position.copy(rest.liner.p); parts.liner.position.y += .047 * linerOpen;
    parts.liner.position.x += .002 * linerOpen;
    rotationEuler.set(.19*linerOpen, .12*linerOpen, -.1*linerOpen);
    linerTilt.setFromEuler(rotationEuler); parts.liner.quaternion.copy(rest.liner.q).multiply(linerTilt);
    const aspect = width/height;
    // At half-open the cap is already high; reserve headroom without changing
    // the approved part poses, progress timing, rotation or scroll controls.
    const intermediateHeadroom = Math.sin(Math.PI * current);
    const assemblyCenter = 1.25 + current*1.22 + intermediateHeadroom*.25;
    // Turn the assembly about its centre, so looking underneath does not
    // swing the jar out of the frame. The two translations cancel at rest.
    root.position.y = assemblyCenter;
    model.position.y = -assemblyCenter;
    root.rotation.set(pitch, yaw, 0);
    const tiltHeadroom = smooth(.2, 1.4, Math.abs(pitch)) * .7;
    shadow.material.opacity = 1 - smooth(.15, .7, Math.abs(pitch));
    const viewHeight = Math.max(4.2 + current*3.05 + intermediateHeadroom*1.2 + tiltHeadroom, 3.65/aspect);
    camera.left = -viewHeight*aspect/2; camera.right = viewHeight*aspect/2;
    camera.top = viewHeight/2; camera.bottom = -viewHeight/2;
    const centerY = assemblyCenter + focus;
    camera.position.set(0, centerY+2.35, 10);
    camera.lookAt(0, centerY, 0); camera.updateProjectionMatrix();
    renderer.render(scene, camera);
  }
  function render(time = 0) {
    frame = 0;
    if (disposed || document.hidden) return;
    const dt = Math.min((time-lastTime)/1000, .06) || .016; lastTime = time;
    const ease = reduced ? 1 : 1-Math.exp(-dt*13);
    current += (target-current)*ease; yaw += (desiredYaw-yaw)*ease; pitch += (desiredPitch-pitch)*ease;
    try {pose();} catch (error) {dispose(); onError?.(error); return;}
    if (Math.abs(target-current)+Math.abs(desiredYaw-yaw)+Math.abs(desiredPitch-pitch) > .0002) invalidate();
  }
  function invalidate() { if (!frame && !disposed) frame = requestAnimationFrame(render); }
  const resize = () => {
    width = Math.max(host.clientWidth, 1); height = Math.max(host.clientHeight, 1);
    renderer.setSize(width, height); invalidate();
  };
  observer = new ResizeObserver(resize); observer.observe(host); resize();
  down = function(e) {
    if (e.button && e.button !== 0) return;
    pointer = { id: e.pointerId, x: e.clientX, y: e.clientY, yaw: desiredYaw, pitch: desiredPitch, touch: e.pointerType==='touch' };
    if (!pointer.touch) canvas.setPointerCapture(e.pointerId);
    canvas.style.cursor = 'grabbing';
  }
  move = function(e) {
    if (!pointer || e.pointerId !== pointer.id) return;
    const dx = e.clientX-pointer.x, dy = e.clientY-pointer.y;
    desiredYaw = pointer.yaw + dx*.015;
    if (!pointer.touch) desiredPitch = clamp(pointer.pitch + dy*.006, -Math.PI*.75, Math.PI*.75);
    invalidate();
  }
  up = function() { pointer = null; canvas.style.cursor = 'grab'; };
  lost = function(e) { e.preventDefault(); dispose(); onError?.(new Error('WebGL context lost')); };
  visible = function() { if (!document.hidden) { lastTime=0; invalidate(); } };
  canvas.style.cursor = 'grab';
  canvas.addEventListener('pointerdown', down); canvas.addEventListener('pointermove', move);
  canvas.addEventListener('pointerup', up); canvas.addEventListener('pointercancel', up); canvas.addEventListener('lostpointercapture', up);
  canvas.addEventListener('webglcontextlost', lost); document.addEventListener('visibilitychange', visible);
  api = {
    setProgress(p) { target = clamp(Number(p)||0, 0, 1); invalidate(); },
    resetView() { desiredYaw=0; desiredPitch=0; selected=null; focus=0; invalidate(); },
    rotate() { desiredYaw += Math.PI/2; invalidate(); },
    viewBottom() {
      desiredYaw=0; desiredPitch=-Math.PI/2-Math.atan2(2.35, 10);
      selected=null; focus=0; invalidate();
    },
    focusPart(key) {
      selected=key; desiredYaw=0; desiredPitch=key==='liner'?.16:key==='cap'?-.15:0;
      focus=key==='cap'?.25:key==='jar'?-.12:0; invalidate();
    },
    getState() { return {progress:target, renderedProgress:current, yaw, pitch, selected, components:Object.keys(parts), meshes:renderer.info.render.calls, triangles:renderer.info.render.triangles}; },
    dispose,
  };
  host.__packagingScene=api;
  cancelAnimationFrame(frame); frame = 0;
  mark('firstFrameStart'); pose(); mark('firstFrame');
  onReady?.(); return api;
  } catch (error) {dispose(); throw error;}
}
