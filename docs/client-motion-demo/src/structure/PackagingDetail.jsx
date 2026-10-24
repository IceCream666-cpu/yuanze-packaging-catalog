import {PACKAGING_PRODUCTS} from './packaging-products.js';
import featured from '../featured.json';
import React, { useEffect, useRef, useState } from 'react';
import { ArrowDown, ArrowLeft, Heart, Focus, Image as ImageIcon, RotateCcw, RotateCw } from 'lucide-react';
import './packaging-detail.css';

let animationTask;

function loadAnimation(signal) {
  if (window.gsap && window.ScrollTrigger) return Promise.resolve();
  if (!animationTask || animationTask.signal.aborted) {
    const task = {signal};
    animationTask = task;
    task.promise = (async () => {
      for (const [globalName, file] of [['gsap', 'gsap.min.js'], ['ScrollTrigger', 'ScrollTrigger.min.js']]) {
        if (signal.aborted) throw signal.reason;
        if (window[globalName]) continue;
        await new Promise((resolve, reject) => {
          const script = document.createElement('script');
          const finish = error => {
            clearTimeout(timer);
            signal.removeEventListener('abort', cancelled);
            script.onload = script.onerror = null;
            if (error) {script.remove(); reject(error);} else resolve();
          };
          const cancelled = () => finish(signal.reason);
          const timer = setTimeout(() => finish(new Error(`Loading ${file} timed out`)), 15000);
          script.src = import.meta.env.BASE_URL + 'assets/packaging/' + file;
          script.onload = () => finish(window[globalName] ? null : new Error(`Cannot initialize ${file}`));
          script.onerror = () => finish(new Error(`Cannot load ${file}`));
          signal.addEventListener('abort', cancelled, {once: true});
          document.head.append(script);
        });
      }
      if (signal.aborted) throw signal.reason;
      window.gsap.registerPlugin(window.ScrollTrigger);
    })().catch(error => {if (animationTask === task) animationTask = undefined; throw error;});
  }
  return animationTask.promise;
}

const PRESETS = [
  { progress: 0, label: ['合拢', 'Closed'] },
  { progress: .5, label: ['半展开', 'Half open'] },
  { progress: 1, label: ['完全展开', 'Exploded'] },
];

function stageFor(progress) {
  if (progress < .07) return 0;
  if (progress < .94) return 1;
  return 2;
}

export default function PackagingDetail({ item, lang, onClose, onOriginal, onFavorite, saved, logo, getModelRequest, getSceneModule }) {
  const zh = lang === 'zh';
  const product = PACKAGING_PRODUCTS[item.id];
  const featuredDesign = featured.find(value => value.id === item.id);
  // Ivory print remains readable when it leaves Woodland's black label.
  const design = item.id === 'poster-042' ? {...featuredDesign, background:'#76513b', ink:'#fff0db', swatch:['#ead5bb','#241e1a']} : featuredDesign;
  const PARTS = product.parts;
  const languageIndex = zh ? 0 : 1;
  const rootRef = useRef(null);
  const scrollRef = useRef(null);
  const trackRef = useRef(null);
  const hostRef = useRef(null);
  const rangeRef = useRef(null);
  const numberRef = useRef(null);
  const apiRef = useRef(null);
  const triggerRef = useRef(null);
  const updateRef = useRef(null);
  const progressRef = useRef(0);
  const stageRef = useRef(0);
  const [stage, setStage] = useState(0);
  const [selected, setSelected] = useState(null);
  const [ready, setReady] = useState(false);
  const [failed, setFailed] = useState(false);
  const [manualOnly, setManualOnly] = useState(false);
  const [retry, setRetry] = useState(0);
  const [reducedMotion, setReducedMotion] = useState(() => window.matchMedia('(prefers-reduced-motion: reduce)').matches);

  useEffect(() => {rootRef.current?.querySelector('button')?.focus({preventScroll: true});}, []);

  useEffect(() => {
    const media = window.matchMedia('(prefers-reduced-motion: reduce)');
    const changed = event => setReducedMotion(event.matches);
    media.addEventListener('change', changed);
    return () => media.removeEventListener('change', changed);
  }, []);

  useEffect(() => {
    let active = true;
    let api;
    let context;
    let frame;
    let failedDuringMount = false;
    let resizeTimer;
    let resizeProgress = null;
    let refreshProgress = null;
    let refreshing = false;
    const controller = new AbortController();
    const modelRequest = getModelRequest?.();
    const mark = phase => modelRequest?.mark(phase);
    let initializationTimer;
    setReady(false);
    setFailed(false);
    setManualOnly(reducedMotion);
    setSelected(null);

    const update = (value, force = false) => {
      if (!active || failedDuringMount || (!force && (refreshing || resizeProgress !== null))) return;
      const progress = Math.max(0, Math.min(1, value));
      progressRef.current = progress;
      api?.setProgress(progress);
      const percent = Math.round(progress * 100);
      if (rangeRef.current) {
        rangeRef.current.value = String(percent);
        rangeRef.current.style.setProperty('--progress', `${percent}%`);
      }
      if (numberRef.current) numberRef.current.textContent = String(percent);
      const nextStage = stageFor(progress);
      if (nextStage !== stageRef.current) {
        stageRef.current = nextStage;
        setStage(nextStage);
      }
    };
    updateRef.current = update;
    update(0);
    scrollRef.current?.scrollTo({ top: 0, behavior: 'instant' });

    const restoreProgressAfterRefresh = trigger => {
      if (!active || failedDuringMount) return;
      const retained = resizeProgress ?? refreshProgress ?? progressRef.current;
      const top = trigger.start + (trigger.end - trigger.start) * retained;
      scrollRef.current?.scrollTo({ top, behavior: 'instant' });
      trigger.update();
      trigger.getTween()?.progress(1);
      trigger.animation?.progress(retained);
      update(retained, true);
      refreshProgress = null;
      refreshing = false;
    };

    // Capture the visible stage before ScrollTrigger recomputes a new scroll range.
    // Keeping scrollTop alone would change the opening percentage after a resize.
    const handleResize = () => {
      if (!active || !triggerRef.current) return;
      if (resizeProgress === null) resizeProgress = progressRef.current;
      clearTimeout(resizeTimer);
      resizeTimer = setTimeout(() => {
        if (!active || !triggerRef.current) return;
        triggerRef.current.refresh();
        restoreProgressAfterRefresh(triggerRef.current);
        resizeProgress = null;
      }, 140);
    };
    window.addEventListener('resize', handleResize, true);

    const fail = error => {
      if (!active || failedDuringMount) return;
      failedDuringMount = true;
      clearTimeout(initializationTimer);
      controller.abort(error);
      modelRequest?.abort(error);
      setFailed(true);
      setReady(false);
      cancelAnimationFrame(frame);
      clearTimeout(resizeTimer);
      context?.revert();
      context = null;
      triggerRef.current = null;
      const failedApi = api;
      api = null;
      apiRef.current = null;
      failedApi?.dispose();
      console.error('Packaging preview unavailable', error);
    };

    initializationTimer = setTimeout(() => fail(new DOMException('Model preparation timed out', 'TimeoutError')), 60000);
    // Animation is optional: never hold the GLB or first frame behind its scripts.
    const animation = reducedMotion ? Promise.resolve(false) : loadAnimation(controller.signal).then(() => {
      mark('animationReady'); return true;
    }, () => false);
    (async () => {
      try {
        const { mountPackagingScene } = await (getSceneModule ? getSceneModule() : import('./packaging-scene.js'));
        if (!active || failedDuringMount) return;
        mark('sceneModule');
        const mountedApi = await mountPackagingScene(hostRef.current, {
          modelRequest, product, design, signal: controller.signal,
          onError: fail,
          onReady: () => {if (active && !failedDuringMount) {clearTimeout(initializationTimer); setReady(true);}},
        });
        if (!active || failedDuringMount) { mountedApi?.dispose(); return; }
        api = mountedApi;
        apiRef.current = api;
        update(0);

        const animationAvailable = await animation;
        if (!active || failedDuringMount) return;
        if (animationAvailable) {
          // Preserve a manual selection made while the animation scripts loaded.
          const retainedProgress = progressRef.current;
          context = window.gsap.context(() => {
            const clock = { progress: 0 };
            const tween = window.gsap.to(clock, {
              progress: 1,
              ease: 'none',
              onUpdate: () => update(clock.progress),
              scrollTrigger: {
                trigger: trackRef.current,
                scroller: scrollRef.current,
                start: 'top top',
                end: 'bottom bottom',
                scrub: .22,
                invalidateOnRefresh: true,
                onRefreshInit: () => {
                  refreshProgress = resizeProgress ?? progressRef.current;
                  refreshing = true;
                },
                onRefresh: restoreProgressAfterRefresh,
              },
            });
            triggerRef.current = tween.scrollTrigger;
          }, rootRef);
          frame = requestAnimationFrame(() => {
            if (!active || failedDuringMount || !triggerRef.current) return;
            resizeProgress = retainedProgress;
            triggerRef.current.refresh();
            restoreProgressAfterRefresh(triggerRef.current);
            resizeProgress = null;
          });
        } else {
          setManualOnly(true);
        }
      } catch (error) {
        fail(error);
      }
    })();

    return () => {
      active = false;
      clearTimeout(initializationTimer);
      controller.abort();
      modelRequest?.abort();
      cancelAnimationFrame(frame);
      clearTimeout(resizeTimer);
      window.removeEventListener('resize', handleResize, true);
      context?.revert();
      api?.dispose();
      apiRef.current = null;
      triggerRef.current = null;
      updateRef.current = null;
    };
  }, [item.id, reducedMotion, retry, getModelRequest, getSceneModule]);

  function jumpTo(value, smooth = true) {
    const progress = Math.max(0, Math.min(1, value));
    const trigger = triggerRef.current;
    if (!trigger || manualOnly || reducedMotion) {
      updateRef.current?.(progress);
      return;
    }
    const top = trigger.start + (trigger.end - trigger.start) * progress;
    scrollRef.current?.scrollTo({ top, behavior: smooth ? 'smooth' : 'instant' });
    if (!smooth) {
      trigger.update();
      trigger.getTween()?.progress(1);
      updateRef.current?.(progress);
    }
  }

  function choosePart(key) {
    const next = selected === key ? null : key;
    setSelected(next);
    if (next && progressRef.current < .7) jumpTo(1);
    apiRef.current?.focusPart(next);
  }

  function resetView() {
    apiRef.current?.resetView();
    apiRef.current?.focusPart(null);
    setSelected(null);
  }

  function viewBottom() {
    apiRef.current?.viewBottom();
    setSelected(null);
  }

  const activePart = PARTS.find(part => part.key === selected);
  const controlsDisabled = !ready || failed;

  return (
    <div ref={rootRef} className={`packaging-detail ${item.id === 'poster-071' ? 'packaging-detail--pump' : item.id === 'poster-039' ? 'packaging-detail--pdrn' : item.id === 'poster-049' ? 'packaging-detail--moisture' : item.id === 'poster-042' ? 'packaging-detail--woodland' : item.id === 'poster-051' ? 'packaging-detail--pure' : ''} ${manualOnly ? 'packaging-detail--manual' : ''} ${failed ? 'packaging-detail--failed' : ''}`} lang={zh ? 'zh-CN' : 'en'} style={['poster-071', 'poster-039', 'poster-049', 'poster-042', 'poster-051'].includes(item.id) ? {'--pack-paper':design.background,'--pack-ink':design.ink,'--pack-muted':design.ink+'ba','--pack-hairline':design.ink+'4a','--pack-accent':design.swatch[0]} : undefined}>
      <header className="packaging-header">
        <button className="packaging-back" onClick={onClose}>
          <ArrowLeft size={18} aria-hidden="true" />
          <span>{zh ? '返回产品' : 'Collection'}</span>
        </button>
        <div className="packaging-logo" aria-label="YUANZE 源泽"><img src={logo} alt="" /><span>yuanze</span></div>
        <div className="packaging-header-actions">
          <button onClick={onOriginal} aria-label={zh ? '查看原海报' : 'View original poster'}><ImageIcon size={17} aria-hidden="true" /><span>{zh ? '原海报' : 'Poster'}</span></button>
          <button onClick={onFavorite} aria-pressed={saved} aria-label={saved ? (zh ? '取消收藏' : 'Remove from saved') : (zh ? '收藏产品' : 'Save product')}>
            <Heart size={17} fill={saved ? 'currentColor' : 'none'} aria-hidden="true" />
            <span>{saved ? (zh ? '已收藏' : 'Saved') : (zh ? '收藏' : 'Save')}</span>
          </button>
        </div>
      </header>

      <div className="packaging-scroll" ref={scrollRef} tabIndex={0} aria-label={zh ? '产品结构展示；向下滚动展开，向上滚动合拢' : 'Product structure; scroll down to open and up to close'}>
        <div className="packaging-track" ref={trackRef}>
          <section className="packaging-stage" aria-labelledby="packaging-title">
            <div className="packaging-heading">
              <h1 id="packaging-title">{design.name.split(' ').map((word,i) => <React.Fragment key={i}>{i > 0 && ' '}<span className={i > 0 ? 'packaging-title-second' : undefined}>{word}</span></React.Fragment>)}</h1>
              <p className="packaging-intro">{item.id === 'poster-012' ? (zh ? 'LIAOSE 磨砂膏罐' : 'LIAOSE scrub jar') : design.kind[lang]}</p>
            </div>

            <div className="packaging-model" ref={hostRef} aria-label={zh ? '可拖拽旋转的分层包材模型' : 'Layered packaging model, drag to rotate or use the bottom view button'} />

            {!ready && !failed && (
              <div className="packaging-loading" role="status">
                <span className="packaging-loading-mark" aria-hidden="true" />
                <p>{zh ? '正在准备包材模型' : 'Preparing the packaging model'}</p>
              </div>
            )}

            {failed && (
              <div className="packaging-error" role="status">
                <img src={item.image} alt={item.title[lang]} />
                <p>{zh ? '模型暂时无法显示' : 'The model is currently unavailable'}</p>
                <div><button onClick={() => setRetry(value => value + 1)}>{zh ? '重新加载' : 'Try again'}</button><button onClick={onOriginal}>{zh ? '查看原海报' : 'View poster'}</button></div>
              </div>
            )}

            <aside className="packaging-parts" aria-label={zh ? '查看部件' : 'Explore the components'}>
              {PARTS.map(part => (
                <button key={part.key} className="packaging-part" aria-pressed={selected === part.key} onClick={() => choosePart(part.key)} disabled={controlsDisabled}>
                  <span className="packaging-part-copy">
                    <span className="packaging-part-title">{part.title[languageIndex]}</span>
                    <span className="packaging-part-detail">{part.detail[languageIndex]}</span>
                  </span>
                  <Focus className="packaging-part-focus" size={16} aria-hidden="true" />
                </button>
              ))}
            </aside>

            <div className="packaging-controls" data-ui>
              <div className="packaging-mobile-parts" aria-label={zh ? '选择部件' : 'Choose a component'}>
                {PARTS.map(part => <button key={part.key} disabled={controlsDisabled} onClick={() => choosePart(part.key)} aria-pressed={selected === part.key}>{part.short[languageIndex]}</button>)}
              </div>
              <div className="packaging-help" aria-live="polite">
                {activePart ? <><span>{activePart.title[languageIndex]}</span><p>{activePart.detail[languageIndex]}</p></> : <><ArrowDown size={16} aria-hidden="true" /><p>{manualOnly ? (zh ? '选择阶段，查看包材结构' : 'Choose a stage to explore the structure') : (zh ? '滚动展开 · 拖拽旋转' : 'Scroll to open. Drag to rotate.')}</p></>}
              </div>
              <div className="packaging-player">
                <div className="packaging-presets" role="group" aria-label={zh ? '展开阶段' : 'Opening stages'}>
                  {PRESETS.map((preset, index) => <button key={preset.progress} disabled={controlsDisabled} onClick={() => jumpTo(preset.progress)} aria-pressed={stage === index}>{preset.label[languageIndex]}</button>)}
                </div>
                <div className="packaging-range-row">
                  <label htmlFor="packaging-opening" className="packaging-sr-only">{zh ? '展开程度' : 'Opening progress'}</label>
                  <input id="packaging-opening" ref={rangeRef} type="range" min="0" max="100" step="1" defaultValue="0" disabled={controlsDisabled} onChange={event => jumpTo(Number(event.target.value) / 100, false)} />
                  <output htmlFor="packaging-opening"><span ref={numberRef}>0</span><span>%</span></output>
                </div>
              </div>
              <div className="packaging-view-actions">
                <button disabled={controlsDisabled} onClick={viewBottom} aria-label={zh ? '查看瓶底' : 'View the bottom'} title={zh ? '直接查看瓶底' : 'Look underneath the jar'}><span>{zh ? '看瓶底' : 'Base'}</span></button>
                <button disabled={controlsDisabled} onClick={resetView} title={zh ? '还原正面视角' : 'Reset to the front view'}><RotateCcw size={17} aria-hidden="true" /><span>{zh ? '回到正面' : 'Front view'}</span></button>
                <button disabled={controlsDisabled} onClick={() => apiRef.current?.rotate()} aria-label={zh ? '旋转 90 度' : 'Rotate 90 degrees'}><RotateCw size={17} aria-hidden="true" /></button>
              </div>
            </div>
            <p className="packaging-footnote">{zh ? '结构示意，以实物为准' : 'Visual reference; check the physical sample.'}</p>
          </section>
        </div>
      </div>
    </div>
  );
}
