import {renderLocalReview} from './local-review.jsx';
import product from '../model-source/collection/poster-072/v2/review-product.json';
import poster from '../../mobile-client-preview/assets/posters/poster-072.webp';
import modelUrl from '../packaging-assets/poster-072-v2.glb?url';

renderLocalReview({
  item: {id: 'poster-072', title: {zh: '日常乳液', en: 'Daily Emulsion'}, image: poster}, product, modelUrl, savedKey: 'daily-emulsion-quality-saved',
  posterAlt: "Daily Emulsion 原海报，磨砂玻璃瓶与透明保护罩",
});
