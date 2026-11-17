import {renderLocalReview} from './local-review.jsx';
import product from '../model-source/collection/poster-085/v3/review-product.json';
import poster from '../../mobile-client-preview/assets/posters/poster-085.webp';
import modelUrl from '../packaging-assets/poster-085-v3.glb?url';

renderLocalReview({
  item: {id: 'poster-085', title: {zh: '铜棕洗护组合', en: 'Daily Hair Ritual'}, image: poster}, product, modelUrl, savedKey: 'daily-hair-quality-saved',
  posterAlt: '铜棕洗护组合原海报，乳白完整泵瓶与玫瑰铜色软管，装饰层和字标分层',
});
