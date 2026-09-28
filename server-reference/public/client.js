import {requestJSON} from './api-client.js';

const $ = selector => document.querySelector(selector);
let session = null, items = [], page = 1, pages = 1, busy = false;
let previewItem = null, previewIndex = 0, previousFocus = null;

function imageURL(image) {
  // Customer media is a separate server-side allowlist; never load original paths.
  const value = typeof image?.url === 'string' ? image.url : '';
  return /^\/client-media\/[A-Za-z0-9_-]+\.(?:jpg|jpeg|png|webp)$/.test(value) ? value : '';
}
function capacityLabel(item) {return item.capacity ? `净含量：${item.capacity}` : '净含量：—';}
function showNotice(message = '') {$('#notice').textContent = message; $('#notice').hidden = !message;}
function setBusy(value) {
  busy = value;
  $('#gallery').setAttribute('aria-busy', String(value));
  $('#previous').disabled = value || page <= 1;
  $('#next').disabled = value || page >= pages;
  $('#jumpForm').querySelectorAll('input,button').forEach(el => el.disabled = value);
  $('#retry').disabled = value;
}
function showImageFailure(image, parent) {
  image.hidden = true;
  const note = document.createElement('p');
  note.className = 'image-unavailable';
  note.textContent = '图片暂时无法显示';
  parent.append(note);
}
function loadWithRetry(image, url, onFailure, stillRelevant = () => image.isConnected) {
  let attempts = 0;
  image.addEventListener('error', () => {
    if (attempts >= 3) {onFailure();return;}
    attempts += 1;
    const suffix = `?retry=${attempts}`;
    setTimeout(() => {
      if (stillRelevant()) image.src = url + suffix;
    }, attempts * 1500);
  });
  image.src = url;
}
function render() {
  const fragment = document.createDocumentFragment();
  for (const item of items) {
    const card = document.createElement('article'); card.className = 'gallery-card';
    const button = document.createElement('button'); button.type = 'button'; button.className = 'photo-button';
    button.setAttribute('aria-label', `查看包材图片，${capacityLabel(item)}`);
    const img = document.createElement('img'); img.alt = '包材图片'; img.loading = 'lazy'; img.decoding = 'async';
    loadWithRetry(img, item.images[0].url, () => showImageFailure(img, button));
    button.append(img);
    if (item.images.length > 1) {const count = document.createElement('span');count.className = 'image-count';count.textContent = `${item.images.length} 张图片`;button.append(count);}
    button.addEventListener('click', () => openPreview(item, button));
    const caption = document.createElement('p');caption.className = 'capacity';caption.textContent = capacityLabel(item);
    card.append(button, caption);fragment.append(card);
  }
  $('#gallery').replaceChildren(fragment);
  $('#empty').hidden = items.length !== 0;
  $('#pagination').hidden = pages <= 1 || items.length === 0;
  $('#pageStatus').textContent = `${page} / ${pages}`;
  $('#pageNumber').value = page;$('#pageNumber').max = pages;
}
async function loadCatalog(target = page, scroll = false) {
  if (busy) return;
  setBusy(true);showNotice();$('#retry').hidden = true;
  $('#catalogStatus').textContent = '正在加载…';
  try {
    const data = await requestJSON(`/api/client/catalog?page=${target}&pageSize=24`);
    if (!Array.isArray(data.items) || !Number.isInteger(data.page) || data.page < 1 || !Number.isInteger(data.pages) || data.pages < 1) throw Error('invalid catalogue');
    items = data.items.map(item => ({
      capacity: typeof item.capacity === 'string' ? item.capacity : '',
      images: Array.isArray(item.images) ? item.images.map(image => ({url:imageURL(image)})).filter(image => image.url) : [],
    })).filter(item => item.images.length > 0);
    page = data.page;pages = data.pages;render();
    $('#catalogStatus').textContent = '';
    if (scroll) $('#galleryMain').scrollIntoView({behavior:matchMedia('(prefers-reduced-motion: reduce)').matches ? 'auto' : 'smooth',block:'start'});
  } catch (error) {
    if (error.status === 401) {location.replace('/login');return;}
    $('#catalogStatus').textContent = '';
    showNotice('暂时无法加载包材图片，请检查网络后重试。');$('#retry').hidden = false;
  } finally {setBusy(false);}
}
function updatePreview() {
  const image = $('#previewImage');image.hidden = false;$('#previewError').hidden = true;
  const currentImage = image.cloneNode();
  currentImage.removeAttribute('src');
  image.replaceWith(currentImage);
  const url = previewItem.images[previewIndex].url;
  loadWithRetry(currentImage, url, () => {currentImage.hidden = true;$('#previewError').hidden = false;},
    () => previewItem && $('#previewImage') === currentImage && currentImage.isConnected);
  $('#previewCapacity').textContent = capacityLabel(previewItem);
  $('#imageStatus').textContent = `${previewIndex + 1} / ${previewItem.images.length}`;
  $('#imagePrevious').disabled = previewIndex === 0;
  $('#imageNext').disabled = previewIndex === previewItem.images.length - 1;
  $('.preview-controls').hidden = previewItem.images.length <= 1;
}
function openPreview(item, source) {previewItem = item;previewIndex = 0;previousFocus = source;updatePreview();$('#preview').showModal();}
function moveImage(delta) {if (!previewItem) return;previewIndex = Math.max(0,Math.min(previewItem.images.length - 1,previewIndex + delta));updatePreview();}
$('#closePreview').addEventListener('click', () => $('#preview').close());
$('#preview').addEventListener('close', () => {$('#previewImage').removeAttribute('src');previewItem = null;previousFocus?.focus();});
$('#preview').addEventListener('click', event => {if (event.target === $('#preview')) $('#preview').close();});
$('#preview').addEventListener('keydown', event => {if (event.key === 'ArrowLeft' || event.key === 'ArrowRight') {event.preventDefault();moveImage(event.key === 'ArrowLeft' ? -1 : 1);}});
$('#imagePrevious').addEventListener('click', () => moveImage(-1));
$('#imageNext').addEventListener('click', () => moveImage(1));
$('#previous').addEventListener('click', () => {if (page > 1) loadCatalog(page - 1,true);});
$('#next').addEventListener('click', () => {if (page < pages) loadCatalog(page + 1,true);});
$('#jumpForm').addEventListener('submit', event => {event.preventDefault();const target = Number($('#pageNumber').value);if (Number.isInteger(target) && target >= 1 && target <= pages && target !== page) loadCatalog(target,true);});
$('#retry').addEventListener('click', () => session ? loadCatalog() : init());
$('#logout').addEventListener('click', async () => {
  $('#logout').disabled = true;showNotice();
  try {
    if (!session) session = await requestJSON('/api/session');
    await requestJSON('/api/logout',{method:'POST',headers:{'Content-Type':'application/json','X-CSRF-Token':session.csrf || ''},body:'{}'});
    location.replace('/login');
  } catch (error) {if (error.status === 401) location.replace('/login');else showNotice('暂时无法退出，请检查网络后重试。');}
  finally {$('#logout').disabled = false;}
});
async function init() {
  $('#retry').hidden = true;showNotice();
  try {
    session = await requestJSON('/api/session');
    if (!['client','admin'].includes(session.role)) {location.replace('/');return;}
    await loadCatalog();
  } catch (error) {
    if (error.status === 401) {location.replace('/login');return;}
    session = null;$('#catalogStatus').textContent = '';showNotice('暂时无法打开页面，请检查网络后重试。');$('#retry').hidden = false;
  }
}
init();
