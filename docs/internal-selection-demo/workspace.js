// Presentation-only enhancement. No fetch, credentials, catalogue copies or business writes.
// Existing delegated handlers remain responsible for search, comparison and all mutations.
const paths = {
  grid:'<rect x="3" y="3" width="7" height="7" rx="1.5"/><rect x="14" y="3" width="7" height="7" rx="1.5"/><rect x="3" y="14" width="7" height="7" rx="1.5"/><rect x="14" y="14" width="7" height="7" rx="1.5"/>',
  star:'<path d="m12 3 2.8 5.7 6.2.9-4.5 4.4 1.1 6.2-5.6-3-5.6 3 1.1-6.2L3 9.6l6.2-.9Z"/>',
  search:'<circle cx="10.5" cy="10.5" r="6.5"/><path d="m16 16 4.5 4.5"/>',
  scan:'<path d="M8 3H5a2 2 0 0 0-2 2v3m13-5h3a2 2 0 0 1 2 2v3M3 16v3a2 2 0 0 0 2 2h3m13-5v3a2 2 0 0 1-2 2h-3"/><path d="m7 14 3-3 4 4 2-2 2 3"/><circle cx="15.5" cy="8" r="1"/>',
};
function icon(document, name) {
  const node = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
  for (const [key,value] of Object.entries({viewBox:'0 0 24 24', fill:'none', stroke:'currentColor', 'stroke-width':'1.6','stroke-linecap':'round','stroke-linejoin':'round','aria-hidden':'true',class:'ws-icon'})) node.setAttribute(key,value);
  node.innerHTML = paths[name]; return node;
}
// A number alone can use the user's confirmed ordinary-price = bare-bottle-price rule.
// Ranges, currencies, quantities, accessories, tax/shipping and multiple quotes stay verbatim.
export function simpleBarePrice(value) {
  const match = String(value || '').trim().match(/^普通报价[：:]\s*(?:裸瓶价格?\s*)?(?:[¥￥]\s*)?(\d+(?:\.\d{1,4})?)\s*(?:元(?:\s*[\/／]\s*(?:个|只))?)?$/);
  return match ? match[1] : null;
}
export function installWorkspace(document) {
  if (!document.body.classList.contains('immersive-workspace')) return () => {};
  const win = document.defaultView;
  let queued = false, disposed = false;
  const copy = (zh,en) => document.documentElement.lang.startsWith('en') ? en : zh;
  const addIcon = (node,name) => { if (node && !node.querySelector('.ws-icon')) node.prepend(icon(document,name)); };
  function enhance() {
    queued = false;
    if (disposed) return;
    observer.disconnect(); languageObserver.disconnect();
    addIcon(document.querySelector('nav [data-view="catalog"]'),'grid');
    addIcon(document.querySelector('nav [data-view="favorites"]'),'star');
    const ordinal = document.querySelector('nav [data-view="catalog"] > span:last-child');
    if (ordinal?.textContent === '01') ordinal.hidden = true;
    const searchIcon = document.querySelector('.search-box > span');
    if (searchIcon && !searchIcon.querySelector('svg')) searchIcon.replaceChildren(icon(document,'search'));
    addIcon(document.querySelector('[data-image-search="open"]'),'scan');
    const form = document.querySelector('#searchForm');
    if (form && !form.querySelector('.ws-shortcuts')) {
      const shortcuts = document.createElement('div'); shortcuts.className = 'ws-shortcuts'; shortcuts.dataset.i18nSkip = '';
      const label = document.createElement('span'); label.dataset.wsLabel = 'uses'; shortcuts.append(label);
      for (const [zh,en] of [['精华液','Serum'],['洁面','Cleanser'],['护手霜','Hand cream'],['洗发水','Shampoo'],['沐浴露','Body wash']]) {
        const button = document.createElement('button');
        button.type = 'button'; button.className = 'ws-shortcut'; button.dataset.wsUse = zh; button.dataset.wsEnglish = en;
        button.addEventListener('click', () => {
          const query = form.querySelector('#query');
          query.value = zh;
          query.dispatchEvent(new win.Event('input',{bubbles:true}));
          form.requestSubmit();
        });
        shortcuts.append(button);
      }
      form.append(shortcuts);
    }
    document.querySelectorAll('[data-ws-label="uses"]').forEach(node => { node.textContent = copy('按用途找','Common uses'); });
    document.querySelectorAll('[data-ws-use]').forEach(node => {
      node.textContent = copy(node.dataset.wsUse,node.dataset.wsEnglish);
      node.setAttribute('aria-pressed',String(document.querySelector('#query')?.value === node.dataset.wsUse));
    });
    document.querySelectorAll('.card .favorite').forEach(node => {
      if (!node.querySelector('svg')) node.replaceChildren(icon(document,'star'));
    });
    document.querySelectorAll('.card .quote-preview').forEach(node => {
      if (!node.dataset.wsOriginal) {
        const value = simpleBarePrice(node.textContent);
        if (!value) return;
        node.dataset.wsOriginal = node.textContent;
        node.title = node.textContent;
        const price = document.createElement('div'); price.className = 'ws-price';
        const label = document.createElement('span'); label.dataset.wsPriceLabel = '';
        const strong = document.createElement('strong'); strong.textContent = '¥' + value;
        price.append(label,strong); node.replaceChildren(price);
      }
      const label = node.querySelector('[data-ws-price-label]');
      if (label) label.textContent = copy('裸瓶价格','Bare bottle');
    });
    // Cancel only the old decorative list entrance; leave functional animations untouched.
    document.querySelectorAll('#main .reveal').forEach(node => {
      node.getAnimations?.().forEach(animation => animation.cancel());
    });
    observer.observe(document.querySelector('#main'),{childList:true,subtree:true});
    observer.observe(document.querySelector('#modalBody'),{childList:true,subtree:true});
    languageObserver.observe(document.documentElement,{attributes:true,attributeFilter:['lang']});
  }
  // This changes content, not animation frames. Safari may suspend rAF while its
  // window is behind another app; a microtask also updates background previews.
  const queue = () => {
    if (queued || disposed) return;
    queued = true;
    win.queueMicrotask(enhance);
  };
  const observer = new win.MutationObserver(queue);
  const languageObserver = new win.MutationObserver(queue);
  enhance();
  return () => { disposed=true; observer.disconnect(); languageObserver.disconnect(); };
}
if (typeof document !== 'undefined') installWorkspace(document);
