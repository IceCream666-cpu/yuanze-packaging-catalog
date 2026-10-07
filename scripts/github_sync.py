#!/usr/bin/env python3
"""Push completed commits only. Never stage, commit, pull, reset or force push."""
import argparse
import fcntl
import json
from pathlib import Path
import shlex
import subprocess
import sys
from datetime import datetime, timezone

REMOTE = 'https://github.com/IceCream666-cpu/yuanze-packaging-catalog.git'
MARKER = '# yuanze-github-auto-sync-v1'

def git(root, *args):
    return subprocess.check_output(['git', '-C', str(root), *args], text=True, timeout=45).strip()

def install(root):
    root = Path(git(root, 'rev-parse', '--show-toplevel'))
    hooks = Path(git(root, 'rev-parse', '--git-path', 'hooks'))
    if not hooks.is_absolute():
        hooks = root / hooks
    hook = hooks / 'post-commit'
    if hook.exists() and MARKER not in hook.read_text():
        raise RuntimeError('Existing post-commit hook must be integrated manually; it was preserved.')
    hooks.mkdir(parents=True, exist_ok=True)
    command = shlex.join([sys.executable, str(root / 'scripts/github_sync.py'), '--root', str(root)])
    hook.write_text('#!/bin/sh\n' + MARKER + '\n' + command + '\n# Upload errors do not undo the local commit.\nexit 0\n')
    hook.chmod(0o755)
    print('Installed repository-local automatic upload hook.')

def sync(root):
    root = Path(git(root, 'rev-parse', '--show-toplevel'))
    git_dir = Path(git(root, 'rev-parse', '--absolute-git-dir'))
    log = git_dir / 'github-sync-status.json'
    with (git_dir / 'github-sync.lock').open('a') as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            return 0
        result = {'time': datetime.now(timezone.utc).isoformat(), 'ok': False}
        try:
            if git(root, 'remote', 'get-url', '--push', 'origin') != REMOTE:
                raise RuntimeError('Unexpected GitHub destination; upload stopped.')
            branch = git(root, 'symbolic-ref', '--short', 'HEAD')
            for _ in range(5):
                head = git(root, 'rev-parse', 'HEAD')
                if git(root, 'symbolic-ref', '--short', 'HEAD') != branch:
                    raise RuntimeError('Branch changed during upload; retry on the next commit.')
                subprocess.run(['git', '-C', str(root), 'push', '--porcelain', 'origin', f'{head}:refs/heads/{branch}'], check=True, timeout=45, capture_output=True, text=True)
                result.update(branch=branch, commit=head, ok=True)
                if git(root, 'rev-parse', 'HEAD') == head:
                    break
            else:
                raise RuntimeError('New commits still arriving; retry upload.')
            print('GitHub automatic upload completed: ' + head[:8])
            return 0
        except (subprocess.SubprocessError, RuntimeError) as error:
            result.update(ok=False, error=type(error).__name__)
            print('GitHub upload failed. Local commits are safe; retry scripts/github_sync.py after resolving network or Git divergence.', file=sys.stderr)
            return 1
        finally:
            log.write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n')

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--root', default=Path(__file__).resolve().parents[1], type=Path)
    parser.add_argument('--install', action='store_true')
    args = parser.parse_args()
    if args.install:
        install(args.root)
        return 0
    return sync(args.root)

if __name__ == '__main__':
    sys.exit(main())
