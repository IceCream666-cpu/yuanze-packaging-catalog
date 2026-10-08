import fs from 'node:fs';
import assert from 'node:assert/strict';
import {test} from 'node:test';
const file=new URL('../../server-reference/public/catalog-taxonomy.js',import.meta.url);
const mod=await import('data:text/javascript;base64,'+fs.readFileSync(file).toString('base64'));
const {recordUses,recordSections,recordBodySections,usageOptions}=mod;
const has=(record,value)=>recordUses(record).includes(value);

test('specific cosmetic and body product names classify with clear regions',()=>{
  for(const name of ['500ml洗手液瓶','液体沐浴露','800mlPET洗发水','护手霜','香水瓶']) assert.deepEqual(recordSections({name}),['body-head']);
  for(const name of ['面霜','眼精华滚珠瓶','粉底液瓶','唇釉口红管','面膜袋']) assert.deepEqual(recordSections({name}),['face']);
  assert.ok(has({name:'搭泵头洗护产品（洗发露/沐浴露/护发素等）'},'护发素'));
  assert.ok(has({name:'Retinol Serum 视黄醇精华液'},'精华液'));
});
test('generic forms and broad applications do not invent face/body scope',()=>{
  for(const name of ['精华液','乳液分装瓶','膏霜罐','精油滴管瓶','防晒霜','洗护瓶系列','膜布','PET圆瓶']) assert.deepEqual(recordSections({name}),[],name);
  assert.deepEqual(recordUses({name:'PET圆瓶'}),[]);
  assert.ok(!has({name:'漱口水瓶/可配乳液泵头'},'乳液'));
});
test('multiple explicit regions and maintained values are preserved',()=>{
  const r={name:'面部及身体精华液',uses:['水剂','院线专用','水剂']};const before=JSON.stringify(r);
  assert.deepEqual(recordSections(r),['face','body-head']);
  assert.deepEqual(recordUses(r),['水剂','院线专用','精华液']);
  assert.equal(JSON.stringify(r),before);
  assert.deepEqual(recordSections({name:'眼霜/护手霜'}),['face','body-head']);
});
test('negative scopes and exclusions do not create false applications',()=>{
  const r={name:'不适用于洗手液/沐浴露；用于面部精华液'};
  assert.deepEqual(recordUses(r),['精华液']);assert.deepEqual(recordSections(r),['face']);
  assert.deepEqual(recordSections({name:'用于身体而非面部'}),['body-head']);
  assert.deepEqual(recordSections({name:'面部（不适用）；手部使用'}),['body-head']);
  assert.deepEqual(recordSections({name:'not for face; body lotion'}),['body-head']);
  assert.deepEqual(recordSections({name:'不用于面部；洗手液瓶'}),['body-head']);
  assert.deepEqual(recordUses({name:'不适用洗手液，沐浴露'}),[]);
  assert.deepEqual(recordUses({name:'非洗手液/沐浴露'}),[]);
  assert.deepEqual(recordSections({name:'not for face, hands'}),[]);
  assert.deepEqual(recordSections({name:'不适用于面部，身体使用'}),['body-head']);
  assert.deepEqual(recordSections({name:'Not only face but also body serum'}),['face','body-head']);
  assert.ok(has({name:'洗手液（不含香精）'},'洗手液'));
});
test('shared catalogue pages and adjacent OCR cannot contaminate individual model',()=>{
  const r={name:'YT938(930)-1#',remarksRaw:'洗手液 沐浴露 面霜 精华液',description:'面部护理',source:{workbook:'洁面乳与洗发水图册.pdf'},
    extraRaw:'本页全部用途：洗发水、面霜',images:[{caption:'洗手液',imageScope:'source_page'}],
    rawCells:{C:'洗手液',original:{source_ocr_excerpt:'沐浴露 面霜'},fieldEvidence:{uses:{text:'面霜',bbox:[0,0,1,1]}}}};
  assert.deepEqual(recordUses(r),[]);assert.deepEqual(recordSections(r),[]);
  assert.deepEqual(recordUses({kind:'source_page',name:'洗手液图册整页'}),[]);
  assert.deepEqual(recordUses({name:'图册整页 / 洗手液与面霜'}),[]);
});
test('only explicitly named per-product usage columns are accepted',()=>{
  const r={name:'A01',rawCells:{用途:'洗手液',original:{适用部位:{value:'面部',cell:'G12'},用途:{value:'精华液',cell:'H12'}}}};
  assert.ok(has(r,'洗手液'));assert.ok(has(r,'精华液'));assert.deepEqual(recordSections(r),['face','body-head']);
  assert.deepEqual(recordUses({name:'A01',rawCells:{用途:{value:'洗手液',scope:'page'}}}),[]);
  assert.deepEqual(recordUses({name:'A01',productDetails:[{label:'用途',value:'面霜',sourceField:'remarksRaw'}]}),[]);
  assert.deepEqual(recordSections({name:'A01',productDetails:[{label:'适用部位',value:'身体',sourceField:''}]}),['body-head']);
});
test('word boundaries and positive repeated calls stay deterministic',()=>{
  assert.deepEqual(recordUses({name:'surface conditioner apparatus'}),[]);
  const r={name:'Hand Cream 护手霜'};
  for(let i=0;i<5;i++){assert.deepEqual(recordUses(r),['护手霜']);assert.deepEqual(recordSections(r),['body-head']);}
});
test('usage options contain common categories plus maintained custom values',()=>{
  const a=usageOptions([{name:'A01',uses:['院线专用','水剂']},{kind:'source_page',uses:['整页噪声']},{archived:true,uses:['已归档独有值']}]);
  for(const s of ['洗手液','精华液','沐浴露','院线专用','水剂'])assert.ok(a.includes(s));
  assert.equal(new Set(a).size,a.length);assert.ok(!a.includes('整页噪声'));assert.ok(!a.includes('已归档独有值'));
});
test('invalid inputs safely return empty record classifications',()=>{
  for(const value of [null,undefined,3,'洗手液']){assert.deepEqual(recordUses(value),[]);assert.deepEqual(recordSections(value),[]);}
  assert.ok(usageOptions(null).includes('精华液'));
});

test('three-area navigation separates body care from hair and scalp care',()=>{
  for(const name of ['500ml洗手液瓶','沐浴露','护手霜','身体乳','body wash','foot cream','hair removal cream']) {
    assert.deepEqual(recordBodySections({name}),['body'],name);
    assert.deepEqual(recordSections({name}),['body-head'],name);
  }
  for(const name of ['洗发水','护发素','发膜','头皮精华','头部护理','hair serum','scalp care','hair conditioner']) {
    assert.deepEqual(recordBodySections({name}),['head'],name);
    assert.deepEqual(recordSections({name}),['body-head'],name);
  }
  for(const name of ['面霜','面部精华','眼部精华','facial serum']) assert.deepEqual(recordBodySections({name}),['face'],name);
});

test('three-area navigation leaves generic products and packaging head names unassigned',()=>{
  for(const name of ['精华液','serum','乳液','精油','防晒','洗护','PET圆瓶','pump head','spray head']) {
    assert.deepEqual(recordBodySections({name}),[],name);
  }
});

test('explicit body areas are validated, deduplicated and combined without mutating the record',()=>{
  const record={name:'沐浴露',bodyAreas:['head','face','head','body','unknown',null,{},'FACE']};
  const before=JSON.stringify(record);
  assert.deepEqual(recordBodySections(record),['face','body','head']);
  assert.equal(JSON.stringify(record),before);
  assert.deepEqual(recordSections(record),['body-head']);
  assert.deepEqual(recordBodySections({bodyAreas:['head','face']}),['face','head']);
  for(const bodyAreas of ['face',null,{},true,['unknown',42]]) assert.deepEqual(recordBodySections({bodyAreas}),[]);
  assert.deepEqual(recordBodySections({uses:['面部精华','沐浴露','头皮精华']}),['face','body','head']);
});

test('three-area inference retains negation boundaries and independently maintained areas',()=>{
  assert.deepEqual(recordBodySections({name:'不适用洗发水、沐浴露；用于面部精华'}),['face']);
  assert.deepEqual(recordBodySections({name:'not for face, scalp; body lotion'}),['body']);
  assert.deepEqual(recordBodySections({name:'头部（不适用）；身体专用'}),['body']);
  assert.deepEqual(recordBodySections({name:'用于身体而非头部'}),['body']);
  assert.deepEqual(recordBodySections({name:'Not only face but also scalp serum'}),['face','head']);
  assert.deepEqual(recordBodySections({name:'不用于面部；沐浴露',bodyAreas:['face']}),['face','body']);
});

test('three-area inference accepts scoped usage fields while excluding source OCR and captions',()=>{
  const record={name:'PET圆瓶',remarksRaw:'面部精华',description:'身体护理',source:{workbook:'洗发水图册.pdf'},
    extraRaw:'头皮护理',images:[{caption:'洗发水',imageScope:'source_page'}],
    rawCells:{C:'沐浴露',original:{source_ocr_excerpt:'面部精华'},fieldEvidence:{uses:{text:'头皮精华'}}}};
  const before=JSON.stringify(record);
  assert.deepEqual(recordBodySections(record),[]);
  assert.deepEqual(recordBodySections({...record,bodyAreas:['head']}),['head']);
  assert.equal(JSON.stringify(record),before);
  assert.deepEqual(recordBodySections({rawCells:{用途:'沐浴露',original:{适用部位:{value:'头皮',cell:'G12'}}},
    productDetails:[{label:'用途',value:'面霜',sourceField:'uses'}]}),['face','body','head']);
  assert.deepEqual(recordBodySections({rawCells:{用途:{value:'沐浴露',scope:'page'}},
    productDetails:[{label:'用途',value:'洗发水',sourceField:'remarksRaw'}]}),[]);
  assert.deepEqual(recordBodySections({name:'图册整页 / 洗发水和面霜'}),[]);
  for(const value of [null,undefined,3,'洗发水',{kind:'source_page',name:'洗发水',bodyAreas:['face','body','head']}]) {
    assert.deepEqual(recordBodySections(value),[]);
  }
});
