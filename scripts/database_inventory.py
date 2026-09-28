#!/usr/bin/env python3
"""Read-only database inventory. Emits structure/counts, never business rows or secrets."""
import argparse
import json
from pathlib import Path
import sqlite3

DATABASES = ('catalog.sqlite', 'admin_uploads.sqlite', 'auth-sessions/sessions.sqlite')


def identifier(value):
    return '"' + value.replace('"', '""') + '"'


def open_readonly(path):
    connection = sqlite3.connect(Path(path).resolve().as_uri() + '?mode=ro', uri=True, timeout=5)
    connection.execute('PRAGMA query_only=ON')
    return connection


def inspect_database(path):
    path = Path(path)
    if not path.is_file():
        return {'status': 'missing'}
    connection = open_readonly(path)
    # Bound costly/corrupt queries while preserving the live database unchanged.
    remaining = 100000
    def budget():
        nonlocal remaining
        remaining -= 1
        return int(remaining <= 0)
    connection.set_progress_handler(budget, 1000)
    try:
        connection.execute('BEGIN')
        checks = connection.execute('PRAGMA quick_check').fetchall()
        violations = connection.execute('PRAGMA foreign_key_check').fetchall()
        tables = {}
        names = [row[0] for row in connection.execute(
            "SELECT name FROM sqlite_schema WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name")]
        for name in names:
            quoted = identifier(name)
            tables[name] = {
                'rows': connection.execute('SELECT COUNT(*) FROM ' + quoted).fetchone()[0],
                'columns': [{'name': row[1], 'type': row[2], 'not_null': bool(row[3]), 'primary_key': row[5]}
                            for row in connection.execute('PRAGMA table_info(' + quoted + ')')],
                'indexes': [{'name': row[1], 'unique': bool(row[2])}
                            for row in connection.execute('PRAGMA index_list(' + quoted + ')')],
            }
        result = {
            'status': 'ok' if checks == [('ok',)] and not violations else 'needs_review',
            'main_file_bytes': path.stat().st_size,
            'quick_check_ok': checks == [('ok',)],
            'foreign_key_violation_count': len(violations),
            'tables': tables,
        }
        if {'admin_records', 'admin_product_codes'} <= set(names):
            summary = {'active_records': 0, 'archived_records': 0, 'invalid_record_json': 0,
                       'package_records_without_code': 0, 'other_records_without_code': 0}
            for content, archived, has_code in connection.execute('''
                SELECT r.content, r.archived, EXISTS(
                    SELECT 1 FROM admin_product_codes p WHERE p.record_id=r.id)
                FROM admin_records r'''):
                summary['archived_records' if archived else 'active_records'] += 1
                try:
                    record = json.loads(content)
                    if not isinstance(record, dict):
                        raise ValueError('Record must be an object')
                except (ValueError, TypeError):
                    summary['invalid_record_json'] += 1
                    continue
                if not has_code:
                    key = 'package_records_without_code' if record.get('kind') == 'package' else 'other_records_without_code'
                    summary[key] += 1
            result['catalog_summary'] = summary
            if summary['invalid_record_json'] or summary['package_records_without_code']:
                result['status'] = 'needs_review'
        return result
    finally:
        connection.rollback()
        connection.close()


def inspect_state(state):
    result = {}
    for relative in DATABASES:
        try:
            result[relative] = inspect_database(Path(state) / relative)
        except (sqlite3.Error, OSError):
            # Error text can contain filesystem paths or data. Return a safe status.
            result[relative] = {'status': 'unreadable'}
    return {'read_only': True, 'databases': result}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--state', type=Path, required=True, help='State directory containing the three SQLite databases')
    args = parser.parse_args()
    result = inspect_state(args.state)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if all(db['status'] == 'ok' for db in result['databases'].values()) else 1


if __name__ == '__main__':
    raise SystemExit(main())
