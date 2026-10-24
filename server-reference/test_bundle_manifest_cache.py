"""Bundle approval caching must notice releases and revocations immediately."""
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from test_server import server


class BundleManifestCache(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.public = Path(temporary.name).resolve()
        replacement = patch.object(server, 'PUBLIC', self.public)
        replacement.start()
        self.addCleanup(replacement.stop)
        for directory in ('showroom', 'login-ui'):
            root = self.public / directory
            root.mkdir()
            (root / 'index.html').write_text('approved page')
            self.save(root)

    def save(self, root, name='index.html'):
        manifest = root / 'bundle-manifest.json'
        manifest.write_text(json.dumps({'schema': 1, 'files': {name: {}}}))
        return manifest

    def loaders(self):
        return ((self.public / 'showroom', server.showroom_asset),
                (self.public / 'login-ui', server.login_asset))

    def test_unchanged_content_is_parsed_once(self):
        server._read_bundle_files.cache_clear()
        with patch.object(server.json, 'loads', wraps=json.loads) as parse:
            for root, lookup in self.loaders():
                for _ in range(20):
                    self.assertEqual(lookup('index.html'), root / 'index.html')
        self.assertEqual(parse.call_count, 1)

    def test_atomic_replacement_with_same_size_and_mtime_revokes_entry(self):
        for root, lookup in self.loaders():
            with self.subTest(bundle=root.name):
                self.assertIsNotNone(lookup('index.html'))
                manifest = root / 'bundle-manifest.json'
                before = manifest.stat()
                temporary = root / 'replacement.json'
                temporary.write_text(manifest.read_text().replace('index.html', 'other.html'))
                os.utime(temporary, ns=(before.st_atime_ns, before.st_mtime_ns))
                temporary.replace(manifest)
                self.assertEqual(manifest.stat().st_size, before.st_size)
                self.assertEqual(manifest.stat().st_mtime_ns, before.st_mtime_ns)
                self.assertIsNone(lookup('index.html'))

    def test_in_place_change_with_restored_mtime_revokes_entry(self):
        for root, lookup in self.loaders():
            with self.subTest(bundle=root.name):
                self.assertIsNotNone(lookup('index.html'))
                manifest = root / 'bundle-manifest.json'
                before = manifest.stat()
                self.save(root, 'other.html')
                os.utime(manifest, ns=(before.st_atime_ns, before.st_mtime_ns))
                self.assertEqual(manifest.stat().st_ino, before.st_ino)
                self.assertEqual(manifest.stat().st_size, before.st_size)
                # Force identical metadata to reproduce coarse filesystem timestamps.
                with patch.object(Path, 'stat', return_value=before):
                    self.assertIsNone(lookup('index.html'))

    def test_deleted_or_invalid_manifest_fails_closed_and_recovers(self):
        invalid = ('broken', '[]', '{"schema":2,"files":{"index.html":{}}}',
                   '{"schema":1,"files":null}', '{"schema":1,"files":["index.html"]}',
                   '{"schema":1,"files":"index.html"}')
        for root, lookup in self.loaders():
            for raw in invalid:
                with self.subTest(bundle=root.name, raw=raw):
                    manifest = self.save(root)
                    self.assertIsNotNone(lookup('index.html'))
                    manifest.write_text(raw)
                    self.assertIsNone(lookup('index.html'))
            manifest = self.save(root)
            self.assertIsNotNone(lookup('index.html'))
            manifest.unlink()
            self.assertIsNone(lookup('index.html'))
            self.save(root)
            self.assertIsNotNone(lookup('index.html'))

    def test_cached_approval_does_not_bypass_target_checks(self):
        secret = self.public / 'secret.html'
        secret.write_text('private')
        for root, lookup in self.loaders():
            with self.subTest(bundle=root.name):
                target = root / 'index.html'
                self.assertIsNotNone(lookup('index.html'))
                target.unlink()
                self.assertIsNone(lookup('index.html'))
                target.symlink_to(secret)
                self.assertIsNone(lookup('index.html'))
                self.assertIsNone(lookup('../secret.html'))
                self.assertIsNone(lookup('bundle-manifest.json'))

    def test_read_error_is_not_cached_and_retries_on_next_request(self):
        for root, lookup in self.loaders():
            with self.subTest(bundle=root.name):
                with patch.object(Path, 'read_bytes', side_effect=PermissionError):
                    self.assertIsNone(lookup('index.html'))
                self.assertIsNotNone(lookup('index.html'))


if __name__ == '__main__':
    unittest.main()
