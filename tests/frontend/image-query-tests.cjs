const {test}=require('node:test');
const assert=require('node:assert/strict');
const path=require('node:path');
const {JSDOM}=require('jsdom');
const {evaluateBrowserModule}=require('./module-loader.cjs');
const {pictureFile,installImageBrowser}=require('./image-browser-fixture.cjs');
const file=path.resolve(__dirname,'../../server-reference/public/image-query.js');
async function context(options={}){const dom=new JSDOM('<canvas id="preview" tabindex="0"></canvas>',{url:'https://catalog.test',runScripts:'outside-only'});const w=dom.window,operations=installImageBrowser(w,options);return {dom,w,d:w.document,operations,api:(await evaluateBrowserModule(dom,file)).namespace};}
test('12 MP camera photo with empty MIME is resized and encoded as a white-backed bounded JPEG',async()=>{
  const p=await context();try{
    const original=pictureFile(p.w,'camera',{width:4032,height:3024,type:''}),size=original.size;
    const canvas=await p.api.prepareImageQuery(original);
    assert.deepEqual([canvas.width,canvas.height],[1280,960]);assert.equal(original.size,size);
    assert.equal(p.operations.find(op=>op.type==='fill').style,'#fff');
    assert.equal(p.operations.find(op=>op.type==='draw').args[0].naturalWidth,4032);
    const query=p.api.imageQueryDataURL(canvas);assert.match(query,/^data:image\/jpeg;base64,/);
    assert.deepEqual(p.operations.filter(op=>op.type==='encode').map(op=>[op.width,op.height]),[[1280,960]]);
  }finally{p.dom.window.close();}
});
test('supported content overrides a misleading MIME; forged SVG, HEIC, oversized and tiny images fail usefully',async()=>{
  const p=await context();try{
    assert.equal((await p.api.prepareImageQuery(pictureFile(p.w,'test.bin',{type:'application/octet-stream'}))).width,320);
    await assert.rejects(p.api.prepareImageQuery(new p.w.File(['<svg/>'],'fake.jpg',{type:'image/jpeg'})),/转换图片格式/);
    const heic=new p.w.File([Buffer.from('\x00\x00\x00\x18ftypheic0000mif1')],'camera.heic',{type:'image/heic'});
    await assert.rejects(p.api.prepareImageQuery(heic),/HEIC.*JPG/);
    await assert.rejects(p.api.prepareImageQuery(new p.w.File([],'empty.jpg')),/不能为空/);
    const oversized=pictureFile(p.w);Object.defineProperty(oversized,'size',{value:20*1024*1024+1});await assert.rejects(p.api.prepareImageQuery(oversized),/20 MB/);
    await assert.rejects(p.api.prepareImageQuery(pictureFile(p.w,'small.png',{width:8,height:8})),/至少 32/);
  }finally{p.dom.window.close();}
  const huge=await context({dimensions:{width:8000,height:6000}});try{await assert.rejects(huge.api.prepareImageQuery(pictureFile(huge.w)),/4000 万像素/);assert.equal(huge.operations.length,0);}finally{huge.dom.window.close();}
});
test('preparation can be cancelled during browser decode and corrupt decode cannot reach the upload',async()=>{
  const p=await context({decodeDelay:30});try{
    const controller=new AbortController(),work=p.api.prepareImageQuery(pictureFile(p.w),{signal:controller.signal});setTimeout(()=>controller.abort(),10);
    await assert.rejects(work,error=>error.name==='AbortError');assert.equal(p.operations.length,0);
  }finally{p.dom.window.close();}
  const broken=await context({broken:true});try{await assert.rejects(broken.api.prepareImageQuery(pictureFile(broken.w)),/无法读取图片/);assert.equal(broken.operations.length,0);}finally{broken.dom.window.close();}
});
test('mouse and touch coordinates, keyboard target selection, rotation, reset and crop export use only the chosen region',async()=>{
  const p=await context();try{
    const base=await p.api.prepareImageQuery(pictureFile(p.w)),canvas=p.d.querySelector('canvas'),selection=p.api.bindImageQueryCrop(canvas,base);
    canvas.getBoundingClientRect=()=>({left:10,top:20,width:160,height:320});
    const pointer=(type,x,y)=>{const e=new p.w.Event(type,{cancelable:true});Object.assign(e,{pointerId:1,button:0,clientX:x,clientY:y});canvas.dispatchEvent(e);};
    pointer('pointerdown',30,40);pointer('pointermove',110,260);pointer('pointerup',110,260);
    assert.deepEqual({...selection.crop},{x:40,y:40,w:160,h:440});selection.dataURL();
    const draw=p.operations.filter(op=>op.type==='draw').at(-1);assert.deepEqual(draw.args.slice(1),[40,40,160,440,0,0,160,440]);
    selection.reset();assert.equal(selection.crop,null);
    canvas.dispatchEvent(new p.w.KeyboardEvent('keydown',{key:'ArrowRight',cancelable:true}));assert.ok(selection.crop);
    const oldWidth=selection.crop.w;canvas.dispatchEvent(new p.w.KeyboardEvent('keydown',{key:'ArrowLeft',shiftKey:true,cancelable:true}));assert.ok(selection.crop.w<oldWidth);
    canvas.dispatchEvent(new p.w.KeyboardEvent('keydown',{key:'Escape',cancelable:true}));assert.equal(selection.crop,null);
    const rotated=p.api.rotateImageQuery(base);assert.deepEqual([rotated.width,rotated.height],[640,320]);assert.equal(p.operations.filter(op=>op.type==='rotate').at(-1).args[0],Math.PI/2);
    assert.throws(()=>p.api.imageQueryDataURL(base,{x:1,y:1,w:4,h:8}),/范围过小/);
    selection.dispose();canvas.dispatchEvent(new p.w.KeyboardEvent('keydown',{key:'ArrowRight'}));assert.equal(selection.crop,null);
  }finally{p.dom.window.close();}
});
test('oversized or duplicated match lists preserve the best 120 candidates with a bounded URL budget',async()=>{
  const p=await context();try{
    const matches=Array.from({length:900},(_,i)=>({record_id:'row-'+i,image_path:'media/p'+i+'.jpg',score:1-i/1000}));
    matches.unshift(null,{record_id:[],image_path:{}},{record_id:'',image_path:'bad'},matches[0]);
    const bounded=p.api.boundedImageMatches(matches);assert.equal(bounded.length,120);assert.equal(bounded[0].record_id,'row-0');assert.equal(bounded.at(-1).record_id,'row-119');
    const long=Array.from({length:900},(_,i)=>({record_id:'包'.repeat(60)+i,image_path:'media/image.jpg'}));
    const result=p.api.boundedImageMatches(long);assert.ok(result.length<120);assert.ok(result.reduce((n,r)=>n+encodeURIComponent(r.record_id).length+10,0)<=5000);
  }finally{p.dom.window.close();}
});
