import {renderLocalReview} from './local-review.jsx';
import product from '../model-source/collection/poster-086/review-product.json';
import poster from '../model-source/collection/poster-086/scalp-essence-poster-v2.png';
import modelUrl from '../packaging-assets/poster-086-v1.glb?url';

renderLocalReview({
  item: {id: 'poster-086', title: {zh: '头皮精华瓶', en: 'Scalp Essence'}, image: poster}, product, modelUrl, savedKey: 'scalp-essence-saved',
  posterAlt: "Scalp Essence 原海报，奶白长盖与铜棕下段细长圆柱瓶",
});
