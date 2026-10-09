// Persistent private query worker. Reuses the browser's exact taxonomy and search rules.
import readline from 'node:readline';
import {prepareRecords,queryPage,matchRecords,catalogFacets,normalizeSearch,codeKey} from './public/catalog-query.js';
import {reviewedProductGroups} from './public/product-group-data.js';
let index=null,facets=null;
const input=readline.createInterface({input:process.stdin,crlfDelay:Infinity});
for await (const line of input) {
  try {
    const job=JSON.parse(line);
    if(job.action==='load') {
      index=prepareRecords(job.catalog,reviewedProductGroups);facets=catalogFacets(index.records);
      process.stdout.write(JSON.stringify({ok:true})+'\n');continue;
    }
    if(!index)throw Error('Not initialized');
    let result;
    if(job.action==='query')result={...queryPage(index,job.options),facets};
    else if(job.action==='records') {
      const requested=job.ids.map(value=>index.recordIdIndex.get(normalizeSearch(value))?.id||index.productCodeIndex.get(codeKey(value))?.id||value);const ids=new Set(requested.flatMap(id=>index.productGroupIndex.get(id)?.records.map(r=>r.id)||[id]));
      result={records:index.records.filter(r=>ids.has(r.id)).map(r=>Object.fromEntries(Object.entries(r).filter(([key])=>!key.startsWith('_'))))};
    } else if(job.action==='export') {
      const fields=['id','productCode','name','kind','materialRaw','specificationRaw','supplierRaw','quoteHeader','quoteRaw','moqRaw','leadTimeRaw','customQuoteRaw','customMoqRaw','customLeadTimeRaw','sampleFeeRaw','moldFeeRaw','source','sourceNote','uses','referenceUses'];
      result={records:matchRecords(index,job.options).map(r=>Object.fromEntries(fields.map(k=>[k,k==='uses'?r._uses:k==='referenceUses'?r._referenceUses:r[k]])))};
    } else throw Error('Invalid operation');
    process.stdout.write(JSON.stringify(result)+'\n');
  } catch {process.stdout.write(JSON.stringify({error:'catalog_query_failed'})+'\n');}
}
