const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const {JSDOM, VirtualConsole} = require('jsdom');
const {evaluateBrowserModule} = require('./module-loader.cjs');

const root = path.resolve(__dirname, '../../server-reference/public');
const clone = value => JSON.parse(JSON.stringify(value));
const checks = [];
const family = [30, 50].map((capacityMl, index) => ({
  id: `workspace-spec-${index}`, productCode: `YZ-BC-80000${index + 1}`, version: 8 + index,
  kind: 'package', name: `独立规格瓶${capacityMl}ml`, capacityMl, specificationRaw: `${capacityMl}mL`,
  materials: ['玻璃'], bodyAreas: ['head'], uses: ['头皮精华'], quoteRaw: `独立报价${index}`,
  source: {workbook: 'synthetic-only.xlsx', sheet: 'fixture', row: index + 1},
  images: [{path: `media/workspace-spec-${index}.jpg`, role: 'product', imageScope: 'single_product'}],
}));
const reviewedGroup = {id: 'workspace-family', name: '独立规格瓶', recordIds: family.map(record => record.id),
  specs: family.map(record => ({label: `${record.capacityMl} mL`, recordIds: [record.id]}))};
const fixtures = [
  ...Array.from({length: 45}, (_, index) => ({
    id: `workspace-${index}`, productCode: `YZ-BC-${String(1000 + index).padStart(6, '0')}`,
    version: index + 2, kind: 'package', name: `保留筛选瓶${index}`, materials: ['PET'],
    capacityMl: 100, specificationRaw: '100 mL', bodyAreas: ['face'], uses: ['面部精华'],
    quoteRaw: `虚构报价${index}`, supplierRaw: '合成测试供应商', images: [],
  })),
  ...Array.from({length: 3}, (_, index) => ({id: `workspace-body-${index}`,
    productCode: `YZ-BC-${String(2000 + index).padStart(6, '0')}`, version: 1, kind: 'package',
    name: `身体护理瓶${index}`, materials: ['PP'], bodyAreas: ['body'], uses: ['沐浴露'], images: []})),
  ...family,
];

async function until(condition, label) {
  const deadline = Date.now() + 5000;
  while (!condition()) {
    if (Date.now() > deadline) throw Error(`Timeout: ${label}`);
    await new Promise(resolve => setTimeout(resolve, 5));
  }
}

async function open({role = 'admin', hash = '', paging = false} = {}) {
  const errors = [], calls = [], records = new Map(fixtures.map(record => [record.id, clone(record)]));
  let favorites = ['workspace-0'], nextId = 1, saveFailure = 0;
  let liveSession = {role, username: `fixture-${role}`, csrf: 'workspace-csrf', authenticated: true};
  const virtualConsole = new VirtualConsole();
  virtualConsole.on('jsdomError', error => errors.push(error.message));
  const dom = new JSDOM(fs.readFileSync(path.join(root, 'index.html'), 'utf8'), {
    url: `https://catalog.test/${role === 'admin' ? 'admin' : ''}${hash}`,
    runScripts: 'outside-only', pretendToBeVisual: true, virtualConsole,
  });
  const w = dom.window, d = w.document;
  w.matchMedia = () => ({matches: true, addEventListener() {}});
  w.scrollTo = () => {};
  w.HTMLElement.prototype.scrollIntoView = function () {};
  w.HTMLDialogElement.prototype.showModal = function () {this.open = true;};
  w.HTMLDialogElement.prototype.close = function () {this.open = false;this.dispatchEvent(new w.Event('close'));};
  w.confirm = () => true;
  const queryEngine=paging?(await evaluateBrowserModule(dom,path.join(root,'catalog-query.js'))).namespace:null;
  w.fetch = async (url, options = {}) => {
    const method = options.method || 'GET';
    const body = options.body ? JSON.parse(options.body) : undefined;
    calls.push({url: String(url), method, body});
    const respond = (value, status = 200) => new Response(JSON.stringify(value), {
      status, headers: {'Content-Type': 'application/json'},
    });
    if (url === '/api/session') return liveSession.authenticated
      ? respond({role: liveSession.role, username: liveSession.username, csrf: liveSession.csrf,catalogPaging:paging})
      : respond({error: '登录已过期，请重新登录。'}, 401);
    if (method === 'POST') {
      if (!liveSession.authenticated) return respond({error: '登录已过期，请重新登录。'}, 401);
      assert.equal(new Headers(options.headers).get('X-CSRF-Token'), liveSession.csrf, 'Write uses the current session CSRF token');
    }
    if(paging&&String(url).startsWith('/api/catalog/')){
      const parsed=new URL(url,'https://catalog.test'),params=parsed.searchParams;
      const index=queryEngine.prepareRecords({records:[...records.values()]},[reviewedGroup]);
      if(parsed.pathname==='/api/catalog/records'){
        const ids=new Set(params.getAll('id').flatMap(id=>index.productGroupIndex.get(id)?.records.map(r=>r.id)||[id]));
        return respond({records:[...records.values()].filter(r=>ids.has(r.id))});
      }
      if(parsed.pathname==='/api/catalog/page')return respond({...queryEngine.queryPage(index,{q:params.get('q'),page:+params.get('page'),pageSize:+params.get('pageSize'),filters:Object.fromEntries(queryEngine.facetKeys.map(k=>[k,params.getAll(k)])),favorites:params.get('favorites')==='1',favoriteIds:favorites}),facets:queryEngine.catalogFacets(index.records),settings:{showBusinessDemo:false}});
    }
    if (url === '/api/catalog') return respond({records: [...records.values()], settings: {showBusinessDemo: false}});
    if (url === '/api/preferences') {
      if (method === 'POST') {favorites = [...body.favorites];return respond({ok: true});}
      return respond({favorites});
    }
    if (url === '/api/image-search/status') return respond({available: false});
    if (String(url).startsWith('/api/admin/')) {
      if (liveSession.role !== 'admin') return respond({error: '仅管理员可以维护资料'}, 403);
      const parsed = new URL(url, 'https://catalog.test');
      if (parsed.pathname === '/api/admin/records' && method === 'GET') {
        assert.equal(parsed.searchParams.getAll('id').length, 1, 'Editor reads exactly one record');
        const item = records.get(parsed.searchParams.get('id'));
        return item ? respond({item}) : respond({error: '记录不存在'}, 404);
      }
      if (parsed.pathname === '/api/admin/records' && method === 'POST') {
        if (saveFailure) return respond({error: '资料已被其他人修改，请刷新后重试'}, saveFailure);
        assert.equal(body.action, 'save');
        const previous = body.id ? records.get(body.id) : null;
        if ((previous ? previous.version : 0) !== body.version) return respond({error: '版本冲突'}, 409);
        const id = previous?.id || `workspace-new-${nextId++}`;
        const saved = {...(previous || {id, kind: 'package', images: [], productCode: 'YZ-BC-900001'}),
          ...body.record, id, version: (previous?.version || 0) + 1};
        records.set(id, clone(saved));
        return respond(saved);
      }
    }
    throw Error(`Unexpected synthetic API request: ${method} ${url}`);
  };
  // Run the real import graph; replace only curated grouping data with synthetic IDs.
  await evaluateBrowserModule(dom, path.join(root, 'app.js'),
    `\nreviewedProductGroups.splice(0, reviewedProductGroups.length, ${JSON.stringify(reviewedGroup)});`);
  await until(() => d.querySelector('#searchForm') && d.querySelector('#favCount').textContent === '1', 'workspace loaded');
  return {dom, w, d, errors, calls, records, failSave(status) {saveFailure = status;},
    setSession(value) {liveSession = {...liveSession, ...value};}};
}

function click(p, selector) {
  const element = p.d.querySelector(selector);
  assert.ok(element, `Missing control: ${selector}`);
  element.click();
  return element;
}
function search(p, value) {
  p.d.querySelector('#query').value = value;
  p.d.querySelector('#searchForm').dispatchEvent(new p.w.Event('submit', {bubbles: true, cancelable: true}));
}
function editField(p, field, value) {
  const element = p.d.querySelector(`[data-editor-field="${field}"]`);
  assert.ok(element, `Missing editor field: ${field}`);
  element.value = value;
  element.dispatchEvent(new p.w.Event('input', {bubbles: true}));
}
function submitEditor(p) {
  const form = p.d.querySelector('[data-editor-form]');
  assert.ok(form, 'Editor form is open');
  form.dispatchEvent(new p.w.Event('submit', {bubbles: true, cancelable: true}));
}
const adminCalls = p => p.calls.filter(call => call.url.startsWith('/api/admin/'));
const saves = p => adminCalls(p).filter(call => call.method === 'POST');
const visible = element => Boolean(element && !element.hidden && !element.closest('[hidden]'));
function injectClick(p, attribute, value) {
  const button = p.d.createElement('button');button.setAttribute(attribute, value);
  p.d.querySelector('#main').append(button);button.click();button.remove();
}

(async () => {
  let p = await open({hash: '#records'});
  try {
    assert.ok(visible(p.d.querySelector('[data-action="new-product"]')));
    assert.ok(visible(p.d.querySelector('[data-action="staff-preview"]')));
    assert.equal(p.d.querySelector('#adminLink').getAttribute('href'), '/admin/tools');
    assert.deepEqual([...p.d.querySelectorAll('#sidebar [data-section]')].map(node => node.dataset.section), ['face', 'body', 'head']);
    assert.equal(p.d.querySelector('#categorySidebar'), null);
    assert.equal(p.d.querySelector('#catalogFilterDetails').hidden, true);
    click(p, '[data-action="toggle-filters"]');
    assert.equal(p.d.querySelector('#catalogFilterDetails').hidden, false);
    click(p, '[data-action="toggle-filters"]');
    assert.equal(p.d.querySelector('#catalogFilterDetails').hidden, true);
    click(p, '[data-action="new-product"]');
    await until(() => p.d.querySelector('[data-editor-form]'), 'new product editor');
    assert.equal(p.d.querySelector('#modal').open, true);
    assert.equal(adminCalls(p).length, 0, 'New draft does not fetch all admin records');
    editField(p, 'name', '合成新增产品');
    editField(p, 'materials', 'PET、玻璃');
    click(p, '[data-editor-area="face"]');
    submitEditor(p);
    await until(() => saves(p).length === 1 && !p.d.querySelector('[data-editor-form]'), 'new product saved');
    const payload = saves(p)[0].body;
    assert.equal(payload.version, 0);
    assert.equal(payload.id, undefined);
    assert.equal(payload.record.productCode, undefined);
    assert.equal(payload.record.source, undefined);
    assert.deepEqual(payload.record.materials, ['PET', '玻璃']);
    assert.deepEqual(payload.record.bodyAreas, ['face']);
    search(p, 'YZ-BC-900001');
    assert.equal(p.d.querySelector('.card-title').dataset.detail, 'workspace-new-1');
    assert.match(p.d.querySelector('.card-title').textContent, /合成新增产品/);
    assert.deepEqual(p.errors, []);
    checks.push('Legacy #records opens the admin catalogue; sidebar has three body areas, filters collapse, and new products receive server IDs and codes');
  } finally {p.dom.window.close();}

  p = await open();
  try {
    search(p, '保留筛选瓶');
    click(p, '[data-action="toggle-filters"]');
    click(p, '[data-filter="material"][value="PET"]');
    click(p, '[data-page-control="next"]');
    const pageRange = p.d.querySelector('.page-range').textContent;
    assert.match(pageRange, /2 \/ 3/);
    const edit = p.d.querySelector('#catalogPageContent [data-edit-record]');
    assert.ok(edit);
    const id = edit.dataset.editRecord, original = clone(p.records.get(id));
    click(p, `#catalogPageContent [data-favorite="${id}"]`);
    await until(() => p.d.querySelector('#favCount').textContent === '2', 'favorite saved');
    const preferencesWrites = p.calls.filter(call => call.url === '/api/preferences' && call.method === 'POST').length;
    click(p, `#catalogPageContent [data-edit-record="${id}"]`);
    await until(() => p.d.querySelector('[data-editor-form]'), 'existing product editor');
    assert.equal(p.d.querySelector('[data-editor-field="name"]').value, original.name);
    editField(p, 'name', original.name + '已更新');
    submitEditor(p);
    await until(() => saves(p).length === 1 && !p.d.querySelector('[data-editor-form]'), 'selected record saved');
    assert.equal(saves(p)[0].body.id, id);
    assert.equal(saves(p)[0].body.version, original.version);
    assert.deepEqual(saves(p)[0].body.record, {name: original.name + '已更新'});
    assert.equal(p.d.querySelector('#query').value, '保留筛选瓶');
    assert.equal(p.d.querySelector('[data-filter="material"][value="PET"]').checked, true);
    assert.equal(p.d.querySelector('.page-range').textContent, pageRange);
    assert.equal(p.d.querySelector('#favCount').textContent, '2');
    assert.ok(p.d.querySelector(`#catalogPageContent [data-favorite="${id}"]`).classList.contains('on'));
    assert.equal(p.calls.filter(call => call.url === '/api/preferences' && call.method === 'POST').length, preferencesWrites);
    assert.equal(p.records.get(id).productCode, original.productCode);
    assert.deepEqual(adminCalls(p).filter(call => call.method === 'GET').map(call => call.url),
      ['/api/admin/records?id=' + encodeURIComponent(id)]);
    assert.deepEqual(p.errors, []);
    checks.push('Editing one card preserves search, selected material, page, favorites and the original product code without loading the entire admin list');
  } finally {p.dom.window.close();}

  p = await open();
  try {
    search(p, 'YZ-BC-800001');
    click(p, '.card-title');
    click(p, '.group-option[data-detail="workspace-spec-1"]');
    click(p, '#modalBody [data-edit-record="workspace-spec-1"]');
    await until(() => p.d.querySelector('[data-editor-form]'), 'current SKU editor');
    assert.equal(p.d.querySelector('[data-editor-field="specificationRaw"]').value, '50mL');
    const untouched = clone(p.records.get('workspace-spec-0'));
    editField(p, 'quoteRaw', '只更新50mL规格的报价');
    submitEditor(p);
    await until(() => saves(p).length === 1 && !p.d.querySelector('[data-editor-form]'), 'current SKU saved');
    assert.equal(saves(p)[0].body.id, 'workspace-spec-1');
    assert.equal(saves(p)[0].body.version, 9);
    assert.deepEqual(saves(p)[0].body.record, {quoteRaw: '只更新50mL规格的报价'});
    assert.deepEqual(p.records.get('workspace-spec-0'), untouched);
    assert.equal(p.records.get('workspace-spec-1').productCode, 'YZ-BC-800002');
    assert.deepEqual(p.errors, []);
    checks.push('Editing from a grouped detail uses the selected specification ID and latest version and leaves its sibling record untouched');
  } finally {p.dom.window.close();}

  p = await open({role: 'employee'});
  try {
    assert.equal(p.d.querySelector('[data-action="new-product"]'), null);
    assert.equal(p.d.querySelector('[data-edit-record]'), null);
    assert.equal(visible(p.d.querySelector('#adminLink')), false);
    assert.equal(visible(p.d.querySelector('[data-action="staff-preview"]')), false);
    click(p, '.card-title');
    assert.equal(p.d.querySelector('#modalBody [data-edit-record]'), null);
    p.d.querySelector('#modal').close();
    injectClick(p, 'data-edit-record', 'workspace-0');
    injectClick(p, 'data-action', 'new-product');
    await new Promise(resolve => setTimeout(resolve, 30));
    assert.equal(adminCalls(p).length, 0);
    assert.equal(p.d.querySelector('[data-editor-form]'), null);
    assert.deepEqual(p.errors, []);
    checks.push('Employee catalogue and details expose no edit controls and ignore forged admin actions without issuing admin requests');
  } finally {p.dom.window.close();}

  p = await open();
  try {
    search(p, '保留筛选瓶');
    click(p, '[data-page-control="next"]');
    const pageRange = p.d.querySelector('.page-range').textContent;
    click(p, '[data-action="staff-preview"]');
    assert.equal(p.d.querySelector('[data-action="new-product"]'), null);
    assert.equal(p.d.querySelector('[data-edit-record]'), null);
    assert.equal(visible(p.d.querySelector('#adminLink')), false);
    injectClick(p, 'data-edit-record', 'workspace-0');
    injectClick(p, 'data-action', 'new-product');
    await new Promise(resolve => setTimeout(resolve, 30));
    assert.equal(adminCalls(p).length, 0);
    assert.equal(p.d.querySelector('#query').value, '保留筛选瓶');
    assert.equal(p.d.querySelector('.page-range').textContent, pageRange);
    click(p, '[data-action="staff-preview"]');
    assert.ok(visible(p.d.querySelector('[data-action="new-product"]')));
    assert.ok(p.d.querySelector('[data-edit-record]'));
    assert.equal(p.calls.filter(call => call.url === '/api/session').length, 1, 'Preview does not change the authenticated role');
    assert.deepEqual(p.errors, []);
    checks.push('Staff preview hides mutation controls and tools without changing account role or losing current search and page');
  } finally {p.dom.window.close();}

  p = await open();
  try {
    click(p, '#catalogPageContent [data-edit-record="workspace-0"]');
    await until(() => p.d.querySelector('[data-editor-form]'), 'conflict editor');
    const original = clone(p.records.get('workspace-0'));
    editField(p, 'name', '冲突时保留草稿');
    p.failSave(409);
    submitEditor(p);
    await until(() => p.d.querySelector('[data-editor-status]')?.classList.contains('is-error'), 'version conflict shown');
    assert.equal(saves(p).length, 1);
    assert.equal(p.d.querySelector('[data-editor-field="name"]').value, '冲突时保留草稿');
    assert.equal(p.d.querySelector('#modal').open, true);
    assert.deepEqual(p.records.get('workspace-0'), original);
    p.w.confirm = () => false;
    click(p, '[data-editor-action="cancel"]');
    assert.ok(p.d.querySelector('[data-editor-form]'));
    assert.equal(saves(p).length, 1);
    assert.deepEqual(p.errors, []);
    checks.push('A version conflict is not replayed, preserves the draft, and cancellation respects the unsaved-change confirmation');
  } finally {p.dom.window.close();}

  p = await open();
  try {
    click(p, '#catalogPageContent [data-edit-record="workspace-0"]');
    await until(() => p.d.querySelector('[data-editor-form]'), 'session-expiry editor');
    editField(p, 'name', '重新登录后保留的草稿');
    const originalURL = p.w.location.href;
    p.setSession({authenticated: false});
    submitEditor(p);
    await until(() => p.d.querySelector('[data-editor-status]')?.classList.contains('is-error'), 'expired session shown without navigation');
    assert.equal(p.w.location.href, originalURL);
    assert.equal(p.d.querySelector('[data-editor-field="name"]').value, '重新登录后保留的草稿');
    assert.equal(p.d.querySelector('#modal').open, true);
    assert.equal(saves(p).length, 0, 'Expired session is rejected before a mutation');
    // A separate tab signs the same administrator in again and replaces the cookie/CSRF pair.
    p.setSession({authenticated: true, csrf: 'workspace-renewed-csrf'});
    submitEditor(p);
    await until(() => saves(p).length === 1 && !p.d.querySelector('[data-editor-form]'), 'draft saved under renewed session');
    assert.equal(saves(p)[0].body.id, 'workspace-0');
    assert.equal(saves(p)[0].body.version, 2);
    assert.equal(saves(p)[0].body.record.name, '重新登录后保留的草稿');
    assert.equal(p.records.get('workspace-0').name, '重新登录后保留的草稿');
    assert.deepEqual(p.errors, []);
    checks.push('An expired session keeps the draft and location; deliberate retry after same-account login refreshes CSRF and saves exactly once');
  } finally {p.dom.window.close();}

  for (const replacement of [{username: 'different-administrator', role: 'admin'}, {username: 'fixture-admin', role: 'employee'}]) {
    p = await open();
    try {
      click(p, '#catalogPageContent [data-edit-record="workspace-0"]');
      await until(() => p.d.querySelector('[data-editor-form]'), 'account-change editor');
      const original = clone(p.records.get('workspace-0'));
      editField(p, 'name', '身份变更时不能保存');
      p.setSession({...replacement, csrf: 'different-session-token'});
      submitEditor(p);
      await until(() => p.d.querySelector('[data-editor-status]')?.classList.contains('is-error'), 'account change rejected');
      assert.equal(saves(p).length, 0, 'Changed identity is rejected before a mutation');
      assert.equal(p.d.querySelector('[data-editor-field="name"]').value, '身份变更时不能保存');
      assert.deepEqual(p.records.get('workspace-0'), original);
      assert.deepEqual(p.errors, []);
    } finally {p.dom.window.close();}
  }
  checks.push('Changing the logged-in account or losing the administrator role blocks saving before POST and retains the draft');

  p=await open({paging:true,hash:'#records/workspace-spec-1'});
  try{
    await until(()=>p.d.querySelector('[data-editor-form]'),'unloaded paged hash editor');
    assert.equal(p.d.querySelector('[data-editor-field="name"]').value,'独立规格瓶50ml');
    editField(p,'name','修改后的50ml瓶');submitEditor(p);
    await until(()=>!p.d.querySelector('[data-editor-form]')&&p.d.querySelector('#modal').textContent.includes('YZ-BC-800002'),'paged save detail');
    assert(p.d.querySelector('#modal [data-detail="workspace-spec-0"]'),'Sibling specifications still available after refresh');
    p.d.querySelector('#modal').close();search(p,'YZ-BC-800002');
    await until(()=>p.d.querySelector('[data-record-id="workspace-spec-1"]'),'saved exact code');
    assert.equal(p.d.querySelector('.card-title').dataset.detail,'workspace-spec-1');
    click(p,'[data-edit-record="workspace-spec-1"]');await until(()=>p.d.querySelector('[data-editor-form]'),'updated paged editor');assert.equal(p.d.querySelector('[data-editor-field="name"]').value,'修改后的50ml瓶');
    assert(!p.calls.some(call=>call.url==='/api/catalog'),'Admin paging never needs the full catalogue');
    assert.equal(saves(p)[0].body.version,9);assert.equal(p.records.get('workspace-spec-1').version,10);
    assert.deepEqual(p.errors,[]);checks.push('Server-paged admin deep links, saved versions, family details and exact-code refresh stay correct without a full catalogue download');
  }finally{p.dom.window.close();}
  console.log(JSON.stringify({passed: true, checks, liveWebsiteRequests: 0}, null, 2));
})().catch(error => {console.error(error);process.exitCode = 1;});
