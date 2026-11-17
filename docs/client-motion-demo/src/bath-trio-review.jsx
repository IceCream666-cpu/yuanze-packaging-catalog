import {renderLocalReview} from './local-review.jsx';
import product from '../model-source/collection/poster-080/review-product.json';
import poster from '../model-source/collection/poster-080/bath-trio.webp';
import modelUrl from '../packaging-assets/poster-080-v2.glb?url';

renderLocalReview({
  item: {id: 'poster-080', title: {zh: 'Bath Trio 沐浴护理三件组', en: 'Bath Trio'}, image: poster}, product, modelUrl, savedKey: 'bath-trio-saved',
  posterAlt: "Bath Trio 三支泵瓶，烟灰蓝沐浴露与两款奶白身体乳并排在条纹毛巾上",
});
