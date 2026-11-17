import {renderLocalReview} from './local-review.jsx';
import product from '../model-source/collection/poster-081/review-product.json';
import poster from '../model-source/collection/poster-081/exfoliating-hand-gel-v1.png';
import modelUrl from '../packaging-assets/poster-081-v1.glb?url';

renderLocalReview({
  item: {id: 'poster-081', title: {zh: '磨砂净手凝露', en: 'Exfoliating Hand Gel'}, image: poster}, product, modelUrl, savedKey: 'hand-gel-saved',
  posterAlt: "磨砂净手凝露，黑色泵头、织物环标与清透厚底瓶身",
});
