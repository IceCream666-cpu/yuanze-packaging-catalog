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
        self.assertEqual(plan['counts'], {'posters':64,'featured':29,'models':29})
        self.assertEqual(len(plan['preservedPackaging']), 28)
        compile(publish.REMOTE_SCRIPT.replace('PAYLOAD', repr('{}')), 'remote-publication', 'exec')

    def test_rejects_stale_unapproved_or_changed_model(self):
        _, candidate, _ = publish.plan()
        original = Path.read_text
        def replace_chunk_role(data):
            name = next(n for n in data['files'] if n.startswith('assets/packaging/PackagingDetail-') and n.endswith('.js'))
            data['files']['assets/packaging/Unexpected-abc123.js'] = data['files'].pop(name)

        def omit_fixed_asset(data):
            data['files']['assets/featured/poster-082.png'] = data['files'].pop('assets/featured/poster-081.png')

        mutations = {
            'wrong compiled chunk role': replace_chunk_role,
            'fixed asset replaced': omit_fixed_asset,
            'stale version': lambda data: data.update(version='client1.44'),
            'unapproved 082 model': lambda data: data['files'].update({'assets/packaging/poster-082-v1.glb': {'bytes':1,'sha256':'x'}}),
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
