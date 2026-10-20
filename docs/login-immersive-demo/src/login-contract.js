// Match the existing username/password contract; never accept a role from a form.
export function loginDestination(role, search = '') {
  if (!['admin', 'employee', 'client'].includes(role)) throw new Error('invalid_role');
  if (role === 'client') return '/client';
  const code = (new URLSearchParams(search).get('code') || '').toUpperCase();
  return /^YZ-BC-\d{6,}$/.test(code)
    ? '/?code=' + encodeURIComponent(code)
    : role === 'admin' ? '/admin' : '/';
}

export async function authenticate(requestJSON, credentials, search = '') {
  const result = await requestJSON('/api/login', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ username: credentials.username, password: credentials.password }),
  });
  const destination = loginDestination(result.role, search);
  let session;
  try {
    session = await requestJSON('/api/session');
  } catch (error) {
    if (error.status === 401) throw new Error('cookie_missing');
    throw error;
  }
  if (session.role !== result.role) throw new Error('role_mismatch');
  return { role: result.role, destination };
}

export function inputWarnings(username, password, capsLock) {
  const notes = [];
  if (/[\u200B-\u200D\u2060\uFEFF]/u.test(username + password)) notes.push('invisible');
  if (password && password !== password.trim()) notes.push('whitespace');
  if (/[\uFF01-\uFF5E]/u.test(username)) notes.push('fullwidth');
  if (capsLock) notes.push('caps');
  return notes;
}
