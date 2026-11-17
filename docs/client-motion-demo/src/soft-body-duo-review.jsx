import {renderLocalReview} from './local-review.jsx';
import product from '../model-source/collection/poster-084/review-product.json';
import poster from '../model-source/collection/poster-084/soft-body-duo-poster-v1.png';
import modelUrl from '../packaging-assets/poster-084-v2.glb?url';

renderLocalReview({
  item: {id: 'poster-084', title: {zh: '蓝粉身体护理组合', en: 'Soft Body Duo'}, image: poster}, product, modelUrl, savedKey: 'soft-body-duo-saved',
  posterAlt: "Soft Body Duo 原海报，透明玻璃瓶内呈蓝色和粉色料体",
});
