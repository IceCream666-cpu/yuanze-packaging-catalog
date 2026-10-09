"""Ensure the design preview serves only its own files, never private directories."""
import importlib.util
from pathlib import Path
from threading import Thread
import unittest
from urllib.error import HTTPError
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('detail_demo_server', ROOT/'scripts/serve_product_detail_demo.py')
demo = importlib.util.module_from_spec(spec)
spec.loader.exec_module(demo)


class ProductDetailDemoServerTest(unittest.TestCase):
    def setUp(self):
        self.server = demo.ThreadingHTTPServer(('127.0.0.1', 0), demo.DemoHandler)
        self.worker = Thread(target=self.server.serve_forever, daemon=True)
        self.worker.start()
        self.base = 'http://127.0.0.1:'+str(self.server.server_port)

    def tearDown(self):
        self.server.shutdown()
        self.worker.join()
        self.server.server_close()

    def test_demo_has_no_api_access_and_loads_only_whitelisted_assets(self):
        for route in ['/', '/demo.css', '/demo.js', '/brand.svg']:
            with urlopen(self.base+route) as response:
                self.assertEqual(response.status, 200)
                self.assertEqual(response.headers['Cache-Control'], 'no-store')
                self.assertIn("connect-src 'none'", response.headers['Content-Security-Policy'])
                self.assertGreater(len(response.read()), 50)

    def test_private_paths_api_and_directory_listing_are_not_served(self):
        for route in ['/api/catalog', '/.secrets/', '/../../server-reference/private/catalog.json', '/%2e%2e/server-reference/private/catalog.json', '/work/', '/README.md']:
            with self.assertRaises(HTTPError) as error:
                urlopen(self.base+route)
            self.assertEqual(error.exception.code, 404)

    def test_head_returns_headers_without_a_body(self):
        with urlopen(Request(self.base+'/demo.js', method='HEAD')) as response:
            self.assertEqual(response.status, 200)
            self.assertGreater(int(response.headers['Content-Length']), 0)
            self.assertEqual(response.read(), b'')
