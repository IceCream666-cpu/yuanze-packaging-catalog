const PRODUCT_ROLES=new Set(['product','supplier','inquiry']);
const SCOPES=new Set(['single_product','same_style_variants','source_page','unresolved']);
const imagesOf=record=>Array.isArray(record?.images)?record.images:[];
const pathKey=value=>String(typeof value==='string'?value:value?.path||value?.file||'').replace(/\\/g,'/').replace(/^\/+/, '');

export function imageScope(image){
  if(SCOPES.has(image?.imageScope))return image.imageScope;
  if(image?.mapping==='pdf-page-preview')return 'source_page';
  // Older/unreviewed pictures must never be silently promoted by role alone.
  return 'unresolved';
}
export function imageScopeLabel(image,record){
  if(record?.kind==='source_page')return '原页／图片线索';
  if(image?.uncertain)return '原页／待核对 · 归属未确认';
  return {single_product:'单品图',same_style_variants:'同款系列参考·规格外观待核对',source_page:'原页／共用参考图',unresolved:'原页／待核对'}[imageScope(image)];
}
export function isProductImage(image){
  return !!image&&!image.missing&&!image.uncertain&&PRODUCT_ROLES.has(image.role)&&['single_product','same_style_variants'].includes(imageScope(image));
}
export function primaryImage(record){
  const images=imagesOf(record);
  if(record?.kind==='package')return images.find(i=>isProductImage(i)&&imageScope(i)==='single_product')||images.find(isProductImage);
  return images.find(i=>!i.missing&&!i.uncertain&&PRODUCT_ROLES.has(i.role))||images.find(i=>!i.missing);
}
export function matchedImage(record,path){
  if(!pathKey(path))return undefined;
  return imagesOf(record).find(i=>pathKey(i)===pathKey(path)&&!i.missing&&(record?.kind==='package'?isProductImage(i):!i.uncertain));
}
export function displayImage(record,matchedPath){return matchedImage(record,matchedPath)||primaryImage(record);}
export function productImageStatus(record){
  const image=primaryImage(record);
  return record?.kind==='package'&&image?imageScope(image):'unresolved';
}
