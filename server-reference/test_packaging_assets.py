"""Approved packaging assets retain the existing customer authentication boundary."""
import hashlib
import http.client
import json
from pathlib import Path
import unittest
from unittest.mock import patch

import test_client_access as client_fixtures
from test_server import server


class PackagingAssets(unittest.TestCase):
    login = client_fixtures.ClientAccess.login
    tearDown = client_fixtures.ClientAccess.tearDown

    def setUp(self):
        client_fixtures.ClientAccess.setUp(self)
        self.public = Path(self.temp.name) / 'public'
        self.showroom = self.public / 'showroom'
        self.showroom.mkdir(parents=True)
        for name in ('login.html', 'client.html', 'client.js', 'index.html'):
            (self.public / name).write_text('<main>Existing page</main>')
        self.assets = {
            'index.html': b'<main>Customer showroom</main>',
            'preview.js': b'/* Existing entrypoint */',
            'assets/packaging/packaging-scene-A1b2.js': b'export const packaging = true;',
            'assets/packaging/packaging-detail-A1b2.css': b'.packaging-root { color: #222; }',
            'assets/packaging/vendor/gsap.min.js': b'/* Locally approved animation library */',
            'assets/packaging/beach-magic-packaging.glb': b'glTF' + bytes(range(128)),
        }
        self.manifest = {'schema': 1, 'files': {}}
        for name, data in self.assets.items():
            self.write_asset(name, data)
        self.save_manifest()
        patcher = patch.object(server, 'PUBLIC', self.public)
        patcher.start()
        self.addCleanup(patcher.stop)

    def write_asset(self, name, data=b'UNAPPROVED DATA', approved=True):
        path = self.showroom / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
        if approved:
            self.manifest['files'][name] = {
                'sha256': hashlib.sha256(data).hexdigest(), 'bytes': len(data),
            }

    def save_manifest(self):
        (self.showroom / 'bundle-manifest.json').write_text(json.dumps(self.manifest))

    def req(self, path, data=None, method=None, headers=None):
        connection = http.client.HTTPConnection(self.host)
        request_headers = {'Origin': 'https://' + self.host, 'Cookie': self.cookie,
                           'X-CSRF-Token': self.csrf, **(headers or {})}
        connection.request(method or ('GET' if data is None else 'POST'), path,
                           body=None if data is None else json.dumps(data), headers=request_headers)
        response = connection.getresponse()
        result = response.status, dict(response.getheaders()), response.read()
        connection.close()
        return result

    def test_roles_and_head_keep_existing_boundaries(self):
        paths = [name for name in self.assets if name.startswith('assets/packaging/')]
        for username, expected in [(None, 401), ('employee', 403), ('client-test', 200), ('admin', 200)]:
            if username:
                self.login(username)
            for name in paths:
                for method in ('GET', 'HEAD'):
                    with self.subTest(username=username, name=name, method=method):
                        status, headers, body = self.req('/showroom/' + name, method=method)
                        self.assertEqual(status, expected)
                        self.assertEqual(headers['X-Content-Type-Options'], 'nosniff')
                        self.assertEqual(headers['Cache-Control'], 'private, no-cache' if expected == 200 else 'no-store')
                        self.assertNotIn('Access-Control-Allow-Origin', headers)
                        if method == 'HEAD':
                            self.assertEqual(body, b'')
                        elif expected == 200:
                            self.assertEqual(body, self.assets[name])
                        else:
                            self.assertNotEqual(body, self.assets[name])

    def test_only_supported_packaging_paths_can_be_approved(self):
        forbidden = ['assets/packaging/scene.mjs', 'assets/packaging/scene.js.map',
                     'assets/packaging/config.json', 'assets/packaging/page.html',
                     'assets/packaging/.hidden.js', 'assets/packaging/payload.wasm',
                     'assets/packaging/models/contents.bin', 'assets/packaging/payload.JS',
                     'assets/packaging-extra/scene.js', 'assets/other/scene.js',
                     'assets/scene.css', 'models/beach-magic.glb', 'gsap.min.js']
        for name in forbidden:
            self.write_asset(name)
        self.write_asset('assets/packaging/unlisted.js', approved=False)
        self.save_manifest()
        self.login()
        for name in [*forbidden, 'assets/packaging/unlisted.js', 'bundle-manifest.json']:
            with self.subTest(name=name):
                self.assertIsNone(server.showroom_asset(name))
                self.assertEqual(self.req('/showroom/' + name)[0], 404)

    def test_alternate_paths_and_symlink_escape_are_rejected(self):
        secret = self.public / 'secret.glb'
        secret.write_bytes(b'PRIVATE FILE')
        escape = self.showroom / 'assets/packaging/escape.glb'
        escape.symlink_to(secret)
        self.manifest['files']['assets/packaging/escape.glb'] = {'bytes': 12, 'sha256': '0' * 64}
        self.save_manifest()
        self.login()
        for name in ('assets/packaging/escape.glb', 'assets/packaging/../packaging/beach-magic-packaging.glb',
                     'assets/packaging/./beach-magic-packaging.glb', 'assets/packaging//beach-magic-packaging.glb',
                     'assets/packaging/%2e%2e/packaging/beach-magic-packaging.glb',
                     'assets/packaging/%5cbeach-magic-packaging.glb'):
            with self.subTest(name=name):
                status, _, body = self.req('/showroom/' + name)
                self.assertEqual(status, 404)
                self.assertNotIn(b'PRIVATE FILE', body)
        for name in (None, [], '/assets/packaging/scene.js', 'assets/packaging/../scene.js'):
            self.assertIsNone(server.showroom_asset(name))

    def test_explicit_mime_types_do_not_depend_on_host_mime_database(self):
        expected = {'.js': 'text/javascript', '.css': 'text/css', '.glb': 'model/gltf-binary'}
        self.login()
        with patch.object(server.mimetypes, 'guess_type', return_value=(None, None)):
            for name in self.assets:
                if not name.startswith('assets/packaging/'):
                    continue
                for method in ('GET', 'HEAD'):
                    with self.subTest(name=name, method=method):
                        status, headers, _ = self.req('/showroom/' + name, method=method)
                        self.assertEqual(status, 200)
                        self.assertEqual(headers['Content-Type'], expected[Path(name).suffix])

    def test_blob_policy_is_scoped_to_showroom_html(self):
        _, headers, _ = self.req('/login')
        self.assertEqual(headers['Content-Security-Policy'], server.DEFAULT_CSP)
        self.assertNotIn('blob:', server.DEFAULT_CSP)
        self.login()
        for path in ('/client', '/client.html', '/showroom/index.html'):
            status, headers, _ = self.req(path)
            self.assertEqual(status, 200)
            self.assertEqual(headers['Content-Security-Policy'], server.SHOWROOM_CSP)
            self.assertIn("img-src 'self' data: blob:", headers['Content-Security-Policy'])
            self.assertIn("connect-src 'self' blob:", headers['Content-Security-Policy'])
            self.assertIn("script-src 'self';", headers['Content-Security-Policy'])
            self.assertIn("frame-ancestors 'none'", headers['Content-Security-Policy'])
        for path in ('/client/products', '/client.js', '/showroom/preview.js', '/api/session'):
            status, headers, _ = self.req(path)
            self.assertEqual(status, 200)
            self.assertNotIn('blob:', headers['Content-Security-Policy'])
        self.login('employee')
        status, headers, _ = self.req('/')
        self.assertEqual(status, 200)
        self.assertEqual(headers['Content-Security-Policy'], server.DEFAULT_CSP)

    def test_model_cache_and_range_are_private_and_revalidate_approval(self):
        self.login()
        name = 'assets/packaging/beach-magic-packaging.glb'
        path = '/showroom/' + name
        model = self.assets[name]
        status, headers, body = self.req(path)
        self.assertEqual((status, body), (200, model))
        self.assertEqual(headers['Accept-Ranges'], 'bytes')
        self.assertEqual(headers['Cache-Control'], 'private, no-cache')
        etag = headers['ETag']
        status, headers, body = self.req(path, headers={'If-None-Match': etag})
        self.assertEqual((status, body), (304, b''))
        status, headers, body = self.req(path, headers={'Range': 'bytes=4-15', 'If-Range': etag})
        self.assertEqual((status, body), (206, model[4:16]))
        self.assertEqual(headers['Content-Range'], f'bytes 4-15/{len(model)}')
        status, headers, body = self.req(path, headers={'Range': 'bytes=4-15', 'If-Range': '"stale"'})
        self.assertEqual((status, body), (200, model))
        status, headers, body = self.req(path, headers={'Range': 'bytes=9999-'})
        self.assertEqual((status, body), (416, b''))
        self.assertEqual(headers['Content-Range'], f'bytes */{len(model)}')

        del self.manifest['files'][name]
        self.save_manifest()
        for request_headers in ({'If-None-Match': etag}, {'Range': 'bytes=4-15'}):
            status, headers, _ = self.req(path, headers=request_headers)
            self.assertEqual(status, 404)
            self.assertEqual(headers['Cache-Control'], 'no-store')
        self.write_asset(name, model)
        self.save_manifest()
        self.assertEqual(self.req('/api/logout', {})[0], 200)
        for request_headers in ({'If-None-Match': etag}, {'Range': 'bytes=4-15'}):
            status, headers, _ = self.req(path, headers=request_headers)
            self.assertEqual(status, 401)
            self.assertEqual(headers['Cache-Control'], 'no-store')

    def test_invalid_or_missing_manifest_never_serves_packaging(self):
        self.login()
        path = '/showroom/assets/packaging/beach-magic-packaging.glb'
        manifest = self.showroom / 'bundle-manifest.json'
        for raw in ('{invalid', '[]', '{"schema":2,"files":{}}', '{"schema":1,"files":[]}'):
            with self.subTest(raw=raw):
                manifest.write_text(raw)
                self.assertEqual(self.req(path)[0], 404)
        manifest.unlink()
        self.assertEqual(self.req(path)[0], 404)


if __name__ == '__main__':
    unittest.main()
