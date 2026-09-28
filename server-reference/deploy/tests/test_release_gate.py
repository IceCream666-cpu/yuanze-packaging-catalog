import importlib.util
import io
import json
import tempfile
import threading
import unittest
from contextlib import redirect_stdout
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from unittest.mock import patch
from urllib.parse import urlsplit

MODULE = Path(__file__).resolve().parents[1] / 'release_gate.py'
spec = importlib.util.spec_from_file_location('release_gate', MODULE)
gate = importlib.util.module_from_spec(spec)
spec.loader.exec_module(gate)


def configuration():
    return {'apps': {'http': {'servers': {'srv0': {'routes': [
        {'match': [{'host': [host]}], 'terminal': True,
         'handle': [{'handler': 'subroute', 'routes': [{'handle': [
             {'handler': 'encode', 'encodings': {'gzip': {}}},
             {'handler': 'reverse_proxy', 'upstreams': [{'dial': '127.0.0.1:4180'}]}
         ]}]}]}
        for host in gate.DEFAULT_HOSTS
    ]}}}}}


class ConfigTests(unittest.TestCase):
    def test_current_transparent_proxy_contract(self):
        self.assertTrue(gate.check_proxy_contract(configuration(), gate.DEFAULT_HOSTS)['transparentProxyContract'])

    def test_rejects_original_root_rewrite_even_with_valid_caddy_syntax(self):
        value = configuration()
        inner = value['apps']['http']['servers']['srv0']['routes'][0]['handle'][0]['routes']
        inner.insert(0, {'match': [{'path': ['/']}], 'handle': [{'handler': 'rewrite', 'uri': '/login'}]})
        with self.assertRaises(gate.GateFailure):
            gate.check_proxy_contract(value, gate.DEFAULT_HOSTS)

    def test_rejects_unconditional_redirect_and_file_server(self):
        for handler in ('static_response', 'file_server', 'rewrite'):
            with self.subTest(handler=handler):
                value = configuration()
                value['apps']['http']['servers']['srv0']['routes'][0]['handle'].insert(0, {'handler': handler})
                with self.assertRaises(gate.GateFailure):
                    gate.check_proxy_contract(value, gate.DEFAULT_HOSTS)

    def test_requires_both_hosts_and_correct_upstream(self):
        value = configuration()
        value['apps']['http']['servers']['srv0']['routes'].pop()
        with self.assertRaises(gate.GateFailure):
            gate.check_proxy_contract(value, gate.DEFAULT_HOSTS)
        value = configuration()
        proxy = value['apps']['http']['servers']['srv0']['routes'][0]['handle'][0]['routes'][0]['handle'][1]
        proxy['upstreams'][0]['dial'] = 'example.invalid:80'
        with self.assertRaises(gate.GateFailure):
            gate.check_proxy_contract(value, gate.DEFAULT_HOSTS)

    def test_catch_all_route_cannot_precede_site(self):
        value = configuration()
        value['apps']['http']['servers']['srv0']['routes'].insert(0, {'handle': [{'handler': 'rewrite', 'uri': '/login'}]})
        with self.assertRaises(gate.GateFailure):
            gate.check_proxy_contract(value, gate.DEFAULT_HOSTS)

    def test_proxy_internal_rewrite_and_auth_header_override_are_rejected(self):
        for extra in ({'rewrite': {'uri': '/login'}},
                      {'headers': {'request': {'set': {'Host': ['wrong.invalid']}}}},
                      {'headers': {'response': {'set': {'Set-Cookie': ['broken']}}}},
                      {'headers': {'request': {'delete': ['Cookie']}}}):
            with self.subTest(extra=extra):
                value = configuration()
                proxy = value['apps']['http']['servers']['srv0']['routes'][0]['handle'][0]['routes'][0]['handle'][1]
                proxy.update(extra)
                with self.assertRaises(gate.GateFailure):
                    gate.check_proxy_contract(value, gate.DEFAULT_HOSTS)

    def test_current_host_and_security_headers_are_allowed(self):
        value = configuration()
        handlers = value['apps']['http']['servers']['srv0']['routes'][0]['handle'][0]['routes'][0]['handle']
        handlers.append({'handler': 'headers', 'response': {'set': {'X-Content-Type-Options': ['nosniff']}}})
        handlers[1]['headers'] = {'request': {'set': {'Host': ['{http.request.hostport}'], 'X-Forwarded-For': ['{http.request.remote.host}']}}}
        gate.check_proxy_contract(value, gate.DEFAULT_HOSTS)

    def test_validate_failure_is_not_ignored_or_printed(self):
        args = type('Args', (), {'caddy_bin': 'caddy', 'caddyfile': 'Caddyfile', 'host': None, 'upstream': '127.0.0.1:4180'})()
        result = type('Result', (), {'returncode': 1, 'stdout': '', 'stderr': 'PRIVATE_CONFIGURATION'})()
        with patch.object(gate.subprocess, 'run', return_value=result):
            with self.assertRaises(gate.GateFailure) as failure:
                gate.config_gate(args)
        self.assertNotIn('PRIVATE_CONFIGURATION', str(failure.exception))


class FakeSite(BaseHTTPRequestHandler):
    def log_message(self, *_args):
        pass

    def reply(self, status, content=b'', headers=None):
        if not isinstance(content, bytes):
            content = json.dumps(content).encode()
        self.send_response(status)
        for name, value in (headers or {}).items():
            self.send_header(name, value)
        self.send_header('Content-Length', str(len(content)))
        self.end_headers()
        self.wfile.write(content)

    def role(self):
        cookie = self.headers.get('Cookie', '')
        for role in ('employee', 'admin'):
            if 'yz_session=' + role in cookie and role in self.server.sessions:
                return role
        return None

    def do_GET(self):
        path = urlsplit(self.path).path
        role = self.role()
        if path == '/login.js':
            return self.reply(200, b"import { api } from './api-client.js';", {'Content-Type': 'text/javascript'})
        if path == '/api-client.js':
            mode = self.server.mode
            if mode == 'missing_module':
                return self.reply(401, {'error': 'login required'})
            return self.reply(200, b'export const api = 1;', {'Content-Type': 'text/html' if mode == 'wrong_mime' else 'application/javascript'})
        if path == '/login':
            if role:
                destination = '/?code=' + gate.CODE if '?code=' in self.path else ('/admin' if role == 'admin' else '/')
                return self.reply(303, headers={'Location': destination})
            return self.reply(200, b'<html><script type="module" src="/login.js"></script></html>')
        if not role:
            if path.startswith('/api/'):
                return self.reply(401, {'error': 'login required'})
            suffix = '?code=' + gate.CODE if '?code=' in self.path else ''
            return self.reply(303, headers={'Location': '/login' + suffix})
        if path == '/' and self.server.mode == 'loop':
            return self.reply(303, headers={'Location': '/'})
        if path == '/' and self.server.mode == 'cross_origin':
            return self.reply(303, headers={'Location': 'https://third-party.invalid/?secret=NEVER_LOG'})
        if path == '/api/session':
            return self.reply(200, {'role': role, 'username': role, 'csrf': 'SENSITIVE_CSRF'})
        if path == '/api/catalog':
            return self.reply(200, {'records': [{'id': 'one'}]})
        if path.startswith('/admin') or path.startswith('/api/admin/'):
            if role != 'admin' and self.server.mode != 'privilege_escalation':
                return self.reply(403, {'error': 'not admin'})
            if path.startswith('/api/'):
                return self.reply(200, {'value': {'siteTitle': 'Test'}})
            return self.reply(200, b'<script src="/admin.js"></script>')
        if path == '/' and role == 'admin' and '?code=' not in self.path:
            return self.reply(303, headers={'Location': '/admin'})
        return self.reply(200, b'<script src="/app.js"></script>')

    def do_POST(self):
        data = json.loads(self.rfile.read(int(self.headers.get('Content-Length', '0'))) or '{}')
        if self.path == '/api/login':
            if self.server.mode == 'bad_credentials':
                return self.reply(401, {'error': 'password=NEVER_LOG'})
            role = data.get('username')
            if role not in {'employee', 'admin'} or data.get('password') != 'ONLY_MEMORY_TEST_SECRET':
                return self.reply(401)
            self.server.sessions.add(role)
            return self.reply(200, {'role': role}, {'Set-Cookie': f'yz_session={role}; HttpOnly; SameSite=Strict; Path=/'})
        if self.path == '/api/logout':
            if self.headers.get('X-CSRF-Token') != 'SENSITIVE_CSRF':
                return self.reply(403)
            self.server.sessions.discard(self.role())
            return self.reply(200, {'ok': True}, {'Set-Cookie': 'yz_session=; Max-Age=0; Path=/'})
        self.reply(404)


class RouteTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = ThreadingHTTPServer(('127.0.0.1', 0), FakeSite)
        cls.server.sessions = set()
        cls.server.mode = 'valid'
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()
        cls.origin = 'http://127.0.0.1:' + str(cls.server.server_port)

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join()

    def setUp(self):
        self.server.mode = 'valid'
        self.server.sessions.clear()

    def run_role(self, role='employee'):
        return gate.role_gate(self.origin, role, {'username': role, 'password': 'ONLY_MEMORY_TEST_SECRET'}, allow_local_http=True)

    def test_complete_employee_and_admin_flow(self):
        for role in ('employee', 'admin'):
            result = self.run_role(role)
            self.assertTrue(result['passed'])
            self.assertEqual(result['loginScriptCount'], 2)
            self.assertIn('logout_invalidates_session', result['checks'])
            self.assertEqual(self.server.sessions, set())

    def test_original_self_loop_is_detected_and_session_cleaned(self):
        self.server.mode = 'loop'
        with self.assertRaisesRegex(gate.GateFailure, 'redirect loop detected'):
            self.run_role()
        self.assertEqual(self.server.sessions, set())

    def test_external_redirect_blocked_without_leaking_location(self):
        self.server.mode = 'cross_origin'
        with self.assertRaises(gate.GateFailure) as failure:
            self.run_role()
        self.assertNotIn('third-party', str(failure.exception))
        self.assertNotIn('NEVER_LOG', str(failure.exception))

    def test_module_dependencies_must_be_public_and_javascript(self):
        for mode in ('missing_module', 'wrong_mime'):
            self.server.mode = mode
            with self.subTest(mode=mode), self.assertRaises(gate.GateFailure):
                self.run_role()
            self.assertEqual(self.server.sessions, set())

    def test_employee_cannot_access_admin(self):
        self.server.mode = 'privilege_escalation'
        with self.assertRaises(gate.GateFailure):
            self.run_role()

    def test_cli_failure_redacts_credentials_cookie_csrf_response(self):
        with tempfile.TemporaryDirectory() as temporary:
            file = Path(temporary) / 'credentials.json'
            file.write_text(json.dumps({'username': 'employee', 'password': 'ONLY_MEMORY_TEST_SECRET'}))
            file.chmod(0o600)
            self.server.mode = 'bad_credentials'
            output = io.StringIO()
            with redirect_stdout(output):
                status = gate.main(['routes', '--origin', self.origin, '--allow-local-http',
                                    '--employee-credentials', str(file), '--admin-credentials', str(file)])
            self.assertEqual(status, 1)
            for sensitive in ('ONLY_MEMORY_TEST_SECRET', 'SENSITIVE_CSRF', 'NEVER_LOG', 'yz_session'):
                self.assertNotIn(sensitive, output.getvalue())

    def test_insecure_remote_origin_is_refused(self):
        with self.assertRaises(gate.GateFailure):
            gate.Client('http://8.134.220.216', allow_local_http=True)

    def test_credentials_file_requires_private_permissions(self):
        with tempfile.TemporaryDirectory() as temporary:
            file = Path(temporary) / 'credentials.txt'
            file.write_text('账号：employee\n密码：ONLY_MEMORY_TEST_SECRET\n')
            file.chmod(0o644)
            with self.assertRaises(gate.GateFailure):
                gate.load_credentials(file)
            file.chmod(0o600)
            self.assertEqual(gate.load_credentials(file)['username'], 'employee')

    def test_stdin_credentials_require_no_server_files(self):
        credentials = {role: {'username': role, 'password': 'ONLY_MEMORY_TEST_SECRET'}
                       for role in ('employee', 'admin')}
        output = io.StringIO()
        with patch.object(gate.sys, 'stdin', io.StringIO(json.dumps(credentials))), redirect_stdout(output):
            status = gate.main(['routes', '--origin', self.origin,
                                '--allow-local-http', '--credentials-stdin'])
        self.assertEqual(status, 0)
        self.assertNotIn('ONLY_MEMORY_TEST_SECRET', output.getvalue())
        self.assertEqual(self.server.sessions, set())

    def test_tcp_override_preserves_tls_hostname(self):
        connection = gate.TargetHTTPSConnection('bmt.yuanzebeauty.com', connect_address='127.0.0.1')
        self.assertEqual(connection.host, 'bmt.yuanzebeauty.com')
        with patch.object(gate.socket, 'create_connection') as create:
            connection._create_connection(('bmt.yuanzebeauty.com', 443), 3)
        create.assert_called_once_with(('127.0.0.1', 443), 3, None)


if __name__ == '__main__':
    unittest.main()
