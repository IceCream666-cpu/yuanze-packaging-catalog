import * as T from '../../client-motion-demo/src/structure/vendor/three.module.js';
import {GLTFLoader} from '../../client-motion-demo/src/structure/vendor/GLTFLoader.js';
import {OrbitControls} from './OrbitControls.js';
(async()=>{
const host=document.querySelector('#stage'),status=document.querySelector('#status'),zoom=document.querySelector('#zoom'),auto=document.querySelector('#auto');
let renderer,controls;
const reduced=matchMedia('(prefers-reduced-motion: reduce)').matches;
try {
 renderer=new T.WebGLRenderer({antialias:true,alpha:true});renderer.setPixelRatio(Math.min(devicePixelRatio,2));renderer.outputColorSpace=T.SRGBColorSpace;renderer.toneMapping=T.ACESFilmicToneMapping;renderer.toneMappingExposure=1.05;host.prepend(renderer.domElement);
 const scene=new T.Scene(),camera=new T.PerspectiveCamera(32,1,.05,100);camera.position.set(.65,2.15,6.5);
 controls=new OrbitControls(camera,renderer.domElement);controls.target.set(0,1.48,0);controls.enablePan=false;controls.enableDamping=true;controls.minDistance=3.8;controls.maxDistance=9;controls.minPolarAngle=.15;controls.maxPolarAngle=Math.PI-.15;controls.autoRotateSpeed=.9;controls.update();controls.saveState();
 const studio=new T.Scene();studio.background=new T.Color('#98978e');
 for(const [pos,size,strength] of [[[-4,4,3],[3,6],3],[[4,2,1],[2,5],2],[[0,5,-3],[4,3],2.5]]){const m=new T.MeshBasicMaterial({color:0xffffff,side:T.DoubleSide});m.color.multiplyScalar(strength);const card=new T.Mesh(new T.PlaneGeometry(...size),m);card.position.set(...pos);card.lookAt(0,1,0);studio.add(card);}
 const pmrem=new T.PMREMGenerator(renderer),environment=pmrem.fromScene(studio,.08);scene.environment=environment.texture;pmrem.dispose();studio.traverse(o=>{o.geometry?.dispose();o.material?.dispose();});
 scene.add(new T.HemisphereLight(0xfffaf0,0x6a7060,1.2));
 const light=new T.DirectionalLight(0xfff8ed,2.7);light.position.set(-3,5,4);scene.add(light);const fill=new T.DirectionalLight(0xe5edff,.8);fill.position.set(4,3,-2);scene.add(fill);
 const raw=atob(document.querySelector('#model-data').textContent.trim()),bytes=Uint8Array.from(raw,c=>c.charCodeAt(0));
 const gltf=await new GLTFLoader().parseAsync(bytes.buffer,'');scene.add(gltf.scene);gltf.scene.traverse(o=>{if(o.isMesh){o.material.envMapIntensity=.55;if(o.material.map)o.material.map.anisotropy=Math.min(8,renderer.capabilities.getMaxAnisotropy());}});
 const shadowCanvas=document.createElement('canvas');shadowCanvas.width=shadowCanvas.height=128;const ctx=shadowCanvas.getContext('2d'),g=ctx.createRadialGradient(64,64,3,64,64,64);g.addColorStop(0,'rgba(40,48,30,.22)');g.addColorStop(1,'rgba(40,48,30,0)');ctx.fillStyle=g;ctx.fillRect(0,0,128,128);const shadow=new T.Mesh(new T.PlaneGeometry(2.6,1.9),new T.MeshBasicMaterial({map:new T.CanvasTexture(shadowCanvas),transparent:true,depthWrite:false}));shadow.rotation.x=-Math.PI/2;shadow.position.y=-.015;scene.add(shadow);
 const frame=()=>{const w=host.clientWidth,h=host.clientHeight;renderer.setSize(w,h,false);camera.aspect=w/h;camera.updateProjectionMatrix();};new ResizeObserver(frame).observe(host);frame();
 const setZoom=value=>{const direction=camera.position.clone().sub(controls.target).normalize();camera.position.copy(controls.target).addScaledVector(direction,9-value/100*5.2);controls.update();};
 zoom.addEventListener('input',()=>setZoom(Number(zoom.value)));controls.addEventListener('change',()=>{zoom.value=String(Math.round((9-camera.position.distanceTo(controls.target))/5.2*100));});
 auto.addEventListener('click',()=>{controls.autoRotate=!controls.autoRotate;auto.setAttribute('aria-pressed',String(controls.autoRotate));auto.textContent=controls.autoRotate?'暂停旋转':'自动旋转';});
 document.querySelector('#reset').addEventListener('click',()=>{gltf.scene.rotation.y=0;controls.reset();controls.autoRotate=false;auto.setAttribute('aria-pressed','false');auto.textContent='自动旋转';});
 host.addEventListener('keydown',e=>{if(['ArrowLeft','ArrowRight','ArrowUp','ArrowDown'].includes(e.key)){e.preventDefault();if(e.key==='ArrowLeft'||e.key==='ArrowRight')gltf.scene.rotation.y+=(e.key==='ArrowLeft'?-1:1)*.15;else setZoom(Math.max(0,Math.min(100,Number(zoom.value)+(e.key==='ArrowUp'?5:-5))));}});
 let last=performance.now();renderer.setAnimationLoop(now=>{const dt=Math.min((now-last)/1000,.05);last=now;controls.update(dt);renderer.render(scene,camera);});
 document.addEventListener('visibilitychange',()=>{if(document.hidden){controls.autoRotate=false;auto.textContent='自动旋转';auto.setAttribute('aria-pressed','false');}});
 for(const button of document.querySelectorAll('button,input'))button.disabled=false;
 status.textContent='';host.dataset.ready='true';host.setAttribute('aria-busy','false');
 const bounds=new T.Box3().setFromObject(gltf.scene),size=bounds.getSize(new T.Vector3());if(size.y<2.9||size.x<1.4)throw Error('Model bounds invalid');
 if(reduced)controls.enableDamping=false;
 window.addEventListener('pagehide',()=>{controls.dispose();renderer.setAnimationLoop(null);renderer.dispose();environment.dispose();gltf.scene.traverse(o=>{o.geometry?.dispose();if(o.material){for(const value of Object.values(o.material))if(value?.isTexture)value.dispose();o.material.dispose();}});},{once:true});
} catch(error){console.error(error);status.textContent='模型未能加载，请重新打开页面。';host.setAttribute('aria-busy','false');document.querySelector('#retry').hidden=false;document.querySelector('#retry').onclick=()=>location.reload();}

})();
