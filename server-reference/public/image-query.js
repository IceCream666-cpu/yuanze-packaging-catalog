// Camera photographs are normalised in the browser before the bounded search
// upload. The original file and its metadata are never sent or saved.
// At most two bounded record fetches; leave room for filters in the page URL.
export const IMAGE_QUERY_LIMIT = 120;
export const IMAGE_QUERY_COPY = {
  '请选择一张图片。':'Choose one image.',
  '图片不能为空，且不能超过 20 MB。':'Choose an image between 1 byte and 20 MB.',
  '暂支持 JPG、PNG、WebP，请转换图片格式后重试。':'Use a JPG, PNG or WebP image, or convert the file before searching.',
  'HEIC／HEIF 图片请先导出为 JPG，再进行搜图。':'Export HEIC / HEIF photographs as JPG before searching.',
  '无法读取图片，请重新导出为 JPG、PNG 或 WebP 后重试。':'Unable to read this image. Export it as JPG, PNG or WebP and try again.',
  '图片过小，请提供边长至少 32 像素的图片。':'Use an image with both sides at least 32 pixels long.',
  '图片尺寸过大，请缩小到 4000 万像素以内，单边不超过 16000 像素。':'Reduce the image to at most 40 megapixels and 16,000 pixels per side.',
  '当前浏览器无法处理图片，请更新浏览器后重试。':'This browser cannot prepare images. Update it and try again.',
  '框选范围过小，请重新框选。':'The selected area is too small. Select a larger area.',
  '图片准备失败，请重新选择图片。':'Unable to prepare this image. Choose it again.',
  '图片已自动缩小，可拖动框选目标包材。':'The image has been resized. Drag to select the target packaging.',
  'JPEG、PNG、WebP · 手机照片自动压缩 · 最大 20 MB':'JPEG, PNG, WebP · Camera photos resized automatically · Up to 20 MB',
  '不框选则使用整张图片；可用方向键调整选框，Shift＋方向键调整大小。':'Search the full image, or drag to select a target. Arrow keys move the selection; Shift + arrows resize it.',
  '已框选目标包材；可重新拖动调整范围。':'Target selected. Drag again to change the selection.',
  '使用整张图片':'Use full image',
  '框选中间包材':'Select centre target',
  '旋转 90°':'Rotate 90°',
  '图片预览，可用鼠标、手指或方向键框选目标包材':'Image preview: select packaging by mouse, touch or arrow keys',
  '正在准备图片…':'Preparing image…',
  '正在查找相似包材…':'Finding similar packaging…',
  '当前文字和筛选仍会限制搜图结果。':'Your current keyword and filters also apply to image results.',
  '清除文字和筛选':'Clear keyword and filters',
  '搜图请求超时，请稍后重试或框选目标包材。':'Image search timed out. Try again, or select the target packaging.',
  '搜图服务繁忙，请稍后重试。':'Image search is busy. Please try again shortly.',
  '未找到相似图片，请框选目标包材或调整拍摄角度后重试。':'No similar images found. Select the target or try another angle.',
};
export class ImageQueryError extends Error {}

function abortError() {return new DOMException('Image preparation cancelled','AbortError');}
function checkSignal(signal) {if(signal?.aborted)throw abortError();}
function readFile(file, method, signal) {
  checkSignal(signal);
  return new Promise((resolve,reject) => {
    const reader = new FileReader();
    const cleanup = () => signal?.removeEventListener('abort',abort);
    const abort = () => {reader.abort();cleanup();reject(abortError());};
    reader.onload = () => {cleanup();resolve(reader.result);};
    reader.onerror = () => {cleanup();reject(new ImageQueryError('无法读取图片，请重新导出为 JPG、PNG 或 WebP 后重试。'));};
    reader.onabort = () => {cleanup();reject(abortError());};
    signal?.addEventListener('abort',abort,{once:true});
    reader[method](file);
  });
}
async function decodeBrowserImage(url, signal) {
  checkSignal(signal);
  return new Promise((resolve,reject) => {
    const image = new Image();
    const cleanup = () => {signal?.removeEventListener('abort',abort);image.onload = image.onerror = null;};
    const abort = () => {cleanup();image.src = '';reject(abortError());};
    image.onload = () => {cleanup();resolve(image);};
    image.onerror = () => {cleanup();reject(new ImageQueryError('无法读取图片，请重新导出为 JPG、PNG 或 WebP 后重试。'));};
    signal?.addEventListener('abort',abort,{once:true});
    // Modern Image decoding applies EXIF orientation before drawing to canvas.
    image.src = url;
  });
}
export async function prepareImageQuery(file, {signal} = {}) {
  if (!file || typeof file.slice !== 'function') throw new ImageQueryError('请选择一张图片。');
  if (!file.size || file.size > 20*1024*1024) throw new ImageQueryError('图片不能为空，且不能超过 20 MB。');
  const bytes = new Uint8Array(await readFile(file.slice(0,32),'readAsArrayBuffer',signal));
  const text = (start,end) => String.fromCharCode(...bytes.slice(start,end));
  const jpeg = bytes[0] === 255 && bytes[1] === 216 && bytes[2] === 255;
  const png = bytes[0] === 137 && text(1,4) === 'PNG' && bytes[4] === 13 && bytes[5] === 10 && bytes[6] === 26 && bytes[7] === 10;
  const webp = text(0,4) === 'RIFF' && text(8,12) === 'WEBP';
  if (!jpeg && !png && !webp) {
    const heif = text(4,8) === 'ftyp' && /heic|heix|hevc|hevx|mif1|msf1/.test(text(8,32));
    throw new ImageQueryError(heif || /image\/(heic|heif)/i.test(file.type || '')
      ? 'HEIC／HEIF 图片请先导出为 JPG，再进行搜图。' : '暂支持 JPG、PNG、WebP，请转换图片格式后重试。');
  }
  const mime = jpeg ? 'image/jpeg' : png ? 'image/png' : 'image/webp';
  const data = await readFile(file,'readAsDataURL',signal);
  const image = await decodeBrowserImage(String(data).replace(/^data:[^;,]*/,`data:${mime}`),signal);
  checkSignal(signal);
  const w = image.naturalWidth, h = image.naturalHeight;
  if (!w || !h || Math.max(w,h)>16000 || w*h>40_000_000) throw new ImageQueryError('图片尺寸过大，请缩小到 4000 万像素以内，单边不超过 16000 像素。');
  if (Math.min(w,h)<32) throw new ImageQueryError('图片过小，请提供边长至少 32 像素的图片。');
  const scale = Math.min(1,1280/Math.max(w,h));
  const canvas = document.createElement('canvas');
  canvas.width = Math.max(1,Math.round(w*scale));canvas.height = Math.max(1,Math.round(h*scale));
  const context = canvas.getContext('2d');
  if (!context) throw new ImageQueryError('当前浏览器无法处理图片，请更新浏览器后重试。');
  context.fillStyle = '#fff';context.fillRect(0,0,canvas.width,canvas.height);
  context.drawImage(image,0,0,canvas.width,canvas.height);
  return canvas;
}
export function imageQueryDataURL(source, crop = null) {
  const rect = crop || {x:0,y:0,w:source.width,h:source.height};
  if (![rect.x,rect.y,rect.w,rect.h].every(Number.isFinite) || rect.x<0 || rect.y<0 || rect.w<16 || rect.h<16
    || rect.x+rect.w>source.width+.001 || rect.y+rect.h>source.height+.001) throw new ImageQueryError('框选范围过小，请重新框选。');
  const canvas = document.createElement('canvas');canvas.width = Math.round(rect.w);canvas.height = Math.round(rect.h);
  const context = canvas.getContext('2d');
  if (!context) throw new ImageQueryError('当前浏览器无法处理图片，请更新浏览器后重试。');
  context.fillStyle = '#fff';context.fillRect(0,0,canvas.width,canvas.height);
  context.drawImage(source,rect.x,rect.y,rect.w,rect.h,0,0,canvas.width,canvas.height);
  const image = canvas.toDataURL('image/jpeg',.9);
  if (!image.startsWith('data:image/jpeg;base64,') || image.length>8*1024*1024) throw new ImageQueryError('图片准备失败，请重新选择图片。');
  return image;
}
export function boundedImageMatches(matches, limit = IMAGE_QUERY_LIMIT) {
  if (!Array.isArray(matches)) return [];
  const seen = new Set(), result = [];let encodedLength=0;
  for (const item of matches) {
    if (!item || typeof item.record_id !== 'string' || !item.record_id || item.record_id.length>200
      || typeof item.image_path !== 'string' || !item.image_path || seen.has(item.record_id)) continue;
    let length;try{length=encodeURIComponent(item.record_id).length+10;}catch{continue;}
    if (encodedLength+length>5000)break;
    encodedLength+=length;seen.add(item.record_id);result.push(item);
    if (result.length>=limit) break;
  }
  return result;
}
export function rotateImageQuery(source) {
  const canvas=document.createElement('canvas');canvas.width=source.height;canvas.height=source.width;
  const context=canvas.getContext('2d');
  if(!context)throw new ImageQueryError('当前浏览器无法处理图片，请更新浏览器后重试。');
  context.fillStyle='#fff';context.fillRect(0,0,canvas.width,canvas.height);
  context.translate(canvas.width,0);context.rotate(Math.PI/2);context.drawImage(source,0,0);
  return canvas;
}
// Reusable mouse/touch/keyboard target selection for a single, prepared image.
export function bindImageQueryCrop(canvas, source, {onChange = () => {}} = {}) {
  let crop = null, anchor = null, activePointer = null;
  canvas.width = source.width;canvas.height = source.height;
  const draw = () => {
    const context = canvas.getContext('2d');if (!context)return;
    context.drawImage(source,0,0);
    if (crop) {
      context.fillStyle = 'rgba(15,45,41,.48)';context.fillRect(0,0,canvas.width,canvas.height);
      context.drawImage(source,crop.x,crop.y,crop.w,crop.h,crop.x,crop.y,crop.w,crop.h);
      context.strokeStyle = '#fff';context.lineWidth = Math.max(2,canvas.width/400);context.strokeRect(crop.x,crop.y,crop.w,crop.h);
    }
    onChange(crop);
  };
  const point = event => {const rect=canvas.getBoundingClientRect();return {x:Math.max(0,Math.min(canvas.width,(event.clientX-rect.left)*canvas.width/(rect.width||canvas.width))),y:Math.max(0,Math.min(canvas.height,(event.clientY-rect.top)*canvas.height/(rect.height||canvas.height)))};};
  const move = event => {if (!anchor || event.pointerId!==activePointer)return;event.preventDefault();const p=point(event);crop={x:Math.min(anchor.x,p.x),y:Math.min(anchor.y,p.y),w:Math.abs(anchor.x-p.x),h:Math.abs(anchor.y-p.y)};draw();};
  const down = event => {if (anchor||event.button>0||canvas.hasAttribute('inert'))return;event.preventDefault();anchor=point(event);activePointer=event.pointerId;canvas.setPointerCapture?.(event.pointerId);};
  const up = event => {if (!anchor || event.pointerId!==activePointer)return;move(event);anchor=null;activePointer=null;if (canvas.hasPointerCapture?.(event.pointerId))canvas.releasePointerCapture(event.pointerId);draw();};
  const cancel = () => {anchor=null;activePointer=null;crop=null;draw();};
  const centre = () => {crop={x:Math.round(source.width*.2),y:Math.round(source.height*.1),w:Math.round(source.width*.6),h:Math.round(source.height*.8)};draw();};
  const keydown = event => {
    if (canvas.hasAttribute('inert'))return;
    if (event.key==='Escape') {event.preventDefault();event.stopPropagation();cancel();return;}
    if (!['ArrowLeft','ArrowRight','ArrowUp','ArrowDown'].includes(event.key))return;
    event.preventDefault();if (!crop||crop.w<16||crop.h<16)centre();
    const dx=event.key==='ArrowLeft'?-1:event.key==='ArrowRight'?1:0,dy=event.key==='ArrowUp'?-1:event.key==='ArrowDown'?1:0,step=Math.max(1,Math.round(Math.min(source.width,source.height)/40));
    if (event.shiftKey) {crop.w=Math.max(16,Math.min(source.width-crop.x,crop.w+dx*step));crop.h=Math.max(16,Math.min(source.height-crop.y,crop.h+dy*step));}
    else {crop.x=Math.max(0,Math.min(source.width-crop.w,crop.x+dx*step));crop.y=Math.max(0,Math.min(source.height-crop.h,crop.y+dy*step));}
    draw();
  };
  const listeners = {pointerdown:down,pointermove:move,pointerup:up,pointercancel:cancel,keydown};
  for (const [name,fn] of Object.entries(listeners))canvas.addEventListener(name,fn);
  draw();
  return {get crop(){return crop;}, reset:cancel, centre, draw, dataURL:()=>imageQueryDataURL(source,crop), dispose:()=>{for(const [name,fn] of Object.entries(listeners))canvas.removeEventListener(name,fn);}};
}
