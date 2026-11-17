import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {createRequire} from 'node:module';
import {JSDOM} from 'jsdom';
import React, {act} from 'react';
import {createRoot} from 'react-dom/client';

const require = createRequire(import.meta.url);
const {transformSync} = createRequire(require.resolve('tsx/package.json'))('esbuild');
const entries = [
  ['amber-ginger', '067', 'poster-067-v2.glb'],
  ['bath-trio', '080', 'poster-080-v2.glb'],
  ['beach-magic-quality', '012', 'poster-012-v2.glb'],
  ['daily-emulsion-quality', '072', 'poster-072-v2.glb'],
  ['daily-hair-ritual', '085', 'poster-085-v2.glb'],
  ['daily-hair-quality', '085', 'poster-085-v3.glb'],
  ['essence-water', '068', 'poster-068-v3.glb'],
  ['hand-gel', '081', 'poster-081-v1.glb'],
  ['moisture-quality', '049', 'poster-049-v2.glb'],
  ['scalp-essence', '086', 'poster-086-v1.glb'],
  ['sculptural-pump', '071', 'poster-071-v2.glb'],
  ['soap-duo', '082', 'poster-082-v1.glb'],
  ['soap-clean-quality', '082', 'poster-082-v2.glb'],
  ['soft-body-duo', '084', 'poster-084-v2.glb'],
];

function load(name, mocks) {
  const url = new URL(`../src/${name}`, import.meta.url);
  const source = readFileSync(url, 'utf8').replace(/^import ['"][^'"]+\.css['"];?\s*$/gm, '');
  const {code} = transformSync(source, {loader: 'jsx', format: 'cjs', jsx: 'transform'});
  const module = {exports: {}}, localRequire = createRequire(url);
  new Function('require', 'module', 'exports', code)(id => {
    if (id in mocks) return mocks[id];
    if (/\.(?:glb\?url|webp|png)$/.test(id)) return new URL(id, url).href;
    return localRequire(id);
  }, module, module.exports);
  return module.exports;
}

test('all local review entries retain their products, assets, favorite keys and poster controls', async () => {
  const published = JSON.parse(readFileSync(new URL('../src/structure/collection-products.json', import.meta.url)));
  const publishedBefore = JSON.stringify(published);
  assert.equal(published['poster-072'].file, 'poster-072.glb');
  assert.equal(published['poster-086'], undefined);
  for (const [name, number, filename] of entries) {
    const dom = new JSDOM('<div id="root"></div>', {url: 'http://localhost/'});
    const previous = Object.fromEntries(['window', 'document', 'sessionStorage', 'IS_REACT_ACT_ENVIRONMENT'].map(key => [key, globalThis[key]]));
    Object.assign(globalThis, {window: dom.window, document: dom.window.document,
      sessionStorage: dom.window.sessionStorage, IS_REACT_ACT_ENVIRONMENT: true});
    dom.window.HTMLDialogElement.prototype.showModal = function() {this.open = true;};
    dom.window.HTMLDialogElement.prototype.close = function() {this.open = false;};
    sessionStorage.setItem(`${name}-saved`, 'yes');
    sessionStorage.setItem('unrelated-saved', 'yes');
    const products = {...published}; let root, received;
    function Detail(props) {
      received = props;
      return <><button onClick={props.onFavorite}>收藏</button><button onClick={props.onOriginal}>原海报</button></>;
    }
    try {
      const shared = load('local-review.jsx', {
        'react-dom/client': {createRoot(node) {return root = createRoot(node);}},
        './structure/PackagingDetailLoader.jsx': Detail,
        './structure/packaging-products.js': {PACKAGING_PRODUCTS: products},
      });
      await act(async () => load(`${name}-review.jsx`, {'./local-review.jsx': shared}));
      assert.equal(received.item.id, `poster-${number}`, name);
      assert.equal(products[received.item.id].file, filename, name);
      assert.ok(received.modelUrl.endsWith(filename + '?url'), name);
      assert.equal(received.saved, true, name);
      const poster = document.querySelector('dialog'), image = poster.querySelector('img');
      assert.equal(image.getAttribute('src'), received.item.image, name);
      assert.ok(image.alt.length > 10, name);
      assert.equal(poster.getAttribute('aria-label'), `${received.item.title.en} 原海报`, name);
      const click = async label => act(async () => [...document.querySelectorAll('button')].find(b => b.textContent === label).click());
      await click('原海报'); assert.equal(poster.open, true, name);
      await click('返回模型'); assert.equal(poster.open, false, name);
      await click('收藏'); assert.equal(received.saved, false, name);
      assert.equal(sessionStorage.getItem(`${name}-saved`), 'no', name);
      assert.equal(sessionStorage.getItem('unrelated-saved'), 'yes', name);
    } finally {
      if (root) await act(async () => root.unmount());
      dom.window.close(); Object.assign(globalThis, previous);
    }
  }
  assert.equal(JSON.stringify(published), publishedBefore, 'local registrations must not alter the published registry');
});
