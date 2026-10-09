#!/usr/bin/env python3
"""Persist an already-verified BBR configuration; never install or restart anything.

Use only after checking the installed kernel and live connections. Existing
unrelated configuration and later changes are deliberately refused.
"""
import argparse
import base64
import json
import os
from pathlib import Path
import subprocess
import tempfile


FILES = {
    'etc/modules-load.d/yuanze-bbr.conf': b'# Yuanze verified transport configuration\ntcp_bbr\n',
    'etc/sysctl.d/99-yuanze-bbr.conf': b'# Yuanze verified transport configuration\nnet.ipv4.tcp_congestion_control = bbr\n',
}


def read_file(path):
    if path.is_symlink():
        raise ValueError('Configuration must not be a symlink')
    if not path.exists():
        return None
    if not path.is_file():
        raise ValueError('Configuration must be a regular file')
    return {'bytes': base64.b64encode(path.read_bytes()).decode(),
            'mode': path.stat().st_mode & 0o777}


def plan(root):
    before = {}
    for name, content in FILES.items():
        path = root / name
        old = read_file(path)
        if old is not None and base64.b64decode(old['bytes']) != content:
            raise ValueError('Existing configuration belongs to another change')
        before[name] = old
    # Refuse an existing policy that could compete with this setting at boot.
    for folder in ('etc/sysctl.d', 'run/sysctl.d', 'usr/local/lib/sysctl.d', 'usr/lib/sysctl.d'):
        for path in (root / folder).glob('*.conf'):
            if path == root / 'etc/sysctl.d/99-yuanze-bbr.conf':
                continue
            for line in path.read_text().splitlines():
                line = line.split('#', 1)[0].split(';', 1)[0].strip()
                key, sep, value = line.partition('=')
                key = key.strip().lstrip('-').replace('/', '.')
                if sep and key == 'net.ipv4.tcp_congestion_control' and value.strip() != 'bbr':
                    raise ValueError('Conflicting boot congestion-control policy')
    return before


def atomic_write(path, data, mode=0o644):
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, name = tempfile.mkstemp(prefix='.yuanze-transport-', dir=path.parent)
    try:
        with os.fdopen(fd, 'wb') as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
            os.fchmod(stream.fileno(), mode)
        os.replace(name, path)
    finally:
        if Path(name).exists():
            Path(name).unlink()


def restore(root, before, changed=None):
    names = list(FILES if changed is None else changed)
    # Check every target before restoring any, to preserve subsequent edits.
    for name in names:
        path = root / name
        now = read_file(path)
        if now is None or now['mode'] != 0o644 or base64.b64decode(now['bytes']) != FILES[name]:
            raise ValueError('Configuration changed after deployment; refusing rollback')
    for name in reversed(names):
        path, old = root / name, before[name]
        if old is None:
            path.unlink()
        else:
            atomic_write(path, base64.b64decode(old['bytes']), old['mode'])


def persist(root, backup, verify):
    before = plan(root)
    # Verification must succeed before any persistent configuration is touched.
    verify()
    backup.mkdir(mode=0o700, parents=False, exist_ok=False)
    saved = backup / 'before.json'
    atomic_write(saved, json.dumps(before, indent=2).encode(), 0o600)
    changed = []
    try:
        for name, content in FILES.items():
            if read_file(root / name) != before[name]:
                raise ValueError('Configuration changed after preflight')
            atomic_write(root / name, content)
            changed.append(name)
        verify()
    except BaseException:
        restore(root, before, changed)
        raise
    return {'persisted': True, 'files': sorted(FILES), 'backup': str(backup)}


def verify_kernel():
    control = subprocess.check_output(['sysctl', '-n', 'net.ipv4.tcp_congestion_control'], text=True).strip()
    available = subprocess.check_output(['sysctl', '-n', 'net.ipv4.tcp_available_congestion_control'], text=True).split()
    if control != 'bbr' or 'bbr' not in available or not Path('/sys/module/tcp_bbr').is_dir():
        raise ValueError('Verify the installed BBR module and live setting first')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=['persist', 'restore-files'])
    parser.add_argument('--backup', required=True, type=Path)
    args = parser.parse_args()
    if os.geteuid() != 0:
        raise SystemExit('Run on the verified Linux server as root')
    if args.action == 'persist':
        print(json.dumps(persist(Path('/'), args.backup, verify_kernel)))
    else:
        restore(Path('/'), json.loads((args.backup / 'before.json').read_text()))
        print(json.dumps({'restoredFiles': True, 'runtimeChanged': False}))


if __name__ == '__main__':
    main()
