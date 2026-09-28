#!/usr/bin/env python3
"""Refuse to start an old release while active accounts use newer roles.

Run as ExecStartPre before server.py.  This reads source syntax without
importing the application or exposing account or session data.
"""
import argparse
import ast
from pathlib import Path
import sqlite3
import sys


def supported_roles(source):
    tree = ast.parse(Path(source).read_text(encoding='utf-8'))
    for node in tree.body:
        if isinstance(node, ast.Assign) and any(
            isinstance(target, ast.Name) and target.id == 'SUPPORTED_ROLES'
            for target in node.targets
        ):
            roles = ast.literal_eval(node.value)
            if not isinstance(roles, (set, frozenset)) or not roles or not all(
                isinstance(role, str) for role in roles
            ):
                raise ValueError('Invalid supported role declaration')
            return roles
    # Releases before the client role supported only these two roles.
    return {'employee', 'admin'}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--source', default='/opt/yuanze-reference/current/server.py')
    parser.add_argument('--database', default='/var/lib/yuanze-reference/catalog.sqlite')
    args = parser.parse_args()
    try:
        supported = supported_roles(args.source)
        with sqlite3.connect(f'file:{args.database}?mode=ro', uri=True, timeout=5) as db:
            active = {
                row[0] for row in db.execute('SELECT DISTINCT role FROM admin_users WHERE active=1')
            }
        incompatible = sorted(active - supported)
        if incompatible:
            print('Release cannot serve active account roles: ' + ', '.join(incompatible), file=sys.stderr)
            return 1
    except (OSError, SyntaxError, ValueError, sqlite3.Error) as error:
        print('Cannot verify account role compatibility: ' + type(error).__name__, file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
