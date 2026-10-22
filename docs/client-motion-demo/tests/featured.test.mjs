import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync, readdirSync} from 'node:fs';
import {fileURLToPath} from 'node:url';
import {resolve} from 'node:path';
import {createHash} from 'node:crypto';

const base=fileURLToPath(new URL('../',import.meta.url));
const json=path=>JSON.parse(readFileSync(resolve(base,path),'utf8'));
const featured=json('src/featured.json'),posters=json('src/posters.json'),manifest=json('featured-manifest.json');
const hash=path=>createHash('sha256').update(readFileSync(path)).digest('hex');

test('eight featured products map by stable ID to the current approved collection',()=>{
 assert.equal(featured.length,8);assert.equal(new Set(featured.map(p=>p.id)).size,8);
 assert.equal(featured[0].id,'poster-012');assert.equal(featured[0].background,'#f4c8d6');
 for(const item of featured){
  assert.ok(posters.some(p=>p.id===item.id));
  assert.ok(item.name&&item.kind.zh&&item.kind.en&&item.description.zh&&item.description.en);
  for(const colour of [item.background,item.ink,...item.swatch])assert.match(colour,/^#[0-9a-f]{6}$/);
  assert.equal(item.swatch.length,2);
 }
});

test('derived cutouts are independently accounted for and cannot overwrite approved poster assets',()=>{
 assert.equal(manifest.scope,'approved-client1.2-display-derivatives');
 assert.deepEqual(manifest.files.map(p=>p.posterId).sort(),featured.map(p=>p.id).sort());
 assert.deepEqual(readdirSync(resolve(base,'featured-assets')).sort(),featured.map(p=>`${p.id}.png`).sort());
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
 let total=0;
 for(const [id,item] of Object.entries(media)){
  assert.equal(item.sourceSha256,manifest.files.find(p=>p.posterId===id).sha256);
  assert.equal('placeholder' in item,false,'tiny full-size placeholders must not ship in the client bundle');
  for(const size of ['640','1024']){
   const entry=item.files[size],file=readFileSync(resolve(base,entry.file));
   assert.equal(hash(resolve(base,entry.file)),entry.sha256);assert.equal(file.length,entry.bytes);
   assert.equal(file.subarray(8,12).toString(),'WEBP');assert.ok(Math.max(entry.width,entry.height)<=Number(size));
   assert.equal(hash(resolve(base,'public/featured',`${id}-${size}.webp`)),entry.sha256);
  }
  assert.ok(item.files['640'].bytes<110000);total+=item.files['640'].bytes;
 }
 assert.ok(total<500000);assert.ok(media['poster-012'].files['640'].bytes<80000);
});
