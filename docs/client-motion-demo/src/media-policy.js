// Width descriptors are real pixel widths, not the longest edge of a portrait.
export const FEATURED_SIZES = '(max-width: 600px) 290px, (max-width: 1100px) 330px, (max-width: 1533px) 30vw, 460px';
export const GRID_SIZES = '(max-width: 600px) 85vw, (max-width: 900px) 43vw, 28vw';
export const GALLERY_SIZES = '(max-width: 760px) 76vw, 55vw';
export function imageCandidates(candidates) {
  return candidates.filter(([url, width]) => url && Number.isFinite(width) && width > 0)
    .sort((a, b) => a[1] - b[1]).map(([url, width]) => `${url} ${width}w`).join(', ');
}
export function retrySource(src, attempt) {
  return attempt ? `${src}${src.includes('?') ? '&' : '?'}retry=${attempt}` : src;
}
