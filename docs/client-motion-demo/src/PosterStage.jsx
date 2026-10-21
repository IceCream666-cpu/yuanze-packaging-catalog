import React, {useEffect, useRef, useState} from 'react';
import {Maximize2, MoveHorizontal} from 'lucide-react';
import {shortestDelta, snapTarget, visibleItems, wrapIndex} from './carousel-model.js';

export default function PosterStage({items, selectedId, onSelect, onOpen, lang, SafeImage}) {
  const initial = Math.max(0, items.findIndex(p => p.id === selectedId));
  const [position, setPosition] = useState(initial);
  const [dragging, setDragging] = useState(false);
  const [width, setWidth] = useState(1000);
  const stage = useRef(null);
  const motion = useRef({position: initial, target: initial, frame: 0, pointer: null, velocity: 0, suppress: 0});
  const callbacks = useRef({onSelect, onOpen});
  callbacks.current = {onSelect, onOpen};
  const reduced = useRef(false);
  const stepWidth = Math.min(460, Math.max(215, width * .37));

  function paint(value) { motion.current.position = value; setPosition(value); }
  function advance(delta) {
    const m = motion.current;
    animate((m.frame ? m.target : Math.round(m.position)) + delta);
  }
  function animate(target, commit = true) {
    // Fractional interpolation can leave tiny float residues across the circular seam.
    // The committed target is always a discrete poster; only paint positions are fractional.
    target = Math.round(target);
    const m = motion.current;
    cancelAnimationFrame(m.frame);
    m.target = target;
    const start = m.position;
    const startTime = performance.now();
    const duration = reduced.current ? 0 : Math.min(660, 360 + Math.abs(target - start) * 70);
    if (commit && items.length) callbacks.current.onSelect(items[wrapIndex(target, items.length)].id);
    const tick = now => {
      const progress = duration ? Math.min(1, (now - startTime) / duration) : 1;
      paint(start + (target - start) * (1 - (1 - progress) ** 4));
      if (progress < 1) m.frame = requestAnimationFrame(tick);
      else { m.frame = 0; m.target = wrapIndex(target, items.length); paint(m.target); }
    };
    m.frame = requestAnimationFrame(tick);
  }

  useEffect(() => {
    const observer = new ResizeObserver(([entry]) => setWidth(entry.contentRect.width));
    observer.observe(stage.current);
    const media = matchMedia('(prefers-reduced-motion: reduce)');
    const update = () => {
      reduced.current = media.matches;
      const m = motion.current;
      if (media.matches && m.frame) {
        cancelAnimationFrame(m.frame); m.frame = 0;
        m.target = wrapIndex(m.target, items.length); paint(m.target);
      }
    };
    update(); media.addEventListener('change', update);
    return () => { observer.disconnect(); media.removeEventListener('change', update); cancelAnimationFrame(motion.current.frame); };
  }, []);

  useEffect(() => {
    if (motion.current.pointer) return;
    const index = Math.max(0, items.findIndex(p => p.id === selectedId));
    const delta = shortestDelta(index, motion.current.position, items.length);
    if (Math.abs(delta) > .001) animate(motion.current.position + delta, false);
  }, [selectedId]);

  useEffect(() => {
    const node = stage.current;
    let timer, lastAt = 0, previousMagnitude = 0, accumulated = 0, locked = false, decayed = false;
    // One intentional trackpad stroke selects one poster; the inertial tail cannot skip more.
    const wheel = event => {
      const x = event.shiftKey && Math.abs(event.deltaX) < 2 ? event.deltaY : event.deltaX;
      if (Math.abs(x) <= Math.abs(event.shiftKey ? 0 : event.deltaY) || Math.abs(x) < .2 || items.length < 2) return;
      event.preventDefault();
      const now = performance.now(), magnitude = Math.abs(x);
      const freshStroke = now - lastAt > 180 || (locked && decayed && magnitude > previousMagnitude * 2.5 && magnitude > 14);
      if (freshStroke) { locked = false; accumulated = 0; decayed = false; }
      if (magnitude < 5) decayed = true;
      lastAt = now; previousMagnitude = magnitude;
      if (!locked) {
        accumulated += x * (event.deltaMode === 1 ? 16 : 1);
        if (Math.abs(accumulated) > 42) { advance(Math.sign(accumulated)); locked = true; }
      }
      clearTimeout(timer); timer = setTimeout(() => { locked = false; accumulated = 0; }, 180);
    };
    node.addEventListener('wheel', wheel, {passive: false});
    const cancel = () => finish(null, true);
    window.addEventListener('blur', cancel);
    return () => { node.removeEventListener('wheel', wheel); window.removeEventListener('blur', cancel); clearTimeout(timer); };
  }, [items.length, stepWidth]);

  function down(event) {
    if (event.button !== 0 || !event.isPrimary || items.length < 2) return;
    const m = motion.current;
    m.pointer = {id: event.pointerId, x: event.clientX, y: event.clientY, lastX: event.clientX, at: performance.now(), start: m.position, moved: false};
    m.velocity = 0;
    // Capture only after horizontal intent, preserving tap targets and vertical page scrolling.
  }
  function move(event) {
    const m = motion.current, p = m.pointer;
    if (!p || event.pointerId !== p.id) return;
    const dx = event.clientX - p.x, dy = event.clientY - p.y;
    if (!p.moved && Math.abs(dy) > Math.abs(dx) + 8) { finish(event, true); return; }
    if (!p.moved && Math.abs(dx) < 7) return;
    if (!p.moved) {
      cancelAnimationFrame(m.frame); m.frame = 0;
      p.start = m.position; p.moved = true;
      stage.current.setPointerCapture(p.id); setDragging(true);
    }
    const now = performance.now(), elapsed = Math.max(1, now - p.at);
    m.velocity = m.velocity * .3 + ((p.lastX - event.clientX) / stepWidth / elapsed) * .7;
    p.lastX = event.clientX; p.at = now;
    paint(p.start - dx / stepWidth);
  }
  function finish(event, cancelled = false) {
    const m = motion.current, p = m.pointer;
    if (!p || (event && event.pointerId !== p.id)) return;
    m.pointer = null;
    if (stage.current?.hasPointerCapture(p.id)) stage.current.releasePointerCapture(p.id);
    setDragging(false);
    if (p.moved) {
      m.suppress = performance.now() + 400;
      const velocity = performance.now() - p.at > 100 || cancelled || reduced.current ? 0 : m.velocity;
      animate(snapTarget(m.position, velocity, items.length));
    }
  }
  const activeIndex = wrapIndex(Math.round(position), items.length);
  return <section className="gallery-shell" aria-label={lang === 'zh' ? '海报画廊' : 'Poster gallery'}>
    <div className={`gallery-stage ${dragging ? 'is-dragging' : ''}`} ref={stage} tabIndex={0} role="region" aria-roledescription="carousel"
      aria-label={lang === 'zh' ? '左右拖动浏览，或使用方向键' : 'Drag sideways or use arrow keys'}
      onPointerDown={down} onPointerMove={move} onPointerUp={finish} onPointerCancel={e => finish(e, true)}
      onLostPointerCapture={e => { if (e.target === stage.current) finish(e, true); }}
      onPointerLeave={e => { if (!motion.current.pointer?.moved) finish(e, true); }}
      onKeyDown={e => { if (e.key === 'ArrowRight' || e.key === 'ArrowLeft') { e.preventDefault(); advance(e.key === 'ArrowRight' ? 1 : -1); } }}>
      <div className="stage-floor" aria-hidden="true" />
      {visibleItems(items, position).map(({poster, index, offset}) => {
        const distance = Math.abs(offset), active = index === activeIndex;
        const scale = Math.max(.62, 1 - distance * .16);
        const turn = Math.max(-14, Math.min(14, offset * -8));
        const drift = Math.max(-9, Math.min(9, offset * 4));
        // With two results the opposite poster changes sides at the circular seam.
        // Fade it before that seam, retaining one real, accessible copy per poster.
        const opacity = items.length === 2 ? Math.max(0, 1 - distance * 1.25) : Math.max(0, 1 - Math.max(0, distance - 1) * .6);
        return <button key={poster.id} className={`poster-plane ${active ? 'center' : ''}`} tabIndex={active ? 0 : -1}
          aria-hidden={distance > 2.5 || opacity < .1} aria-label={`${lang === 'zh' ? (active ? '查看海报' : '选择海报') : (active ? 'View poster' : 'Select poster')}: ${poster.title[lang]}`}
          data-poster-id={poster.id}
          style={{'--ratio': poster.width / poster.height, zIndex: 20 - Math.round(distance * 3), opacity, pointerEvents: distance > 2.5 || opacity < .1 ? 'none' : 'auto', aspectRatio: `${poster.width} / ${poster.height}`, transform: `translate(-50%, -50%) translateX(${offset * stepWidth}px) translateY(${distance * 16}px) rotateY(${turn}deg) rotateZ(${drift}deg) scale(${scale})`}}
          onClick={() => {
            if (performance.now() < motion.current.suppress) return;
            if (active) callbacks.current.onOpen(poster);
            else animate(motion.current.position + shortestDelta(index, motion.current.position, items.length));
          }}>
          <SafeImage src={poster.image} alt={poster.title[lang]} draggable="false" decoding="async" />
          <span className="expand-hint"><Maximize2 size={15} />{lang === 'zh' ? '查看完整海报' : 'View full poster'}</span>
        </button>;
      })}
    </div>
    <div className="gesture-hint"><MoveHorizontal size={18}/><span>{lang === 'zh' ? '左右拖动，让灵感流动' : 'Drag to find your inspiration'}</span></div>
  </section>;
}
