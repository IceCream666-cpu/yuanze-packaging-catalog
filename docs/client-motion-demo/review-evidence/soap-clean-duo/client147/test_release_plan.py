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
        self.assertEqual(plan['counts'], {'posters':65,'featured':29,'models':30})
        self.assertEqual(len(plan['preservedPackaging']), 29)
        compile(publish.REMOTE_SCRIPT.replace('PAYLOAD', repr('{}')), 'remote-publication', 'exec')

    def test_insufficient_disk_space_stops_before_staging_or_upload(self):
        candidate = 200 * 1024 * 1024
        required = candidate + 256 * 1024 * 1024
        for available in (0, candidate, required - 1):
            with self.subTest(available=available), self.assertRaisesRegex(RuntimeError, 'Insufficient service-user disk space'):
                publish.require_disk_headroom(available, candidate)
        self.assertEqual(publish.require_disk_headroom(required, candidate), required)
        self.assertLess(publish.REMOTE_SCRIPT.index('require_disk_headroom(space.'), publish.REMOTE_SCRIPT.index('shutil.copytree(old,new)'))
        source = Path(publish.__file__).read_text()
        self.assertLess(source.index('capacity = ssh.remote'), source.index('upload = ssh.remote'))

    def test_rejects_stale_unapproved_or_changed_model(self):
        _, candidate, _ = publish.plan()
        original = Path.read_text
        def replace_chunk_role(data):
            name = next(n for n in data['files'] if n.startswith('assets/packaging/PackagingDetail-') and n.endswith('.js'))
            data['files']['assets/packaging/Unexpected-abc123.js'] = data['files'].pop(name)

        def omit_fixed_asset(data):
            data['files']['assets/featured/poster-082.png'] = data['files'].pop('assets/posters/poster-082.webp')

        mutations = {
            'wrong compiled chunk role': replace_chunk_role,
            'fixed asset replaced': omit_fixed_asset,
            'stale version': lambda data: data.update(version='client1.46'),
            'changed approved 082 model': lambda data: data['files']['assets/packaging/poster-082-v1.glb'].update(sha256='0'*64),
            'deleted retained 080 model': lambda data: data['files'].pop('assets/packaging/poster-080-v2.glb'),
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
