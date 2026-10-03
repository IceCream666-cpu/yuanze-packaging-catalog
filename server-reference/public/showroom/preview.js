(() => {
  'use strict';
  const content = window.YuanzeCompanyContent;
  const toggle = document.getElementById('language-toggle');
  const dialog = document.getElementById('photo-dialog');
  const photo = document.getElementById('expanded-photo');
  const photoCaption = document.getElementById('photo-caption');
  const closePhoto = document.getElementById('close-photo');
  const frame = document.getElementById('catalog-frame');
  const production = document.documentElement.dataset.mode === 'production';
  const logout = document.getElementById('showroom-logout');
  const sessionMessage = document.getElementById('session-message');
  const pages = ['home', 'products', 'contact'];
  let activePage = '';
  let shortlist = [];
  let inquiryStatus = '';
  let language = 'zh';
  let selectedPhoto = null;
  let photoTrigger = null;
  let loggingOut = false;
  let logoutFailed = false;
  document.querySelector('.preview-label').hidden = production;
  logout.hidden = !production;
  try { if ((localStorage.getItem('yuanze-language') || localStorage.getItem('yuanze-mobile-preview-language')) === 'en') language = 'en'; } catch (_) {}

  function notifyLanguage() {
    if (frame.hasAttribute('src')) frame.contentWindow?.postMessage({type:'yuanze-language', language}, location.origin);
  }

  function renderInquiry() {
    const copy = content[language], box = document.getElementById('inquiry-items');
    box.replaceChildren();
    shortlist.forEach(item => {
      const row = document.createElement('div');
      const code = document.createElement('strong');
      const capacity = document.createElement('span');
      code.textContent = item.productCode;
      capacity.textContent = `${copy.inquiryCapacity}: ${item.capacity || '—'}`;
      row.append(code, capacity); box.append(row);
    });
    document.getElementById('inquiry-empty').hidden = shortlist.length > 0;
    document.getElementById('inquiry-status').textContent = inquiryStatus ? copy[inquiryStatus] : '';
  }

  function showPage(name, focus = false) {
    const next = pages.includes(name) ? name : 'home';
    if (activePage === next) return;
    activePage = next;
    document.querySelectorAll('[data-page]').forEach(panel => { panel.hidden = panel.dataset.page !== next; });
    document.querySelectorAll('[data-page-navigation] [data-page-link]').forEach(link => {
      if (link.dataset.pageLink === next) link.setAttribute('aria-current', 'page');
      else link.removeAttribute('aria-current');
    });
    if (next === 'products' && !frame.hasAttribute('src')) frame.src = frame.dataset.src;
    if (focus) document.getElementById(`page-${next}`).focus({preventScroll:true});
  }

  function navigate(name) {
    const hash = `#/${name}`;
    if (location.hash !== hash) history.pushState(null, '', hash);
    showPage(name, true);
  }

  function assetFor(id) {
    if (content.images[id]) return content.images[id];
    return content.certificates[id].versions[language];
  }

  function translate() {
    const copy = content[language];
    document.documentElement.lang = language === 'zh' ? 'zh-CN' : 'en';
    document.title = production ? copy.title : copy.previewTitle;
    document.querySelectorAll('[data-copy]').forEach(node => { node.textContent = copy[node.dataset.copy]; });
    document.querySelectorAll('[data-alt]').forEach(node => { node.alt = copy[node.dataset.alt]; });
    document.querySelectorAll('[data-aria]').forEach(node => { node.setAttribute('aria-label', copy[node.dataset.aria]); });
    document.querySelectorAll('[data-placeholder]').forEach(node => { node.placeholder = copy[node.dataset.placeholder]; });
    document.querySelectorAll('[data-page]').forEach(node => { node.setAttribute('aria-label',copy[node.dataset.page]); });
    frame.title = copy.products;
    document.querySelectorAll('[data-capability]').forEach(node => { node.textContent = copy.capabilities[Number(node.dataset.capability)]; });
    document.querySelectorAll('[data-certificate-image]').forEach(node => {
      const id = node.dataset.certificateImage;
      const asset = assetFor(id);
      node.src = asset.src;
      node.alt = copy[`${id}Caption`];
      node.width = asset.width;
      node.height = asset.height;
    });
    document.querySelectorAll('[data-certificate-pdf]').forEach(node => { node.href = assetFor(node.dataset.certificatePdf).pdf; });
    document.querySelectorAll('[data-certificate-number]').forEach(node => { node.textContent = content.certificates[node.dataset.certificateNumber].number; });
    document.querySelectorAll('[data-certificate-date]').forEach(node => { node.textContent = `${copy.certificateExpiry} ${content.certificates[node.dataset.certificateDate].expiresAt}`; });
    if (selectedPhoto) {
      photo.src = assetFor(selectedPhoto).src;
      photo.alt = copy[`${selectedPhoto}Alt`] || copy[`${selectedPhoto}Caption`];
      photoCaption.textContent = copy[`${selectedPhoto}Caption`];
      dialog.setAttribute('aria-label', copy[`${selectedPhoto}Caption`]);
    }
    renderInquiry();
    renderSession();
    notifyLanguage();
  }

  function renderSession() {
    logout.disabled = loggingOut;
    logout.textContent = content[language][loggingOut ? 'loggingOut' : 'logout'];
    sessionMessage.hidden = !logoutFailed;
    sessionMessage.textContent = logoutFailed ? content[language].logoutError : '';
  }

  logout.addEventListener('click', async () => {
    if (!production || loggingOut) return;
    loggingOut = true; logoutFailed = false; renderSession();
    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), 15000);
    const options = {credentials:'same-origin', cache:'no-store', redirect:'error', signal:controller.signal, headers:{Accept:'application/json'}};
    try {
      // Obtain current CSRF at the moment of logout. Never store credentials in
      // the bundle, and do not automatically replay the POST after a timeout.
      const sessionResponse = await fetch('/api/session', options);
      if (sessionResponse.status === 401) { location.replace('/login'); return; }
      if (!sessionResponse.ok) throw Error('Session unavailable');
      const session = await sessionResponse.json();
      if (typeof session.csrf !== 'string' || !session.csrf) throw Error('Missing CSRF');
      const response = await fetch('/api/logout', {...options,method:'POST',headers:{...options.headers,'Content-Type':'application/json','X-CSRF-Token':session.csrf},body:'{}'});
      if (response.status === 401) { location.replace('/login'); return; }
      if (!response.ok || (await response.json()).ok !== true) throw Error('Logout unavailable');
      location.replace('/login');
    } catch (_) { logoutFailed = true; }
    finally { clearTimeout(timer); loggingOut = false; renderSession(); }
  });

  function setLanguage(value) {
    language = value;
    try { localStorage.setItem('yuanze-mobile-preview-language', language); localStorage.setItem('yuanze-language', language); } catch (_) {}
    translate();
  }
  toggle.addEventListener('click', () => setLanguage(language === 'zh' ? 'en' : 'zh'));
  frame.addEventListener('load', notifyLanguage);
  window.addEventListener('message', event => {
    if (event.origin !== location.origin || event.source !== frame.contentWindow || !event.data) return;
    if (event.data.type === 'yuanze-home') {navigate('home');return;}
    if (event.data.type === 'yuanze-auth-required') {location.replace('/login');return;}
    if (event.data.type === 'yuanze-language' && ['zh','en'].includes(event.data.language) && language !== event.data.language) setLanguage(event.data.language);
    if (event.data.type === 'yuanze-contact') navigate('contact');
    if (event.data.type === 'yuanze-shortlist' && Array.isArray(event.data.items)) {
      const seen = new Set();
      shortlist = event.data.items.filter(item => item && /^YZ-BC-\d{6,}$/.test(item.productCode) && !seen.has(item.productCode) && seen.add(item.productCode)).slice(0,100).map(item => ({productCode:item.productCode,capacity:typeof item.capacity === 'string' && /^\d+(?:\.\d+)?\s*(?:mL|ml|L|g|kg)$/.test(item.capacity) ? item.capacity : ''}));
      inquiryStatus = ''; renderInquiry();
    }
  });
  document.getElementById('copy-inquiry').addEventListener('click', async () => {
    const copy = content[language];
    const lines = [copy.inquiryTitle, ...shortlist.map(item => `${item.productCode} · ${item.capacity || '—'}`), document.getElementById('inquiry-note').value.trim()].filter(Boolean);
    try { await navigator.clipboard.writeText(lines.join('\n')); inquiryStatus = 'inquiryCopied'; }
    catch (_) { inquiryStatus = 'inquiryCopyFailed'; }
    renderInquiry();
  });
  document.querySelectorAll('[data-photo], [data-certificate]').forEach(button => button.addEventListener('click', () => {
    selectedPhoto = button.dataset.photo || button.dataset.certificate;
    photoTrigger = button;
    photo.src = assetFor(selectedPhoto).src;
    translate();
    dialog.showModal();
    closePhoto.focus();
  }));
  closePhoto.addEventListener('click', () => dialog.close());
  dialog.addEventListener('close', () => {
    photo.removeAttribute('src');
    selectedPhoto = null;
    if (photoTrigger) photoTrigger.focus();
  });
  document.querySelectorAll('[data-page-link]').forEach(link => link.addEventListener('click', event => {
    event.preventDefault(); navigate(link.dataset.pageLink);
  }));
  document.querySelector('[data-copy="aboutLink"]').addEventListener('click', event => {event.preventDefault(); document.getElementById('about').scrollIntoView({behavior:matchMedia('(prefers-reduced-motion: reduce)').matches ? 'auto' : 'smooth'});});
  window.addEventListener('popstate', () => showPage(location.hash.slice(2), true));
  window.addEventListener('hashchange', () => showPage(location.hash.slice(2), true));

  translate();
  showPage(location.hash.slice(2));
  if ('IntersectionObserver' in window && !window.matchMedia('(prefers-reduced-motion: reduce)').matches) {
    const observer = new IntersectionObserver(entries => entries.forEach(entry => {
      if (entry.isIntersecting) { entry.target.classList.add('visible'); observer.unobserve(entry.target); }
    }), {threshold:0.08});
    document.querySelectorAll('.reveal').forEach(node => observer.observe(node));
    document.documentElement.classList.add('motion-ready');
  }
})();
