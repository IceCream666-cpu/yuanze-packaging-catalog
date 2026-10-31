import {mountPackagingScene} from '../src/structure/packaging-scene.js';

const data = JSON.parse(document.getElementById('portfolio-data').textContent);
export const {posters, featured, logo} = data;
export const getSceneModule = () => Promise.resolve({mountPackagingScene});

// Decode only the selected model; closing the original viewer disposes its GPU resources.
export function getModelRequest(id) {
  const controller = new AbortController();
  const promise = Promise.resolve().then(() => {
    controller.signal.throwIfAborted();
    const payload = document.getElementById(`model-${id}`);
    if (!payload) throw new Error('此作品没有内嵌模型');
    const binary = atob(payload.textContent.trim());
    const bytes = new Uint8Array(binary.length);
    for (let i = 0; i < binary.length; i++) bytes[i] = binary.charCodeAt(i);
    return bytes.buffer;
  });
  return {promise, signal: controller.signal, abort: () => controller.abort(), mark() {}};
}
