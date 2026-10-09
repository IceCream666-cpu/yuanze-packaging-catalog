import {t,registerTranslations} from './i18n.js';
registerTranslations({'通常用于':'Typically used for','MOQ · 起订量':'MOQ'});
const esc=value=>String(value??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
export function factRows(f,{client=false}={}){
 return [['材质',f.material],['规格',f.spec],['MOQ · 起订量',f.moq||''],['货期',f.lead||''],['通常用于',f.uses]].map(([label,value],i)=>`<div class="pd-fact${i===4?' pd-wide':''}"><dt>${esc(t(label))}</dt><dd data-i18n-skip>${esc(value)}</dd></div>`).join('');
}
