// Loopback-only preview of the new login against the existing live application.
// No credentials are stored, logged, rewritten, or sent to any configurable host.
import http from 'node:http';
import https from 'node:https';
import { stat } from 'node:fs/promises';
import { createReadStream } from 'node:fs';
import { fileURLToPath } from 'node:url';
import path from 'node:path';

export const UPSTREAM = 'https://bmt.yuanzebeauty.com';
const BUILD = fileURLToPath(new URL('./dist/', import.meta.url));
const PREFIX = '/_login/';
const WORKSPACE = fileURLToPath(new URL('../internal-selection-demo/', import.meta.url));
const WORKSPACE_FILES = new Set(['workspace.css', 'workspace.js']);
const MIME = { '.html': 'text/html; charset=utf-8', '.js': 'text/javascript', '.css': 'text/css', '.png': 'image/png', '.jpg': 'image/jpeg', '.mp4': 'video/mp4', '.svg': 'image/svg+xml' };
const HOP = new Set(['connection', 'keep-alive', 'proxy-authenticate', 'proxy-authorization', 'te', 'trailer', 'transfer-encoding', 'upgrade']);

export function decorateWorkspaceHTML(html) {
  // Only the authenticated employee workspace returned by the upstream is eligible.
  // Login redirects, customer pages, admin tools and APIs are never substituted.
  if (!/<body\b[^>]*class="[^"]*\bcatalog-workspace\b/.test(html)) return html;
  return html.replace(/(<body\b[^>]*class=")([^"]*)"/, '$1$2 immersive-workspace"')
    .replace('</head>', '<link rel="stylesheet" href="/_workspace/workspace.css">\n<script type="module" src="/_workspace/workspace.js"></script>\n</head>');
}

export function createPreviewServer({ upstreamRequest = https.request, build = BUILD, workspace = WORKSPACE } = {}) {
  return http.createServer(async (req, res) => {
    const origin = `http://127.0.0.1:${req.socket.localPort}`;
    const fail = (status, message) => {
      if (res.headersSent) return res.destroy();
      res.writeHead(status, { 'Content-Type': 'application/json', 'Cache-Control': 'no-store' });
      res.end(JSON.stringify({ error: message }));
    };
    // Prevent DNS rebinding and cross-site use of this authenticated proxy.
    if (req.headers.host !== new URL(origin).host) return fail(403, '仅可通过本机 127.0.0.1 访问');
    if (!['GET', 'HEAD', 'POST', 'PUT', 'PATCH', 'DELETE'].includes(req.method)) return fail(405, '不支持的请求');
    if (req.headers['sec-fetch-site'] === 'cross-site' || (req.headers.origin && req.headers.origin !== origin)
      || (!['GET', 'HEAD'].includes(req.method) && req.headers.origin !== origin)) return fail(403, '请求来源无效');
    if (!req.url.startsWith('/') || req.url.startsWith('//')) return fail(400, '路径无效');
    let url;
    try { url = new URL(req.url, origin); } catch { return fail(400, '路径无效'); }
    const localLogin = ['/login', '/login.html', '/_login/', '/_login/index.html'].includes(url.pathname);
    if (url.pathname.startsWith('/_workspace/')) {
      const name = url.pathname.slice('/_workspace/'.length);
      if (!WORKSPACE_FILES.has(name)) return fail(404, '文件不存在');
      if (!['GET', 'HEAD'].includes(req.method)) return fail(405, '不支持的请求');
      try {
        const file = path.join(workspace, name), info = await stat(file);
        res.writeHead(200, {
          'Content-Type': MIME[path.extname(file)], 'Content-Length': info.size,
          'Cache-Control': 'no-store', 'X-Content-Type-Options': 'nosniff',
        });
        if (req.method === 'HEAD') return res.end();
        createReadStream(file).on('error', () => res.destroy()).pipe(res);
      } catch { fail(404, '预览文件不存在'); }
      return;
    }
    if (localLogin || url.pathname.startsWith(PREFIX)) {
      if (!['GET', 'HEAD'].includes(req.method)) return fail(405, '不支持的请求');
      let relative;
      try { relative = localLogin ? 'index.html' : decodeURIComponent(url.pathname.slice(PREFIX.length)); } catch { return fail(400, '路径无效'); }
      const file = path.resolve(build, relative);
      if (!file.startsWith(path.resolve(build) + path.sep) || relative.split(/[\\/]/).some(p => p.startsWith('.'))) return fail(404, '文件不存在');
      try {
        const info = await stat(file);
        if (!info.isFile()) return fail(404, '文件不存在');
        const headers = { 'Content-Type': MIME[path.extname(file)] || 'application/octet-stream', 'X-Content-Type-Options': 'nosniff',
          'Referrer-Policy': 'no-referrer', 'X-Frame-Options': 'DENY',
          'Cache-Control': localLogin ? 'no-store' : 'public, max-age=31536000, immutable',
          'Accept-Ranges': 'bytes',
          'Content-Security-Policy': "default-src 'self'; img-src 'self'; media-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; connect-src 'self'; frame-ancestors 'none'; base-uri 'self'; form-action 'self'" };
        let start = 0, end = info.size - 1, status = 200;
        if (req.headers.range) {
          const match = /^bytes=(\d+)-(\d*)$/.exec(req.headers.range);
          if (!match) return fail(416, '不支持的文件范围');
          start = Number(match[1]); end = match[2] ? Math.min(Number(match[2]), end) : end;
          if (start > end || start >= info.size) return fail(416, '文件范围无效');
          status = 206; headers['Content-Range'] = `bytes ${start}-${end}/${info.size}`;
        }
        res.writeHead(status, { ...headers, 'Content-Length': end - start + 1 });
        if (req.method === 'HEAD') return res.end();
        createReadStream(file, { start, end }).on('error', () => res.destroy()).pipe(res);
      } catch { fail(404, '预览文件不存在，请先运行 build'); }
      return;
    }
    // Root and all workspace routes are served by the real app, including its
    // unauthenticated redirect to /login and role boundaries. No local bypass.
    const headers = Object.fromEntries(Object.entries(req.headers).filter(([key]) => !HOP.has(key) && !key.startsWith('x-forwarded-') && !['forwarded', 'host', 'origin', 'referer'].includes(key)));
    headers.host = new URL(UPSTREAM).host;
    const workspacePage = req.method === 'GET' && ['/', '/index.html'].includes(url.pathname);
    if (workspacePage) {
      headers['accept-encoding'] = 'identity';
      delete headers['if-none-match']; delete headers['if-modified-since'];
    }
    if (req.headers.origin) headers.origin = UPSTREAM;
    if (req.headers.referer?.startsWith(origin + '/')) headers.referer = UPSTREAM + new URL(req.headers.referer).pathname;
    const upstream = upstreamRequest(new URL(url.pathname + url.search, UPSTREAM), { method: req.method, headers, timeout: 20000 }, response => {
      const output = Object.fromEntries(Object.entries(response.headers).filter(([key]) => !HOP.has(key) && !['strict-transport-security', 'alt-svc'].includes(key)));
      if (typeof output.location === 'string' && output.location.startsWith(UPSTREAM + '/')) output.location = output.location.slice(UPSTREAM.length);
      if (workspacePage && response.statusCode === 200 && /^text\/html\b/i.test(output['content-type'] || '') && !output['content-encoding']) {
        const chunks = []; let size = 0;
        response.on('data', chunk => {
          size += Buffer.byteLength(chunk);
          if (size > 4 * 1024 * 1024) { response.destroy(); fail(502, '预览页面过大'); }
          else chunks.push(Buffer.from(chunk));
        });
        response.on('error', () => fail(502, '预览页面加载失败，请重试'));
        response.on('end', () => {
          if (res.writableEnded || res.destroyed) return;
          const html = decorateWorkspaceHTML(Buffer.concat(chunks).toString('utf8'));
          delete output.etag; delete output['last-modified'];
          output['cache-control'] = 'no-store';
          output['content-length'] = Buffer.byteLength(html);
          res.writeHead(200, output); res.end(html);
        });
        return;
      }
      // Preserve HttpOnly, Secure and SameSite on upstream session cookies.
      res.writeHead(response.statusCode, output);
      response.on('error', () => res.destroy()).pipe(res);
    });
    upstream.on('timeout', () => upstream.destroy(new Error('upstream_timeout')));
    upstream.on('error', () => fail(502, '暂时无法连接包材库服务器，请稍后重试'));
    req.on('aborted', () => upstream.destroy());
    res.on('close', () => { if (!res.writableEnded) upstream.destroy(); });
    req.pipe(upstream);
  });
}

if (process.argv[1] && path.resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  const server = createPreviewServer();
  server.listen(8772, '127.0.0.1', () => console.log('Login preview: http://127.0.0.1:8772/login (existing account authentication)'));
  server.on('error', error => { console.error('Preview could not start:', error.code); process.exitCode = 1; });
}
