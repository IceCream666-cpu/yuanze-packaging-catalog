// Isolated design prototype: screenshot rates are illustrative, never live quotes.
(() => {
  'use strict';
  const $ = selector => document.querySelector(selector);
  const esc = value => String(value ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const state = {role:'employee', empty:false, language:'zh', selected:new Set(), colors:{silk:1,foil:1,spray:1}, favorite:false, shortlist:false};
  const words = {
    zh:{catalog:'包材选型库',details:'产品详情',name:'面霜罐',kind:'膏霜类',code:'产品编号',price:'裸瓶价格',currency:'¥',per:'/ 个',history:'历史询价',terms:'含运 · 不含税',tax:'含税价格未录入',material:'材质',spec:'规格',moq:'MOQ · 起订量',lead:'货期',use:'通常用于',cream:'面霜',reference:'选型参考',days:'天',units:'个',craft:'加工工艺',craftHint:'费用、起订与货期分别记录',craftName:'工艺',fee:'费用',minimum:'起订量',estimated:'预计货期',bare:'裸瓶',above:'见上方',base:'基础项',silk:'丝印',foil:'烫金 / 烫银',injection:'注塑色',spray:'喷涂',frost:'蒙砂',bodyPlate:'电镀瓶身',capPlate:'电镀盖子',other:'其他工艺',craftNote:'空白表示未录入。工艺可能改变 MOQ、货期和价格，由业务员结合需求判断。',selected:'已标记',selectedEnd:'；不自动合计报价',stock:'现货情况',stockUnknown:'未确认',stockPhoto:'暂无已确认的现货图',internal:'内部资料与原始报价',internalHint:'供应商、税运条件、原文出处',supplier:'供应商',contact:'联系方式',supplierExample:'示例供应商',contactExample:'示例业务联系人',raw:'原始报价',source:'来源',sourceValue:'截图对应询价记录 · 第 8 行',evidence:'50g；裸瓶价格1.8元；5000；20天',internalNote:'演示中的联系人为占位；未录入材质，不根据图片推断。',favorite:'收藏',favorited:'已收藏',compare:'加入对比',compared:'已加入对比',intent:'加入意向清单',intended:'已加入意向',download:'下载图片',photo:'优化主图',enlarge:'点击查看大图',note:'价格与交付条件需按本次需求复核。',clientNote:'图片与规格用于选型，具体需求可交由业务员确认。',demoAction:'已在本次预览中标记，未写入正式系统。',viewBlank:'未录入',close:'关闭图片'},
    en:{catalog:'Packaging library',details:'Product details',name:'Cream jar',kind:'Cream packaging',code:'Product code',price:'Bare container price',currency:'¥',per:'/ unit',history:'Historical quote',terms:'Freight included · tax excluded',tax:'Tax-inclusive price not recorded',material:'Material',spec:'Specification',moq:'MOQ',lead:'Lead time',use:'Typically used for',cream:'Face cream',reference:'Selection reference',days:' days',units:' units',craft:'Finishing options',craftHint:'Fee, MOQ and lead time recorded separately',craftName:'Finish',fee:'Fee',minimum:'MOQ',estimated:'Lead time',bare:'Bare container',above:'See above',base:'Base item',silk:'Screen printing',foil:'Gold / silver foil',injection:'Moulded colour',spray:'Spray coating',frost:'Frosting',bodyPlate:'Body plating',capPlate:'Cap plating',other:'Other finish',craftNote:'Blank fields are not recorded. Finishing may affect MOQ, lead time and price; confirm for each request.',selected:'Marked',selectedEnd:'; no automatic quote total',stock:'Stock availability',stockUnknown:'Unconfirmed',stockPhoto:'No confirmed stock photo',internal:'Internal information & source quote',internalHint:'Supplier, terms and source evidence',supplier:'Supplier',contact:'Contact',supplierExample:'Example supplier',contactExample:'Example business contact',raw:'Source quote',source:'Source',sourceValue:'Quoted record shown in the reference · row 8',evidence:'50g; bare container CNY 1.8; 5000; 20 days',internalNote:'Contacts are placeholders. Material is not inferred from the image.',favorite:'Save',favorited:'Saved',compare:'Compare',compared:'Added to compare',intent:'Add to enquiry list',intended:'Added to enquiry',download:'Download image',photo:'Enhanced product image',enlarge:'View larger image',note:'Confirm price and delivery terms for each request.',clientNote:'Images and specifications support selection. Confirm your requirements with your sales contact.',demoAction:'Marked in this preview only; no production data changed.',viewBlank:'Not recorded',close:'Close image'}
  };
  const finishes = ['silk','foil','injection','spray','frost','bodyPlate','capPlate','other'];
  const demoRates={silk:0.10,foil:0.20,spray:0.50};
  const estimateWords={
    zh:{demo:'演示标准 · 费用待补充确认',unit:'/ 色',colors:'颜色数',estimate:'选配参考价',base:'裸瓶 + 已选工艺',need:'所选工艺费用未填写，暂不能估算',unknown:'缺少费用',missing:'裸瓶价格未录入，暂不能估算',partial:'已知工艺费用',hint:'按截图示例标准估算，未计材质差价、配件及税费；不作为正式报价。MOQ、货期需按选配工艺另行确认。',none:'选择工艺，预览参考价格',invalid:'颜色数量须为 1–9 的整数',plus:'工艺增量',per:'/ 个'},
    en:{demo:'Demo rates · pending confirmation',unit:'/ colour',colors:'Colour count',estimate:'Estimated configured price',base:'Bare container + selected finishes',need:'Selected finishing fees are missing; estimate unavailable',unknown:'Missing fees',missing:'Bare container price not recorded; estimate unavailable',partial:'Known finishing fees',hint:'Based on illustrative rates. Material differences, components and tax are excluded; this is not a formal quote. Confirm MOQ and lead time for selected finishes.',none:'Select finishes to preview a reference price',invalid:'Colour count must be a whole number from 1 to 9',plus:'Finishing increment',per:'/ unit'}
  };
  function estimate() {
    const unknown=[],invalid=[];let cents=0;
    for(const finish of state.selected){
      if(demoRates[finish]===undefined){unknown.push(finish);continue;}
      const count=Number(state.colors[finish]);
      if(!Number.isInteger(count)||count<1||count>9){invalid.push(finish);continue;}
      cents+=Math.round(demoRates[finish]*100)*count;
    }
    return {unknown,invalid,increment:(cents/100).toFixed(2),total:(!state.empty&&!unknown.length&&!invalid.length)?((180+cents)/100).toFixed(2):null};
  }
  function estimateMarkup(w) {
    const e=estimate(),ew=estimateWords[state.language];
    const result=!state.selected.size?`<p class="estimate-placeholder">${ew.none}</p>`:e.total!==null?`<div class="estimate-result"><span class="estimate-total">¥${e.total}<small>${ew.per}</small></span><span>${ew.plus} + ¥${e.increment}</span></div>`:`<p class="estimate-missing">${state.empty?ew.missing:e.invalid.length?ew.invalid:ew.need}</p>${e.unknown.length?`<p class="estimate-partial">${ew.unknown}：${e.unknown.map(f=>w[f]).join('、')}</p>`:''}`;
    return `<section class="estimate" aria-label="${ew.estimate}" aria-live="polite"><div class="estimate-title"><h3>${ew.estimate}</h3><span>${ew.base}</span></div>${result}<p class="estimate-hint">${ew.hint}</p></section>`;
  }
  const emptyCell = label => `<span class="blank" aria-label="${esc(label)}">—</span>`;
  function render() {
    const w = words[state.language], ew=estimateWords[state.language], employee = state.role === 'employee';
    document.documentElement.lang = state.language === 'zh' ? 'zh-CN' : 'en';
    const zh=state.language==='zh';
    $('#preview-title').textContent=zh?'产品详情 · 设计预览':'Product details · Design preview';
    $('#preview-note').textContent=zh?'本地 demo':'Local demo';
    $('#role-label').textContent=zh?'视角':'View';
    $('#scenario-label').textContent=zh?'资料':'Data';
    $('#role option[value="employee"]').textContent=zh?'业务员':'Employee';
    $('#role option[value="client"]').textContent=zh?'客户':'Client';
    $('#scenario option[value="known"]').textContent=zh?'现有资料':'Recorded';
    $('#scenario option[value="empty"]').textContent=zh?'未录入状态':'Not recorded';
    $('#language').setAttribute('aria-label',zh?'切换中英文':'Switch language');
    $('#breadcrumbs').innerHTML = `<span>${w.catalog}</span><span aria-hidden="true">/</span><span>${w.details}</span>`;
    $('#detail').innerHTML = `<article class="detail-layout">
      <section class="gallery" aria-label="${w.photo}">
        <button type="button" class="hero-image" data-action="image" aria-label="${w.enlarge}"><img src="./sample.png" alt="${w.name}" fetchpriority="high"><span class="expand-image" aria-hidden="true">↗</span></button>
        <div class="gallery-caption"><span>${w.photo}</span><a class="download" href="./sample.png" download="YZ-BC-000005.png">↓ ${w.download}</a></div>
        <div class="photo-foot"><button type="button" class="photo-thumb" data-action="image" aria-label="${w.enlarge}"><img src="./sample.png" alt=""></button><span>${w.enlarge}</span></div>
      </section>
      <section class="detail-info" aria-label="${w.details}">
        <p class="eyebrow">PACKAGING / 005</p>
        <div class="title-row"><h1>${w.name}</h1><span class="badge">${w.kind}</span></div>
        <p class="code">${w.code} · YZ-BC-000005</p>
        ${employee ? `<section class="price-block" aria-label="${w.price}"><div class="price-head"><span>${w.price}</span><span class="price-unit">${w.history}</span></div><div class="price-value">${state.empty ? emptyCell(w.viewBlank) : `<span class="currency">${w.currency}</span>1.80<span class="per">${w.per}</span>`}</div><p class="price-terms">${state.empty ? '&nbsp;' : `<strong>${w.terms}</strong> &nbsp;·&nbsp; ${w.tax}`}</p></section>` : ''}
        <dl class="facts">
          <div class="fact"><dt>${w.material}</dt><dd class="empty" aria-label="${w.viewBlank}"></dd></div>
          <div class="fact"><dt>${w.spec}</dt><dd>${state.empty ? '' : '50 g'}</dd></div>
          <div class="fact"><dt>${w.moq}</dt><dd>${state.empty ? '' : '5,000'+w.units}</dd></div>
          <div class="fact"><dt>${w.lead}</dt><dd>${state.empty ? '' : '20'+w.days}</dd></div>
          <div class="fact" style="grid-column:1/-1"><dt>${w.use}</dt><dd class="use">${state.empty ? '' : `<span>${w.cream}</span><span class="use-note">${w.reference}</span>`}</dd></div>
        </dl>
        ${employee ? `<section aria-label="${w.craft}"><div class="section-head"><h2>${w.craft}</h2><span class="demo-rate-label">${ew.demo}</span></div><div class="table-wrap"><table><thead><tr><th scope="col">${w.craftName}</th><th scope="col">${w.fee}</th><th scope="col">${w.minimum}</th><th scope="col">${w.estimated}</th></tr></thead><tbody><tr class="basis-row"><td>${w.bare}</td><td>${w.above}</td><td colspan="2">${w.base}</td></tr>${finishes.map(f=>`<tr class="${state.selected.has(f)?'selected-row':''}"><td><label class="craft-label"><input type="checkbox" value="${f}" ${state.selected.has(f)?'checked':''}><span>${w[f]}</span></label></td><td>${demoRates[f]!==undefined?`<span class="finish-rate">¥${demoRates[f].toFixed(2)} <small>${ew.unit}</small></span>${state.selected.has(f)?`<label class="colour-count"><input type="number" min="1" max="9" step="1" value="${esc(state.colors[f])}" data-colours="${f}" aria-label="${esc(w[f]+' '+ew.colors)}"><span>${state.language==='zh'?'色':'colours'}</span></label>`:''}`:''}</td><td></td><td></td></tr>`).join('')}</tbody></table></div><p class="table-note">${w.craftNote}</p>${estimateMarkup(w)}</section>` : ''}
        <section class="stock" aria-label="${w.stock}"><div><h2>${w.stock}</h2><span class="stock-empty">${w.stockPhoto}</span></div><span class="stock-status"><i class="stock-dot" aria-hidden="true"></i>${w.stockUnknown}</span></section>
        ${employee ? `<details class="internal"><summary><span>${w.internal}<br><small>${w.internalHint}</small></span></summary><div class="internal-content"><dl><div><dt>${w.supplier}</dt><dd>${w.supplierExample}</dd></div><div><dt>${w.contact}</dt><dd>${w.contactExample}</dd></div></dl><p><strong>${w.raw}</strong>　${state.empty ? '' : w.evidence}</p><p><strong>${w.source}</strong>　${w.sourceValue}</p><small>${w.internalNote}</small></div></details>` : ''}
        <div class="actions"><button type="button" class="button" data-action="favorite" aria-pressed="${state.favorite}">${state.favorite ? '★ '+w.favorited : '☆ '+w.favorite}</button><button type="button" class="button primary" data-action="shortlist" aria-pressed="${state.shortlist}">${state.shortlist ? (employee ? w.compared : w.intended) : (employee ? w.compare : w.intent)} <span aria-hidden="true">↗</span></button></div>
        <p class="footer-note">${employee ? w.note : w.clientNote}</p>
      </section>
    </article>`;
    $('#close-image').setAttribute('aria-label',w.close);
    $('#lightbox-title').textContent = w.name;
    $('#lightbox-image').alt = w.name;
  }
  function notify() {
    const notice=$('#notice');notice.textContent=words[state.language].demoAction;notice.classList.add('visible');
    clearTimeout(notify.timer);notify.timer=setTimeout(()=>notice.classList.remove('visible'),2500);
  }
  $('#role').addEventListener('change',e=>{state.role=e.target.value;state.selected.clear();state.shortlist=false;render();});
  $('#scenario').addEventListener('change',e=>{state.empty=e.target.value==='empty';render();});
  $('#language').addEventListener('click',()=>{state.language=state.language==='zh'?'en':'zh';render();});
  function updateColour(e) {
    const finish=e.target.dataset.colours;
    if(!Object.hasOwn(demoRates,finish)||state.role!=='employee')return;
    state.colors[finish]=e.target.value;
    $('.estimate').outerHTML=estimateMarkup(words[state.language]);
  }
  $('#detail').addEventListener('input',updateColour);
  $('#detail').addEventListener('change',e=>{
    if(e.target.dataset.colours){updateColour(e);return;}
    if(e.target.type!=='checkbox')return;const value=e.target.value;if(!finishes.includes(value))return;e.target.checked?state.selected.add(value):state.selected.delete(value);render();$(`input[value="${value}"]`)?.focus({preventScroll:true});
  });
  $('#detail').addEventListener('click',e=>{
    const action=e.target.closest('[data-action]')?.dataset.action;
    if(action==='image'){$('#lightbox-image').src='./sample.png';$('#image-dialog').showModal();}
    if(action==='favorite'){state.favorite=!state.favorite;render();$('[data-action="favorite"]').focus({preventScroll:true});notify();}
    if(action==='shortlist'){state.shortlist=!state.shortlist;render();$('[data-action="shortlist"]').focus({preventScroll:true});notify();}
  });
  $('#close-image').addEventListener('click',()=>$('#image-dialog').close());
  $('#image-dialog').addEventListener('click',e=>{if(e.target===$('#image-dialog'))$('#image-dialog').close();});
  render();
})();
