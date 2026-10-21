import React, {useRef, useState} from 'react';

// Keep the complete tiny cutout visible until the selected display image is
// fully decoded. Slow PNG-style scanlines must never reveal half a product.
export default function FeaturedImage({poster, active, enabled, onReady, alt}) {
  const image = useRef(null);
  const [ready, setReady] = useState(false);
  const [failed, setFailed] = useState(false);
  async function loaded(event) {
    const node = event.currentTarget;
    try {await node.decode?.();} catch {if (!node.complete || !node.naturalWidth) return;}
    if (image.current !== node) return;
    setReady(true); onReady();
  }
  return <span className="featured-media" data-ready={ready} data-failed={failed}>
    <img className="featured-placeholder" src={poster.placeholder} alt="" aria-hidden="true" draggable="false" style={{opacity:ready ? 0 : 1}}/>
    <picture>
      <source media="(max-width: 640px)" srcSet={enabled ? poster.displayMobile : undefined}/>
      <img ref={image} src={enabled ? poster.displayImage : undefined} alt={alt} draggable="false" decoding="async" fetchPriority={active ? 'high' : 'low'} width={poster.displayWidth} height={poster.displayHeight} style={{opacity:ready ? 1 : 0}} onLoad={loaded} onError={() => {setFailed(true); onReady();}}/>
    </picture>
  </span>;
}
