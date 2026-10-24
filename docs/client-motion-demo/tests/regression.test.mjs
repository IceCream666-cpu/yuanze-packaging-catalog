import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync,statSync,readdirSync} from 'node:fs';
import {fileURLToPath} from 'node:url';
import {resolve,relative} from 'node:path';
import {createHash} from 'node:crypto';
import {FAVORITES_KEY,filterPosters,readFavorites,persist,toggleFavorite} from '../src/model.js';
import {FAVORITES_KEY as previousFavoritesKey} from '../../client-apple-demo/src/model.js';

const base=fileURLToPath(new URL('../',import.meta.url));
const root=resolve(base,'../..');
const json=path=>JSON.parse(readFileSync(path,'utf8'));
const posters=json(resolve(base,'src/posters.json'));
const previous=json(resolve(base,'../client-apple-demo/src/posters.json'));
const manifest=json(resolve(base,'assets-manifest.json'));
const packagingManifest=json(resolve(base,'packaging-manifest.json'));
const assetPaths=json(resolve(base,'src/asset-paths.json'));
const approvedBundle=json(resolve(root,'server-reference/public/showroom/bundle-manifest.json'));
const raw=readFileSync(resolve(root,'server-reference/public/showroom/product-posters.js'),'utf8');
const approved=JSON.parse(raw.slice(raw.indexOf('{')).trim().replace(/;$/,''));
const hash=path=>createHash('sha256').update(readFileSync(path)).digest('hex');

test('the approved collection grows without dropping previous poster identities or changing their public facts',()=>{
 assert.ok(posters.length>=previous.length);
 assert.equal(new Set(posters.map(p=>p.id)).size,posters.length);
 assert.deepEqual(posters.map(p=>p.id).sort(),approved.items.map(p=>p.id).sort());
 for(const original of previous){
  const current=posters.find(p=>p.id===original.id);assert.ok(current,original.id);
  for(const field of ['title','category','width','height'])assert.deepEqual(current[field],original[field],`${original.id}.${field}`);
 }
 for(const p of posters){
  assert.deepEqual(Object.keys(p).sort(),['id','title','category','style','image','thumb','original','width','height','smallImage','smallWidth','smallHeight','imageWidth','imageHeight','stripThumb','stripWidth','stripHeight'].sort());
  assert.deepEqual(Object.keys(p.title).sort(),['en','zh']);
  const source=approved.items.find(item=>item.id===p.id);
  assert.deepEqual(p.title,source.title);assert.equal(p.category,source.category);
  assert.equal(p.width,source.width);assert.equal(p.height,source.height);
  for(const field of ['image','thumb','original'])assert.match(p[field],/^\/assets\/poster-\d+(?:-thumb|-original)?\.webp$/);
 }
});

test('original poster assets and separately approved packaging assets match exactly their manifests and bytes',()=>{
 assert.equal(manifest.count,posters.length);assert.equal(manifest.files.length,posters.length*5+2);
 assert.equal(new Set(manifest.files.map(f=>f.target)).size,manifest.files.length);
 const declared=new Set(manifest.files.map(f=>f.target));
 assert.equal(packagingManifest.schema,1);
 assert.equal(packagingManifest.scope,'approved-client1.12-pure-volume-packaging');
 assert.equal(packagingManifest.posterId,'poster-012');
 assert.equal(packagingManifest.containsFormula,false);
 assert.deepEqual(packagingManifest.components,['Jar','OuterCap','InnerLid']);
 assert.deepEqual(packagingManifest.additionalProducts,[{"posterId":"poster-071","file":"liaose-pump.glb","components":["BottleAssembly","Closure","PumpStem","PumpHead","LogoPrint"]},{"posterId":"poster-039","file":"poster-039.glb","components":["Body","Closure","InnerLid","LogoPrint"]},{"posterId":"poster-049","file":"poster-049.glb","components":["Body","Closure","PumpStem","Actuator","PaperLabel","LogoPrint"]},{"posterId":"poster-042","file":"poster-042.glb","components":["Body","Closure","StopperInsert","PaperLabel","LogoPrint"]},{"posterId":"poster-051","file":"poster-051.glb","components":["Body","Closure","PumpStem","Actuator","Cord","PaperLabel","LogoPrint"]}]);
 const packagingKinds={'beach-magic-packaging.glb':'model','liaose-pump.glb':'model','poster-039.glb':'model','poster-049.glb':'model','poster-042.glb':'model','poster-051.glb':'model','gsap.min.js':'animation','ScrollTrigger.min.js':'scroll-animation'};
 assert.deepEqual(packagingManifest.files.map(entry=>entry.name).sort(),Object.keys(packagingKinds).sort());
 const packagingDeclared=new Set(packagingManifest.files.map(entry=>entry.productionTarget));
 assert.equal(packagingDeclared.size,packagingManifest.files.length);
 for(const target of packagingDeclared)assert.ok(!declared.has(target),'new packaging assets cannot overwrite original posters');
 const actual=readdirSync(resolve(base,'public/assets'),{recursive:true}).filter(p=>statSync(resolve(base,'public/assets',p)).isFile()).map(p=>`assets/${p}`);
 assert.deepEqual([...declared,...packagingDeclared].sort(),actual.sort());
 for(const entry of manifest.files){
  assert.match(entry.source,/^server-reference\/public\/showroom\/assets\//);
  assert.ok(!entry.source.split('/').includes('..'));assert.ok(!entry.target.split('/').includes('..'));
  const source=resolve(root,entry.source),target=resolve(base,'public',entry.target);
  assert.ok(relative(resolve(base,'public'),target).startsWith('assets/'));
  const approvedPath=entry.source.replace('server-reference/public/showroom/','');
  const gate=approvedBundle.files[approvedPath];assert.ok(gate,`approved manifest entry: ${approvedPath}`);
  assert.equal(entry.sha256,gate.sha256,entry.target);assert.equal(entry.bytes,gate.bytes,entry.target);
  assert.equal(hash(source),gate.sha256,entry.source);assert.equal(hash(target),gate.sha256,entry.target);
  assert.equal(statSync(target).size,entry.bytes);
  assert.equal(assetPaths[`/${entry.target}`],`/showroom/${approvedPath}`);
 }
 for(const entry of packagingManifest.files){
  assert.equal(entry.kind,packagingKinds[entry.name]);
  assert.equal(entry.file,`packaging-assets/${entry.name}`);
  assert.equal(entry.productionTarget,`assets/packaging/${entry.name}`);
  const source=resolve(base,entry.file),target=resolve(base,'public',entry.productionTarget);
  assert.equal(hash(source),entry.sha256,entry.file);
  assert.equal(hash(target),entry.sha256,entry.productionTarget);
  assert.equal(statSync(source).size,entry.bytes);
  assert.equal(statSync(target).size,entry.bytes);
 }
 for(const p of posters)for(const field of ['image','thumb','original','smallImage','stripThumb'])assert.ok(declared.has(p[field].slice(1)));
});

test('bilingual searches are case-insensitive, trimmed and restricted to public titles',()=>{
 assert.ok(filterPosters(posters,{query:'  蓬松  '}).some(p=>p.id==='poster-051'));
 assert.deepEqual(filterPosters(posters,{query:'  WOODLAND  '}).map(p=>p.id),['poster-042']);
 assert.equal(filterPosters(posters,{query:'unlikely-absent-query-123'}).length,0);
 const bait={...posters[0],supplier:'secret-supplier-token',source:'private-cost-token'};
 assert.equal(filterPosters([bait],{query:'secret-supplier-token'}).length,0);
 assert.equal(filterPosters([bait],{query:'private-cost-token'}).length,0);
});

test('combined category, style, favorites and search filters preserve AND semantics',()=>{
 assert.deepEqual(filterPosters(posters,{category:'hair',style:'natural',favorites:['poster-051','poster-042'],query:'shampoo'}).map(p=>p.id),['poster-051']);
 assert.equal(filterPosters(posters,{category:'body',style:'natural',favorites:['poster-051']}).length,0);
 assert.deepEqual(filterPosters(posters,{favorites:[]}),[]);
 assert.equal(filterPosters(posters,{}).length,posters.length);
 const source=JSON.stringify(posters);filterPosters(posters,{category:'hair',query:'洗'});assert.equal(JSON.stringify(posters),source);
});

test('existing local favorites survive version changes and stale entries cannot create items',()=>{
 assert.equal(FAVORITES_KEY,previousFavoritesKey);
 const valid=new Set(posters.map(p=>p.id));
 const value=JSON.stringify(['poster-051','poster-051','../private','poster-removed',null,{},'poster-042']);
 let requestedKey;const saved=readFavorites({getItem(key){requestedKey=key;return value;}},valid);
 assert.equal(requestedKey,previousFavoritesKey);assert.deepEqual(saved,['poster-051','poster-042']);
 assert.deepEqual(filterPosters(posters,{favorites:saved}).map(p=>p.id).sort(),['poster-042','poster-051']);
 const original=['poster-051'];const added=toggleFavorite(original,'poster-042');
 assert.deepEqual(original,['poster-051']);assert.deepEqual(added,['poster-051','poster-042']);
 assert.deepEqual(toggleFavorite(added,'poster-051'),['poster-042']);
 assert.deepEqual(toggleFavorite(toggleFavorite([],'poster-051'),'poster-051'),[]);
});

test('unavailable or malformed local storage fails safely without losing current operations',()=>{
 const valid=new Set(posters.map(p=>p.id));
 for(const payload of ['{broken','null','{}','42','"poster-051"'])assert.deepEqual(readFavorites({getItem:()=>payload},valid),[]);
 assert.deepEqual(readFavorites(null,valid),[]);
 assert.deepEqual(readFavorites({getItem(){throw Error('blocked');}},valid),[]);
 assert.equal(persist(null,FAVORITES_KEY,['poster-051']),false);
 assert.equal(persist({setItem(){throw Error('quota');}},FAVORITES_KEY,['poster-051']),false);
 let write;assert.equal(persist({setItem(k,v){write=[k,v];}},FAVORITES_KEY,['poster-051']),true);
 assert.deepEqual(write,[FAVORITES_KEY,'["poster-051"]']);
});
