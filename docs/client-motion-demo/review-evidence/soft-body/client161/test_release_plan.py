"""Local-only scope guards: these tests never load the SSH helper."""
import copy
import json
from pathlib import Path
import unittest
from unittest.mock import patch
import publish


class ReleasePlanTests(unittest.TestCase):
    def test_approved_inventory_and_remote_syntax(self):
        _, _, plan = publish.plan()
        self.assertEqual(plan['counts'], {'posters':68,'featured':31,'models':32})
        self.assertEqual(plan['changed'], sorted(['index.html','preview.js',*publish.ADDED_ASSETS]))
        self.assertEqual(plan['added'], publish.ADDED_ASSETS)
        self.assertEqual(plan['removed'], publish.REMOVED)
        self.assertEqual(len(plan['preservedPackaging']), 31)
        compile(publish.REMOTE_SCRIPT.replace('PAYLOAD', repr('{}')), 'remote-publication', 'exec')

    def test_current_edition_stamp_and_bundle_match_the_reviewed_sources(self):
        import importlib.util
        spec=importlib.util.spec_from_file_location('client161_builder',publish.ROOT/'scripts/build_customer_showroom.py')
        builder=importlib.util.module_from_spec(spec);spec.loader.exec_module(builder)
        self.assertEqual(builder.check(edition='client161'), [])
        self.assertEqual(builder.CLIENT_EDITIONS['client161'], 'client1.61')
        with patch.object(builder.sys,'argv',['build_customer_showroom.py','--check']), patch.object(builder,'check',return_value=[]) as check:
            self.assertEqual(builder.main(),0)
            self.assertEqual(check.call_args.kwargs['edition'],'client161')
        source=publish.ROOT/'docs/client-motion-demo'
        self.assertEqual(json.loads((source/'package.json').read_text())['version'],'1.61.0')
        self.assertIn('client1.61',(source/'index.html').read_text())
        self.assertEqual((source/'src/copy.js').read_text().count("version:'client1.61'"),2)
        approved=json.loads((source/'packaging-manifest.json').read_text())
        self.assertEqual(approved['scope'],'approved-client1.61-collection-packaging')

    def test_insufficient_disk_space_stops_before_staging_or_upload(self):
        candidate = 200 * 1024 * 1024
        required = candidate + 256 * 1024 * 1024
        for available in (0, candidate, required - 1):
            with self.subTest(available=available), self.assertRaisesRegex(RuntimeError, 'Insufficient service-user disk space'):
                publish.require_disk_headroom(available, candidate)
        self.assertEqual(publish.require_disk_headroom(required, candidate), required)
        self.assertLess(publish.REMOTE_SCRIPT.index('require_disk_headroom(space.'), publish.REMOTE_SCRIPT.index('shutil.copytree(old,new,copy_function=os.link)'))
        source = Path(publish.__file__).read_text()
        self.assertLess(source.index('capacity = ssh.remote'), source.index('upload = ssh.remote'))

    def test_hardlinked_baseline_is_not_mutated(self):
        import os, tempfile, shutil
        with tempfile.TemporaryDirectory() as d:
            src=Path(d)/'old';dst=Path(d)/'new';src.mkdir();(src/'asset').write_bytes(b'old')
            shutil.copytree(src,dst,copy_function=os.link)
            self.assertEqual((src/'asset').stat().st_ino,(dst/'asset').stat().st_ino)
            (dst/'asset').unlink();(dst/'asset').write_bytes(b'new')
            self.assertEqual((src/'asset').read_bytes(),b'old')
        self.assertLess(publish.REMOTE_SCRIPT.index('if target.exists(): target.unlink()'),publish.REMOTE_SCRIPT.index('target.write_bytes('))

    def test_rejects_stale_unapproved_or_changed_model(self):
        _, candidate, _ = publish.plan()
        original = Path.read_text
        def replace_chunk_role(data):
            name = 'assets/packaging/poster-071-v2.glb'
            data['files']['assets/packaging/Unexpected-abc123.js'] = data['files'].pop(name)

        def omit_fixed_asset(data):
            data['files']['assets/featured/poster-086.png'] = data['files'].pop('assets/posters/poster-085.webp')

        mutations = {
            'wrong compiled chunk role': replace_chunk_role,
            'fixed asset replaced': omit_fixed_asset,
            'stale version': lambda data: data.update(version='client1.52'),
            'unapproved 086 model': lambda data: data['files'].update({'assets/packaging/poster-086-v1.glb': {'bytes':1,'sha256':'x'}}),
            'unapproved 072 v2 model': lambda data: data['files'].update({'assets/packaging/poster-072-v2.glb': {'bytes':1,'sha256':'x'}}),
            'unapproved 081 v2 model': lambda data: data['files'].update({'assets/packaging/poster-081-v2.glb': {'bytes':1,'sha256':'x'}}),
            'changed stylesheet': lambda data: data['files']['preview.css'].update(sha256='0'*64),
            'changed approved 081 model': lambda data: data['files']['assets/packaging/poster-081-v1.glb'].update(sha256='0'*64),
        }
        for name, mutate in mutations.items():
            with self.subTest(name=name):
                altered = copy.deepcopy(candidate)
                mutate(altered)
                def read(path, *args, **kwargs):
                    if path == publish.LOCAL/'bundle-manifest.json':
                        return json.dumps(altered)
                    return original(path, *args, **kwargs)
                with patch.object(Path, 'read_text', read), self.assertRaises(AssertionError):
                    publish.plan()


if __name__ == '__main__':
    unittest.main()
