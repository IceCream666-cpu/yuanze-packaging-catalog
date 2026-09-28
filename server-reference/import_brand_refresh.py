"""Evidence-based blank-field enrichment and reversible no-image cleanup."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path

from admin_store import ConflictError, RECORD_SELECT, dumps, now

ENRICHABLE = {'materials', 'capacityMl', 'bottleType', 'model', 'series', 'uses', 'productDetails'}


def has_any_image(record, private, state):
    """Reference pages and images awaiting classification are still real images."""
    for image in record.get('images', []):
        if image.get('missing'):
            continue
        path = image.get('path', '')
        if path.startswith('media/'):
            base = Path(private).resolve()
        elif path.startswith('uploads/'):
            base = Path(state).resolve()
        else:
            continue
        target = (base / path).resolve()
        if target.is_relative_to(base) and target.is_file():
            return True
    return False


def apply_batch(store, batch):
    marker = batch['batch']
    updates = batch['updates']
    assert not batch.get('newRecords'), 'This migration cannot create products'
    ids = [p['id'] for p in updates]
    if len(ids) != len(set(ids)):
        raise ValueError('Duplicate product patches')
    with store.connection(write=True) as c:
        if c.execute('SELECT 1 FROM admin_migrations WHERE name=?', (marker,)).fetchone():
            return {'status': 'already_imported', 'batch': marker}
        # Validate every version before any write, including archive-only rows.
        for patch in updates:
            row = c.execute(RECORD_SELECT + ' WHERE r.id=?', (patch['id'],)).fetchone()
            if (not row or row['version'] != patch['expectedVersion'] or
                    bool(row['archived']) != bool(patch['expectedArchived']) or
                    hashlib.sha256(row['content'].encode()).hexdigest() != patch['expectedContentSha256']):
                raise ConflictError('Product changed since review: ' + patch['id'])
        stamp = now()
        archived = enriched = 0
        for patch in updates:
            row = c.execute(RECORD_SELECT + ' WHERE r.id=?', (patch['id'],)).fetchone()
            before = store._record(row)
            content = json.loads(row['content'])
            changes = patch.get('set', {})
            if set(changes) - ENRICHABLE or content.get('kind') != 'package':
                raise ValueError('Unsupported enrichment fields or record kind')
            archive = patch.get('archived', row['archived'])
            if archive != row['archived']:
                if archive is not True or has_any_image(content, store.private, store.state):
                    raise ValueError('Only products without any actual images may be archived')
            for key, value in changes.items():
                if key == 'productDetails':
                    existing = content.get(key) or []
                    if not isinstance(value, list) or value[:len(existing)] != existing:
                        raise ValueError('Existing product details must be preserved')
                elif content.get(key) not in (None, '', []):
                    raise ValueError('Only blank product parameters may be filled: ' + key)
            if changes:
                checked = store._normalized_record(c, {'record': changes}, before)
                content.update({key: deepcopy(checked[key]) for key in changes})
                content['searchText'] = checked['searchText']
                enriched += 1
            if not changes and archive == row['archived']:
                raise ValueError('Empty patch')
            archived += int(bool(archive) and not row['archived'])
            c.execute('UPDATE admin_records SET content=?,version=version+1,archived=?,updated=? WHERE id=?',
                      (dumps(content) if changes else row['content'], int(archive), stamp, patch['id']))
            after = store._record(c.execute(RECORD_SELECT + ' WHERE r.id=?', (patch['id'],)).fetchone())
            action = 'product_cleanup_archive' if archive != row['archived'] else 'product_details_enrich'
            store._audit(c, 'records', patch['id'], action, 'system:brand-refresh', before, after)
        result = {'status': 'imported', 'batch': marker, 'updated': len(updates),
                  'archived': archived, 'enriched': enriched}
        c.execute('INSERT INTO admin_migrations VALUES(?,?)', (marker, stamp))
        store._audit(c, 'imports', marker, 'brand_refresh', 'system:brand-refresh', None, result)
        return result
