import {renderLocalReview} from './local-review.jsx';
import product from '../model-source/collection/poster-081/v2/review-product.json';
import poster from '../../mobile-client-preview/assets/posters/poster-081.webp';
import modelUrl from '../packaging-assets/poster-081-v2.glb?url';

renderLocalReview({
  item: {id: 'poster-081', title: {zh: '磨砂净手凝露', en: 'Exfoliating Hand Gel'}, image: poster}, product, modelUrl, savedKey: 'hand-gel-quality-saved',
  posterAlt: '磨砂净手凝露原海报，黑色完整泵头、织物环标与侧旗、透明厚底瓶身',
});
