export function wrapIndex(index, length) {
  return length > 0 ? ((index % length) + length) % length : 0;
}

// Keep halfway jumps deterministic, including collections of two posters.
export function shortestDelta(index, current, length) {
  if (length <= 1) return 0;
  const delta = wrapIndex(index - current, length);
  return delta > length / 2 ? delta - length : delta;
}

export function visibleItems(items, position, limit = 7) {
  return items.map((poster, index) => ({poster, index, offset: shortestDelta(index, position, items.length)}))
    .sort((a, b) => Math.abs(a.offset) - Math.abs(b.offset))
    .slice(0, Math.max(0, limit))
    .sort((a, b) => a.offset - b.offset);
}

export function snapTarget(position, velocity, length) {
  if (length <= 1) return 0;
  return Math.round(position + Math.max(-0.85, Math.min(0.85, velocity * 150)));
}
