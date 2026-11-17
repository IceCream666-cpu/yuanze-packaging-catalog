import {renderLocalReview} from './local-review.jsx';
import product from '../model-source/collection/poster-085/review-product.json';
import poster from '../model-source/collection/poster-085/daily-hair-ritual-poster-v1.png';
import modelUrl from '../packaging-assets/poster-085-v2.glb?url';

renderLocalReview({
  item: {id: 'poster-085', title: {zh: '铜棕洗护组合', en: 'Daily Hair Ritual'}, image: poster}, product, modelUrl, savedKey: 'daily-hair-ritual-saved',
  posterAlt: "Daily Hair Ritual 原海报，铜棕色泵瓶搭配玫瑰棕软管",
});
