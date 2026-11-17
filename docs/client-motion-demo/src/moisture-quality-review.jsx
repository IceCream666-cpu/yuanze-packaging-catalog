import {renderLocalReview} from './local-review.jsx';
import product from '../model-source/collection/poster-049/v2/review-product.json';
import poster from '../../mobile-client-preview/assets/posters/poster-049.webp';
import modelUrl from '../packaging-assets/poster-049-v2.glb?url';

renderLocalReview({
  item: {id: 'poster-049', title: {zh: '滋润洗发水', en: 'Moisture Shampoo'}, image: poster}, product, modelUrl, savedKey: 'moisture-quality-saved',
  posterAlt: "Moisture Shampoo 原海报，透明宽口瓶身与银色完整泵头",
});
