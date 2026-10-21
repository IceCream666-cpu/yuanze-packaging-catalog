"""Real HTTP regression coverage for the company-wide login entry point."""
import unittest

import test_http
from test_server import server


class UnifiedLogin(unittest.TestCase):
    # Reuse the isolated database/server fixture without inheriting its tests.
    setUp = test_http.HTTP.setUp
    tearDown = test_http.HTTP.tearDown
    req = test_http.HTTP.req

    def sign_in(self, role):
        username = 'review_admin' if role == 'admin' else 'review'
        status, headers, body = self.req(
            '/api/login', {'username': username, 'password': self.password})
        self.assertEqual(status, 200, body)
        self.assertEqual(body['role'], role)
        self.assertIn('HttpOnly', headers['Set-Cookie'])
        self.assertIn('Secure', headers['Set-Cookie'])
        self.cookie = headers['Set-Cookie'].split(';')[0]
        status, _, session = self.req('/api/session')
        self.assertEqual(status, 200)
        self.assertEqual(session['role'], role)
        self.csrf = session['csrf']

    def assert_redirect(self, path, destination):
        status, headers, _ = self.req(path)
        self.assertEqual(status, 303, path)
        self.assertEqual(headers.get('Location'), destination, path)
        self.assertEqual(headers.get('Cache-Control'), 'no-store', path)

    def assert_page(self, path, filename):
        status, headers, body = self.req(path)
        self.assertEqual(status, 200, path)
        self.assertTrue(headers['Content-Type'].startswith('text/html'), path)
        self.assertEqual(body, (server.PUBLIC / filename).read_bytes(), path)

    def test_logged_out_links_share_the_same_login_page(self):
        for path in ('/', '/index.html', '/catalog', '/admin', '/admin.html', '/admin/tools'):
            with self.subTest(path=path):
                self.assert_redirect(path, '/login')
        status, _, login = self.req('/login')
        self.assertEqual(status, 200)
        self.assertIn(b'data-login-version="yuanze2.0.3"', login)
        self.assertIn(b'/_login/login.js', login)
        self.assertEqual(self.req('/login.html')[2], login)
        for path in ('/api/catalog', '/api/admin/records', '/api/admin/users'):
            self.assertEqual(self.req(path)[0], 401, path)

    def test_employee_entry_and_existing_session_login(self):
        self.sign_in('employee')
        for path in ('/', '/index.html', '/catalog'):
            self.assert_page(path, 'index.html')
        for path in ('/login', '/login.html'):
            self.assert_redirect(path, '/')

    def test_admin_entry_and_explicit_employee_catalog(self):
        self.sign_in('admin')
        for path in ('/', '/index.html', '/login', '/login.html'):
            self.assert_redirect(path, '/admin')
        self.assert_page('/admin', 'index.html')
        self.assert_page('/admin.html', 'index.html')
        self.assert_page('/admin/tools', 'admin.html')
        self.assert_page('/catalog', 'index.html')
        self.assertEqual(self.req('/api/admin/users')[0], 200)

    def test_product_deep_links_survive_login_for_both_roles(self):
        self.assert_redirect('/?code=yz-bc-000001', '/login?code=YZ-BC-000001')
        for role in ('employee', 'admin'):
            with self.subTest(role=role):
                self.sign_in(role)
                self.assert_page('/?code=YZ-BC-000001', 'index.html')
                for path in ('/login', '/login.html'):
                    self.assert_redirect(path + '?code=yz-bc-000001', '/?code=YZ-BC-000001')

    def test_invalid_product_redirects_never_escape_role_home(self):
        invalid_queries = (
            '?next=https%3A%2F%2Fexample.com',
            '?code=https%3A%2F%2Fexample.com',
            '?code=%2F%2Fevil.example',
            '?code=YZ-BC-000001%0A',
            '?code=YZ-BC-12345',
            '?code=YZ-BC-%EF%BC%90%EF%BC%90%EF%BC%90%EF%BC%90%EF%BC%90%EF%BC%91',
        )
        for query in invalid_queries:
            with self.subTest(role='logged out', query=query):
                self.assert_redirect('/' + query, '/login')
        for role, destination in (('employee', '/'), ('admin', '/admin')):
            self.sign_in(role)
            for query in invalid_queries:
                with self.subTest(role=role, query=query):
                    for path in ('/login', '/login.html'):
                        self.assert_redirect(path + query, destination)
                    if role == 'admin':
                        self.assert_redirect('/' + query, destination)

    def test_employee_permissions_cannot_be_promoted_by_url_or_role_input(self):
        status, headers, body = self.req('/api/login', {
            'username': 'review', 'password': self.password, 'role': 'admin'})
        self.assertEqual(status, 200)
        self.assertEqual(body['role'], 'employee')
        self.cookie = headers['Set-Cookie'].split(';')[0]
        self.csrf = self.req('/api/session')[2]['csrf']
        for path in ('/admin', '/admin.html', '/admin/tools', '/admin.js', '/admin.css',
                     '/api/admin/records', '/api/admin/users', '/api/admin/export'):
            self.assertEqual(self.req(path)[0], 403, path)
        self.assertEqual(self.req('/api/admin/users', {
            'action': 'save', 'id': 'review', 'role': 'admin'})[0], 403)
        self.assert_page('/?role=admin', 'index.html')

    def test_logout_and_expired_sessions_return_to_common_login(self):
        self.sign_in('admin')
        self.assertEqual(self.req('/api/logout', {})[0], 200)
        self.assert_redirect('/', '/login')
        self.assert_redirect('/admin', '/login')
        self.assertEqual(self.req('/login')[0], 200)
        self.sign_in('employee')
        with server.SESSION_STORE.connection() as conn:
            conn.execute('UPDATE sessions SET expires=0')
        self.assert_redirect('/', '/login')
        self.assertEqual(self.req('/login')[0], 200)


if __name__ == '__main__':
    unittest.main()
