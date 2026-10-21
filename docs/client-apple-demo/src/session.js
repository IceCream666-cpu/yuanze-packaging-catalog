// Use the existing server session; credentials are never stored in this app.
export async function loadSession(fetcher = fetch) {
  const response = await fetcher('/api/session', {credentials: 'same-origin', cache: 'no-store'});
  if (!response.ok) throw Object.assign(new Error('Session unavailable'), {status: response.status});
  const session = await response.json();
  if (!['client', 'admin'].includes(session.role) || !session.csrf) {
    throw Object.assign(new Error('Session not authorized'), {status: 403});
  }
  return session;
}

export async function logoutSession(session, fetcher = fetch) {
  const active = session || await loadSession(fetcher);
  const response = await fetcher('/api/logout', {
    method: 'POST', credentials: 'same-origin', cache: 'no-store',
    headers: {'Content-Type': 'application/json', 'X-CSRF-Token': active.csrf},
    body: '{}',
  });
  if (!response.ok) throw Object.assign(new Error('Logout failed'), {status: response.status});
}
