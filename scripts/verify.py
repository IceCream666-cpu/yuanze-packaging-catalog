#!/usr/bin/env python3
"""Run local, synthetic regression suites before committing. No production calls."""
import os
from pathlib import Path
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]

def run(command, cwd=ROOT):
    print('+ ' + ' '.join(map(str, command)), flush=True)
    subprocess.run(command, cwd=cwd, check=True)

def main():
    # Fail rather than silently skipping optional image regression tests.
    for module in ('PIL', 'numpy', 'openpyxl', 'defusedxml'):
        __import__(module)
    node = os.environ.get('NODE_BIN') or shutil.which('node')
    if not node:
        raise SystemExit('Node.js is required; add it to PATH or set NODE_BIN.')
    run([sys.executable, '-m', 'unittest', 'discover', '-s', 'tests', '-q'])
    run([sys.executable, '-m', 'unittest', 'discover', '-s', '.', '-p', 'test_*.py', '-q'], ROOT/'server-reference')
    run([sys.executable, '-m', 'unittest', 'discover', '-s', 'server-reference/deploy/tests', '-q'])
    run([node, '--experimental-vm-modules', 'tests/frontend/run.mjs'])
    run([node, '--test', *map(str, sorted((ROOT / 'docs/client-apple-demo/tests').glob('*.test.mjs')))])
    run([node, '--test', *map(str, sorted((ROOT / 'docs/client-motion-demo/tests').glob('*.test.mjs')))])
    run([node, 'docs/client-motion-demo/node_modules/tsx/dist/cli.mjs', '--test', *map(str, sorted((ROOT / 'docs/client-motion-demo/tests').glob('*.test.jsx')))])
    run([sys.executable, 'scripts/build_customer_showroom.py', '--check'])
    run([sys.executable, 'scripts/build_login.py', '--check'])
    login = ROOT / 'docs/login-immersive-demo'
    run([node, 'node_modules/vite/bin/vite.js', 'build'], login)
    run([node, 'node_modules/tsx/dist/cli.mjs', '--test', *map(str, sorted((login / 'tests').glob('*.test.*')))], login)
    run(['git', 'diff', '--check'])
    run(['git', 'diff', '--cached', '--check'])
    print('All verification suites passed.', flush=True)

if __name__ == '__main__':
    main()
