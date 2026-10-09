// Only this reviewed manifest defines visual families. Shared images, names and
// catalogue pages are never enough to merge records automatically.
import {imageViewKey} from './image-viewport.js';
import {primaryImage as recordPrimaryImage} from './image-policy.js';
export function createProductGroupIndex(records, reviewedGroups) {
  const known = new Map(records.map(record => [record.id, record]));
  const index = new Map();
  for (const definition of reviewedGroups || []) {
    if (!definition || !Array.isArray(definition.recordIds)) continue;
    const members = [...new Set(definition.recordIds)].map(id => known.get(id))
      .filter(record => record?.kind === 'package' && !index.has(record.id));
    if (!members.length) continue;
    const ids = new Set(members.map(record => record.id));
    const overrides = new Map(members.flatMap(record => {
      const override = record.specificationOverride;
      return override && ['capacityMl', 'specificationRaw'].includes(override.sourceField)
        && typeof override.label === 'string' && override.label.trim()
        ? [[record.id, override.label.trim()]] : [];
    }));
    const specs = (Array.isArray(definition.specs) ? definition.specs : [])
      .filter(spec => spec && typeof spec.label === 'string' && spec.label.trim())
      .map(spec => ({label: spec.label.trim(), recordIds: (spec.recordIds || []).filter(id => ids.has(id) && !overrides.has(id))}))
      .filter(spec => spec.recordIds.length);
    // Each override replaces only this SKU's reviewed labels. The manifest and
    // sibling SKU associations remain untouched, including shared old labels.
    for (const [id, label] of overrides) {
      const spec = specs.find(item => item.label === label);
      if (spec) spec.recordIds.push(id);
      else specs.push({label, recordIds: [id]});
    }
    const capacities = [...new Set(members.flatMap(record => record._capacities ||
      (Number(record.capacityMl) > 0 ? [Number(record.capacityMl)] : [])))];
    const primary = definition.primaryImage;
    const primaryImage = primary ? {role: 'product', imageScope: 'same_style_variants',
      ...(typeof primary === 'string' ? {path: primary} : primary)} : null;
    const group = {id: definition.id || members[0].id, name: definition.name || members[0].name,
      records: members, specs, capacities, primaryImage, imageMappingPending: definition.imageMappingPending === true,
      galleryScope: definition.galleryScope === 'record' ? 'record' : 'group',
      imageAliases: definition.imageAliases && typeof definition.imageAliases === 'object' && !Array.isArray(definition.imageAliases)
        ? {...definition.imageAliases} : {},
      classification: definition.classification || null,
      multiSpec: new Set(specs.map(spec => spec.label)).size > 1 || capacities.length > 1};
    // Keep explicitly edited single-SKU groups scoped even when their size was
    // cleared, so old page OCR cannot become the size-search fallback.
    if (members.length < 2 && !group.multiSpec && !overrides.size && !definition.classification) continue;
    for (const record of members) index.set(record.id, group);
  }
  return index;
}

// Call after SKU filtering/sorting. The first matching SKU remains the selected
// record, so exact-number lookup, image rank, and favourites retain their meaning.
export function groupProducts(matchingRecords, index) {
  const result = [], displayed = new Map();
  for (const record of matchingRecords) {
    const group = index.get(record.id);
    if (!group) { result.push(record); continue; }
    if (displayed.has(group)) { displayed.get(group)._matchedRecords.push(record); continue; }
    const item = {...record, _group: group, _matchedRecords: [record]};
    displayed.set(group, item);
    result.push(item);
  }
  return result;
}

export function groupRecordSpec(record, index) {
  const group = index.get(record.id);
  const labels = group?.specs.filter(spec => spec.recordIds.includes(record.id)).map(spec => spec.label) || [];
  return [...new Set(labels)].join(' / ') || (record._capacities ||
    (Number(record.capacityMl) > 0 ? [Number(record.capacityMl)] : [])).map(value => `${value} mL`).join(' / ') ||
    record.specificationRaw || record.model || '';
}

// Dedupe presentation by resolved path while keeping every source association
// (including its unmodified image metadata) available in the detail view.
export function groupGalleryImages(record, index, pathForImage) {
  const group = index.get(record.id), images = new Map(), available = new Map(), entries = [];
  function add(image, owner) {
    const value = typeof image === 'string' ? {path: image} : image;
    if (!value || value.missing || !(value.path || value.file)) return;
    const path = pathForImage(value);
    if (!available.has(path)) available.set(path, value);
    entries.push({path, value, owner});
  }
  // A reviewed family can share a card while each size has its own gallery.
  // Keep the selected SKU's primary first and never borrow a sibling's image.
  const recordGallery = group?.galleryScope === 'record';
  if (!recordGallery && group?.primaryImage) add(group.primaryImage);
  for (const member of recordGallery ? [record] : group?.records || [record]) {
    const original = member.images || [], primary = recordGallery ? recordPrimaryImage(member) : null;
    const ordered = primary ? [primary, ...original.filter(image => image !== primary)] : original;
    for (const image of ordered) add(image, member);
  }
  const aliases = new Map(Object.entries(group?.imageAliases || {})
    .filter(([from, to]) => from.trim() && typeof to === 'string' && to.trim())
    .map(([from, to]) => [pathForImage(from), pathForImage(to)]));
  function retainedPath(original) {
    const seen = new Set([original]);
    let path = original;
    while (aliases.has(path)) {
      const target = aliases.get(path);
      // A missing/cross-group target never removes an existing picture.
      if (!available.has(target)) break;
      if (seen.has(target)) return original;
      seen.add(target); path = target;
    }
    return path;
  }
  for (const {path, value, owner} of entries) {
    const retained = retainedPath(path);
    // A type-specific viewport and its full catalogue page are separate views,
    // even when both read the same file. Keep the original page for verification.
    const key = imageViewKey(value, retained);
    if (!images.has(key)) images.set(key, {...(value.displayCrop || retained === path ? value : available.get(retained)), _groupSources: [], _groupPaths: []});
    const image = images.get(key);
    if (!image._groupPaths.includes(path)) image._groupPaths.push(path);
    if (owner) image._groupSources.push({recordId: owner.id, image: value});
  }
  return [...images.values()];
}
