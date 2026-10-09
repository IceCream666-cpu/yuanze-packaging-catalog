"""Deployment failures and rollback must not overwrite other boot policies."""
import importlib.util
from pathlib import Path
import tempfile
import unittest

spec = importlib.util.spec_from_file_location('persist_bbr', Path(__file__).parents[1] / 'persist_bbr.py')
transport = importlib.util.module_from_spec(spec)
spec.loader.exec_module(transport)


class Persistence(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.backup = self.root / 'backup'

    def test_persist_and_restore_absent_files(self):
        checks = []
        result = transport.persist(self.root, self.backup, lambda: checks.append(True))
        self.assertTrue(result['persisted'])
        self.assertEqual(len(checks), 2)
        self.assertEqual((self.backup / 'before.json').stat().st_mode & 0o777, 0o600)
        for name, expected in transport.FILES.items():
            self.assertEqual((self.root / name).read_bytes(), expected)
        import json
        transport.restore(self.root, json.loads((self.backup / 'before.json').read_text()))
        self.assertTrue(all(not (self.root / name).exists() for name in transport.FILES))

    def test_preflight_failure_writes_nothing(self):
        def fail():
            raise RuntimeError('Kernel verification failed')
        with self.assertRaises(RuntimeError):
            transport.persist(self.root, self.backup, fail)
        self.assertFalse(self.backup.exists())
        self.assertTrue(all(not (self.root / name).exists() for name in transport.FILES))

    def test_postflight_failure_restores_preexisting_mode(self):
        name = next(iter(transport.FILES))
        path = self.root / name
        path.parent.mkdir(parents=True)
        path.write_bytes(transport.FILES[name]);path.chmod(0o640)
        calls = []
        def verify():
            calls.append(True)
            if len(calls) == 2:
                raise RuntimeError('Postflight failed')
        with self.assertRaises(RuntimeError):
            transport.persist(self.root, self.backup, verify)
        self.assertEqual(path.read_bytes(), transport.FILES[name])
        self.assertEqual(path.stat().st_mode & 0o777, 0o640)
        self.assertFalse((self.root / 'etc/sysctl.d/99-yuanze-bbr.conf').exists())

    def test_unrelated_target_refused_without_any_writes(self):
        path = self.root / 'etc/sysctl.d/99-yuanze-bbr.conf'
        path.parent.mkdir(parents=True);path.write_text('private existing config')
        with self.assertRaises(ValueError):
            transport.persist(self.root, self.backup, lambda: None)
        self.assertEqual(path.read_text(), 'private existing config')
        self.assertFalse(self.backup.exists())

    def test_conflicting_policy_refused_in_each_boot_directory(self):
        for folder in ('etc/sysctl.d', 'run/sysctl.d', 'usr/local/lib/sysctl.d', 'usr/lib/sysctl.d'):
            with self.subTest(folder=folder):
                path = self.root / folder / 'other.conf'
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text('-net/ipv4/tcp_congestion_control = cubic # existing policy\n')
                with self.assertRaises(ValueError):
                    transport.plan(self.root)
                path.unlink()

    def test_comments_and_matching_policy_do_not_conflict(self):
        path = self.root / 'etc/sysctl.d/other.conf'
        path.parent.mkdir(parents=True)
        path.write_text('# net.ipv4.tcp_congestion_control = cubic\nnet.ipv4.tcp_congestion_control = bbr\nnet.core.default_qdisc = fq_codel\n')
        transport.persist(self.root, self.backup, lambda: None)
        self.assertIn('fq_codel', path.read_text())

    def test_rollback_preflights_all_files_before_touching_any(self):
        before = transport.plan(self.root)
        transport.persist(self.root, self.backup, lambda: None)
        names = list(transport.FILES)
        (self.root / names[-1]).write_text('later user change')
        with self.assertRaises(ValueError):
            transport.restore(self.root, before)
        self.assertEqual((self.root / names[0]).read_bytes(), transport.FILES[names[0]])
        self.assertEqual((self.root / names[-1]).read_text(), 'later user change')

    def test_symlink_target_refused(self):
        target = self.root / 'unrelated';target.write_text('untouched')
        path = self.root / next(iter(transport.FILES));path.parent.mkdir(parents=True)
        path.symlink_to(target)
        with self.assertRaises(ValueError):
            transport.plan(self.root)
        self.assertEqual(target.read_text(), 'untouched')

    def test_backup_cannot_be_reused(self):
        transport.persist(self.root, self.backup, lambda: None)
        with self.assertRaises(FileExistsError):
            transport.persist(self.root, self.backup, lambda: None)

    def test_change_during_preflight_is_preserved(self):
        name = next(iter(transport.FILES));path = self.root / name
        def concurrent_edit():
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text('another operator changed this file')
        with self.assertRaises(ValueError):
            transport.persist(self.root, self.backup, concurrent_edit)
        self.assertEqual(path.read_text(), 'another operator changed this file')
        self.assertFalse((self.root / 'etc/sysctl.d/99-yuanze-bbr.conf').exists())

    def test_rollback_preserves_later_permission_changes(self):
        before = transport.plan(self.root)
        transport.persist(self.root, self.backup, lambda: None)
        path = self.root / next(iter(transport.FILES));path.chmod(0o640)
        with self.assertRaises(ValueError):
            transport.restore(self.root, before)
        self.assertEqual(path.stat().st_mode & 0o777, 0o640)


if __name__ == '__main__':
    unittest.main()
