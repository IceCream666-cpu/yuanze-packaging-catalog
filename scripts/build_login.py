#!/usr/bin/env python3
"""Build the approved login only, or check its reproducible source/file receipt."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / 'docs/login-immersive-demo'
DESTINATION = ROOT / 'server-reference/public/login-ui'
VERSION = 'yuanze2.0.3'


def sha(data):
    return hashlib.sha256(data).hexdigest()


def source_hash():
    paths = [*sorted((SOURCE / 'src').glob('*')), SOURCE / 'index.html',
             SOURCE / 'vite.config.js', SOURCE / 'package.json', SOURCE / 'pnpm-lock.yaml',
             SOURCE / 'assets/login-glow.mp4', SOURCE / 'assets/login-glow-poster.jpg',
             ROOT / 'server-reference/public/api-client.js']
    return sha(b''.join(path.relative_to(ROOT).as_posix().encode() + b'\0' + path.read_bytes() for path in paths))


def manifest():
    files = {p.relative_to(DESTINATION).as_posix(): {'sha256': sha(p.read_bytes()), 'bytes': p.stat().st_size}
             for p in sorted(DESTINATION.rglob('*')) if p.is_file() and p.name != 'bundle-manifest.json'}
    assert set(files) >= {'index.html', 'login.js'}, 'Missing login entrypoints'
    assert len(files) == 5, 'Only HTML, JS, CSS, one video and one poster may ship'
    assert sorted(Path(name).suffix for name in files) == ['.css', '.html', '.jpg', '.js', '.mp4']
    return {'schema': 1, 'version': VERSION, 'sourceSha256': source_hash(), 'files': files}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args()
    if not args.check:
        node = os.environ.get('NODE_BIN') or shutil.which('node')
        if not node:
            raise SystemExit('Node.js is required; set NODE_BIN.')
        subprocess.run([node, 'node_modules/vite/bin/vite.js', 'build', '--mode', 'release'], cwd=SOURCE, check=True)
        (DESTINATION / 'bundle-manifest.json').write_text(json.dumps(manifest(), indent=2) + '\n')
    assert json.loads((DESTINATION / 'bundle-manifest.json').read_text()) == manifest(), 'Stale login build; run scripts/build_login.py'
    print(f'{VERSION}: source and 5 production files verified.')


if __name__ == '__main__':
    main()
