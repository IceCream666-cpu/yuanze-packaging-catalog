// Product-scoped taxonomy only. Shared catalogue OCR, source filenames, supplier
// prose and source-page image captions deliberately never contribute evidence.
const RULES = [
  ['洁面', /洁面|洗面奶|洗颜|洗脸|\b(?:facial|face)\s+(?:cleanser|wash|cleansing)\b/giu, 'face'],
  ['卸妆', /卸妆|\bmake[ -]?up\s+remov(?:er|al)\b|\bcleansing\s+(?:oil|balm)\b/giu, 'face'],
  ['精华液', /精华(?:液|露|素)?|\bserum\b/giu, ''],
  ['爽肤水', /爽肤水|\b(?:facial\s+|skin\s+)?toner\b/giu, 'face'],
  ['化妆水', /化妆水/gu, 'face'],
  ['面霜', /面霜|\b(?:face|facial)\s+cream\b/giu, 'face'],
  ['眼霜', /眼霜|\beye\s+cream\b/giu, 'face'],
  ['眼部精华', /眼(?:部)?精华|\beye\s+serum\b/giu, 'face'],
  ['面膜', /面膜|眼膜|\b(?:face|facial|eye|sheet)\s+mask\b/giu, 'face'],
  ['唇部护理', /唇部护理|润唇|唇膏|唇油|\blip\s+(?:care|balm|oil|mask)\b/giu, 'face'],
  ['防晒', /防晒|\bsun\s*(?:screen|block|care)\b/giu, ''],
  ['粉底液', /粉底液|\bliquid\s+foundation\b/giu, 'face'],
  ['底妆', /粉底(?!液)|隔离(?:霜|乳|管|瓶)?|妆前|遮瑕|气垫|\b(?:foundation|concealer|make[ -]?up\s+primer)\b/giu, 'face'],
  ['唇彩', /口红|唇釉|唇泥|唇彩|\blip(?:stick|\s+gloss|\s+tint)\b/giu, 'face'],
  ['眉妆', /眉粉|眉笔|染眉|眉胶|\b(?:eyebrow|brow)\s+(?:powder|pencil|gel)\b/giu, 'face'],
  ['睫毛产品', /睫毛|\b(?:mascara|eyelash)\b/giu, 'face'],
  ['洗手液', /洗手(?:液|慕斯|泡沫|露)|\bhand\s*(?:wash|soap)\b/giu, 'body-head'],
  ['洗发水', /洗发(?:水|露|液|乳)|洗头(?:水|液)|\bshampoo\b/giu, 'body-head'],
  ['护发素', /护发素|\bhair\s+conditioner\b/giu, 'body-head'],
  ['发膜', /发膜|\bhair\s+mask\b/giu, 'body-head'],
  ['头皮护理', /头皮|\bscalp\b/giu, 'body-head'],
  ['头发造型', /发胶|发蜡|发泥|定型(?:喷雾|水|胶)|啫喱水|\bhair\s*(?:spray|gel|wax|styling)\b/giu, 'body-head'],
  ['染发', /染发|\bhair\s+(?:dye|color|colour)\b/giu, 'body-head'],
  ['沐浴露', /沐浴(?:露|乳|液|油|泡沫)|\bbody\s+wash\b|\bshower\s+(?:gel|cream|oil)\b/giu, 'body-head'],
  ['身体乳', /身体乳|\bbody\s+lotion\b/giu, 'body-head'],
  ['身体霜', /身体霜|身体润肤霜|\bbody\s+(?:cream|butter)\b/giu, 'body-head'],
  ['身体油', /身体油|\bbody\s+oil\b/giu, 'body-head'],
  ['身体磨砂', /身体磨砂|磨砂沐浴|\bbody\s+scrub\b/giu, 'body-head'],
  ['护手霜', /护手霜|手霜|\bhand\s+cream\b/giu, 'body-head'],
  ['手足护理', /手足|手部护理|足部护理|脚部护理|手膜|足膜|脚膜/gu, 'body-head'],
  ['护足霜', /护足霜|脚霜|\bfoot\s+cream\b/giu, 'body-head'],
  ['脱毛', /脱毛|\bdepilatory\b|\bhair\s+removal\b/giu, 'body-head'],
  ['止汗除臭', /止汗|体香剂|除体味|腋下|\b(?:deodorant|antiperspirant)\b/giu, 'body-head'],
  ['香水', /香水|\b(?:perfume|eau\s+de\s+(?:parfum|toilette))\b/giu, 'body-head'],
  ['身体香氛', /身体香氛|身体喷雾|\bbody\s+(?:mist|fragrance)\b/giu, 'body-head'],
  ['香氛', /香氛|\bfragrance\b/giu, ''],
  ['美甲', /指甲油|美甲|甲油胶|\bnail\s+(?:polish|gel|care)\b/giu, 'body-head'],
  ['口腔护理', /漱口水|牙膏|口腔护理|\b(?:mouthwash|toothpaste|oral\s+care)\b/giu, ''],
  ['精油', /精油|\bessential\s+oil\b/giu, ''],
  ['乳液', /乳液(?!泵|头)|\blotion\b/giu, ''],
  ['膏霜', /膏霜/gu, ''],
  ['凝胶', /凝胶/gu, ''],
  ['洗护', /洗护/gu, ''],
  ['洗衣液', /洗衣液|\blaundry\s+detergent\b/giu, ''],
  ['家居清洁', /洗洁精|家居清洁|厨房清洁|\b(?:dishwashing\s+liquid|household\s+cleaner)\b/giu, ''],
];
const USAGE_COLUMN = /^(?:用途|产品用途|适用用途|适用产品|应用产品|usage|purpose|application|uses)$/iu;
const AREA_COLUMN = /^(?:使用部位|适用部位|应用部位|bodyarea|applicationarea)$/iu;
const SECTION_RULES = [
  ['face', /面部|脸部|眼部|唇部|\b(?:face|facial)\b/giu],
  ['body-head', /身体|全身|躯干|手部|手足|足部|脚部|头部|头皮|头发|\b(?:body|scalp|hair|hands?|foot|feet)\b/giu],
];
const BODY_SECTIONS = ['face', 'body', 'head'];
const HEAD_USES = new Set(['洗发水', '护发素', '发膜', '头皮护理', '头发造型', '染发']);
const BODY_SECTION_RULES = [
  SECTION_RULES[0],
  ['body', /身体|全身|躯干|手部|手足|足部|脚部|\b(?:body|hands?|foot|feet)\b/giu],
  // A pump head and body-hair removal are not evidence of scalp/hair care.
  ['head', /头部|头皮|头发|\b(?:scalp|hair(?!\s+removal\b))\b/giu],
];
const NEGATIVE_BEFORE = /(?:不(?:适用|适合|用于|供|可(?:以)?(?:用|装|盛|灌)|能(?:用|装)|推荐|支持|建议)|避免用于|禁(?:止)?(?:用|装)|不得(?:用|装)|\bnot\s+(?:suitable\s+|intended\s+)?for\b|\bnot\s+(?:suitable|applicable)\b|\bdo\s+not\s+use\b)/iu;
const NEGATIVE_IMMEDIATE = /(?:而非|并非|非|不是|无用途为|\bnot\s+)\s*$/iu;
const SHARED_MARKER = /图册整页|整页(?:参考|共用)|共用参考|共享参考|原页(?:共用|参考)|source[ -]page\s+reference/iu;
const unique = values => [...new Set(values.filter(v => typeof v === 'string' && v.trim()).map(v => v.trim()))];
const asText = value => typeof value === 'string' ? value.normalize('NFKC').trim() : '';
const isProduct = record => record && typeof record === 'object' && (!record.kind || record.kind === 'package');

function columnValue(value) {
  if (typeof value === 'string') return value;
  if (!value || typeof value !== 'object' || Array.isArray(value)) return '';
  if (value.shared || value.sharedPage || ['page','source_page','catalog'].includes(value.scope)) return '';
  return typeof value.value === 'string' ? value.value : '';
}

function scopedSources(record) {
  if (!isProduct(record)) return [];
  const sources=[];
  const name=asText(record.name);
  if (name && !SHARED_MARKER.test(name)) sources.push(name);
  sources.push(...(Array.isArray(record.uses) ? record.uses : typeof record.uses === 'string' ? [record.uses] : []).map(asText));
  // Only literal named usage/area columns are accepted. Spreadsheet letters,
  // OCR excerpts, source captions and generic fieldEvidence are not usage columns.
  for (const cells of [record.rawCells, record.rawCells?.original]) {
    if (!cells || typeof cells !== 'object' || Array.isArray(cells)) continue;
    for (const [key,value] of Object.entries(cells)) {
      const label=asText(key).replace(/[\s:_-]/g,'');
      if (!USAGE_COLUMN.test(label) && !AREA_COLUMN.test(label)) continue;
      const s=asText(columnValue(value));
      if (s && s.length<=500 && !SHARED_MARKER.test(s)) sources.push(s);
    }
  }
  // Explicit administrator-authored usage details count; imported whole-page
  // remarks/extraRaw do not become reliable merely by being copied into a detail.
  for (const detail of Array.isArray(record.productDetails) ? record.productDetails : []) {
    if (!detail || typeof detail !== 'object') continue;
    const label=asText(detail.label).replace(/[\s:_-]/g,'');
    if ((!USAGE_COLUMN.test(label) && !AREA_COLUMN.test(label)) || !['','name','uses'].includes(detail.sourceField || '')) continue;
    const value=asText(detail.value);
    if (value && value.length<=500 && !SHARED_MARKER.test(value)) sources.push(value);
  }
  return unique(sources);
}

function clauses(source) {
  // "Not only"/"不限于" is positive, while a negative list remains one scope.
  const result=[];
  const sentences=source.replace(/(?:不仅(?:限于)?|不只(?:是)?|不限于|\bnot\s+only\b)/giu,' ')
    .split(/[；;。\n\r]+|但是|但|而是|\bbut\b/giu);
  for(const sentence of sentences){
    let negativeList=false;
    for(let clause of sentence.split(/[，,]+/u).map(s=>s.trim()).filter(Boolean)){
      if(/^(?:不是|并非|非(?!标))/u.test(clause))clause='不适用于'+clause;
      const negative=NEGATIVE_BEFORE.test(clause);
      const explicitPositive=!negative&&/(?:可以|可用|可装|适用|适合|用于|使用|专用|仅供|\bfor\b|\bonly\b)/iu.test(clause);
      result.push(negativeList&&!explicitPositive?'不适用于'+clause:clause);
      if(negative)negativeList=true;
      else if(explicitPositive)negativeList=false;
    }
  }
  return result;
}

function positiveMatch(source, expression) {
  for (const clause of clauses(source)) {
    // Clone the regexp so exported functions never depend on a shared lastIndex.
    for (const match of clause.matchAll(new RegExp(expression.source, expression.flags))) {
      const before=clause.slice(0,match.index);
      const after=clause.slice(match.index+match[0].length);
      if (NEGATIVE_BEFORE.test(before) || NEGATIVE_IMMEDIATE.test(before)) continue;
      if (/^\s*[（(]?\s*(?:不适用|不适合|禁用|不可用)/u.test(after)) continue;
      return true;
    }
  }
  return false;
}

function inferred(record) {
  const sources=scopedSources(record);
  const labels=[];const sections=new Set();
  for (const [label,re,section] of RULES) {
    if (!sources.some(source=>positiveMatch(source,re))) continue;
    labels.push(label);
    if (section) sections.add(section);
  }
  for (const [section,re] of SECTION_RULES) {
    if (sources.some(source=>positiveMatch(source,re))) sections.add(section);
  }
  return {labels,sections};
}

/** Maintained values remain intact; only product-scoped positive evidence adds tags. */
export function recordUses(record) {
  if (!isProduct(record)) return [];
  const maintained=Array.isArray(record.uses) ? record.uses : typeof record.uses==='string' ? [record.uses] : [];
  return unique([...maintained,...inferred(record).labels]);
}

/** May return both regions; generic serum/lotion/sunscreen/oil never implies a region. */
export function recordSections(record) {
  if (!isProduct(record)) return [];
  const sections=inferred(record).sections;
  return ['face','body-head'].filter(section=>sections.has(section));
}

/** Three independent body areas; maintained areas and positive product evidence form a union. */
export function recordBodySections(record) {
  if (!isProduct(record)) return [];
  const maintained = Array.isArray(record.bodyAreas) ? record.bodyAreas : [];
  const sections = new Set(maintained.filter(section => BODY_SECTIONS.includes(section)));
  const sources = scopedSources(record);
  for (const [label, expression, section] of RULES) {
    if (!section || !sources.some(source => positiveMatch(source, expression))) continue;
    sections.add(section === 'face' ? 'face' : HEAD_USES.has(label) ? 'head' : 'body');
  }
  for (const [section, expression] of BODY_SECTION_RULES) {
    if (sources.some(source => positiveMatch(source, expression))) sections.add(section);
  }
  return BODY_SECTIONS.filter(section => sections.has(section));
}

/** Common choices plus all actual maintained/inferred values from active packages. */
export function usageOptions(records) {
  const choices=RULES.map(([label])=>label);
  for (const record of Array.isArray(records) ? records : []) {
    if (!isProduct(record) || record.archived) continue;
    choices.push(...recordSearchUses(record));
  }
  return unique(choices);
}

// A second, explicitly referential dimension. Never write these suggestions
// into maintained uses or infer a body area from them. These exact structure
// aliases mirror usage_references.py; parity tests cover their public contract.
const REFERENCE_CATEGORIES = new Map([
  ...['','瓶','瓶类','bottle','bottles'].map(value=>[value,'bottle']),
  ...['软管','tube','tubes'].map(value=>[value,'tube']),
  ...['罐','罐类','罐与广口盒','jar','jars'].map(value=>[value,'jar']),
  ...['滴管与滴管瓶','滴管','dropper','droppers'].map(value=>[value,'dropper']),
]);
const REFERENCE_RULES = [
  [['软管','tube','tubes'],'tube',['洁面','护手霜','身体乳']],
  [['滴管瓶','精油滴管瓶','精华滴管瓶','dropper bottle'],'dropper',['精华液','精油']],
  [['真空瓶','可替换真空瓶','airless bottle','airless'],'bottle',['精华液','乳液','面霜']],
  [['乳液瓶','lotion bottle'],'bottle',['乳液','身体乳']],
  [['泡沫瓶','慕斯瓶','foam bottle','foaming bottle','foam'],'bottle',['洁面','洗手液']],
  [['喷雾瓶','spray bottle','spray'],'bottle',['爽肤水','身体香氛']],
  [['膏霜罐','广口膏霜罐','广口罐','cream jar'],'jar',['面霜','身体霜']],
  [['滚珠瓶','roll-on bottle','roller bottle','香水瓶','perfume bottle'],'bottle',['香水']],
];
const REFERENCE_BY_TYPE = new Map(REFERENCE_RULES.flatMap(([aliases,family,labels])=>aliases.map(alias=>[alias,{family,labels,ruleId:aliases[0]}])));
const REFERENCE_BY_CATEGORY = {tube:{labels:['洁面','护手霜','身体乳'],ruleId:'软管'},jar:{labels:['面霜','身体霜'],ruleId:'膏霜罐'}};
const SPECIAL_TUBE_USES = new Set(['唇彩','唇部护理','眼霜','眼部精华','口腔护理','眉妆','睫毛产品','美甲','染发','脱毛','家居清洁','洗衣液']);
const structureKey = value=>asText(value).toLowerCase();

export function referenceUseInfo(record) {
  const empty={mode:'automatic',labels:[],ruleId:'',reason:''};
  if(!isProduct(record))return empty;
  const maintained=unique(Array.isArray(record.uses)?record.uses:typeof record.uses==='string'?[record.uses]:[]);
  if(Object.hasOwn(record,'referenceUses'))return {...empty,mode:'manual',labels:unique(Array.isArray(record.referenceUses)?record.referenceUses:[]).filter(value=>!maintained.includes(value)),reason:'管理员维护的参考用途'};
  const rawCategory=structureKey(record.category),category=rawCategory==='待细分'?'':rawCategory,type=structureKey(record.bottleType),family=REFERENCE_CATEGORIES.get(category);
  if(!family)return empty;
  let rule;
  if(type){
    rule=REFERENCE_BY_TYPE.get(type);
    if(!rule||category&&family!==rule.family&&!(family==='bottle'&&rule.family==='dropper'))return empty;
  }else rule=REFERENCE_BY_CATEGORY[family];
  if(!rule||rule.ruleId==='软管'&&recordUses(record).some(value=>SPECIAL_TUBE_USES.has(value)))return empty;
  return {...empty,labels:rule.labels.filter(value=>!maintained.includes(value)),ruleId:rule.ruleId,reason:'依据明确包材结构整理，具体适配待确认'};
}

export function recordReferenceUses(record) {return referenceUseInfo(record).labels;}
export function recordSearchUses(record) {return unique([...recordUses(record),...recordReferenceUses(record)]);}

const USAGE_SEARCH_ALIASES = {
  '洁面':['洗面奶','洗颜','face wash','facial cleanser'],
  '护手霜':['手霜','hand cream'],'身体乳':['body lotion'],
  '精华液':['精华','精华露','精华素','serum'],'精油':['essential oil'],
  '乳液':['lotion'],'面霜':['face cream','facial cream'],
  '洗手液':['洗手慕斯','hand wash','hand soap'],
  '爽肤水':['toner','facial toner'],'身体香氛':['身体喷雾','body mist','body fragrance'],
  '身体霜':['身体润肤霜','body cream','body butter'],'香水':['perfume','eau de parfum','eau de toilette'],
};
export function usageSearchTerms(record) {return unique(recordSearchUses(record).flatMap(label=>[label,...(USAGE_SEARCH_ALIASES[label]||[])]));}
