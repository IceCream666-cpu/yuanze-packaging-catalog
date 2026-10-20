import test from 'node:test';
import assert from 'node:assert/strict';
import http from 'node:http';
import { readdir } from 'node:fs/promises';
import { PassThrough } from 'node:stream';
import { createPreviewServer, UPSTREAM } from '../preview-server.js';

test('loopback proxy preserves authentication, rejects foreign origins and does not retry mutations', async t => {
  const calls = [];
  const server = createPreviewServer({ upstreamRequest(url, options, callback) {
    const request = new PassThrough();
    let body = '';
    request.on('data', chunk => { body += chunk; });
    request.on('end', () => {
      calls.push({ url: url.href, options, body });
      const response = new PassThrough();
      response.statusCode = url.pathname === '/api/login' ? 200 : 401;
      response.headers = { 'content-type': 'application/json', 'set-cookie': ['yz_session=fixture; HttpOnly; Secure; SameSite=Strict; Path=/'] };
      callback(response);
      response.end(JSON.stringify(url.pathname === '/api/login' ? {role:'client'} : {error:'请先登录'}));
    });
    return request;
  } });
  await new Promise(resolve => server.listen(0, '127.0.0.1', resolve));
  t.after(() => new Promise(resolve => server.close(resolve)));
  const origin = `http://127.0.0.1:${server.address().port}`;
  const send = (route, { method = 'GET', headers = {}, body = '' } = {}) => new Promise((resolve, reject) => {
    const req = http.request(origin + route, {method, headers}, res => {
      let text = ''; res.on('data', data => { text += data; });
      res.on('end', () => resolve({status:res.statusCode, headers:res.headers, text}));
    }); req.on('error', reject); req.end(body);
  });
  for (const headers of [{}, {Origin:'https://other.example'}, {Origin:origin, Host:'other.example'}, {Origin:origin, 'Sec-Fetch-Site':'cross-site'}]) {
    assert.equal((await send('/api/login', {method:'POST', headers})).status, 403);
  }
  assert.equal(calls.length, 0);
  assert.equal((await send('/api/session')).status, 401);
  const body = JSON.stringify({username:'fixture', password:' exact bytes '});
  const response = await send('/api/login', {method:'POST', headers:{Origin:origin, Referer:origin+'/login', Cookie:'yz_session=fixture', 'Content-Type':'application/json', 'Content-Length':Buffer.byteLength(body), 'X-CSRF-Token':'fixture-csrf', 'X-Forwarded-For':'attacker'}, body});
  assert.equal(response.status, 200);
  assert.match(response.headers['set-cookie'][0], /HttpOnly; Secure; SameSite=Strict/);
  assert.equal(calls.length, 2);
  assert.equal(calls[1].url, UPSTREAM + '/api/login');
  assert.equal(calls[1].body, body);
  assert.equal(calls[1].options.headers.origin, UPSTREAM);
  assert.equal(calls[1].options.headers['x-forwarded-for'], undefined);
  assert.equal(calls[1].options.headers['x-csrf-token'], 'fixture-csrf');
  assert.equal(calls[1].options.headers.cookie, 'yz_session=fixture');
  const page = await send('/login');
  assert.equal(page.status, 200);
  assert.equal(page.headers['cache-control'], 'no-store');
  assert.match(page.headers['content-security-policy'], /frame-ancestors 'none'/);
  const videoName = (await readdir(new URL('../dist/assets/', import.meta.url))).find(x => x.endsWith('.mp4'));
  const video = await send('/_login/assets/' + videoName, {headers:{Range:'bytes=0-63'}});
  assert.equal(video.status, 206);
  assert.equal(video.headers['content-length'], '64');
  assert.match(video.headers['content-range'], /^bytes 0-63\//);
  // Missing/traversal assets must not fall through to the upstream application.
  assert.equal((await send('/_login/.private')).status, 404);
  assert.equal((await send('/_login/%2e%2e%2fpreview-server.js')).status, 404);
});
