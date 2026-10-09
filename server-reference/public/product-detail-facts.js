import {t,registerTranslations} from './i18n.js';
registerTranslations({'通常用于':'Typically used for','MOQ · 起订量':'MOQ','资料标注用途':'Uses in product records','结构参考用途':'Uses to consider for this container','参考用途':'Reference uses','根据包材结构整理，具体适配请与业务员确认。':'Suggestions are based on the container structure. Confirm suitability with your sales representative.'});
const esc=value=>String(value??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
function explicitMaterials(value){
 // Historical material cells can contain printing fees. Only explicit material
 // names/codes belong in this fact; keep all other source text in the disclosure.
 const raw=typeof value==='string'?value.normalize('NFKC').toUpperCase():'',found=[];
 for(const match of raw.matchAll(/(?<![A-Z])(?:PETG|PET|HDPE|LDPE|PMMA|ABS|PVC|PP|PE|AS|PS)(?![A-Z])/g))found.push({at:match.index,label:match[0]});
 for(const match of raw.matchAll(/铝塑复合|不锈钢|无纺布|硅胶|橡胶|玻璃|塑料|塑胶/g))found.push({at:match.index,label:/塑料|塑胶/.test(match[0])?'塑料（待细分）':match[0]});
 // Single-character labels must be a material term or a container component,
 // rather than a printing note such as 贴纸0.1 or an aluminium-colour finish.
 for(const match of raw.matchAll(/(?:^|[\s,，、/+;；:：])(铝|纸)(?=$|[\s,，、/+;；]|[瓶罐盖箔盒袋板])/g))found.push({at:match.index,label:match[1]});
 return [...new Set(found.sort((a,b)=>a.at-b.at).map(item=>item.label))];
}
export function materialFact(record={}){
 const supplied=Array.isArray(record.materials)?record.materials.filter(value=>typeof value==='string'&&value.trim()).map(value=>value.trim()):[];
 if(supplied.length)return supplied.join(' / ');
 const raw=explicitMaterials(record.materialRaw);
 if(raw.length)return raw.join(' / ');
 const details=Array.isArray(record.productDetails)?record.productDetails:[];
 const materials=details.filter(detail=>/^(?:材质|材料)$/.test(String(detail?.label||'').replace(/[\s：:／/（）()·]/g,'')))
  .flatMap(detail=>explicitMaterials(detail.value));
 return [...new Set(materials)].join(' / ');
}
export function factRows(f,{client=false}={}){
 const rows=[['材质',f.material],['规格',f.spec],...(!client?[['MOQ · 起订量',f.moq||''],['货期',f.lead||'']]:[]),['资料标注用途',f.uses]];
 return rows.map(([label,value])=>`<div class="pd-fact${label==='资料标注用途'?' pd-wide':''}"><dt>${esc(t(label))}</dt><dd data-i18n-skip>${esc(value)}</dd></div>`).join('')+(f.referenceUses?`<div class="pd-fact pd-wide pd-reference-use"><dt>${esc(t('结构参考用途'))}</dt><dd data-i18n-skip>${esc(f.referenceUses)}</dd><p class="pd-use-note">${esc(t('根据包材结构整理，具体适配请与业务员确认。'))}</p></div>`:'');
}
