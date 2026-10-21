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
const assetPaths=json(resolve(base,'src/asset-paths.json'));
const approvedBundle=json(resolve(root,'server-reference/public/showroom/bundle-manifest.json'));
const raw=readFileSync(resolve(root,'server-reference/public/showroom/product-posters.js'),'utf8');
const approved=JSON.parse(raw.slice(raw.indexOf('{')).trim().replace(/;$/,''));
const hash=path=>createHash('sha256').update(readFileSync(path)).digest('hex');

test('client1.1 retains exactly the 38 approved poster identities and public facts',()=>{
 assert.equal(posters.length,38);
 assert.equal(new Set(posters.map(p=>p.id)).size,38);
 assert.deepEqual(posters.map(p=>p.id).sort(),approved.items.map(p=>p.id).sort());
 assert.deepEqual(posters.map(p=>p.id).sort(),previous.map(p=>p.id).sort());
 for(const p of posters){
  assert.deepEqual(Object.keys(p).sort(),['id','title','category','style','image','thumb','original','width','height'].sort());
  assert.deepEqual(Object.keys(p.title).sort(),['en','zh']);
  const source=approved.items.find(item=>item.id===p.id);
  assert.deepEqual(p.title,source.title);assert.equal(p.category,source.category);
  assert.equal(p.width,source.width);assert.equal(p.height,source.height);
  for(const field of ['image','thumb','original'])assert.match(p[field],/^\/assets\/poster-\d+(?:-thumb|-original)?\.webp$/);
 }
});

test('all copied images and logo match the approved deployment manifest and bytes',()=>{
 assert.equal(manifest.count,38);assert.equal(manifest.files.length,115);
 assert.equal(new Set(manifest.files.map(f=>f.target)).size,115);
 const declared=new Set(manifest.files.map(f=>f.target));
 const actual=readdirSync(resolve(base,'public/assets'),{recursive:true}).filter(p=>statSync(resolve(base,'public/assets',p)).isFile()).map(p=>`assets/${p}`);
 assert.deepEqual([...declared].sort(),actual.sort());
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
 for(const p of posters)for(const field of ['image','thumb','original'])assert.ok(declared.has(p[field].slice(1)));
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
 assert.equal(filterPosters(posters,{}).length,38);
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
