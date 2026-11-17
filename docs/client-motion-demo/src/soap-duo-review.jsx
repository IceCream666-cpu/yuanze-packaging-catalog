import {renderLocalReview} from './local-review.jsx';
import product from '../model-source/collection/poster-082/review-product.json';
import poster from '../model-source/collection/poster-082/soap-clean-duo-v2.png';
import modelUrl from '../packaging-assets/poster-082-v1.glb?url';

renderLocalReview({
  item: {id: 'poster-082', title: {zh: '蓝白洗护组合', en: 'Soap Clean Duo'}, image: poster}, product, modelUrl, savedKey: 'soap-duo-saved',
  posterAlt: "蓝白洗护组合，浅蓝条纹软管与乳白圆盘泵瓶",
});
