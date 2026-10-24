// Rasterize editable vector print plates; never bake a second logo into the fixed label.
import fs from 'node:fs/promises';
import sharp from '/Users/icecream/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/sharp/dist/index.mjs';
import {fileURLToPath} from 'node:url';
const base=fileURLToPath(new URL('.',import.meta.url));
const items=JSON.parse(await fs.readFile(base+'products.json','utf8'));
const wordmark=await fs.readFile(new URL('../../../long-neck-3d/assets/liaose.svg',import.meta.url),'utf8');
const inner=wordmark.replace(/^[\s\S]*?<svg[^>]*>/,'').replace(/<\/svg>\s*$/,'');
const escape=s=>s.replaceAll('&','&amp;').replaceAll('<','&lt;');
for(const p of items){
 const dir=base+p.id;await fs.mkdir(dir,{recursive:true});
 const W=Math.round(900*p.w*1.5/(p.h*.62));
 const logo=`<svg x="${W*.15}" y="130" width="${W*.70}" height="${W*.70/2.72}" viewBox="0 0 340 125">${inner.replace(/fill="[^"]*"/g,`fill="${p.ink}"`)}</svg>`;
 const bg=p.label?`<rect x="16" y="16" width="${W-32}" height="868" rx="28" fill="${p.label}"/>`:'';
 const lines=p.lines.map((line,i)=>`<text x="${W/2}" y="${Math.max(450,130+W*.70/2.72+55)+i*100}" text-anchor="middle" font-family="Helvetica Neue,Arial,sans-serif" font-size="${Math.min(48,(W-80)/line.length*1.7)}" fill="${p.ink}" letter-spacing="1">${escape(line)}</text>`).join('');
 for(const [kind,content] of [['label',bg+lines],['print',logo]]){
  const svg=`<svg xmlns="http://www.w3.org/2000/svg" xmlns:ns0="http://www.w3.org/2000/svg" width="${W}" height="900" viewBox="0 0 ${W} 900">${content}</svg>`;
  await fs.writeFile(dir+'/'+kind+'.svg',svg);await sharp(Buffer.from(svg)).png().toFile(dir+'/'+kind+'.png');
 }
}
