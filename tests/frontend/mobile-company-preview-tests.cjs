const {test} = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const {JSDOM} = require('jsdom');
const base = path.resolve(__dirname, '../../docs/mobile-client-preview');
const original = 'We research, develop, and manufacture skincare, body care, hair care, and sun protection products for brands and retailers in over 30 countries worldwide. Our products are FDA-registered and certified to ISO 22716 and GMPC standards, with a formulation science foundation built on 14 years of experience. From your first private label line to millions of retail items, you need only partner with one trusted collaborator.';

function setup(language = 'zh', blockedStorage = false) {
  const dom = new JSDOM(fs.readFileSync(path.join(base,'index.html'),'utf8'), {url:'http://localhost/',runScripts:'outside-only'});
  const {window} = dom;
  if (blockedStorage) Object.defineProperty(window,'localStorage',{get(){throw new Error('unavailable');}});
  else window.localStorage.setItem('yuanze-mobile-preview-language',language);
  window.HTMLDialogElement.prototype.showModal = function(){this.open=true;};
  window.HTMLDialogElement.prototype.close = function(){this.open=false;this.dispatchEvent(new window.Event('close'));};
  window.eval(fs.readFileSync(path.join(base,'company-content.js'),'utf8'));
  window.eval(fs.readFileSync(path.join(base,'preview.js'),'utf8'));
  return {dom,window,document:window.document};
}

test('company material preserves the supplied original and maps photos to correct sections', () => {
  const {dom,window,document} = setup();
  assert.equal(window.YuanzeCompanyContent.originalIntroductionEn,original);
  assert.doesNotMatch(window.YuanzeCompanyContent.en.introduction,/FDA-registered|FDA-approved|FDA certified/);
  assert.match(window.YuanzeCompanyContent.en.introduction,/manufacturing management system/);
  assert.match(document.querySelector('[data-photo=showroom] img').src,/assets\/showroom.png$/);
  assert.match(document.querySelector('#about [data-photo=reception] img').src,/assets\/reception.png$/);
  for (const image of Object.values(window.YuanzeCompanyContent.images)) assert(fs.existsSync(path.join(base,image.src)));
  for (const cert of Object.values(window.YuanzeCompanyContent.certificates)) for (const variant of Object.values(cert.versions)) {
    assert(fs.existsSync(path.join(base,variant.src)));
    assert(fs.existsSync(path.join(base,variant.pdf)));
  }
  assert(!document.querySelector('[data-copy=introduction]').textContent.includes('undefined'));
  dom.window.close();
});

test('language toggle switches certificate image and original PDF together without resetting expanded introduction', () => {
  const {dom,window,document} = setup();
  const details = document.getElementById('company-details');
  details.open=false;
  document.getElementById('language-toggle').click();
  assert.equal(document.documentElement.lang,'en');
  assert.equal(details.open,false);
  assert.equal(window.localStorage.getItem('yuanze-mobile-preview-language'),'en');
  for (const id of ['gmpc','iso22716']) {
    assert.match(document.querySelector(`[data-certificate-image=${id}]`).src,new RegExp(id+'-en.png$'));
    assert.match(document.querySelector(`[data-certificate-pdf=${id}]`).href,new RegExp(id+'-en.pdf$'));
  }
  assert.match(document.querySelector('[data-copy=introduction]').textContent,/ISO 22716/);
  assert(!document.body.textContent.includes('undefined'));
  document.getElementById('language-toggle').click();
  assert.equal(document.documentElement.lang,'zh-CN');
  assert.match(document.querySelector('[data-certificate-pdf=gmpc]').href,/gmpc-zh.pdf$/);
  dom.window.close();
});

test('certificate enlargement follows selected language and close restores focus', () => {
  const {dom,document} = setup('en');
  const button = document.querySelector('[data-certificate=iso22716]');
  button.click();
  const dialog = document.getElementById('photo-dialog');
  assert.equal(dialog.open,true);
  assert.match(document.getElementById('expanded-photo').src,/iso22716-en.png$/);
  assert.match(document.getElementById('photo-caption').textContent,/ISO 22716/);
  document.getElementById('close-photo').click();
  assert.equal(dialog.open,false);
  assert.equal(document.activeElement,button);
  assert.equal(document.getElementById('expanded-photo').hasAttribute('src'),false);
  document.querySelector('[data-photo=reception]').click();
  assert.match(document.getElementById('expanded-photo').src,/reception.png$/);
  dom.window.close();
});

test('blocked browser storage does not prevent translations or certificate access', () => {
  const {dom,document} = setup('zh',true);
  document.getElementById('language-toggle').click();
  assert.equal(document.documentElement.lang,'en');
  document.querySelector('[data-certificate=gmpc]').click();
  assert.equal(document.getElementById('photo-dialog').open,true);
  assert.match(document.querySelector('[data-certificate-pdf=gmpc]').href,/gmpc-en.pdf$/);
  dom.window.close();
});

test('bottom navigation switches independent pages, preserves mounted catalogue and supports history', () => {
  const {dom,window,document} = setup();
  const panel = name => document.getElementById('page-'+name);
  const tab = name => document.querySelector('.bottom-nav [data-page-link='+name+']');
  const frame = document.getElementById('catalog-frame');
  assert.equal(panel('home').hidden,false);
  assert.equal(panel('products').hidden,true);
  assert.equal(frame.hasAttribute('src'),false);
  assert.equal(panel('home').querySelector('iframe'),null);
  assert.equal(panel('home').querySelector('#contact'),null);
  tab('products').click();
  assert.equal(window.location.hash,'#/products');
  assert.equal(panel('home').hidden,true);
  assert.equal(panel('products').hidden,false);
  assert.equal(frame.getAttribute('src'),'/client?showroom=1');
  const childWindow=frame.contentWindow;
  panel('home').scrollTop=240;
  tab('contact').click();
  assert.equal(panel('products').hidden,true);
  assert.equal(panel('contact').hidden,false);
  tab('products').click();
  assert.equal(frame.contentWindow,childWindow);
  assert.equal(panel('home').scrollTop,240);
  window.history.replaceState(null,'','#/home');
  window.dispatchEvent(new window.PopStateEvent('popstate'));
  assert.equal(panel('home').hidden,false);
  assert.equal(document.querySelectorAll('.bottom-nav [aria-current=page]').length,1);
  assert.equal(tab('home').getAttribute('aria-current'),'page');
  assert(document.querySelector('meta[name=robots]').content.includes('noindex'));
  dom.window.close();
});

test('contact accepts only allowlisted shortlist fields from the catalogue frame and safely copies an enquiry', async () => {
  const {dom,window,document} = setup();
  document.querySelector('.bottom-nav [data-page-link=products]').click();
  const frame=document.getElementById('catalog-frame');
  const data={type:'yuanze-shortlist',items:[{productCode:'YZ-BC-000001',capacity:'100 mL',supplier:'PRIVATE SUPPLIER',price:'PRIVATE PRICE'},{productCode:'YZ-BC-000002',capacity:'<img src=x>'},{productCode:'<script>',capacity:'20 mL'}]};
  const send=(origin,source,payload=data)=>window.dispatchEvent(new window.MessageEvent('message',{origin,source,data:payload}));
  send('https://attacker.invalid',frame.contentWindow);
  assert.equal(document.getElementById('inquiry-items').children.length,0);
  send('http://localhost',window);
  assert.equal(document.getElementById('inquiry-items').children.length,0);
  send('http://localhost',frame.contentWindow);
  assert.equal(document.getElementById('inquiry-items').children.length,2);
  assert.doesNotMatch(document.getElementById('inquiry-items').innerHTML,/PRIVATE|<img|<script/);
  send('http://localhost',frame.contentWindow,{type:'yuanze-contact'});
  assert.equal(document.getElementById('page-contact').hidden,false);
  let copied='';Object.defineProperty(window.navigator,'clipboard',{value:{writeText:async text=>{copied=text;}}});
  document.getElementById('inquiry-note').value='Need 5,000 bottles';
  document.getElementById('copy-inquiry').click();
  await new Promise(resolve=>setImmediate(resolve));
  assert.match(copied,/YZ-BC-000001 · 100 mL/);
  assert.match(copied,/Need 5,000 bottles/);
  assert.doesNotMatch(copied,/PRIVATE|<img/);
  assert.match(document.getElementById('inquiry-status').textContent,/已复制/);
  send('http://localhost',frame.contentWindow,{type:'yuanze-language',language:'en'});
  assert.equal(document.documentElement.lang,'en');
  assert.equal(document.getElementById('inquiry-note').value,'Need 5,000 bottles');
  assert.equal(document.getElementById('page-contact').hidden,false);
  dom.window.close();
});
