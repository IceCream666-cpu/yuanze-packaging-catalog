import {renderLocalReview} from './local-review.jsx';
import product from '../model-source/collection/poster-071/v2/review-product.json';
import poster from '../../mobile-client-preview/assets/posters/poster-071.webp';
import modelUrl from '../packaging-assets/poster-071-v2.glb?url';

renderLocalReview({
  item: {id: 'poster-071', title: {zh: '长颈雕塑泵瓶', en: 'Sculptural Pump'}, image: poster}, product, modelUrl, savedKey: 'sculptural-pump-saved',
  posterAlt: "Sculptural Pump 原海报，乳白长颈瓶身与细纹泵头",
});
