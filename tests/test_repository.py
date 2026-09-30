"""Ensure credentials/runtime data stay out of a fresh Git checkout."""
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]

class RepositoryBoundaries(unittest.TestCase):
    def test_private_paths_are_ignored_but_source_remains_trackable(self):
        private = ['.secrets/key', '.env', 'server-reference/state/catalog.sqlite',
                   'server-reference/private/media/quote.png', 'server-reference/private/catalog.json',
                   'auth.json', 'admin-bootstrap.json', 'server.pem', '员工登录信息.txt',
                   'node_modules/jsdom/index.js', 'work/audit.json', 'outputs/export.xlsx']
        source = ['AGENTS.md', 'README.md', 'server-reference/server.py',
                  'server-reference/public/client.js', 'server-reference/public/brand/yuanze-mark.svg',
                  'site/dist/workflow.mjs', 'tests/frontend/client-ui-tests.cjs', '.env.example']
        with tempfile.TemporaryDirectory() as folder:
            subprocess.run(['git', 'init', '-q', folder], check=True)
            Path(folder, '.gitignore').write_bytes((ROOT/'.gitignore').read_bytes())
            for path in private + source:
                result = subprocess.run(['git', 'check-ignore', '-q', '--no-index', path], cwd=folder)
                self.assertEqual(result.returncode, 0 if path in private else 1, path)

    def test_real_credentials_and_runtime_files_are_not_tracked(self):
        result = subprocess.run(['git', 'ls-files', '-z', '--cached'], cwd=ROOT, capture_output=True, check=True)
        tracked = [name for name in result.stdout.decode().split('\0') if name]
        if tracked:
            result = subprocess.run(['git', 'check-ignore', '--no-index', '--stdin'], cwd=ROOT,
                                    input='\n'.join(tracked)+'\n', text=True, capture_output=True)
            self.assertIn(result.returncode, (0, 1), result.stderr)
            self.assertEqual(result.stdout, '', 'Ignored files were force-added to Git')

    def test_history_does_not_publish_previously_removed_private_files(self):
        # A clean working tree is insufficient: push also transfers older commits.
        commits = subprocess.run(['git', 'rev-list', '--all'], cwd=ROOT,
                                 capture_output=True, text=True, check=True)
        historical_paths = set()
        for commit in commits.stdout.splitlines():
            tree = subprocess.run(['git', 'ls-tree', '-r', '-z', '--name-only', commit],
                                  cwd=ROOT, capture_output=True, text=True, check=True)
            historical_paths.update(name for name in tree.stdout.split('\0') if name)
        if historical_paths:
            checked = subprocess.run(['git', 'check-ignore', '--no-index', '--stdin', '-z'],
                                     cwd=ROOT, input='\0'.join(sorted(historical_paths))+'\0',
                                     text=True, capture_output=True)
            self.assertIn(checked.returncode, (0, 1), checked.stderr)
            self.assertEqual(checked.stdout, '', 'Private or runtime paths exist in Git history')

if __name__ == '__main__':
    unittest.main()
