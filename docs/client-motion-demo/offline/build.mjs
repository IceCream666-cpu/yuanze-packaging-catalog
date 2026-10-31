import {build} from 'vite';
import fs from 'node:fs';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
import {createHash} from 'node:crypto';
import {execFileSync} from 'node:child_process';
import assert from 'node:assert/strict';
import {PACKAGING_PRODUCTS} from '../src/structure/packaging-products.js';

const here = path.dirname(fileURLToPath(import.meta.url));
const demo = path.dirname(here);
const repo = path.resolve(demo, '../..');
const publicRoot = path.join(repo, 'server-reference/public');
const showroom = path.join(publicRoot, 'showroom');
const output = path.resolve(process.argv[2] || path.join(repo, 'outputs/包材库作品集-20261031'));
const folder = path.join(output, 'YUANZE_Portfolio');
const sha = data => createHash('sha256').update(data).digest('hex');
const json = file => JSON.parse(fs.readFileSync(path.join(demo, 'src', file), 'utf8'));
const mappings = json('asset-paths.json');
const originals = [];

function publicFile(url) {
  assert(url.startsWith('/showroom/assets/'), `Unexpected asset: ${url}`);
  const file = path.resolve(publicRoot, '.' + url);
  assert(file.startsWith(showroom + path.sep), 'Asset escapes public directory');
  return file;
}

function dataURL(url, mime = 'image/webp') {
  return `data:${mime};base64,${fs.readFileSync(publicFile(url)).toString('base64')}`;
}

const posters = json('posters.json').map(item => {
  const source = publicFile(mappings[item.original]);
  const destination = `海报原图/${item.id}.webp`;
  const bytes = fs.readFileSync(source);
  originals.push({source, destination, bytes: bytes.length, sha256: sha(bytes)});
  return {...item,
    image: dataURL(mappings[item.image]),
    smallImage: dataURL(mappings[item.smallImage]),
    thumb: dataURL(mappings[item.smallImage]),
    stripThumb: dataURL(mappings[item.smallImage]),
    original: destination,
  };
});
const featured = json('featured.json').map(item => ({...item, image: dataURL(`/showroom/assets/featured/${item.id}-1024.webp`)}));
const modelBlocks = [];
const models = featured.map(item => {
  const product = PACKAGING_PRODUCTS[item.id];
  assert(product, `Missing model configuration: ${item.id}`);
  const bytes = fs.readFileSync(path.join(showroom, 'assets/packaging', product.file));
  assert.equal(bytes.readUInt32LE(0), 0x46546c67, 'Not a GLB');
  assert.equal(bytes.readUInt32LE(8), bytes.length, 'GLB length mismatch');
  modelBlocks.push(`<script type="application/octet-stream" id="model-${item.id}">${bytes.toString('base64')}</script>`);
  return {id: item.id, file: product.file, bytes: bytes.length, sha256: sha(bytes)};
});
assert.equal(posters.length, 61);
assert.equal(featured.length, 26);
assert.equal(new Set(models.map(item => item.file)).size, 26);
const data = {posters, featured, models, logo: dataURL('/showroom/assets/yuanze-mark.svg', 'image/svg+xml'), sourceRelease: 'client1.40'};

const result = await build({
  configFile: false,
  root: demo,
  base: './',
  publicDir: false,
  logLevel: 'warn',
  define: {'process.env.NODE_ENV': '"production"'},
  build: {
    write: false, minify: true, target: 'es2022', cssCodeSplit: false,
    lib: {entry: path.join(here, 'main.jsx'), name: 'YuanzePortfolio', formats: ['iife']},
    rollupOptions: {output: {inlineDynamicImports: true}},
  },
});
const emitted = Array.isArray(result) ? result.flatMap(item => item.output) : result.output;
const js = emitted.filter(item => item.type === 'chunk');
assert.equal(js.length, 1, 'Offline page must have one classic script');
assert.equal(js[0].imports.length, 0);
assert(!/\bimport\s*\(/.test(js[0].code), 'Offline bundle still contains a dynamic import');
const css = emitted.filter(item => item.fileName.endsWith('.css')).map(item => item.source.toString()).join('\n');
assert(css.length > 1000, 'Missing viewer stylesheet');
const script = code => `<script>${code.replaceAll('</script', '<\\/script')}</script>`;
const animation = ['gsap.min.js', 'ScrollTrigger.min.js'].map(file => fs.readFileSync(path.join(showroom, 'assets/packaging', file), 'utf8')).map(script).join('\n');
const html = `<!doctype html>
<html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<meta http-equiv="Content-Security-Policy" content="default-src 'none'; script-src 'unsafe-inline'; style-src 'unsafe-inline'; img-src data: blob: file:; connect-src blob:; base-uri 'none'; form-action 'none'">
<title>源泽包材库 · 交互作品集</title>
<style>${css.replaceAll('</style', '<\\/style')}</style></head>
<body><div id="root"><p style="padding:48px;font-family:sans-serif">正在打开源泽包材库作品集…</p></div>
<noscript>请使用开启 JavaScript 的桌面浏览器打开此文件，以查看交互式 3D 模型。</noscript>
<script type="application/json" id="portfolio-data">${JSON.stringify(data).replaceAll('<', '\\u003c')}</script>
${modelBlocks.join('\n')}
${animation}
${script(js[0].code)}
</body></html>`;
assert(Buffer.byteLength(html) < 150_000_000, 'Embedded page unexpectedly large');

fs.mkdirSync(path.join(folder, '海报原图'), {recursive: true});
fs.writeFileSync(path.join(folder, '打开作品.html'), html);
for (const item of originals) fs.copyFileSync(item.source, path.join(folder, item.destination));
const instructions = `源泽包材库 · 交互作品集\n2026.10.31｜正式展示版本 client1.40\n\n【打开方法】\n1. 先将整个 ZIP 解压到电脑本地文件夹。\n2. 双击“打开作品.html”，使用桌面浏览器查看。Windows 可用 Edge / Chrome；Mac 可用 Chrome / Edge / Safari。\n3. 无需登录、联网、安装插件或开发工具。请勿在邮件、网盘或压缩软件的内置预览中打开，内置预览通常不运行 3D。\n\n【核心交互】\n选择“3D 作品”中的产品进入模型。拖拽模型可旋转，滚动页面或拖动展开滑杆可查看结构；也可直接选择合拢、半展开或完全展开。右侧部件名称可聚焦部件，“回到正面”恢复视角，“原海报”查看对应设计。\n\n【作品内容】\n26 款可交互 3D 展示，包含正式模型、贴图、材质与原版分层动画。\n61 张展示海报，高清原图存于“海报原图”文件夹。\n页面中所有预览与 3D 模型已内嵌；请保留完整文件夹以查看高清海报；需要使用原图时，直接从“海报原图”文件夹复制即可。\n\n【兼容说明】\n需要支持 WebGL 2 的现代桌面浏览器，并启用图形/硬件加速。若某款模型不能显示，请尝试 Chrome 或 Edge，关闭其他占用显卡的页面后重开。\n本包在 macOS Ego Lite（Chromium）实际 file:// 路径及模拟断网环境验证；未进行 Windows 实机或 Safari 实测。\n3D 为包装结构与视觉展示，隐藏尺寸和装配细节仍以实物为准。\n\n【文件范围】\n离线展示副本，仅含作品与展示代码，不含账户、客户信息、后台数据库或服务器凭据。原网站未作更改。第三方许可见“第三方许可.txt”。\n`;
fs.writeFileSync(path.join(folder, '先读我.txt'), '\ufeff' + instructions);
const licensePaths = [
  ['Three.js / GLTFLoader', path.join(demo, 'src/structure/vendor/LICENSE')],
  ['React', path.join(demo, 'node_modules/react/LICENSE')],
  ['React DOM', path.join(demo, 'node_modules/react-dom/LICENSE')],
  ['Lucide React', path.join(demo, 'node_modules/lucide-react/LICENSE')],
];
const licenses = licensePaths.map(([name, file]) => `${name}\n${fs.readFileSync(file, 'utf8')}`).join('\n\n');
fs.writeFileSync(path.join(folder, '第三方许可.txt'), licenses + '\n\nGSAP / ScrollTrigger 3.13.0\nCopyright 2025 GreenSock. All rights reserved.\nSubject to https://gsap.com/standard-license\nThe original copyright and license notices are retained in the embedded scripts.\n');
const manifest = {created: '2026-10-31', sourceRelease: 'client1.40', sourceCommit: 'd736a61754579c03846835d2b8b9dc56d6916240', models, originals: originals.map(({source, ...item}) => item), htmlBytes: Buffer.byteLength(html), htmlSha256: sha(html)};
fs.writeFileSync(path.join(folder, '作品清单.json'), JSON.stringify(manifest, null, 2) + '\n');

const zip = path.join(output, '源泽包材库作品集_含26款交互3D_Windows与Mac.zip');
execFileSync('python3', ['-c', `import pathlib,sys,zipfile\np=pathlib.Path(sys.argv[1]); z=pathlib.Path(sys.argv[2]); files=sorted(p.rglob('*')); total=sum(f.stat().st_size for f in files if f.is_file()); assert total<300000000,total\nwith zipfile.ZipFile(z,'w',zipfile.ZIP_DEFLATED,compresslevel=6) as out:\n for f in files:\n  if f.is_file(): out.write(f,f.relative_to(p.parent))\nassert z.stat().st_size<300000000,z.stat().st_size\nwith zipfile.ZipFile(z) as out: assert out.testzip() is None\nprint('ZIP bytes:',z.stat().st_size,'Unpacked bytes:',total)`, folder, zip], {stdio: 'inherit'});
console.log(JSON.stringify({folder, zip, models: models.length, posters: posters.length, htmlBytes: Buffer.byteLength(html)}, null, 2));
