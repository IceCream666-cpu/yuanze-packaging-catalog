import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {JSDOM} from 'jsdom';

test('showroom contains horizontal viewport navigation while preserving vertical and pinch gestures', () => {
  const dom = new JSDOM('<html><head></head><body><div class="gallery-stage"></div></body></html>');
  try {
    const {document} = dom.window;
    const style = document.createElement('style');
    style.textContent = readFileSync(new URL('../src/mobile.css', import.meta.url), 'utf8');
    document.head.append(style);
    for (const root of [document.documentElement, document.body]) {
      const computed = dom.window.getComputedStyle(root);
      assert.equal(computed.getPropertyValue('overscroll-behavior-x'), 'contain');
      assert.equal(computed.getPropertyValue('overscroll-behavior-y'), 'auto', 'Do not suppress native vertical overscroll');
      assert.equal(computed.getPropertyValue('touch-action'), 'auto', 'Do not block zoom at the viewport');
    }
    assert.equal(dom.window.getComputedStyle(document.querySelector('.gallery-stage')).getPropertyValue('touch-action'), 'pan-y pinch-zoom');
  } finally {
    dom.window.close();
  }
});
