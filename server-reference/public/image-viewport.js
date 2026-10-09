// A reviewed viewport changes presentation, never the source bitmap. Coordinates
// are normalized to the full source page, not to a resized thumbnail.
export function validImageCrop(image) {
  const c = image?.displayCrop;
  if (!c || !['x','y','width','height','sourceWidth','sourceHeight'].every(k => Number.isFinite(c[k]))) return null;
  if (c.x < 0 || c.y < 0 || c.width <= 0 || c.height <= 0 || c.sourceWidth <= 0 || c.sourceHeight <= 0
    || c.x + c.width > 1.000001 || c.y + c.height > 1.000001) return null;
  const aspect=c.width*c.sourceWidth/(c.height*c.sourceHeight);
  if (!Number.isFinite(aspect) || aspect<=0 || !Number.isFinite(100/c.width) || !Number.isFinite(100*c.y/c.height))return null;
  return c;
}

export function imageViewKey(image, path) {
  const crop = validImageCrop(image);
  return path + (crop ? '#view=' + [crop.x,crop.y,crop.width,crop.height,crop.sourceWidth,crop.sourceHeight].join(',') : '');
}

// All attribute content is escaped by the caller. The nested img keeps native
// loading, alt text and download behavior; CSS clips only the reviewed region.
export function renderImageViewport(image, imgMarkup) {
  const c = validImageCrop(image);
  if (!c) return imgMarkup;
  const style = `--crop-aspect:${c.width*c.sourceWidth/(c.height*c.sourceHeight)};--crop-width:${100/c.width}%;--crop-left:${-100*c.x/c.width}%;--crop-top:${-100*c.y/c.height}%`;
  return `<span class="image-viewport" style="${style}">${imgMarkup}</span>`;
}
