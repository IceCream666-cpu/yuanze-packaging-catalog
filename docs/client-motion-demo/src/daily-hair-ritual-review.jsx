import React, {useRef, useState} from 'react';
import {createRoot} from 'react-dom/client';
import PackagingDetailLoader from './structure/PackagingDetailLoader.jsx';
import {PACKAGING_PRODUCTS} from './structure/packaging-products.js';
import './structure/packaging-shell.css';
import product from '../model-source/collection/poster-085/review-product.json';
import poster from '../model-source/collection/poster-085/daily-hair-ritual-poster-v1.png';
import modelUrl from '../packaging-assets/poster-085-v2.glb?url';
import logo from '../optimized-assets/yuanze-mark-compact.webp';

const item = {id: 'poster-085', title: {zh: '铜棕洗护组合', en: 'Daily Hair Ritual'}, image: poster};
// This entry is served for local review only. The main showroom has its own catalogue.
PACKAGING_PRODUCTS[item.id] = product;
function Review() {
  const posterDialog = useRef(null);
  const [saved, setSaved] = useState(() => sessionStorage.getItem('daily-hair-ritual-saved') === 'yes');
  return <>
    <PackagingDetailLoader item={item} lang="zh" modelUrl={modelUrl}
      logo={logo} saved={saved}
      onFavorite={() => {sessionStorage.setItem('daily-hair-ritual-saved', saved ? 'no' : 'yes'); setSaved(!saved);}}
      onOriginal={() => posterDialog.current.showModal()} onClose={() => location.assign('./')}/>
    <dialog ref={posterDialog} className="poster" aria-label="Daily Hair Ritual 原海报">
      <img src={poster} alt="Daily Hair Ritual 原海报，铜棕色泵瓶搭配玫瑰棕软管" />
      <button onClick={() => posterDialog.current.close()}>返回模型</button>
    </dialog>
  </>;
}
createRoot(document.getElementById('root')).render(<Review/>);
