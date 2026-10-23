import React, {useEffect, useRef, useState} from 'react';

function retryURL(url, token) {
  if (!url) return undefined;
  const [path, hash] = url.split('#');
  return `${path}${path.includes('?') ? '&' : '?'}media_retry=${token}${hash ? `#${hash}` : ''}`;
}

// Every base image is already clear at 640px. Upgrade after motion and warming settle,
// keeping that decoded image visible until the larger candidate is ready.
function DetailUpgrade({poster, active}) {
  const [enabled, setEnabled] = useState(false), [ready, setReady] = useState(false);
  const mounted = useRef(true), image = useRef(null);
  useEffect(() => {mounted.current = true; return () => {mounted.current = false;};}, []);
  useEffect(() => {
    if (ready) return;
    if (!active) {setEnabled(false); return;}
    const timer = setTimeout(() => setEnabled(true), 220);
    return () => clearTimeout(timer);
  }, [active, ready]);
  async function loaded(event) {
    const node = event.currentTarget;
    try {await node.decode?.();} catch {return;}
    if (mounted.current && image.current === node) setReady(true);
  }
  return enabled ? <img className="featured-detail" ref={image} src={poster.displayImage}
    srcSet={poster.displaySrcSet} sizes={poster.displaySizes} width={poster.displayWidth} height={poster.displayHeight}
    alt="" aria-hidden="true" draggable="false" decoding="async" fetchPriority={active ? 'high' : 'low'}
    style={{opacity: ready ? 1 : 0}} onLoad={loaded}/> : null;
}

function ImageRequest({poster, active, urgent = active, allowUpgrade = true, enabled, requestKey, onTransferred, onSettled, alt, lang, retryDelay, timeoutMs, decodeTimeoutMs}) {
  const image = useRef(null), callback = useRef(onSettled), finished = useRef(false);
  const handled = useRef(-1), retryTimer = useRef(null), mounted = useRef(true);
  const transferred = useRef(onTransferred), timeout = useRef(null), plan = useRef(null);
  const didTransfer = useRef(false);
  const decodeTimer = useRef(null);
  const [attempt, setAttempt] = useState(0);
  const [phase, setPhase] = useState(enabled ? 'loading' : 'waiting');
  callback.current = onSettled;
  transferred.current = onTransferred;
  if (enabled && !plan.current) plan.current = {light: !!poster.displayMobile,
    src: poster.displayMobile || poster.displayImage};
  const ready = phase === 'loaded', failed = phase === 'error', zh = lang !== 'en';
  // Retry the lighter approved derivative instead of forcing a larger download.
  const src = !enabled || failed ? undefined : attempt
    ? retryURL(poster.displayMobile || plan.current.src, `${requestKey}-${attempt}`) : plan.current.src;
  const srcSet = enabled && !attempt && !failed && !plan.current?.light ? poster.displaySrcSet : undefined;

  function fail(node, currentAttempt) {
    if (!mounted.current || finished.current || image.current !== node || handled.current === currentAttempt) return;
    clearTimeout(timeout.current);
    handled.current = currentAttempt;
    if (currentAttempt < 1 && !didTransfer.current) {
      setPhase('retrying');
      retryTimer.current = setTimeout(() => {setAttempt(currentAttempt + 1); setPhase('loading');}, retryDelay);
    } else {
      finished.current = true; setPhase('error'); callback.current?.('error');
    }
  }
  async function loaded(event, currentAttempt) {
    const node = event.currentTarget;
    if (!mounted.current || image.current !== node || finished.current || handled.current === currentAttempt) return;
    clearTimeout(timeout.current);
    didTransfer.current = true;
    transferred.current?.();
    try {await Promise.race([node.decode?.(), new Promise((_, reject) => {
      decodeTimer.current = setTimeout(() => reject(new Error('Image decode timed out')), decodeTimeoutMs);
    })]);}
    catch {if (!node.complete || !node.naturalWidth) {fail(node, currentAttempt); return;}}
    finally {clearTimeout(decodeTimer.current);}
    if (!mounted.current || image.current !== node || finished.current || handled.current === currentAttempt) return;
    finished.current = true; setPhase('loaded'); callback.current?.('loaded');
  }
  useEffect(() => {
    mounted.current = true;
    return () => {mounted.current = false; clearTimeout(retryTimer.current); clearTimeout(timeout.current); clearTimeout(decodeTimer.current);};
  }, []);
  useEffect(() => {
    if (!enabled) return;
    const node = image.current;
    timeout.current = setTimeout(() => fail(node, attempt), timeoutMs);
    return () => clearTimeout(timeout.current);
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
        alt={ready ? alt : ''} draggable="false" decoding="async" fetchPriority={urgent ? 'high' : 'low'}
        width={poster.displayWidth} height={poster.displayHeight} style={{opacity: ready ? 1 : 0}}
        onLoad={event => loaded(event, attempt)} onError={event => fail(event.currentTarget, attempt)}/>
    </picture>
    {ready && plan.current?.light && <DetailUpgrade poster={poster} active={active && urgent && allowUpgrade}/>}
  </span>;
}

// Tokens change only for a first request/manual retry, never on active selection.
export default function FeaturedImage({requestKey = 1, retryDelay = 350, timeoutMs = 12000, decodeTimeoutMs = 2500, ...props}) {
  return <ImageRequest key={requestKey} requestKey={requestKey} retryDelay={retryDelay} timeoutMs={timeoutMs} decodeTimeoutMs={decodeTimeoutMs} {...props}/>;
}
