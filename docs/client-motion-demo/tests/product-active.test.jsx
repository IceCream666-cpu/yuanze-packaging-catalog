import test from 'node:test';
import assert from 'node:assert/strict';
import {JSDOM} from 'jsdom';
import React, {act, useState} from 'react';
import {createRoot} from 'react-dom/client';
import PosterStage from '../src/PosterStage.jsx';

test('visual product notifications follow continuous wheel/reversal before selection settles', async () => {
  const dom = new JSDOM('<div id="root"></div>', {url:'http://localhost/', pretendToBeVisual:true});
  let frameId = 0, time = 0;
  const frames = new Map(), visible = [], selected = [];
  const media = {matches:false, addEventListener(){}, removeEventListener(){}};
  Object.assign(globalThis, {
    window:dom.window, document:dom.window.document, IS_REACT_ACT_ENVIRONMENT:true,
    matchMedia:() => media,
    ResizeObserver:class {constructor(fn){this.fn=fn;} observe(){this.fn([{contentRect:{width:1200}}]);} disconnect(){}},
    requestAnimationFrame:fn => {frames.set(++frameId,fn);return frameId;},
    cancelAnimationFrame:id => frames.delete(id),
  });
  const items = Array.from({length:23}, (_,i) => ({
    id:`p${i}`, title:{zh:`产品${i}`,en:`Product ${i}`}, width:1200, height:1000, displayImage:`/${i}.webp`,
  }));
  function Demo() {
    const [target,setTarget] = useState('p0'), [current,setCurrent] = useState('p0');
    return <>
      <output>{current}</output>
      <PosterStage items={items} selectedId={target} presentation="products" lang="zh"
        onSelect={id => {selected.push(id);setTarget(id);}}
        onActiveChange={id => {visible.push(id);setCurrent(id);}}
        onOpen={() => {throw Error('Wheel must not open a poster');}}/>
    </>;
  }
  const root = createRoot(document.getElementById('root'));
  const frame = async () => {
    await act(async () => {
      time += 16.667;
      const jobs = [...frames.values()];frames.clear();
      jobs.forEach(fn => fn(performance.now() + time));
    });
  };
  try {
    await act(async () => root.render(<Demo/>));
    assert.deepEqual(visible,['p0']);
    const stage = document.querySelector('.gallery-stage');
    const wheel = async (deltaX, expected) => {
      await act(async () => stage.dispatchEvent(new window.WheelEvent('wheel',{deltaX,deltaY:0,bubbles:true,cancelable:true})));
      await frame();
      assert.equal(document.querySelector('.center').dataset.posterId,expected);
      assert.equal(document.querySelector('output').textContent,expected);
      assert.deepEqual(selected,[],'Visual notifications must not settle the controller during an active gesture');
    };
    await wheel(220,'p1');
    await wheel(294,'p2');
    await wheel(-500,'p0');
    await wheel(620,'p2');
    assert.deepEqual(visible,['p0','p1','p2','p0','p2']);
    await act(async () => new Promise(resolve => setTimeout(resolve,135)));
    assert.deepEqual(selected,['p2'],'Only the end-of-gesture settle commits the selected target');
    for(let i=0;i<100 && frames.size;i++) await frame();
    assert.equal(frames.size,0);
    assert.deepEqual(visible,['p0','p1','p2','p0','p2'],'Selection echoes must not restart or duplicate visual notifications');
  } finally {
    await act(async () => root.unmount());dom.window.close();
  }
});
