import React, {useCallback, useEffect, useMemo, useRef, useState} from 'react';
import {ArrowLeft, ArrowUpRight, Box, Heart, Search, X} from 'lucide-react';
import PackagingDetail from '../src/structure/PackagingDetail.jsx';
import {posters, featured, logo, getModelRequest, getSceneModule} from './assets.js';
import './portfolio.css';

const posterById = new Map(posters.map(item => [item.id, item]));
const modelItems = featured.map(item => ({...posterById.get(item.id), ...item}));
const searchable = item => [item.name, item.title?.zh, item.title?.en, item.kind?.zh, item.kind?.en, item.id].filter(Boolean).join(' ').toLocaleLowerCase();
const posterTitle = item => item?.title?.zh || item?.name || '产品海报';

export default function Portfolio() {
  const [section, setSection] = useState('models');
  const [query, setQuery] = useState('');
  const [modelId, setModelId] = useState(null);
  const [poster, setPoster] = useState(null);
  const [saved, setSaved] = useState(() => new Set());
  const [posterFailed, setPosterFailed] = useState(false);
  const modelDialog = useRef(null);
  const posterDialog = useRef(null);
  const modelTrigger = useRef(null);
  const posterTrigger = useRef(null);
  const searchInput = useRef(null);
  const model = modelItems.find(item => item.id === modelId);
  const requestModel = useCallback(() => getModelRequest(modelId), [modelId]);
  const items = section === 'models' ? modelItems : posters;
  const results = useMemo(() => {
    const words = query.trim().toLocaleLowerCase().split(/\s+/).filter(Boolean);
    return items.filter(item => words.every(word => searchable(item).includes(word)));
  }, [items, query]);

  useEffect(() => {
    if (modelId && !modelDialog.current.open) modelDialog.current.showModal();
  }, [modelId]);

  useEffect(() => {
    if (poster && !posterDialog.current.open) posterDialog.current.showModal();
  }, [poster]);

  useEffect(() => {
    if (!modelId && !poster) return;
    const previous = document.body.style.overflow;
    document.body.style.overflow = 'hidden';
    return () => {document.body.style.overflow = previous;};
  }, [modelId, poster]);

  function openModel(item) {
    modelTrigger.current = document.activeElement;
    setModelId(item.id);
  }

  function closeModel() {
    modelDialog.current?.close();
    setModelId(null);
    requestAnimationFrame(() => modelTrigger.current?.focus({preventScroll: true}));
  }

  function openPoster(item) {
    posterTrigger.current = document.activeElement;
    setPosterFailed(false);
    setPoster(posterById.get(item.id) || item);
  }

  function closePoster() {
    posterDialog.current?.close();
    setPoster(null);
    requestAnimationFrame(() => posterTrigger.current?.focus({preventScroll: true}));
  }

  function toggleSaved(id) {
    setSaved(previous => {
      const next = new Set(previous);
      if (next.has(id)) next.delete(id); else next.add(id);
      return next;
    });
  }

  const hero = modelItems[0];

  return <>
    <div className="portfolio">
      <a className="pf-skip" href="#collection">跳转至作品</a>
      <header className="pf-header">
        <div className="pf-brand" aria-label="源泽包材作品集">
          <img src={logo} alt="" />
          <div><strong>源泽</strong><span>包材作品集</span></div>
        </div>
        <nav className="pf-navigation" aria-label="作品分类">
          <button type="button" aria-pressed={section === 'models'} onClick={() => setSection('models')}>3D 作品<span>{modelItems.length}</span></button>
          <button type="button" aria-pressed={section === 'posters'} onClick={() => setSection('posters')}>设计海报<span>{posters.length}</span></button>
        </nav>
        <span className="pf-header-note">交互作品 · 离线珍藏</span>
      </header>

      <main>
        {section === 'models' && <section className="pf-introduction" aria-labelledby="portfolio-heading">
          <div className="pf-introduction-copy">
            <h1 id="portfolio-heading">让包材，<br />立体呈现。</h1>
            <p>从完整外观到分层结构，<br className="pf-mobile-break" />近看每一件作品的材质与细节。</p>
            <button type="button" className="pf-primary" onClick={() => openModel(hero)}>进入 3D 体验<ArrowUpRight size={20} aria-hidden="true" /></button>
            <span className="pf-interaction-hint">拖拽旋转 · 滑动展开</span>
          </div>
          <button type="button" className="pf-hero-art" onClick={() => openModel(hero)} aria-label={`进入 ${hero.name} 3D 体验`} style={{background: hero.background, color: hero.ink}}>
            <img src={hero.image} alt={hero.name} fetchPriority="high" />
            <span className="pf-hero-caption"><span>{hero.name}</span><Box size={20} aria-hidden="true" /></span>
          </button>
        </section>}

        <section className="pf-collection" id="collection" aria-labelledby="collection-heading">
          <div className="pf-collection-header">
            <div>
              <h2 id="collection-heading">{section === 'models' ? '探索 3D 作品' : '设计海报'}</h2>
              <p>{section === 'models' ? `${modelItems.length} 款交互模型，逐一旋转、展开与细看。` : `${posters.length} 张完整海报，保留原始构图与高清细节。`}</p>
            </div>
            <div className="pf-search">
              <Search size={19} aria-hidden="true" />
              <label className="pf-sr-only" htmlFor="portfolio-search">搜索中英文产品名称</label>
              <input id="portfolio-search" ref={searchInput} value={query} onChange={event => setQuery(event.target.value)} type="search" placeholder="搜索中英文产品名称" autoComplete="off" />
              {query && <button type="button" aria-label="清除搜索" onClick={() => {setQuery(''); searchInput.current?.focus();}}><X size={17} aria-hidden="true" /></button>}
            </div>
          </div>
          <p className="pf-result-count" role="status" aria-live="polite">{query ? `找到 ${results.length} ${section === 'models' ? '款作品' : '张海报'}` : `全部 ${results.length} ${section === 'models' ? '款' : '张'}`}</p>

          {results.length > 0 ? <div className={`pf-grid ${section === 'posters' ? 'pf-grid--posters' : ''}`}>
            {results.map(item => <article className="pf-work" key={item.id}>
              <button type="button" className={`pf-work-image ${section === 'models' ? 'pf-work-image--model' : ''}`} onClick={() => section === 'models' ? openModel(item) : openPoster(item)} aria-label={section === 'models' ? `查看 ${item.name} 3D 模型` : `查看${posterTitle(item)}完整海报`} style={section === 'models' ? {background: item.background} : undefined}>
                <img src={section === 'models' ? item.image : (item.image || item.smallImage)} alt="" loading="lazy" decoding="async" />
                <span className="pf-open"><span>{section === 'models' ? '探索 3D' : '查看海报'}</span><ArrowUpRight size={20} aria-hidden="true" /></span>
              </button>
              <div className="pf-work-caption">
                <div><h3><button type="button" onClick={() => section === 'models' ? openModel(item) : openPoster(item)}>{section === 'models' ? item.name : posterTitle(item)}</button></h3><p>{section === 'models' ? item.kind?.zh : item.title?.en}</p></div>
                <button type="button" className="pf-favorite" onClick={() => toggleSaved(item.id)} aria-pressed={saved.has(item.id)} aria-label={`${saved.has(item.id) ? '取消收藏' : '收藏'}${item.name || posterTitle(item)}`}><Heart size={20} fill={saved.has(item.id) ? 'currentColor' : 'none'} aria-hidden="true" /></button>
              </div>
            </article>)}
          </div> : <div className="pf-empty"><h3>没有找到这件作品</h3><p>试试产品的中文名或英文名，也可以清除搜索查看全部。</p><button type="button" className="pf-text-button" onClick={() => {setQuery(''); searchInput.current?.focus();}}>清除搜索</button></div>}
        </section>
      </main>

      <footer className="pf-footer"><span>YUANZE · 源泽包材作品集</span><p>3D 为外观与结构展示示意，以实物为准。</p></footer>
    </div>

    <dialog className="pf-model-dialog" ref={modelDialog} aria-label={model ? `${model.name} 交互模型` : '交互模型'} onCancel={event => {event.preventDefault(); closeModel();}}>
      {model && <PackagingDetail key={model.id} item={model} lang="zh" onClose={closeModel} onOriginal={() => openPoster(model)} onFavorite={() => toggleSaved(model.id)} saved={saved.has(model.id)} logo={logo} getModelRequest={requestModel} getSceneModule={getSceneModule} />}
    </dialog>

    <dialog className="pf-poster-dialog" ref={posterDialog} aria-labelledby="poster-dialog-title" onCancel={event => {event.preventDefault(); event.stopPropagation(); closePoster();}}>
      {poster && <div className="pf-poster-layout">
        <header className="pf-poster-header"><div><h2 id="poster-dialog-title">{posterTitle(poster)}</h2><p>完整原海报</p></div><button type="button" className="pf-dialog-close" onClick={closePoster} aria-label={model ? '返回 3D 模型' : '关闭原海报'}><X size={23} aria-hidden="true" /></button></header>
        <div className="pf-poster-image">{posterFailed ? <p role="alert">这张海报未能显示，请关闭后重新打开。</p> : <img src={poster.original || poster.image} alt={posterTitle(poster)} onError={() => setPosterFailed(true)} />}</div>
        <footer className="pf-poster-footer"><button type="button" className="pf-text-button" onClick={closePoster}><ArrowLeft size={18} aria-hidden="true" />{model ? '返回 3D 模型' : '返回海报作品'}</button><a className="pf-download" href={poster.original || poster.image} target="_blank" rel="noopener noreferrer"><ArrowUpRight size={18} aria-hidden="true" />打开高清原图</a></footer>
      </div>}
    </dialog>
  </>;
}
