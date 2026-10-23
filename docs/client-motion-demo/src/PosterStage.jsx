import React, {useEffect, useLayoutEffect, useMemo, useRef, useState} from 'react';
import FeaturedImage from './FeaturedImage.jsx';
import {createFeaturedLoadQueue} from './featured-loading.js';
import {Maximize2, MoveHorizontal} from 'lucide-react';
import {shortestDelta, snapTarget, visibleItems, wrapIndex} from './carousel-model.js';
import {createCarouselMotion, horizontalWheel, wheelSnap} from './carousel-motion.js';
import {productArc} from './product-arc.js';

export default function PosterStage({items, selectedId, onSelect, onActiveChange, onOpen, lang, SafeImage, presentation = 'posters'}) {
  const products = presentation === 'products';
  const indices = useMemo(() => new Map(items.map((item, index) => [item.id, index])), [items]);
  const [imageLoads, setImageLoads] = useState({});
  const imageQueue = useRef(null);
  if (!imageQueue.current) imageQueue.current = createFeaturedLoadQueue({ids: items.map(item => item.id), onChange: setImageLoads});
  const initial = Math.max(0, items.findIndex(p => p.id === selectedId));
  const [anchor, setAnchor] = useState(initial);
  const [width, setWidth] = useState(1000);
  const stage = useRef(null), planes = useRef(new Map());
  const pointer = useRef(null), wheel = useRef({timer: 0, start: null});
  const suppress = useRef(0), anchorRef = useRef(initial), reduced = useRef(false);
  const latest = useRef(null);
  const stepWidth = products ? Math.min(360, Math.max(205, width * .245)) : Math.min(460, Math.max(215, width * .37));
  const motion = useRef(null);

  function paint(position, moving) {
    const {items, indices, products, stepWidth, width} = latest.current;
    stage.current?.classList.toggle('is-moving', moving);
    const nextAnchor = wrapIndex(Math.round(position), items.length);
    // React handles semantic/visible-window changes, never fractional animation frames.
    if (nextAnchor !== anchorRef.current) {anchorRef.current = nextAnchor; setAnchor(nextAnchor);}
    for (const [id, node] of planes.current) {
      const index = indices.get(id);
      const offset = shortestDelta(index, position, items.length), distance = Math.abs(offset);
      // Keep decoded image nodes stable, but avoid rewriting invisible far-away products every frame.
      if (products && distance >= 2.7 && node.style.visibility === 'hidden') continue;
      const arc = products ? productArc(offset, width, items.length) : null;
      const scale = Math.max(.62, 1 - distance * .16);
      const turn = Math.max(-14, Math.min(14, offset * -8));
      const drift = Math.max(-9, Math.min(9, offset * 4));
      // Hide circular-seam crossings before relocating the off-screen item.
      const opacity = arc ? arc.opacity : items.length === 2 ? Math.max(0, 1 - distance * 1.25)
        : Math.max(0, 1 - Math.max(0, distance - 1) * .6);
      node.style.transform = arc
        ? `translate(-50%, -50%) translate3d(${arc.x}px,${arc.y}px,${arc.z}px) rotateY(${arc.rotateY}deg) scale(${arc.scale})`
        : `translate(-50%, -50%) translate3d(${offset * stepWidth}px,${distance * 16}px,0) rotateY(${turn}deg) rotateZ(${drift}deg) scale(${scale})`;
      node.style.opacity = opacity;
      node.style.zIndex = 20 - Math.round(distance * 3);
      node.style.visibility = opacity < .001 ? 'hidden' : 'visible';
      node.style.pointerEvents = distance > 2.5 || opacity < .1 ? 'none' : 'auto';
      node.setAttribute('aria-hidden', String(distance > 2.5 || opacity < .1));
    }
  }
  latest.current = {items, indices, products, stepWidth, width, onSelect, onActiveChange, onOpen, paint};
  if (!motion.current) motion.current = createCarouselMotion({
    initial, length: items.length,
    now: () => performance.now(), requestFrame: fn => requestAnimationFrame(fn), cancelFrame: id => cancelAnimationFrame(id),
    paint: (position, moving) => latest.current.paint(position, moving),
    select: index => latest.current.onSelect(latest.current.items[index].id)
  });
  const controller = motion.current;
  const activeId = items[anchor]?.id;

  // Detail copy follows the product nearest the visual center, even before a
  // drag settles. This notification never feeds a new target into the spring.
  useEffect(() => {
    if (activeId !== undefined) latest.current.onActiveChange?.(activeId);
  }, [activeId]);

  useEffect(() => {
    if (products) imageQueue.current.select(items[anchor]?.id);
  }, [anchor, products]);

  useLayoutEffect(() => {paint(controller.state.position, !!controller.state.frame || controller.state.input);});
  useEffect(() => {
    const observer = new ResizeObserver(([entry]) => setWidth(entry.contentRect.width));
    observer.observe(stage.current);
    const media = matchMedia('(prefers-reduced-motion: reduce)');
    const update = () => {reduced.current = media.matches; controller.setReduced(media.matches);};
    const inactive = () => {
      finish(null, true); endWheel();
      if (document.hidden) controller.setReduced(true);
      else controller.setReduced(media.matches);
    };
    update(); media.addEventListener('change', update);
    document.addEventListener('visibilitychange', inactive);
    window.addEventListener('blur', inactive);
    return () => {
      observer.disconnect(); media.removeEventListener('change', update);
      document.removeEventListener('visibilitychange', inactive); window.removeEventListener('blur', inactive);
      clearTimeout(wheel.current.timer); controller.dispose();
      imageQueue.current.dispose();
    };
  }, []);

  useEffect(() => {
    if (pointer.current || wheel.current.start !== null) return;
    controller.selectIndex(Math.max(0, items.findIndex(p => p.id === selectedId)));
  }, [selectedId]);

  function endWheel() {
    clearTimeout(wheel.current.timer);
    if (wheel.current.start === null) return;
    const target = wheelSnap(controller.state.position, wheel.current.start);
    wheel.current.start = null; controller.settle(target);
  }
  useEffect(() => {
    const node = stage.current;
    const handleWheel = event => {
      const dx = horizontalWheel(event, latest.current.stepWidth);
      if (!dx || items.length < 2 || pointer.current) return;
      event.preventDefault();
      const w = wheel.current;
      if (w.start === null) w.start = controller.state.position;
      // Consume every horizontal delta, including reversals and closely spaced strokes.
      controller.moveTo(controller.state.position + dx / latest.current.stepWidth);
      suppress.current = performance.now() + 250;
      clearTimeout(w.timer); w.timer = setTimeout(endWheel, 120);
    };
    node.addEventListener('wheel', handleWheel, {passive:false});
    return () => node.removeEventListener('wheel', handleWheel);
  }, [items.length]);

  function down(event) {
    if (event.button !== 0 || !event.isPrimary || items.length < 2) return;
    endWheel();
    pointer.current = {id:event.pointerId, x:event.clientX, y:event.clientY, lastX:event.clientX, at:performance.now(), start:controller.state.position, moved:false, velocity:0};
  }
  function move(event) {
    const p = pointer.current;
    if (!p || event.pointerId !== p.id) return;
    const dx = event.clientX - p.x, dy = event.clientY - p.y;
    if (!p.moved && Math.abs(dy) > Math.abs(dx) + 8) {finish(event, true); return;}
    if (!p.moved && Math.abs(dx) < 7) return;
    if (!p.moved) {
      p.start = controller.state.position; p.moved = true;
      stage.current.setPointerCapture(p.id); stage.current.classList.add('is-dragging');
    }
    const now = performance.now(), elapsed = Math.max(1, now - p.at);
    p.velocity = p.velocity * .3 + ((p.lastX - event.clientX) / stepWidth / elapsed) * .7;
    p.lastX = event.clientX; p.at = now;
    controller.moveTo(p.start - dx / stepWidth);
  }
  function finish(event, cancelled = false) {
    const p = pointer.current;
    if (!p || (event && event.pointerId !== p.id)) return;
    pointer.current = null;
    if (stage.current?.hasPointerCapture(p.id)) stage.current.releasePointerCapture(p.id);
    stage.current?.classList.remove('is-dragging');
    if (p.moved) {
      suppress.current = performance.now() + 400;
      const velocity = performance.now() - p.at > 100 || cancelled || reduced.current ? 0 : p.velocity;
      controller.settle(snapTarget(controller.state.position, velocity, items.length));
    }
  }
  // Product nodes retain their decoded images; requests remain limited to the current item and neighbours.
  // Full-poster libraries keep a stable seven-item window.
  const mounted = visibleItems(items, anchor, products ? items.length : 7).sort((a,b) => a.index - b.index);
  return <section className={`gallery-shell ${products ? 'product-stage-shell' : ''}`} aria-label={lang === 'zh' ? (products ? '精选产品' : '海报画廊') : (products ? 'Featured products' : 'Poster gallery')}>
    <div className="gallery-stage" ref={stage} tabIndex={0} role="region" aria-roledescription="carousel"
      aria-label={lang === 'zh' ? '左右拖动浏览，或使用方向键' : 'Drag sideways or use arrow keys'}
      onPointerDown={down} onPointerMove={move} onPointerUp={e => finish(e)} onPointerCancel={e => finish(e, true)}
      onLostPointerCapture={e => {if (e.target === stage.current) finish(e, true);}}
      onPointerLeave={e => {if (!pointer.current?.moved) finish(e, true);}}
      onKeyDown={e => {if (e.key === 'ArrowRight' || e.key === 'ArrowLeft') {e.preventDefault(); endWheel(); controller.advance(e.key === 'ArrowRight' ? 1 : -1);}}}>
      {!products && <div className="stage-floor" aria-hidden="true"/>}
      {mounted.map(({poster,index}) => {
        const active = index === anchor;
        const load = imageLoads[poster.id];
        const retryable = products && active && load?.status === 'error';
        return <button key={poster.id} ref={node => {if(node) planes.current.set(poster.id,node);else planes.current.delete(poster.id);}}
          className={`poster-plane ${active ? 'center' : ''}`} tabIndex={active ? 0 : -1}
          aria-label={`${retryable ? (lang === 'zh' ? '重试图片' : 'Retry image') : lang === 'zh' ? (active ? '查看海报' : '选择海报') : (active ? 'View poster' : 'Select poster')}: ${poster.title[lang]}`}
          data-poster-id={poster.id} style={{'--ratio':poster.width/poster.height,aspectRatio:products ? undefined : `${poster.width} / ${poster.height}`}}
          onClick={() => {
            if (performance.now() < suppress.current) return;
            if (retryable) {imageQueue.current.retry(poster.id); return;}
            if (index === wrapIndex(Math.round(controller.state.position),items.length)) latest.current.onOpen(poster);
            else controller.settle(controller.state.position + shortestDelta(index,controller.state.position,items.length));
          }}>
          {products ? <FeaturedImage poster={poster} active={active} enabled={load?.enabled || false}
            requestKey={load?.token || 1} onSettled={status => imageQueue.current.finish(poster.id, load?.token, status)}
            alt={poster.title[lang]} lang={lang}/>
            : <SafeImage src={poster.image} srcSet={poster.imageSrcSet} sizes={poster.gallerySizes}
              enabled={Math.abs(shortestDelta(index, anchor, items.length)) <= 2}
              alt={poster.title[lang]} draggable="false" decoding="async" loading={active ? 'eager' : 'lazy'} fetchPriority={active ? 'high' : 'low'}/>}
          {!products && <span className="expand-hint"><Maximize2 size={15}/>{lang === 'zh' ? '查看完整海报' : 'View full poster'}</span>}
        </button>;
      })}
    </div>
    {!products && <div className="gesture-hint"><MoveHorizontal size={18}/><span>{lang === 'zh' ? '左右拖动，让灵感流动' : 'Drag to find your inspiration'}</span></div>}
  </section>;
}
