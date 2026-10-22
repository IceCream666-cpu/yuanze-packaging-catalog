import React, {useEffect, useRef, useState} from 'react';

function retryURL(url, token) {
  if (!url) return undefined;
  const [path, hash] = url.split('#');
  return `${path}${path.includes('?') ? '&' : '?'}media_retry=${token}${hash ? `#${hash}` : ''}`;
}

function ImageRequest({poster, active, enabled, requestKey, onSettled, alt, lang, retryDelay, timeoutMs}) {
  const image = useRef(null), callback = useRef(onSettled), finished = useRef(false);
  const handled = useRef(-1), retryTimer = useRef(null), mounted = useRef(true);
  const [attempt, setAttempt] = useState(0);
  const [phase, setPhase] = useState(enabled ? 'loading' : 'waiting');
  callback.current = onSettled;
  const ready = phase === 'loaded', failed = phase === 'error', zh = lang !== 'en';
  // A retry uses the approved fallback size independently of the failed candidate.
  const src = !enabled || failed ? undefined : attempt ? retryURL(poster.displayImage, `${requestKey}-${attempt}`) : poster.displayImage;
  const srcSet = enabled && !attempt && !failed ? poster.displaySrcSet : undefined;

  function fail(node, currentAttempt) {
    if (!mounted.current || finished.current || image.current !== node || handled.current === currentAttempt) return;
    handled.current = currentAttempt;
    if (currentAttempt < 1) {
      setPhase('retrying');
      retryTimer.current = setTimeout(() => {setAttempt(currentAttempt + 1); setPhase('loading');}, retryDelay);
    } else {
      finished.current = true; setPhase('error'); callback.current?.('error');
    }
  }
  async function loaded(event, currentAttempt) {
    const node = event.currentTarget;
    try {await node.decode?.();}
    catch {if (!node.complete || !node.naturalWidth) {fail(node, currentAttempt); return;}}
    if (!mounted.current || image.current !== node || finished.current || handled.current === currentAttempt) return;
    finished.current = true; setPhase('loaded'); callback.current?.('loaded');
  }
  useEffect(() => {
    mounted.current = true;
    return () => {mounted.current = false; clearTimeout(retryTimer.current);};
  }, []);
  useEffect(() => {
    if (!enabled) return;
    const node = image.current;
    const timeout = setTimeout(() => fail(node, attempt), timeoutMs);
    return () => clearTimeout(timeout);
  }, [enabled, attempt, timeoutMs]);

  return <span className="featured-media" data-ready={ready} data-failed={failed} aria-busy={!ready && !failed}>
    {!ready && <span className={`featured-loading ${failed ? 'has-error' : ''}`} aria-hidden="true">
      <span className="featured-loading-shape"/>
      {active && <span className="featured-loading-label">{failed
        ? (zh ? '图片未能加载 · 点击重试' : 'Image unavailable · Click to retry')
        : (zh ? '正在加载清晰图片…' : 'Loading a clear image…')}</span>}
    </span>}
    <picture>
      <img key={attempt} ref={image} src={src} srcSet={srcSet} sizes={srcSet ? poster.displaySizes : undefined}
        alt={ready ? alt : ''} draggable="false" decoding="async" fetchPriority={active ? 'high' : 'low'}
        width={poster.displayWidth} height={poster.displayHeight} style={{opacity: ready ? 1 : 0}}
        onLoad={event => loaded(event, attempt)} onError={event => fail(event.currentTarget, attempt)}/>
    </picture>
  </span>;
}

// Tokens change only for a new/manual retry, never on ordinary active selection.
export default function FeaturedImage({requestKey = 1, retryDelay = 350, timeoutMs = 12000, ...props}) {
  return <ImageRequest key={requestKey} requestKey={requestKey} retryDelay={retryDelay} timeoutMs={timeoutMs} {...props}/>;
}
