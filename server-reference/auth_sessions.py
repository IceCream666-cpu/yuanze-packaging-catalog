"""Durable login sessions; employee/customer access keeps tokens off disk."""
from contextlib import contextmanager
import hashlib
import os
from pathlib import Path
import re
import sqlite3
import time


class SessionLimit(Exception):
    pass


class SessionStore:
    def __init__(self, state, employee_limit=0, admin_limit=20):
        # Zero explicitly disables only the employee cap. Administrators retain
        # a positive cap; booleans must not silently turn either limit on/off.
        if type(employee_limit) is not int or not 0 <= employee_limit <= 10000:
            raise ValueError('Employee session limit must be 0 (unlimited) or between 1 and 10000')
        if type(admin_limit) is not int or not 1 <= admin_limit <= 10000:
            raise ValueError('Admin session limit must be between 1 and 10000')
        directory = Path(state) / 'auth-sessions'
        directory.mkdir(mode=0o700, exist_ok=True)
        directory.chmod(0o700)
        self.path = directory / 'sessions.sqlite'
        self.limits = {'employee': employee_limit, 'admin': admin_limit, 'client': 0}
        descriptor = os.open(self.path, os.O_CREAT | os.O_WRONLY, 0o600)
        os.close(descriptor)
        self.path.chmod(0o600)
        with self.connection() as conn:
            conn.executescript('''PRAGMA journal_mode=WAL;
                CREATE TABLE IF NOT EXISTS sessions (
                    token_hash TEXT PRIMARY KEY,
                    username TEXT NOT NULL,
                    csrf TEXT NOT NULL,
                    expires REAL NOT NULL,
                    auth_version INTEGER NOT NULL,
                    role TEXT NOT NULL
                );
                CREATE INDEX IF NOT EXISTS session_user ON sessions(username);
                CREATE INDEX IF NOT EXISTS session_expiry ON sessions(expires);
            ''')
            conn.execute('DELETE FROM sessions WHERE expires<=?', (time.time(),))

    @contextmanager
    def connection(self):
        conn = sqlite3.connect(self.path, timeout=5)
        conn.row_factory = sqlite3.Row
        try:
            with conn:
                yield conn
        finally:
            conn.close()

    @staticmethod
    def token_hash(token):
        if not isinstance(token, str) or not re.fullmatch(r'[A-Za-z0-9_-]{32,128}', token):
            return None
        return hashlib.sha256(token.encode('ascii')).hexdigest()

    def create(self, token, session):
        digest = self.token_hash(token)
        if not digest:
            raise ValueError('Invalid session token')
        if session.get('role') not in self.limits:
            raise ValueError('Unsupported session role')
        with self.connection() as conn:
            conn.execute('BEGIN IMMEDIATE')
            conn.execute('DELETE FROM sessions WHERE expires<=?', (time.time(),))
            # A password reset/revocation does not consume the new account's cap.
            conn.execute('DELETE FROM sessions WHERE username=? AND auth_version<>?',
                         (session['username'], session['auth_version']))
            limit = self.limits.get(session['role'], self.limits['admin'])
            if limit:
                count = conn.execute('SELECT COUNT(*) FROM sessions WHERE username=?',
                                     (session['username'],)).fetchone()[0]
                if count >= limit:
                    raise SessionLimit()
            conn.execute('INSERT INTO sessions VALUES(?,?,?,?,?,?)',
                         (digest, session['username'], session['csrf'], session['expires'],
                          session['auth_version'], session['role']))

    def get(self, token):
        digest = self.token_hash(token)
        if not digest:
            return None, 'missing_session'
        with self.connection() as conn:
            row = conn.execute('SELECT username,csrf,expires,auth_version,role '
                               'FROM sessions WHERE token_hash=?', (digest,)).fetchone()
            if not row:
                return None, 'unknown_session'
            if row['expires'] <= time.time():
                conn.execute('DELETE FROM sessions WHERE token_hash=?', (digest,))
                return None, 'expired_session'
            return dict(row), 'valid_session'

    def delete(self, token):
        digest = self.token_hash(token)
        if digest:
            with self.connection() as conn:
                conn.execute('DELETE FROM sessions WHERE token_hash=?', (digest,))
