// Show documented prices and their conditions; never derive totals or tax prices.
const esc = value => String(value ?? '').replace(/[&<>"']/g, character => ({
  '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;',
}[character]));
const text = value => typeof value === 'string' ? value.trim() : typeof value === 'number' && Number.isFinite(value) ? String(value) : '';
const clean = value => {
  const result = text(value);
  return /^(?:[/／—–\-]+|暂无|无|待补(?:充)?|待确认|待核对|待询价|报价待补|未填写|未注明|未提供|N\/?A|null)$/i.test(result) ? '' : result;
};
const key = value => text(value).replace(/[\s：:／/（）()·]/g, '');
const unique = values => [...new Set(values.map(clean).filter(Boolean))];
const lines = value => unique(clean(value).split(/\r?\n/));
const priceSignal = value => /(?:[¥￥$]\s*\d|\d(?:[.,]\d+)?\s*(?:元|人民币|RMB|CNY|USD|美元)|(?:单价|报价|价格)\s*[：:=为]?\s*\d)/i.test(value);
const component = /裸瓶|瓶身|瓶体|内塞|垫片|旋盖|盖子|瓶盖|外盖|泵头|喷头|滴管/;
const process = /丝印|印刷|烫金|烫银|喷涂|喷砂|电镀|磨砂|蒙砂|工艺/;
const fee = /打样|样品费|模具|开模|运费|税点/;
const negativeTax = value => /不含税|未含税|未税|税前|另加税|税另计/.test(value);
const positiveTax = value => !negativeTax(value) && !/待确认|待核对|未确认|待询|是否|不确定|未知|需确认/.test(value) && /含税|税后/.test(value);

function detailRows(record) {
  return (Array.isArray(record.productDetails) ? record.productDetails : [])
    .filter(row => row && typeof row.label === 'string')
    .map(row => ({label: clean(row.label), value: clean(row.value), evidence: clean(row.evidence)}));
}

// A recognized administrator field, even when deliberately cleared, takes
// precedence over old quotation text. Duplicate labels preserve tiered prices.
function preferred(details, matcher, fallback = []) {
  const selected = details.filter(row => matcher(key(row.label)));
  return selected.length ? selected.filter(row => row.value) : unique(fallback).map(value => ({value}));
}

function entriesMarkup(entries, {labels = false} = {}) {
  const seen = new Set();
  return entries.filter(entry => entry.value).map(entry => {
    const id = (labels ? entry.label || '' : '') + '\n' + entry.value;
    if (seen.has(id)) return '';
    seen.add(id);
    return `<div class="price-entry">${labels && entry.label ? `<span class="price-source">${esc(entry.label)}</span>` : ''}<span>${esc(entry.value)}</span></div>`;
  }).join('');
}

function cell(label, entries, options) {
  return `<div class="price-cell"><dt>${esc(label)}</dt><dd class="price-value">${entriesMarkup(entries, options)}</dd></div>`;
}

function conditionalRaw(ordinary, custom) {
  const regular = unique(ordinary), tailored = unique(custom);
  return [...regular.map(value => ({value: tailored.length ? '普通：' + value : value})),
    ...tailored.map(value => ({value: '定制：' + value}))];
}

function conditions(details, header) {
  const explicit = details.filter(row => /^(?:报价口径|报价条件|价格口径)$/.test(key(row.label)));
  const taxRows = details.filter(row => /税运|税费|运输条件|税务条件/.test(key(row.label)));
  const values = unique([...explicit.map(row => row.value), ...taxRows.map(row => row.value),
    ...(explicit.length ? [] : [header])]);
  const canonical = value => value.replace(/[\s，,；;。]/g, '').replace(/(?:价格|报价)$/, '');
  // “含运” and “含运不含税价格” are not two different terms. Keep the
  // more complete documented condition, including any original tax rate.
  return values.filter((value, index) => !values.some((other, otherIndex) => {
    const a = canonical(value), b = canonical(other);
    return index !== otherIndex && b.includes(a) && (b.length > a.length || otherIndex < index);
  })).map(value => ({value}));
}

function isBareBottlePrice(value) {
  if (!/裸瓶|瓶身|瓶体/.test(value)) return false;
  if (priceSignal(value)) return true;
  // A decimal immediately following a component name in a quotation is kept
  // verbatim, including all siblings and quantity/color conditions on that line.
  return /(?:裸瓶|瓶身|瓶体)[：:\s]*\d+\.\d+(?!\d|\s*(?:m[lm]|毫升|克|g\b))/i.test(value);
}

function ordinaryPriceLine(value) {
  return !component.test(value) && !process.test(value) && !fee.test(value)
    && (priceSignal(value) || /^\d+(?:\.\d+)?(?:\s*(?:元|RMB|CNY|USD))?$/i.test(value));
}

function pricingNotes(details) {
  return details.filter(row => /(?:打样|样品|开模|模具|配件|泵头|喷头|内塞|旋盖|盖子|瓶盖|外盖|垫片|滴管)/.test(row.label)
    && /(?:价|费|款项|条件)/.test(row.label) && row.value);
}

/** Return escaped, dependency-free HTML for the first section of a product. */
export function pricingData(record = {}) {
  const details = detailRows(record), raw = lines(record.quoteRaw), custom = lines(record.customQuoteRaw);
  const confirmed = record.unitPrice !== null && record.unitPrice !== undefined && clean(record.unitPrice) !== ''
    ? clean(record.unitPrice) + (clean(record.currency) ? ' ' + clean(record.currency) : '') : '';
  const ordinaryLabel = label => /^(?:确认单价|普通单价|普通报价|单价|采购单价|单价普通报价|普通确认单价)$/.test(label);
  const ordinaryExplicit = details.some(row => ordinaryLabel(key(row.label)));
  const ordinary = preferred(details, ordinaryLabel,
    confirmed ? [confirmed] : raw.filter(ordinaryPriceLine));

  const explicitTax = details.filter(row => /^(?:含税(?:价格|单价|报价)|税后(?:价格|单价|报价))$/.test(key(row.label)));
  const taxCandidates = ordinaryExplicit ? ordinary.map(row => row.value) : raw;
  const taxFallback = taxCandidates.filter(value => positiveTax(value) && priceSignal(value) && !component.test(value) && !process.test(value));
  if (!taxFallback.length && positiveTax(clean(record.quoteHeader))) {
    taxFallback.push(...ordinary.map(row => row.value).filter(value => !negativeTax(value) && !component.test(value) && !process.test(value)));
  }
  const tax = explicitTax.length ? explicitTax.filter(row => row.value && !negativeTax(row.value))
    : unique(taxFallback).map(value => ({value}));
  const bare = Object.hasOwn(record,'bareBottlePrice') ? (clean(record.bareBottlePrice)?[{value:clean(record.bareBottlePrice)}]:[]) : preferred(details, label => /^(?:裸瓶|瓶身|瓶体)(?:价格|单价|报价|价)$/.test(label), raw.filter(isBareBottlePrice));
  const craftsmanship = preferred(details, label => /^(?:工艺|工艺说明|工艺价格|工艺费用|印刷工艺|印刷费用|历史工艺费用及条件)$/.test(label),
    clean(record.processRaw) ? [record.processRaw] : raw.filter(value => process.test(value) && !component.test(value)));

  const moqDetails = details.filter(row => /(?:MOQ|起订|最小订购)/i.test(key(row.label)));
  const moq = moqDetails.length ? moqDetails.filter(row => row.value)
    : conditionalRaw([record.moqRaw], [record.customMoqRaw]);
  const leadDetails = details.filter(row => /^(?:普通|定制)?(?:货期|交期|交货期|生产周期|交货周期)$/.test(key(row.label)));
  const lead = leadDetails.length ? leadDetails.filter(row => row.value)
    : conditionalRaw([record.leadTimeRaw], [record.customLeadTimeRaw]);
  const terms = conditions(details, record.quoteHeader);
  const components = pricingNotes(details);
  const customPrice = preferred(details, label => /^(?:定制价格|定制报价|定制单价)$/.test(label), custom);

  // Keep every complete source quote visible, including configurations that
  // cannot safely be classified as one price. It is never an inferred total.
  const quoteOriginal = [
    ['规格原文', clean(record.specificationRaw)], ['原始报价（含配置与分项）', clean(record.quoteRaw)],
    ['定制报价原文', clean(record.customQuoteRaw)],
  ].filter(([, value]) => value);
  return {ordinary,tax,bare,craftsmanship,moq,lead,terms,components,customPrice,quoteOriginal,moqDetails,leadDetails};
}

export function renderPricing(record = {}) {
  const {ordinary,tax,bare,craftsmanship,moq,lead,terms,components,customPrice,quoteOriginal,moqDetails,leadDetails}=pricingData(record);
  return `<section class="pricing-section" aria-label="价格与报价"><h3>价格与报价</h3><dl class="pricing-grid">${
    cell('普通／确认单价', ordinary)
  }${cell('含税价格', tax)}${cell('裸瓶价格', bare)}${cell('工艺', craftsmanship)}${
    cell('起订量／MOQ', moq, {labels: moqDetails.length > 0})
  }${cell('货期', lead, {labels: leadDetails.length > 0})}${cell('报价口径', terms)}</dl>${
    components.length ? `<div class="pricing-quote"><h4>配件、打样与其他费用</h4><div class="price-value">${entriesMarkup(components, {labels: true})}</div></div>` : ''
  }${customPrice.length ? `<div class="pricing-quote"><h4>定制报价</h4><div class="price-value">${entriesMarkup(customPrice)}</div></div>` : ''}${
    quoteOriginal.length ? `<div class="pricing-quote pricing-original"><h4>规格与完整报价原文</h4>${quoteOriginal.map(([label, value]) => `<div class="price-source">${esc(label)}</div><div class="price-value">${esc(value)}</div>`).join('')}</div>` : ''
  }<p class="price-source">按原文保留适用规格、数量和条件；分项价格不代表整套合计，使用前请复核报价有效性。</p></section>`;
}
