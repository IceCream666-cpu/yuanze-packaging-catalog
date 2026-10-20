// Keep transient movement out of React state; only a completed gesture selects a poster.
export function gestureAxis(dx, dy) {
  if (Math.max(Math.abs(dx), Math.abs(dy)) < 8) return null;
  if (Math.abs(dx) > Math.abs(dy) * 1.25) return 'x';
  if (Math.abs(dy) > Math.abs(dx) * 1.25) return 'y';
  return null;
}

export function swipeDirection({dx, dy, duration, width, cancelled = false}) {
  if (cancelled || gestureAxis(dx, dy) !== 'x') return 0;
  const threshold = Math.min(96, Math.max(44, width * 0.12));
  const flick = Math.abs(dx) >= 28 && duration > 0 && duration <= 180 && Math.abs(dx) / duration > 0.45;
  return Math.abs(dx) >= threshold || flick ? (dx < 0 ? 1 : -1) : 0;
}

export function wheelDistance(event) {
  if (event.ctrlKey) return 0; // Trackpad pinch is browser zoom.
  const dx = event.deltaX || (event.shiftKey ? event.deltaY : 0);
  const dy = event.shiftKey ? 0 : event.deltaY;
  if (Math.abs(dx) <= Math.abs(dy) * 1.25) return 0;
  return dx * (event.deltaMode === 1 ? 16 : event.deltaMode === 2 ? 320 : 1);
}

export function bindGalleryGestures(element, onStep, env = window) {
  let pointer = null, frame = 0, pending = 0, suppressUntil = 0;
  const freshWheel = () => ({sum: 0, at: -Infinity, committed: false, committedAt: 0, direction: 0, peak: 0, floor: Infinity});
  let wheel = freshWheel(), wheelTimer = 0;
  const now = () => env.performance.now();
  const motion = env.matchMedia('(prefers-reduced-motion: reduce)');
  const paint = distance => {
    pending = motion.matches ? 0 : distance;
    if (!frame) frame = env.requestAnimationFrame(() => {
      frame = 0;
      element.style.setProperty('--gallery-drag', `${pending}px`);
    });
  };
  const settle = () => {
    if (frame) env.cancelAnimationFrame(frame);
    frame = 0;
    element.classList.remove('is-dragging');
    element.style.setProperty('--gallery-drag', '0px');
  };
  const resetPointer = () => {
    const previous = pointer;
    pointer = null;
    if (previous && element.hasPointerCapture?.(previous.id)) element.releasePointerCapture(previous.id);
    settle();
  };
  const resetWheel = () => {
    env.clearTimeout(wheelTimer);
    wheelTimer = 0;
    wheel = freshWheel();
    settle();
  };
  const down = event => {
    if (pointer) { suppressUntil = now() + 350; resetPointer(); return; }
    if (event.isPrimary === false || (event.pointerType === 'mouse' && event.button !== 0)) return;
    suppressUntil = 0;
    resetWheel();
    pointer = {id: event.pointerId, type: event.pointerType, x: event.clientX, y: event.clientY, at: now(), axis: null};
  };
  const move = event => {
    if (!pointer || pointer.id !== event.pointerId) return;
    const dx = event.clientX - pointer.x, dy = event.clientY - pointer.y;
    pointer.axis ||= gestureAxis(dx, dy);
    if (pointer.axis !== 'x') return;
    event.preventDefault();
    element.setPointerCapture?.(pointer.id);
    element.classList.add('is-dragging');
    const limit = element.clientWidth * 0.48;
    paint(Math.max(-limit, Math.min(limit, dx)));
  };
  const up = event => {
    if (!pointer || pointer.id !== event.pointerId) return;
    const dx = event.clientX - pointer.x, dy = event.clientY - pointer.y;
    const moved = Math.max(Math.abs(dx), Math.abs(dy)) >= 8;
    const direction = pointer.axis === 'y' ? 0 : swipeDirection({
      dx, dy, duration: now() - pointer.at, width: element.clientWidth
    });
    if (moved) suppressUntil = now() + 350;
    resetPointer();
    if (direction) onStep(direction);
  };
  const cancel = () => {
    if (pointer) suppressUntil = now() + 350;
    resetPointer();
    resetWheel();
  };
  const click = event => {
    if (event.detail !== 0 && now() < suppressUntil) {
      event.preventDefault();
      event.stopPropagation();
    }
  };
  const scroll = event => {
    // A mouse release outside the element before capture can otherwise leave
    // a pending click blocking all later trackpad input.
    if (pointer?.type === 'mouse' && !(event.buttons & 1)) resetPointer();
    if (pointer) return;
    const delta = wheelDistance(event);
    if (!delta) {
      if (event.ctrlKey || Math.abs(event.deltaY) >= 4) resetWheel();
      return;
    }
    event.preventDefault();
    const at = now(), magnitude = Math.abs(delta), direction = Math.sign(delta);
    // macOS can send tiny momentum events for a long time. They must not keep
    // renewing the lock or start another image transition after idle.
    if (magnitude < 0.5) return;
    if (at - wheel.at >= 180) resetWheel();
    if (wheel.committed) {
      const age = at - wheel.committedAt;
      const reversed = direction !== wheel.direction && magnitude >= 6 && age >= 80;
      const renewed = age >= 160 && wheel.floor <= wheel.peak * 0.6 &&
        magnitude >= 12 && magnitude >= wheel.floor * 1.8 + 4;
      // WheelEvent has no portable momentum phase. A deliberate reversal or
      // renewed acceleration after a decaying tail starts a fresh stroke.
      if (reversed || renewed) resetWheel();
    }
    wheel.at = at;
    env.clearTimeout(wheelTimer);
    wheelTimer = env.setTimeout(resetWheel, 180);
    if (wheel.committed) {
      wheel.peak = Math.max(wheel.peak, magnitude);
      wheel.floor = Math.min(wheel.floor, magnitude);
      return;
    }
    if (wheel.direction && direction !== wheel.direction) wheel.sum = 0;
    wheel.direction = direction;
    wheel.sum += delta;
    element.classList.add('is-dragging');
    paint(-Math.max(-60, Math.min(60, wheel.sum)));
    if (Math.abs(wheel.sum) >= 60) {
      wheel.committed = true;
      wheel.committedAt = at;
      wheel.peak = wheel.floor = magnitude;
      settle();
      onStep(wheel.sum > 0 ? 1 : -1);
    }
  };
  const lost = event => { if (pointer?.id === event.pointerId) cancel(); };
  element.addEventListener('pointerdown', down);
  element.addEventListener('pointermove', move, {passive: false});
  element.addEventListener('pointerup', up);
  element.addEventListener('pointercancel', cancel);
  element.addEventListener('lostpointercapture', lost);
  element.addEventListener('click', click, true);
  element.addEventListener('wheel', scroll, {passive: false});
  env.addEventListener('blur', cancel);
  return () => {
    resetWheel();
    resetPointer();
    element.removeEventListener('pointerdown', down);
    element.removeEventListener('pointermove', move);
    element.removeEventListener('pointerup', up);
    element.removeEventListener('pointercancel', cancel);
    element.removeEventListener('lostpointercapture', lost);
    element.removeEventListener('click', click, true);
    element.removeEventListener('wheel', scroll);
    env.removeEventListener('blur', cancel);
  };
}
