"""One-time, idempotent import of the September 24 internal source catalogue.

Run only against a stopped application after taking a consistent state backup.
Existing administrator edits are never overwritten.
"""
import argparse
from collections import Counter
import json
from pathlib import Path
import sqlite3

from admin_store import dumps, now


def import_batch(state, private):
    state = Path(state)
    private = Path(private)
    data = json.loads((private / 'materials-20260924.json').read_text())
    marker = data['batch']
    records = data['records']
    ids = [r['id'] for r in records]
    if len(ids) != len(set(ids)):
        raise ValueError('素材编号重复，导入已中止')
    if any(r.get('provenance', {}).get('batch') != marker for r in records):
        raise ValueError('素材批次来源不一致')
    for record in records:
        for image in record.get('images', []):
            path = image['path']
            target = (private / path).resolve()
            if not target.is_relative_to((private / 'media').resolve()) or not target.is_file():
                raise ValueError('缺少来源图片：' + path)
    database = state / 'catalog.sqlite'
    if not database.is_file():
        raise ValueError('请先初始化目标站点的数据库')
    connection = sqlite3.connect(database, timeout=30)
    try:
        connection.execute('BEGIN IMMEDIATE')
        if connection.execute('SELECT 1 FROM admin_migrations WHERE name=?',
                              (marker,)).fetchone():
            connection.rollback()
            return {'status': 'already_imported', 'batch': marker}
        existing = set(row[0] for row in connection.execute('SELECT id FROM admin_records'))
        collisions = existing.intersection(ids)
        if collisions:
            raise ValueError(f'发现 {len(collisions)} 个同名编号，导入已中止')
        stamp = now()
        connection.executemany(
            'INSERT INTO admin_records(id,content,original,version,archived,created,updated) '
            'VALUES(?,?,?,?,?,?,?)',
            [(r['id'], dumps(r), dumps(r), 1, 0, stamp, stamp) for r in records])
        counts = dict(Counter(r['kind'] for r in records))
        connection.execute('INSERT INTO admin_migrations(name,created) VALUES(?,?)',
                           (marker, stamp))
        connection.execute(
            'INSERT INTO admin_audit(resource,entity_id,action,actor,before_json,after_json,created) '
            'VALUES(?,?,?,?,?,?,?)',
            ('imports', marker, 'import', 'system', 'null',
             dumps({'records': len(records), 'kinds': counts}), stamp))
        connection.commit()
        return {'status': 'imported', 'batch': marker, 'records': len(records),
                'kinds': counts}
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--state', required=True)
    parser.add_argument('--private', required=True)
    args = parser.parse_args()
    print(json.dumps(import_batch(args.state, args.private), ensure_ascii=False))
