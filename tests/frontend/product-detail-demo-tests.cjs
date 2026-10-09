const {test} = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const {JSDOM} = require('jsdom');
const base = path.resolve(__dirname, '../../docs/product-detail-demo');

function setup() {
  const dom = new JSDOM(fs.readFileSync(path.join(base,'index.html'),'utf8'),{url:'http://127.0.0.1:8901/',runScripts:'outside-only'});
  const {window} = dom, doc=window.document;
  window.fetch=()=>{throw Error('Demo must not contact the production API');};
  window.HTMLDialogElement.prototype.showModal=function(){this.setAttribute('open','');};
  window.HTMLDialogElement.prototype.close=function(){this.removeAttribute('open');};
  window.eval(fs.readFileSync(path.join(base,'demo.js'),'utf8'));
  function change(selector,value){const el=doc.querySelector(selector);el.value=value;el.dispatchEvent(new window.Event('change',{bubbles:true}));}
  function finish(value,checked=true){const el=doc.querySelector(`input[value="${value}"]`);el.checked=checked;el.dispatchEvent(new window.Event('change',{bubbles:true}));}
  return {window,doc,change,finish,close:()=>window.close()};
}

test('core fields are compact and keep unsupported material blank',()=>{
  const e=setup();try {
    assert.equal(e.doc.querySelectorAll('.price-block').length,1);
    assert.deepEqual(Array.from(e.doc.querySelectorAll('.facts dt'),n=>n.textContent),['材质','规格','MOQ · 起订量','货期','通常用于']);
    assert.equal(e.doc.querySelector('.facts dd').textContent,'');
    assert.match(e.doc.querySelector('.price-value').textContent,/1\.80/);
    assert.match(e.doc.querySelector('.facts').textContent,/50 g/);
    assert.match(e.doc.querySelector('.facts').textContent,/5,000个/);
    assert.match(e.doc.querySelector('.facts').textContent,/20天/);
    assert.equal(e.doc.querySelector('.internal').open,false);
  } finally{e.close();}
});
test('all requested finishes are represented without inventing MOQ or lead time',()=>{
  const e=setup();try {
    const rows=Array.from(e.doc.querySelectorAll('tbody tr'));
    assert.equal(rows.length,9);
    assert.match(rows.map(n=>n.textContent).join(' '),/裸瓶.*丝印.*烫金 \/ 烫银.*注塑色.*喷涂.*蒙砂.*电镀瓶身.*电镀盖子.*其他工艺/);
    for(const row of rows.slice(1)) assert.equal(row.cells[2].textContent+row.cells[3].textContent,'');
    assert.match(e.doc.querySelector('.demo-rate-label').textContent,/演示标准/);
  }finally{e.close();}
});
test('estimate uses per-colour rates, updates selections and does not accumulate rounding errors',()=>{
  const e=setup();try {
    e.finish('silk');e.change('[data-colours="silk"]','2');e.finish('foil');
    assert.match(e.doc.querySelector('.estimate-total').textContent,/2\.20/);
    e.finish('spray');assert.match(e.doc.querySelector('.estimate-total').textContent,/2\.70/);
    e.finish('foil',false);assert.match(e.doc.querySelector('.estimate-total').textContent,/2\.50/);
    assert.match(e.doc.querySelector('.estimate-hint').textContent,/未计材质差价、配件及税费/);
  }finally{e.close();}
});
test('editing colour count updates the estimate immediately without replacing the active input',()=>{
  const e=setup();try{
    e.finish('silk');const input=e.doc.querySelector('[data-colours="silk"]');input.focus();input.value='2';
    input.dispatchEvent(new e.window.Event('input',{bubbles:true}));
    assert.match(e.doc.querySelector('.estimate-total').textContent,/2\.00/);
    assert.equal(e.doc.querySelector('[data-colours="silk"]'),input);
    assert.equal(e.doc.activeElement,input);
    e.finish('foil');assert.match(e.doc.querySelector('.estimate-total').textContent,/2\.20/);
  }finally{e.close();}
});
test('a selected finish with no fee blocks the total instead of treating it as free',()=>{
  const e=setup();try {
    e.finish('silk');e.finish('bodyPlate');
    assert.equal(e.doc.querySelector('.estimate-total'),null);
    assert.match(e.doc.querySelector('.estimate').textContent,/缺少费用：电镀瓶身/);
    e.finish('bodyPlate',false);assert.match(e.doc.querySelector('.estimate-total').textContent,/1\.90/);
  }finally{e.close();}
});
test('missing base price and invalid colour quantities cannot produce a total',()=>{
  const e=setup();try {
    e.finish('silk');
    for(const value of ['0','-1','1.5','10','']){
      e.change('[data-colours="silk"]',value);
      assert.equal(e.doc.querySelector('.estimate-total'),null,value);
      assert.match(e.doc.querySelector('.estimate-missing').textContent,/1–9/);
    }
    e.change('[data-colours="silk"]','1');e.change('#scenario','empty');
    assert.equal(e.doc.querySelector('.estimate-total'),null);
    assert.match(e.doc.querySelector('.estimate-missing').textContent,/裸瓶价格未录入/);
    for(const dd of e.doc.querySelectorAll('.facts dd'))assert.equal(dd.textContent,'');
  }finally{e.close();}
});
test('client preview removes all monetary, supplier and internal quote markup',()=>{
  const e=setup();try {
    e.finish('silk');e.change('#role','client');
    const detail=e.doc.querySelector('#detail');
    for(const selector of ['.price-block','.estimate','.internal','table'])assert.equal(detail.querySelector(selector),null,selector);
    assert.doesNotMatch(detail.textContent,/供应商|联系方式|价格|报价|1\.80|¥|含税|原始/);
    assert.match(detail.textContent,/50 g/);
    assert.match(detail.textContent,/加入意向清单/);
    assert.equal(detail.querySelectorAll('img').length,2);
  }finally{e.close();}
});
test('language change preserves selections and computed reference while translating labels',()=>{
  const e=setup();try {
    e.finish('silk');e.change('[data-colours="silk"]','3');e.doc.querySelector('#language').click();
    assert.equal(e.doc.documentElement.lang,'en');
    assert.match(e.doc.querySelector('.estimate-total').textContent,/2\.10/);
    assert.equal(e.doc.querySelector('[data-colours="silk"]').value,'3');
    assert.match(e.doc.querySelector('.estimate-hint').textContent,/not a formal quote/);
    assert.match(e.doc.querySelector('h1').textContent,/Cream jar/);
    e.change('#role','client');assert.doesNotMatch(e.doc.querySelector('#detail').textContent,/Supplier|quote|¥/);
  }finally{e.close();}
});
test('image viewer and local-only actions work without storing or sending production data',()=>{
  const e=setup();try {
    e.doc.querySelector('.hero-image').click();assert.equal(e.doc.querySelector('#image-dialog').open,true);
    e.doc.querySelector('#close-image').click();assert.equal(e.doc.querySelector('#image-dialog').open,false);
    e.doc.querySelector('[data-action="favorite"]').click();assert.equal(e.doc.querySelector('[data-action="favorite"]').getAttribute('aria-pressed'),'true');
    e.doc.querySelector('[data-action="shortlist"]').click();assert.equal(e.doc.querySelector('[data-action="shortlist"]').getAttribute('aria-pressed'),'true');
    assert.match(e.doc.querySelector('#notice').textContent,/未写入正式系统/);
    assert.equal(e.window.localStorage.length,0);
    assert.equal(e.doc.querySelector('a.download').getAttribute('download'),'YZ-BC-000005.png');
  }finally{e.close();}
});
