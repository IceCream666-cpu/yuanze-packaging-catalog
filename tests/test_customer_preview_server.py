"""Local preview must never become a back door to employee data or files."""
import base64
import http.client
import importlib.util
import io
import json
from pathlib import Path
import tempfile
import threading
import unittest
from unittest.mock import patch

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('customer_preview', ROOT / 'scripts/preview_customer_showroom.py')
preview = importlib.util.module_from_spec(spec)
spec.loader.exec_module(preview)


def image_bytes():
    output = io.BytesIO()
    Image.new('RGB', (32, 32), 'teal').save(output, format='JPEG')
    return output.getvalue()


class CustomerPreviewServerTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.media = self.root / 'outputs/mobile-preview/client-media'
        self.media.mkdir(parents=True)
        self.token = 'a' * 64 + '.jpg'
        (self.media / self.token).write_bytes(image_bytes())
        self.items = []
        for i, (material, capacity, section) in enumerate([('PET', '30 mL', 'face'), ('玻璃', '50 mL', 'face'), ('PE', '100 mL', 'body-head')]):
            self.items.append({'id': f'{i:064x}', 'productCode': f'YZ-BC-{i+1:06d}',
                'name': 'PRIVATE VENDOR price 1.20', 'capacity': capacity, 'capacityMl': 999,
                'category': '瓶类', 'bottleType': '喷雾瓶', 'materials': [material],
                'uses': ['精华液'] if section == 'face' else ['洗手液'], 'sections': [section],
                'specifications': [{'label': '口径', 'value': '24 mm'}, {'label': '供应商', 'value': 'PRIVATE VENDOR'}],
                'images': [{'url': '/client-media/' + self.token, 'supplier': 'PRIVATE'}],
                'supplier': 'PRIVATE VENDOR', 'price': 1.2, 'raw': {'password': 'PRIVATE'}})
        (self.media.parent / 'catalog.json').write_text(json.dumps({'items': self.items,
            'facets': {'materials': ['PRIVATE VENDOR']}}))
        (self.root / 'server-reference/public/brand').mkdir(parents=True)
        (self.root / 'server-reference/public/client.html').write_text('<h1>Customer products</h1>')
        (self.root / 'server-reference/public/admin.html').write_text('PRIVATE ADMIN')
        draft = self.root / 'docs/mobile-client-preview'
        (draft / 'assets').mkdir(parents=True)
        (draft / 'index.html').write_text('<h1>Draft showroom</h1>')
        (draft / 'assets/showroom.png').write_bytes(image_bytes())
        (draft / 'assets/manifest.json').write_text(json.dumps({'files': [{'path': 'showroom.png'}]}))
        (draft / 'secret.txt').write_text('PRIVATE FILE')
        self.server = preview.PreviewServer(self.root, port=0)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=2)
        self.temporary.cleanup()

    def request(self, path='/', method='GET', payload=None, headers=None):
        conn = http.client.HTTPConnection('127.0.0.1', self.server.server_port, timeout=5)
        encoded = json.dumps(payload) if payload is not None else None
        base_headers = {'Content-Type': 'application/json'} if payload is not None else {}
        conn.request(method, path, body=encoded, headers={**base_headers, **(headers or {})})
        response = conn.getresponse()
        data = response.read()
        result = response.status, dict(response.getheaders()), data
        conn.close()
        return result

    def test_only_safe_fields_leave_preview_and_facets_use_safe_data(self):
        status, headers, raw = self.request('/api/client/catalog')
        self.assertEqual(status, 200)
        self.assertNotIn(b'PRIVATE', raw)
        self.assertNotIn(b'price', raw)
        self.assertNotIn(b'supplier', raw)
        body = json.loads(raw)
        self.assertEqual(body['total'], 3)
        self.assertEqual(body['items'][0]['capacityMl'], 30)
        self.assertEqual(body['items'][0]['specifications'], [{'label': '口径', 'value': '24 mm'}])
        self.assertEqual(body['facets']['materials'], ['PE', 'PET', '玻璃'])
        self.assertEqual(headers['Cache-Control'], 'no-store')
        self.assertEqual(headers['X-Frame-Options'], 'SAMEORIGIN')
        self.assertEqual(self.server.server_address[0], '127.0.0.1')

    def test_multiselect_intersection_search_codes_and_pagination(self):
        body = json.loads(self.request('/api/client/catalog?material=PET&material=PE&section=face')[2])
        self.assertEqual([i['productCode'] for i in body['items']], ['YZ-BC-000001'])
        self.assertEqual(json.loads(self.request('/api/client/catalog?q=YZ-BC-000002')[2])['total'], 1)
        self.assertEqual(json.loads(self.request('/api/client/catalog?q=PRIVATE')[2])['total'], 0)
        body = json.loads(self.request('/api/client/catalog?pageSize=2&page=200')[2])
        self.assertEqual((body['page'], body['pages'], len(body['items'])), (2, 2, 1))
        self.assertEqual(json.loads(self.request('/api/client/catalog?page=no&pageSize=no')[2])['page'], 1)
        self.assertEqual(json.loads(self.request('/api/client/catalog?q=30ml')[2])['total'], 1)

    def test_file_allowlist_media_and_path_traversal(self):
        self.assertEqual(self.request('/')[0], 200)
        self.assertEqual(self.request('/client?showroom=1')[0], 200)
        self.assertEqual(self.request('/assets/showroom.png')[0], 200)
        self.assertEqual(self.request('/client-media/' + self.token)[0], 200)
        for path in ['/admin', '/admin.html', '/api/catalog', '/private/catalog.json', '/api/admin/records',
                     '/assets/manifest.json', '/secret.txt', '/%2e%2e/secret.txt', '/assets/%2e%2e/secret.txt',
                     '/client-media/' + 'b' * 64 + '.jpg']:
            with self.subTest(path=path):
                status, _, data = self.request(path)
                self.assertEqual(status, 404)
                self.assertNotIn(b'PRIVATE', data)

    def test_reject_host_rebinding_and_cross_origin_requests(self):
        for headers in [{'Host': 'evil.test'}, {'Origin': 'https://evil.test'}, {'Sec-Fetch-Site': 'cross-site'}]:
            with self.subTest(headers=headers):
                self.assertEqual(self.request('/api/client/catalog', headers=headers)[0], 403)
                self.assertEqual(self.request('/api/client/image-search', 'POST', {}, headers)[0], 403)
        own_origin = {'Origin': f'http://127.0.0.1:{self.server.server_port}'}
        self.assertEqual(self.request('/api/session', headers=own_origin)[0], 200)

    def test_csrf_and_mutation_denial(self):
        session = json.loads(self.request('/api/session')[2])
        self.assertEqual(session['role'], 'client')
        self.assertTrue(session['preview'])
        self.assertEqual(self.request('/api/logout', 'POST', {})[0], 403)
        headers = {'X-CSRF-Token': session['csrf']}
        self.assertEqual(self.request('/api/admin/records', 'POST', {}, headers)[0], 403)
        self.assertEqual(self.request('/api/logout', 'POST', {}, headers)[0], 200)
        self.assertNotEqual(session['csrf'], json.loads(self.request('/api/session')[2])['csrf'])
        self.assertEqual(self.request('/api/logout', 'POST', {}, headers)[0], 403)
        self.assertEqual(self.request('/api/catalog', 'PUT', {})[0], 405)

    def test_image_search_returns_safe_items_in_rank_order(self):
        headers = {'X-CSRF-Token': self.server.csrf}
        ranked = [{'record_id': self.items[1]['id'], 'score': .99, 'image_path': 'PRIVATE'},
                  {'record_id': self.items[0]['id'], 'score': .80, 'image_path': 'PRIVATE'}]
        with patch.object(self.server.visual, 'search', return_value=ranked) as search:
            status, _, raw = self.request('/api/client/image-search', 'POST', {'image': 'data:test'}, headers)
        search.assert_called_once_with('data:test')
        self.assertEqual(status, 200)
        body = json.loads(raw)
        self.assertTrue(body['imageSearch'])
        self.assertEqual([i['productCode'] for i in body['items']], ['YZ-BC-000002', 'YZ-BC-000001'])
        self.assertNotIn(b'PRIVATE', raw)
        self.assertNotIn(b'score', raw)

    def test_unavailable_model_has_actionable_failure_not_fake_results(self):
        image = 'data:image/jpeg;base64,' + base64.b64encode(image_bytes()).decode()
        headers = {'X-CSRF-Token': self.server.csrf}
        status, _, raw = self.request('/api/client/image-search', 'POST', {'image': image}, headers)
        self.assertEqual(status, 503)
        self.assertEqual(json.loads(raw)['code'], 'CLIENT_SEARCH_UNAVAILABLE')
        self.assertNotIn('items', json.loads(raw))
        self.assertEqual(self.request('/api/client/image-search', 'POST', {'image': 'bad'}, headers)[0], 400)
        self.assertEqual(self.request('/api/client/catalog')[0], 200)

    def test_image_results_include_more_than_one_default_page_with_explicit_cap(self):
        items = [{**self.server.snapshot.items[0], 'id': f'{i:064x}',
                  'productCode': f'YZ-BC-{i+1:06d}'} for i in range(60)]
        self.server.snapshot.items = items
        ranking = [{'record_id': item['id']} for item in reversed(items)]
        with patch.object(self.server.visual, 'search', return_value=ranking):
            status, _, raw = self.request('/api/client/image-search', 'POST',
                {'image': 'data:test'}, {'X-CSRF-Token': self.server.csrf})
        body = json.loads(raw)
        self.assertEqual(status, 200)
        self.assertEqual((body['total'], len(body['items']), body['pages']), (48, 48, 1))
        self.assertEqual(body['items'][0]['productCode'], 'YZ-BC-000060')
        self.assertEqual(body['items'][-1]['productCode'], 'YZ-BC-000013')

    def test_unapproved_missing_or_symlink_media_is_dropped(self):
        (self.media / ('c' * 64 + '.jpg')).symlink_to(self.root / 'server-reference/public/admin.html')
        raw = {**self.items[0], 'images': [{'url': '/client-media/' + 'c' * 64 + '.jpg'}]}
        self.assertIsNone(preview.public_item(raw, self.media))
        raw['images'] = [{'url': '/client-media/' + 'd' * 64 + '.jpg'}]
        self.assertIsNone(preview.public_item(raw, self.media))
        raw['images'] = [{'url': '/media/private.jpg'}, {'url': 'https://evil.test/private.jpg'}]
        self.assertIsNone(preview.public_item(raw, self.media))
        (self.media / self.token).unlink()
        (self.media / self.token).symlink_to(self.root / 'server-reference/public/admin.html')
        self.assertEqual(self.request('/client-media/' + self.token)[0], 404)


if __name__ == '__main__':
    unittest.main()
