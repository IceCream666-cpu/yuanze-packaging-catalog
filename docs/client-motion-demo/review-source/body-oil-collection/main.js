import {mountPackagingScene} from '../../src/structure/packaging-scene.js';

const clamp = (value, min, max) => Math.max(min, Math.min(max, value));

export function mountReview(root, {mountScene = mountPackagingScene, fetchImpl = window.fetch.bind(window)} = {}) {
  const $ = selector => root.querySelector(selector);
  const host = $('#model'), stage = $('.review-stage'), controls = $('#controls');
  const opening = $('#opening'), zoom = $('#zoom');
  const status = $('#load-status'), message = $('#load-message'), retry = $('#retry');
  const reference = $('#reference-view'), referenceToggle = $('#reference-toggle');
  let api, request, deadline, attempt = 0, destroyed = false, ready = false, showingReference = false;
  let progress = 0, magnification = 1;
  const listeners = [];
  const listen = (node, event, fn, options) => {
    node.addEventListener(event, fn, options);
    listeners.push(() => node.removeEventListener(event, fn, options));
  };
  const enableControls = () => { controls.disabled = !ready || showingReference; };
  function setProgress(value) {
    progress = clamp(Number(value) || 0, 0, 1);
    opening.value = String(Math.round(progress * 100));
    $('#opening-value').value = `${Math.round(progress * 100)}%`;
    opening.setAttribute('aria-valuetext', `${progress === 0 ? '合拢' : progress === 1 ? '完全展开' : '展开'}，${Math.round(progress * 100)}%`);
    $('#close-model').setAttribute('aria-pressed', String(progress === 0));
    $('#open-model').setAttribute('aria-pressed', String(progress === 1));
    api?.setProgress(progress);
  }
  function setZoom(value) {
    magnification = clamp(Number(value) || 1, .7, 1.7);
    zoom.value = String(magnification);
    $('#zoom-value').value = `${Math.round(magnification * 100)}%`;
    zoom.setAttribute('aria-valuetext', `${Math.round(magnification * 100)}%`);
    api?.setZoom(magnification);
  }
  function showReference(show) {
    showingReference = show;
    reference.hidden = !show;
    stage.dataset.view = show ? 'reference' : 'model';
    host.setAttribute('aria-hidden', String(show));
    referenceToggle.setAttribute('aria-pressed', String(show));
    referenceToggle.textContent = show ? '返回交互模型' : '查看原海报';
    enableControls();
  }
  function release() {
    clearTimeout(deadline);
    request?.abort();
    api?.dispose();
    api = undefined;
  }
  async function load() {
    if (destroyed) return;
    const currentAttempt = ++attempt;
    release();
    request = new AbortController();
    const controller = request;
    const active = () => !destroyed && currentAttempt === attempt;
    const fail = error => {
      if (!active()) return;
      ready = false;
      release();
      enableControls();
      host.setAttribute('aria-busy', 'false');
      status.hidden = false;
      message.textContent = error?.name === 'TimeoutError' ? '模型加载超时。可以重试，或先查看原海报。' : '模型暂时无法加载。请重试，或先查看原海报。';
      retry.hidden = false;
    };
    ready = false; enableControls();
    host.setAttribute('aria-busy', 'true');
    status.hidden = false; retry.hidden = true; message.textContent = '正在准备产品结构…';
    deadline = setTimeout(() => fail(new DOMException('Model preparation timed out', 'TimeoutError')), 300000);
    try {
      const configResponse = await fetchImpl('./review-config.json', {signal: controller.signal, cache: 'no-cache'});
      if (!configResponse.ok) throw new Error('Review configuration is unavailable');
      const {product, design} = await configResponse.json();
      if (!active() || controller.signal.aborted) return;
      if (product?.file !== 'body-oil-collection.glb' || !Array.isArray(product.parts) || !design?.name) throw new Error('Invalid review configuration');
      root.style.setProperty('--paper', design.background);
      root.style.setProperty('--ink', design.ink);
      $('h1').textContent = design.name;
      const modelRequest = {
        signal: controller.signal,
        mark() {},
        promise: fetchImpl(`./${product.file}`, {signal: controller.signal, cache: 'no-cache'}).then(response => {
          if (!response.ok) throw new Error(`Model request failed (${response.status})`);
          return response.arrayBuffer();
        }),
      };
      modelRequest.promise.catch(() => {});
      const mounted = await mountScene(host, {product, design, modelRequest, signal: controller.signal, onError: fail});
      if (!active() || controller.signal.aborted) {mounted?.dispose(); return;}
      api = mounted;
      clearTimeout(deadline);
      api.setProgress(progress); api.setZoom(magnification);
      ready = true; enableControls();
      host.setAttribute('aria-busy', 'false'); status.hidden = true;
    } catch (error) {
      if (active() && !controller.signal.aborted) fail(error);
    }
  }
  listen(opening, 'input', () => setProgress(Number(opening.value) / 100));
  listen(zoom, 'input', () => setZoom(zoom.value));
  listen($('#close-model'), 'click', () => setProgress(0));
  listen($('#open-model'), 'click', () => setProgress(1));
  listen($('#rotate-model'), 'click', () => api?.rotate());
  listen($('#reset-model'), 'click', () => {api?.resetView(); setProgress(0); setZoom(1);});
  listen(referenceToggle, 'click', () => showReference(!showingReference));
  listen(root, 'keydown', event => {if (event.key === 'Escape' && showingReference) showReference(false);});
  listen(retry, 'click', () => {void load();});
  listen(stage, 'wheel', event => {
    if (!ready || showingReference || event.ctrlKey || event.metaKey) return;
    event.preventDefault();
    const pixels = event.deltaY * (event.deltaMode === 1 ? 16 : event.deltaMode === 2 ? stage.clientHeight : 1);
    setProgress(progress + pixels / 1400);
  }, {passive: false});
  const destroy = () => {
    if (destroyed) return;
    destroyed = true; attempt++;
    release(); listeners.forEach(remove => remove());
  };
  listen(window, 'pagehide', destroy);
  void load();
  return {load, destroy};
}

const root = typeof document === 'undefined' ? null : document.querySelector('.review-app');
if (root) mountReview(root);
