import {renderLocalReview} from './local-review.jsx';
import product from '../model-source/collection/poster-084/v3/review-product.json';
import poster from '../../mobile-client-preview/assets/posters/poster-084.webp';
import modelUrl from '../packaging-assets/poster-084-v3.glb?url';

renderLocalReview({
  item: {id: 'poster-084', title: {zh: '蓝粉身体护理组合', en: 'Soft Body Duo'}, image: poster}, product, modelUrl, savedKey: 'soft-body-quality-saved',
  posterAlt: 'Soft Body Duo 原海报，透明玻璃双瓶，蓝粉色为料体颜色',
});
