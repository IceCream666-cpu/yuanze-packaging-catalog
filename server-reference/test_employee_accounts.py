"""Employee administration through real HTTP against disposable, synthetic state."""
import json
import secrets
import unittest

import test_http
from test_server import server


class EmployeeAccounts(unittest.TestCase):
    setUp = test_http.HTTP.setUp
    tearDown = test_http.HTTP.tearDown
    req = test_http.HTTP.req

    def sign_in(self, username, password):
        status, headers, body = self.req('/api/login', {
            'username': username, 'password': password})
        self.assertEqual(status, 200, body)
        self.cookie = headers['Set-Cookie'].split(';')[0]
        status, _, session = self.req('/api/session')
        self.assertEqual(status, 200, session)
        self.csrf = session['csrf']
        return self.cookie, self.csrf

    def administrator(self):
        self.admin_session = self.sign_in('review_admin', self.password)

    def as_admin(self):
        self.cookie, self.csrf = self.admin_session

    def save_user(self, username, version=0, **fields):
        self.as_admin()
        status, _, body = self.req('/api/admin/users', {
            'action': 'save', 'id': username, 'version': version, **fields})
        self.assertEqual(status, 200, body)
        return body

    def test_complete_employee_lifecycle_and_access_boundaries(self):
        self.administrator()
        username = 'employee.lifecycle'
        original_password, replacement_password = secrets.token_urlsafe(18), secrets.token_urlsafe(18)
        user = self.save_user(username, name='验收员工', role='employee',
                              active=True, password=original_password)
        self.assertEqual(user['username'], username)
        self.assertEqual(user['role'], 'employee')
        employee_session = self.sign_in(username, original_password)
        self.assertEqual(self.req('/')[0], 200)
        self.assertEqual(self.req('/api/preferences')[0], 200)
        for path in ('/admin', '/admin.js', '/api/admin/users', '/api/admin/records'):
            self.assertEqual(self.req(path)[0], 403, path)
        self.assertEqual(self.req('/api/admin/users', {
            'action': 'save', 'id': username, 'version': user['version'],
            'role': 'admin'})[0], 403)

        user = self.save_user(username, user['version'], password=replacement_password)
        self.cookie, self.csrf = employee_session
        self.assertEqual(self.req('/api/session')[0], 401)
        self.assertEqual(self.req('/api/login', {
            'username': username, 'password': original_password})[0], 401)
        employee_session = self.sign_in(username, replacement_password)

        user = self.save_user(username, user['version'], active=False)
        self.cookie, self.csrf = employee_session
        self.assertEqual(self.req('/api/session')[0], 401)
        self.assertEqual(self.req('/api/login', {
            'username': username, 'password': replacement_password})[0], 401)

        user = self.save_user(username, user['version'], active=True)
        self.assertTrue(user['active'])
        self.cookie, self.csrf = employee_session
        self.assertEqual(self.req('/api/session')[0], 401, 'Re-enabling must not revive revoked cookies')
        self.sign_in(username, replacement_password)
        self.assertEqual(self.req('/api/preferences')[0], 200)
        self.as_admin()
        audit = self.req('/api/admin/audit?resource=users&id=' + username)[2]['items']
        self.assertEqual(len(audit), 4)
        self.assertTrue(any(item['action'] == 'password_reset' for item in audit))
        serialized = json.dumps({'user': user, 'audit': audit})
        for forbidden in (original_password, replacement_password, '"salt"', '"hash"'):
            self.assertNotIn(forbidden, serialized)

    def test_duplicate_creation_and_stale_changes_cannot_overwrite_accounts(self):
        self.administrator()
        password = secrets.token_urlsafe(18)
        user = self.save_user('employee.unique', name='原始姓名', role='employee', password=password)
        self.assertEqual(self.req('/api/admin/users', {
            'action': 'save', 'id': user['username'], 'version': 0,
            'name': '重复创建覆盖', 'password': secrets.token_urlsafe(18)})[0], 409)
        user = self.save_user(user['username'], user['version'], name='更新后的姓名')
        self.assertEqual(self.req('/api/admin/users', {
            'action': 'save', 'id': user['username'], 'version': user['version'] - 1,
            'name': '旧版本覆盖'})[0], 409)
        entries = self.req('/api/admin/users')[2]['items']
        matching = [entry for entry in entries if entry['username'] == user['username']]
        self.assertEqual(len(matching), 1)
        self.assertEqual(matching[0]['name'], '更新后的姓名')
        self.sign_in(user['username'], password)

    def test_password_validation_and_last_administrator_protection(self):
        self.administrator()
        for password in ('short', ' ' + secrets.token_urlsafe(18), secrets.token_urlsafe(18) + ' '):
            self.assertEqual(self.req('/api/admin/users', {
                'action': 'save', 'id': 'employee.validation', 'version': 0,
                'name': '验收员工', 'role': 'employee', 'password': password})[0], 400)
        self.assertNotIn('employee.validation', [u['username'] for u in self.req('/api/admin/users')[2]['items']])
        administrator = next(u for u in self.req('/api/admin/users')[2]['items'] if u['username'] == 'review_admin')
        for fields in ({'active': False}, {'role': 'employee'}):
            self.assertEqual(self.req('/api/admin/users', {
                'action': 'save', 'id': administrator['username'],
                'version': administrator['version'], **fields})[0], 400)
        self.assertEqual(self.req('/api/session')[0], 200)

    def test_separate_employee_accounts_keep_personal_preferences_separate(self):
        self.administrator()
        first_password, second_password = secrets.token_urlsafe(18), secrets.token_urlsafe(18)
        self.save_user('employee.first', password=first_password)
        self.save_user('employee.second', password=second_password)
        record_id = server.CATALOG['records'][0]['id']
        first_session = self.sign_in('employee.first', first_password)
        self.assertEqual(self.req('/api/preferences', {'favorites': [record_id]})[0], 200)
        self.sign_in('employee.second', second_password)
        self.assertEqual(self.req('/api/preferences')[2]['favorites'], [])
        self.cookie, self.csrf = first_session
        self.assertEqual(self.req('/api/preferences')[2]['favorites'], [record_id])


if __name__ == '__main__':
    unittest.main()
