export const FAVORITES_KEY='yuanze2.0.1.demo.favorites.v1';
export const BRIEFS_KEY='yuanze2.0.1.demo.briefs.v1';
export function filterPosters(items,{query='',category='all',style='all',favorites=null}={}){
  const q=query.trim().toLocaleLowerCase();
  return items.filter(p=>(category==='all'||p.category===category)&&(style==='all'||p.style===style)&&(!favorites||favorites.includes(p.id))&&(!q||Object.values(p.title).join(' ').toLocaleLowerCase().includes(q)));
}
export function readFavorites(storage, validIds){
  try {const value=JSON.parse(storage.getItem(FAVORITES_KEY)||'[]'); return Array.isArray(value)?[...new Set(value.filter(id=>typeof id==='string'&&validIds.has(id)))]:[];}catch{return [];}
}
export function readBriefs(storage,validIds){
  try {const value=JSON.parse(storage.getItem(BRIEFS_KEY)||'[]');return Array.isArray(value)?value.filter(b=>b&&validIds.has(b.posterId)&&['style','shape'].includes(b.focus)&&typeof b.id==='string'&&typeof b.note==='string'&&b.note.length<=500&&typeof b.createdAt==='string'&&Number.isFinite(Date.parse(b.createdAt))).slice(0,30):[];}catch{return [];}
}
export function persist(storage,key,value){try{storage.setItem(key,JSON.stringify(value));return true;}catch{return false;}}
export function toggleFavorite(ids,id){return ids.includes(id)?ids.filter(x=>x!==id):[...ids,id];}
export function stepIndex(index,delta,length){return length?((index+delta)%length+length)%length:0;}

export function galleryItems(items,index){const count=Math.min(5,items.length);const start=-Math.floor((count-1)/2);return Array.from({length:count},(_,i)=>({poster:items[stepIndex(index,start+i,items.length)],offset:start+i}));}
