import test from 'node:test';
import assert from 'node:assert/strict';
import {bindGalleryGestures, gestureAxis, swipeDirection, wheelDistance} from '../src/gallery-gestures.js';

function fixture(reduced = false) {
  let time = 0, next = 1;
  const frames = new Map(), timers = new Map(), classes = new Set(), styles = new Map(), captures = new Set();
  const element = Object.assign(new EventTarget(), {
    clientWidth: 400,
    style: {setProperty: (k, v) => styles.set(k, v)},
    classList: {add: k => classes.add(k), remove: k => classes.delete(k)},
    setPointerCapture: id => captures.add(id),
    hasPointerCapture: id => captures.has(id),
    releasePointerCapture: id => captures.delete(id)
  });
  const env = Object.assign(new EventTarget(), {
    performance: {now: () => time}, matchMedia: () => ({matches: reduced}),
    requestAnimationFrame: fn => {const id = next++; frames.set(id, fn); return id;},
    cancelAnimationFrame: id => frames.delete(id),
    setTimeout: fn => {const id = next++; timers.set(id, fn); return id;},
    clearTimeout: id => timers.delete(id)
  });
  const steps = [], dispose = bindGalleryGestures(element, d => steps.push(d), env);
  function emit(type, data = {}) {
    const event = Object.assign(new Event(type, {cancelable: true}), {
      pointerId: 1, isPrimary: true, pointerType: 'mouse', button: 0,
      clientX: 200, clientY: 100, deltaX: 0, deltaY: 0, deltaMode: 0, detail: 1, ...data
    });
    element.dispatchEvent(event);
    return event;
  }
  return {emit, steps, dispose, styles, classes, captures, frames, timers,
    advance: ms => {time += ms;},
    frame: () => {const callbacks = [...frames.values()];frames.clear();callbacks.forEach(fn => fn());},
    idle: () => {const callbacks = [...timers.values()];timers.clear();callbacks.forEach(fn => fn());}
  };
}

test('intent thresholds reject taps, vertical scrolling and cancelled gestures', () => {
  assert.equal(gestureAxis(4, 3), null);
  assert.equal(gestureAxis(10, 80), 'y');
  assert.equal(swipeDirection({dx: -130, dy: 2, duration: 700, width: 400}), 1);
  assert.equal(swipeDirection({dx: 130, dy: 2, duration: 700, width: 400}), -1);
  assert.equal(swipeDirection({dx: -30, dy: 2, duration: 45, width: 400}), 1);
  assert.equal(swipeDirection({dx: -30, dy: 2, duration: 600, width: 400}), 0);
  assert.equal(swipeDirection({dx: -130, dy: 200, duration: 200, width: 400}), 0);
  assert.equal(swipeDirection({dx: -130, dy: 2, duration: 200, width: 400, cancelled: true}), 0);
});

test('drag follows the pointer, completes once and suppresses the accidental image click', () => {
  const f = fixture();
  f.emit('pointerdown');
  f.advance(120);
  f.emit('pointermove', {clientX: 80});
  f.frame();
  assert.equal(f.styles.get('--gallery-drag'), '-120px');
  assert.ok(f.captures.has(1));
  f.emit('pointerup', {clientX: 80});
  assert.deepEqual(f.steps, [1]);
  assert.equal(f.styles.get('--gallery-drag'), '0px');
  assert.equal(f.emit('click').defaultPrevented, true);
  assert.equal(f.emit('click', {detail: 0}).defaultPrevented, false);
  f.emit('pointerdown');
  f.emit('pointerup');
  assert.equal(f.emit('click').defaultPrevented, false);
  f.dispose();
});

test('vertical and short drags keep the selected image; cancel and multitouch restore the rail', () => {
  const f = fixture();
  f.emit('pointerdown');
  const vertical = f.emit('pointermove', {clientX: 205, clientY: 180});
  assert.equal(vertical.defaultPrevented, false);
  f.emit('pointerup', {clientX: 205, clientY: 180});
  f.emit('pointerdown');
  f.advance(500);
  f.emit('pointermove', {clientX: 180});
  f.emit('pointerup', {clientX: 180});
  f.emit('pointerdown');
  f.emit('pointermove', {clientX: 80});
  f.emit('pointercancel');
  f.emit('pointerup', {clientX: 80});
  f.emit('pointerdown');
  f.emit('pointermove', {clientX: 80});
  f.emit('pointerdown', {pointerId: 2, isPrimary: false});
  f.emit('pointerup', {clientX: 80});
  assert.deepEqual(f.steps, []);
  assert.equal(f.styles.get('--gallery-drag'), '0px');
  assert.equal(f.captures.size, 0);
  f.dispose();
});

test('horizontal trackpad momentum makes one change per gesture and keeps vertical scroll and zoom native', () => {
  const f = fixture();
  assert.equal(f.emit('wheel', {deltaY: 100}).defaultPrevented, false);
  assert.equal(f.emit('wheel', {deltaX: 100, ctrlKey: true}).defaultPrevented, false);
  for (let i = 0; i < 8; i++) {
    f.advance(20);
    assert.equal(f.emit('wheel', {deltaX: 30}).defaultPrevented, true);
  }
  assert.deepEqual(f.steps, [1]);
  f.advance(300);
  f.emit('wheel', {deltaX: -80});
  assert.deepEqual(f.steps, [1, -1]);
  f.advance(300);
  f.emit('wheel', {deltaX: 15});
  f.frame();f.idle();
  assert.equal(f.styles.get('--gallery-drag'), '0px');
  assert.equal(wheelDistance({deltaX: 0, deltaY: 5, shiftKey: true, deltaMode: 1}), 80);
  f.dispose();
});

test('reduced motion keeps selection working without displacement; cleanup cancels pending work', () => {
  const f = fixture(true);
  f.emit('pointerdown');
  f.emit('pointermove', {clientX: 80});
  f.frame();
  assert.equal(f.styles.get('--gallery-drag'), '0px');
  f.emit('pointerup', {clientX: 80});
  assert.deepEqual(f.steps, [1]);
  f.emit('wheel', {deltaX: 20});
  f.dispose();
  assert.equal(f.frames.size, 0);
  assert.equal(f.timers.size, 0);
  f.emit('wheel', {deltaX: 200});
  assert.deepEqual(f.steps, [1]);
});


test('touch pointer swipe, vertical-scroll cancellation and lost capture leave no stuck drag', () => {
  const f = fixture();
  f.emit('pointerdown', {pointerType: 'touch'});
  f.advance(220);
  f.emit('pointermove', {pointerType: 'touch', clientX: 75});
  f.frame();
  assert.equal(f.styles.get('--gallery-drag'), '-125px');
  f.emit('pointerup', {pointerType: 'touch', clientX: 75});
  assert.deepEqual(f.steps, [1]);
  f.emit('pointerdown', {pointerType: 'touch'});
  assert.equal(f.emit('pointermove', {pointerType: 'touch', clientY: 180}).defaultPrevented, false);
  f.emit('pointercancel', {pointerType: 'touch'});
  f.emit('pointerdown');
  f.emit('pointermove', {clientX: 75});
  f.emit('lostpointercapture');
  f.emit('pointerup', {clientX: 75});
  assert.deepEqual(f.steps, [1]);
  assert.equal(f.styles.get('--gallery-drag'), '0px');
  assert.equal(f.classes.has('is-dragging'), false);
  f.dispose();
});

test('a fresh same-direction stroke interrupts a long momentum tail without vertical reset', () => {
  const f = fixture();
  const stroke = deltas => deltas.forEach(deltaX => {
    f.advance(16);
    f.emit('wheel', {deltaX});
  });
  stroke([30, 40, 36, 30, 24, 18, 12, 8, 5, 3, 2, 1, 1, 1, 1, 1]);
  assert.deepEqual(f.steps, [1]);
  stroke([4, 12, 26, 38, 30, 20, 12, 6, 3, 1, 1, 1, 1, 1, 1, 1]);
  assert.deepEqual(f.steps, [1, 1], 'next deliberate stroke must not be swallowed by momentum');
  stroke([5, 15, 30, 40, 28, 17, 8, 3, 1]);
  assert.deepEqual(f.steps, [1, 1, 1]);
  f.dispose();
});

test('reverse and vertical-to-horizontal gestures do not remain locked', () => {
  const f = fixture();
  f.emit('wheel', {deltaX: 80});
  for (const deltaX of [24, 16, 8, 4, 2, 1, 1, 1, 1, 1]) {
    f.advance(16); f.emit('wheel', {deltaX});
  }
  for (const deltaX of [-14, -25, -36]) {
    f.advance(16); f.emit('wheel', {deltaX});
  }
  assert.deepEqual(f.steps, [1, -1]);
  const vertical = f.emit('wheel', {deltaX: 1, deltaY: 60});
  assert.equal(vertical.defaultPrevented, false);
  f.advance(32);
  f.emit('wheel', {deltaX: 80});
  assert.deepEqual(f.steps, [1, -1, 1]);
  f.dispose();
});

test('idle reset really unlocks; subpixel tail and early acceleration cannot retrigger a stroke', () => {
  const f = fixture();
  for (const deltaX of [35, 35, 50, 65, 45, 30, 18, 8, 3, 1]) {
    f.advance(16); f.emit('wheel', {deltaX});
  }
  for (let i = 0; i < 40; i++) {
    f.advance(16); f.emit('wheel', {deltaX: 0.15});
  }
  assert.deepEqual(f.steps, [1]);
  f.idle();
  f.emit('wheel', {deltaX: 80});
  assert.deepEqual(f.steps, [1, 1]);
  f.dispose();
});

test('small momentum jitter stays suppressed, and a released pending mouse click cannot block trackpad input', () => {
  const f = fixture();
  f.emit('wheel', {deltaX: 80});
  for (const deltaX of [40, 20, 10, 5, 3, 2, 1, 2, 1, 3, 1, -1, 1, 2]) {
    f.advance(20); f.emit('wheel', {deltaX});
  }
  assert.deepEqual(f.steps, [1]);
  f.emit('pointerdown');
  f.emit('wheel', {deltaX: 80, buttons: 1});
  assert.deepEqual(f.steps, [1], 'an active mouse drag retains ownership');
  f.emit('wheel', {deltaX: 80, buttons: 0});
  assert.deepEqual(f.steps, [1, 1], 'released mouse must not leave a stale pointer gate');
  f.dispose();
});
