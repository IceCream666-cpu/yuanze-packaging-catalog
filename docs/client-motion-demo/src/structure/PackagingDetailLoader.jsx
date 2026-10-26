import {PACKAGING_PRODUCTS} from './packaging-products.js';
import React, {useCallback, useEffect, useRef, useState} from 'react';

let loadSequence = 0;
const MODEL_TIMEOUT = 300000;
const MODULE_TIMEOUT = 120000;

// Keep only the bytes for this opening. Reopening still revalidates the protected
// asset with the server; no model or GPU resources survive the dialog lifecycle.
export function startPackagingModelRequest(productId = 'poster-012') {
  const product = PACKAGING_PRODUCTS[productId];
  if (!Object.hasOwn(PACKAGING_PRODUCTS, productId)) throw new Error('Unsupported packaging product');
  const controller = new AbortController();
  const id = ++loadSequence;
  const timings = {};
  const clock = window.performance;
  const started = clock.now();
  const prefix = `packaging:${id}:`;
  const mark = phase => {
    timings[phase] = clock.now() - started;
    clock.mark?.(prefix + phase);
  };
  const records = window.__packagingLoadMetrics ||= [];
  records.push({id, timings});
  while (records.length > 10) {
    const previous = records.shift();
    Object.keys(previous.timings).forEach(phase => clock.clearMarks?.(`packaging:${previous.id}:${phase}`));
  }
  mark('start');
  const abort = (reason = new DOMException('Packaging view closed', 'AbortError')) => {
    clearTimeout(timer);
    if (!controller.signal.aborted) { mark('aborted'); controller.abort(reason); }
  };
  const timer = setTimeout(() => abort(new DOMException('Model request timed out', 'TimeoutError')), MODEL_TIMEOUT);
  const promise = (async () => {
    mark('fetchStart');
    const response = await fetch(`${import.meta.env.BASE_URL}assets/packaging/${product.file}`, {
      credentials: 'same-origin', cache: 'no-cache', signal: controller.signal,
    });
    if (!response.ok) throw new Error(`Model request failed (${response.status})`);
    const bytes = await response.arrayBuffer();
    if (controller.signal.aborted) throw controller.signal.reason;
    mark('fetchEnd');
    return bytes;
  })().catch(error => { mark('fetchError'); throw error; }).finally(() => clearTimeout(timer));
  // The detail module may still be downloading when a model request fails.
  promise.catch(() => {});
  return {promise, signal: controller.signal, abort, mark, timings};
}

// Keep the renderer, scene and detail styles out of the collection's initial load.
export default function PackagingDetailLoader(props) {
  const [Detail, setDetail] = useState(null);
  const [failed, setFailed] = useState(false);
  const [attempt, setAttempt] = useState(0);
  const modelRef = useRef(null);
  const sceneRef = useRef(null);
  const getModelRequest = useCallback(() => {
    if (!modelRef.current || modelRef.current.signal.aborted) modelRef.current = startPackagingModelRequest(props.item.id);
    return modelRef.current;
  }, [props.item.id]);
  const getSceneModule = useCallback(() => {
    if (!sceneRef.current) {
      const pending = import('./packaging-scene.js');
      sceneRef.current = pending;
      pending.catch(() => {if (sceneRef.current === pending) sceneRef.current = null;});
    }
    return sceneRef.current;
  }, []);
  useEffect(() => {
    let active = true;
    let settled = false;
    setFailed(false);
    const request = getModelRequest();
    getSceneModule();
    const timer = setTimeout(() => {
      settled = true;
      request.abort(new DOMException('Detail module timed out', 'TimeoutError'));
      if (active) setFailed(true);
    }, MODULE_TIMEOUT);
    import('./PackagingDetail.jsx').then(module => {
      if (active && !settled) {request.mark('detailModule'); setDetail(() => module.default);}
    }).catch(() => {request.abort(); if (active && !settled) setFailed(true);}).finally(() => clearTimeout(timer));
    return () => {active = false; clearTimeout(timer); request.abort();};
  }, [attempt, getModelRequest, getSceneModule]);
  if (Detail) return <Detail {...props} getModelRequest={getModelRequest} getSceneModule={getSceneModule}/>;
  const zh = props.lang === 'zh';
  return <div className="packaging-shell" aria-busy={!failed}>
    <button className="packaging-shell-back" onClick={props.onClose}>{zh ? '返回产品' : 'Back to collection'}</button>
    <div role="status"><p>{failed ? (zh ? '产品结构暂时无法加载' : 'Product structure is unavailable') : (zh ? '正在准备产品结构' : 'Preparing the product structure')}</p>
      {failed && <button onClick={() => setAttempt(value => value + 1)}>{zh ? '重新加载' : 'Try again'}</button>}
      <button onClick={props.onOriginal}>{zh ? '查看原海报' : 'View original poster'}</button>
    </div>
  </div>;
}
