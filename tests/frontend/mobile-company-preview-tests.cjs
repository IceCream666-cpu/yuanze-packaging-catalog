const {test} = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const {JSDOM,VirtualConsole} = require('jsdom');
const base = path.resolve(__dirname, '../../docs/mobile-client-preview');
const original = 'We research, develop, and manufacture skincare, body care, hair care, and sun protection products for brands and retailers in over 30 countries worldwide. Our products are FDA-registered and certified to ISO 22716 and GMPC standards, with a formulation science foundation built on 14 years of experience. From your first private label line to millions of retail items, you need only partner with one trusted collaborator.';
const lightURL=(source,edge=512)=>source.replace(/assets\/(.+)\.(png|webp)$/,`assets/previews/$1-${edge}.webp`);
const bannerFiles = ['01-pdrn-capsule-cream', '02-body-care-collection', '03-cherry-blossom-gift-set', '04-hand-care-collection', '05-daylight-still'];

// Drive elapsed time and browser visibility through public browser APIs so the
// carousel can be tested without exposing its implementation or waiting 6 s.
function bannerEnvironment(window, options) {
  let now=0, nextTimer=1, hidden=Boolean(options.hidden), visible=options.visible!==false;
  const timers=new Map(), observers=new Set(), mediaListeners=new Set();
  window.setTimeout=(callback,delay=0,...args)=>{
    const id=nextTimer++;
    timers.set(id,{at:now+Math.max(0,Number(delay)||0),callback,args});
    return id;
  };
  window.clearTimeout=id=>timers.delete(id);
  Object.defineProperty(window.document,'hidden',{configurable:true,get:()=>hidden});
  Object.defineProperty(window.document,'visibilityState',{configurable:true,get:()=>hidden?'hidden':'visible'});
  const media={matches:Boolean(options.reducedMotion),media:'(prefers-reduced-motion: reduce)',
    addEventListener(type,callback){if(type==='change')mediaListeners.add(callback);},
    removeEventListener(type,callback){if(type==='change')mediaListeners.delete(callback);},
    addListener(callback){mediaListeners.add(callback);},removeListener(callback){mediaListeners.delete(callback);}};
  window.matchMedia=()=>media;
  window.IntersectionObserver=class {
    constructor(callback){this.callback=callback;this.targets=new Set();observers.add(this);}
    observe(target){this.targets.add(target);this.callback([{target,isIntersecting:visible,intersectionRatio:visible?1:0}]);}
    unobserve(target){this.targets.delete(target);}
    disconnect(){this.targets.clear();observers.delete(this);}
  };
  return {
    advance(milliseconds){
      const end=now+milliseconds;
      let calls=0;
      while(true){
        const pending=Array.from(timers).filter(([,timer])=>timer.at<=end).sort((a,b)=>a[1].at-b[1].at||a[0]-b[0])[0];
        if(!pending)break;
        assert(++calls<1000,'Timer loop did not settle');
        const [id,timer]=pending;now=timer.at;timers.delete(id);timer.callback(...timer.args);
      }
      now=end;
    },
    setHidden(value){hidden=value;window.document.dispatchEvent(new window.Event('visibilitychange'));},
    setVisible(value){
      visible=value;
      for(const observer of observers){
        const entries=Array.from(observer.targets).filter(target=>target.id==='poster-banner').map(target=>({target,isIntersecting:value,intersectionRatio:value?1:0}));
        if(entries.length)observer.callback(entries);
      }
    },
    setReducedMotion(value){media.matches=value;for(const callback of mediaListeners)callback({matches:value,media:media.media});},
  };
}

function setup(language = 'zh', blockedStorage = false, options = {}) {
  const errors = [], virtualConsole = new VirtualConsole();
  virtualConsole.on('jsdomError',error => {if (!error.message.includes('Not implemented: navigation')) errors.push(error.message);});
  const html = fs.readFileSync(path.join(base,'index.html'),'utf8').replace('data-mode="preview"',`data-mode="${options.mode || 'preview'}"`);
  const dom = new JSDOM(html, {url:'http://localhost/'+(options.hash || ''),runScripts:'outside-only',virtualConsole});
  const {window} = dom;
  if(options.legacyBanner)window.document.getElementById('poster-banner').remove();
  window.fetch = options.fetch || (async () => {throw Error('Unexpected fetch');});
  if(options.beforeStart)options.beforeStart(window);
  const banner=options.banner ? bannerEnvironment(window,options.banner) : null;
  if (blockedStorage) Object.defineProperty(window,'localStorage',{get(){throw new Error('unavailable');}});
  else window.localStorage.setItem('yuanze-mobile-preview-language',language);
  window.HTMLDialogElement.prototype.showModal = function(){this.open=true;};
  window.HTMLDialogElement.prototype.close = function(){this.open=false;this.dispatchEvent(new window.Event('close'));};
  window.eval(fs.readFileSync(path.join(base,'company-content.js'),'utf8'));
  window.eval(fs.readFileSync(path.join(base,'product-posters.js'),'utf8'));
  const source = fs.readFileSync(path.join(base,'preview.js'),'utf8');
  if (options.navigation) {
    // Execute the unchanged shell with a location adapter to verify navigation
    // targets, since jsdom itself does not implement cross-document navigation.
    const location = {get origin(){return window.location.origin;},get hash(){return window.location.hash;},replace:url=>options.navigation.push(url)};
    vm.runInNewContext(source,{window,document:window.document,location,history:window.history,localStorage:window.localStorage,navigator:window.navigator,fetch:window.fetch,AbortController:window.AbortController,setTimeout:window.setTimeout.bind(window),clearTimeout:window.clearTimeout.bind(window)});
  } else window.eval(source);
  return {dom,window,document:window.document,errors,banner};
}

function historyChange(window, action) {
  return new Promise((resolve, reject) => {
    const timer = setTimeout(() => reject(Error('Expected a browser history event')), 1000);
    window.addEventListener('popstate', () => {clearTimeout(timer);resolve();}, {once:true});
    action();
  });
}

test('expertise labels show service models before scripts load and after language changes', () => {
  const expected = ['OEM', 'ODM', 'OBM', 'private label'];
  const markup = new JSDOM(fs.readFileSync(path.join(base, 'index.html'), 'utf8'));
  const labels = document => Array.from(document.querySelectorAll('[data-capability]'), node => node.textContent);
  assert.deepEqual(labels(markup.window.document), expected);
  markup.window.close();
  for (const language of ['zh', 'en']) {
    const {dom, document, errors} = setup(language);
    assert.deepEqual(labels(document), expected);
    document.getElementById('language-toggle').click();
    assert.deepEqual(labels(document), expected);
    document.getElementById('language-toggle').click();
    assert.deepEqual(labels(document), expected);
    assert.deepEqual(errors, []);
    dom.window.close();
  }
});

function activeBanner(document) {
  const slides=Array.from(document.querySelectorAll('img[data-banner-slide][aria-hidden="false"]'));
  assert.equal(slides.length,1,'Exactly one background is current');
  assert.equal(slides[0].parentElement.classList.contains('is-active'),true);
  assert.equal(slides[0].parentElement.getAttribute('aria-hidden'),'false');
  for(const image of document.querySelectorAll('img[data-banner-slide][aria-hidden="true"]')){
    assert.equal(image.parentElement.getAttribute('aria-hidden'),'true','Inactive labelled groups must also leave the accessibility tree');
  }
  return Number(slides[0].dataset.bannerSlide);
}

test('legacy markup without the banner keeps poster viewing, downloads, languages and navigation usable', async () => {
  const {dom,window,document,errors}=setup('zh',false,{hash:'#/products',legacyBanner:true});
  assert.equal(document.getElementById('poster-banner'),null);
  assert.equal(document.querySelectorAll('[data-poster-card]').length,53);
  assert.equal(document.getElementById('poster-view').hidden,false);
  document.querySelector('[data-poster-image=poster-001]').click();
  assert.equal(document.getElementById('photo-dialog').open,true);
  assert.equal(document.getElementById('expanded-photo').getAttribute('src'),lightURL('assets/posters/poster-001.webp'));
  const download=document.getElementById('photo-download');
  assert.equal(download.hidden,false);
  assert.equal(download.getAttribute('href'),'assets/posters/poster-001.webp?download=yuanze-poster-001.webp');
  assert.equal(download.download,'yuanze-poster-001.webp');
  document.getElementById('photo-language-toggle').click();
  assert.equal(download.textContent,'Download image');
  assert.equal(document.getElementById('photo-caption').textContent,'Collagen hydrogel mask · Teal');
  await historyChange(window,()=>document.getElementById('close-photo').click());
  assert.equal(document.getElementById('photo-dialog').open,false);
  document.querySelector('[data-product-view=catalog]').click();
  const frame=document.getElementById('catalog-frame'),child=frame.contentWindow;
  assert.equal(frame.getAttribute('src'),'/client/products?showroom=1');
  document.querySelector('.bottom-nav [data-page-link=home]').click();
  assert.equal(document.getElementById('page-home').hidden,false);
  document.querySelector('.bottom-nav [data-page-link=products]').click();
  assert.equal(document.getElementById('poster-view').hidden,false);
  assert.equal(frame.contentWindow,child);
  assert.equal(document.querySelectorAll('[data-poster-card]:not([hidden])').length,window.YuanzeProductPosters.items.length);
  assert.deepEqual(errors,[]);dom.window.close();
});

test('the five banner images load only when selected on the poster page and do not enter the poster catalogue', () => {
  const {dom,window,document,errors,banner}=setup('zh',false,{banner:{}});
  const slides=Array.from(document.querySelectorAll('img[data-banner-slide]'));
  assert.equal(slides.length,5);
  assert.deepEqual(slides.map(image=>image.dataset.bannerSlide),['0','1','2','3','4']);
  assert.deepEqual(slides.map(image=>image.dataset.src),bannerFiles.map(name=>`assets/poster-banners/${name}.webp`));
  assert.equal(slides.some(image=>image.hasAttribute('src')),false);
  assert.equal(window.YuanzeProductPosters.items.length,53);
  banner.advance(18000);
  assert.equal(slides.some(image=>image.hasAttribute('src')),false);
  document.querySelector('.bottom-nav [data-page-link=products]').click();
  assert.equal(activeBanner(document),0);
  assert.equal(document.getElementById('banner-position').textContent,'1 / 5');
  assert.equal(slides[0].getAttribute('src'),lightURL('assets/poster-banners/01-pdrn-capsule-cream.webp',1280));
  assert.equal(slides.slice(1).some(image=>image.hasAttribute('src')),false);
  assert.equal(document.querySelectorAll('[data-poster-card]').length,53);
  assert.equal(document.getElementById('catalog-frame').hasAttribute('src'),false);
  assert.deepEqual(errors,[]);dom.window.close();
});

test('banner rotation waits six seconds, resets after manual selection, wraps and keeps pause across language changes', () => {
  const {dom,window,document,errors,banner}=setup('zh',false,{hash:'#/products',banner:{}});
  const previous=document.getElementById('banner-previous'),next=document.getElementById('banner-next'),toggle=document.getElementById('banner-toggle');
  assert.equal(activeBanner(document),0);
  banner.advance(5999);assert.equal(activeBanner(document),0);
  banner.advance(1);assert.equal(activeBanner(document),1);
  banner.advance(3000);previous.click();assert.equal(activeBanner(document),0);
  banner.advance(5999);assert.equal(activeBanner(document),0);
  banner.advance(1);assert.equal(activeBanner(document),1);
  previous.click();previous.click();assert.equal(activeBanner(document),4);
  assert.equal(document.getElementById('banner-position').textContent,'5 / 5');
  next.click();assert.equal(activeBanner(document),0);
  toggle.click();
  assert.match(toggle.textContent,/继续|播放/);
  banner.advance(60000);assert.equal(activeBanner(document),0);
  const previousLabel=previous.getAttribute('aria-label'),nextLabel=next.getAttribute('aria-label');
  assert(previousLabel);assert(nextLabel);
  document.getElementById('language-toggle').click();
  const current=document.querySelector('img[data-banner-slide="0"]');
  assert.equal(current.alt,window.YuanzeCompanyContent.posterBanners[0].title.en);
  assert.notEqual(previous.getAttribute('aria-label'),previousLabel);
  assert.notEqual(next.getAttribute('aria-label'),nextLabel);
  assert.match(toggle.textContent,/resume|play|continue/i);
  banner.advance(6000);assert.equal(activeBanner(document),0);
  toggle.click();banner.advance(6000);assert.equal(activeBanner(document),1);
  assert.equal(document.getElementById('catalog-frame').hasAttribute('src'),false);
  assert.deepEqual(errors,[]);dom.window.close();
});

test('banner automatic rotation suspends while the tab, banner, page, catalogue or poster dialog is not visible', async () => {
  const {dom,window,document,errors,banner}=setup('zh',false,{hash:'#/products',banner:{}});
  banner.advance(2000);
  banner.setHidden(true);banner.advance(60000);assert.equal(activeBanner(document),0);
  banner.setHidden(false);banner.advance(6000);assert.equal(activeBanner(document),1);
  banner.setVisible(false);banner.advance(60000);assert.equal(activeBanner(document),1);
  banner.setVisible(true);banner.advance(6000);assert.equal(activeBanner(document),2);
  document.querySelector('.bottom-nav [data-page-link=home]').click();
  banner.advance(60000);assert.equal(activeBanner(document),2);
  document.querySelector('.bottom-nav [data-page-link=products]').click();
  banner.advance(6000);assert.equal(activeBanner(document),3);
  document.querySelector('[data-product-view=catalog]').click();
  banner.advance(60000);assert.equal(activeBanner(document),3);
  document.querySelector('[data-product-view=posters]').click();
  banner.advance(6000);assert.equal(activeBanner(document),4);
  document.querySelector('[data-poster-image=poster-001]').click();
  assert.equal(document.getElementById('photo-dialog').open,true);
  banner.advance(60000);assert.equal(activeBanner(document),4);
  await historyChange(window,()=>document.getElementById('close-photo').click());
  assert.equal(document.getElementById('photo-dialog').open,false);
  banner.advance(6000);assert.equal(activeBanner(document),0);
  document.getElementById('banner-toggle').click();
  document.querySelector('.bottom-nav [data-page-link=home]').click();banner.advance(6000);
  document.querySelector('.bottom-nav [data-page-link=products]').click();
  banner.setHidden(true);banner.setHidden(false);banner.setVisible(false);banner.setVisible(true);
  banner.advance(18000);assert.equal(activeBanner(document),0);
  assert.deepEqual(errors,[]);dom.window.close();
});

test('reduced motion starts paused while allowing manual selection and explicit automatic playback', () => {
  const {dom,document,errors,banner}=setup('zh',false,{hash:'#/products',banner:{reducedMotion:true}});
  const toggle=document.getElementById('banner-toggle');
  assert.match(toggle.textContent,/继续|播放/);
  banner.advance(60000);assert.equal(activeBanner(document),0);
  document.getElementById('banner-next').click();assert.equal(activeBanner(document),1);
  banner.advance(60000);assert.equal(activeBanner(document),1);
  toggle.click();banner.advance(6000);assert.equal(activeBanner(document),2);
  assert.deepEqual(errors,[]);dom.window.close();
});

test('a failed banner shows its fallback and users can continue to an intact background', () => {
  const {dom,window,document,errors}=setup('zh',false,{hash:'#/products',banner:{}});
  const first=document.querySelector('img[data-banner-slide="0"]');
  first.dispatchEvent(new window.Event('error'));
  assert.equal(document.getElementById('banner-error').hidden,false);
  assert(first.closest('.image-failed'));
  document.getElementById('banner-next').click();
  assert.equal(activeBanner(document),1);
  assert.equal(document.getElementById('banner-error').hidden,true);
  assert.equal(document.querySelector('img[data-banner-slide="1"]').getAttribute('src'),lightURL('assets/poster-banners/02-body-care-collection.webp',1280));
  assert.equal(document.getElementById('catalog-frame').hasAttribute('src'),false);
  assert.deepEqual(errors,[]);dom.window.close();
});

test('poster landing shows every active thumbnail without loading the catalogue or full artwork', () => {
  const {dom,window,document,errors} = setup('zh',false,{hash:'#/products'});
  const data=window.YuanzeProductPosters, frame=document.getElementById('catalog-frame');
  assert.equal(data.items.length,53);
  assert.equal(document.getElementById('poster-view').hidden,false);
  assert.equal(document.getElementById('catalog-view').hidden,true);
  assert.equal(frame.hasAttribute('src'),false);
  assert.equal(document.querySelectorAll('[data-poster-card]:not([hidden])').length,data.items.length);
  assert.equal(document.querySelectorAll('[data-poster-category]').length,data.categories.length+1);
  assert.match(document.getElementById('poster-count').textContent,new RegExp(String(data.items.length)));
  assert.equal(document.getElementById('expanded-photo').hasAttribute('src'),false);
  for(const item of data.items) {
    const image=document.querySelector(`[data-poster-card="${item.id}"] img`);
    assert.equal(image.getAttribute('src'),lightURL(item.src));
    assert.equal(image.loading,'lazy');
    assert.equal(image.decoding,'async');
    assert.equal(image.alt,item.title.zh);
    assert.equal(document.querySelector(`img[src="${item.src}"]`),null);
  }
  const scripts=Array.from(document.querySelectorAll('script'),script=>script.getAttribute('src'));
  assert(scripts.indexOf('product-posters.js')<scripts.indexOf('preview.js'));
  assert.equal(document.querySelector('script[src="product-posters.js"]').defer,true);
  assert.deepEqual(errors,[]);dom.window.close();
});

test('poster category buttons filter cards, counts and translated labels without loading packaging', () => {
  const {dom,window,document,errors} = setup('zh',false,{hash:'#/products'});
  for(const category of window.YuanzeProductPosters.categories) {
    const button=document.querySelector(`[data-poster-category="${category.id}"]`);
    button.click();
    const items=window.YuanzeProductPosters.items.filter(item=>item.category===category.id);
    assert.equal(window.location.hash,`#/products?category=${category.id}`);
    assert.equal(button.getAttribute('aria-pressed'),'true');
    assert.equal(document.querySelectorAll('[data-poster-category][aria-pressed=true]').length,1);
    assert.deepEqual(Array.from(document.querySelectorAll('[data-poster-card]:not([hidden])'),card=>card.dataset.posterCard),Array.from(items,item=>item.id));
    assert.equal(document.getElementById('poster-count').textContent,`${items.length} 张海报 · 共 ${window.YuanzeProductPosters.items.length} 张`);
  }
  const hash=window.location.hash;
  document.getElementById('language-toggle').click();
  assert.equal(window.location.hash,hash);
  assert.equal(document.querySelector('[data-poster-category=sets]').textContent,'Care sets');
  assert.equal(document.querySelector('[data-poster-category=sets]').getAttribute('aria-pressed'),'true');
  assert.match(document.getElementById('poster-count').textContent,/posters/);
  document.querySelector('[data-poster-category=all]').click();
  assert.equal(document.querySelectorAll('[data-poster-card]:not([hidden])').length,window.YuanzeProductPosters.items.length);
  assert.equal(document.getElementById('catalog-frame').hasAttribute('src'),false);
  assert.deepEqual(errors,[]);dom.window.close();
});

test('poster viewer respects category bounds, keyboard navigation and language while retaining its route', async () => {
  const {dom,window,document,errors} = setup('zh',false,{hash:'#/products'});
  document.querySelector('[data-poster-category=face]').click();
  const items=window.YuanzeProductPosters.items.filter(item=>item.category==='face');
  const dialog=document.getElementById('photo-dialog'), image=document.getElementById('expanded-photo');
  const previous=document.getElementById('previous-poster'), next=document.getElementById('next-poster');
  document.querySelector(`[data-poster-image="${items[0].id}"]`).click();
  assert.equal(dialog.open,true);assert.equal(image.getAttribute('src'),lightURL(items[0].src));assert.equal(previous.disabled,true);
  assert.equal(document.activeElement,document.getElementById('close-photo'));
  next.click();
  assert.equal(image.getAttribute('src'),lightURL(items[1].src));
  const hash=window.location.hash;
  document.getElementById('photo-language-toggle').click();
  assert.equal(dialog.open,true);assert.equal(window.location.hash,hash);
  assert.equal(document.getElementById('photo-caption').textContent,items[1].title.en);
  assert.equal(document.querySelector('[data-poster-category=face]').getAttribute('aria-pressed'),'true');
  assert.equal(previous.textContent,'Previous');
  dialog.dispatchEvent(new window.KeyboardEvent('keydown',{key:'ArrowLeft',bubbles:true}));
  assert.equal(image.getAttribute('src'),lightURL(items[0].src));assert.equal(previous.disabled,true);
  for(let i=1;i<items.length;i++) next.click();
  assert.equal(image.getAttribute('src'),lightURL(items.at(-1).src));assert.equal(next.disabled,true);
  dialog.dispatchEvent(new window.KeyboardEvent('keydown',{key:'ArrowRight',bubbles:true}));
  assert.equal(image.getAttribute('src'),lightURL(items.at(-1).src));
  assert.equal(document.getElementById('poster-position').textContent,`${items.length} / ${items.length}`);
  await historyChange(window,()=>document.getElementById('close-photo').click());
  assert.equal(dialog.open,false);assert.equal(window.location.hash,'#/products?category=face');
  assert.equal(document.activeElement,document.querySelector(`[data-poster-image="${items.at(-1).id}"]`));
  assert.equal(image.hasAttribute('src'),false);
  assert.deepEqual(errors,[]);dom.window.close();
});

test('browser Back and Forward restore poster, category and catalogue without recreating its window', async () => {
  const {dom,window,document,errors} = setup('zh',false,{hash:'#/products'});
  const frame=document.getElementById('catalog-frame'),dialog=document.getElementById('photo-dialog');
  document.querySelector('[data-poster-category=hair]').click();
  const first=document.querySelector('[data-poster-card]:not([hidden]) button');
  first.click();
  const posterHash=window.location.hash;
  document.querySelector('#poster-controls [data-copy=enterCatalog]').click();
  assert.equal(window.location.hash,'#/products/catalog');assert.equal(dialog.open,false);
  const child=frame.contentWindow;child.selectionState='preserved';
  await historyChange(window,()=>window.history.back());
  assert.equal(window.location.hash,posterHash);assert.equal(dialog.open,true);
  assert.equal(document.querySelector('[data-poster-category=hair]').getAttribute('aria-pressed'),'true');
  await historyChange(window,()=>window.history.forward());
  assert.equal(window.location.hash,'#/products/catalog');assert.equal(dialog.open,false);
  assert.equal(frame.contentWindow,child);assert.equal(child.selectionState,'preserved');
  await historyChange(window,()=>window.history.back());
  await historyChange(window,()=>dialog.dispatchEvent(new window.Event('cancel',{cancelable:true})));
  assert.equal(dialog.open,false);assert.equal(window.location.hash,'#/products?category=hair');
  await historyChange(window,()=>window.history.back());
  assert.equal(document.querySelector('[data-poster-category=all]').getAttribute('aria-pressed'),'true');
  await historyChange(window,()=>window.history.forward());
  assert.equal(document.querySelector('[data-poster-category=hair]').getAttribute('aria-pressed'),'true');
  assert.deepEqual(errors,[]);dom.window.close();
});

test('direct catalogue and poster links work, and contact continues directly to the mounted catalogue', () => {
  const {dom,window,document,errors} = setup('en',false,{hash:'#/products/catalog'});
  const frame=document.getElementById('catalog-frame'),child=frame.contentWindow;
  assert.equal(frame.getAttribute('src'),'/client/products?showroom=1');
  assert.equal(document.getElementById('catalog-view').hidden,false);
  assert.equal(document.querySelector('.top-nav [data-page-link=products]').getAttribute('aria-current'),'page');
  document.querySelector('.bottom-nav [data-page-link=contact]').click();
  document.querySelector('[data-copy=continueSelection]').click();
  assert.equal(window.location.hash,'#/products/catalog');assert.equal(frame.contentWindow,child);
  document.getElementById('language-toggle').click();assert.equal(window.location.hash,'#/products/catalog');
  assert.deepEqual(errors,[]);dom.window.close();
  const direct=setup('en',false,{hash:'#/products?category=face&poster=poster-001'});
  assert.equal(direct.document.getElementById('photo-dialog').open,true);
  direct.document.getElementById('close-photo').click();
  assert.equal(direct.window.location.hash,'#/products?category=face');
  assert.equal(direct.document.getElementById('photo-dialog').open,false);
  assert.equal(direct.document.getElementById('catalog-frame').hasAttribute('src'),false);
  direct.dom.window.close();
});

test('new attachment poster deep link opens the body artwork and preserves its English caption and category', () => {
  const hash='#/products?category=body&poster=poster-041';
  const {dom,window,document,errors}=setup('zh',false,{hash});
  const item=window.YuanzeProductPosters.items.find(poster=>poster.id==='poster-041');
  assert(item);assert.equal(item.category,'body');
  assert.equal(document.querySelector('[data-poster-category=body]').getAttribute('aria-pressed'),'true');
  assert.equal(document.querySelector('[data-poster-card=poster-041]').hidden,false);
  assert.equal(document.querySelector('[data-poster-card=poster-001]').hidden,true);
  assert.equal(document.getElementById('photo-dialog').open,true);
  assert.equal(document.getElementById('expanded-photo').getAttribute('src'),lightURL('assets/posters/poster-041.webp'));
  assert.equal(document.getElementById('photo-caption').textContent,'liaose 果酸精油身体磨砂膏');
  assert.equal(document.getElementById('next-poster').disabled,false);
  assert.equal(document.getElementById('catalog-frame').hasAttribute('src'),false);
  document.getElementById('photo-language-toggle').click();
  assert.equal(document.getElementById('photo-caption').textContent,'liaose AHA & essential oil body scrub');
  assert.equal(document.getElementById('expanded-photo').alt,'liaose AHA & essential oil body scrub');
  assert.equal(document.getElementById('expanded-photo').getAttribute('src'),lightURL('assets/posters/poster-041.webp'));
  assert.equal(document.querySelector('[data-poster-category=body]').textContent,'Body care');
  assert.equal(window.location.hash,hash);
  document.getElementById('close-photo').click();
  assert.equal(window.location.hash,'#/products?category=body');
  assert.equal(document.querySelector('[data-poster-category=body]').getAttribute('aria-pressed'),'true');
  assert.equal(document.getElementById('catalog-frame').hasAttribute('src'),false);
  assert.deepEqual(errors,[]);dom.window.close();
});

test('a removed poster deep link cannot load its artwork and still allows browsing retained body posters', () => {
  const {dom,window,document,errors}=setup('zh',false,{hash:'#/products?category=body&poster=poster-028'});
  assert.equal(document.getElementById('poster-view').hidden,false);
  assert.equal(document.querySelector('[data-poster-category=body]').getAttribute('aria-pressed'),'true');
  assert.equal(document.querySelector('[data-poster-card=poster-028]'),null);
  assert.equal(document.getElementById('photo-dialog').open,false);
  assert.equal(document.getElementById('expanded-photo').hasAttribute('src'),false);
  assert.equal(document.querySelector('img[src*="poster-028"]'),null);
  document.querySelector('[data-poster-image=poster-032]').click();
  assert.equal(document.getElementById('photo-dialog').open,true);
  assert.equal(document.getElementById('expanded-photo').getAttribute('src'),lightURL('assets/posters/poster-032.webp'));
  assert.equal(window.location.hash,'#/products?category=body&poster=poster-032');
  document.getElementById('next-poster').click();
  assert.equal(document.getElementById('expanded-photo').getAttribute('src'),lightURL('assets/posters/poster-033.webp'));
  assert.equal(window.location.hash,'#/products?category=body&poster=poster-033');
  assert.equal(document.getElementById('catalog-frame').hasAttribute('src'),false);
  assert.deepEqual(errors,[]);dom.window.close();
});

test('unrecognised poster routes and unavailable artwork leave navigation and packaging accessible', () => {
  const {dom,window,document,errors} = setup('zh',false,{hash:'#/products?category=unknown&poster=missing'});
  assert.equal(document.querySelector('[data-poster-category=all]').getAttribute('aria-pressed'),'true');
  assert.equal(document.getElementById('photo-dialog').open,false);
  const card=document.querySelector('[data-poster-card]');
  card.querySelector('img').dispatchEvent(new window.Event('error'));
  assert.equal(card.querySelector('.poster-image-error').hidden,false);
  card.querySelector('button').click();
  const photo=document.getElementById('expanded-photo');
  photo.dispatchEvent(new window.Event('error'));
  assert.equal(document.getElementById('photo-error').hidden,false);
  document.getElementById('next-poster').click();
  assert.equal(document.getElementById('photo-error').hidden,true);assert.equal(photo.hidden,false);
  document.querySelector('#poster-controls [data-copy=enterCatalog]').click();
  assert.equal(document.getElementById('catalog-frame').getAttribute('src'),'/client/products?showroom=1');
  assert.equal(document.getElementById('photo-dialog').open,false);
  assert.deepEqual(errors,[]);dom.window.close();
});

test('company material preserves the supplied original and maps photos to correct sections', () => {
  const {dom,window,document} = setup();
  assert.equal(window.YuanzeCompanyContent.originalIntroductionEn,original);
  assert.doesNotMatch(window.YuanzeCompanyContent.en.introduction,/FDA-registered|FDA-approved|FDA certified/);
  assert.match(window.YuanzeCompanyContent.en.introduction,/manufacturing management system/);
  assert.match(document.querySelector('[data-photo=showroom] img').src,/assets\/previews\/showroom-1280.webp$/);
  assert.match(document.querySelector('#about [data-photo=reception] img').src,/assets\/previews\/reception-1280.webp$/);
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
    assert.match(document.querySelector(`[data-certificate-image=${id}]`).src,new RegExp(id+'-en-512.webp$'));
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
  assert.match(document.getElementById('expanded-photo').src,/iso22716-en-512.webp$/);
  assert.match(document.getElementById('photo-caption').textContent,/ISO 22716/);
  document.getElementById('close-photo').click();
  assert.equal(dialog.open,false);
  assert.equal(document.activeElement,button);
  assert.equal(document.getElementById('expanded-photo').hasAttribute('src'),false);
  document.querySelector('[data-photo=reception]').click();
  assert.match(document.getElementById('expanded-photo').src,/reception-512.webp$/);
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

test('bottom navigation opens posters first, mounts catalogue on demand and preserves it across all views', () => {
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
  assert.equal(frame.hasAttribute('src'),false);
  assert.equal(document.getElementById('poster-view').hidden,false);
  document.querySelector('[data-copy=enterCatalog]').click();
  assert.equal(window.location.hash,'#/products/catalog');
  assert.equal(frame.getAttribute('src'),'/client/products?showroom=1');
  assert.equal(document.getElementById('poster-view').hidden,true);
  const childWindow=frame.contentWindow;
  childWindow.selectionState={search:'100 mL',page:2,shortlist:['YZ-BC-000001']};
  panel('home').scrollTop=240;
  tab('contact').click();
  assert.equal(panel('products').hidden,true);
  assert.equal(panel('contact').hidden,false);
  tab('products').click();
  assert.equal(frame.contentWindow,childWindow);
  assert.equal(document.getElementById('poster-view').hidden,false);
  document.querySelector('[data-copy=enterCatalog]').click();
  assert.equal(frame.contentWindow.selectionState.search,'100 mL');
  assert.equal(frame.contentWindow.selectionState.page,2);
  assert.deepEqual(frame.contentWindow.selectionState.shortlist,['YZ-BC-000001']);
  assert.equal(panel('home').scrollTop,240);
  window.history.replaceState(null,'','#/home');
  window.dispatchEvent(new window.PopStateEvent('popstate'));
  assert.equal(panel('home').hidden,false);
  assert.equal(document.querySelectorAll('.bottom-nav [aria-current=page]').length,1);
  assert.equal(tab('home').getAttribute('aria-current'),'page');
  assert(document.querySelector('meta[name=robots]').content.includes('noindex'));
  dom.window.close();
});

test('desktop header and mobile bottom navigation share the same independent page state', () => {
  const {dom,window,document,errors} = setup();
  const top = name => document.querySelector('.top-nav [data-page-link='+name+']');
  const bottom = name => document.querySelector('.bottom-nav [data-page-link='+name+']');
  const frame = document.getElementById('catalog-frame');
  top('products').click();
  assert.equal(document.getElementById('page-products').hidden,false);
  assert.equal(top('products').getAttribute('aria-current'),'page');
  assert.equal(bottom('products').getAttribute('aria-current'),'page');
  assert.equal(frame.hasAttribute('src'),false);
  document.querySelector('[data-product-view=catalog]').click();
  assert.equal(top('products').getAttribute('aria-current'),'page');
  assert.equal(bottom('products').getAttribute('aria-current'),'page');
  const child=frame.contentWindow;
  bottom('contact').click();assert.equal(top('contact').getAttribute('aria-current'),'page');
  document.getElementById('inquiry-note').value='Keep this selection';
  document.getElementById('language-toggle').click();
  assert.equal(top('contact').textContent,'Contact');
  assert.equal(document.getElementById('inquiry-note').value,'Keep this selection');
  top('products').click();assert.equal(frame.contentWindow,child);
  top('home').click();
  assert.equal(document.querySelectorAll('[data-page]:not([hidden])').length,1);
  assert.equal(document.getElementById('page-home').querySelectorAll('iframe,#contact').length,0);
  assert.equal(window.location.hash,'#/home');
  assert.deepEqual(errors,[]);dom.window.close();
});

test('production mode removes preview labels and performs one CSRF-protected logout without retries', async () => {
  const calls=[];
  let releaseSession;
  const fetch = async (url,options) => {
    calls.push({url,options});
    if (url==='/api/session') return new Promise(resolve => {releaseSession=()=>resolve({ok:true,status:200,json:async()=>({role:'client',csrf:'fresh-csrf'})});});
    return {ok:true,status:200,json:async()=>({ok:true})};
  };
  const {dom,document,errors} = setup('zh',false,{mode:'production',fetch});
  assert.equal(document.querySelector('.preview-label').hidden,true);
  assert.equal(document.title,'YUANZE · 客户展厅');
  const logout=document.getElementById('showroom-logout');assert.equal(logout.hidden,false);
  logout.click();logout.click();assert.equal(logout.disabled,true);assert.equal(calls.length,1);assert.equal(logout.textContent,'正在退出…');
  releaseSession();await new Promise(resolve=>setImmediate(resolve));
  assert.deepEqual(calls.map(call=>call.url),['/api/session','/api/logout']);
  assert.equal(calls[1].options.method,'POST');assert.equal(calls[1].options.headers['X-CSRF-Token'],'fresh-csrf');
  assert.equal(calls[1].options.body,'{}');assert.equal(calls[1].options.credentials,'same-origin');assert.equal(calls[1].options.redirect,'error');
  assert.equal(logout.disabled,false);assert.equal(document.getElementById('session-message').hidden,true);
  document.getElementById('language-toggle').click();assert.equal(document.title,'YUANZE · Customer showroom');assert.equal(logout.textContent,'Log out');
  assert.deepEqual(errors,[]);dom.window.close();
});

test('logout failures are translated and private server errors are not rendered or retried', async () => {
  const calls=[];let validSession=false;
  const fetch=async(url,options)=>{
    calls.push({url,options});
    if(url==='/api/session')return{ok:true,status:200,json:async()=>({csrf:validSession?'csrf':'',error:'PRIVATE SERVER ERROR'})};
    return{ok:false,status:403,json:async()=>({error:'PRIVATE SERVER ERROR'})};
  };
  const {dom,document,errors}=setup('zh',false,{mode:'production',fetch});
  const logout=document.getElementById('showroom-logout');logout.click();await new Promise(resolve=>setImmediate(resolve));
  assert.deepEqual(calls.map(call=>call.url),['/api/session']);assert.equal(document.getElementById('session-message').hidden,false);
  assert.doesNotMatch(document.body.textContent,/PRIVATE SERVER ERROR/);assert.equal(logout.disabled,false);
  document.getElementById('language-toggle').click();assert.match(document.getElementById('session-message').textContent,/Unable to log out/);
  validSession=true;logout.click();await new Promise(resolve=>setImmediate(resolve));
  assert.deepEqual(calls.map(call=>call.url),['/api/session','/api/session','/api/logout']);
  assert.equal(document.getElementById('session-message').hidden,false);assert.equal(logout.disabled,false);
  assert.deepEqual(errors,[]);dom.window.close();
});

test('preview mode keeps logout unavailable and makes no session requests', () => {
  let requests=0;
  const {dom,document}=setup('en',false,{fetch:async()=>{requests++;throw Error('No session for preview');}});
  assert.equal(document.querySelector('.preview-label').hidden,false);assert.match(document.title,/preview/);
  const logout=document.getElementById('showroom-logout');assert.equal(logout.hidden,true);logout.click();assert.equal(requests,0);
  dom.window.close();
});

test('only the trusted catalogue frame can request Home or fixed top-level login navigation', () => {
  const navigation=[];
  const {dom,window,document,errors}=setup('zh',false,{mode:'production',navigation});
  document.querySelector('.top-nav [data-page-link=products]').click();
  document.querySelector('[data-product-view=catalog]').click();
  const frame=document.getElementById('catalog-frame'),child=frame.contentWindow;
  const send=(origin,source,type,extra={})=>window.dispatchEvent(new window.MessageEvent('message',{origin,source,data:{type,...extra}}));
  send('https://attacker.invalid',child,'yuanze-home');assert.equal(document.getElementById('page-products').hidden,false);
  send('http://localhost',window,'yuanze-home');assert.equal(document.getElementById('page-products').hidden,false);
  send('http://localhost',child,'yuanze-home');assert.equal(document.getElementById('page-home').hidden,false);
  document.querySelector('.top-nav [data-page-link=products]').click();assert.equal(frame.contentWindow,child);
  send('https://attacker.invalid',child,'yuanze-auth-required');send('http://localhost',window,'yuanze-auth-required');assert.deepEqual(navigation,[]);
  send('http://localhost',child,'yuanze-auth-required',{url:'https://attacker.invalid'});assert.deepEqual(navigation,['/login']);
  assert.equal(frame.getAttribute('src'),'/client/products?showroom=1');assert.deepEqual(errors,[]);dom.window.close();
});

test('contact accepts only allowlisted shortlist fields from the catalogue frame and safely copies an enquiry', async () => {
  const {dom,window,document} = setup();
  document.querySelector('.bottom-nav [data-page-link=products]').click();
  document.querySelector('[data-product-view=catalog]').click();
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


test('every company photo, certificate and active poster has a matching download', () => {
  const {dom,window,document,errors}=setup();
  const link=document.getElementById('photo-download');
  for(const button of document.querySelectorAll('[data-photo], [data-certificate]')) {
    button.click();
    const src=document.getElementById('expanded-photo').dataset.original;
    assert.equal(link.getAttribute('href'),src+'?download='+encodeURIComponent(link.download));
    assert.equal(link.hidden,false);
    assert.equal(link.textContent,'下载图片');
    document.getElementById('photo-language-toggle').click();
    assert.equal(link.textContent,'Download image');
    assert.equal(link.getAttribute('href'),document.getElementById('expanded-photo').dataset.original+'?download='+encodeURIComponent(link.download));
    document.getElementById('photo-language-toggle').click();
    document.getElementById('close-photo').click();
  }
  for(const item of window.YuanzeProductPosters.items) {
    window.location.hash='#/products?poster='+encodeURIComponent(item.id);
    window.dispatchEvent(new window.HashChangeEvent('hashchange'));
    if(document.getElementById('expanded-photo').getAttribute('src')!==item.src) {
      document.querySelector('[data-poster-open="'+item.id+'"]')?.click();
    }
    // Download remains the original artwork even when the viewer is a preview.
    assert.equal(link.getAttribute('href'),item.src+'?download='+encodeURIComponent(link.download));
    assert.doesNotMatch(link.getAttribute('href'),/-thumb/);
  }
  assert.deepEqual(errors,[]);
  dom.window.close();
});

test('home does not fetch poster thumbnails, and the gallery loads only nearby visible cards', () => {
  const observers=[];
  const {dom,document,window,errors}=setup('zh',false,{beforeStart(window){
    window.matchMedia=()=>({matches:false});
    window.IntersectionObserver=class {
      constructor(callback,options){this.callback=callback;this.options=options;this.targets=new Set();observers.push(this);}
      observe(target){this.targets.add(target);}
      unobserve(target){this.targets.delete(target);}
    };
  }});
  const cards=Array.from(document.querySelectorAll('[data-poster-card] img'));
  assert.equal(cards.length,53);assert(cards.every(image=>!image.hasAttribute('src')));
  const observer=observers.find(item=>item.options.root?.id==='poster-view');
  assert.equal(observer.targets.size,0);
  document.querySelector('.bottom-nav [data-page-link=products]').click();
  assert.equal(observer.targets.size,53);assert(cards.every(image=>!image.hasAttribute('src')));
  assert.equal(observer.options.rootMargin,'120px 0px');
  observer.callback([{target:cards[0],isIntersecting:true},{target:cards[1],isIntersecting:false}]);
  assert.equal(cards[0].getAttribute('src'),lightURL(window.YuanzeProductPosters.items[0].src));
  assert(cards.slice(1).every(image=>!image.hasAttribute('src')));
  document.querySelector('[data-poster-category=hair]').click();
  observer.callback([{target:cards[1],isIntersecting:true}]);
  assert.equal(cards[1].hasAttribute('src'),false,'a late callback must not load a now-hidden category');
  document.querySelector('.bottom-nav [data-page-link=home]').click();
  observer.callback([{target:cards[2],isIntersecting:true}]);
  assert.equal(cards[2].hasAttribute('src'),false);
  assert.equal(document.getElementById('catalog-frame').hasAttribute('src'),false);
  assert.deepEqual(errors,[]);dom.window.close();
});

test('viewer shows a small preview first, upgrades it safely, and downloads the original', () => {
  const pending=[];
  const {dom,window,document,errors}=setup('zh',false,{hash:'#/products',beforeStart(window){
    window.Image=function(){const image=window.document.createElement('img');pending.push(image);return image;};
  }});
  const posters=window.YuanzeProductPosters.items;
  document.querySelector(`[data-poster-image="${posters[0].id}"]`).click();
  const image=document.getElementById('expanded-photo'), download=document.getElementById('photo-download');
  assert.equal(image.getAttribute('src'),lightURL(posters[0].src));
  assert.equal(pending[0].getAttribute('src'),lightURL(posters[0].src,1280));
  assert.equal(download.getAttribute('href'),posters[0].src+'?download='+encodeURIComponent(download.download));
  document.getElementById('next-poster').click();
  assert.equal(image.getAttribute('src'),lightURL(posters[1].src));
  pending[0].onload();assert.equal(image.getAttribute('src'),lightURL(posters[1].src));
  pending[1].onload();assert.equal(image.src,pending[1].src);
  document.getElementById('photo-language-toggle').click();assert.equal(pending.length,2);
  document.getElementById('photo-dialog').close();pending[1].onload();
  assert.equal(image.hasAttribute('src'),false,'a closed viewer must not restart its image request');
  assert.deepEqual(errors,[]);dom.window.close();
});

test('HD is explicit, preserves the preview on failure, displays actual dimensions and retains language', () => {
  const pending=[];
  const {dom,window,document,errors}=setup('zh',false,{hash:'#/products',beforeStart(window){
    window.Image=function(){const image=window.document.createElement('img');pending.push(image);return image;};
  }});
  const poster=window.YuanzeProductPosters.items[0];
  document.querySelector(`[data-poster-image="${poster.id}"]`).click();
  const shown=document.getElementById('expanded-photo'), button=document.getElementById('photo-original');
  assert.equal(pending.length,1);assert.notEqual(shown.getAttribute('src'),poster.src);
  button.click();assert.equal(pending[1].getAttribute('src'),poster.src);
  assert.equal(pending[0].hasAttribute('src'),false,'HD stops the superseded preview transfer');
  assert.equal(button.textContent,'取消高清加载');assert.match(document.getElementById('photo-original-status').textContent,/正在加载/);
  pending[0].onload();assert.equal(shown.getAttribute('src'),lightURL(poster.src),'older preview cannot replace an HD request');
  pending[1].onerror();assert.notEqual(shown.getAttribute('src'),poster.src);assert.equal(shown.hidden,false);
  assert.equal(button.textContent,'重试高清原图');button.click();const original=pending[2];
  Object.defineProperties(original,{naturalWidth:{value:2400},naturalHeight:{value:1800}});
  original.onload();assert.equal(shown.getAttribute('src'),poster.src);
  assert.match(document.getElementById('photo-original-status').textContent,/2400 × 1800/);
  document.getElementById('photo-language-toggle').click();assert.equal(pending.length,3);
  assert.equal(shown.getAttribute('src'),poster.src);assert.equal(button.textContent,'Back to preview');
  assert.match(document.getElementById('photo-original-status').textContent,/HD original.*2400 × 1800 pixels/);
  button.click();assert.equal(shown.getAttribute('src'),lightURL(poster.src,1280));
  assert.deepEqual(errors,[]);dom.window.close();
});

test('HD cancel, image change, close and language-dependent certificate change reject late events', () => {
  const pending=[];
  const {dom,window,document,errors}=setup('zh',false,{hash:'#/products',beforeStart(window){
    window.Image=function(){const image=window.document.createElement('img');pending.push(image);return image;};
  }});
  const button=document.getElementById('photo-original'), shown=document.getElementById('expanded-photo');
  document.querySelector('[data-poster-image]').click();button.click();const cancelled=pending.at(-1);
  button.click();assert.equal(cancelled.hasAttribute('src'),false);cancelled.onload();
  assert.equal(shown.getAttribute('src'),lightURL(window.YuanzeProductPosters.items[0].src,1280));
  button.click();const stale=pending.at(-1);document.getElementById('next-poster').click();
  const nextSource=shown.getAttribute('src');stale.onload();assert.equal(shown.getAttribute('src'),nextSource);
  button.click();const closed=pending.at(-1);document.getElementById('photo-dialog').close();closed.onload();
  assert.equal(shown.hasAttribute('src'),false);
  document.querySelector('[data-certificate=iso22716]').click();button.click();const zh=pending.at(-1);
  document.getElementById('photo-language-toggle').click();assert.equal(zh.hasAttribute('src'),false);zh.onload();
  assert.match(shown.getAttribute('src'),/iso22716-en-512.webp$/);assert.equal(button.textContent,'View HD original');
  assert.deepEqual(errors,[]);dom.window.close();
});

test('HD timeout keeps a usable preview and attachment click acknowledges request without fetching a blob', () => {
  const pending=[],calls=[];
  const {dom,window,document,errors,banner}=setup('zh',false,{hash:'#/products',banner:{reducedMotion:true},fetch:async (...args)=>{calls.push(args);throw Error('Unexpected download fetch');},beforeStart(window){
    window.Image=function(){const image=window.document.createElement('img');pending.push(image);return image;};
  }});
  document.querySelector('[data-poster-image]').click();document.getElementById('photo-original').click();
  banner.advance(60000);assert.equal(document.getElementById('photo-original').textContent,'重试高清原图');
  assert.equal(document.getElementById('expanded-photo').hidden,false);
  const link=document.getElementById('photo-download'), first=new window.MouseEvent('click',{bubbles:true,cancelable:true});
  link.dispatchEvent(first);assert.equal(first.defaultPrevented,false);
  assert.match(document.getElementById('photo-download-status').textContent,/已发起下载/);
  assert.doesNotMatch(document.getElementById('photo-download-status').textContent,/下载完成|下载成功/);
  const duplicate=new window.MouseEvent('click',{bubbles:true,cancelable:true});link.dispatchEvent(duplicate);assert.equal(duplicate.defaultPrevented,true);
  document.getElementById('photo-language-toggle').click();assert.match(document.getElementById('photo-download-status').textContent,/Download requested/);
  banner.advance(2000);const retry=new window.MouseEvent('click',{bubbles:true,cancelable:true});link.dispatchEvent(retry);assert.equal(retry.defaultPrevented,false);
  assert.equal(calls.length,0);assert.deepEqual(errors,[]);dom.window.close();
});
