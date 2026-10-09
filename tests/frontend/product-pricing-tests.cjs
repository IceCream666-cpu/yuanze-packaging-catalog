const {test}=require('node:test');
const assert=require('node:assert/strict');
const path=require('node:path');
const {JSDOM}=require('jsdom');
const {evaluateBrowserModule}=require('./module-loader.cjs');

const root=path.resolve(__dirname,'../../server-reference/public');
async function setup(){
  const dom=new JSDOM('<body><main></main></body>',{url:'https://synthetic.test/',runScripts:'outside-only'});
  const pricing=(await evaluateBrowserModule(dom,path.join(root,'product-pricing.js'))).namespace;
  const view=(await evaluateBrowserModule(dom,path.join(root,'product-detail-view.js'))).namespace;
  return {dom,pricing,view,close:()=>dom.window.close()};
}
const values=entries=>Array.from(entries,entry=>entry.value);
const joined=entries=>values(entries).join('\n');
const record=(quoteRaw,extra={})=>({id:'synthetic-quote',kind:'package',quoteRaw,...extra});
function assertOriginal(pricing,input){
  const data=pricing.pricingData(input);
  assert.equal(Array.from(data.quoteOriginal).find(row=>row[0]==='原始报价（含配置与分项）')?.[1],input.quoteRaw.trim());
  const container=new JSDOM(pricing.renderPricing(input)).window.document;
  assert.ok(container.querySelector('.pricing-original').textContent.includes(input.quoteRaw.trim()));
  container.defaultView.close();
}

test('bare scope selects only the current mass specification from a multiline quote',async()=>{
  const e=await setup();try{
    const quoteRaw='裸瓶\n30g：1.10元/个\n50g：1.50元/个';
    for(const [specificationRaw,wanted,unwanted] of [['30g','1.10','1.50'],['50 g','1.50','1.10']]){
      const input=record(quoteRaw,{specificationRaw});
      const data=e.pricing.pricingData(input);
      assert.equal(data.bare.length,1,'One current specification must provide one bare quotation');
      assert.deepEqual(values(data.ordinary),[],'Prices in bare scope must not reappear as generic quotations');
      assert.match(joined(data.bare),new RegExp(wanted.replace('.','\\.')));
      assert.doesNotMatch(joined(data.bare),new RegExp(unwanted.replace('.','\\.')));
      assertOriginal(e.pricing,input);
    }
    for(const specificationRaw of ['', '100g']){
      assert.deepEqual(values(e.pricing.pricingData(record(quoteRaw,{specificationRaw})).bare),[],'Absent or unmatched specification must not pick another product price');
    }
  }finally{e.close();}
});

test('bare scope selects the current volume using explicit capacity and leaves pump quotes separate',async()=>{
  const e=await setup();try{
    const quoteRaw='裸瓶价格\n30mL：1.20元/个\n50mL：1.60元/个\n泵头0.42元/个';
    const input=record(quoteRaw,{capacityMl:50});
    const data=e.pricing.pricingData(input);
    assert.equal(data.bare.length,1);
    assert.deepEqual(values(data.ordinary),[]);
    assert.match(joined(data.bare),/1\.60/);
    assert.doesNotMatch(joined(data.bare),/1\.20|0\.42/);
    assertOriginal(e.pricing,input);
  }finally{e.close();}
});

test('bare context recognizes a following without-pump price without adding the pump price',async()=>{
  const e=await setup();try{
    const input=record('裸瓶\n不加泵头1.65元/个\n泵头0.42元/个');
    const data=e.pricing.pricingData(input);
    assert.equal(data.bare.length,1);
    assert.deepEqual(values(data.ordinary),[]);
    assert.match(joined(data.bare),/不加泵头1\.65元\/个/);
    assert.doesNotMatch(joined(data.bare),/0\.42/);
    assertOriginal(e.pricing,input);
  }finally{e.close();}
});

test('bare set quotations retain their documented set unit and cannot become a per-item estimate',async()=>{
  const e=await setup();try{
    for(const quoteRaw of ['裸瓶一套3.1','裸瓶\n一套是2.6','裸瓶\n2块钱/套','裸瓶：2块钱/套']){
      const input=record(quoteRaw),data=e.pricing.pricingData(input),bare=joined(data.bare);
      assert.equal(data.bare.length,1,quoteRaw);
      assert.match(bare,/套/,quoteRaw+' must retain the original unit');
      assert.match(bare,quoteRaw.includes('3.1')?/3\.1/:quoteRaw.includes('2.6')?/2\.6/:/2块钱/,quoteRaw);
      assert.equal(e.view.bareAmount(bare,'CNY'),null,quoteRaw+' is not a per-item estimate');
      assertOriginal(e.pricing,input);
    }
  }finally{e.close();}
});

test('explicit bare-container configurations preserve every component and do not infer a currency or a per-item base',async()=>{
  const e=await setup();try{
    for(const quoteRaw of ['裸瓶+银色盖：2.6','裸瓶+泵头+盖子 2.8 一套','裸瓶+喷砂工艺：1.3元']){
      const input=record(quoteRaw),data=e.pricing.pricingData(input),bare=joined(data.bare);
      assert.deepEqual(values(data.bare),[quoteRaw],'An explicit complete configuration remains one complete quote');
      assert.deepEqual(values(data.ordinary),[],'A configured quote must not become a generic bare amount');
      assert.equal(e.view.bareAmount(bare,input.currency),null,'Components or finishing prevent an unconditional per-item base');
      assert.equal(e.view.bareAmount(bare,'CNY'),null,'Adding a known currency still must not erase the configuration');
      assertOriginal(e.pricing,input);
    }
  }finally{e.close();}
});

test('direct bare-container and bottle-body prices remain available verbatim',async()=>{
  const e=await setup();try{
    for(const quoteRaw of ['裸瓶1.80元/瓶','裸瓶报价：1.80元/个','瓶身1.80元/个','瓶体价格：1.80元']){
      const input=record(quoteRaw),data=e.pricing.pricingData(input);
      assert.deepEqual(values(data.bare),[quoteRaw]);
      assert.deepEqual(values(data.ordinary),[]);
      assertOriginal(e.pricing,input);
    }
  }finally{e.close();}
});

test('body finishing fees cannot appear as a bare-container price',async()=>{
  const e=await setup();try{
    for(const quoteRaw of ['瓶身渐变0.30元/个','瓶身喷镀加工费0.40元/个','瓶身做色+0.12元/个','瓶体喷涂0.20元/个']){
      const input=record(quoteRaw),data=e.pricing.pricingData(input);
      assert.deepEqual(values(data.bare),[],quoteRaw);
      assert.deepEqual(values(data.ordinary),[],quoteRaw);
      assertOriginal(e.pricing,input);
    }
  }finally{e.close();}
});

test('bare mentions, capacities and MOQ cannot borrow an accessory price from the same quote',async()=>{
  const e=await setup();try{
    for(const quoteRaw of ['裸瓶50mL，泵头0.30元/个','裸瓶报价待确认，瓶盖0.20元/个','裸瓶\n50mL\n5000个起\n泵头0.42元/个']){
      const input=record(quoteRaw),data=e.pricing.pricingData(input);
      assert.deepEqual(values(data.bare),[],quoteRaw);
      assert.deepEqual(values(data.ordinary),[],quoteRaw);
      assertOriginal(e.pricing,input);
    }
  }finally{e.close();}
});

test('discount deltas, labelling and neck modification fees cannot appear as ordinary unit prices',async()=>{
  const e=await setup();try{
    for(const quoteRaw of ['优惠0.03元/个','每个少0.03元','贴标0.15元/个','改牙费800元']){
      const input=record(quoteRaw),data=e.pricing.pricingData(input);
      assert.deepEqual(values(data.ordinary),[],quoteRaw);
      assert.deepEqual(values(data.bare),[],quoteRaw);
      assertOriginal(e.pricing,input);
    }
  }finally{e.close();}
});

test('ordinary reference prices also provide the bare price while preserving their original currency and unit text',async()=>{
  const e=await setup();try{
    for(const quoteRaw of ['1.8','1.8元/瓶','1.8元/个']){
      const input=record(quoteRaw),data=e.pricing.pricingData(input);
      assert.deepEqual(values(data.ordinary),[quoteRaw]);
      assert.deepEqual(values(data.bare),[quoteRaw]);
      assert.equal(e.view.coreFacts(input).bare,quoteRaw);
      if(quoteRaw==='1.8')assert.equal(e.view.bareAmount(joined(data.bare),input.currency),null,'A pure number does not establish a currency or unit for calculation');
      assertOriginal(e.pricing,input);
    }
  }finally{e.close();}
});

test('ordinary reference quotations select only the current mass or volume specification before bare fallback',async()=>{
  const e=await setup();try{
    for(const [quoteRaw,extra,wanted,unwanted] of [
      ['30g：1.10元/个\n50g：1.50元/个',{specificationRaw:'50 g'},'1.50','1.10'],
      ['30mL：1.20元/瓶\n50mL：1.60元/瓶',{capacityMl:50},'1.60','1.20'],
    ]){
      const input=record(quoteRaw,extra),data=e.pricing.pricingData(input);
      assert.equal(data.ordinary.length,1);
      assert.equal(data.bare.length,1);
      assert.match(joined(data.ordinary),new RegExp(wanted.replace('.','\\.')));
      assert.match(joined(data.bare),new RegExp(wanted.replace('.','\\.')));
      assert.doesNotMatch(joined(data.ordinary),new RegExp(unwanted.replace('.','\\.')));
      assert.doesNotMatch(joined(data.bare),new RegExp(unwanted.replace('.','\\.')));
      assertOriginal(e.pricing,input);
    }
  }finally{e.close();}
});

test('ordinary fallback keeps quantity tiers and conditions visible without turning them into a single base amount',async()=>{
  const e=await setup();try{
    const input=record('5000个1.80元/瓶，10000个1.60元/瓶；不含税，含运'),data=e.pricing.pricingData(input);
    assert.deepEqual(values(data.ordinary),[input.quoteRaw]);
    assert.deepEqual(values(data.bare),[input.quoteRaw]);
    assert.equal(e.view.bareAmount(joined(data.bare),'CNY'),null);
    assertOriginal(e.pricing,input);
  }finally{e.close();}
});

test('capacity and neck-dimension OCR are not ordinary or bare-container prices',async()=>{
  const e=await setup();try{
    for(const quoteRaw of ['300mL','24mm','300mL/24mm','容量300mL，口径24mm','30g/50g']){
      const input=record(quoteRaw),data=e.pricing.pricingData(input);
      assert.deepEqual(values(data.ordinary),[],quoteRaw);
      assert.deepEqual(values(data.bare),[],quoteRaw);
      assertOriginal(e.pricing,input);
    }
  }finally{e.close();}
});

test('explicit bare-field clearing and administrator detail values keep precedence over source quotation',async()=>{
  const e=await setup();try{
    const quoteRaw='裸瓶报价1.80元/个';
    for(const bareBottlePrice of ['',null]){
      const data=e.pricing.pricingData(record(quoteRaw,{bareBottlePrice,productDetails:[{label:'裸瓶报价',value:'1.90元/个'}]}));
      assert.deepEqual(values(data.bare),[],'The presence of a cleared field suppresses all historical bare fallbacks');
      const ordinary=e.pricing.pricingData(record('1.80元/瓶',{bareBottlePrice}));
      assert.deepEqual(values(ordinary.ordinary),['1.80元/瓶']);
      assert.deepEqual(values(ordinary.bare),[],'Explicit clearing also suppresses ordinary-price fallback');
    }
    const explicit=record(quoteRaw,{bareBottlePrice:'2.10元/个',productDetails:[{label:'裸瓶报价',value:'1.90元/个'}]});
    assert.deepEqual(values(e.pricing.pricingData(explicit).bare),['2.10元/个']);
    assert.deepEqual(values(e.pricing.pricingData(record(quoteRaw,{productDetails:[{label:'裸瓶报价',value:''}]})).bare),[]);
    assert.deepEqual(values(e.pricing.pricingData(record('1.80元/瓶',{productDetails:[{label:'裸瓶报价',value:''}]})).bare),[]);
    assert.deepEqual(values(e.pricing.pricingData(record(quoteRaw,{productDetails:[{label:'裸瓶报价',value:'1.90元/个'}]})).bare),['1.90元/个']);
    assertOriginal(e.pricing,explicit);
  }finally{e.close();}
});

test('quotation conditions and all source tiers remain unchanged when a current bare price is selected',async()=>{
  const e=await setup();try{
    const input=record('裸瓶\n30g：1.10元/个（5000个起）\n50g：1.50元/个（10000个起）',{
      specificationRaw:'50g',quoteHeader:'含运不含税',moqRaw:'10000个',leadTimeRaw:'20天',customQuoteRaw:'定制每套3.20元，交期另议',
    });
    const data=e.pricing.pricingData(input);
    assert.match(joined(data.bare),/1\.50元\/个（10000个起）/);
    assert.doesNotMatch(joined(data.bare),/1\.10/);
    assert.deepEqual(values(data.terms),['含运不含税']);
    assert.deepEqual(values(data.moq),['10000个']);
    assert.deepEqual(values(data.lead),['20天']);
    assert.equal(Array.from(data.quoteOriginal).find(row=>row[0]==='定制报价原文')?.[1],input.customQuoteRaw);
    assertOriginal(e.pricing,input);
  }finally{e.close();}
});

test('current-spec regular and limited-stock quotes retain stock quantity without borrowing sibling or finishing amounts',async()=>{
  const e=await setup();try{
    const quoteRaw='图片裸瓶含运不含税\n30g:4.3元/个\n50g:4.6元/个\n丝印0.1元/色\n有少量现货1000个左右，30g单价4.5元/个，50g单价4.8元/个丝印400元/色';
    for(const [specificationRaw,current,sibling] of [
      ['30g',['4.3','4.5'],['4.6','4.8']],
      ['50g',['4.6','4.8'],['4.3','4.5']],
    ]){
      const input=record(quoteRaw,{specificationRaw}),data=e.pricing.pricingData(input),bare=joined(data.bare);
      for(const price of current)assert.match(bare,new RegExp(price.replace('.','\\.')),specificationRaw+' must retain both regular and limited-stock prices');
      for(const price of sibling)assert.doesNotMatch(bare,new RegExp(price.replace('.','\\.')),specificationRaw+' must not display the sibling price');
      assert.match(bare,/少量现货/,'The available-stock condition must accompany its price');
      assert.match(bare,/1000个左右/,'The stock quantity must remain part of the conditional quote');
      assert.doesNotMatch(bare,/丝印|0\.1元|400元/,'Screen-printing fees are not product prices');
      assert.equal(e.view.bareAmount(bare,'CNY'),null,'Regular and stock tiers must not become one unconditional base amount');
      assertOriginal(e.pricing,input);
    }
  }finally{e.close();}
});

test('standalone without-pump quotations are bare prices without borrowing a separate pump range or dimensions',async()=>{
  const e=await setup();try{
    for(const exclusion of ['不加','不含','不带','不配']){
      const priceLine=exclusion+'泵头1.55元/个';
      const input=record('28牙78克不加工艺不含税\n'+priceLine+'\n泵头0.45-0.55元/个');
      const data=e.pricing.pricingData(input);
      assert.deepEqual(values(data.bare),[priceLine],'An independently priced without-pump line is the complete bare-price source');
      assert.doesNotMatch(joined(data.bare),/0\.45|0\.55|28牙|78克/,'Separate pump prices and specification numbers must not enter the bare value');
      assertOriginal(e.pricing,input);
      const dimensionOnly=record(exclusion+'泵头50mL');
      assert.deepEqual(values(e.pricing.pricingData(dimensionOnly).bare),[],'A without-pump description still requires an actual price');
      assert.deepEqual(values(e.pricing.pricingData(dimensionOnly).ordinary),[]);
      assertOriginal(e.pricing,dimensionOnly);
    }
  }finally{e.close();}
});

test('a quantity-conditioned product price retains an additional setup fee without becoming an unconditional base amount',async()=>{
  const e=await setup();try{
    const input=record('3000个单价1.38元，另外加上机费500元'),data=e.pricing.pricingData(input);
    assert.deepEqual(values(data.ordinary),[input.quoteRaw],'The full product quotation must retain its quantity and additional fixed fee');
    assert.deepEqual(values(data.bare),[input.quoteRaw],'Ordinary fallback must preserve the complete source conditions');
    assert.equal(e.view.bareAmount(joined(data.bare),input.currency),null);
    assert.equal(e.view.bareAmount(joined(data.bare),'CNY'),null,'Neither the conditional 1.38 nor the fixed 500 is an unconditional base amount');
    assertOriginal(e.pricing,input);
    for(const quoteRaw of ['上机费500元','丝印单价0.15元，另外加上机费500元']){
      const feeOnly=record(quoteRaw),fees=e.pricing.pricingData(feeOnly);
      assert.deepEqual(values(fees.ordinary),[],'A setup fee or processing unit price is not a product price');
      assert.deepEqual(values(fees.bare),[],'Processing-only quotes cannot feed the bare-price fallback');
      assertOriginal(e.pricing,feeOnly);
    }
  }finally{e.close();}
});

test('mass specifications written with 的 retain only their own prices and both quantity-tier conditions',async()=>{
  const e=await setup();try{
    for(const [productCode,specificationRaw,regular,bulk,otherRegular,otherBulk] of [
      ['YZ-BC-000115','30g','3.2','3.0','3.5','3.4'],
      ['YZ-BC-000116','50g','3.5','3.4','3.2','3.0'],
      ['YZ-BC-000117','30g','3.1','3.0','3.9','3.8'],
      ['YZ-BC-000118','50g','3.9','3.8','3.1','3.0'],
    ]){
      const isFirstPair=['YZ-BC-000115','YZ-BC-000116'].includes(productCode);
      const quoteRaw=isFirstPair
        ? '含运不含税，税点10%\n一万以下：\n30g的3.2元/个\n50g的3.5元/个\n丝印+0.1/色\n\n一万以上\n30g的3.0元/只\n50g的3.4元/只'
        : '含运不含税，税点10%\n一万以下：\n30g的3.1元/个\n50g的3.9元/个\n丝印+0.1/色\n\n一万以上\n30g的3.0元/只\n50g的3.8元/只';
      const input=record(quoteRaw,{productCode,specificationRaw}),before=JSON.stringify(input),data=e.pricing.pricingData(input);
      for(const field of ['ordinary','bare']){
        assert.equal(data[field].length,2,productCode+' '+field+' must contain exactly the two current-spec tiers');
        const text=joined(data[field]);
        assert.match(data[field][0].value,/一万以下/,productCode+' first quote must retain the lower-quantity condition');
        assert.match(data[field][0].value,new RegExp(regular.replace('.','\\.')+'元/个'));
        assert.match(data[field][1].value,/一万以上/,productCode+' second quote must retain the bulk-quantity condition');
        assert.match(data[field][1].value,new RegExp(bulk.replace('.','\\.')+'元/只'));
        for(const price of [otherRegular,otherBulk])assert.doesNotMatch(text,new RegExp(price.replace('.','\\.')+'元'),productCode+' must not borrow the sibling specification price');
        assert.doesNotMatch(text,/丝印|0\.1\/色/,'Finishing increments are not product price tiers');
      }
      assert.equal(e.view.bareAmount(joined(data.bare),'CNY'),null,'Both quantity tiers remain conditional');
      assertOriginal(e.pricing,input);
      assert.equal(JSON.stringify(input),before,'Price selection and rendering must not change the source record');
    }
  }finally{e.close();}
});

test('missing or explicitly multiple mass specifications preserve the source without selecting a price tier',async()=>{
  const e=await setup();try{
    const quoteRaw='含运不含税，税点10%\n一万以下：\n30g的3.2元/个\n50g的3.5元/个\n丝印+0.1/色\n\n一万以上\n30g的3.0元/只\n50g的3.4元/只';
    for(const specificationRaw of ['', '30g+50g','30g / 50g']){
      const input=record(quoteRaw,{specificationRaw}),before=JSON.stringify(input),data=e.pricing.pricingData(input);
      assert.deepEqual(values(data.ordinary),[],'An unresolved current specification cannot select ordinary prices');
      assert.deepEqual(values(data.bare),[],'An unresolved current specification cannot feed bare-price fallback');
      assertOriginal(e.pricing,input);
      assert.equal(JSON.stringify(input),before,'Unresolved source records must remain unchanged');
    }
  }finally{e.close();}
});

test('plate, machine, colour and labour charges never become product prices while mixed product quotes remain complete',async()=>{
  const e=await setup();try{
    for(const quoteRaw of [
      '打版费用1000元，大货抵扣',
      '打板费不少于1000元/500元每款',
      '开机费合计收1000元',
      '喷色+0.3元/个',
      '低于5000数量每款按500元/色',
      '有色加0.02元',
      '颜色版费300元/色',
      '板费350元/色',
      '人工费0.02元/片',
      '注塑色2000元',
      '4款做1.2万，收2000，做大货只抵扣1000元',
      '5000/10000个（后期看石油情况，涨幅0.2元左右）',
    ]){
      const input=record(quoteRaw),before=JSON.stringify(input),data=e.pricing.pricingData(input);
      assert.deepEqual(values(data.ordinary),[],quoteRaw+' is a processing or fixed fee, not a product unit price');
      assert.deepEqual(values(data.bare),[],quoteRaw+' cannot feed bare-price fallback');
      assertOriginal(e.pricing,input);
      assert.equal(JSON.stringify(input),before,'Fee exclusion must preserve the source record');
    }
    const productQuote=record('3000个单价1.38元，另外加上机费500元'),before=JSON.stringify(productQuote),data=e.pricing.pricingData(productQuote);
    assert.deepEqual(values(data.ordinary),[productQuote.quoteRaw],'A genuine product unit price retains its additional setup-fee condition');
    assert.deepEqual(values(data.bare),[productQuote.quoteRaw],'Fee exclusion must not erase a mixed product quotation');
    assert.equal(e.view.bareAmount(joined(data.bare),'CNY'),null);
    assertOriginal(e.pricing,productQuote);
    assert.equal(JSON.stringify(productQuote),before);
  }finally{e.close();}
});
