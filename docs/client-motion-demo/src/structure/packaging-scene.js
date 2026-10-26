import {PACKAGING_PRODUCTS} from './packaging-products.js';
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

export async function mountPackagingScene(host, { onError, onReady, modelRequest, signal, product = PACKAGING_PRODUCTS['poster-012'], design = {background:'#f4c8d6',name:'Beach Magic'} } = {}) {
  const pdrn = product.file === 'poster-039.glb';
  const moisture = product.file === 'poster-049.glb';
  const woodland = product.file === 'poster-042.glb';
  const pureVolume = product.file === 'poster-051.glb';
  const gentle = product.file === 'poster-044.glb';
  const coastal = product.file === 'poster-047.glb';
  const golden = product.file === 'poster-056.glb';
  const b5 = product.file === 'poster-057.glb';
  const review = product.review, appearance = review?.appearance, explosion = review?.explosion;
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
  renderer.setClearColor(design.background, 1);
  host.append(renderer.domElement);
  canvas = renderer.domElement;
  canvas.setAttribute('aria-label', `${design.name} 分层包材模型，可拖拽旋转`);
  canvas.setAttribute('role', 'img');
  canvas.style.touchAction = 'pan-y';
  scene = new T.Scene();
  scene.background = new T.Color(design.background);
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
  if (pdrn || moisture || appearance?.metal) {
    studio.background.set('#b9b9b5');
    reflectionCard([0, 8, 0], [14, 14], '#ffffff', 2.2);
    reflectionCard([0, 2, -7], [12, 5], '#ffffff', 2.5);
    reflectionCard([-4, 2, 5], [3, 10], '#ffffff', 3.6);
    reflectionCard([4, 2, 5], [2, 10], '#ffffff', 3.1);
    reflectionCard([-1.7, 2, 6], [.6, 9], '#111311', .25);
    reflectionCard([1.8, 2, 6], [.4, 9], '#121412', .25);
    reflectionCard([-7, 1, 0], [4, 10], '#121512', 1);
    reflectionCard([7, 1, 0], [4, 10], '#121512', 1);
  }
  if (woodland || coastal || golden || b5 || review) {
    reflectionCard([-4, 2, 5], [1.5, 8], '#ffffff', 2.6);
    reflectionCard([4, 2, 5], [.7, 7], '#ffffff', 1.9);
  }
  if (golden) {
    reflectionCard([1.8, 2, 7], [.25, 6], '#ffffff', 3.5);
    reflectionCard([-1.8, 2, 7], [.15, 6], '#ffffff', 2.8);
  }
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
  model.scale.setScalar(product.scale);
  const collection = product.kind === 'collection';
  const pump = product.file === 'liaose-pump.glb';
  const parts = Object.fromEntries(product.parts.map(part => [part.key, model.getObjectByName(part.node)]));
  if (Object.values(parts).some(v => !v)) {
    throw new Error('All approved packaging components are required.');
  }
  const rest = Object.fromEntries(Object.entries(parts).map(([key, value]) => [key, { p: value.position.clone(), q: value.quaternion.clone(), s: value.scale.clone() }]));
  model.traverse(o => {
    if (!o.isMesh) return;
    let component=o; while(component.parent && component.parent!==model) component=component.parent;
    const isReviewOvercap=review && component===parts.overcap;
    const isReviewFilm=review && component===parts.refill;
    o.frustumCulled = false;
    // GLTFLoader replaces spaces in object names; userData retains the source name.
    const isPullTongue = (o.userData.name || o.name).replaceAll('_', ' ').includes('short flexible pull tongue');
    // Component-specific finishes must not mutate another part sharing the GLB material.
    if (isPullTongue || isReviewOvercap || isReviewFilm || (golden && o.material.name.includes('olive')) || (appearance?.tintedGlass && o.material.transmission>.5)) o.material = o.material.clone();
    const m = o.material;
    if (isPullTongue) m.color.multiplyScalar(.9);
    if (m.map) { m.map.anisotropy = Math.min(8, renderer.capabilities.getMaxAnisotropy()); }
    if (pump || collection) {
      m.envMapIntensity = .65; o.castShadow = !m.map; o.receiveShadow = !m.map;
      if (pdrn || moisture || woodland || gentle || coastal || golden || b5 || review) {
        if (m.map) {m.specularIntensity=.05; if (!review || m.metalness<.3) m.roughness=.7; m.envMapIntensity=.1;}
        if (m.transmission > .5) {
          if (!review && !woodland && !(golden && m.name.includes('olive'))) m.color.set('#ffffff');
          if (!review) m.transmission=1;
          m.roughness=review ? Math.max(appearance.frosted && !(isReviewOvercap && appearance.clearOvercap === true) ? .24 : .012,m.roughness) : woodland ? .035 : golden && m.name.includes('olive') ? .035 : .012;
          m.ior=1.48; m.thickness=isReviewFilm ? .005 : isReviewOvercap || gentle && m.name.includes('cover') ? .012 : .08; m.envMapIntensity=.3;
          if(isReviewFilm) m.color.set('#ffffff');
          if ((woodland && m.name.includes('amber')) || (golden && m.name.includes('olive'))) {
            m.attenuationColor.copy(m.color); m.color.set('#ffffff');
            m.attenuationDistance=golden ? .18 : .85; m.thickness=.12; m.envMapIntensity=golden ? 1.4 : .65;
          }
          if (appearance?.tintedGlass) {m.attenuationColor.copy(m.color);m.color.set('#ffffff');m.attenuationDistance=appearance.attenuationDistance;}
          // Match the untonemapped backdrop through the clear wall.
          m.toneMapped=Boolean(isReviewOvercap && appearance.clearOvercap !== true); m.specularIntensity=review ? .35 : .7;
          m.transparent=false; m.opacity=1; m.side=isReviewOvercap || isReviewFilm || golden && m.name.includes('overcap') ? T.FrontSide : T.DoubleSide;
          // The same restrained rim correction used by the first approved glass jar.
          m.onBeforeCompile = shader => {
            shader.fragmentShader = shader.fragmentShader.replace('#include <dithering_fragment>', `#include <dithering_fragment>
              float wallEdge = pow(1.0 - abs(dot(normalize(normal), normalize(vViewPosition))), 9.0);
              gl_FragColor.rgb *= 1.0 - 0.18 * wallEdge;
            `);
          };
          o.castShadow=false; o.receiveShadow=false;
        } else if (m.metalness > .9) {
          m.roughness=review ? Math.max(.06,m.roughness) : moisture ? .16 : .075; m.envMapIntensity=1;
          o.castShadow=false;
        }
      }
      // shortcut: Blend the inner tube in WebGL's single transmission pass; use multipass rendering if accurate nested refraction is required.
      if ((b5 || appearance?.pipette) && m.transmission > .5) m.depthWrite=false;
      if ((b5 || appearance?.pipette) && m.name.toLowerCase().includes('pipette')) {m.transmission=0; m.transparent=true; m.opacity=.38; m.depthWrite=false; m.side=T.FrontSide; o.renderOrder=1;}
      if (b5 && m.map) m.toneMapped=false;
      if (m.map) {m.depthWrite=!m.transparent; m.polygonOffset=true; m.polygonOffsetFactor=-1; o.renderOrder=m.transparent?2:0;}
      return;
    }
    if (o === parts.print) {m.depthWrite=false; m.polygonOffset=true; m.polygonOffsetFactor=-1; o.renderOrder=2;}
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
  // Keep the lettering above the translucent substrate at every viewing angle.
  if (gentle || golden || b5 || review) parts.print.traverse(o => {if (o.isMesh) o.renderOrder=3;});
  const shadowCanvas = document.createElement('canvas'); shadowCanvas.width = shadowCanvas.height = 256;
  const context = shadowCanvas.getContext('2d');
  const gradient = context.createRadialGradient(128, 128, 4, 128, 128, 124);
  gradient.addColorStop(0, 'rgba(57,49,42,.30)'); gradient.addColorStop(.45, 'rgba(57,49,42,.13)'); gradient.addColorStop(1, 'rgba(71,53,44,0)');
  context.fillStyle = gradient; context.fillRect(0, 0, 256, 256);
  const shadowTexture = new T.CanvasTexture(shadowCanvas); // taste-skill-ignore: physical grounding texture.
  const shadow = new T.Mesh(new T.PlaneGeometry(4.6, 4.6), new T.MeshBasicMaterial({map: shadowTexture, transparent: true, depthWrite: false})); // taste-skill-ignore: physical grounding under the model.
  shadow.rotation.x = -Math.PI/2; shadow.position.y = -.025; scene.add(shadow);
  const reduced = matchMedia('(prefers-reduced-motion: reduce)').matches;
  let target = 0, current = 0, yaw = 0, pitch = 0, desiredYaw = 0, desiredPitch = 0, selected = null, focus = 0, width = 1, height = 1, zoom = 1;
  const capTilt = new T.Quaternion(), linerTilt = new T.Quaternion();
  const rotationEuler = new T.Euler();
  let pointer = null;
  function pose() {
    const narrowReview=review && width>1 && width<768;
    if (explosion) {
      for (const [key, offset] of Object.entries(explosion.offsets)) {
        const interval=explosion.timing?.[key];
        const amount=interval ? smooth(...interval,current) : current;
        const travel=new T.Vector3(...offset);
        // Keep the same front-to-back separation while fitting wide print pairs on phones.
        if(narrowReview && (key==='label' || key==='print' || key==='name')) travel.x*=.5;
        parts[key].position.copy(rest[key].p).addScaledVector(travel,amount);
        const scale=explosion.scales?.[key] ?? 1;
        parts[key].scale.copy(rest[key].s).multiplyScalar(1+(scale-1)*amount);
        const rotation=explosion.rotations?.[key];
        if (rotation) {
          rotationEuler.set(...rotation.map(v=>v*amount));
          capTilt.setFromEuler(rotationEuler); parts[key].quaternion.copy(rest[key].q).multiply(capTilt);
        }
      }
      if (appearance.clearLabel) parts.label.traverse(o=>{if(o.isMesh)o.material.opacity=.05+.95*smooth(.03,.6,current);});
    } else if (pdrn) {
      const capOpen=smooth(.02,.72,current), linerOpen=smooth(.25,1,current);
      parts.closure.position.copy(rest.closure.p).add(new T.Vector3(-.18,3.45,0).multiplyScalar(capOpen));
      rotationEuler.set(-.68*capOpen,-Math.PI*1.25*capOpen,-.10*capOpen);
      capTilt.setFromEuler(rotationEuler); parts.closure.quaternion.copy(rest.closure.q).multiply(capTilt);
      parts.liner.position.copy(rest.liner.p).add(new T.Vector3(.06,1.41,0).multiplyScalar(linerOpen));
      rotationEuler.set(.16*linerOpen,.10*linerOpen,-.06*linerOpen);
      linerTilt.setFromEuler(rotationEuler); parts.liner.quaternion.copy(rest.liner.q).multiply(linerTilt);
    } else if (b5) {
      parts.head.position.copy(rest.head.p).y += 4.1*current;
      parts.stem.position.copy(rest.stem.p).y += 3.45*current;
      parts.closure.position.copy(rest.closure.p).y += .95*current;
      parts.base.position.copy(rest.base.p).add(new T.Vector3(1.7*smooth(.3,1,current),-.8*smooth(0,.3,current),.35*smooth(.3,1,current)));
      parts.label.position.copy(rest.label.p).addScaledVector(new T.Vector3(-1.4,.08,.65),current);
      parts.label.scale.copy(rest.label.s).multiplyScalar(1+.15*current);
      parts.label.traverse(o => {if (o.isMesh) o.material.opacity=.05+.95*smooth(.03,.6,current);});
    } else if (gentle || golden) {
      parts.overcap.position.copy(rest.overcap.p).y += golden ? 4.85*smooth(0,.65,current) : 3.6*smooth(0,.85,current);
      parts.head.position.copy(rest.head.p).y += (golden ? 2.6 : 2.5)*current;
      parts.stem.position.copy(rest.stem.p).y += 1.5*current;
      parts.closure.position.copy(rest.closure.p).y += .75*current;
      parts.label.position.copy(rest.label.p).addScaledVector(new T.Vector3(golden ? -1.85 : -1.25,.08,.65),current);
      parts.label.scale.copy(rest.label.s).multiplyScalar(1+.15*current);
      if (golden) parts.label.traverse(o => {if (o.isMesh) o.material.opacity=.05+.95*smooth(.03,.6,current);});
    } else if (pureVolume) {
      parts.closure.position.copy(rest.closure.p).y += .9*current;
      parts.stem.position.copy(rest.stem.p).y += 1.8*current;
      parts.head.position.copy(rest.head.p).y += 2.8*current;
      parts.cord.position.copy(rest.cord.p).addScaledVector(new T.Vector3(1.05,.30,.25),current);
      parts.label.position.copy(rest.label.p).addScaledVector(new T.Vector3(-1.65,.08,.65),current);
      parts.label.scale.copy(rest.label.s).multiplyScalar(1+.15*current);
      // The clear film should be readable in isolation without adding a paper patch at rest.
      parts.label.traverse(o => {if (o.isMesh) o.material.opacity=.05+.95*smooth(.03,.6,current);});
    } else if (woodland || coastal) {
      parts.closure.position.copy(rest.closure.p).y += 2.8*current;
      if (woodland) parts.liner.position.copy(rest.liner.p).y += 1.35*current;
      parts.label.position.copy(rest.label.p).addScaledVector(new T.Vector3(-1.50,.08,.65),current);
      parts.label.scale.copy(rest.label.s).multiplyScalar(1+.15*current);
    } else if (moisture) {
      parts.closure.position.copy(rest.closure.p).y += .85*current;
      parts.stem.position.copy(rest.stem.p).y += 1.75*current;
      parts.head.position.copy(rest.head.p).y += 2.8*current;
      parts.label.position.copy(rest.label.p).addScaledVector(new T.Vector3(-1.25,.08,.65),current);
      parts.label.scale.copy(rest.label.s).multiplyScalar(1+.15*current);
    } else if (collection) {
      const offsets={closure:[0,.48,0],liner:[0,.24,0],stem:[0,.88,0],head:[0,1.28,0],overcap:[.10,2.30,0],outerpack:[-.22,.02,-.20]};
      for (const [key,xyz] of Object.entries(offsets)) if(parts[key]) parts[key].position.copy(rest[key].p).addScaledVector(new T.Vector3(...xyz),current);
    } else if (pump) {
      parts.closure.position.copy(rest.closure.p).y += .38*current;
      parts.stem.position.copy(rest.stem.p).y += .84*current;
      parts.head.position.copy(rest.head.p).y += 1.35*current;
    } else {
    const capOpen = smooth(.02, .65, current), linerOpen = smooth(.27, 1, current);
    parts.cap.position.copy(rest.cap.p); parts.cap.position.y += .100 * capOpen;
    parts.cap.position.x -= .006 * capOpen;
    rotationEuler.set(-.75*capOpen, -Math.PI*1.25*capOpen, -.12*capOpen);
    capTilt.setFromEuler(rotationEuler); parts.cap.quaternion.copy(rest.cap.q).multiply(capTilt);
    parts.liner.position.copy(rest.liner.p); parts.liner.position.y += .047 * linerOpen;
    parts.liner.position.x += .002 * linerOpen;
    rotationEuler.set(.19*linerOpen, .12*linerOpen, -.1*linerOpen);
    linerTilt.setFromEuler(rotationEuler); parts.liner.quaternion.copy(rest.liner.q).multiply(linerTilt);
    }
    if (!explosion) {
    parts.print.position.copy(rest.print.p);
    parts.print.position.x -= (pdrn ? 2.15 : b5 ? 3.1 : golden ? 3.8 : pureVolume ? 3.4 : woodland || coastal ? 3.1 : moisture || gentle ? 2.65 : pump || collection ? .63 : .025)*current;
    parts.print.position.y += (gentle ? .50 : b5 ? .10 : golden ? .18 : moisture || woodland || pureVolume || coastal ? .18 : pump || collection ? .10 : .004)*current;
    parts.print.position.z += (pdrn ? 1.10 : moisture || woodland || pureVolume || gentle || coastal || golden || b5 ? 1.65 : pump || collection ? .86 : .035)*current;
    parts.print.scale.copy(rest.print.s).multiplyScalar(1+(gentle || golden || b5 ? .95 : .45)*current);
    }
    const aspect = width/height;
    // At half-open the cap is already high; reserve headroom without changing
    // the approved part poses, progress timing, rotation or scroll controls.
    const intermediateHeadroom = Math.sin(Math.PI * current);
    const interpolate = pair => pair[0]+(pair[1]-pair[0])*current;
    const assemblyCenter = explosion ? interpolate(explosion.camera.centerY) : b5 ? 1.45+current*1.8 : golden ? 1.45+current*2.4+intermediateHeadroom*.8 : pdrn ? 1.45+current*1.85+intermediateHeadroom*.25 : gentle ? 1.45+current*1.8+intermediateHeadroom*.3 : moisture || woodland || pureVolume || coastal ? 1.45+current*1.4 : pump || collection ? 1.48 + current*.65 : 1.25 + current*1.22 + intermediateHeadroom*.25;
    // Turn the assembly about its centre, so looking underneath does not
    // swing the jar out of the frame. The two translations cancel at rest.
    root.position.y = assemblyCenter;
    model.position.y = -assemblyCenter;
    root.rotation.set(pitch, yaw, 0);
    const tiltHeadroom = smooth(.2, 1.4, Math.abs(pitch)) * .7;
    shadow.material.opacity = 1 - smooth(.15, .7, Math.abs(pitch));
    let viewHeight = explosion ? Math.max(interpolate(explosion.camera.height)+tiltHeadroom,interpolate(explosion.camera.width)/aspect) : Math.max((b5 ? 4.2+current*4.6 : golden ? 4.2+current*4.5+intermediateHeadroom*1.6 : pdrn ? 4.2+current*4.3+intermediateHeadroom*1.3 : gentle ? 4.2+current*3.4+intermediateHeadroom*.6 : moisture || woodland || pureVolume || coastal ? 4.2+current*2.3 : pump || collection ? 4.2 + current*2.0 : 4.2 + current*3.05 + intermediateHeadroom*1.2) + tiltHeadroom, (pdrn ? 4.25 : b5 ? 3.8+current*3.6 : golden ? 3.9+current*3.4 : pureVolume ? 3.8+current*3.4 : woodland || coastal ? 3.65+current*2.75 : moisture || gentle ? 3.65+current*2.15 : product.wide ? 4.8 : 3.65)/aspect);
    let centerY = assemblyCenter + focus;
    let centerX = explosion ? interpolate(explosion.camera.centerX) : b5 ? -.4*current : golden ? -1.45*current : pureVolume ? -.75*current : woodland || coastal ? -.85*current : moisture || gentle ? -.65*current : 0;
    if(narrowReview) {
      root.updateMatrixWorld(true);
      const bounds=new T.Box3().setFromObject(root),size=bounds.getSize(new T.Vector3()),center=bounds.getCenter(new T.Vector3());
      centerX=center.x;centerY=center.y;
      viewHeight=Math.max(interpolate(explosion.camera.height),size.y+size.z*.105+.55,(size.x+.55)/aspect);
    }
    viewHeight /= zoom;
    camera.left = -viewHeight*aspect/2; camera.right = viewHeight*aspect/2;
    camera.top = viewHeight/2; camera.bottom = -viewHeight/2;
    camera.position.set(centerX, centerY+(pdrn || moisture || woodland || pureVolume || gentle || coastal || golden || b5 || review ? 1.05 : 2.35), 10);
    camera.lookAt(centerX, centerY, 0); camera.updateProjectionMatrix();
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
    setZoom(value) { const next=Number(value); if (Number.isFinite(next)) {zoom=clamp(next,.7,1.7);invalidate();} },
    resetView() { desiredYaw=0; desiredPitch=0; selected=null; focus=0; invalidate(); },
    rotate() { desiredYaw += Math.PI/2; invalidate(); },
    viewBottom() {
      desiredYaw=0; desiredPitch=-Math.PI/2-Math.atan2(pdrn || moisture || woodland || pureVolume || gentle || coastal || golden || b5 || review ? 1.05 : 2.35, 10);
      selected=null; focus=0; invalidate();
    },
    focusPart(key) {
      selected=key; desiredYaw=0; desiredPitch=key==='liner'?.16:key==='cap'?-.15:0;
      focus=key==='cap'?.25:key==='jar'?-.12:0; invalidate();
    },
    getState() { return {progress:target, renderedProgress:current, yaw, pitch, selected, zoom, printOffset:parts.print.position.clone().sub(rest.print.p).toArray(), components:Object.keys(parts), partStates:Object.fromEntries(Object.entries(parts).map(([key,o])=>[key,{visible:o.visible,position:o.position.toArray(),offset:o.position.clone().sub(rest[key].p).toArray(),scale:o.scale.toArray()}])), meshes:renderer.info.render.calls, triangles:renderer.info.render.triangles}; },
    dispose,
  };
  host.__packagingScene=api;
  cancelAnimationFrame(frame); frame = 0;
  mark('firstFrameStart'); pose(); mark('firstFrame');
  onReady?.(); return api;
  } catch (error) {dispose(); throw error;}
}
