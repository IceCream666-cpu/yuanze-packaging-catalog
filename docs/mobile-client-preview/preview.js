(() => {
  'use strict';
  const content = window.YuanzeCompanyContent;
  const posters = window.YuanzeProductPosters || {categories:[], items:[]};
  const toggle = document.getElementById('language-toggle');
  const dialog = document.getElementById('photo-dialog');
  const photo = document.getElementById('expanded-photo');
  const photoCaption = document.getElementById('photo-caption');
  const closePhoto = document.getElementById('close-photo');
  const frame = document.getElementById('catalog-frame');
  const posterView = document.getElementById('poster-view');
  const catalogView = document.getElementById('catalog-view');
  const posterGrid = document.getElementById('poster-grid');
  const posterCategories = document.getElementById('poster-categories');
  const posterControls = document.getElementById('poster-controls');
  const posterPosition = document.getElementById('poster-position');
  const previousPoster = document.getElementById('previous-poster');
  const nextPoster = document.getElementById('next-poster');
  const photoError = document.getElementById('photo-error');
  const production = document.documentElement.dataset.mode === 'production';
  const logout = document.getElementById('showroom-logout');
  const sessionMessage = document.getElementById('session-message');
  const pages = ['home', 'products', 'contact'];
  let activeRoute = null;
  let shortlist = [];
  let inquiryStatus = '';
  let language = 'zh';
  let selectedPhoto = null;
  let selectedPoster = null;
  let posterCategory = 'all';
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

  function format(key, values) {
    return content[language][key].replace(/\{(\w+)\}/g, (_, key) => values[key]);
  }

  function filteredPosters() {
    return posters.items.filter(item => posterCategory === 'all' || item.category === posterCategory);
  }

  function posterRoute(category = posterCategory, id = '') {
    const query = new window.URLSearchParams();
    if (category !== 'all') query.set('category', category);
    if (id) query.set('poster', id);
    const suffix = query.toString();
    return `products${suffix ? `?${suffix}` : ''}`;
  }

  // Keep poster state in the URL so Back/Forward can restore category and viewer.
  // The catalogue remains mounted when its subpage is hidden.
  function showPage(route, focus = false) {
    if (activeRoute === route) return;
    activeRoute = route;
    const [path, query = ''] = route.split('?');
    const next = path === 'products/catalog' ? 'products' : pages.includes(path) ? path : 'home';
    const catalog = path === 'products/catalog';
    document.querySelectorAll('[data-page]').forEach(panel => { panel.hidden = panel.dataset.page !== next; });
    document.querySelectorAll('[data-page-navigation] [data-page-link]').forEach(link => {
      if (link.dataset.pageLink === next) link.setAttribute('aria-current', 'page');
      else link.removeAttribute('aria-current');
    });
    posterView.hidden = catalog;
    catalogView.hidden = !catalog;
    document.querySelectorAll('[data-product-view]').forEach(link => {
      if (link.dataset.productView === (catalog ? 'catalog' : 'posters')) link.setAttribute('aria-current', 'page');
      else link.removeAttribute('aria-current');
    });
    if (next === 'products' && catalog && !frame.hasAttribute('src')) frame.src = frame.dataset.src;
    let poster = null;
    if (next === 'products' && !catalog) {
      const params = new window.URLSearchParams(query);
      posterCategory = posters.categories.some(category => category.id === params.get('category')) ? params.get('category') : 'all';
      renderPosters();
      poster = filteredPosters().find(item => item.id === params.get('poster')) || null;
    }
    const closingPoster = selectedPoster && !poster;
    if (poster) {
      selectedPhoto = null;
      selectedPoster = poster.id;
      photoTrigger = posterGrid.querySelector(`[data-poster-image="${poster.id}"]`);
      updatePhoto();
      if (!dialog.open) { dialog.showModal(); closePhoto.focus(); }
    } else if (selectedPoster) {
      selectedPoster = null;
      if (dialog.open) dialog.close();
    }
    if (focus && !dialog.open && (!closingPoster || !photoTrigger || photoTrigger.closest('[hidden]'))) document.getElementById(`page-${next}`).focus({preventScroll:true});
  }

  function navigate(route, options = {}) {
    const hash = `#/${route}`;
    if (location.hash !== hash) history[options.replace ? 'replaceState' : 'pushState'](options.state || null, '', hash);
    showPage(route, !options.keepFocus);
  }

  function initializePosters() {
    [{id:'all'}, ...posters.categories].forEach(category => {
      const button = document.createElement('button');
      button.type = 'button'; button.dataset.posterCategory = category.id;
      button.addEventListener('click', () => navigate(posterRoute(category.id), {keepFocus:true}));
      posterCategories.append(button);
    });
    posters.items.forEach(item => {
      const card = document.createElement('article');
      card.className = 'poster-card'; card.dataset.posterCard = item.id;
      const button = document.createElement('button');
      button.type = 'button'; button.className = 'poster-card-button'; button.dataset.posterImage = item.id;
      const image = document.createElement('img');
      image.src = item.thumbnail; image.width = item.width; image.height = item.height;
      image.loading = 'lazy'; image.decoding = 'async';
      const details = document.createElement('span'); details.className = 'poster-card-details';
      const title = document.createElement('strong'); title.dataset.posterTitle = item.id;
      const action = document.createElement('span'); action.dataset.copy = 'posterView';
      const error = document.createElement('span'); error.className = 'poster-image-error'; error.dataset.copy = 'posterImageError'; error.hidden = true;
      image.addEventListener('error', () => { image.hidden = true; error.hidden = false; });
      details.append(title, action); button.append(image, error, details); card.append(button); posterGrid.append(card);
      button.addEventListener('click', () => {
        photoTrigger = button;
        navigate(posterRoute(posterCategory, item.id), {state:{yuanzePosterEntry:true}});
      });
    });
  }

  function renderPosters() {
    const visible = filteredPosters();
    posterCategories.querySelectorAll('button').forEach(button => {
      const id = button.dataset.posterCategory;
      button.textContent = id === 'all' ? content[language].allPosters : posters.categories.find(category => category.id === id)[language];
      button.setAttribute('aria-pressed', String(id === posterCategory));
    });
    posters.items.forEach(item => {
      const card = document.querySelector(`[data-poster-card="${item.id}"]`);
      card.hidden = posterCategory !== 'all' && item.category !== posterCategory;
      card.querySelector('strong').textContent = item.title[language];
      card.querySelector('img').alt = item.title[language];
      card.querySelector('button').setAttribute('aria-label', format('posterOpen', {title:item.title[language]}));
    });
    document.getElementById('poster-count').textContent = format('posterCount', {count:visible.length, total:posters.items.length});
  }

  function updatePhoto() {
    posterControls.hidden = !selectedPoster;
    posterPosition.hidden = !selectedPoster;
    dialog.classList.toggle('poster-dialog', Boolean(selectedPoster));
    const poster = posters.items.find(item => item.id === selectedPoster);
    const asset = poster || (selectedPhoto ? assetFor(selectedPhoto) : null);
    if (!asset) return;
    // Avoid restarting an image request when the language alone changes.
    if (photo.getAttribute('src') !== asset.src) {
      photoError.hidden = true; photo.hidden = false; photo.src = asset.src;
    }
    photo.alt = poster ? poster.title[language] : content[language][`${selectedPhoto}Alt`] || content[language][`${selectedPhoto}Caption`];
    photoCaption.textContent = poster ? poster.title[language] : content[language][`${selectedPhoto}Caption`];
    dialog.setAttribute('aria-label', photoCaption.textContent);
    if (poster) {
      const visible = filteredPosters(), index = visible.findIndex(item => item.id === selectedPoster);
      posterPosition.textContent = format('posterPosition', {current:index + 1, total:visible.length});
      previousPoster.disabled = index <= 0;
      nextPoster.disabled = index >= visible.length - 1;
    }
  }

  function movePoster(step) {
    const visible = filteredPosters(), index = visible.findIndex(item => item.id === selectedPoster);
    const item = visible[index + step];
    if (selectedPoster && item) navigate(posterRoute(posterCategory, item.id), {replace:true, keepFocus:true, state:history.state});
  }

  function closeViewer() {
    if (!selectedPoster) { dialog.close(); return; }
    if (history.state?.yuanzePosterEntry) history.back();
    else navigate(posterRoute(), {replace:true, keepFocus:true});
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
    frame.title = copy.catalogTab;
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
    renderPosters();
    updatePhoto();
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
  document.getElementById('photo-language-toggle').addEventListener('click', () => setLanguage(language === 'zh' ? 'en' : 'zh'));
  frame.addEventListener('load', notifyLanguage);
  window.addEventListener('message', event => {
    if (!frame.hasAttribute('src') || event.origin !== location.origin || event.source !== frame.contentWindow || !event.data) return;
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
    selectedPoster = null;
    photoTrigger = button;
    updatePhoto();
    dialog.showModal();
    closePhoto.focus();
  }));
  closePhoto.addEventListener('click', closeViewer);
  dialog.addEventListener('cancel', event => { event.preventDefault(); closeViewer(); });
  dialog.addEventListener('keydown', event => {
    if (!selectedPoster || !['ArrowLeft','ArrowRight'].includes(event.key)) return;
    event.preventDefault(); movePoster(event.key === 'ArrowLeft' ? -1 : 1);
  });
  previousPoster.addEventListener('click', () => movePoster(-1));
  nextPoster.addEventListener('click', () => movePoster(1));
  photo.addEventListener('error', () => { photo.hidden = true; photoError.hidden = false; });
  dialog.addEventListener('close', () => {
    photo.removeAttribute('src');
    selectedPhoto = null;
    selectedPoster = null;
    if (photoTrigger && !photoTrigger.closest('[hidden]')) photoTrigger.focus();
  });
  document.querySelectorAll('[data-page-link]').forEach(link => link.addEventListener('click', event => {
    event.preventDefault(); navigate(link.dataset.pageLink === 'products' ? posterRoute() : link.dataset.pageLink);
  }));
  document.querySelector('[data-copy="aboutLink"]').addEventListener('click', event => {event.preventDefault(); document.getElementById('about').scrollIntoView({behavior:matchMedia('(prefers-reduced-motion: reduce)').matches ? 'auto' : 'smooth'});});
  window.addEventListener('popstate', () => showPage(location.hash.slice(2), true));
  window.addEventListener('hashchange', () => showPage(location.hash.slice(2), true));

  initializePosters();
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
