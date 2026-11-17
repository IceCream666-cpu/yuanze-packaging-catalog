import {renderLocalReview} from './local-review.jsx';
import product from '../model-source/collection/poster-056/v2/review-product.json';
import poster from '../../mobile-client-preview/assets/posters/poster-056.webp';
import modelUrl from '../packaging-assets/poster-056-v2.glb?url';

renderLocalReview({
  item: {id: 'poster-056', title: {zh: '金色面部护理油', en: 'Golden Face Oil'}, image: poster}, product, modelUrl, savedKey: 'golden-face-oil-quality-saved',
  posterAlt: 'Golden Face Oil 原海报，扁方磨砂瓶与深橄榄绿保护盖',
});
