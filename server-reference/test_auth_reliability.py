"""Authentication regressions using private, synthetic databases only."""
from contextlib import contextmanager, redirect_stdout
import hashlib
import io
import json
import secrets
import sqlite3
import tempfile
import threading
import time
import unittest
from unittest.mock import patch

from auth_sessions import SessionStore, SessionLimit
import test_http
from test_server import server


class DurableSessions(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.store = SessionStore(self.temp.name)

    def issue(self, store=None, role='employee', username='employee', expires=None):
        token = secrets.token_urlsafe(32)
        session = dict(username=username, role=role, auth_version=1,
                       csrf=secrets.token_urlsafe(24), expires=expires or time.time() + 28800)
        (store or self.store).create(token, session)
        return token, session

    def test_new_instance_reads_hashed_sessions_from_private_files(self):
        token, session = self.issue()
        independent = SessionStore(self.temp.name)
        self.assertIsNot(independent, self.store)
        self.assertEqual(independent.get(token)[0], session)
        with independent.connection() as conn:
            saved = dict(conn.execute('SELECT * FROM sessions').fetchone())
        self.assertEqual(saved.pop('token_hash'), hashlib.sha256(token.encode()).hexdigest())
        self.assertNotIn(token, json.dumps(saved))
        self.assertEqual(self.store.path.stat().st_mode & 0o777, 0o600)
        self.assertEqual(self.store.path.parent.stat().st_mode & 0o777, 0o700)

    def test_500_employee_logins_do_not_evict_first_device(self):
        store = SessionStore(self.temp.name, employee_limit=500)
        first, _ = self.issue(store)
        for _ in range(499):
            self.issue(store)
        with self.assertRaises(SessionLimit):
            self.issue(store)
        self.assertEqual(store.get(first)[1], 'valid_session')
        store.delete(first)
        new, _ = self.issue(store)
        self.assertEqual(store.get(new)[1], 'valid_session')

    def test_unlimited_employees_exceed_500_and_survive_new_instance(self):
        self.assertEqual(self.store.limits['employee'], 0)
        first, first_session = self.issue()
        for _ in range(500):
            self.issue()
        independent = SessionStore(self.temp.name, employee_limit=0)
        last, last_session = self.issue(independent)
        self.assertEqual(independent.get(first)[0], first_session)
        self.assertEqual(independent.get(last)[0], last_session)
        with independent.connection() as conn:
            self.assertEqual(conn.execute('SELECT COUNT(*) FROM sessions').fetchone()[0], 502)

    def test_unlimited_login_does_not_count_employee_sessions(self):
        queries = []
        original = self.store.connection

        @contextmanager
        def traced_connection():
            with original() as conn:
                conn.set_trace_callback(queries.append)
                yield conn

        with patch.object(self.store, 'connection', traced_connection):
            self.issue()
        self.assertFalse(any('COUNT(' in query.upper() for query in queries))

    def test_invalid_limits_are_rejected_and_only_employees_allow_zero(self):
        for employee_limit in (-1, True, False, 1.0, '0', None, 10001):
            with self.subTest(employee_limit=employee_limit), self.assertRaises(ValueError):
                SessionStore(self.temp.name, employee_limit=employee_limit)
        for admin_limit in (0, -1, True, False, 1.0, '20', None, 10001):
            with self.subTest(admin_limit=admin_limit), self.assertRaises(ValueError):
                SessionStore(self.temp.name, admin_limit=admin_limit)

    def test_admin_capacity_is_20_without_evicting_existing_sessions(self):
        first, _ = self.issue(role='admin', username='admin')
        for _ in range(19):
            self.issue(role='admin', username='admin')
        with self.assertRaises(SessionLimit):
            self.issue(role='admin', username='admin')
        self.assertIsNotNone(self.store.get(first)[0])
        self.assertIsNotNone(self.issue()[0])

    def test_capacity_is_atomic_under_simultaneous_logins(self):
        store = SessionStore(self.temp.name, employee_limit=2)
        barrier = threading.Barrier(8)
        results = []

        def worker():
            barrier.wait()
            try:
                self.issue(store)
                results.append('ok')
            except SessionLimit:
                results.append('full')

        threads = [threading.Thread(target=worker) for _ in range(8)]
        for thread in threads: thread.start()
        for thread in threads: thread.join(5)
        self.assertEqual(sorted(results), ['full'] * 6 + ['ok'] * 2)

    def test_expiry_logout_and_password_version_survive_new_instance(self):
        expired, _ = self.issue(expires=time.time() - 1)
        self.assertIsNone(self.store.get(expired)[0])
        token, session = self.issue()
        self.store.delete(token)
        self.assertIsNone(SessionStore(self.temp.name).get(token)[0])
        token, session = self.issue()
        session['auth_version'] = 2
        replacement = secrets.token_urlsafe(32)
        self.store.create(replacement, session)
        self.assertIsNone(self.store.get(token)[0])
        self.assertEqual(self.store.get(replacement)[0]['auth_version'], 2)


class LoginReliability(unittest.TestCase):
    setUp = test_http.HTTP.setUp
    tearDown = test_http.HTTP.tearDown
    req = test_http.HTTP.req

    def login(self):
        status, headers, body = self.req('/api/login',
            {'username': 'review', 'password': self.password})
        self.assertEqual(status, 200, body)
        self.cookie = headers['Set-Cookie'].split(';')[0]
        self.csrf = self.req('/api/session')[2]['csrf']

    def test_fresh_service_and_session_store_accept_existing_cookie(self):
        self.login()
        cookie, csrf = self.cookie, self.csrf
        self.srv.shutdown(); self.srv.server_close(); self.thread.join()
        old_store = server.SESSION_STORE
        server.initialize()
        self.assertIsNot(server.SESSION_STORE, old_store)
        self.srv = server.ThreadingHTTPServer(('127.0.0.1', 0), server.Handler)
        self.thread = threading.Thread(target=self.srv.serve_forever, daemon=True)
        self.thread.start()
        self.host = '127.0.0.1:' + str(self.srv.server_port)
        status, _, session = self.req('/api/session')
        self.assertEqual(status, 200)
        self.assertEqual(session['csrf'], csrf)
        self.assertEqual(self.cookie, cookie)
        self.assertEqual(self.req('/api/preferences', {'favorites': []})[0], 200)

    def test_disabled_and_password_changed_accounts_revoke_persistent_cookie(self):
        self.login()
        with server.db() as conn:
            conn.execute('UPDATE admin_users SET auth_version=auth_version+1 WHERE username=?', ('review',))
        self.assertEqual(self.req('/api/session')[0], 401)
        self.login()
        with server.db() as conn:
            conn.execute('UPDATE admin_users SET active=0 WHERE username=?', ('review',))
        self.assertEqual(self.req('/api/session')[0], 401)

    def test_rate_limit_keeps_existing_protection_and_explains_retry_time(self):
        for _ in range(10):
            self.assertEqual(self.req('/api/login', {'username': 'review', 'password': 'wrong'})[0], 401)
        status, headers, body = self.req('/api/login', {'username': 'review', 'password': self.password})
        self.assertEqual(status, 429)
        self.assertEqual(body['code'], 'LOGIN_RATE_LIMITED')
        self.assertEqual(headers['Retry-After'], str(body['retryAfter']))
        self.assertGreaterEqual(body['retryAfter'], 1)
        self.assertLessEqual(body['retryAfter'], 600)
        with patch.object(server.time, 'time', return_value=time.time() + 601):
            self.assertEqual(self.req('/api/login', {'username': 'review', 'password': self.password})[0], 200)

    def test_logs_have_status_request_id_and_reason_without_credentials(self):
        output = io.StringIO()
        marker = 'credential-that-must-never-be-logged'
        with redirect_stdout(output):
            status, headers, body = self.req('/api/login?private=' + marker,
                {'username': 'review', 'password': marker})
        self.assertEqual(status, 401)
        self.assertEqual(body['code'], 'INVALID_CREDENTIALS')
        events = [json.loads(line) for line in output.getvalue().splitlines() if line.startswith('{')]
        event = next(event for event in events if event.get('event') == 'http_request')
        self.assertEqual(event['status'], 401)
        self.assertEqual(event['path'], '/api/login')
        self.assertEqual(event['request_id'], headers['X-Request-ID'])
        self.assertEqual(event['auth_reason'], 'invalid_credentials')
        self.assertNotIn(marker, output.getvalue())
        self.assertNotIn('password', output.getvalue())
        self.assertNotIn('csrf', output.getvalue())

    def test_busy_auth_storage_returns_503_without_revoking_cookie(self):
        self.login()
        cookie = self.cookie
        for target, method, path, data in (
            (server.SESSION_STORE, 'get', '/api/session', None),
            (server.STORE, 'get_user', '/', None),
            (server.STORE, 'authenticate', '/api/login', {'username': 'review', 'password': self.password}),
            (server.SESSION_STORE, 'create', '/api/login', {'username': 'review', 'password': self.password}),
        ):
            output = io.StringIO()
            with self.subTest(method=method), redirect_stdout(output), patch.object(
                    target, method, side_effect=sqlite3.OperationalError('private SQL file path')):
                status, headers, body = self.req(path, data)
                self.assertEqual(status, 503)
                self.assertEqual(body['code'], 'AUTH_STORAGE_UNAVAILABLE')
                self.assertEqual(headers['Retry-After'], '2')
                self.assertNotIn('Set-Cookie', headers)
                self.assertNotIn('private SQL', json.dumps(body) + output.getvalue())
                self.assertIn('storage_unavailable', output.getvalue())
        self.assertEqual(self.cookie, cookie)
        self.assertEqual(self.req('/api/session')[0], 200)

    def test_anonymous_shared_login_script_is_javascript(self):
        status, headers, body = self.req('/api-client.js')
        self.assertEqual(status, 200)
        self.assertIn('javascript', headers['Content-Type'])
        self.assertNotIn(b'<html', body.lower())


class CatalogueDelivery(unittest.TestCase):
    def test_second_catalog_can_load_while_first_download_is_sending(self):
        statuses = []
        second = server.Handler.__new__(server.Handler)
        second.command = 'GET'
        second.response_headers = lambda code, *args: statuses.append(code)
        second.wfile = io.BytesIO()
        entered = []

        class SlowClient:
            def write(self, chunk):
                if not entered:
                    entered.append(True)
                    second.respond_catalog(lambda: {'records': ['second client']})

        first = server.Handler.__new__(server.Handler)
        first.command = 'GET'
        first.response_headers = lambda code, *args: statuses.append(code)
        first.wfile = SlowClient()
        first.respond_catalog(lambda: {'records': ['first client']})
        self.assertEqual(statuses, [200, 200])
        self.assertEqual(json.loads(second.wfile.getvalue())['records'], ['second client'])


if __name__ == '__main__':
    unittest.main()
