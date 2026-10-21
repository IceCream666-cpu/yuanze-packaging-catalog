import {shortestDelta, wrapIndex} from './carousel-model.js';

// A single, interruptible animation clock. Input updates never queue animations.
export function createCarouselMotion({initial = 0, length, paint, select, requestFrame, cancelFrame, now}) {
  const state = {position: initial, target: initial, velocity: 0, frame: 0, input: false, reduced: false};
  let lastTime = now();
  function schedule() { if (!state.frame) state.frame = requestFrame(tick); }
  function integrate(time) {
    // Analytic critically damped spring: preserve velocity when the target changes.
    const dt = Math.max(0, Math.min(.064, (time - lastTime) / 1000));
    lastTime = time;
    const omega = 22, distance = state.position - state.target;
    const b = state.velocity + omega * distance, decay = Math.exp(-omega * dt);
    state.position = state.target + (distance + b * dt) * decay;
    state.velocity = (state.velocity - omega * b * dt) * decay;
  }
  function tick(time) {
    state.frame = 0;
    if (state.input) { paint(state.position, true); return; }
    integrate(time);
    if (state.reduced || (Math.abs(state.position - state.target) < .0007 && Math.abs(state.velocity) < .008)) {
      state.position = state.target = wrapIndex(state.target, length);
      state.velocity = 0;
      paint(state.position, false);
    } else { paint(state.position, true); schedule(); }
  }
  function animate(target, commit = true) {
    target = Math.round(target);
    if (!state.input && state.frame) integrate(now());
    state.input = false; state.target = target; lastTime = now();
    if (commit && length) select(wrapIndex(target, length));
    if (state.reduced) {
      cancelFrame(state.frame); state.frame = 0;
      state.position = state.target = wrapIndex(target, length); state.velocity = 0;
      paint(state.position, false);
    } else schedule();
  }
  return {
    state,
    advance(delta) { animate((state.input ? Math.round(state.position) : state.target) + delta); },
    selectIndex(index) {
      // React's selection echo must not restart an animation already heading there.
      if (!state.input && wrapIndex(state.target, length) === index) return;
      animate(state.position + shortestDelta(index, state.position, length), false);
    },
    moveTo(position) {
      if (!state.input) { cancelFrame(state.frame); state.frame = 0; }
      state.input = true; state.position = position; state.target = Math.round(position); state.velocity = 0;
      schedule(); // Multiple wheel/pointer events are painted only once per display frame.
    },
    settle: animate,
    setReduced(value) {
      state.reduced = value;
      if (value && !state.input) animate(state.target, false);
    },
    dispose() { cancelFrame(state.frame); state.frame = 0; }
  };
}

export function horizontalWheel(event, pageWidth) {
  if (event.ctrlKey || event.metaKey) return 0; // Preserve pinch-to-zoom/browser gestures.
  const x = event.shiftKey && Math.abs(event.deltaX) < 2 ? event.deltaY : event.deltaX;
  const y = event.shiftKey ? 0 : event.deltaY;
  if (!Number.isFinite(x) || Math.abs(x) <= Math.abs(y) || Math.abs(x) < .01) return 0;
  return x * (event.deltaMode === 1 ? 16 : event.deltaMode === 2 ? pageWidth : 1);
}

export function wheelSnap(position, start) {
  const target = Math.round(position);
  // A deliberate short swipe advances one item; subpixel inertial tails do not.
  return target === Math.round(start) && Math.abs(position - start) >= .16
    ? target + Math.sign(position - start) : target;
}
