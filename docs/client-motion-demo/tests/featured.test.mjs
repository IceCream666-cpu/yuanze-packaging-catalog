import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync, readdirSync} from 'node:fs';
import {fileURLToPath} from 'node:url';
import {resolve} from 'node:path';
import {createHash} from 'node:crypto';
import {PACKAGING_PRODUCTS} from '../src/structure/packaging-products.js';

const base=fileURLToPath(new URL('../',import.meta.url));
const json=path=>JSON.parse(readFileSync(resolve(base,path),'utf8'));
const featured=json('src/featured.json'),posters=json('src/posters.json'),manifest=json('featured-manifest.json');
const hash=path=>createHash('sha256').update(readFileSync(path)).digest('hex');

test('featured retains the exact original 24 order and appends only the two existing 3D products',()=>{
 const original=[12,13,39,49,42,51,44,47,56,57,58,59,60,61,62,63,64,65,66,67,68,69,70,71];
 assert.deepEqual(featured.map(p=>p.id),[...original,72,73,79].map(n=>`poster-${String(n).padStart(3,'0')}`));
 assert.equal(new Set(featured.map(p=>p.id)).size,27);
 assert.deepEqual(Object.keys(PACKAGING_PRODUCTS).sort(),featured.map(p=>p.id).sort());
 assert.equal(featured[0].id,'poster-012');assert.equal(featured[0].background,'#f4c8d6');
 for(const item of featured){
  assert.ok(posters.some(p=>p.id===item.id));
  assert.ok(PACKAGING_PRODUCTS[item.id].file);
  assert.ok(item.name&&item.kind.zh&&item.kind.en&&item.description.zh&&item.description.en);
  for(const colour of [item.background,item.ink,...item.swatch])assert.match(colour,/^#[0-9a-f]{6}$/);
  assert.equal(item.swatch.length,2);
 }
});

test('poster-derived single bottles retain detail identity and theme without claiming empty contents',()=>{
 for(const id of ['poster-072','poster-073']){
  const item=featured.find(p=>p.id===id),design=PACKAGING_PRODUCTS[id].design;
  for(const key of ['name','background','ink','swatch'])assert.deepEqual(item[key],design[key],`${id} ${key}`);
  assert.match(item.kind.zh,/单瓶/);
  assert.doesNotMatch(JSON.stringify([item.kind,item.description]),/空包材|empty/);
  const source=manifest.files.find(p=>p.posterId===id);
  assert.equal(source.productCount,1);
  assert.equal(source.sourceModel,undefined,'The display image is derived from the poster, not the empty GLB');
 }
 assert.match(featured.find(p=>p.id==='poster-073').description.zh,/02号单瓶.*金琥珀色油液/);
 assert.match(manifest.files.find(p=>p.posterId==='poster-073').selectedObject,/02.*only/);
});

test('derived cutouts are independently accounted for and cannot overwrite approved poster assets',()=>{
 assert.equal(manifest.version,'client1.41');
 assert.equal(manifest.scope,`approved-${manifest.version}-display-derivatives`);
 assert.deepEqual(manifest.files.map(p=>p.posterId).sort(),featured.map(p=>p.id).sort());
 const archived=Array.from({length:5},(_,i)=>`poster-${String(74+i).padStart(3,'0')}`);
 assert.ok(archived.every(id=>!featured.some(p=>p.id===id)));
 assert.deepEqual(readdirSync(resolve(base,'featured-assets')).sort(),[...featured.map(p=>`${p.id}.png`),...archived.map(id=>`${id}.png`)].sort());
 assert.deepEqual(readdirSync(resolve(base,'public/featured')).sort(),featured.flatMap(p=>[`${p.id}.png`,`${p.id}-640.webp`,`${p.id}-1024.webp`]).sort());
 for(const entry of manifest.files){
  assert.equal(entry.file,`featured-assets/${entry.posterId}.png`);
  assert.equal(entry.target,`featured/${entry.posterId}.png`);
  assert.equal(entry.productionTarget,`assets/featured/${entry.posterId}.png`);
  assert.equal(entry.approvedPoster,`server-reference/public/showroom/assets/posters/${entry.posterId}.webp`);
  assert.equal(hash(resolve(base,'../..',entry.approvedPoster)),entry.approvedPosterSha256);
  const file=readFileSync(resolve(base,entry.file));
  assert.equal(hash(resolve(base,entry.file)),entry.sha256);assert.equal(file.length,entry.bytes);
  assert.equal(hash(resolve(base,'public',entry.target)),entry.sha256);
  assert.equal(file.subarray(1,4).toString(),'PNG');
  assert.ok(file.readUInt32BE(16)>=800&&file.readUInt32BE(20)>=800);
  assert.equal(file[25],6,'Each product has an RGBA channel rather than a baked background');
 }
});

test('mobile display derivatives retain source identity and fit the first-screen budget',()=>{
 const media=json('src/featured-media.json');
 assert.deepEqual(Object.keys(media).sort(),featured.map(p=>p.id).sort());
 for(const [id,item] of Object.entries(media)){
  assert.equal(item.sourceSha256,manifest.files.find(p=>p.posterId===id).sha256);
  assert.equal('placeholder' in item,false,'tiny full-size placeholders must not ship in the client bundle');
  for(const size of ['640','1024']){
   const entry=item.files[size],file=readFileSync(resolve(base,entry.file));
   assert.equal(hash(resolve(base,entry.file)),entry.sha256);assert.equal(file.length,entry.bytes);
   assert.equal(file.subarray(8,12).toString(),'WEBP');assert.ok(Math.max(entry.width,entry.height)<=Number(size));
   assert.equal(hash(resolve(base,'public/featured',`${id}-${size}.webp`)),entry.sha256);
  }
  assert.ok(item.files['640'].bytes<110000);
 }
 const initial=[0,1,-1,2,-2].map(offset=>featured[(offset+featured.length)%featured.length].id);
 assert.ok(initial.reduce((sum,id)=>sum+media[id].files['640'].bytes,0)<500000,'Current product and four neighbours retain the initial mobile resource budget');
 assert.ok(media['poster-012'].files['640'].bytes<80000);
});
