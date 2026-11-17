import {renderLocalReview} from './local-review.jsx';
import product from '../model-source/collection/poster-082/v2/review-product.json';
import poster from '../../mobile-client-preview/assets/posters/poster-082.webp';
import modelUrl from '../packaging-assets/poster-082-v2.glb?url';

renderLocalReview({
  item: {id: 'poster-082', title: {zh: '蓝白洗护组合', en: 'Soap Clean Duo'}, image: poster}, product, modelUrl, savedKey: 'soap-clean-quality-saved',
  posterAlt: '蓝白洗护组合原海报，浅蓝直印条纹软管、完整翻盖与乳白圆盘泵瓶',
});
