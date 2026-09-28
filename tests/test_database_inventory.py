import hashlib
import importlib.util
import json
from pathlib import Path
import sqlite3
import tempfile
import unittest

spec = importlib.util.spec_from_file_location('inventory', Path(__file__).resolve().parents[1]/'scripts/database_inventory.py')
inventory = importlib.util.module_from_spec(spec)
spec.loader.exec_module(inventory)


class DatabaseInventoryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name)/'带 空格 ? #.sqlite'

    def create(self):
        with sqlite3.connect(self.path) as connection:
            connection.executescript('''
                CREATE TABLE admin_records(id TEXT PRIMARY KEY, content TEXT, archived INTEGER);
                CREATE TABLE admin_product_codes(record_id TEXT REFERENCES admin_records(id));
                CREATE TABLE accounts(password_hash TEXT, csrf TEXT);
            ''')
            connection.execute('INSERT INTO accounts VALUES(?,?)', ('secret-hash-fixture', 'secret-csrf-fixture'))
            connection.executemany('INSERT INTO admin_records VALUES(?,?,0)', [
                ('one', json.dumps({'kind': 'package', 'supplier': 'private-supplier'})),
                ('page', json.dumps({'kind': 'source_page'})),
            ])
            connection.execute("INSERT INTO admin_product_codes VALUES('one')")

    def test_inventory_never_outputs_row_values_and_preserves_database(self):
        self.create()
        before = hashlib.sha256(self.path.read_bytes()).hexdigest()
        result = inventory.inspect_database(self.path)
        self.assertEqual(result['status'], 'ok')
        self.assertEqual(result['tables']['accounts']['rows'], 1)
        self.assertEqual(result['catalog_summary']['package_records_without_code'], 0)
        self.assertEqual(result['catalog_summary']['other_records_without_code'], 1)
        for private in ['secret-hash-fixture', 'secret-csrf-fixture', 'private-supplier']:
            self.assertNotIn(private, json.dumps(result))
        self.assertEqual(hashlib.sha256(self.path.read_bytes()).hexdigest(), before)

    def test_readonly_connection_rejects_writes(self):
        self.create()
        connection = inventory.open_readonly(self.path)
        try:
            with self.assertRaises(sqlite3.OperationalError):
                connection.execute('DELETE FROM accounts')
        finally:
            connection.close()

    def test_missing_database_does_not_get_created(self):
        self.assertEqual(inventory.inspect_database(self.path), {'status': 'missing'})
        self.assertFalse(self.path.exists())

    def test_detects_missing_product_codes_and_invalid_records(self):
        self.create()
        with sqlite3.connect(self.path) as connection:
            connection.execute('DELETE FROM admin_product_codes')
            connection.execute("INSERT INTO admin_records VALUES('bad','not-json',0)")
        result = inventory.inspect_database(self.path)
        self.assertEqual(result['status'], 'needs_review')
        self.assertEqual(result['catalog_summary']['invalid_record_json'], 1)
        self.assertEqual(result['catalog_summary']['package_records_without_code'], 1)

    def test_foreign_keys_and_quoted_table_names(self):
        self.create()
        with sqlite3.connect(self.path) as connection:
            connection.execute("INSERT INTO admin_product_codes VALUES('missing')")
            connection.execute('CREATE TABLE "odd""table"(value TEXT)')
        result = inventory.inspect_database(self.path)
        self.assertEqual(result['status'], 'needs_review')
        self.assertEqual(result['foreign_key_violation_count'], 1)
        self.assertIn('odd"table', result['tables'])

    def test_corrupt_database_report_does_not_echo_contents(self):
        path = Path(self.temp.name)/'catalog.sqlite'
        path.write_bytes(b'private broken database contents')
        result = inventory.inspect_state(self.temp.name)
        self.assertEqual(result['databases']['catalog.sqlite']['status'], 'unreadable')
        self.assertNotIn('private broken', json.dumps(result))


if __name__ == '__main__':
    unittest.main()
