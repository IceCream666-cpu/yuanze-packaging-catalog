import test, {after} from 'node:test';
import assert from 'node:assert/strict';
import {copyFileSync, existsSync, mkdirSync, mkdtempSync, readFileSync, rmSync, writeFileSync} from 'node:fs';
import {execFileSync} from 'node:child_process';
import {tmpdir} from 'node:os';
import {resolve} from 'node:path';
import {fileURLToPath} from 'node:url';
import {JSDOM} from 'jsdom';
import {PACKAGING_PRODUCTS} from '../src/structure/packaging-products.js';

const base = fileURLToPath(new URL('../', import.meta.url));
const read = path => readFileSync(resolve(base, path), 'utf8');
const featured = JSON.parse(read('src/featured.json'));
const posters = Object.fromEntries(JSON.parse(read('src/posters.json')).map(item => [item.id, item]));
const status = JSON.parse(read('model-review-status.json'));
const script = read('public/model-review.js');
const css = read('public/model-review.css');
const ready = state => state === 'complete' || state === 'published';

// Exercise the actual generator without rewriting the developer's active preview.
const temporary = mkdtempSync(resolve(tmpdir(), 'model-review-test-'));
after(() => rmSync(temporary, {recursive: true, force: true}));
const fixture = resolve(temporary, 'docs/client-motion-demo');
mkdirSync(resolve(temporary, 'scripts'), {recursive: true});
mkdirSync(resolve(fixture, 'src'), {recursive: true});
mkdirSync(resolve(fixture, 'public'), {recursive: true});
copyFileSync(resolve(base, '../../scripts/build_model_review.py'), resolve(temporary, 'scripts/build_model_review.py'));
for (const name of ['featured.json', 'posters.json']) copyFileSync(resolve(base, 'src', name), resolve(fixture, 'src', name));
function generate(states) {
  writeFileSync(resolve(fixture, 'model-review-status.json'), JSON.stringify(states));
  execFileSync('python3', [resolve(temporary, 'scripts/build_model_review.py')], {encoding: 'utf8'});
  return readFileSync(resolve(fixture, 'public/model-review.html'), 'utf8');
}
const currentPage = generate(status);
const mixedStatus = {
  [featured[0].id]: {state: 'published', components: ['Body', 'LogoPrint'], screenshots: {closed: '/review/a-closed.png', open: '/review/a-open.png'}},
  [featured[1].id]: {state: 'complete', components: ['Body', 'PaperLabel', 'LogoPrint'], screenshots: {closed: '/review/b-closed.png', open: '/review/b-open.png'}},
  [featured[2].id]: {state: 'working'},
};
const mixedPage = generate(mixedStatus);
function harness(t, html = currentPage) {
  const dom = new JSDOM(html, {url: 'http://127.0.0.1:8784/model-review.html', runScripts: 'outside-only'});
  t.after(() => dom.window.close());
  const {document} = dom.window;
  const style = document.createElement('style');
  style.textContent = css;
  document.head.append(style);
  dom.window.eval(script);
  const cards = [...document.querySelectorAll('article')];
  const search = value => {
    const input = document.querySelector('#search');
    input.value = value;
    input.dispatchEvent(new dom.window.Event('input', {bubbles: true}));
  };
  const choose = view => document.querySelector(`[data-view="${view}"]`).click();
  return {dom, document, cards, search, choose};
}
function assertLocalAsset(route) {
  assert.match(route, /^\/(?!\/)/, `Expected a local preview asset: ${route}`);
  assert.ok(existsSync(resolve(base, 'public', route.slice(1))), `Missing preview asset ${route}`);
}

test('review generator preserves all current featured identities and their original poster links', t => {
  const {document, cards} = harness(t);
  assert.equal(featured.length, 26);
  assert.equal(new Set(featured.map(item => item.id)).size, featured.length);
  assert.equal(cards.length, featured.length);
  assert.equal(document.querySelector('section').getAttribute('aria-label'), `${featured.length}款精选包材`);
  cards.forEach((card, index) => {
    const item = featured[index], poster = posters[item.id];
    assert.ok(poster, `Missing poster record ${item.id}`);
    assert.equal(card.querySelector('h2').textContent, item.name);
    assert.equal(card.querySelector('p').textContent, item.kind.zh);
    assert.equal(card.dataset.name, `${item.name} ${item.kind.zh}`);
    const original = [...card.querySelectorAll('a')].find(link => link.textContent === '原海报');
    assert.equal(original?.getAttribute('href'), poster.original);
    assertLocalAsset(poster.original);
    assertLocalAsset(poster.image);
    assertLocalAsset(poster.thumb);
    assert.equal(original.target, '_blank');
    assert.ok(original.relList.contains('noopener'));
  });
});

test('ready count and model links follow current completion state without treating working models as ready', t => {
  const {document, cards} = harness(t);
  assert.equal(Number(document.querySelector('.progress strong').textContent), featured.filter(item => ready(status[item.id]?.state)).length);
  cards.forEach((card, index) => {
    const id = featured[index].id, record = status[id] ?? {state: 'working'};
    assert.equal(card.dataset.state, record.state);
    const link = card.querySelector('a[href^="/?model="]');
    if (ready(record.state)) {
      assert.equal(link?.getAttribute('href'), `/?model=${id}`);
      assert.equal(link.target, '_blank');
      assert.ok(link.relList.contains('noopener'));
      assert.ok(PACKAGING_PRODUCTS[id]?.file, `${id} has no viewer model configuration`);
      const bytes = readFileSync(resolve(base, 'packaging-assets', PACKAGING_PRODUCTS[id].file));
      assert.equal(bytes.subarray(0, 4).toString(), 'glTF', `${id} model link has no GLB asset`);
      assert.equal(bytes.readUInt32LE(4), 2);
      assert.equal(card.querySelector('.pending'), null);
    } else {
      assert.equal(link, null);
      assert.ok(card.querySelector('.pending'));
    }
    for (const route of Object.values(record.screenshots ?? {})) assertLocalAsset(route);
  });
});

test('published, local complete and missing status remain distinct with safe poster fallbacks', t => {
  const {document, cards} = harness(t, mixedPage);
  assert.equal(document.querySelector('.progress strong').textContent, '2');
  assert.equal(cards[0].querySelector('.status').textContent, '已上线');
  assert.equal(cards[1].querySelector('.status').textContent, '已完成 · 本地预览');
  for (const card of cards.slice(2)) {
    assert.equal(card.dataset.state, 'working');
    assert.equal(card.querySelector('.status').textContent, '逐款制作中');
    assert.equal(card.querySelector('a[href^="/?model="]'), null);
  }
  cards.forEach((card, index) => {
    const id = featured[index].id, photos = mixedStatus[id]?.screenshots ?? {}, image = card.querySelector('img');
    assert.equal(image.getAttribute('src'), photos.closed ?? posters[id].thumb);
    assert.equal(image.dataset.closed, photos.closed ?? posters[id].thumb);
    assert.equal(image.dataset.open, photos.open ?? posters[id].thumb);
    assert.equal(image.dataset.poster, posters[id].image);
  });
});

test('search matches English names case-insensitively, trims whitespace and also matches Chinese categories', t => {
  const {cards, search, document} = harness(t);
  for (const query of ['  b5 sErUm  ', '身体护理', 'Oil']) {
    search(query);
    const normalized = query.trim().toLocaleLowerCase();
    const expected = featured.filter(item => `${item.name} ${item.kind.zh}`.toLocaleLowerCase().includes(normalized));
    assert.ok(expected.length > 0 && expected.length < featured.length);
    assert.deepEqual(cards.filter(card => !card.hidden).map(card => card.querySelector('h2').textContent), expected.map(item => item.name));
    assert.equal(document.querySelector('#empty').hidden, true);
  }
});

test('an unmatched query exposes the empty message and clearing restores every card', t => {
  const {dom, document, cards, search} = harness(t);
  search('no-such-packaging-不匹配');
  assert.ok(cards.every(card => card.hidden));
  assert.ok(cards.every(card => dom.window.getComputedStyle(card).display === 'none'));
  assert.equal(document.querySelector('#empty').hidden, false);
  assert.notEqual(dom.window.getComputedStyle(document.querySelector('#empty')).display, 'none');
  for (const cleared of ['', '   ']) {
    search(cleared);
    assert.ok(cards.every(card => !card.hidden));
    assert.equal(document.querySelector('#empty').hidden, true);
  }
});

test('closed, exploded and original views synchronize all card images and the pressed button', t => {
  const {document, cards, choose} = harness(t, mixedPage);
  const buttons = [...document.querySelectorAll('[data-view]')];
  const links = [...document.querySelectorAll('a')].map(link => link.href);
  const check = view => {
    assert.equal(buttons.filter(button => button.getAttribute('aria-pressed') === 'true').length, 1);
    assert.equal(document.querySelector('[aria-pressed="true"]').dataset.view, view);
    for (const card of cards) {
      const image = card.querySelector('img');
      assert.equal(image.getAttribute('src'), image.dataset[view]);
    }
    assert.deepEqual([...document.querySelectorAll('a')].map(link => link.href), links);
  };
  check('closed');
  for (const view of ['open', 'poster', 'closed', 'open']) {
    choose(view);
    check(view);
    const description = {closed: '模型合拢预览', open: '模型展开预览', poster: '原海报'}[view];
    cards.forEach(card => assert.equal(card.querySelector('img').alt, `${card.querySelector('h2').textContent} ${description}`));
  }
});

test('view changes also update filtered cards so clearing search never restores a stale image mode', t => {
  const {cards, search, choose, document} = harness(t, mixedPage);
  search('B5 Serum');
  assert.ok(cards.some(card => card.hidden));
  choose('open');
  search('');
  assert.ok(cards.every(card => !card.hidden && card.querySelector('img').getAttribute('src') === card.querySelector('img').dataset.open));
  search('no-such-packaging');
  choose('poster');
  assert.equal(document.querySelector('#empty').hidden, false);
  search('');
  assert.ok(cards.every(card => !card.hidden && card.querySelector('img').getAttribute('src') === card.querySelector('img').dataset.poster));
  assert.equal(document.querySelector('#empty').hidden, true);
});
