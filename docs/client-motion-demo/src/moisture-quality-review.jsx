import React, {useRef, useState} from 'react';
import {createRoot} from 'react-dom/client';
import PackagingDetailLoader from './structure/PackagingDetailLoader.jsx';
import {PACKAGING_PRODUCTS} from './structure/packaging-products.js';
import './structure/packaging-shell.css';
import product from '../model-source/collection/poster-049/v2/review-product.json';
import poster from '../../mobile-client-preview/assets/posters/poster-049.webp';
import modelUrl from '../packaging-assets/poster-049-v2.glb?url';
import logo from '../optimized-assets/yuanze-mark-compact.webp';

const item = {id: 'poster-049', title: {zh: '滋润洗发水', en: 'Moisture Shampoo'}, image: poster};
// This entry is served for local review only. The main showroom has its own catalogue.
PACKAGING_PRODUCTS[item.id] = product;
function Review() {
  const posterDialog = useRef(null);
  const [saved, setSaved] = useState(() => sessionStorage.getItem('moisture-quality-saved') === 'yes');
  return <>
    <PackagingDetailLoader item={item} lang="zh" modelUrl={modelUrl}
      logo={logo} saved={saved}
      onFavorite={() => {sessionStorage.setItem('moisture-quality-saved', saved ? 'no' : 'yes'); setSaved(!saved);}}
      onOriginal={() => posterDialog.current.showModal()} onClose={() => location.assign('./')}/>
    <dialog ref={posterDialog} className="poster" aria-label="Moisture Shampoo 原海报">
      <img src={poster} alt="Moisture Shampoo 原海报，透明宽口瓶身与银色完整泵头" />
      <button onClick={() => posterDialog.current.close()}>返回模型</button>
    </dialog>
  </>;
}
createRoot(document.getElementById('root')).render(<Review/>);
