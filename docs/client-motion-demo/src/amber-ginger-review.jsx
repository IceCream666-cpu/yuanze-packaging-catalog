import {renderLocalReview} from './local-review.jsx';
import product from '../model-source/collection/poster-067/v2/review-product.json';
import poster from '../../mobile-client-preview/assets/posters/poster-067.webp';
import modelUrl from '../packaging-assets/poster-067-v2.glb?url';

renderLocalReview({
  item: {id: 'poster-067', title: {zh: '琥珀生姜洗发水', en: 'Amber Ginger Shampoo'}, image: poster}, product, modelUrl, savedKey: 'amber-ginger-saved',
  posterAlt: "Amber Ginger Shampoo 原海报，琥珀玻璃、黑色长弧泵嘴与棕色编绳",
});
