#!/usr/bin/env python3
"""Reproduce audited display/native image bindings without changing images."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'server-reference'))
from search_views import PROVENANCE_FILENAME, reviewed_search_views


def digest(path):
    result = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            result.update(block)
    return result.hexdigest()


def source_file(private, name):
    path = private / name
    if path.is_symlink() or not path.resolve().is_relative_to((private / 'media').resolve()) or not path.is_file():
        raise ValueError('Reviewed image is missing or outside the private media directory: ' + name)
    return path


def build_provenance(private, public, records):
    private, public = Path(private).resolve(), Path(public).resolve()
    views = reviewed_search_views(public, records)
    if not views:
        raise ValueError('No active reviewed image views found; refusing an empty provenance publication')
    native_hashes = {}
    # Verify every original review first. A failed native check must never
    # produce a partial file authorizing previously unverified derivatives.
    for view in views:
        name = view['review_native_path']
        if name not in native_hashes:
            native_hashes[name] = digest(source_file(private, name))
        if native_hashes[name] != view['review_sha256']:
            raise ValueError('Reviewed native image checksum mismatch: ' + name)
    delivered_hashes, bindings = {}, {}
    for view in views:
        name = view['path']
        if name not in delivered_hashes:
            delivered_hashes[name] = digest(source_file(private, name))
        key = (name, view['review_native_path'], view['review_sha256'])
        bindings[key] = {'path': name, 'sha256': delivered_hashes[name],
                         'native_path': view['review_native_path'],
                         'native_sha256': view['review_sha256']}
    return {'version': 1, 'entries': [bindings[key] for key in sorted(bindings)]}, len(views)


def save(path, document):
    path = Path(path).resolve()
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(mode='w', encoding='utf-8', dir=path.parent,
                                     prefix=path.name + '.', delete=False) as stream:
        temporary = Path(stream.name)
        try:
            json.dump(document, stream, ensure_ascii=False, indent=2, sort_keys=True)
            stream.write('\n')
        except BaseException:
            temporary.unlink(missing_ok=True)
            raise
    try:
        temporary.chmod(0o644)
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--records', type=Path, required=True, help='Current active catalogue JSON snapshot')
    parser.add_argument('--private', type=Path, default=ROOT / 'server-reference/private')
    parser.add_argument('--public', type=Path, default=ROOT / 'server-reference/public')
    parser.add_argument('--output', type=Path, default=ROOT / 'server-reference' / PROVENANCE_FILENAME)
    parser.add_argument('--expect-views', type=int, help='Abort if the audited view count changes')
    arguments = parser.parse_args()
    records = json.loads(arguments.records.read_text(encoding='utf-8'))
    document, view_count = build_provenance(arguments.private, arguments.public, records)
    if arguments.expect_views is not None and view_count != arguments.expect_views:
        raise ValueError('Reviewed view count changed; inspect before publishing provenance')
    save(arguments.output, document)
    print(json.dumps({'reviewedViews': view_count, 'bindings': len(document['entries']),
                      'provenanceSha256': digest(arguments.output)}, ensure_ascii=False))


if __name__ == '__main__':
    main()
