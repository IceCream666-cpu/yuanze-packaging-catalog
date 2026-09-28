"""Reviewed image-only migration. Stop the web service and back up state first."""
import argparse
from copy import deepcopy
import hashlib
import json
from pathlib import Path
from admin_store import AdminStore, ConflictError, RECORD_SELECT, dumps, now


def apply_batch(store, batch):
    marker=batch['batch'];updates=batch['updates'];new=batch['newRecords']
    ids=[r['id'] for r in updates+new]
    if len(ids)!=len(set(ids)):
        raise ValueError('Duplicate migration record IDs')
    with store.connection(write=True) as c:
        if c.execute('SELECT 1 FROM admin_migrations WHERE name=?',(marker,)).fetchone():
            return {'status':'already_imported','batch':marker}
        # Preflight the entire batch before any mutation. Concurrent admin edits
        # cause a conflict rather than silently replacing their images or fields.
        for patch in updates:
            row=c.execute(RECORD_SELECT+' WHERE r.id=?',(patch['id'],)).fetchone()
            if (not row or row['version']!=patch['expectedVersion'] or
                hashlib.sha256(row['content'].encode()).hexdigest()!=patch['expectedContentSha256']):
                raise ConflictError('Product changed since image review: '+patch['id'])
        for record in new:
            if c.execute('SELECT 1 FROM admin_records WHERE id=?',(record['id'],)).fetchone():
                raise ConflictError('New product ID already exists: '+record['id'])
        stamp=now()
        for patch in updates:
            row=c.execute(RECORD_SELECT+' WHERE r.id=?',(patch['id'],)).fetchone()
            before=store._record(row);record=json.loads(row['content'])
            # Validate trusted paths without normalizing any commercial fields.
            normalized=store._images(c,patch['images'])
            for supplied,checked in zip(patch['images'],normalized):
                if supplied.get('imageScope')!=checked.get('imageScope'):
                    raise ValueError('Untrusted image scope: '+supplied['path'])
            record['images']=deepcopy(patch['images'])
            c.execute('UPDATE admin_records SET content=?,version=version+1,updated=? WHERE id=?',
                      (dumps(record),stamp,record['id']))
            after=store._record(c.execute(RECORD_SELECT+' WHERE r.id=?',(record['id'],)).fetchone())
            if not c.execute('SELECT 1 FROM admin_audit WHERE resource=? AND entity_id=?',('records',record['id'])).fetchone():
                store._audit(c,'records',record['id'],'initial','system:image-review',None,before)
            store._audit(c,'records',record['id'],'image_review','system:image-review',before,after)
        for source in new:
            # New curated source provenance is retained, and all editable fields
            # pass the same validation as an administrator save.
            record=store._normalized_record(c,{'record':source},source)
            record['id']=source['id']
            c.execute('INSERT INTO admin_records VALUES(?,?,?,?,?,?,?)',
                      (record['id'],dumps(record),dumps(record),1,0,stamp,stamp))
            store._ensure_product_code(c,record['id'],'package')
            after=store._record(c.execute(RECORD_SELECT+' WHERE r.id=?',(record['id'],)).fetchone())
            store._audit(c,'records',record['id'],'image_review_create','system:image-review',None,after)
        c.execute('INSERT INTO admin_migrations VALUES(?,?)',(marker,stamp))
        result={'status':'imported','batch':marker,'updated':len(updates),'created':len(new)}
        store._audit(c,'imports',marker,'image_review','system:image-review',None,result)
    return result


if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--state',required=True);parser.add_argument('--private',required=True);parser.add_argument('--batch',required=True)
    args=parser.parse_args()
    if not (Path(args.state)/'catalog.sqlite').is_file():raise ValueError('Existing catalogue database required')
    store=AdminStore(args.state,args.private,{},json.loads((Path(args.private)/'catalog.json').read_text()))
    print(json.dumps(apply_batch(store,json.loads(Path(args.batch).read_text())),ensure_ascii=False))
