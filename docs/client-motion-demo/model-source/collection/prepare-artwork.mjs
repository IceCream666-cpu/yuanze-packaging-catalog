// Rasterize editable vector print plates; never bake a second logo into the fixed label.
import fs from 'node:fs/promises';
import sharp from '/Users/icecream/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/sharp/dist/index.mjs';
import {fileURLToPath} from 'node:url';
const base=fileURLToPath(new URL('.',import.meta.url));
const items=JSON.parse(await fs.readFile(base+'products.json','utf8'));
const wordmark=await fs.readFile(new URL('../../../long-neck-3d/assets/liaose.svg',import.meta.url),'utf8');
const inner=wordmark.replace(/^[\s\S]*?<svg[^>]*>/,'').replace(/<\/svg>\s*$/,'');
const escape=s=>s.replaceAll('&','&amp;').replaceAll('<','&lt;');
for(const p of items.filter(p=>!process.argv[2] || p.id===process.argv[2])){
 const dir=base+p.id;await fs.mkdir(dir,{recursive:true});
 const W=Math.round(900*p.w*1.5/(p.h*.62));
 const logo=`<svg x="${W*.15}" y="130" width="${W*.70}" height="${W*.70/2.72}" viewBox="0 0 340 125">${inner.replace(/fill="[^"]*"/g,`fill="${p.ink}"`)}</svg>`;
 const bg=p.label?`<rect x="16" y="16" width="${W-32}" height="868" rx="28" fill="${p.label}"/>`:'';
 const lines=p.lines.map((line,i)=>`<text x="${W/2}" y="${Math.max(450,130+W*.70/2.72+55)+i*100}" text-anchor="middle" font-family="Helvetica Neue,Arial,sans-serif" font-size="${Math.min(48,(W-80)/line.length*1.7)}" fill="${p.ink}" letter-spacing="1">${escape(line)}</text>`).join('');
 for(const [kind,content] of [['label',bg+lines],['print',logo]]){
  const pdrnContent=kind==='print'
   ? `<svg x="105" y="0" width="790" height="290" viewBox="0 0 340 125">${inner.replace(/fill="[^"]*"/g,'fill="#080b09"')}</svg>`
   : '<text x="500" y="365" text-anchor="middle" font-family="Times New Roman,Times,serif" font-size="57" fill="#080b09">PDRN CAPSULE CREAM</text><text x="500" y="453" text-anchor="middle" font-family="Times New Roman,Times,serif" font-size="45" fill="#080b09">DAILY SKINCARE</text><path d="M441 515H559" stroke="#080b09" stroke-width="6"/>';
  const moistureContent=kind==='label'
   ? '<rect x="3" y="3" width="994" height="1154" rx="420" fill="#f4f0e5"/>'
   : `<svg x="40" y="160" width="920" height="360" viewBox="0 0 340 125">${inner.replace(/fill="[^"]*"/g,'fill="#080907"')}</svg><path d="M128 646H872M128 855H872" stroke="#080907" stroke-width="3"/><text x="500" y="780" text-anchor="middle" font-family="Helvetica Neue,Arial,sans-serif" font-size="61" letter-spacing="4" textLength="744" lengthAdjust="spacingAndGlyphs" fill="#080907">WHIPPED MOISTURE</text><text x="500" y="989" text-anchor="middle" font-family="Helvetica Neue,Arial,sans-serif" font-size="64" letter-spacing="29" textLength="610" lengthAdjust="spacingAndGlyphs" fill="#080907">SHAMPOO</text>`;
  const svg=p.id==='poster-039'
   ? `<svg xmlns="http://www.w3.org/2000/svg" xmlns:ns0="http://www.w3.org/2000/svg" width="1600" height="992" viewBox="0 0 1000 620">${pdrnContent}</svg>`
   : p.id==='poster-049'
   ? `<svg xmlns="http://www.w3.org/2000/svg" xmlns:ns0="http://www.w3.org/2000/svg" width="1500" height="1740" viewBox="0 0 1000 1160">${moistureContent}</svg>`
   : `<svg xmlns="http://www.w3.org/2000/svg" xmlns:ns0="http://www.w3.org/2000/svg" width="${W}" height="900" viewBox="0 0 ${W} 900">${content}</svg>`;
  await fs.writeFile(dir+'/'+kind+'.svg',svg);await sharp(Buffer.from(svg)).png().toFile(dir+'/'+kind+'.png');
 }
}
