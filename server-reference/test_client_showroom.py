"""Company showroom build, authentication and framing boundaries."""
import hashlib
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import test_client_access as client_fixtures
from test_server import server

ROOT = Path(__file__).resolve().parents[1]
BANNER_PATHS = [f'assets/poster-banners/{name}.webp' for name in (
    '01-pdrn-capsule-cream', '02-body-care-collection', '03-cherry-blossom-gift-set',
    '04-hand-care-collection', '05-daylight-still',
)]
spec = importlib.util.spec_from_file_location('build_customer_showroom', ROOT / 'scripts/build_customer_showroom.py')
builder = importlib.util.module_from_spec(spec)
spec.loader.exec_module(builder)


class ShowroomBuild(unittest.TestCase):
    def test_deterministic_bundle_and_stale_files_detected_and_removed(self):
        with tempfile.TemporaryDirectory() as temp:
            target = Path(temp) / 'showroom'
            builder.build(destination=target)
            first = {p.relative_to(target).as_posix(): p.read_bytes() for p in target.rglob('*') if p.is_file()}
            builder.build(destination=target)
            self.assertEqual(first, {p.relative_to(target).as_posix(): p.read_bytes() for p in target.rglob('*') if p.is_file()})
            self.assertEqual(builder.check(destination=target), [])
            (target / 'private-snapshot.json').write_text('PRIVATE')
            (target / 'preview.js').write_text('stale')
            self.assertEqual(builder.check(destination=target), ['preview.js', 'private-snapshot.json'])
            builder.build(destination=target)
            self.assertEqual(builder.check(destination=target), [])
            self.assertFalse((target / 'private-snapshot.json').exists())

    def test_bundle_only_contains_reviewed_material_and_relocated_urls(self):
        files = builder.expected_files(); manifest = json.loads(files['bundle-manifest.json'])
        assets = json.loads((builder.SOURCE / 'assets/manifest.json').read_text())
        self.assertEqual(set(builder.ENTRYPOINTS),
                         {'index.html', 'preview.css', 'preview.js', 'company-content.js', 'product-posters.js'})
        self.assertEqual(set(files), set(builder.ENTRYPOINTS) |
                         {'assets/' + entry['path'] for entry in assets['files']} | {'bundle-manifest.json'})
        self.assertEqual(manifest['schema'], 1)
        self.assertEqual(set(manifest['files']), set(files) - {'bundle-manifest.json'})
        for name, entry in manifest['files'].items():
            self.assertEqual(hashlib.sha256(files[name]).hexdigest(), entry['sha256'])
            self.assertEqual(len(files[name]), entry['bytes'])
        html = files['index.html'].decode()
        for value in ['data-mode="production"', 'data-src="/client/products?showroom=1"',
                      'src="/showroom/preview.js"', '<style data-showroom-styles>']:
            self.assertIn(value, html)
        self.assertNotIn('src="/showroom/company-content.js"', html)
        self.assertNotIn('src="/showroom/product-posters.js"', html)
        self.assertNotIn('href="/showroom/preview.css"', html)
        script = files['preview.js'].decode()
        self.assertLess(script.index('window.YuanzeCompanyContent'), script.index('window.YuanzeProductPosters'))
        self.assertLess(script.index('window.YuanzeProductPosters'), script.index("const content = window.YuanzeCompanyContent"))
        self.assertIn("'/showroom/assets/", files['company-content.js'].decode())
        posters = files['product-posters.js'].decode()
        self.assertIn('"/showroom/assets/posters/', posters)
        self.assertNotIn('"assets/', posters)
        self.assertNotIn("'assets/", posters)
        for name in ['catalog.json', 'auth.json', 'preview_customer_showroom.py', 'assets/manifest.json']:
            self.assertNotIn(name, files)
        self.assertEqual(len([name for name in files if name.endswith('.pdf')]), 4)
        self.assertEqual(len([name for name in files if name.startswith('assets/posters/')]), 124)
        self.assertIn('assets/posters/poster-079.webp', files)
        self.assertIn('assets/posters/poster-079-thumb.webp', files)
        self.assertEqual({name for name in files if name.startswith('assets/poster-banners/')}, set(BANNER_PATHS))
        for path in BANNER_PATHS:
            self.assertIn('/showroom/' + path, files['company-content.js'].decode())

    def test_poster_paths_are_relocated_without_changing_metadata(self):
        with tempfile.TemporaryDirectory() as temp:
            source = Path(temp); (source / 'assets').mkdir()
            for name in builder.ENTRYPOINTS:
                (source / name).write_text('<html></html>' if name == 'index.html' else '')
            (source / 'assets/manifest.json').write_text('{"files":[]}')
            content = 'window.YuanzeProductPosters = {src: "assets/posters/full.webp", thumbnail: \'assets/posters/thumb.webp\', title: "Poster"};'
            (source / 'product-posters.js').write_text(content)
            actual = builder.expected_files(source)['product-posters.js'].decode()
            self.assertEqual(actual, content.replace('"assets/', '"/showroom/assets/').replace("'assets/", "'/showroom/assets/"))

    def test_asset_checksums_and_manifest_paths_validated_before_build(self):
        with tempfile.TemporaryDirectory() as temp:
            source = Path(temp) / 'source'; (source / 'assets').mkdir(parents=True)
            for name in builder.ENTRYPOINTS:
                (source / name).write_text('<html></html>' if name == 'index.html' else '')
            (source / 'assets/a.png').write_bytes(b'changed')
            manifest = source / 'assets/manifest.json'
            manifest.write_text(json.dumps({'files': [{'path': 'a.png', 'sha256': '0'*64, 'bytes': 7}]}))
            with self.assertRaisesRegex(ValueError, 'checksum'):
                builder.build(source, Path(temp) / 'showroom')
            manifest.write_text(json.dumps({'files': [{'path': '../../secret.pdf', 'sha256': '0'*64, 'bytes': 7}]}))
            with self.assertRaisesRegex(ValueError, 'invalid path'):
                builder.expected_files(source)


class ShowroomRoutes(unittest.TestCase):
    req = client_fixtures.ClientAccess.req
    login = client_fixtures.ClientAccess.login
    tearDown = client_fixtures.ClientAccess.tearDown

    def setUp(self):
        client_fixtures.ClientAccess.setUp(self)
        public = Path(self.temp.name) / 'public'; public.mkdir()
        for name, text in {'client.html': '<main>SAFE PRODUCTS</main>', 'index.html': 'EMPLOYEE CATALOGUE',
                           'admin.html': 'ADMIN WORKSPACE', 'client.js': 'client only',
                           'client.css': 'client styles', 'login.html': 'LOGIN'}.items():
            (public / name).write_text(text)
        builder.build(destination=public / 'showroom')
        self.poster_paths = [f'assets/posters/{poster}{suffix}.webp'
                             for poster in ('poster-001', 'poster-032', 'poster-041', 'poster-056', 'poster-070')
                             for suffix in ('', '-thumb')]
        self.public = public
        patcher = patch.object(server, 'PUBLIC', public)
        patcher.start(); self.addCleanup(patcher.stop)

    def test_all_company_content_requires_authentication(self):
        for path in ['/client', '/client.html', '/client/products']:
            status, headers, _ = self.req(path)
            self.assertEqual(status, 303); self.assertEqual(headers['Location'], '/login')
        for path in ['/showroom/index.html', '/showroom/preview.js', '/showroom/assets/showroom.png',
                     '/showroom/assets/certificates/gmpc-en.pdf', '/showroom/product-posters.js',
                     *['/showroom/' + poster for poster in self.poster_paths]]:
            for method in ['GET', 'HEAD']:
                status, headers, body = self.req(path, method=method)
                self.assertEqual(status, 401); self.assertEqual(headers['Cache-Control'], 'no-store')
                self.assertNotIn(b'%PDF', body)
                self.assertNotIn(b'WEBP', body)
        self.login(); self.assertEqual(self.req('/api/logout', {})[0], 200)
        self.assertEqual(self.req('/showroom/assets/reception.png')[0], 401)
        self.assertEqual(self.req('/showroom/' + self.poster_paths[0])[0], 401)

    def test_client_admin_routes_and_framing_only_on_products_page(self):
        for username in ['client-test', 'admin']:
            self.login(username)
            for path in ['/client', '/client.html', '/showroom/index.html']:
                status, headers, body = self.req(path)
                self.assertEqual(status, 200)
                self.assertIn(b'data-mode="production"', body)
                self.assertIn(b'/client/products?showroom=1', body)
                self.assertEqual(headers['X-Frame-Options'], 'DENY')
                self.assertIn("frame-ancestors 'none'", headers['Content-Security-Policy'])
                self.assertIn("frame-src 'self'", headers['Content-Security-Policy'])
            status, headers, body = self.req('/client/products?showroom=1')
            self.assertEqual(status, 200); self.assertEqual(body, b'<main>SAFE PRODUCTS</main>')
            self.assertEqual(headers['X-Frame-Options'], 'SAMEORIGIN')
            self.assertIn("frame-ancestors 'self'", headers['Content-Security-Policy'])
            self.assertNotIn("frame-ancestors 'none'", headers['Content-Security-Policy'])
            _, headers, _ = self.req('/client.js')
            self.assertEqual(headers['X-Frame-Options'], 'DENY')
            for path in ['product-posters.js', *self.poster_paths]:
                status, headers, body = self.req('/showroom/' + path)
                self.assertEqual(status, 200)
                self.assertGreater(len(body), 0)
                self.assertEqual(headers['Cache-Control'], 'private, no-cache')
                self.assertIn('ETag', headers)
                self.assertEqual(headers['X-Content-Type-Options'], 'nosniff')
                self.assertNotIn('Access-Control-Allow-Origin', headers)
        _, headers, _ = self.req('/admin')
        self.assertEqual(headers['X-Frame-Options'], 'DENY')
        self.assertIn("frame-ancestors 'none'", headers['Content-Security-Policy'])

    def test_removed_poster_artwork_and_thumbnails_are_absent_for_clients_and_admins(self):
        removed_paths = [f'assets/posters/poster-{index:03d}{suffix}.webp'
                         for index in range(15, 32) for suffix in ('', '-thumb')]
        manifest = json.loads((self.public / 'showroom/bundle-manifest.json').read_text())
        for path in removed_paths:
            self.assertNotIn(path, manifest['files'])
            self.assertFalse((self.public / 'showroom' / path).exists())
        for username in ['client-test', 'admin']:
            self.login(username)
            for path in removed_paths:
                with self.subTest(username=username, path=path):
                    for method in ['GET', 'HEAD']:
                        status, _, body = self.req('/showroom/' + path, method=method)
                        self.assertEqual(status, 404)
                        self.assertNotIn(b'WEBP', body)

    def test_five_banner_images_require_customer_or_admin_access_and_preserve_their_content(self):
        for username, expected_status in [(None, 401), ('employee', 403), ('client-test', 200), ('admin', 200)]:
            if username:
                self.login(username)
            for path in BANNER_PATHS:
                with self.subTest(username=username, path=path):
                    status, headers, body = self.req('/showroom/' + path)
                    self.assertEqual(status, expected_status)
                    self.assertEqual(headers['Cache-Control'], 'private, no-cache' if expected_status == 200 else 'no-store')
                    if expected_status == 200:
                        self.assertEqual(headers['Content-Type'], 'image/webp')
                        self.assertEqual(headers['X-Content-Type-Options'], 'nosniff')
                        self.assertEqual(body, (builder.SOURCE / path).read_bytes())
                    else:
                        self.assertNotIn(b'WEBP', body)
                    status, head_headers, head = self.req('/showroom/' + path, method='HEAD')
                    self.assertEqual(status, expected_status)
                    self.assertEqual(head, b'')
                    if expected_status == 200:
                        self.assertEqual(head_headers['Content-Type'], 'image/webp')
                        self.assertEqual(head_headers['Content-Length'], str(len(body)))

    def test_pdf_images_and_script_mime_and_head(self):
        self.login()
        for path, mime in [('assets/certificates/iso22716-zh.pdf', 'application/pdf'),
                           ('assets/certificates/gmpc-en.png', 'image/png'),
                           ('preview.css', 'text/css'), ('company-content.js', 'text/javascript'),
                           ('product-posters.js', 'text/javascript'),
                           *[(poster, 'image/webp') for poster in self.poster_paths]]:
            status, headers, body = self.req('/showroom/' + path)
            self.assertEqual(status, 200); self.assertEqual(headers['Content-Type'], mime)
            self.assertGreater(len(body), 0)
            status, headers, head = self.req('/showroom/' + path, method='HEAD')
            self.assertEqual(status, 200); self.assertEqual(headers['Content-Length'], str(len(body)))
            self.assertEqual(head, b'')

    def test_preview_images_keep_role_and_session_boundaries(self):
        paths = ['/showroom/assets/previews/showroom-512.webp',
                 '/showroom/assets/previews/certificates/gmpc-en-1280.webp',
                 '/showroom/assets/previews/posters/poster-001-512.webp']
        for path in paths:
            self.assertEqual(self.req(path)[0], 401)
        self.login('employee')
        for path in paths:
            self.assertEqual(self.req(path)[0], 403)
        for username in ['client-test', 'admin']:
            self.login(username)
            for path in paths:
                status, headers, body = self.req(path)
                self.assertEqual(status, 200)
                self.assertEqual(headers['Content-Type'], 'image/webp')
                self.assertEqual(headers['Cache-Control'], 'private, no-cache')
                self.assertGreater(len(body), 0)

    def test_webp_mime_does_not_depend_on_the_host_mime_database(self):
        self.login()
        with patch.object(server.mimetypes, 'guess_type', return_value=(None, None)):
            for path in self.poster_paths:
                for method in ['GET', 'HEAD']:
                    status, headers, _ = self.req('/showroom/' + path, method=method)
                    self.assertEqual(status, 200)
                    self.assertEqual(headers['Content-Type'], 'image/webp')
                    self.assertEqual(headers['X-Content-Type-Options'], 'nosniff')

    def test_employee_unchanged_and_customer_resources_denied(self):
        self.login('employee')
        self.assertEqual(self.req('/')[2], b'EMPLOYEE CATALOGUE')
        for path in ['/client', '/client/products', '/showroom/index.html',
                     '/showroom/assets/showroom.png', '/showroom/assets/certificates/gmpc-en.pdf',
                     '/showroom/product-posters.js', *['/showroom/' + poster for poster in self.poster_paths]]:
            for method in ['GET', 'HEAD']:
                self.assertEqual(self.req(path, method=method)[0], 403, path)
        self.assertEqual(self.req('/x/../showroom/index.html')[0], 404)
        self.assertEqual(self.req('/x/%2e%2e/showroom/assets/showroom.png')[0], 404)
        for path in ['/./admin.html', '/%2e/admin.html', '/./admin.js', '/./showroom/index.html',
                     '/%2e/showroom/assets/showroom.png', '/showroom//index.html',
                     '/showroom/%2fassets/showroom.png', '/%2fadmin.html',
                     '/showroom/./index.html', '/showroom/%00index.html', '/showroom/%5cindex.html']:
            with self.subTest(path=path):
                status, _, body = self.req(path)
                self.assertEqual(status, 404)
                self.assertNotIn(b'ADMIN WORKSPACE', body)
                self.assertNotIn(b'data-mode="production"', body)
        self.assertEqual(self.req('/')[1]['X-Frame-Options'], 'DENY')

    def test_manifest_unlisted_files_traversal_and_symlinks_fail_closed(self):
        self.login(); directory = self.public / 'showroom'
        (directory / 'private.json').write_text('PRIVATE')
        (directory / 'assets/unlisted.pdf').write_bytes(b'%PDF PRIVATE')
        (directory / 'assets/posters/unlisted.webp').write_bytes(b'PRIVATE POSTER')
        (directory / 'assets/poster-banners/unlisted.webp').write_bytes(b'PRIVATE BANNER')
        (directory / 'unlisted.js').write_text('PRIVATE SCRIPT')
        (directory / 'assets/symlink.pdf').symlink_to(self.public / 'admin.html')
        manifest_path = directory / 'bundle-manifest.json'
        manifest = json.loads(manifest_path.read_text())
        manifest['files']['assets/symlink.pdf'] = {'sha256': '0'*64, 'bytes': 0}
        # A manifest cannot extend the reviewed script entrypoint allowlist.
        manifest['files']['unlisted.js'] = {'sha256': '0'*64, 'bytes': 0}
        manifest_path.write_text(json.dumps(manifest))
        for path in ['bundle-manifest.json', 'private.json', 'assets/manifest.json', 'assets/unlisted.pdf',
                     'assets/posters/unlisted.webp', 'assets/poster-banners/unlisted.webp',
                     'unlisted.js', 'assets/symlink.pdf', '../admin.html',
                     '%2e%2e/admin.html', 'assets/%2e%2e/%2e%2e/admin.html']:
            status, _, body = self.req('/showroom/' + path)
            self.assertEqual(status, 404, path); self.assertNotIn(b'PRIVATE', body)
        for malformed in ['broken', '[]', '{"schema":1,"files":null}']:
            manifest_path.write_text(malformed)
            self.assertEqual(self.req('/client')[0], 404)
            self.assertEqual(self.req('/showroom/assets/showroom.png')[0], 404)
            self.assertEqual(self.req('/showroom/product-posters.js')[0], 404)
            self.assertEqual(self.req('/showroom/' + self.poster_paths[0])[0], 404)
        self.assertEqual(self.req('/client/products')[0], 200)


if __name__ == '__main__':
    unittest.main()
