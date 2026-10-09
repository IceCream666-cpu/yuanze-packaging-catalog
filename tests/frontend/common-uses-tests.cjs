const assert=require('node:assert/strict');
const path=require('node:path');
const {test}=require('node:test');
const {execFileSync}=require('node:child_process');
const {JSDOM}=require('jsdom');
const {evaluateBrowserModule}=require('./module-loader.cjs');
const root=path.resolve(__dirname,'../..');
const source=path.join(root,'server-reference/public');
async function modules(){
  const dom=new JSDOM('<!doctype html>',{url:'https://catalog.test/',runScripts:'outside-only'});
  const taxonomy=(await evaluateBrowserModule(dom,path.join(source,'catalog-taxonomy.js'))).namespace;
  const query=(await evaluateBrowserModule(dom,path.join(source,'catalog-query.js'))).namespace;
  return {dom,taxonomy,query};
}
const plain=value=>JSON.parse(JSON.stringify(value));

test('one tube has several reference uses without changing its source or body areas',async()=>{
  const {dom,taxonomy:t}=await modules();try{
    const record={kind:'package',category:'软管',name:'A001',uses:['洁面'],bodyAreas:['face']};
    const before=JSON.stringify(record);
    assert.deepEqual(plain(t.recordReferenceUses(record)),['护手霜','身体乳']);
    assert.deepEqual(plain(t.recordSearchUses(record)),['洁面','护手霜','身体乳']);
    assert.deepEqual(plain(t.recordUses(record)),['洁面']);
    assert.deepEqual(plain(t.recordBodySections(record)),['face']);
    assert.equal(JSON.stringify(record),before);
  }finally{dom.window.close();}
});

test('manual, disabled and automatic reference modes remain distinguishable',async()=>{
  const {dom,taxonomy:t}=await modules();try{
    const base={bottleType:'真空瓶',uses:['精华液']};
    assert.equal(t.referenceUseInfo(base).mode,'automatic');
    assert.deepEqual(plain(t.recordReferenceUses(base)),['乳液','面霜']);
    assert.deepEqual(plain(t.recordReferenceUses({...base,referenceUses:[]})),[]);
    assert.equal(t.referenceUseInfo({...base,referenceUses:[]}).mode,'manual');
    assert.deepEqual(plain(t.recordReferenceUses({...base,referenceUses:['精华液','护手霜','护手霜']})),['护手霜']);
    for(const invalid of [null,{},true,'护手霜'])assert.deepEqual(plain(t.recordReferenceUses({...base,referenceUses:invalid})),[]);
    assert.ok(t.usageOptions([{referenceUses:['管理员参考用途']}]).includes('管理员参考用途'));
  }finally{dom.window.close();}
});

test('special eye and lip tube evidence suppresses generic references without reading shared prose',async()=>{
  const {dom,taxonomy:t,query:q}=await modules();try{
    const base={kind:'package',bottleType:'软管',uses:[]};
    for(const evidence of [
      {name:'ø19mm锌合金眼霜管'},{name:'圆形陶瓷头唇部护理管'},
      {rawCells:{用途:'眼霜'}},{rawCells:{original:{产品用途:{value:'lip balm'}}}},
      {productDetails:[{label:'用途',value:'牙膏',sourceField:'uses'}]},
      {name:'不适用于眼霜，但可用于唇膏'},
    ])assert.deepEqual(plain(t.recordReferenceUses({...base,...evidence})),[],JSON.stringify(evidence));
    for(const evidence of [
      {description:'眼霜'},{source:{workbook:'眼霜图册.pdf'}},{images:[{caption:'眼霜'}]},
      {rawCells:{A:'眼霜'}},{rawCells:{用途:{value:'眼霜',scope:'page'}}},
      {productDetails:[{label:'用途',value:'眼霜',sourceField:'remarksRaw'}]},
      {name:'图册整页 / 眼霜'},{name:'不适用于眼霜、唇膏'},
    ])assert.deepEqual(plain(t.recordReferenceUses({...base,...evidence})),['洁面','护手霜','身体乳'],JSON.stringify(evidence));
    assert.deepEqual(plain(t.recordReferenceUses({...base,name:'眼霜管',referenceUses:['身体乳']})),['身体乳']);
    const index=q.prepareRecords({records:[{...base,id:'tube-1',name:'洗面奶软管'}]});
    assert.ok(index.records[0]._uses.includes('洁面'));
    assert.ok(!index.records[0]._referenceUses.includes('洁面'));
  }finally{dom.window.close();}
});

test('shared pages, accessories, conflicting structures and generic shapes cannot invent applications',async()=>{
  const {dom,taxonomy:t}=await modules();try{
    for(const record of [
      {kind:'source_page',category:'软管',referenceUses:['洁面']},
      {category:'泵头与喷头',bottleType:'真空瓶'},
      {category:'套装',bottleType:'乳液瓶'},
      {category:'罐',bottleType:'滴管瓶'},
      {category:'瓶',bottleType:'软管'},
      {category:'软管',bottleType:'滚珠软管'},
      {category:'滴管'},
      {bottleType:'圆瓶'},
      {bottleType:'滴管瓶/膏霜罐'},
      {name:'软管',description:'真空瓶',images:[{caption:'泡沫瓶'}]},
      {bottleType:'软管',uses:['唇彩']},
    ])assert.deepEqual(plain(t.recordReferenceUses(record)),[],JSON.stringify(record));
    assert.deepEqual(plain(t.recordReferenceUses({category:'待细分',bottleType:'精油滴管瓶'})),['精华液','精油']);
  }finally{dom.window.close();}
});

test('novice synonyms and either usage tag find the same product without duplicating results',async()=>{
  const {dom,query:q}=await modules();try{
    const records=[
      {id:'tube',productCode:'YZ-BC-990001',kind:'package',name:'通用款A',category:'软管',uses:[],capacityMl:50},
      {id:'documented',productCode:'YZ-BC-990002',kind:'package',name:'洗面奶包材',uses:['洁面'],capacityMl:50},
      {id:'unknown',productCode:'YZ-BC-990003',kind:'package',name:'通用款B',bottleType:'方瓶',uses:[]},
    ];
    const index=q.prepareRecords({records},[]);
    assert.deepEqual(plain(q.matchRecords(index,{q:'洗面奶'}).map(r=>r.id)),['documented','tube']);
    for(const use of ['洁面','护手霜','身体乳'])assert.ok(q.matchRecords(index,{filters:{use:[use]}}).some(r=>r.id==='tube'));
    const result=q.queryPage(index,{filters:{use:['护手霜','身体乳']}});
    assert.equal(result.total,1);assert.equal(result.matchingRecords,1);
    assert.equal(q.matchRecords(index,{filters:{use:['护手霜'],capacity:[30]}}).length,0);
    assert.equal(q.matchRecords(index,{q:'hand cream'})[0].id,'tube');
    assert.deepEqual(records[0].uses,[]);
  }finally{dom.window.close();}
});

test('documented applications rank before structure references in usage-filtered results',async()=>{
  const {dom,query:q}=await modules();try{
    const index=q.prepareRecords({records:[
      {id:'reference',kind:'package',name:'先录入款',category:'软管'},
      {id:'confirmed',kind:'package',name:'后录入款',uses:['护手霜']},
    ]},[]);
    assert.deepEqual(plain(q.matchRecords(index,{filters:{use:['护手霜']}}).map(r=>r.id)),['confirmed','reference']);
    // Picture-search relevance keeps its own ranking when both filters apply.
    assert.deepEqual(plain(q.matchRecords(index,{filters:{use:['护手霜']},imageIds:['reference','confirmed']}).map(r=>r.id)),['reference','confirmed']);
  }finally{dom.window.close();}
});

test('browser and Python use exactly the same structure and override contracts',async()=>{
  const {dom,taxonomy:t}=await modules();try{
    const categories=['','待细分','瓶','瓶类','软管','罐','罐与广口盒','滴管','泵头','套装','other',' TUBES '];
    const types=['','软管','精油滴管瓶','精华滴管瓶','滴管瓶','真空瓶','可替换真空瓶','乳液瓶','泡沫瓶','喷雾瓶','广口膏霜罐','滚珠瓶','香水瓶','圆瓶','压泵瓶','滴管/罐',' ＡＩＲＬＥＳＳ '];
    const cases=categories.flatMap(category=>types.flatMap(bottleType=>[
      {category,bottleType},{category,bottleType,uses:['洁面']},{category,bottleType,uses:['唇彩']},
      {category,bottleType,referenceUses:[]},{category,bottleType,referenceUses:['洁面','护手霜','护手霜'],uses:['洁面']},
    ]));
    cases.push({kind:'source_page',bottleType:'软管'},null,{}, {referenceUses:null,bottleType:'真空瓶'});
    for(const evidence of [
      {name:'ø19mm锌合金眼霜管'},{name:'圆形陶瓷头唇部护理管'},{name:'Tube for eye cream'},
      {uses:['专用眼霜管待核对']},{name:'不适用于眼霜，但可用于唇膏'},
      {name:'不适用于眼霜、唇膏'},{name:'not suitable for eye cream, lip balm'},
      {name:'眼霜（不适用）'},{name:'图册整页 / 眼霜'},{description:'眼霜'},
      {rawCells:{用途:'眼霜'}},{rawCells:{original:{产品用途:{value:'lip balm'}}}},
      {rawCells:{用途:{value:'眼霜',scope:'page'}}},{rawCells:{A:'眼霜'}},
      {productDetails:[{label:'用途',value:'牙膏',sourceField:'uses'}]},
      {productDetails:[{label:'用途',value:'眼霜',sourceField:'remarksRaw'}]},
    ])cases.push({bottleType:'软管',...evidence});
    const python=path.join(root,'.venv/bin/python');
    const script="import sys,json;sys.path.insert(0,'server-reference');from usage_references import reference_uses;print(json.dumps([reference_uses(r) for r in json.load(sys.stdin)],ensure_ascii=False))";
    const expected=JSON.parse(execFileSync(python,['-c',script],{cwd:root,input:JSON.stringify(cases),encoding:'utf8'}));
    assert.deepEqual(cases.map(record=>plain(t.recordReferenceUses(record))),expected);
  }finally{dom.window.close();}
});
