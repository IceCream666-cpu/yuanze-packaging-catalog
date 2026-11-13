import React, {useRef, useState} from 'react';
import {createRoot} from 'react-dom/client';
import PackagingDetailLoader from './structure/PackagingDetailLoader.jsx';
import {PACKAGING_PRODUCTS} from './structure/packaging-products.js';
import './structure/packaging-shell.css';
import product from '../model-source/collection/poster-067/v2/review-product.json';
import poster from '../../mobile-client-preview/assets/posters/poster-067.webp';
import modelUrl from '../packaging-assets/poster-067-v2.glb?url';
import logo from '../optimized-assets/yuanze-mark-compact.webp';

const item = {id: 'poster-067', title: {zh: '琥珀生姜洗发水', en: 'Amber Ginger Shampoo'}, image: poster};
// This entry is served for local review only. The main showroom has its own catalogue.
PACKAGING_PRODUCTS[item.id] = product;
function Review() {
  const posterDialog = useRef(null);
  const [saved, setSaved] = useState(() => sessionStorage.getItem('amber-ginger-saved') === 'yes');
  return <>
    <PackagingDetailLoader item={item} lang="zh" modelUrl={modelUrl}
      logo={logo} saved={saved}
      onFavorite={() => {sessionStorage.setItem('amber-ginger-saved', saved ? 'no' : 'yes'); setSaved(!saved);}}
      onOriginal={() => posterDialog.current.showModal()} onClose={() => location.assign('./')}/>
    <dialog ref={posterDialog} className="poster" aria-label="Amber Ginger Shampoo 原海报">
      <img src={poster} alt="Amber Ginger Shampoo 原海报，琥珀玻璃、黑色长弧泵嘴与棕色编绳" />
      <button onClick={() => posterDialog.current.close()}>返回模型</button>
    </dialog>
  </>;
}
createRoot(document.getElementById('root')).render(<Review/>);
