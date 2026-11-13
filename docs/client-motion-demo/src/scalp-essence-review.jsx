import React, {useRef, useState} from 'react';
import {createRoot} from 'react-dom/client';
import PackagingDetailLoader from './structure/PackagingDetailLoader.jsx';
import {PACKAGING_PRODUCTS} from './structure/packaging-products.js';
import './structure/packaging-shell.css';
import product from '../model-source/collection/poster-086/review-product.json';
import poster from '../model-source/collection/poster-086/scalp-essence-poster-v2.png';
import modelUrl from '../packaging-assets/poster-086-v1.glb?url';
import logo from '../optimized-assets/yuanze-mark-compact.webp';

const item = {id: 'poster-086', title: {zh: '头皮精华瓶', en: 'Scalp Essence'}, image: poster};
// This entry is served for local review only. The main showroom has its own catalogue.
PACKAGING_PRODUCTS[item.id] = product;
function Review() {
  const posterDialog = useRef(null);
  const [saved, setSaved] = useState(() => sessionStorage.getItem('scalp-essence-saved') === 'yes');
  return <>
    <PackagingDetailLoader item={item} lang="zh" modelUrl={modelUrl}
      logo={logo} saved={saved}
      onFavorite={() => {sessionStorage.setItem('scalp-essence-saved', saved ? 'no' : 'yes'); setSaved(!saved);}}
      onOriginal={() => posterDialog.current.showModal()} onClose={() => location.assign('./')}/>
    <dialog ref={posterDialog} className="poster" aria-label="Scalp Essence 原海报">
      <img src={poster} alt="Scalp Essence 原海报，奶白长盖与铜棕下段细长圆柱瓶" />
      <button onClick={() => posterDialog.current.close()}>返回模型</button>
    </dialog>
  </>;
}
createRoot(document.getElementById('root')).render(<Review/>);
