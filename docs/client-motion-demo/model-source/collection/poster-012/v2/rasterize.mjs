import sharp from '/Users/icecream/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/sharp/dist/index.mjs';
import {fileURLToPath} from 'node:url';
const here=fileURLToPath(new URL('.',import.meta.url));
for (const name of ['paper','logo','product']) {
  await sharp(here+name+'.svg').resize(2048,1280).png({compressionLevel:9}).toFile(here+name+'.png');
}
