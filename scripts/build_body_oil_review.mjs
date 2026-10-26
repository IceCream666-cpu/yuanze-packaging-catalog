import {createRequire} from 'node:module';
import {fileURLToPath} from 'node:url';
import {resolve, dirname} from 'node:path';
import {readFile, writeFile, copyFile, mkdir} from 'node:fs/promises';
import {createHash} from 'node:crypto';

const root = resolve(dirname(fileURLToPath(import.meta.url)), '..');
const client = resolve(root, 'docs/client-motion-demo');
const source = resolve(client, 'review-source/body-oil-collection');
const output = resolve(client, 'public/review/body-oil-collection');
const preview = resolve(client, 'dist/review/body-oil-collection');
const require = createRequire(resolve(client, 'package.json'));
const {build} = createRequire(require.resolve('tsx/package.json'))('esbuild');
const config = JSON.parse(await readFile(resolve(source, 'review-config.json'), 'utf8'));
if (config.product?.file !== 'body-oil-collection.glb' || !Array.isArray(config.product.parts) || !config.design?.name) throw new Error('Invalid Body Oil review configuration');
const expectedParts = {closure:'Closure', liner:'InnerSeal', body:'Body', label:'PaperLabel', print:'LogoPrint', name:'ProductPrint'};
if (JSON.stringify(config.product.parts.map(part => part.key).sort()) !== JSON.stringify(Object.keys(expectedParts).sort())
    || config.product.parts.some(part => part.node !== expectedParts[part.key])) throw new Error('Body Oil preview requires the six reviewed empty-bottle component groups');

// The model builder owns these files; this build only packages this review directory.
const model = await readFile(resolve(output, config.product.file));
const reference = await readFile(resolve(output, 'reference.png'));
if (model.toString('ascii', 0, 4) !== 'glTF' || model.readUInt32LE(8) !== model.length) throw new Error('Invalid Body Oil GLB');
if (!reference.subarray(0, 8).equals(Buffer.from([137,80,78,71,13,10,26,10]))) throw new Error('Reference must be a PNG');
await mkdir(output, {recursive:true});
await build({entryPoints:[resolve(source, 'main.js')], outfile:resolve(output, 'main.js'), bundle:true,
  format:'esm', platform:'browser', target:'es2022', minify:true, sourcemap:false,
  define:{'import.meta.env.BASE_URL':'"/"'}});
for (const name of ['index.html', 'style.css', 'review-config.json']) await copyFile(resolve(source, name), resolve(output, name));
const names = ['index.html', 'style.css', 'main.js', 'review-config.json', config.product.file, 'reference.png'];
const files = [];
for (const file of names) {
  const bytes = await readFile(resolve(output, file));
  files.push({file, bytes:bytes.length, sha256:createHash('sha256').update(bytes).digest('hex')});
}
await writeFile(resolve(output, 'review-build.json'), JSON.stringify({scope:'local-review-only', publicationApproved:false,
  model:'Body Oil Collection', files}, null, 2) + '\n');
await mkdir(preview, {recursive:true});
for (const name of [...names, 'review-build.json']) await copyFile(resolve(output, name), resolve(preview, name));
console.log(JSON.stringify({url:'http://127.0.0.1:8784/review/body-oil-collection/', scope:'local-review-only', files}, null, 2));
