import {renderLocalReview} from './local-review.jsx';
import product from '../model-source/collection/poster-012/v2/review-product.json';
import poster from '../../mobile-client-preview/assets/posters/poster-012.webp';
import modelUrl from '../packaging-assets/poster-012-v2.glb?url';

renderLocalReview({
  item: {id: 'poster-012', title: {zh: '双色磨砂膏', en: 'Beach Magic'}, image: poster}, product, modelUrl, savedKey: 'beach-magic-quality-saved',
  posterAlt: 'Beach Magic 原海报，黄粉双色磨砂膏与乳白色完整旋盖',
});
