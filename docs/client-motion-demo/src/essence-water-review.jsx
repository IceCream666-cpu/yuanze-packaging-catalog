import {renderLocalReview} from './local-review.jsx';
import product from '../model-source/collection/poster-068/v3/review-product.json';
import poster from '../../mobile-client-preview/assets/posters/poster-068.webp';
import modelUrl from '../packaging-assets/poster-068-v3.glb?url';

renderLocalReview({
  item: {id: 'poster-068', title: {zh: '精华水', en: 'Essence Water'}, image: poster}, product, modelUrl, savedKey: 'essence-water-saved',
  posterAlt: "Essence Water 原海报，透明扁方玻璃、淡紫折面盖与银色颈圈",
});
