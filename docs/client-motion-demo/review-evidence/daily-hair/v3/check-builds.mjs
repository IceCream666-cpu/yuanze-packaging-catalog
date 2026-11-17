import assert from 'node:assert/strict';
import {readFileSync,readdirSync,writeFileSync} from 'node:fs';
import {resolve,relative} from 'node:path';
import {fileURLToPath} from 'node:url';
import {createHash} from 'node:crypto';
import {build} from 'vite';

const evidence=fileURLToPath(new URL('.',import.meta.url));
const client=resolve(evidence,'../../..'),project=resolve(client,'../..');
const sha=file=>createHash('sha256').update(readFileSync(file)).digest('hex');
const baseline=JSON.parse(readFileSync(resolve(evidence,'frozen-client163-before.json')));
const inventory=(base,dir=base)=>Object.fromEntries(readdirSync(dir,{withFileTypes:true}).flatMap(item=>{
  const file=resolve(dir,item.name);assert.ok(!item.isSymbolicLink(),file);
  return item.isDirectory()?Object.entries(inventory(base,file)):[[relative(base,file),sha(file)]];
}));
function checkFrozen(){
  assert.deepEqual(inventory(resolve(project,'server-reference/public/showroom')),baseline.showroom);
  assert.deepEqual(inventory(resolve(client,'release')),baseline.release);
  assert.equal(sha(resolve(client,'src/structure/collection-products.json')),baseline.registry);
  assert.equal(sha(resolve(client,'packaging-manifest.json')),baseline.packagingManifest);
}
checkFrozen();
const outDirs=['/private/tmp/daily-hair085-showroom-check','/private/tmp/daily-hair085-preview-check'];
await build({root:client,configFile:resolve(client,'vite.config.js'),mode:'showroom',publicDir:false,build:{outDir:outDirs[0],copyPublicDir:false,emptyOutDir:true}});
await build({root:client,configFile:resolve(client,'vite.config.js'),mode:'preview',publicDir:false,build:{outDir:outDirs[1],copyPublicDir:false,emptyOutDir:true,rollupOptions:{input:resolve(client,'daily-hair-quality.html')}}});
checkFrozen();
const modelHash=sha(resolve(client,'packaging-assets/poster-085-v3.glb'));
const bundled=Object.entries(inventory(outDirs[1])).filter(([name])=>name.endsWith('.glb'));
assert.equal(bundled.length,1);assert.equal(bundled[0][1],modelHash);
const report={passed:true,outDirs,publicDir:false,copyPublicDir:false,modelSha256:modelHash,bundledModelPath:resolve(outDirs[1],bundled[0][0]),frozenManifestSha256:baseline.showroom['bundle-manifest.json'],all514ResourcesAndManifestUnchanged:true,all8ReleaseFilesUnchanged:true,registryAndPackagingManifestUnchanged:true,productionBuildOverwritten:false};
writeFileSync(resolve(evidence,'build-checks.json'),JSON.stringify(report,null,2)+'\n');
console.log(JSON.stringify(report));
