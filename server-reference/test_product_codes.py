"""Stable display numbering does not replace IDs or mutate source evidence."""
from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
import base64
import hashlib
import json
from pathlib import Path
import sqlite3
import tempfile
import unittest

from admin_imports import parse_import
from admin_store import AdminStore, AdminError, ConflictError, dumps


def seed_admin(state):
    salt = 'ef' * 16
    state.mkdir(parents=True, exist_ok=True)
    (state / 'admin-bootstrap.json').write_text(json.dumps({
        'username': 'number-admin', 'salt': salt, 'iterations': 100000,
        'hash': hashlib.pbkdf2_hmac('sha256', b'fixture-not-live-password', bytes.fromhex(salt), 100000).hex(),
    }))


def legacy_database(state, count=4):
    """Simulate existing deployed records, including archive and audit history."""
    with sqlite3.connect(state / 'catalog.sqlite') as c:
        c.executescript('''
            CREATE TABLE admin_records(id TEXT PRIMARY KEY,content TEXT NOT NULL,original TEXT NOT NULL,
                version INTEGER NOT NULL,archived INTEGER NOT NULL DEFAULT 0,created TEXT NOT NULL,updated TEXT NOT NULL);
            CREATE TABLE admin_migrations(name TEXT PRIMARY KEY,created TEXT NOT NULL);
            INSERT INTO admin_migrations VALUES('catalog-v1','original-date');
        ''')
        for index in range(count):
            data = {'id': f'SOURCE-{index}', 'kind': 'package' if index < 2 else 'source_page',
                    'name': f'旧产品{index}', 'source': {'workbook': 'source.pdf', 'row': index + 1},
                    'rawCells': {'A': f'原始{index}'}, 'images': []}
            c.execute('INSERT INTO admin_records VALUES(?,?,?,?,?,?,?)',
                      (data['id'], dumps(data), dumps(data), index + 3, index % 2,
                       'original-created', 'original-updated'))


class ProductCodeTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.state = Path(self.temp.name) / 'state'
        self.private = Path(self.temp.name) / 'private'
        self.private.mkdir()
        seed_admin(self.state)
        legacy_database(self.state)
        with sqlite3.connect(self.state / 'catalog.sqlite') as c:
            self.original_rows = c.execute('SELECT * FROM admin_records ORDER BY rowid').fetchall()
        self.store = AdminStore(self.state, self.private, {}, {'meta': {}, 'records': []})

    def tearDown(self):
        self.temp.cleanup()

    def mutate(self, data, action='save'):
        return self.store.mutate('records', action, data, 'number-admin')

    def test_migration_includes_archived_and_preserves_every_record_column(self):
        records = {r['id']: r for r in self.store.catalog(include_archived=True)['records']}
        self.assertEqual(records['SOURCE-0']['productCode'], 'YZ-BC-000001')
        self.assertEqual(records['SOURCE-1']['productCode'], 'YZ-BC-000002')
        self.assertTrue(records['SOURCE-1']['archived'])
        self.assertIsNone(records['SOURCE-2']['productCode'])
        with self.store.connection() as c:
            after = [tuple(r) for r in c.execute('SELECT * FROM admin_records ORDER BY rowid')]
            self.assertEqual(after, self.original_rows)
            self.assertEqual(c.execute('SELECT count(*) FROM admin_audit').fetchone()[0], 0)
        self.assertEqual(self.store.product_code_migration, {'assigned': 2, 'total': 2, 'nextNumber': 3})
        again = AdminStore(self.state, self.private, {}, {'records': []})
        self.assertEqual(again.product_code_migration, {'assigned': 0, 'total': 2, 'nextNumber': 3})
        self.assertEqual(again.read_admin('records', 'SOURCE-0')['productCode'], 'YZ-BC-000001')
        exported = again.export()
        self.assertEqual(next(r for r in exported['records'] if r['id'] == 'SOURCE-1')['productCode'], 'YZ-BC-000002')
        self.assertNotIn('productCode', exported['originalRecords']['SOURCE-1'])

    def test_edit_archive_kind_change_and_history_restore_never_renumber(self):
        current = self.store.read_admin('records', 'SOURCE-0')
        code = current['productCode']
        updated = self.mutate({'id': current['id'], 'version': current['version'], 'productCode': code,
                               'name': '改名', 'kind': 'source_page'})
        self.assertEqual(updated['productCode'], code)
        archived = self.mutate({'id': current['id'], 'version': updated['version']}, 'archive')
        self.assertEqual(archived['productCode'], code)
        initial = next(a for a in self.store.read_admin('audit', id=current['id']) if a['action'] == 'initial')
        restored = self.mutate({'id': current['id'], 'version': archived['version'], 'revision': initial['id']}, 'restore')
        self.assertEqual(restored['productCode'], code)
        self.assertEqual(restored['id'], current['id'])
        self.assertTrue(restored['archived'])
        self.assertEqual(restored['name'], current['name'])
        live = self.mutate({'id': current['id'], 'version': restored['version']}, 'unarchive')
        self.assertEqual(live['productCode'], code)

    def test_first_package_conversion_and_pre_number_history_restore(self):
        initial = self.store.read_admin('records', 'SOURCE-2')
        revised = self.mutate({'id': initial['id'], 'version': initial['version'], 'name': '保留原类型'})
        history = next(a for a in self.store.read_admin('audit', id=initial['id']) if a['action'] == 'save')
        self.assertIsNone(history['after']['productCode'])
        assigned = self.mutate({'id': initial['id'], 'version': revised['version'], 'kind': 'package'})
        self.assertEqual(assigned['productCode'], 'YZ-BC-000003')
        restored = self.mutate({'id': initial['id'], 'version': assigned['version'], 'revision': history['id']}, 'restore')
        self.assertEqual(restored['kind'], 'source_page')
        self.assertEqual(restored['productCode'], 'YZ-BC-000003')
        self.assertEqual(self.store.read_admin('records', 'SOURCE-0')['productCode'], 'YZ-BC-000001')

    def test_reject_code_tampering_on_create_update_archive_restore_and_preview(self):
        record = self.store.read_admin('records', 'SOURCE-0')
        for action in ('save', 'archive', 'unarchive', 'restore'):
            for value in ('YZ-BC-000999', '', None, 1):
                with self.subTest(action=action, value=value), self.assertRaises(AdminError):
                    self.mutate({'id': record['id'], 'version': record['version'], 'productCode': value}, action)
        with self.assertRaises(AdminError):
            self.mutate({'version': 0, 'name': '新瓶', 'productCode': 'YZ-BC-000001'})
        with self.assertRaises(AdminError):
            self.mutate({'id': record['id'], 'version': record['version'], 'productCode': 'YZ-BC-000002',
                         'record': {'name': '偷改外层', 'productCode': record['productCode']}})
        preview = self.store.bulk_preview([{'id': record['id'], 'name': record['name'], 'productCode': 'wrong'}])
        self.assertFalse(preview['valid'])
        self.assertEqual(self.store.read_admin('records', record['id'])['version'], record['version'])

    def test_import_roundtrip_assigns_only_on_commit_and_rolls_back_allocation(self):
        csv = '记录编号,产品编号,版本,名称\nSOURCE-0,YZ-BC-000001,3,导入更新\n,,,新瓶\n'
        parsed = parse_import({'filename': 'codes.csv', 'content': base64.b64encode(csv.encode()).decode()})
        preview = self.store.bulk_preview(parsed['rows'])
        self.assertTrue(preview['valid'])
        self.assertEqual(preview['rows'][0]['record']['productCode'], 'YZ-BC-000001')
        self.assertIsNone(preview['rows'][1]['record']['productCode'])
        with self.store.connection() as c:
            self.assertEqual(c.execute('SELECT next_number FROM admin_product_code_sequence').fetchone()[0], 3)
        # First new row tentatively allocates code 3; later stale row must undo it.
        stale = deepcopy(preview['rows'][0])
        stale['version'] = -1
        with self.assertRaises(ConflictError):
            self.store.bulk_save([preview['rows'][1], stale], 'number-admin')
        with self.store.connection() as c:
            self.assertEqual(c.execute('SELECT next_number FROM admin_product_code_sequence').fetchone()[0], 3)
            self.assertEqual(c.execute('SELECT count(*) FROM admin_product_codes').fetchone()[0], 2)
        saved = self.store.bulk_save(preview['rows'], 'number-admin')['records']
        self.assertEqual(saved[0]['productCode'], 'YZ-BC-000001')
        self.assertEqual(saved[1]['productCode'], 'YZ-BC-000003')

    def test_concurrent_creation_allocates_unique_codes_and_database_enforces_immutability(self):
        def create(index):
            return self.mutate({'id': f'NEW-{index}', 'version': 0, 'name': f'瓶{index}'})
        with ThreadPoolExecutor(max_workers=4) as pool:
            records = list(pool.map(create, range(12)))
        self.assertEqual(len({r['productCode'] for r in records}), 12)
        self.assertEqual(sorted(r['productCode'] for r in records), [f'YZ-BC-{i:06d}' for i in range(3, 15)])
        for statement in ("UPDATE admin_product_codes SET product_code='YZ-BC-000999' WHERE number=1",
                          'DELETE FROM admin_product_codes WHERE number=1'):
            with self.assertRaises(sqlite3.IntegrityError), self.store.connection(True) as c:
                c.execute(statement)

    def test_linear_bulk_migration_at_current_deployment_scale(self):
        large_state = Path(self.temp.name) / 'large-state'
        large_state.mkdir()
        with sqlite3.connect(large_state / 'catalog.sqlite') as c:
            c.executescript('''CREATE TABLE admin_records(id TEXT PRIMARY KEY,content TEXT NOT NULL,original TEXT NOT NULL,
                version INTEGER NOT NULL,archived INTEGER NOT NULL,created TEXT NOT NULL,updated TEXT NOT NULL);
                CREATE TABLE admin_migrations(name TEXT PRIMARY KEY,created TEXT NOT NULL);
                INSERT INTO admin_migrations VALUES('catalog-v1','old');''')
            c.executemany('INSERT INTO admin_records VALUES(?,?,?,?,?,?,?)',
                          ((f'ROW-{i}', dumps({'id': f'ROW-{i}', 'name': '样式', 'kind': 'package' if i < 8001 else 'source_page'}),
                            '{"original":true}', 7, i % 2, 'old', 'old') for i in range(11006)))
        store = AdminStore(large_state, self.private, {}, {'records': []})
        self.assertEqual(store.product_code_migration, {'assigned': 8001, 'total': 8001, 'nextNumber': 8002})
        self.assertEqual(store.read_admin('records', 'ROW-8000')['productCode'], 'YZ-BC-008001')
        self.assertIsNone(store.read_admin('records', 'ROW-8001')['productCode'])
        with store.connection() as c:
            self.assertEqual(c.execute('SELECT count(*) FROM admin_records WHERE version=7 AND updated=?', ('old',)).fetchone()[0], 11006)
            self.assertEqual(c.execute('SELECT count(*) FROM admin_records WHERE original=?', ('{"original":true}',)).fetchone()[0], 11006)


if __name__ == '__main__':
    unittest.main()
