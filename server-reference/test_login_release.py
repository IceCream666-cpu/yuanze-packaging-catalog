"""The production React login must work before authentication, including Safari ranges."""
import http.client
import json
import unittest
from unittest.mock import patch

import test_http
from test_server import server


class LoginRelease(unittest.TestCase):
    setUp = test_http.HTTP.setUp
    tearDown = test_http.HTTP.tearDown
    req = test_http.HTTP.req

    def resource(self, path, headers=None, method='GET'):
        connection = http.client.HTTPConnection(self.host)
        connection.request(method, path, headers=headers or {})
        response = connection.getresponse()
        result = response.status, dict(response.getheaders()), response.read()
        connection.close()
        return result

    def test_production_assets_are_public_and_preview_sources_are_not(self):
        manifest = json.loads((server.PUBLIC / 'login-ui/bundle-manifest.json').read_text())
        for name in manifest['files']:
            if name == 'index.html':
                continue
            status, headers, body = self.resource('/_login/' + name)
            self.assertEqual(status, 200, name)
            self.assertEqual(body, (server.PUBLIC / 'login-ui' / name).read_bytes())
            self.assertNotIn('text/html', headers['Content-Type'])
        for name in ('index.html', 'bundle-manifest.json', 'preview-server.js', 'src/App.jsx', 'assets/absent.mp4', '../private/catalog.json'):
            self.assertEqual(self.resource('/_login/' + name)[0], 404, name)
        self.assertEqual(self.req('/api/catalog')[0], 401)
        self.assertEqual(self.req('/showroom/preview.js')[0], 401)
        self.assertIn(b'data-login-version="yuanze2.0.3"', self.req('/login')[2])
        with patch.object(server, 'login_asset', return_value=None):
            self.assertIn(b'id="loginForm"', self.req('/login')[2], 'Missing release falls back to the existing functional login')

    def test_video_range_resume_cache_head_and_unsatisfiable_request(self):
        video = next((server.PUBLIC / 'login-ui/assets').glob('*.mp4'))
        path = '/_login/assets/' + video.name
        original = video.read_bytes()
        status, headers, body = self.resource(path)
        self.assertEqual(status, 200)
        self.assertEqual(headers['Content-Type'], 'video/mp4')
        self.assertEqual(headers['Accept-Ranges'], 'bytes')
        self.assertEqual(body, original)
        etag = headers['ETag']
        for request_range, expected in [('bytes=0-1', original[:2]), ('bytes=-32', original[-32:]), ('bytes=64-', original[64:])]:
            status, headers, body = self.resource(path, {'Range': request_range, 'If-Range': etag})
            self.assertEqual(status, 206)
            self.assertEqual(body, expected)
            self.assertEqual(int(headers['Content-Length']), len(expected))
            self.assertIn('Content-Range', headers)
        self.assertEqual(self.resource(path, {'Range': f'bytes={len(original)}-'})[0], 416)
        self.assertEqual(self.resource(path, {'If-None-Match': etag})[0], 304)
        self.assertEqual(self.resource(path, {'Range': 'bytes=0-1', 'If-Range': '"stale"'})[0], 200)
        status, headers, body = self.resource(path, method='HEAD')
        self.assertEqual(status, 200)
        self.assertEqual(body, b'')
        self.assertEqual(int(headers['Content-Length']), len(original))


if __name__ == '__main__':
    unittest.main()
