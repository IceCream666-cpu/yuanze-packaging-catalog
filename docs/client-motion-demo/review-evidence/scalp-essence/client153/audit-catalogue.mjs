// Inspect real shipping GLBs, using the same scene/part resolution as the viewer.
import {readFileSync,writeFileSync} from 'node:fs';
import {createHash} from 'node:crypto';
import assert from 'node:assert/strict';
import {PACKAGING_PRODUCTS} from '../../../src/structure/packaging-products.js';
const base=new URL('../../../',import.meta.url),read=p=>JSON.parse(readFileSync(new URL(p,base),'utf8'));
const posters=read('src/posters.json'),featured=read('src/featured.json');
const manifest=read('../../server-reference/public/showroom/bundle-manifest.json');
const results=[];
for(const [id,p] of Object.entries(PACKAGING_PRODUCTS)){
 assert.ok(posters.some(x=>x.id===id),id);
 const b=readFileSync(new URL('packaging-assets/'+p.file,base));
 assert.equal(b.toString('ascii',0,4),'glTF');assert.equal(b.readUInt32LE(4),2);assert.equal(b.readUInt32LE(8),b.length);
 const g=JSON.parse(b.toString('utf8',20,20+b.readUInt32LE(12)));
 const scenes=p.finishes?g.scenes:[g.scenes[g.scene??0]];
 for(const scene of scenes){
  const active=new Set();const walk=i=>{assert.ok(i>=0&&i<g.nodes.length);assert.ok(!active.has(i),'cycle or repeated scene node');active.add(i);for(const j of g.nodes[i].children??[])walk(j);};scene.nodes.forEach(walk);
  for(const part of p.parts){
   const found=p.finishes?scene.nodes.some(i=>g.nodes[i].extras?.partKey===part.node):[...active].some(i=>g.nodes[i].name===part.node);
   assert.ok(found,`${id}/${scene.name}/${part.node}`);
  }
 }
 for(const finish of p.finishes??[])assert.ok(scenes.some(s=>s.name===finish.scene),id);
 for(const n of g.nodes)for(const k of ['translation','rotation','scale','matrix'])assert.ok((n[k]??[]).every(Number.isFinite),id);
 for(const a of g.accessors)for(const k of ['min','max'])assert.ok((a[k]??[]).every(Number.isFinite),id);
 for(const buffer of g.buffers)assert.equal(buffer.uri,undefined);
 for(const image of g.images??[])assert.ok(!image.uri||image.uri.startsWith('data:'),id);
 assert.equal(createHash('sha256').update(b).digest('hex'),manifest.files['assets/packaging/'+p.file].sha256);
 results.push({id,file:p.file,parts:p.parts.map(x=>x.node),scenes:scenes.length,bytes:b.length,onHome:featured.some(x=>x.id===id),valid:true});
}
assert.equal(results.length,32);assert.equal(new Set(posters.map(x=>x.id)).size,68);assert.equal(posters.length,68);
assert.equal(new Set(featured.map(x=>x.id)).size,31);assert.equal(featured.length,31);assert.ok(featured.every(x=>PACKAGING_PRODUCTS[x.id]));
assert.ok(!Object.keys(manifest.files).some(p=>p.includes('poster-086')));
const out={counts:{posters:68,featured:31,models:32},allGlbChecksPassed:true,models:results,intentionalHomeExclusion:{'poster-080':'Replaced on homepage by approved poster-082 duo; retained in catalogue'},unfinishedSimplification:['poster-067','poster-068','poster-071'],withdrawn:'poster-086'};
writeFileSync(new URL('catalogue-audit.json',import.meta.url),JSON.stringify(out,null,2)+'\n');console.log({actualGlbValidated:32,featuredWithModel:31,duplicatePosterIds:0,withdrawnAbsent:true});
