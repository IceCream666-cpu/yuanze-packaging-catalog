// Warm the small display images continuously. A swipe changes priority, not
// request identity: restarting downloads on every crossing prevents progress.
export function createFeaturedLoadQueue({ids, onChange = () => {}, concurrency = 2, warmCollection = true}) {
  const records = Object.fromEntries(ids.map(id => [id, {enabled: false, status: 'idle', token: 0}]));
  const limit = Math.max(1, Math.min(3, Math.floor(concurrency) || 2));
  const retries = new Set();
  let selected = ids[0], direction = 1, disposed = false, firstTransferred = false;
  const snapshot = () => Object.fromEntries(Object.entries(records).map(([id, state]) => [id, {...state}]));
  const candidates = () => {
    const index = ids.indexOf(selected);
    const offsets = [0, direction, direction * 2, -direction, -direction * 2];
    if (warmCollection) for (let distance = 3; distance < ids.length; distance++) offsets.push(distance * direction);
    return [...new Set(offsets.map(offset => ids[((index + offset) % ids.length + ids.length) % ids.length]))].filter(Boolean);
  };
  function pump() {
    const order = candidates();
    let changed = false;
    function start(id) {
      const item = records[id];
      retries.delete(id); item.enabled = true; item.status = 'loading'; item.token += 1;
      changed = true;
    }
    const inFlight = () => Object.values(records).filter(item => item.status === 'loading').length;
    const primary = records[selected];
    if (!primary) return changed;
    if (primary.status === 'idle' || retries.has(selected)) {
      // One reserved foreground slot lets a new center pass two warm-up jobs.
      // Further input is coalesced to the latest center until a slot completes.
      if (inFlight() < limit + 1) start(selected);
    }
    // On first entry the center downloads alone. Once its bytes arrive,
    // neighbours can download while that image decodes and becomes visible.
    if (!firstTransferred) return changed;
    for (const id of order) {
      if (inFlight() >= limit) break;
      if (records[id].status === 'idle' || retries.has(id)) start(id);
    }
    return changed;
  }
  return {
    snapshot,
    select(id) {
      if (disposed || !records[id]) return;
      const delta = ids.indexOf(id) - ids.indexOf(selected);
      const wrapped = ((delta + ids.length / 2 + ids.length) % ids.length) - ids.length / 2;
      if (wrapped) direction = Math.sign(wrapped);
      selected = id;
      if (pump()) onChange(snapshot());
    },
    finish(id, token, status) {
      const item = records[id];
      if (disposed || !item || item.token !== token || !['loading', 'decoding'].includes(item.status)) return;
      firstTransferred = true;
      if (status === 'downloaded') {
        if (item.status !== 'loading') return;
        item.status = 'decoding';
      } else item.status = status === 'loaded' ? 'loaded' : 'error';
      pump(); onChange(snapshot());
    },
    retry(id) {
      if (disposed || records[id]?.status !== 'error') return;
      selected = id;
      retries.add(id);
      if (pump()) onChange(snapshot());
    },
    dispose() {disposed = true;}
  };
}
