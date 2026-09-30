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

test('preview does not make background production requests and gallery link uses existing sign-in entry', () => {
  const {dom,document} = setup();
  const link = document.querySelector('[data-copy=packagingButton]');
  assert.equal(link.href,'https://bmt.yuanzebeauty.com/');
  assert.equal(link.rel,'noopener noreferrer');
  for (const file of ['company-content.js','preview.js']) assert.doesNotMatch(fs.readFileSync(path.join(base,file),'utf8'),/\b(?:fetch|XMLHttpRequest|WebSocket)\s*\(/);
  assert(document.querySelector('meta[name=robots]').content.includes('noindex'));
  dom.window.close();
});
