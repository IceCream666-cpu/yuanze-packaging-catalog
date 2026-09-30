(() => {
  'use strict';
  const content = window.YuanzeCompanyContent;
  const toggle = document.getElementById('language-toggle');
  const dialog = document.getElementById('photo-dialog');
  const photo = document.getElementById('expanded-photo');
  const photoCaption = document.getElementById('photo-caption');
  const closePhoto = document.getElementById('close-photo');
  let language = 'zh';
  let selectedPhoto = null;
  let photoTrigger = null;
  try { if (localStorage.getItem('yuanze-mobile-preview-language') === 'en') language = 'en'; } catch (_) {}

  function assetFor(id) {
    if (content.images[id]) return content.images[id];
    return content.certificates[id].versions[language];
  }

  function translate() {
    const copy = content[language];
    document.documentElement.lang = language === 'zh' ? 'zh-CN' : 'en';
    document.title = language === 'zh' ? 'YUANZE · 手机客户展厅预览' : 'YUANZE · Mobile showroom preview';
    document.querySelectorAll('[data-copy]').forEach(node => { node.textContent = copy[node.dataset.copy]; });
    document.querySelectorAll('[data-alt]').forEach(node => { node.alt = copy[node.dataset.alt]; });
    document.querySelectorAll('[data-aria]').forEach(node => { node.setAttribute('aria-label', copy[node.dataset.aria]); });
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
  }

  toggle.addEventListener('click', () => {
    language = language === 'zh' ? 'en' : 'zh';
    try { localStorage.setItem('yuanze-mobile-preview-language', language); } catch (_) {}
    translate();
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
  document.querySelectorAll('.bottom-nav a').forEach(link => link.addEventListener('click', () => {
    document.querySelectorAll('.bottom-nav a').forEach(item => item.removeAttribute('aria-current'));
    link.setAttribute('aria-current', 'page');
  }));

  translate();
  if ('IntersectionObserver' in window && !window.matchMedia('(prefers-reduced-motion: reduce)').matches) {
    const observer = new IntersectionObserver(entries => entries.forEach(entry => {
      if (entry.isIntersecting) { entry.target.classList.add('visible'); observer.unobserve(entry.target); }
    }), {threshold:0.08});
    document.querySelectorAll('.reveal').forEach(node => observer.observe(node));
    document.documentElement.classList.add('motion-ready');
  }
})();
