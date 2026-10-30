import * as T from '../../src/structure/vendor/three.module.js';
import {GLTFLoader} from '../../src/structure/vendor/GLTFLoader.js';
const scope=document.getElementById('liaose-interactive')||document;
const host=scope.querySelector('#stage'),status=scope.querySelector('#status');
const data=JSON.parse(scope.querySelector('#models').textContent);
const state={product:Object.keys(data)[0],filled:true,yaw:0,pitch:0,zoom:1,ready:false};
let renderer,active,formula,glass=[],dirty=true;
const models={};
try {
 renderer=new T.WebGLRenderer({antialias:true,alpha:false,powerPreference:'high-performance'});
 renderer.setPixelRatio(Math.min(devicePixelRatio,1.5));renderer.toneMapping=T.ACESFilmicToneMapping;renderer.toneMappingExposure=1;
 host.append(renderer.domElement);const canvas=renderer.domElement;canvas.setAttribute('aria-label','3D 产品，可拖动旋转、滚轮缩放');
 const scene=new T.Scene(),background=new T.Color('#e6ddcf');scene.background=background;
 const camera=new T.PerspectiveCamera(36,1,.1,50);camera.position.set(0,1.7,6.2);camera.lookAt(0,1.45,0);
 const root=new T.Group();root.position.y=1.45;scene.add(root);
 const studio=new T.Scene();studio.background=new T.Color('#9f9b91');
 function card(p,size,color,power){const m=new T.MeshBasicMaterial({color,side:T.DoubleSide});m.color.multiplyScalar(power);const o=new T.Mesh(new T.PlaneGeometry(...size),m);o.position.set(...p);o.lookAt(0,1.4,0);studio.add(o);}
 card([-4,3,4],[1.7,6],'#fff8ed',2.5);card([4,2,3],[.7,5],'#ffffff',2);card([0,6,-2],[5,3],'#fffaf1',1.7);card([0,2,-5],[3,4],'#ffffff',1.2);card([0,2,5],[2,6],'#514b43',.7);
 const pmrem=new T.PMREMGenerator(renderer),env=pmrem.fromScene(studio,.03);scene.environment=env.texture;pmrem.dispose();studio.traverse(o=>{o.geometry?.dispose();o.material?.dispose();});
 scene.add(new T.HemisphereLight('#fff6e9','#8b8070',1.0));
 for(const [x,y,z,power] of [[-3,5,4,2.0],[4,3,-2,1.1]]){const l=new T.DirectionalLight('#fff7ee',power);l.position.set(x,y,z);scene.add(l);}
 const target=new T.WebGLRenderTarget(1,1,{type:T.HalfFloatType});target.texture.colorSpace=T.LinearSRGBColorSpace;
 // shortcut: Two ordered transmission passes approximate nested liquid/glass; use path tracing for physically converged internal reflections.
 function render(){
  if(!dirty||!active)return;dirty=false;root.rotation.set(state.pitch,state.yaw,0);camera.zoom=state.zoom;camera.updateProjectionMatrix();canvas.dataset.yaw=state.yaw.toFixed(3);canvas.dataset.pitch=state.pitch.toFixed(3);canvas.dataset.zoom=state.zoom.toFixed(3);canvas.dataset.filled=String(state.filled);
  scene.background=background;formula.visible=state.filled;
  if(state.filled){glass.forEach(o=>o.visible=false);renderer.toneMapping=T.NoToneMapping;renderer.setRenderTarget(target);renderer.render(scene,camera);glass.forEach(o=>o.visible=true);formula.visible=false;scene.background=target.texture;}
  renderer.toneMapping=T.ACESFilmicToneMapping;renderer.setRenderTarget(null);renderer.render(scene,camera);formula.visible=state.filled;scene.background=background;
 }
 function resize(){const {width,height}=host.getBoundingClientRect();renderer.setSize(width,height,false);camera.aspect=width/Math.max(1,height);const px=renderer.getDrawingBufferSize(new T.Vector2());target.setSize(px.x,px.y);dirty=true;render();}
 new ResizeObserver(resize).observe(host);
 function update(){
  if(active)root.remove(active);active=models[state.product];root.add(active);formula=active.getObjectByName('Formula');glass=[];active.traverse(o=>{if(o.isMesh&&o.material.transmission>.5&&!isIn(o,formula))glass.push(o);});
  scope.querySelectorAll('[data-product]').forEach(b=>b.setAttribute('aria-pressed',String(b.dataset.product===state.product)));
  scope.querySelectorAll('[data-filled]').forEach(b=>b.setAttribute('aria-pressed',String((b.dataset.filled==='true')===state.filled)));
  scope.querySelector('#name').textContent=state.product==='oil'?'Body Oil 02':'Daily Emulsion';
  status.textContent=(state.filled?'含料体':'空包材')+' · 拖动旋转，滚轮缩放';dirty=true;resize();
 }
 function isIn(o,parent){while(o){if(o===parent)return true;o=o.parent;}return false;}
 const loader=new GLTFLoader();
 loader.register(parser=>{parser.textureLoader=new T.TextureLoader(parser.options.manager);return {name:'EmbeddedImageTextures'};});
 for(const key of Object.keys(data)){
  const bytes=Uint8Array.from(atob(data[key]),c=>c.charCodeAt(0));const buffer=bytes[0]===31&&bytes[1]===139?await new Response(new Blob([bytes]).stream().pipeThrough(new DecompressionStream('gzip'))).arrayBuffer():bytes.buffer;const gltf=await loader.parseAsync(buffer,'');const model=gltf.scene;model.position.y=-1.45;
  const fill=model.getObjectByName('Formula');if(!fill)throw new Error('料体模型缺失');
  model.traverse(o=>{
   if(!o.isMesh)return;o.frustumCulled=false;const m=o.material;
   if(isIn(o,model.getObjectByName('PaperLabel'))){o.visible=false;return;}
   if(m.map){m.depthWrite=false;m.polygonOffset=true;m.polygonOffsetFactor=-2;o.renderOrder=3;m.side=T.FrontSide;}
   else if(m.transmission>.5){m.side=T.FrontSide;m.envMapIntensity=.8;if(!isIn(o,fill)){m.ior=1.48;m.thickness=.04;m.specularIntensity=.8;m.toneMapped=false;m.side=T.DoubleSide;}}
  });models[key]=model;
 }
 const saved=window.openai?.widgetState?.privateContent;if(saved){for(const key of ['yaw','pitch','zoom'])if(Number.isFinite(saved[key]))state[key]=saved[key];if(typeof saved.filled==='boolean')state.filled=saved.filled;}
 const save=()=>window.openai?.setWidgetState({modelContent:{product:state.product,filled:state.filled},privateContent:{yaw:state.yaw,pitch:state.pitch,zoom:state.zoom,filled:state.filled}})?.catch(()=>{});
 window.addEventListener('openai:set_globals',e=>{const s=e.detail?.globals?.widgetState?.privateContent;if(s){for(const key of ['yaw','pitch','zoom'])if(Number.isFinite(s[key]))state[key]=s[key];if(typeof s.filled==='boolean')state.filled=s.filled;update();}});
 state.ready=true;scope.querySelectorAll('button').forEach(b=>b.disabled=false);update();
 scope.querySelectorAll('[data-product]').forEach(b=>b.onclick=()=>{state.product=b.dataset.product;update();save();});
 scope.querySelectorAll('[data-filled]').forEach(b=>b.onclick=()=>{state.filled=b.dataset.filled==='true';update();save();});
 scope.querySelector('#reset').onclick=()=>{Object.assign(state,{yaw:0,pitch:0,zoom:1});dirty=true;render();save();};
 scope.querySelector('#rotate').onclick=()=>{state.yaw+=Math.PI/2;dirty=true;render();save();};
 let last=null;
 canvas.onpointerdown=e=>{canvas.dataset.pointer=e.type+':'+e.button;if(e.button!==0)return;last={x:e.clientX,y:e.clientY,id:e.pointerId};canvas.setPointerCapture(e.pointerId);canvas.focus();};
 canvas.onpointermove=e=>{canvas.dataset.pointer=e.type+':'+e.buttons;if(!last||last.id!==e.pointerId)return;state.yaw+=(e.clientX-last.x)*.009;state.pitch=T.MathUtils.clamp(state.pitch+(e.clientY-last.y)*.008,-1.3,1.3);last={x:e.clientX,y:e.clientY,id:e.pointerId};dirty=true;render();};
 canvas.onpointerup=canvas.onpointercancel=()=>{last=null;save();};canvas.onlostpointercapture=()=>last=null;
 canvas.addEventListener('wheel',e=>{canvas.dataset.wheel=String(e.deltaY);e.preventDefault();state.zoom=T.MathUtils.clamp(state.zoom*Math.exp(-e.deltaY*.001),.65,2.3);dirty=true;render();},{passive:false});
 canvas.onkeydown=e=>{if(!['ArrowLeft','ArrowRight','ArrowUp','ArrowDown','+','=','-'].includes(e.key))return;e.preventDefault();if(e.key==='ArrowLeft')state.yaw-=.15;if(e.key==='ArrowRight')state.yaw+=.15;if(e.key==='ArrowUp')state.pitch-=.12;if(e.key==='ArrowDown')state.pitch+=.12;if(e.key==='+'||e.key==='=')state.zoom*=1.1;if(e.key==='-')state.zoom/=1.1;state.pitch=T.MathUtils.clamp(state.pitch,-1.3,1.3);state.zoom=T.MathUtils.clamp(state.zoom,.65,2.3);dirty=true;render();};
 canvas.addEventListener('webglcontextlost',e=>{e.preventDefault();status.textContent='3D 显示中断，请重新打开此页。';});
 window.demo={state:()=>({...state,formulaVisible:formula.visible,canvas:[canvas.width,canvas.height],meshes:active.children.length}),render};
} catch(e){status.textContent='3D 加载失败：'+e.message;scope.querySelector('#error').hidden=false;console.error(e);}
