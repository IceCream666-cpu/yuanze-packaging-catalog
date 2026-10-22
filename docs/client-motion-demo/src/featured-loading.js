// Started images keep their sources. Only the current product and neighbours
// enter this bounded queue; a newer selection takes the next available slot.
export function createFeaturedLoadQueue({ids, onChange = () => {}, concurrency = 2}) {
  const records = Object.fromEntries(ids.map(id => [id, {enabled: false, status: 'idle', token: 0}]));
  const retries = new Set();
  let selected = ids[0], disposed = false;
  const snapshot = () => Object.fromEntries(Object.entries(records).map(([id, state]) => [id, {...state}]));
  const candidates = () => {
    const index = ids.indexOf(selected);
    return [...new Set([0, 1, -1, 2, -2].map(offset => ids[(index + offset + ids.length) % ids.length]))].filter(Boolean);
  };
  function pump() {
    let available = Math.max(1, concurrency) - Object.values(records).filter(item => item.status === 'loading').length;
    let changed = false;
    for (const id of candidates()) {
      const item = records[id];
      if (available < 1) break;
      if (item.status !== 'idle' && !retries.has(id)) continue;
      retries.delete(id);
      item.enabled = true; item.status = 'loading'; item.token += 1;
      available -= 1; changed = true;
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
      if (disposed || !item || item.token !== token || item.status !== 'loading') return;
      item.status = status === 'loaded' ? 'loaded' : 'error';
      pump(); onChange(snapshot());
    },
    retry(id) {
      if (disposed || records[id]?.status !== 'error') return;
      retries.add(id);
      if (pump()) onChange(snapshot());
    },
    dispose() {disposed = true;}
  };
}
