import test from 'node:test';
import assert from 'node:assert/strict';
import {productArc} from '../src/product-arc.js';
import {shortestDelta} from '../src/carousel-model.js';

const near = (a, b, tolerance = 1e-8) => assert.ok(Math.abs(a - b) < tolerance, `${a} ≈ ${b}`);

test('the active product is frontmost and lower than mirrored, smaller neighbours', () => {
  for (const width of [288, 393, 600, 900, 1440]) {
    const center = productArc(0, width, 23);
    near(center.x, 0); near(center.y, 0); near(center.z, 0);
    near(center.rotateY, 0); near(center.scale, 1); near(center.opacity, 1);
    for (const offset of [.25, 1, 2, 3]) {
      const left = productArc(-offset, width, 23), right = productArc(offset, width, 23);
      near(left.x, -right.x); near(left.rotateY, -right.rotateY);
      for (const property of ['y', 'z', 'scale', 'opacity']) near(left[property], right[property]);
      assert.ok(right.x > 0 && right.y < 0 && right.z < 0);
      assert.ok(right.scale < center.scale && right.opacity < center.opacity);
    }
  }
});

test('depth and height progress continuously rather than stepping at each selection', () => {
  let previous = productArc(0, 820, 23);
  for (let offset = .01; offset < 2.7; offset += .01) {
    const frame = productArc(offset, 820, 23);
    assert.ok(frame.y < previous.y && frame.z < previous.z && frame.scale < previous.scale);
    assert.ok(Math.abs(frame.x - previous.x) < 4 && Math.abs(frame.y - previous.y) < 1.4);
    assert.ok(Math.abs(frame.z - previous.z) < 5 && Math.abs(frame.opacity - previous.opacity) < .03);
    previous = frame;
  }
  const left = productArc(-.0001, 820, 23), right = productArc(.0001, 820, 23);
  near(left.y, right.y); near(left.z, right.z); near(left.scale, right.scale);
});

test('last-to-first travel has no geometric jump after the spring normalizes position', () => {
  for (const length of [2, 3, 4, 8, 23]) {
    for (let index = 0; index < length; index++) {
      for (const position of [-.25, 0, .25]) {
        const normalized = productArc(shortestDelta(index, position, length), 600, length);
        const wrapped = productArc(shortestDelta(index, position + length, length), 600, length);
        for (const property of Object.keys(normalized)) near(normalized[property], wrapped[property]);
      }
    }
  }
});

test('circular seam crossings are invisible for short and full collections', () => {
  for (const length of [2, 3, 4, 5, 6, 8, 23]) {
    const before = productArc(shortestDelta(0, length / 2 - .0001, length), 500, length);
    const after = productArc(shortestDelta(0, length / 2 + .0001, length), 500, length);
    assert.ok(before.opacity < .001 && after.opacity < .001);
  }
  assert.equal(productArc(0, 320, 1).opacity, 1);
  assert.equal(productArc(1, 320, 2).opacity, 0);
  assert.equal(productArc(2.7, 320, 23).opacity, 0);
  assert.equal(productArc(3, 320, 23).opacity, 0,'Unqueued third neighbours stay invisible');
});
