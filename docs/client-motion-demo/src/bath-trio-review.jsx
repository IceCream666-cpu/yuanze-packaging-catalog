import React, {useRef, useState} from 'react';
import {createRoot} from 'react-dom/client';
import PackagingDetailLoader from './structure/PackagingDetailLoader.jsx';
import {PACKAGING_PRODUCTS} from './structure/packaging-products.js';
import './structure/packaging-shell.css';
import product from '../model-source/collection/poster-080/review-product.json';
import poster from '../model-source/collection/poster-080/bath-trio.webp';
import modelUrl from '../packaging-assets/poster-080-v2.glb?url';
import logo from '../optimized-assets/yuanze-mark-compact.webp';

const item = {id: 'poster-080', title: {zh: 'Bath Trio 沐浴护理三件组', en: 'Bath Trio'}, image: poster};
// This entry is served for local review only. The main showroom has its own catalogue.
PACKAGING_PRODUCTS[item.id] = product;
function Review() {
  const posterDialog = useRef(null);
  const [saved, setSaved] = useState(() => sessionStorage.getItem('bath-trio-saved') === 'yes');
  return <>
    <PackagingDetailLoader item={item} lang="zh" modelUrl={modelUrl}
      logo={logo} saved={saved}
      onFavorite={() => {sessionStorage.setItem('bath-trio-saved', saved ? 'no' : 'yes'); setSaved(!saved);}}
      onOriginal={() => posterDialog.current.showModal()} onClose={() => location.assign('./')}/>
    <dialog ref={posterDialog} className="poster" aria-label="Bath Trio 原海报">
      <img src={poster} alt="Bath Trio 三支泵瓶，烟灰蓝沐浴露与两款奶白身体乳并排在条纹毛巾上" />
      <button onClick={() => posterDialog.current.close()}>返回模型</button>
    </dialog>
  </>;
}
createRoot(document.getElementById('root')).render(<Review/>);
