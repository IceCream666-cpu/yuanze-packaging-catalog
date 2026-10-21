import test from 'node:test';
import assert from 'node:assert/strict';
import {JSDOM} from 'jsdom';
import {lockPageScroll} from '../src/modal-scroll.js';

test('mobile modal locks the background and restores reading position and existing styles', () => {
  const dom = new JSDOM('<body style="color:red;position:relative;top:4px!important"></body>');
  const view = dom.window;
  Object.defineProperties(view, {scrollX: {value: 0}, scrollY: {value: 430}});
  const calls = [];
  view.scrollTo = (...args) => calls.push(args);
  const restore = lockPageScroll(view);
  assert.equal(view.document.body.style.position, 'fixed');
  assert.equal(view.document.body.style.top, '-430px');
  assert.equal(view.document.documentElement.style.overflow, 'hidden');
  restore(); restore();
  assert.deepEqual(calls, [[0, 430]], 'cleanup restores scroll only once');
  assert.equal(view.document.body.style.position, 'relative');
  assert.equal(view.document.body.style.top, '4px');
  assert.equal(view.document.body.style.getPropertyPriority('top'), 'important');
  assert.equal(view.document.body.style.color, 'red');
  assert.equal(view.document.body.style.width, '');
  assert.equal(view.document.documentElement.style.overflow, '');
  dom.window.close();
});
