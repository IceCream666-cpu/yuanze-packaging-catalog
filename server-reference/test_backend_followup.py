"""Regression checks using synthetic catalog rows and an isolated HTTP server."""
import base64
from contextlib import contextmanager
import http.client
import json
from pathlib import Path
import tempfile
import threading
import time
from types import SimpleNamespace
import unittest
from unittest.mock import patch

import server


class BackendFollowup(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        root = Path(self.temp.name)
        state, private = root / 'state', root / 'private'
        state.mkdir()
        private.mkdir()
        bootstrap = {'username': 'fixture-admin', 'salt': '00' * 16,
                     'hash': '00' * 32, 'iterations': 100000}
        (state / 'admin-bootstrap.json').write_text(json.dumps(bootstrap))
        self.ids = ['FIXTURE-%04d' % i for i in range(1000)]
        base = {'meta': {}, 'records': [
            {'id': rid, 'name': 'Synthetic bottle', 'kind': 'package',
             'source': {'workbook': 'synthetic.csv', 'sheet': '', 'row': offset + 2}}
            for offset, rid in enumerate(self.ids)]}
        store = server.AdminStore(state, private, {}, base)
        session = {'username': 'fixture-admin', 'csrf': 'fixture-csrf',
                   'expires': time.time() + 3600, 'auth_version': 1, 'role': 'admin'}
        sessions = server.SessionStore(state)
        self.token = 'fixture-token-' + 'a' * 32
        sessions.create(self.token, session)
        fixture = patch.multiple(server, STATE=state, STORE=store, LOCAL=False,
                                 IMAGE_SEARCH=SimpleNamespace(refresh=lambda: None),
                                 SESSION_STORE=sessions, IMPORTS={},
                                 LOCK=threading.Lock(), IMPORT_GATE=threading.Lock())
        fixture.start()
        self.addCleanup(fixture.stop)

        class QuietHandler(server.Handler):
            def log_message(self, *args):
                pass
            def log_request(self, *args):
                pass

        self.httpd = server.ThreadingHTTPServer(('127.0.0.1', 0), QuietHandler)
        self.thread = threading.Thread(target=self.httpd.serve_forever, daemon=True)
        self.thread.start()
        self.addCleanup(self.stop_http)
        self.host = '127.0.0.1:%d' % self.httpd.server_port

    def stop_http(self):
        self.httpd.shutdown()
        self.httpd.server_close()
        self.thread.join()

    def req(self, path, data=None):
        conn = http.client.HTTPConnection(self.host, timeout=5)
        headers = {'Origin': 'https://' + self.host,
                   'Cookie': 'yz_session=' + self.token, 'X-CSRF-Token': 'fixture-csrf'}
        conn.request('GET' if data is None else 'POST', path,
                     body=None if data is None else json.dumps(data), headers=headers)
        response = conn.getresponse()
        status, body = response.status, json.loads(response.read())
        conn.close()
        return status, body

    def preview(self, contents):
        payload = {'filename': 'synthetic.csv',
                   'content': base64.b64encode(contents.encode()).decode()}
        return self.req('/api/admin/import/preview', payload)

    def test_thousand_favorites_use_only_three_batched_id_queries(self):
        statements = []
        original = server.db

        @contextmanager
        def traced_db():
            with original() as conn:
                conn.set_trace_callback(statements.append)
                yield conn

        with patch.object(server, 'db', traced_db):
            status, body = self.req('/api/preferences', {'favorites': self.ids})
        self.assertEqual(status, 200, body)
        lookups = [sql for sql in statements if sql.startswith('SELECT id FROM admin_records')]
        self.assertEqual(len(lookups), 3, '1000 ids must need three SQL batches, not repeated scans')
        self.assertEqual(self.req('/api/preferences')[1]['favorites'], self.ids)

    def test_favorites_reject_archived_unknown_and_over_limit_without_overwrite(self):
        self.assertEqual(self.req('/api/preferences', {'favorites': [self.ids[0]]})[0], 200)
        server.STORE.mutate('records', 'archive', {'id': self.ids[1], 'version': 1}, 'fixture-admin')
        for invalid in ([self.ids[1]], ['ABSENT'], self.ids + ['EXTRA']):
            self.assertEqual(self.req('/api/preferences', {'favorites': invalid})[0], 400)
        self.assertEqual(self.req('/api/preferences')[1]['favorites'], [self.ids[0]])

    def test_import_duplicate_running_commit_is_rejected_and_sessions_continue(self):
        _, preview = self.preview('记录编号,版本,名称\nFIXTURE-0000,1,Updated\n')
        self.assertTrue(preview['valid'], preview)
        entered, release = threading.Event(), threading.Event()
        original = server.STORE.bulk_save
        result = []

        def slow(rows, actor):
            entered.set()
            if not release.wait(5):
                raise RuntimeError('test did not release import')
            return original(rows, actor)

        with patch.object(server.STORE, 'bulk_save', side_effect=slow) as write:
            worker = threading.Thread(target=lambda: result.append(self.req(
                '/api/admin/import/commit', {'token': preview['token']})))
            worker.start()
            try:
                self.assertTrue(entered.wait(5))
                self.assertEqual(self.req('/api/admin/import/commit', {'token': preview['token']})[0], 429)
                self.assertEqual(self.req('/api/session')[0], 200)
            finally:
                release.set()
                worker.join(5)
            self.assertEqual(write.call_count, 1)
        self.assertEqual(result[0][0], 200, result)
        self.assertEqual(self.req('/api/admin/import/commit', {'token': preview['token']})[0], 400)
        self.assertEqual(server.STORE.read_admin('records', 'FIXTURE-0000')['version'], 2)

    def test_import_failed_transaction_rolls_back_and_same_token_can_retry(self):
        _, preview = self.preview('记录编号,版本,名称\nNEW-ROW,,New\nFIXTURE-0000,1,Updated\n')
        self.assertTrue(preview['valid'], preview)
        original = server.STORE._save_record

        def fail_second(conn, action, data, actor):
            if data['id'] == 'FIXTURE-0000':
                raise RuntimeError('synthetic interruption during transaction')
            return original(conn, action, data, actor)

        with patch.object(server.STORE, '_save_record', side_effect=fail_second):
            self.assertEqual(self.req('/api/admin/import/commit', {'token': preview['token']})[0], 500)
        self.assertNotIn('NEW-ROW', server.active_ids(['NEW-ROW']))
        self.assertEqual(server.STORE.read_admin('records', 'FIXTURE-0000')['version'], 1)
        self.assertEqual(server.IMPORTS[preview['token']]['state'], 'preview')
        self.assertEqual(self.req('/api/admin/import/commit', {'token': preview['token']})[0], 200)
        self.assertIn('NEW-ROW', server.active_ids(['NEW-ROW']))

    def test_import_store_errors_report_actual_spreadsheet_row(self):
        status, preview = self.preview('记录编号,版本,名称\nNEW-ROW,,New\nFIXTURE-0000,,Old update\n')
        self.assertEqual(status, 200)
        self.assertFalse(preview['valid'])
        self.assertEqual(preview['errors'][0]['row'], 3)
        status, preview = self.preview('记录编号,版本,名称\n\nNEW-ROW,,New\nFIXTURE-0000,,Old update\n')
        self.assertEqual(status, 200)
        self.assertFalse(preview['valid'])
        self.assertEqual(preview['errors'][0]['row'], 4)

    def test_import_all_invalid_rows_preserve_specific_cell_errors(self):
        status, preview = self.preview('记录编号,名称,容量ml\nBAD-1,Invalid,-1\nBAD-2,Invalid,not-a-number\n')
        self.assertEqual(status, 200, preview)
        self.assertFalse(preview['valid'])
        self.assertIsNone(preview['token'])
        self.assertEqual(preview['rows'], [])
        self.assertEqual([error['row'] for error in preview['errors']], [2, 3])
        self.assertIn('容量', preview['errors'][0]['message'])

    def test_import_mixed_parser_and_store_errors_keep_original_rows(self):
        status, preview = self.preview(
            '记录编号,版本,名称,容量ml\nBAD-1,,Invalid,-1\n\nFIXTURE-0000,,Old update,50\n')
        self.assertEqual(status, 200, preview)
        self.assertFalse(preview['valid'])
        self.assertIsNone(preview['token'])
        self.assertEqual([error['row'] for error in preview['errors']], [2, 4])


if __name__ == '__main__':
    unittest.main()
