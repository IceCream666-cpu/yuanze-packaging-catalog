import React, {useRef, useState} from 'react';
import {createRoot} from 'react-dom/client';
import PackagingDetailLoader from './structure/PackagingDetailLoader.jsx';
import {PACKAGING_PRODUCTS} from './structure/packaging-products.js';
import logo from '../optimized-assets/yuanze-mark-compact.webp';
import './structure/packaging-shell.css';

function LocalReview({item, modelUrl, savedKey, posterAlt}) {
  const posterDialog = useRef(null);
  const [saved, setSaved] = useState(() => sessionStorage.getItem(savedKey) === 'yes');
  return <>
    <PackagingDetailLoader item={item} lang="zh" modelUrl={modelUrl} logo={logo} saved={saved}
      onFavorite={() => {sessionStorage.setItem(savedKey, saved ? 'no' : 'yes'); setSaved(!saved);}}
      onOriginal={() => posterDialog.current.showModal()} onClose={() => location.assign('./')}/>
    <dialog ref={posterDialog} className="poster" aria-label={`${item.title.en} 原海报`}>
      <img src={item.image} alt={posterAlt}/>
      <button onClick={() => posterDialog.current.close()}>返回模型</button>
    </dialog>
  </>;
}

export function renderLocalReview({item, product, ...props}) {
  // Local review entries override their own product without changing the published catalogue.
  PACKAGING_PRODUCTS[item.id] = product;
  createRoot(document.getElementById('root')).render(<LocalReview item={item} {...props}/>);
}
