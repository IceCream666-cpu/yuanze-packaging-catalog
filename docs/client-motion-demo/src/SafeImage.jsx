import React, {useEffect, useRef, useState} from 'react';
import {retrySource} from './media-policy.js';

// Assign a source only near the viewport. Once started, never revoke it when
// the carousel moves: an in-flight request and its decoded node are reusable.
export default function SafeImage({src, srcSet, sizes, alt, enabled = true, loading = 'eager', onLoad, onError, ...props}) {
  const host = useRef(null), image = useRef(null), mounted = useRef(true);
  const request = useRef({signature: '', generation: 0}), brokenGeneration = useRef(-1);
  const [started, setStarted] = useState(enabled && loading !== 'lazy');
  const [ready, setReady] = useState(false), [failed, setFailed] = useState(false), [attempt, setAttempt] = useState(0);
  // The same image element survives retries, so DOM identity alone cannot guard
  // an older decode promise. Invalidate it synchronously when its source changes.
  const signature = JSON.stringify([src, srcSet, attempt]);
  if (request.current.signature !== signature) request.current = {signature, generation: request.current.generation + 1};
  const generation = request.current.generation;
  useEffect(() => {mounted.current = true; return () => {mounted.current = false;};}, []);
  useEffect(() => {setReady(false); setFailed(false); setAttempt(0);}, [src]);
  useEffect(() => {
    if (started || !enabled) return;
    if (loading !== 'lazy' || typeof IntersectionObserver === 'undefined') {setStarted(true); return;}
    const observer = new IntersectionObserver(entries => {
      if (entries.some(entry => entry.isIntersecting)) {setStarted(true); observer.disconnect();}
    }, {rootMargin: '200px'});
    observer.observe(host.current);
    return () => observer.disconnect();
  }, [enabled, loading, started]);
  async function loaded(event) {
    const node = event.currentTarget;
    const candidate = node.currentSrc || node.src;
    const current = () => mounted.current && image.current === node && request.current.generation === generation
      && (node.currentSrc || node.src) === candidate && brokenGeneration.current !== generation;
    try {await node.decode?.();}
    catch {if (!current()) return; if (!node.complete || !node.naturalWidth) return broken(node, generation);}
    if (!current()) return;
    setReady(true); setFailed(false); onLoad?.();
  }
  function broken(node, sourceGeneration) {
    if (!mounted.current || image.current !== node || request.current.generation !== sourceGeneration || brokenGeneration.current === sourceGeneration) return;
    brokenGeneration.current = sourceGeneration;
    if (attempt < 1) {setReady(false); setAttempt(1);}
    else {setFailed(true); onError?.();}
  }
  function retry(event) {event.preventDefault(); event.stopPropagation(); setFailed(false); setReady(false); setAttempt(n => n + 1);}
  return <span ref={host} className="responsive-media" data-ready={ready} data-failed={failed} aria-busy={started && !ready && !failed}>
    <img {...props} ref={image} src={started ? retrySource(src, attempt) : undefined}
      srcSet={started && !attempt ? srcSet : undefined} sizes={sizes} alt={alt}
      loading="eager" decoding="async" style={{...props.style, opacity: ready ? 1 : 0}}
      onLoad={loaded} onError={event => broken(event.currentTarget, generation)}/>
    {!ready && <span className={`media-status ${failed ? 'is-error' : ''}`} onClick={failed ? retry : undefined}>
      {failed ? '图片加载失败，点击重试 / Retry image' : <span className="sr-only">图片加载中 / Loading image</span>}
    </span>}
  </span>;
}
