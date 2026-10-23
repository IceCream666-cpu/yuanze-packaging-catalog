// Reserve bandwidth for the product the user chose. Completed downloads keep
// their sources; unfinished, lower-priority requests can be preempted.
export function createFeaturedLoadQueue({ids, onChange = () => {}, concurrency = 2}) {
  const records = Object.fromEntries(ids.map(id => [id, {enabled: false, status: 'idle', token: 0}]));
  const limit = Math.max(1, Math.min(3, Math.floor(concurrency) || 2));
  const retries = new Set();
  let selected = ids[0], disposed = false;
  const snapshot = () => Object.fromEntries(Object.entries(records).map(([id, state]) => [id, {...state}]));
  const candidates = () => {
    const index = ids.indexOf(selected);
    return [...new Set([0, 1, -1, 2, -2].map(offset => ids[(index + offset + ids.length) % ids.length]))].filter(Boolean);
  };
  function pump() {
    const order = candidates(), wanted = new Set(order);
    let changed = false;
    function cancel(item) {
      item.enabled = false; item.status = 'idle'; item.token += 1;
      changed = true;
    }
    function start(id) {
      const item = records[id];
      retries.delete(id); item.enabled = true; item.status = 'loading'; item.token += 1;
      changed = true;
    }
    const inFlight = () => Object.values(records).filter(item => item.status === 'loading').length;
    // Cancelling increments the token before the DOM source is removed, so a
    // late load/error from the previous request cannot complete its successor.
    for (const [id, item] of Object.entries(records)) {
      if (item.status === 'loading' && !wanted.has(id)) cancel(item);
    }
    const primary = records[selected];
    if (!primary) return changed;
    if (primary.status === 'idle' || retries.has(selected)) {
      while (inFlight() >= limit) {
        const lowerPriority = [...order].reverse().find(id => id !== selected && records[id].status === 'loading');
        if (!lowerPriority) break;
        cancel(records[lowerPriority]);
      }
      if (inFlight() < limit) start(selected);
    }
    // On first entry the center downloads alone. Once its bytes arrive,
    // neighbours can download while that image decodes and becomes visible.
    if (primary.status === 'loading') return changed;
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
      selected = id;
      if (pump()) onChange(snapshot());
    },
    finish(id, token, status) {
      const item = records[id];
      if (disposed || !item || item.token !== token || !['loading', 'decoding'].includes(item.status)) return;
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
