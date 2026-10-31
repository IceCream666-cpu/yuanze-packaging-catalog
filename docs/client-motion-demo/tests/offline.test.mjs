import test from 'node:test';
import assert from 'node:assert/strict';
import {JSDOM} from 'jsdom';

test('offline adapter preserves binary bytes, rejects missing models and honours early cancellation', async () => {
  const bytes = Buffer.from([0, 1, 127, 128, 254, 255]);
  const dom = new JSDOM(`<script id="portfolio-data" type="application/json">{"posters":[],"featured":[],"logo":"data:image/svg+xml;base64,PHN2Zy8+"}</script><script id="model-test" type="application/octet-stream">${bytes.toString('base64')}</script>`);
  const previous = globalThis.document;
  globalThis.document = dom.window.document;
  try {
    const {getModelRequest, getSceneModule} = await import('../offline/assets.js');
    const request = getModelRequest('test');
    assert.deepEqual(Buffer.from(await request.promise), bytes);
    assert.equal(request.signal.aborted, false);
    request.abort();
    assert.equal(request.signal.aborted, true);
    await assert.rejects(getModelRequest('missing').promise, /没有内嵌模型/);
    const cancelled = getModelRequest('test');
    cancelled.abort();
    await assert.rejects(cancelled.promise, {name: 'AbortError'});
    assert.equal(typeof (await getSceneModule()).mountPackagingScene, 'function');
  } finally {
    globalThis.document = previous;
    dom.window.close();
  }
});
