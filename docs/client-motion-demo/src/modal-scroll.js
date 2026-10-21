// Fixed body also prevents background touch scrolling in mobile Safari.
// Restore the exact inline styles and reading position when the dialog closes.
export function lockPageScroll(view = window) {
  const {document} = view;
  const x = view.scrollX, y = view.scrollY;
  const changes = [[document.documentElement, {overflow: 'hidden'}], [document.body, {
    position: 'fixed', top: `${-y}px`, left: `${-x}px`, width: '100%', overflow: 'hidden'
  }]];
  const previous = changes.map(([element, values]) => [element, Object.keys(values).map(key =>
    [key, element.style.getPropertyValue(key), element.style.getPropertyPriority(key)])]);
  changes.forEach(([element, values]) => Object.entries(values).forEach(([key, value]) => element.style.setProperty(key, value)));
  let restored = false;
  return () => {
    if (restored) return;
    restored = true;
    previous.forEach(([element, values]) => values.forEach(([key, value, priority]) => {
      if (value) element.style.setProperty(key, value, priority);
      else element.style.removeProperty(key);
    }));
    view.scrollTo(x, y);
  };
}
