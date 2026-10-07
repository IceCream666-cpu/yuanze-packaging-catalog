import importlib.util
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch
import json

spec = importlib.util.spec_from_file_location('github_sync', Path(__file__).resolve().parents[1] / 'scripts/github_sync.py')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

class GitHubSyncTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name) / 'repo'
        self.remote = Path(self.tmp.name) / 'remote.git'
        self.root.mkdir()
        self.run_git(self.root, 'init', '-b', 'main')
        self.run_git(self.remote.parent, 'init', '--bare', str(self.remote))
        self.run_git(self.root, 'config', 'user.name', 'Test')
        self.run_git(self.root, 'config', 'user.email', 'test@example.invalid')
        self.run_git(self.root, 'remote', 'add', 'origin', str(self.remote))
        (self.root / 'source.txt').write_text('complete change\n')
        self.run_git(self.root, 'add', 'source.txt')
        self.run_git(self.root, 'commit', '-m', 'completed change')

    def run_git(self, root, *args):
        return subprocess.check_output(['git', '-C', str(root), *args], text=True, stderr=subprocess.DEVNULL).strip()

    def test_push_only_committed_code_and_preserve_dirty_work(self):
        (self.root / 'source.txt').write_text('unfinished change\n')
        (self.root / '.env').write_text('PRIVATE_TEST_VALUE=not-a-real-secret\n')
        with patch.object(module, 'REMOTE', str(self.remote)):
            self.assertEqual(module.sync(self.root), 0)
        local = self.run_git(self.root, 'rev-parse', 'HEAD')
        self.assertEqual(self.run_git(self.remote, 'rev-parse', 'main'), local)
        self.assertEqual(self.run_git(self.remote, 'show', 'main:source.txt'), 'complete change')
        self.assertNotIn('.env', self.run_git(self.remote, 'ls-tree', '--name-only', 'main'))
        self.assertEqual((self.root / 'source.txt').read_text(), 'unfinished change\n')
        self.assertTrue(json.loads((self.root / '.git/github-sync-status.json').read_text())['ok'])

    def test_timeout_preserves_commit_and_retry_uploads(self):
        original = self.run_git(self.root, 'rev-parse', 'HEAD')
        with patch.object(module, 'REMOTE', str(self.remote)):
            real_run = subprocess.run
            def timeout_push(command, **kwargs):
                if 'push' in command:
                    raise subprocess.TimeoutExpired('git push', 45)
                return real_run(command, **kwargs)
            with patch.object(module.subprocess, 'run', side_effect=timeout_push):
                self.assertEqual(module.sync(self.root), 1)
            self.assertEqual(self.run_git(self.root, 'rev-parse', 'HEAD'), original)
            self.assertFalse(json.loads((self.root / '.git/github-sync-status.json').read_text())['ok'])
            self.assertEqual(module.sync(self.root), 0)
        self.assertEqual(self.run_git(self.remote, 'rev-parse', 'main'), original)

    def test_unexpected_destination_is_blocked(self):
        self.assertEqual(module.sync(self.root), 1)
        self.assertFalse(json.loads((self.root / '.git/github-sync-status.json').read_text())['ok'])

    def test_existing_hook_is_preserved(self):
        hook = self.root / '.git/hooks/post-commit'
        hook.write_text('# existing project hook\n')
        with self.assertRaises(RuntimeError):
            module.install(self.root)
        self.assertEqual(hook.read_text(), '# existing project hook\n')

    def test_install_is_repeatable_and_repository_local(self):
        module.install(self.root)
        module.install(self.root)
        hook = self.root / '.git/hooks/post-commit'
        self.assertIn(module.MARKER, hook.read_text())
        self.assertIn('--root', hook.read_text())
        self.assertTrue(hook.stat().st_mode & 0o100)
        self.assertNotIn('force', hook.read_text())

    def test_non_fast_forward_does_not_overwrite_remote(self):
        with patch.object(module, 'REMOTE', str(self.remote)):
            self.assertEqual(module.sync(self.root), 0)
            first = self.run_git(self.root, 'rev-parse', 'HEAD')
            (self.root / 'source.txt').write_text('remote update\n')
            self.run_git(self.root, 'commit', '-am', 'remote update')
            self.assertEqual(module.sync(self.root), 0)
            remote_head = self.run_git(self.remote, 'rev-parse', 'main')
            self.run_git(self.root, 'checkout', '-B', 'main', first)
            (self.root / 'source.txt').write_text('conflicting local update\n')
            self.run_git(self.root, 'commit', '-am', 'local update')
            self.assertEqual(module.sync(self.root), 1)
            self.assertEqual(self.run_git(self.remote, 'rev-parse', 'main'), remote_head)

if __name__ == '__main__':
    unittest.main()
