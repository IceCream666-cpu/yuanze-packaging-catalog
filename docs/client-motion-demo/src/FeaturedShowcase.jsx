import React, {useEffect, useRef, useState} from 'react';
import {ArrowLeft, ArrowRight, ArrowUpRight, Heart, Info, LogOut, Pause, Play} from 'lucide-react';
import PosterStage from './PosterStage.jsx';
import {categories, styles} from './copy.js';

export default function FeaturedShowcase({items, selectedId, onSelect, onBrowse, onFavorites, onOpen, onInfo, onLanguage, lang, favorites, onFavorite, SafeImage, modalOpen, logo, production, onSignOut, signingOut}) {
  const [playing, setPlaying] = useState(false);
  const [hovered, setHovered] = useState(false);
  const [focused, setFocused] = useState(false);
  const [hidden, setHidden] = useState(document.hidden);
  const [reduced, setReduced] = useState(() => matchMedia('(prefers-reduced-motion: reduce)').matches);
  const [interacted, setInteracted] = useState(0);
  const [visibleId, setVisibleId] = useState(selectedId);
  const swatches = useRef(null);
  const current = items.find(p => p.id === visibleId) || items[0];
  const currentIndex = items.indexOf(current);
  const latest = useRef({items, selectedId, onSelect});
  latest.current = {items, selectedId, onSelect};
  const zh = lang === 'zh';
  const category = categories.find(item => item[0] === current.category)?.[zh ? 1 : 2];
  const style = styles.find(item => item[0] === current.style)?.[zh ? 1 : 2];
  useEffect(() => {
    const strip = swatches.current;
    if (!strip) return;
    const reveal = () => {
      const selected = strip.querySelector('[aria-pressed="true"]');
      if (!selected) return;
      const frame = strip.getBoundingClientRect(), item = selected.getBoundingClientRect();
      // Move only the horizontal rail, never the page or the user's vertical position.
      const delta = item.left < frame.left + 6 ? item.left - frame.left - 6
        : item.right > frame.right - 6 ? item.right - frame.right + 6 : 0;
      if (delta) strip.scrollLeft += delta;
    };
    reveal();
    const observer = new ResizeObserver(reveal);
    observer.observe(strip);
    return () => observer.disconnect();
  }, [current.id, items.length]);
  useEffect(() => {
    const visibility = () => setHidden(document.hidden);
    const media = matchMedia('(prefers-reduced-motion: reduce)');
    const preference = () => {setReduced(media.matches); if (media.matches) setPlaying(false);};
    document.addEventListener('visibilitychange', visibility);
    media.addEventListener('change', preference);
    return () => {document.removeEventListener('visibilitychange', visibility); media.removeEventListener('change', preference);};
  }, []);
  useEffect(() => {
    if (!playing || hovered || focused || hidden || reduced || modalOpen) return;
    const timer = setTimeout(() => {
      const {items, selectedId, onSelect} = latest.current;
      const index = items.findIndex(p => p.id === selectedId);
      onSelect(items[(index + 1) % items.length].id);
    }, 4200);
    return () => clearTimeout(timer);
  }, [playing, hovered, focused, hidden, reduced, modalOpen, selectedId, interacted]);
  function choose(id) {setInteracted(n => n + 1); onSelect(id);}
  function step(delta) {
    // Functional updates retain every rapid button press before React commits a frame.
    setInteracted(n => n + 1);
    onSelect(id => items[(items.findIndex(p => p.id === id) + delta + items.length) % items.length].id);
  }
  const interaction = {
    onPointerEnter: e => {if (e.pointerType === 'mouse') setHovered(true);},
    onPointerLeave: () => setHovered(false),
    onFocusCapture: () => setFocused(true),
    onBlurCapture: e => {if (!e.currentTarget.contains(e.relatedTarget)) setFocused(false);},
    onPointerDownCapture: () => setInteracted(n => n + 1)
  };
  return <div className="colour-experience arc-experience">
    <header className="colour-header">
      <a href="#" className="colour-brand" aria-label={zh ? '源泽 · 精选展示' : 'Yuanze · Featured collection'} onClick={e => e.preventDefault()}><img src={logo} alt=""/><span>yuanze</span></a>
      <span className="colour-tagline">A daily dose of delight.</span>
      <nav className="colour-nav" aria-label={zh ? '主导航' : 'Main navigation'}>
        <button className="colour-favorites" onClick={onFavorites} aria-label={zh ? `我的收藏 ${favorites.length}` : `Favorites ${favorites.length}`}><Heart size={17}/>{favorites.length > 0 && <small>{favorites.length}</small>}</button>
        <button className="colour-language" onClick={onLanguage}>{zh ? 'EN' : '中文'}</button>
        <button className="browse-collection" onClick={onBrowse}>{zh ? '浏览全系列' : 'Explore collection'}<ArrowUpRight size={25} strokeWidth={1}/></button>
      </nav>
    </header>
    <main className="colour-main">
      <div className="arc-hero">
        <section className="colour-details arc-information" aria-labelledby="featured-title">
          <h1>Care in colour.</h1>
          <div className="colour-copy" aria-live={playing ? 'off' : 'polite'} aria-atomic="true" data-product-id={current.id}>
            <div className="arc-copy-transition" key={`${current.id}-${lang}`}>
              <h2 id="featured-title">{current.name}</h2>
              <p className="colour-kind">{current.kind[lang]}</p>
              <p className="colour-description">{current.description[lang]}</p>
              <dl className="arc-product-facts">
                {category && <div><dt>{zh ? '产品类目' : 'Category'}</dt><dd>{category}</dd></div>}
                {style && <div><dt>{zh ? '视觉风格' : 'Visual style'}</dt><dd>{style}</dd></div>}
              </dl>
            </div>
          </div>
        </section>
        <div className="arc-display" {...interaction}>
          <div className="colour-carousel">
            <PosterStage items={items} selectedId={selectedId} onActiveChange={setVisibleId} onSelect={choose} onOpen={onOpen} lang={lang} SafeImage={SafeImage} presentation="products"/>
          </div>
          <div className="arc-stage-controls">
            <p>{zh ? '左右拖动，发现下一款' : 'Drag to discover your next favourite'}</p>
            <div className="colour-arrows"><button onClick={() => step(-1)} aria-label={zh ? '上一款' : 'Previous product'}><ArrowLeft size={21} strokeWidth={1.5}/></button><button onClick={() => step(1)} aria-label={zh ? '下一款' : 'Next product'}><ArrowRight size={21} strokeWidth={1.5}/></button></div>
          </div>
        </div>
        <div className="colour-product-actions">
          <button className="colour-poster" onClick={() => onOpen(current)}>{zh ? '查看产品海报' : 'View product poster'}<ArrowUpRight size={24} strokeWidth={1}/></button>
          <button className="colour-save" aria-label={favorites.includes(current.id) ? (zh ? '取消收藏' : 'Remove favorite') : (zh ? '收藏此款' : 'Save favorite')} aria-pressed={favorites.includes(current.id)} onClick={() => onFavorite(current.id)}><Heart size={19} strokeWidth={1.4} fill={favorites.includes(current.id) ? 'currentColor' : 'none'}/></button>
        </div>
      </div>
      <div className="colour-collection-bar"><span>{zh ? '选择你的色彩' : 'Find your colour'}</span><div className="colour-swatch-picker"><div className="colour-swatches" ref={swatches} role="group" aria-label={zh ? `选择精选产品，共 ${items.length} 款` : `Choose from ${items.length} featured products`}>{items.map(p => <button key={p.id} onClick={() => choose(p.id)} aria-label={p.name} aria-pressed={p.id === current.id} title={p.name}><span><i style={{background:p.swatch[0]}}/><i style={{background:p.swatch[1]}}/></span></button>)}</div><span className="colour-position" aria-hidden="true">{String(currentIndex + 1).padStart(2, '0')} / {items.length}</span></div><button className="colour-play" disabled={reduced} aria-pressed={playing} onClick={() => setPlaying(!playing)} title={reduced ? (zh ? '已遵循系统减少动态效果设置' : 'Reduced motion is enabled') : undefined}>{playing ? <Pause size={22} strokeWidth={1}/> : <Play size={24} strokeWidth={1}/>}<span>{reduced ? (zh ? '已减少动态效果' : 'Reduced motion') : playing ? (zh ? '暂停轮播' : 'Pause slideshow') : (zh ? '自动轮播' : 'Auto play')}</span></button></div>
    </main>
    <footer className="colour-footer"><span>Body · Face · Hair</span><div><button onClick={onInfo} aria-label={zh ? '关于客户端' : 'About the client'}><Info size={14}/></button><span>YUANZE Collection</span>{production && <button onClick={onSignOut} disabled={signingOut} aria-label={zh ? '退出登录' : 'Log out'}><LogOut size={15}/></button>}</div></footer>
  </div>;
}
