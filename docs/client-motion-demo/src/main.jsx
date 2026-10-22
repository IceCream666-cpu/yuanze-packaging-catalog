import React, {useEffect, useMemo, useRef, useState} from 'react';
import {createRoot} from 'react-dom/client';
import {ArrowRight, Check, ChevronLeft, ChevronRight, Download, GalleryHorizontalEnd, Heart, Images, Info, LayoutGrid, LogOut, Maximize2, Search, X, ZoomIn, ZoomOut} from 'lucide-react';
import posterData from './posters.json';
import assetPaths from './asset-paths.json';
import {FAVORITES_KEY, filterPosters, readFavorites, persist, toggleFavorite, stepIndex} from './model.js';
import {loadSession, logoutSession} from './session.js';
import {copy, categories, styles} from './copy.js';
import PosterStage from './PosterStage.jsx';
import FeaturedShowcase from './FeaturedShowcase.jsx';
import featuredData from './featured.json';
import featuredMedia from './featured-media.json';
import {lockPageScroll} from './modal-scroll.js';
import SafeImage from './SafeImage.jsx';
import {FEATURED_SIZES, GRID_SIZES, GALLERY_SIZES, imageCandidates} from './media-policy.js';
import './style.css';
import './colour.css';
import './mobile.css';
import './presentation.css';
import './media-loading.css';
import './responsive-media.css';

// The preview is offline. Authentication remains the responsibility of the existing server.
const production = import.meta.env.MODE === 'showroom';
const assetURL = path => production ? assetPaths[path] : `${import.meta.env.BASE_URL}${path.replace(/^\//, '')}`;
const posters = posterData.map(p => ({...p, image: assetURL(p.image), thumb: assetURL(p.thumb), original: assetURL(p.original),
  smallImage: assetURL(p.smallImage), stripThumb: assetURL(p.stripThumb),
  imageSrcSet: imageCandidates([[assetURL(p.smallImage), p.smallWidth], [assetURL(p.image), p.imageWidth]]),
  gallerySizes: GALLERY_SIZES}));
// Featured cutouts have a separate review manifest; the production build registers approved derivatives under assets/.
const featured = featuredData.map(p => {
  const media = featuredMedia[p.id];
  const prefix = `${import.meta.env.BASE_URL}${production ? 'assets/' : ''}featured/`;
  return {...posters.find(item => item.id === p.id), ...p,
    displayImage: `${prefix}${p.id}-1024.webp`, displayMobile: `${prefix}${p.id}-640.webp`,
    displaySrcSet: imageCandidates(Object.values(media.files).map(f => [`${prefix}${f.file.split('/').pop()}`, f.width])),
    displaySizes: FEATURED_SIZES, displayWidth: media.width, displayHeight: media.height};
});
const localStore = (() => {try {return window.localStorage;} catch {return null;}})();
const validIds = new Set(posters.map(p => p.id));

function App() {
  const [page, setPage] = useState('home');
  const [featuredId, setFeaturedId] = useState(featured[0].id);
  const [lang, setLang] = useState('zh');
  const [section, setSection] = useState('discover');
  const [category, setCategory] = useState('all');
  const [style, setStyle] = useState('all');
  const [query, setQuery] = useState('');
  const [layout, setLayout] = useState('grid');
  const [selectedId, setSelectedId] = useState(posters[0].id);
  const [favorites, setFavorites] = useState(() => readFavorites(localStore, validIds));
  const [modal, setModal] = useState(null);
  const [toast, setToast] = useState('');
  const [hd, setHd] = useState(false);
  const [zoom, setZoom] = useState(false);
  const [hdStatus, setHdStatus] = useState('idle');
  const [imageAttempt, setImageAttempt] = useState(0);
  const [sessionState, setSessionState] = useState(production ? 'loading' : 'ready');
  const [signingOut, setSigningOut] = useState(false);
  const sessionRef = useRef(null), dialogRef = useRef(null), triggerRef = useRef(null), searchRef = useRef(null), filmstripRef = useRef(null);
  const t = copy[lang];
  const filtered = useMemo(() => filterPosters(posters, {query, category, style, favorites: section === 'favorites' ? favorites : null}), [query, category, style, section, favorites]);
  const index = Math.max(0, filtered.findIndex(p => p.id === selectedId));
  const current = filtered[index];
  const palette = page === 'home' ? featured.find(p => p.id === featuredId) : {background: '#f4ebe6', ink: '#3c1927', accent: '#74565c'};
  const categoryName = id => categories.find(c => c[0] === id)?.[lang === 'zh' ? 1 : 2];
  const stageKey = filtered.map(p => p.id).join('|');

  useEffect(() => {document.documentElement.lang = lang === 'zh' ? 'zh-CN' : 'en';}, [lang]);
  useEffect(() => {
    if (!production) return;
    let active = true;
    const refresh = () => loadSession().then(session => {if (active) {sessionRef.current = session; setSessionState('ready');}}).catch(error => {
      if (!active) return;
      if (error.status === 401) window.location.replace('/login'); else setSessionState('error');
    });
    refresh(); window.addEventListener('focus', refresh);
    return () => {active = false; window.removeEventListener('focus', refresh);};
  }, []);
  useEffect(() => {if (toast) {const timer = setTimeout(() => setToast(''), 2500); return () => clearTimeout(timer);}}, [toast]);
  useEffect(() => {
    if (modal) dialogRef.current?.showModal();
    else {dialogRef.current?.close(); triggerRef.current?.focus?.();}
  }, [modal?.type]);
  useEffect(() => {
    if (modal) return lockPageScroll();
  }, [modal?.type]);
  useEffect(() => {
    const shortcut = event => {if ((event.metaKey || event.ctrlKey) && event.key.toLowerCase() === 'k' && !modal) {event.preventDefault(); searchRef.current?.focus();}};
    window.addEventListener('keydown', shortcut);
    return () => window.removeEventListener('keydown', shortcut);
  }, [modal]);
  useEffect(() => {
    const strip = filmstripRef.current, item = strip?.querySelector('[aria-pressed="true"]');
    if (!strip || !item) return;
    strip.scrollTo({left: item.offsetLeft - strip.offsetLeft - strip.clientWidth / 2 + item.clientWidth / 2, behavior: matchMedia('(prefers-reduced-motion: reduce)').matches ? 'instant' : 'smooth'});
  }, [current?.id, layout]);

  function favorite(id) {
    const next = toggleFavorite(favorites, id), wasSaved = favorites.includes(id);
    setFavorites(next);
    setToast(persist(localStore, FAVORITES_KEY, next) ? (wasSaved ? t.favoriteRemoved : t.favoriteAdded) : t.storage);
  }
  function open(type, item) {
    triggerRef.current = document.activeElement;
    setHd(false); setZoom(false); setHdStatus('idle'); setImageAttempt(0); setModal({type, item});
  }
  function close() {setModal(null);}
  function reset() {setCategory('all'); setStyle('all'); setQuery('');}
  function navigate(next) {setSection(next); reset();}
  function browse(next) {if (next) navigate(next); setPage('library'); window.scrollTo(0, 0);}
  function step(delta) {if (current) setSelectedId(filtered[stepIndex(index, delta, filtered.length)].id);}
  async function signOut() {
    if (signingOut) return;
    setSigningOut(true);
    try {await logoutSession(sessionRef.current); window.location.replace('/login');}
    catch (error) {if (error.status === 401) window.location.replace('/login'); else {setToast(t.logoutError); setSigningOut(false);}}
  }

  return <div className={`showroom ${page === 'home' ? 'home-page' : 'library-page'}`} style={{'--scene': palette.background, '--ink': palette.ink, '--accent': palette.accent || palette.ink}}>
    {sessionState === 'error' && <div className="session-error" role="alert">{t.sessionError}<button onClick={() => location.reload()}>{t.retry}</button></div>}
    {page === 'home' ? <FeaturedShowcase items={featured} selectedId={featuredId} onSelect={setFeaturedId} onBrowse={() => browse()} onFavorites={() => browse('favorites')} onOpen={p => open('image', p)} onInfo={() => open('info')} onLanguage={() => setLang(lang === 'zh' ? 'en' : 'zh')} lang={lang} favorites={favorites} onFavorite={favorite} SafeImage={SafeImage} modalOpen={!!modal} logo={assetURL('/assets/yuanze-mark-compact.webp')} production={production} onSignOut={signOut} signingOut={signingOut || sessionState !== 'ready'}/> : <>
    <header className="topbar">
      <button className="brand" onClick={() => {setPage('home'); window.scrollTo(0, 0);}} aria-label={lang === 'zh' ? '返回精选首页' : 'Back to featured collection'}><img src={assetURL('/assets/yuanze-mark-compact.webp')} alt="YUANZE 源泽"/><span className="back-home-label"><ChevronLeft size={20} aria-hidden="true"/>{lang === 'zh' ? '返回精选' : 'Featured'}</span></button>
      <nav className="main-nav" aria-label={lang === 'zh' ? '主导航' : 'Main navigation'}>
        <button className={section === 'discover' ? 'active' : ''} aria-current={section === 'discover' ? 'page' : undefined} onClick={() => navigate('discover')}>{t.discover}</button>
        <button className={section === 'favorites' ? 'active' : ''} aria-current={section === 'favorites' ? 'page' : undefined} onClick={() => navigate('favorites')}><Heart size={16}/>{t.favorites}<small>{favorites.length}</small></button>
      </nav>
      <div className="header-actions"><button className="language" onClick={() => setLang(lang === 'zh' ? 'en' : 'zh')} aria-label={lang === 'zh' ? 'Switch to English' : '切换为中文'}>{lang === 'zh' ? 'EN' : '中文'}</button><button className="icon-button" onClick={() => open('info')} aria-label={t.info}><Info size={19}/></button>{production && <button className="icon-button" onClick={signOut} disabled={signingOut || sessionState !== 'ready'} aria-label={t.logout}><LogOut size={19}/></button>}</div>
    </header>
    <main>
      <section className="intro">
        <div className="intro-copy"><h1>{section === 'discover' ? t.title : t.favorites}</h1><p>{section === 'discover' ? t.intro : t.favHint}</p></div>
        <div className="browse-tools"><label className="search-box"><Search size={18}/><input ref={searchRef} type="search" value={query} onChange={e => setQuery(e.target.value)} placeholder={t.search} aria-label={t.search}/>{query ? <button className="clear-search" onClick={() => {setQuery(''); searchRef.current.focus();}} aria-label={lang === 'zh' ? '清除搜索' : 'Clear search'}><X size={16}/></button> : <kbd>⌘ K</kbd>}</label><div className="view-toggle" role="group" aria-label={lang === 'zh' ? '展示方式' : 'Display mode'}><button aria-pressed={layout === 'gallery'} aria-label={t.gallery} onClick={() => setLayout('gallery')}><GalleryHorizontalEnd size={19}/></button><button aria-pressed={layout === 'grid'} aria-label={t.all} onClick={() => setLayout('grid')}><LayoutGrid size={19}/></button></div></div>
      </section>
      <section className="filter-bar" aria-label={lang === 'zh' ? '海报筛选' : 'Filter posters'}>
        <div className="category-tabs" role="group" aria-label={lang === 'zh' ? '海报用途' : 'Poster categories'}>{categories.map(([key, zh, en]) => <button key={key} aria-pressed={category === key} className={category === key ? 'active' : ''} onClick={() => setCategory(key)}>{lang === 'zh' ? zh : en}{key === 'all' && <span>{section === 'favorites' ? favorites.length : posters.length}</span>}</button>)}</div>
        <label className="style-picker"><span className="sr-only">{t.theme}</span><select value={style} onChange={e => setStyle(e.target.value)} aria-label={t.theme}>{styles.map(([key, zh, en]) => <option key={key} value={key}>{lang === 'zh' ? zh : en}</option>)}</select></label>
      </section>
      {!current ? <div className="empty-state"><Search size={36} strokeWidth={1.3}/><h2>{section === 'favorites' && !favorites.length ? t.noFavorites : t.empty}</h2><p>{section === 'favorites' && !favorites.length ? t.favHint : t.emptyHint}</p><button className="primary-button" onClick={() => section === 'favorites' && !favorites.length ? navigate('discover') : reset()}>{section === 'favorites' && !favorites.length ? t.start : t.clear}<ArrowRight size={17}/></button></div> : layout === 'gallery' ? <>
        <PosterStage key={stageKey} items={filtered} selectedId={current.id} onSelect={setSelectedId} onOpen={p => open('image', p)} lang={lang} SafeImage={SafeImage}/>
        <section className="poster-detail" aria-live="polite" aria-atomic="true">
          <div className="poster-title"><span className="category-label">{categoryName(current.category)}</span><h2>{current.title[lang].replace(/^liaose\s/i, '')}</h2></div>
          <div className="poster-actions"><button className={`save-button ${favorites.includes(current.id) ? 'is-saved' : ''}`} aria-pressed={favorites.includes(current.id)} onClick={() => favorite(current.id)}><Heart size={19} fill={favorites.includes(current.id) ? 'currentColor' : 'none'}/><span>{favorites.includes(current.id) ? t.saved : t.save}</span></button><button className="primary-button" onClick={() => open('image', current)}>{t.zoom}<ArrowRight size={17}/></button></div>
          <div className="gallery-navigation"><button className="round-button" disabled={filtered.length < 2} onClick={() => step(-1)} aria-label={t.prev}><ChevronLeft size={22}/></button><span><strong>{String(index + 1).padStart(2, '0')}</strong><i>/</i>{String(filtered.length).padStart(2, '0')}</span><button className="round-button" disabled={filtered.length < 2} onClick={() => step(1)} aria-label={t.next}><ChevronRight size={22}/></button></div>
        </section>
        <div className="filmstrip" ref={filmstripRef} aria-label={t.select}>{filtered.map((p, i) => <button key={p.id} aria-label={p.title[lang]} aria-pressed={p.id === current.id} onClick={() => setSelectedId(p.id)}><SafeImage src={p.stripThumb} width={p.stripWidth} height={p.stripHeight} alt="" loading="lazy" fetchPriority="low"/><span>{String(i + 1).padStart(2, '0')}</span></button>)}</div>
      </> : <section className="grid-section"><div className="grid-count">{filtered.length} {t.count}</div><div className="poster-grid">{filtered.map((p, position) => <article key={p.id}><button className="grid-image" onClick={() => open('image', p)} aria-label={`${t.openPoster}: ${p.title[lang]}`}><SafeImage src={p.image} srcSet={p.imageSrcSet} sizes={GRID_SIZES} width={p.imageWidth} height={p.imageHeight} loading={position === 0 ? "eager" : "lazy"} fetchPriority={position === 0 ? "high" : "low"} alt={p.title[lang]}/><span className="grid-expand"><Maximize2 size={18}/></span></button><div className="grid-caption"><div><span className="category-label">{categoryName(p.category)}</span><h2>{p.title[lang].replace(/^liaose\s/i, '')}</h2></div><button className="icon-button" onClick={() => favorite(p.id)} aria-label={favorites.includes(p.id) ? t.saved : t.save} aria-pressed={favorites.includes(p.id)}><Heart size={18} fill={favorites.includes(p.id) ? 'currentColor' : 'none'}/></button></div></article>)}</div></section>}
    </main>
    <footer><span>YUANZE <b>·</b> {lang === 'zh' ? '每一种风格，都值得被看见。' : 'Every style deserves a closer look.'}</span><span>{t.version}{!production && (lang === 'zh' ? ' · 设计预览' : ' · Design preview')}</span></footer></>}
    <dialog ref={dialogRef} className={`modal ${modal?.type === 'image' ? 'image-modal' : 'info-modal'}`} aria-label={modal?.type === 'image' ? modal.item.title[lang] : t.info} onCancel={e => {e.preventDefault(); close();}} onClick={e => {if (e.target === e.currentTarget) close();}}>
      {modal && <div className="modal-inner"><header className="modal-toolbar"><strong>{modal.type === 'image' ? modal.item.title[lang] : t.info}</strong><button className="icon-button" onClick={close} aria-label={t.close}><X size={22}/></button></header>{modal.type === 'image' ? <><div className={`lightbox-image ${zoom ? 'zoomed' : ''}`}><SafeImage key={`${modal.item.id}-${hd}-${imageAttempt}`} src={hd ? modal.item.original : modal.item.image} alt={modal.item.title[lang]} onLoad={() => {if (hd) setHdStatus('loaded');}} onError={() => {if (hd) setHdStatus('error');}}/></div><div className="lightbox-controls"><span>{hdStatus === 'loaded' ? `${modal.item.width} × ${modal.item.height}` : t.fullImage}</span><div><button className="soft-button" aria-pressed={zoom} onClick={() => {setZoom(!zoom); if (!zoom && !hd) {setHd(true); setHdStatus('loading'); setImageAttempt(n => n + 1);}}}>{zoom ? <ZoomOut size={17}/> : <ZoomIn size={17}/>}<span>{zoom ? '100%' : '200%'}</span></button><button className="soft-button" disabled={hdStatus === 'loading' || hdStatus === 'loaded'} onClick={() => {setHd(true); setHdStatus('loading'); setImageAttempt(n => n + 1);}}>{hdStatus === 'loaded' ? <Check size={17}/> : <Maximize2 size={17}/>}<span>{hdStatus === 'loaded' ? t.originalLoaded : hdStatus === 'loading' ? t.originalLoading : hdStatus === 'error' ? t.originalRetry : t.original}</span></button><a className="soft-button" href={production ? `${modal.item.original}?download=${modal.item.id}.webp` : modal.item.original} download={`${modal.item.id}.webp`}><Download size={17}/><span>{t.download}</span></a></div></div></> : <div className="info-content"><img src={assetURL('/assets/yuanze-mark-compact.webp')} alt="源泽"/><h2>{t.demo}</h2><p>{t.infoText}</p><p className="preview-note">{production ? (lang === 'zh' ? `client1.4 · ${featured.length} 款精选展示，${posters.length} 张完整产品海报。首页产品图用于展示，包装细节请查看原海报。` : `client1.4 · ${featured.length} featured products and ${posters.length} original posters. For packaging details, view the original poster.`) : (lang === 'zh' ? `client1.4 设计预览 · ${featured.length} 款精选与 ${posters.length} 张海报。` : `client1.4 design preview · ${featured.length} featured products and ${posters.length} posters.`)}</p><button className="primary-button" onClick={close}>{t.back}<ArrowRight size={17}/></button></div>}</div>}
    </dialog>
    <div className={`toast ${toast ? 'shown' : ''}`} role="status" aria-live="polite"><Check size={17}/>{toast}</div>
  </div>;
}
createRoot(document.getElementById('root')).render(<App/>);
