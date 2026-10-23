const clamp = (value, min, max) => Math.max(min, Math.min(max, value));

// A shallow 3D bowl: the selected product sits nearest and lowest, while its
// neighbours rise around the same arc and recede into the stage perspective.
// Geometry is independent of the input clock, so dragging and spring settling
// travel through precisely the same path without creating extra animations.
export function productArc(offset, width, length) {
  const distance = Math.abs(offset);
  const angle = clamp(offset * .65, -1.8, 1.8);
  const recession = 1 - Math.cos(angle);
  const radius = clamp(width * .6, 220, 580);
  const depth = clamp(width * .9, 400, 760);
  const rise = clamp(width * .28, 100, 210);
  // Fade before the circular seam changes sides, including short collections.
  const edge = Math.min(2.7, length / 2);
  const fade = length <= 1 ? 1 : clamp((edge - distance) / .6, 0, 1);
  const opacity = length === 2 ? clamp(1 - distance * 1.25, 0, 1)
    : (1 - Math.min(distance, 2.7) * .11) * fade;
  return {
    x: Math.sin(angle) * radius,
    y: -recession * rise,
    z: -recession * depth,
    rotateY: clamp(-angle * 18, -26, 26),
    scale: 1 - recession * .22,
    opacity,
  };
}
