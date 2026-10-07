import {requestJSON} from './api-client.js';
import {t, getLanguage, setLanguage, onLanguageChange, installLanguageSwitch, registerTranslations} from './i18n.js';

const $ = selector => document.querySelector(selector);
const esc = value => String(value ?? '').replace(/[&<>"']/g, char => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[char]));
const copy = {
  '源泽':'YUANZE','广州源泽药业有限公司':'Guangzhou Yuanze Pharmaceutical Co., Ltd.',
  '包材选型库':'Packaging catalogue','源泽包材库':'YUANZE packaging catalogue','包材导航':'Packaging navigation',
  '跳至包材内容':'Skip to packaging','包材分区':'Application area','面部':'Face','身体／头部':'Body / Hair',
  '可与材质、容量等条件联合检索':'Combine with material, capacity and other filters',
  '分类浏览':'Browse categories','源泽 · 包材展厅':'YUANZE · Packaging showroom',
  '让每一个想法，找到合适的形态。':'Find the right form for every idea.',
  '包材展厅 / 包材选型库':'Showroom / Packaging catalogue','退出登录':'Log out',
  '为每一种配方，找到合适的包装。':'The right packaging for every formula.',
  '按材质、容量与瓶型，探索包材灵感。':'Explore packaging by material, capacity and bottle type.',
  '开始选型':'Explore collection','精选包材':'Featured packaging',
  '从产品编号到理想瓶型，轻松查找合适的包材。':'Find the right packaging by product code, shape and specification.',
  '检索条件':'Search filters','检索包材':'Search packaging','搜索产品编号、材质、规格或用途':'Search product code, material, specification or use',
  '搜索':'Search','重置':'Reset','筛选项可多选，同一项满足任一条件，不同项同时满足。':'Select multiple options. Match any option within a filter, and all selected filters.',
  '已选筛选':'Selected filters','筛选结果':'Search results','包材列表':'Packaging collection',
  '正在加载…':'Loading…','清除筛选':'Clear filters','重新加载':'Retry','产品列表分页':'Catalogue pages',
  '上一页':'Previous','下一页':'Next','跳至':'Jump to','跳转页码':'Page number','前往':'Go',
  '包材详情':'Packaging details','关闭详情':'Close details','关闭':'Close','包材图片':'Packaging image',
  '图片暂时无法显示，请稍后再试。':'This image is unavailable. Please try again later.',
  '图片暂时无法显示':'Image currently unavailable','上一张图片':'Previous image','下一张图片':'Next image',
  '产品规格':'Product specifications','收起侧栏':'Hide sidebar','展开侧栏':'Show sidebar','关闭侧栏':'Close sidebar',
  '材质':'Material','规格':'Specification','瓶型':'Bottle type','用途':'Uses','包材类型':'Category',
  '净含量':'Net content','使用部位':'Application area','产品编号':'Product code','查看详情':'View details',
  '全部分类':'All categories','不限材质':'All materials','不限规格':'All specifications','不限瓶型':'All bottle types','不限用途':'All uses',
  '清空本项':'Clear selection','没有匹配的选项':'No matching options','查找{label}…':'Find {label}…','筛选{label}选项':'Search {label} options',
  '{label}，可多选':'{label}, multiple selections allowed','移除{label}：{value}':'Remove {label}: {value}',
  '查看{code}详情':'View details for {code}','第 {number} 张图片':'Image {number}',
  '{count} 张图片':'{count} images','找到 {count} 款包材':'{count} packaging items',
  '第 {start}–{end} 条 · 第 {page} / {pages} 页':'Items {start}–{end} · Page {page} / {pages}',
  '第 {number} 页':'Page {number}','净含量：{capacity}':'Net content: {capacity}',
  '暂无匹配的包材':'No matching packaging','试试调整搜索关键词或清除部分筛选条件。':'Try another keyword or remove a filter.',
  '更多包材，即将呈现':'More packaging to discover soon','欢迎稍后再来看看。':'Please check back later.',
  '暂时无法加载包材，请检查网络后重试。':'Unable to load the catalogue. Check your connection and try again.',
  '暂时无法退出，请检查网络后重试。':'Unable to log out. Check your connection and try again.',
  '暂时无法打开页面，请检查网络后重试。':'Unable to open the page. Check your connection and try again.',
  '包材':'Packaging',
  '我的收藏':'My favourites','意向清单':'Shortlist','收藏':'Save','已收藏':'Saved','加入意向':'Add to shortlist','已加入意向':'Shortlisted',
  '加入对比':'Compare','已加入对比':'Selected for comparison','对比':'Compare','包材对比':'Packaging comparison',
  '最多选择四款，可对照图片、材质、容量和产品规格。':'Compare up to four items by image, material, capacity and specifications.',
  '最多可同时对比四款包材。':'You can compare up to four packaging items at a time.',
  '请先选择需要对比的包材。':'Select packaging items to compare first.',
  '显示方式':'Display mode','网格':'Grid','列表':'List','每页':'Per page','每页数量':'Items per page',
  '导出当前页':'Export this page','导出意向清单':'Export shortlist','返回全部包材':'Back to all packaging',
  '收藏和意向清单仅在本次页面打开期间保留。':'Favourites and shortlist are kept only while this page remains open.',
  '咨询所选包材':'Enquire about shortlist','复制以下产品编号和规格，发送给您的业务员咨询。':'Copy these product codes and specifications and send them to your sales contact.',
  '咨询内容':'Enquiry details','复制咨询内容':'Copy enquiry','已复制，可发送给业务员。':'Copied. You can send it to your sales contact.',
  '请手动选中并复制咨询内容。':'Please select and copy the enquiry text manually.',
  '上传图片找相似':'Find similar by image','以图找包材':'Search by image','查找相似包材':'Find similar packaging',
  '上传瓶型或包材图片，查找客户展厅中可展示的相似包材。':'Upload a packaging image to find similar items available in the customer showroom.',
  '选择图片（JPG、PNG、WebP，最大 6 MB）':'Choose an image (JPG, PNG or WebP, up to 6 MB)',
  '请选择 JPG、PNG 或 WebP 图片，文件不超过 6 MB。':'Choose a JPG, PNG or WebP image no larger than 6 MB.',
  '暂时无法搜图，请稍后重试。':'Image search is unavailable. Please try again later.',
  '图片相似结果':'Similar-image results','全部分区':'All application areas',
  '筛选条件':'Filters',
  '暂无收藏':'No favourites yet','点击包材卡片上的收藏按钮，将喜欢的款式保留在本次浏览中。':'Save items from their cards to keep them during this visit.',
  '意向清单为空':'Your shortlist is empty','将感兴趣的包材加入意向清单，即可一起咨询业务员。':'Add packaging to your shortlist to enquire about several items together.',
};
const categories = {'瓶类':'Bottles','罐与广口盒':'Jars & wide-mouth containers','软管':'Tubes','泵头与喷头':'Pumps & sprayers','盖与其他配件':'Caps & accessories','滴管与滴管瓶':'Droppers & dropper bottles','袋类':'Pouches','外包装':'Outer packaging','标签辅材':'Labels & accessories','套装':'Sets','其他':'Other'};
const bottles = {'圆瓶':'Round bottle','方瓶':'Square bottle','异形瓶':'Shaped bottle','广口瓶':'Wide-mouth bottle','真空瓶':'Airless bottle','泡沫瓶':'Foam bottle','喷雾瓶':'Spray bottle','滴管瓶':'Dropper bottle','膏霜罐':'Cream jar','乳液瓶':'Lotion bottle','香水瓶':'Perfume bottle','滚珠瓶':'Roll-on bottle','安瓿瓶':'Ampoule'};
const materials = {'玻璃':'Glass','PET':'PET','PETG':'PETG','PE':'PE','HDPE':'HDPE','LDPE':'LDPE','PP':'PP','PMMA':'PMMA','AS':'AS','ABS':'ABS','PS':'PS','PVC':'PVC','铝':'Aluminium','纸':'Paper','塑料（待细分）':'Plastic (unspecified)','硅胶':'Silicone','橡胶':'Rubber','不锈钢':'Stainless steel','无纺布':'Nonwoven fabric','铝塑复合':'Aluminium-plastic composite'};
const uses = {'洁面':'Facial cleanser','卸妆':'Makeup remover','精华液':'Serum','爽肤水':'Toner','化妆水':'Skin toner','面霜':'Face cream','眼霜':'Eye cream','眼部精华':'Eye serum','面膜':'Face mask','唇部护理':'Lip care','防晒':'Sunscreen','粉底液':'Liquid foundation','底妆':'Base makeup','唇彩':'Lip colour','眉妆':'Brow makeup','睫毛产品':'Lash products','洗手液':'Hand wash','洗发水':'Shampoo','护发素':'Hair conditioner','发膜':'Hair mask','头皮护理':'Scalp care','头发造型':'Hair styling','染发':'Hair dye','沐浴露':'Body wash','身体乳':'Body lotion','身体霜':'Body cream','身体油':'Body oil','身体磨砂':'Body scrub','护手霜':'Hand cream','手足护理':'Hand & foot care','护足霜':'Foot cream','脱毛':'Hair removal','止汗除臭':'Deodorant','香水':'Perfume','身体香氛':'Body fragrance','香氛':'Fragrance','美甲':'Nail care','口腔护理':'Oral care','精油':'Essential oil','乳液':'Lotion','膏霜':'Cream','凝胶':'Gel','洗护':'Personal care','洗衣液':'Laundry detergent','家居清洁':'Household cleaning','水剂':'Water-based formulas','油剂':'Oil-based formulas','粉体':'Powder'};
const specs = {'口径':'Neck diameter','瓶高':'Bottle height','高度':'Height','直径':'Diameter','底径':'Base diameter','长度':'Length','宽度':'Width','厚度':'Thickness','重量':'Weight','满口容量':'Brimful capacity'};
registerTranslations(Object.fromEntries(Object.entries({...copy,...categories,...bottles,...materials,...uses,...specs}).map(([zh,en]) => [zh,{zh,en}])));

const facetConfig = {
  category:{source:'categories',label:'包材类型',placeholder:'全部分类',values:categories},
  section:{source:'sections',label:'包材分区',placeholder:'全部分区',values:{face:'Face','body-head':'Body / Hair'}},
  material:{source:'materials',label:'材质',placeholder:'不限材质',values:materials},
  capacity:{source:'capacities',label:'规格',placeholder:'不限规格'},
  bottle:{source:'bottleTypes',label:'瓶型',placeholder:'不限瓶型',values:bottles},
  use:{source:'uses',label:'用途',placeholder:'不限用途',values:uses},
};
const selected = Object.fromEntries(Object.keys(facetConfig).map(key => [key,[]]));
let session = null, items = [], facets = {}, heroItems = [], query = '', page = 1, pages = 1, total = 0;
let busy = false, loaded = false, noticeKey = '', requestSequence = 0, controller = null, retryPage = 1;
let previewItem = null, previewIndex = 0, previousFocus = null;
let mobile = matchMedia('(max-width: 760px)').matches, sidebarOpen = !mobile;
// Per-tab memory deliberately avoids leaking a shared customer's selections
// through browser storage to the next visitor using the same account.
const favourites = new Map(), shortlist = new Map(), comparison = new Map();
let collection = 'catalog', pageSize = 24, imageResults = [], imageRequest = 0, imageController = null, filtersExpanded = false;
const embedded = new URLSearchParams(location.search).get('showroom') === '1';
document.documentElement.classList.toggle('embedded-showroom',embedded);
const capacityPattern = /^\d+(?:\.\d+)?\s*(?:mL|ml|L|g|kg)$/;
const specPattern = /^\d+(?:\.\d+)?\s*(?:mm|cm|m|g|kg|mL|ml|L)$/;
const known = (value, values) => typeof value === 'string' && Object.hasOwn(values, value) ? value : '';
const safeArray = (value, values) => Array.isArray(value) ? [...new Set(value.map(item => known(item,values)).filter(Boolean))] : [];
function imageURL(image) {
  // Customer images always use opaque allowlisted URLs, never original paths.
  const value = typeof image?.url === 'string' ? image.url : '';
  return /^\/client-media\/[A-Za-z0-9_-]+\.(?:jpg|jpeg|png|webp)$/.test(value) ? value : '';
}
function safeItem(item) {
  return {
    id:typeof item?.id === 'string' && /^[A-Za-z0-9_-]{1,200}$/.test(item.id) ? item.id : '',
    productCode:/^YZ-BC-\d{6,}$/.test(item?.productCode) ? item.productCode : '',
    capacity:typeof item?.capacity === 'string' && capacityPattern.test(item.capacity) ? item.capacity : '',
    category:known(item?.category,categories), bottleType:known(item?.bottleType,bottles),
    materials:safeArray(item?.materials,materials), uses:safeArray(item?.uses,uses), sections:safeArray(item?.sections,facetConfig.section.values),
    specifications:Array.isArray(item?.specifications) ? item.specifications.filter(spec => known(spec?.label,specs) && typeof spec.value === 'string' && specPattern.test(spec.value)).map(({label,value}) => ({label,value})) : [],
    images:Array.isArray(item?.images) ? item.images.map(image => ({url:imageURL(image)})).filter(image => image.url) : [],
  };
}
function safeFacets(input) {
  return Object.fromEntries(Object.entries(facetConfig).map(([key,{source,values}]) => [key,values ? safeArray(input?.[source],values) : Array.isArray(input?.[source]) ? [...new Set(input[source].filter(value => typeof value === 'string' && capacityPattern.test(value)))] : []]));
}
function label(key, value) {return key === 'section' ? t(value === 'face' ? '面部' : '身体／头部') : t(value);}
function joined(values) {return values.map(value => t(value)).join(getLanguage() === 'en' ? ', ' : '、');}
function itemName(item) {return [t(item.bottleType || item.category || '包材'),item.capacity].filter(Boolean).join(' · ');}
function hasFilters() {return Boolean(query || Object.values(selected).some(values => values.length));}
function showNotice(key = '') {noticeKey = key;$('#notice').textContent = key ? t(key) : '';$('#notice').hidden = !key;}
function setBusy(value) {
  busy = value;$('#gallery').setAttribute('aria-busy',String(value));
  $('#previous').disabled = value || page <= 1;$('#next').disabled = value || page >= pages;
  $('#jumpForm').querySelectorAll('input,button').forEach(el => el.disabled = value);
  $('#pageButtons').querySelectorAll('button').forEach(el => el.disabled = value);
  $('#retry').disabled = value;
  renderStatus();
}
function renderText() {
  document.title = `${t('包材选型库')} · YUANZE`;
  document.querySelectorAll('[data-client-text]').forEach(el => {el.textContent = t(el.dataset.clientText);});
  document.querySelectorAll('[data-client-label]').forEach(el => {el.setAttribute('aria-label',t(el.dataset.clientLabel));});
  document.querySelectorAll('[data-client-placeholder]').forEach(el => {el.placeholder = t(el.dataset.clientPlaceholder);});
  showNotice(noticeKey);updateSidebar();
}
function renderStatus() {
  $('#resultCount').textContent = loaded ? t('找到 {count} 款包材',{count:total}) : '';
  $('#catalogStatus').textContent = busy ? t('正在加载…') : total && loaded ? t('第 {start}–{end} 条 · 第 {page} / {pages} 页',{start:(page-1)*pageSize+1,end:Math.min(page*pageSize,total),page,pages}) : '';
}
function renderSidebar() {
  $('#categorySidebar').innerHTML = `<button type="button" class="side-facet ${selected.category.length ? '' : 'active'}" data-all-categories aria-pressed="${!selected.category.length}"><span>${esc(t('全部分类'))}</span><span aria-hidden="true">›</span></button>` + (facets.category || []).map(value => `<button type="button" class="side-facet ${selected.category.includes(value) ? 'active' : ''}" data-category="${esc(value)}" aria-pressed="${selected.category.includes(value)}"><span>${esc(t(value))}</span><span aria-hidden="true">${selected.category.includes(value) ? '✓' : '›'}</span></button>`).join('');
  document.querySelectorAll('[data-section]').forEach(button => {const active = selected.section.includes(button.dataset.section);button.classList.toggle('active',active);button.setAttribute('aria-pressed',String(active));});
  $('#allCatalog').classList.toggle('active',collection === 'catalog' && !hasFilters());
  $('#favoritesView').classList.toggle('active',collection === 'favourites');
  $('#shortlistView').classList.toggle('active',collection === 'shortlist');
}
function renderFilters() {
  const focused = document.activeElement;
  const focusFacet = focused?.closest('.multi-filter')?.dataset.facet;
  const focusValue = focused?.dataset.filter ? focused.value : null;
  const focusSearch = focused?.matches('.multi-option-search');
  const open = new Map([...document.querySelectorAll('.multi-filter')].map(el => [el.dataset.facet,{open:el.open,search:el.querySelector('.multi-option-search').value,scroll:el.querySelector('.multi-options').scrollTop}]));
  $('#filterGrid').innerHTML = Object.keys(facetConfig).map(key => {
    const config = facetConfig[key], values = [...new Set([...(facets[key] || []),...selected[key]])];
    const summary = selected[key].length ? selected[key].map(value => label(key,value)).join(getLanguage() === 'en' ? ', ' : '、') : t(config.placeholder);
    return `<div class="filter-field"><span class="filter-field-label" id="facet-label-${key}">${esc(t(config.label))}</span><details class="multi-filter" data-facet="${key}"><summary aria-labelledby="facet-label-${key} facet-summary-${key}"><span class="multi-summary" id="facet-summary-${key}" title="${esc(summary)}">${esc(summary)}</span>${selected[key].length ? `<span class="multi-count">${selected[key].length}</span>` : ''}</summary><div class="multi-menu"><input type="search" class="multi-option-search" placeholder="${esc(t('查找{label}…',{label:t(config.label)}))}" aria-label="${esc(t('筛选{label}选项',{label:t(config.label)}))}"><button type="button" class="quiet" data-clear-facet="${key}">${esc(t('清空本项'))}</button><div class="multi-options" role="group" aria-label="${esc(t('{label}，可多选',{label:t(config.label)}))}">${values.map(value => `<label class="multi-option"><input type="checkbox" data-filter="${key}" value="${esc(value)}" ${selected[key].includes(value) ? 'checked' : ''}><span>${esc(label(key,value))}</span></label>`).join('')}</div><p class="multi-empty" hidden>${esc(t('没有匹配的选项'))}</p></div></details></div>`;
  }).join('');
  for (const el of document.querySelectorAll('.multi-filter')) {const saved = open.get(el.dataset.facet);if (saved) {el.open = saved.open;el.querySelector('.multi-option-search').value = saved.search;filterOptions(el.querySelector('.multi-option-search'));el.querySelector('.multi-options').scrollTop = saved.scroll;}}
  if (focusFacet) {
    const panel = [...document.querySelectorAll('.multi-filter')].find(el => el.dataset.facet === focusFacet);
    const target = focusSearch ? panel?.querySelector('.multi-option-search') : focusValue !== null ? [...(panel?.querySelectorAll('[data-filter]') || [])].find(input => input.value === focusValue) : focused?.tagName === 'SUMMARY' ? panel?.querySelector('summary') : panel?.querySelector('[data-clear-facet]');
    target?.focus({preventScroll:true});
  }
  const chips = Object.entries(selected).flatMap(([key,values]) => values.map(value => `<button type="button" class="filter-chip" data-clear-filter="${key}" data-filter-value="${esc(value)}" aria-label="${esc(t('移除{label}：{value}',{label:t(facetConfig[key].label),value:label(key,value)}))}">${esc(t(facetConfig[key].label))}: ${esc(label(key,value))}<span aria-hidden="true">×</span></button>`));
  $('#activeFilters').innerHTML = chips.join('');$('#activeFilters').hidden = !chips.length;
  renderFilterToggle();
}
function renderFilterToggle() {
  const compact = embedded && mobile, count = Object.values(selected).reduce((sum,values) => sum+values.length,0);
  $('#filterToggle').hidden = !compact;$('#filterToggle').setAttribute('aria-expanded',String(!compact || filtersExpanded));
  $('#filterGrid').hidden = compact && !filtersExpanded;$('#filterHelp').hidden = compact && !filtersExpanded;
  $('#filterToggleCount').textContent = count;$('#filterToggleCount').hidden = count === 0;
}
function filterOptions(input) {
  const panel = input.closest('.multi-filter'), value = input.value.trim().normalize('NFKC').toLowerCase();let count = 0;
  panel.querySelectorAll('.multi-option').forEach(option => {option.hidden = !`${option.textContent} ${option.querySelector('input').value}`.normalize('NFKC').toLowerCase().includes(value);if (!option.hidden) count++;});
  panel.querySelector('.multi-empty').hidden = count > 0;
}
function loadImage(image, url, stillRelevant = () => image.isConnected) {
  let attempts = 0;
  image.addEventListener('error',() => {
    if (attempts >= 2) {image.hidden = true;const parent = image.closest('.preview-image-wrap');if (parent) $('#previewError').hidden = false;else if (!image.parentElement.querySelector('.image-unavailable')) {const note = document.createElement('span');note.className = 'image-unavailable';note.textContent = t('图片暂时无法显示');image.parentElement.append(note);}return;}
    attempts += 1;setTimeout(() => {if (stillRelevant()) image.src = `${url}?retry=${attempts}`;},attempts*1000);
  });
  image.src = url;
}
function attachImages(parent) {parent.querySelectorAll('img[data-image-url]').forEach(image => {loadImage(image,image.dataset.imageUrl);image.removeAttribute('data-image-url');});}
function renderHero() {
  $('#showroomHero').hidden = embedded || collection !== 'catalog' || hasFilters() || page > 1 || loaded && !heroItems.length;
  $('#heroImages').innerHTML = heroItems.slice(0,3).map((item,index) => `<button type="button" class="showroom-object" data-hero="${index}" aria-label="${esc(t('查看{code}详情',{code:item.productCode || itemName(item)}))}"><img data-image-url="${esc(item.images[0].url)}" alt="${esc(itemName(item))}" loading="lazy"><span>${esc(item.productCode || item.capacity)}</span></button>`).join('');
  attachImages($('#heroImages'));
}
function paginationItems() {
  const visible = new Set([1,pages]);for (let n = Math.max(1,page-1);n <= Math.min(pages,page+1);n++) visible.add(n);
  if (page <= 3) for (let n = 1;n <= Math.min(5,pages);n++) visible.add(n);
  if (page >= pages-2) for (let n = Math.max(1,pages-4);n <= pages;n++) visible.add(n);
  const output = [];for (const n of [...visible].sort((a,b) => a-b)) {if (output.length && n-output.at(-1) > 1) output.push('…');output.push(n);}return output;
}
function renderGallery() {
  $('#gallery').innerHTML = items.map((item,index) => `<article class="gallery-card"><button type="button" class="photo-button" data-detail="${index}" aria-label="${esc(t('查看{code}详情',{code:item.productCode || itemName(item)}))}"><img data-image-url="${esc(item.images[0].url)}" alt="${esc(itemName(item))}" loading="lazy" decoding="async">${item.images.length > 1 ? `<span class="image-count">${esc(t('{count} 张图片',{count:item.images.length}))}</span>` : ''}</button><div class="card-body"><p class="record-code">${esc(item.productCode)}</p><button type="button" class="card-title" data-detail="${index}">${esc(itemName(item))}</button><div class="tags">${item.category ? `<span class="tag">${esc(t(item.category))}</span>` : ''}${item.materials.slice(0,2).map(value => `<span class="tag material">${esc(t(value))}</span>`).join('')}</div><p class="capacity">${esc(t('净含量：{capacity}',{capacity:item.capacity || '—'}))}</p></div><button type="button" class="card-foot" data-detail="${index}"><span>${esc(t('查看详情'))}</span><span aria-hidden="true">↗</span></button></article>`).join('');
  attachImages($('#gallery'));
  $('#empty').hidden = !loaded || items.length !== 0 || Boolean(noticeKey);
  $('#emptyTitle').textContent = t(hasFilters() ? '暂无匹配的包材' : collection === 'favourites' ? '暂无收藏' : collection === 'shortlist' ? '意向清单为空' : '更多包材，即将呈现');
  $('#emptyText').textContent = t(hasFilters() ? '试试调整搜索关键词或清除部分筛选条件。' : collection === 'favourites' ? '点击包材卡片上的收藏按钮，将喜欢的款式保留在本次浏览中。' : collection === 'shortlist' ? '将感兴趣的包材加入意向清单，即可一起咨询业务员。' : '欢迎稍后再来看看。');
  $('#emptyReset').hidden = !hasFilters();
  $('#pagination').hidden = pages <= 1 || !items.length;
  $('#pageStatus').textContent = `${page} / ${pages}`;$('#pageNumber').value = page;$('#pageNumber').max = pages;
  $('#pageButtons').innerHTML = paginationItems().map(number => number === '…' ? '<span class="page-gap" aria-hidden="true">…</span>' : `<button type="button" class="button ${number === page ? 'current' : ''}" data-page="${number}" aria-label="${esc(t('第 {number} 页',{number}))}" ${number === page ? 'aria-current="page"' : ''}>${number}</button>`).join('');
  $('#gallery').querySelectorAll('.gallery-card').forEach((card,index) => {const actions = document.createElement('div');actions.className = 'card-actions';actions.innerHTML = itemActions(items[index],String(index));card.append(actions);});
  renderHero();renderStatus();setBusy(busy);renderTools();
}
async function loadCatalog(target = page, scroll = false) {
  const sequence = ++requestSequence;controller?.abort();controller = new AbortController();retryPage = target;
  setBusy(true);showNotice();$('#retry').hidden = true;
  if (collection !== 'catalog') {renderLocalCollection(target);setBusy(false);if (scroll) scrollToFilters();return;}
  const params = new URLSearchParams({page:String(target),pageSize:String(pageSize)});
  if (query) params.set('q',query);
  for (const [key,values] of Object.entries(selected)) values.forEach(value => params.append(key,value));
  try {
    const data = await requestJSON(`/api/client/catalog?${params}`,{signal:controller.signal});
    if (sequence !== requestSequence) return;
    if (!Array.isArray(data.items) || !Number.isInteger(data.page) || data.page < 1 || !Number.isInteger(data.pages) || data.pages < 1 || !Number.isInteger(data.total) || data.total < 0) throw Error('Invalid catalogue');
    items = data.items.map(safeItem).filter(item => item.images.length);facets = safeFacets(data.facets);page = data.page;pages = data.pages;total = data.total;loaded = true;
    if (!hasFilters() && page === 1) heroItems = items.slice(0,3);
    renderSidebar();renderFilters();renderGallery();
    if (scroll) scrollToFilters();
  } catch (error) {
    if (sequence !== requestSequence || error.name === 'AbortError') return;
    if (error.status === 401) {navigateToLogin();return;}
    items = [];total = 0;showNotice('暂时无法加载包材，请检查网络后重试。');renderGallery();$('#retry').hidden = false;
  } finally {if (sequence === requestSequence) setBusy(false);}
}
function factHTML(labelText, value) {return `<div><dt>${esc(t(labelText))}</dt><dd>${esc(value || '—')}</dd></div>`;}
function renderDetails(changeImage = false) {
  if (!previewItem) return;
  $('#detailCode').textContent = previewItem.productCode;$('#detailTitle').textContent = itemName(previewItem);
  $('#detailTags').innerHTML = previewItem.materials.map(value => `<span class="tag material">${esc(t(value))}</span>`).join('');
  $('#detailFacts').innerHTML = [factHTML('包材类型',t(previewItem.category)),factHTML('瓶型',t(previewItem.bottleType)),factHTML('净含量',previewItem.capacity),factHTML('材质',joined(previewItem.materials)),factHTML('用途',joined(previewItem.uses)),factHTML('使用部位',previewItem.sections.map(value => label('section',value)).join(getLanguage() === 'en' ? ', ' : '、'))].join('');
  $('#specifications').hidden = !previewItem.specifications.length;
  $('#detailSpecifications').innerHTML = previewItem.specifications.map(spec => factHTML(spec.label,spec.value)).join('');
  $('#imageStatus').textContent = `${previewIndex+1} / ${previewItem.images.length}`;
  $('#imagePrevious').disabled = previewIndex === 0;$('#imageNext').disabled = previewIndex === previewItem.images.length-1;
  $('.preview-controls').hidden = previewItem.images.length <= 1;
  $('#imageThumbnails').hidden = previewItem.images.length <= 1;
  $('#imageThumbnails').innerHTML = previewItem.images.map((image,index) => `<button type="button" data-image-index="${index}" aria-current="${index === previewIndex}" aria-label="${esc(t('第 {number} 张图片',{number:index+1}))}"><img src="${esc(image.url)}" loading="lazy" alt=""></button>`).join('');
  if (changeImage) {
    const old = $('#previewImage'), image = old.cloneNode();image.removeAttribute('src');image.hidden = false;old.replaceWith(image);$('#previewError').hidden = true;
    loadImage(image,previewItem.images[previewIndex].url,() => previewItem && $('#previewImage') === image && image.isConnected);
  }
  $('#previewImage').alt = `${itemName(previewItem)} · ${t('第 {number} 张图片',{number:previewIndex+1})}`;
  $('#detailActions').innerHTML = itemActions(previewItem,'preview');
}
function openPreview(item, source) {if (!item) return;previewItem = item;previewIndex = 0;previousFocus = source;renderDetails(true);$('#preview').showModal();}
function moveImage(delta) {if (!previewItem) return;previewIndex = Math.max(0,Math.min(previewItem.images.length-1,previewIndex+delta));renderDetails(true);}
function updateSidebar() {
  document.body.classList.toggle('menu-open',mobile && sidebarOpen);document.body.classList.toggle('sidebar-collapsed',!mobile && !sidebarOpen);
  $('#sidebarBackdrop').hidden = !mobile || !sidebarOpen;$('#menuButton').setAttribute('aria-expanded',String(sidebarOpen));
  const text = t(sidebarOpen ? '收起侧栏' : '展开侧栏');$('#menuLabel').textContent = text;$('#menuButton').setAttribute('aria-label',text);
  document.body.style.overflow = mobile && sidebarOpen ? 'hidden' : '';
}
function closeMobileSidebar() {if (mobile) {sidebarOpen = false;updateSidebar();}}
function applyFilters() {query = $('#query').value.trim();renderSidebar();renderFilters();closeMobileSidebar();loadCatalog(1);}
function toggleFacet(key, value) {selected[key] = selected[key].includes(value) ? selected[key].filter(item => item !== value) : [...selected[key],value];applyFilters();}
function reset() {for (const key of Object.keys(selected)) selected[key] = [];query = '';$('#query').value = '';applyFilters();}
$('#searchForm').addEventListener('submit',event => {event.preventDefault();applyFilters();});
$('#reset').addEventListener('click',reset);$('#emptyReset').addEventListener('click',reset);$('#allCatalog').addEventListener('click',() => {collection = 'catalog';cancelImageSearch();reset();});
$('#browse').addEventListener('click',() => {$('#filters').scrollIntoView({behavior:matchMedia('(prefers-reduced-motion: reduce)').matches ? 'auto' : 'smooth',block:'start'});$('#query').focus({preventScroll:true});});
document.addEventListener('change',event => {const key = event.target.dataset.filter;if (facetConfig[key]) {const value = event.target.value;toggleFacet(key,value);const input = [...document.querySelectorAll('[data-filter]')].find(input => input.dataset.filter === key && input.value === value);input?.focus({preventScroll:true});}});
document.addEventListener('input',event => {if (event.target.matches('.multi-option-search')) filterOptions(event.target);});
document.addEventListener('click',event => {
  const button = event.target.closest('button');
  if (button?.dataset.itemAction) toggleItemAction(button.dataset.itemAction,button.dataset.itemIndex === 'preview' ? previewItem : items[Number(button.dataset.itemIndex)]);
  else if (button?.dataset.detail !== undefined) openPreview(items[Number(button.dataset.detail)],button);
  else if (button?.dataset.hero !== undefined) openPreview(heroItems[Number(button.dataset.hero)],button);
  else if (button?.dataset.section) toggleFacet('section',button.dataset.section);
  else if (button?.dataset.category) toggleFacet('category',button.dataset.category);
  else if (button?.hasAttribute('data-all-categories')) {selected.category = [];applyFilters();}
  else if (button?.dataset.clearFilter) toggleFacet(button.dataset.clearFilter,button.dataset.filterValue);
  else if (button?.dataset.clearFacet) {selected[button.dataset.clearFacet] = [];applyFilters();}
  else if (button?.dataset.page && !busy) loadCatalog(Number(button.dataset.page),true);
  else if (button?.dataset.imageIndex !== undefined && previewItem) {previewIndex = Number(button.dataset.imageIndex);renderDetails(true);}
  const summary = event.target.closest('.multi-filter summary');
  for (const panel of document.querySelectorAll('.multi-filter[open]')) if (summary && panel !== summary.parentElement || !event.target.closest('.multi-filter')) panel.open = false;
});
document.addEventListener('keydown',event => {if (event.key !== 'Escape') return;const panel = event.target.closest('.multi-filter[open]');if (panel) {panel.open = false;panel.querySelector('summary').focus();}else if (mobile && sidebarOpen) {closeMobileSidebar();$('#menuButton').focus();}});
$('#menuButton').addEventListener('click',() => {sidebarOpen = !sidebarOpen;updateSidebar();});
$('#sidebarClose').addEventListener('click',() => {sidebarOpen = false;updateSidebar();$('#menuButton').focus();});$('#sidebarBackdrop').addEventListener('click',closeMobileSidebar);
matchMedia('(max-width: 760px)').addEventListener?.('change',event => {mobile = event.matches;sidebarOpen = !mobile;updateSidebar();renderFilterToggle();});
$('#closePreview').addEventListener('click',() => $('#preview').close());
$('#preview').addEventListener('close',() => {const code = previewItem?.productCode;$('#previewImage').removeAttribute('src');previewItem = null;if (previousFocus?.isConnected) previousFocus.focus();else {[...document.querySelectorAll('.photo-button')].find(button => items[Number(button.dataset.detail)]?.productCode === code)?.focus();}});
$('#preview').addEventListener('click',event => {if (event.target === $('#preview')) $('#preview').close();});
$('#preview').addEventListener('keydown',event => {if (event.key === 'ArrowLeft' || event.key === 'ArrowRight') {event.preventDefault();moveImage(event.key === 'ArrowLeft' ? -1 : 1);}});
$('#imagePrevious').addEventListener('click',() => moveImage(-1));$('#imageNext').addEventListener('click',() => moveImage(1));
$('#previous').addEventListener('click',() => {if (!busy && page > 1) loadCatalog(page-1,true);});$('#next').addEventListener('click',() => {if (!busy && page < pages) loadCatalog(page+1,true);});
$('#jumpForm').addEventListener('submit',event => {event.preventDefault();const target = Number($('#pageNumber').value);if (!busy && Number.isInteger(target) && target >= 1 && target <= pages && target !== page) loadCatalog(target,true);});
$('#retry').addEventListener('click',() => session ? loadCatalog(retryPage) : init());
$('#logout').addEventListener('click',async () => {
  $('#logout').disabled = true;showNotice();
  try {if (!session) session = await requestJSON('/api/session');await requestJSON('/api/logout',{method:'POST',headers:{'Content-Type':'application/json','X-CSRF-Token':session.csrf || ''},body:'{}'});navigateToLogin();}
  catch (error) {if (error.status === 401) navigateToLogin();else showNotice('暂时无法退出，请检查网络后重试。');}
  finally {$('#logout').disabled = false;}
});

function scrollToFilters() {$('#filters').scrollIntoView({behavior:matchMedia('(prefers-reduced-motion: reduce)').matches ? 'auto' : 'smooth',block:'start'});}
function itemKey(item) {return item.productCode || item.id || item.images[0]?.url;}
function notifyParent(message) {if (embedded && window.parent !== window) window.parent.postMessage(message,location.origin);}
function navigateToLogin() {
  // Login and the showroom shell intentionally deny framing. The shell must
  // navigate its own top-level page when this embedded catalogue loses auth.
  if (embedded && window.parent !== window) notifyParent({type:'yuanze-auth-required'});
  else location.replace('/login');
}
function notifyShortlist() {notifyParent({type:'yuanze-shortlist',items:[...shortlist.values()].map(item => ({productCode:item.productCode,capacity:item.capacity}))});}
function itemActions(item, index) {
  const key = itemKey(item);
  return [['favourite',favourites,'收藏','已收藏'],['shortlist',shortlist,'加入意向','已加入意向'],['compare',comparison,'加入对比','已加入对比']].map(([action,store,off,on]) => `<button type="button" class="item-action ${store.has(key) ? 'selected' : ''}" data-item-action="${action}" data-item-index="${index}" aria-pressed="${store.has(key)}">${esc(t(store.has(key) ? on : off))}</button>`).join('');
}
function renderTools() {
  $('#favoriteCount').textContent = favourites.size;$('#shortlistCount').textContent = shortlist.size;$('#compareCount').textContent = `${comparison.size} / 4`;
  $('#compareOpen').disabled = comparison.size === 0;$('#exportList').disabled = !items.length;
  $('#exportShortlist').disabled = !shortlist.size;$('#consultShortlist').disabled = !shortlist.size;
  $('#collectionBar').hidden = collection === 'catalog';$('#shortlistTools').hidden = !['favourites','shortlist'].includes(collection);
  $('#collectionLabel').textContent = t({catalog:'包材选型库',favourites:'我的收藏',shortlist:'意向清单',image:'图片相似结果'}[collection]);
  $('#galleryTitle').textContent = $('#collectionLabel').textContent;
  $('#imageSearchSubmit').disabled = Boolean(imageController);
  $('#imageSearchSubmit').textContent = t(imageController ? '正在加载…' : '查找相似包材');
}
function publicFacetValues(item) {return {category:[item.category],section:item.sections,material:item.materials,capacity:[item.capacity],bottle:[item.bottleType],use:item.uses};}
function matchesLocal(item) {
  const values = publicFacetValues(item);
  if (Object.entries(selected).some(([key,choices]) => choices.length && !choices.some(value => values[key].includes(value)))) return false;
  // Keep term boundaries and both languages, regardless of the display language.
  // Joining an entire query ("100ml PET") would wrongly require adjacent fields.
  const normalize = value => String(value).normalize('NFKC').toLowerCase().replace(/(\d+(?:\.\d+)?)\s*(?:毫升|ml)/g,'$1ml');
  const publicWords = Object.entries(values).flatMap(([key,entries]) => entries.flatMap(value => [value,facetConfig[key].values?.[value] || '']));
  const sectionNames = item.sections.map(value => value === 'face' ? '面部' : '身体／头部');
  const search = normalize([item.productCode,...publicWords,...sectionNames,...item.specifications.flatMap(spec => [spec.label,specs[spec.label],spec.value])].join(' '));
  const terms = normalize(query).match(/[\p{L}\p{N}_]+(?:[.-][\p{L}\p{N}_]+)*/gu) || [];
  return terms.every(term => /^[a-z0-9_.-]+$/.test(term)
    ? new RegExp(`(^|[^a-z0-9])${term.replace(/[.*+?^${}()|[\]\\]/g,'\\$&')}(?![a-z0-9])`).test(search)
    : search.includes(term));
}
function renderLocalCollection(target = 1) {
  const source = collection === 'favourites' ? [...favourites.values()] : collection === 'shortlist' ? [...shortlist.values()] : imageResults;
  // Derive options before applying filters, from this collection's safe items.
  // A previous image search may have entirely different material/category facets.
  facets = Object.fromEntries(Object.keys(facetConfig).map(key => [key,[...new Set(source.flatMap(item => publicFacetValues(item)[key]).filter(Boolean))]]));
  const filtered = source.filter(matchesLocal);total = filtered.length;pages = Math.max(1,Math.ceil(total/pageSize));page = Math.max(1,Math.min(target,pages));
  items = filtered.slice((page-1)*pageSize,page*pageSize);loaded = true;renderSidebar();renderFilters();renderGallery();
}
function changeCollection(next) {
  collection = next;cancelImageSearch();closeMobileSidebar();loadCatalog(1);renderSidebar();
}
function toggleItemAction(action,item) {
  if (!item) return;
  const store = {favourite:favourites,shortlist,compare:comparison}[action];if (!store) return;
  const key = itemKey(item);
  if (store.has(key)) store.delete(key);
  else {if (action === 'compare' && store.size >= 4) {showNotice('最多可同时对比四款包材。');return;}store.set(key,item);}
  showNotice();
  if (collection === 'favourites' && action === 'favourite' || collection === 'shortlist' && action === 'shortlist') renderLocalCollection(page);
  else renderGallery();
  renderDetails();renderSidebar();renderComparison();renderConsultation();
  if (action === 'shortlist') notifyShortlist();
}
function renderComparison() {
  const products = [...comparison.values()];
  const rows = [['产品编号',item => item.productCode],['包材类型',item => t(item.category)],['瓶型',item => t(item.bottleType)],['净含量',item => item.capacity],['材质',item => joined(item.materials)],['用途',item => joined(item.uses)],['使用部位',item => item.sections.map(value => label('section',value)).join(' / ')],...Object.keys(specs).filter(name => products.some(item => item.specifications.some(spec => spec.label === name))).map(name => [name,item => item.specifications.find(spec => spec.label === name)?.value])];
  $('#compareTable').innerHTML = `<thead><tr><th scope="col">${esc(t('包材图片'))}</th>${products.map(item => `<th scope="col"><img src="${esc(item.images[0].url)}" alt="${esc(itemName(item))}"><span>${esc(itemName(item))}</span></th>`).join('')}</tr></thead><tbody>${rows.map(([name,value]) => `<tr><th scope="row">${esc(t(name))}</th>${products.map(item => `<td>${esc(value(item) || '—')}</td>`).join('')}</tr>`).join('')}</tbody>`;
}
function csvText(products) {
  const headings = ['产品编号','包材类型','瓶型','净含量','材质','用途','使用部位',...Object.keys(specs)];
  const cell = value => `"${String(value ?? '').replace(/"/g,'""')}"`;
  return '\uFEFF' + [headings.map(value => t(value)),...products.map(item => [item.productCode,t(item.category),t(item.bottleType),item.capacity,joined(item.materials),joined(item.uses),item.sections.map(value => label('section',value)).join(' / '),...Object.keys(specs).map(name => item.specifications.find(spec => spec.label === name)?.value || '')])].map(row => row.map(cell).join(',')).join('\r\n');
}
function exportProducts(products,name) {
  if (!products.length) return;
  const url = URL.createObjectURL(new Blob([csvText(products)],{type:'text/csv;charset=utf-8'})), link = document.createElement('a');
  link.href = url;link.download = name;document.body.append(link);link.click();link.remove();setTimeout(() => URL.revokeObjectURL(url),1000);
}
function renderConsultation() {
  $('#consultText').value = [...shortlist.values()].map(item => [item.productCode,itemName(item)].filter(Boolean).join(' · ')).join('\n');
  $('#copyStatus').textContent = '';
}
function cancelImageSearch() {imageRequest++;imageController?.abort();imageController = null;renderTools();}
function readImage(file) {
  return new Promise((resolve,reject) => {const reader = new FileReader();reader.onload = () => resolve(reader.result);reader.onerror = () => reject(Error('Unable to read image'));reader.readAsDataURL(file);});
}
async function searchImage(event) {
  event.preventDefault();if (imageController) return;
  const file = $('#imageSearchFile').files?.[0];$('#imageSearchError').hidden = true;
  if (!file || !['image/jpeg','image/png','image/webp'].includes(file.type) || !file.size || file.size > 6*1024*1024) {$('#imageSearchError').textContent = t('请选择 JPG、PNG 或 WebP 图片，文件不超过 6 MB。');$('#imageSearchError').hidden = false;return;}
  const request = ++imageRequest;imageController = new AbortController();const signal = imageController.signal;renderTools();
  try {
    const image = await readImage(file);if (request !== imageRequest) return;
    const response = await requestJSON('/api/client/image-search',{method:'POST',headers:{'Content-Type':'application/json','X-CSRF-Token':session?.csrf || ''},body:JSON.stringify({image}),signal,timeoutMs:60000});
    if (request !== imageRequest) return;
    if (!Array.isArray(response.items)) throw Error('Invalid image search results');
    imageResults = response.items.map(safeItem).filter(item => item.images.length);collection = 'image';
    requestSequence++;controller?.abort();showNotice();$('#retry').hidden = true;setBusy(false);renderLocalCollection(1);$('#imageSearchDialog').close();scrollToFilters();
  } catch (error) {
    if (request !== imageRequest || error.name === 'AbortError') return;
    if (error.status === 401) {navigateToLogin();return;}
    $('#imageSearchError').textContent = t('暂时无法搜图，请稍后重试。');$('#imageSearchError').hidden = false;
  } finally {if (request === imageRequest) {imageController = null;renderTools();}}
}
$('#favoritesView').addEventListener('click',() => changeCollection('favourites'));
$('#filterToggle').addEventListener('click',() => {filtersExpanded = !filtersExpanded;renderFilterToggle();});
if (embedded) $('.brand').addEventListener('click',event => {if (window.parent === window) return;event.preventDefault();closeMobileSidebar();notifyParent({type:'yuanze-home'});});
$('#shortlistView').addEventListener('click',() => changeCollection('shortlist'));
$('#catalogReturn').addEventListener('click',() => changeCollection('catalog'));
$('#pageSize').addEventListener('change',() => {const value = Number($('#pageSize').value);if ([12,24,48].includes(value)) {pageSize = value;loadCatalog(1);}});
for (const [id,isList] of [['gridView',false],['listView',true]]) $('#'+id).addEventListener('click',() => {
  $('#gallery').classList.toggle('list-mode',isList);
  for (const [button,active] of [['gridView',!isList],['listView',isList]]) {$('#'+button).setAttribute('aria-pressed',String(active));$('#'+button).classList.toggle('active',active);}
});
$('#exportList').addEventListener('click',() => exportProducts(items,'yuanze-packaging-page.csv'));
$('#exportShortlist').addEventListener('click',() => exportProducts([...shortlist.values()],'yuanze-packaging-shortlist.csv'));
$('#compareOpen').addEventListener('click',() => {if (!comparison.size) return;renderComparison();$('#compareDialog').showModal();});
$('#compareClose').addEventListener('click',() => $('#compareDialog').close());
$('#imageSearchOpen').addEventListener('click',() => {$('#imageSearchError').hidden = true;$('#imageSearchDialog').showModal();});
$('#imageSearchClose').addEventListener('click',() => $('#imageSearchDialog').close());
$('#imageSearchDialog').addEventListener('close',cancelImageSearch);
$('#imageSearchForm').addEventListener('submit',searchImage);
$('#consultShortlist').addEventListener('click',() => {if (!shortlist.size) return;notifyShortlist();if (embedded && window.parent !== window) notifyParent({type:'yuanze-contact'});else {renderConsultation();$('#consultDialog').showModal();}});
$('#consultClose').addEventListener('click',() => $('#consultDialog').close());
$('#copyConsult').addEventListener('click',async () => {try {await navigator.clipboard.writeText($('#consultText').value);$('#copyStatus').textContent = t('已复制，可发送给业务员。');}catch {$('#consultText').select();$('#copyStatus').textContent = t('请手动选中并复制咨询内容。');}});
for (const [id,trigger] of [['compareDialog','compareOpen'],['imageSearchDialog','imageSearchOpen'],['consultDialog','consultShortlist']]) {
  $('#'+id).addEventListener('click',event => {if (event.target === $('#'+id)) $('#'+id).close();});
  $('#'+id).addEventListener('close',() => $('#'+trigger).focus({preventScroll:true}));
}
window.addEventListener('message',event => {
  if (!embedded || event.origin !== location.origin || event.source !== window.parent) return;
  if (event.data?.type === 'yuanze-language' && ['zh','en'].includes(event.data.language) && event.data.language !== getLanguage()) setLanguage(event.data.language);
});
onLanguageChange(() => {renderText();renderSidebar();renderFilters();renderGallery();renderDetails();renderComparison();renderConsultation();notifyParent({type:'yuanze-language',language:getLanguage()});});
installLanguageSwitch($('#languageSwitch'));
renderText();renderSidebar();renderFilters();renderStatus();
async function init() {
  $('#retry').hidden = true;showNotice();
  try {session = await requestJSON('/api/session');if (!['client','admin'].includes(session.role)) {if (embedded && window.parent !== window) navigateToLogin();else location.replace('/');return;}await loadCatalog();}
  catch (error) {if (error.status === 401) {navigateToLogin();return;}session = null;$('#catalogStatus').textContent = '';showNotice('暂时无法打开页面，请检查网络后重试。');$('#retry').hidden = false;}
}
init();
