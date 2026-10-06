#!/usr/bin/env python3
"""Plan and publish visually reviewed image edits; never generate or edit pixels.

Image generation uses the built-in imagegen tool separately. Production writes
use the administrator API, its version checks and image-only audit action.
"""
import argparse
import base64
from copy import deepcopy
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
SCOPES = {'single_product', 'same_style_variants', 'source_page', 'unresolved'}


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def write_private(path, data):
    path = Path(path)
    path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    temporary = path.with_name(path.name + '.next')
    with temporary.open('w') as stream:
        os.chmod(temporary, 0o600)
        json.dump(data, stream, ensure_ascii=False, indent=2)
        stream.write('\n')
    temporary.replace(path)


def plan(records, private):
    private = Path(private).resolve()
    jobs = {}
    for record in records:
        if record.get('archived') or record.get('kind') not in {'package', 'source_page'}:
            continue
        for image in record.get('images', []):
            name = image.get('path', '')
            target = (private / name).resolve()
            if image.get('missing') or not name.startswith('media/') or not target.is_relative_to(private) or not target.is_file():
                continue
            if name not in jobs:
                jobs[name] = {'sourcePath': name, 'sourceFile': str(target), 'sourceSHA256': sha(target),
                              'status': 'pending', 'scopes': [], 'records': [], 'clientApproved': False}
            job = jobs[name]
            scope = image.get('imageScope', 'unresolved')
            if scope not in SCOPES:
                scope = 'unresolved'
            if scope not in job['scopes']:
                job['scopes'].append(scope)
            ref = {'id': record['id'], 'code': record.get('productCode'), 'kind': record['kind']}
            if ref not in job['records']:
                job['records'].append(ref)
            job['clientApproved'] |= bool(image.get('clientVisible'))
    return sorted(jobs.values(), key=lambda j: (not j['clientApproved'], 'single_product' not in j['scopes'], j['sourcePath']))


def validate_edit(edit):
    if edit.get('status') != 'reviewed' or not all(edit.get('qa', {}).get(k) is True for k in ('identity', 'count', 'watermarks')):
        raise ValueError('Visual review must pass before publishing')
    if edit.get('scope') not in SCOPES:
        raise ValueError('Invalid image scope')
    for field, checksum in [('sourceFile', 'sourceSHA256'), ('outputFile', 'outputSHA256')]:
        if sha(edit[field]) != edit[checksum]:
            raise ValueError('Image changed after review: ' + field)
    if Path(edit['sourceFile']).resolve() == Path(edit['outputFile']).resolve():
        raise ValueError('Original image cannot be overwritten')
    from PIL import Image
    with Image.open(edit['outputFile']) as image:
        image.verify()
    with Image.open(edit['outputFile']) as image:
        if min(image.size) < 256 or max(image.size) > 4000:
            raise ValueError('Output dimensions outside publishing limits')


def image_patch(record, edit, uploaded):
    original = [i for i in record.get('images', []) if i.get('path') == edit['sourcePath']]
    if not original:
        return None
    if any(i.get('path') == uploaded['path'] for i in record.get('images', [])):
        return None
    if len(record.get('images', [])) >= 30:
        raise ValueError('Keep original gallery: cannot exceed 30 images')
    customer = (any(i.get('clientVisible') for i in original)
                and edit['qa'].get('clientSafe') is True
                and edit['scope'] in {'single_product', 'same_style_variants'})
    fresh = {**uploaded, 'role': 'product', 'imageScope': edit['scope'],
             'caption': 'AI优化主图 · 原图保留供核对', 'clientVisible': customer}
    images = deepcopy(record.get('images', []))
    # Supplier/price watermarks on the original remain staff-only once replaced.
    for image in images:
        if image.get('path') == edit['sourcePath']:
            image['clientVisible'] = False
    return {'action': 'images', 'id': record['id'], 'version': record['version'], 'images': [fresh, *images]}


def unchanged_product(before, after):
    ignored = {'images', 'version', 'updated'}
    return ({k: v for k, v in before.items() if k not in ignored}
            == {k: v for k, v in after.items() if k not in ignored})


def publish(manifest, credentials, origin):
    spec = importlib.util.spec_from_file_location('image_batch_gate', ROOT / 'server-reference/deploy/release_gate.py')
    gate = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(gate)
    path = Path(manifest)
    state = json.loads(path.read_text())
    # Validate every selected output before creating a production upload.
    edits = [e for e in state['edits'] if e.get('status') == 'reviewed']
    for edit in edits:
        validate_edit(edit)
    browser = gate.Client(origin, 90, False, None)
    try:
        gate.expect_status(browser, '/api/login', 200, gate.load_credentials(Path(credentials)))
        _, body = gate.expect_status(browser, '/api/session', 200)
        session = json.loads(body)
        if session['role'] != 'admin':
            raise ValueError('Administrator account required')
        browser.csrf = session['csrf']
        _, body = gate.expect_status(browser, '/api/admin/records', 200)
        records = {r['id']: r for r in json.loads(body)['items']}
        snapshot = path.with_name('before-images.json')
        if not snapshot.exists():
            write_private(snapshot, list(records.values()))
        count = 0
        for edit in edits:
            if not edit.get('uploaded'):
                raw = Path(edit['outputFile']).read_bytes()
                image = 'data:image/png;base64,' + base64.b64encode(raw).decode('ascii')
                _, body = gate.expect_status(browser, '/api/admin/uploads', 201, {'image': image})
                edit['uploaded'] = json.loads(body)['image']
                write_private(path, state)
            saved = edit.setdefault('publishedRecords', [])
            matches = [r for r in records.values() if not r.get('archived') and r.get('kind') in {'package', 'source_page'}
                       and any(i.get('path') == edit['sourcePath'] for i in r.get('images', []))]
            for before in matches:
                payload = image_patch(before, edit, edit['uploaded'])
                if payload is None:
                    continue
                _, body = gate.expect_status(browser, '/api/admin/records', 200, payload)
                after = json.loads(body)
                if not unchanged_product(before, after):
                    raise RuntimeError('Unexpected non-image product change; stop batch')
                records[before['id']] = after
                saved.append({'id': before['id'], 'code': before.get('productCode'), 'version': after['version']})
                count += 1
                write_private(path, state)
            edit['status'] = 'published'
            write_private(path, state)
        print(json.dumps({'publishedImages': len(edits), 'updatedRecords': count}))
    finally:
        if browser.csrf:
            try:
                gate.expect_status(browser, '/api/logout', 200, {})
            except Exception:
                pass
        browser.jar.clear()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    inventory = sub.add_parser('plan')
    inventory.add_argument('--catalog', required=True)
    inventory.add_argument('--private', required=True)
    inventory.add_argument('--out', required=True)
    live = sub.add_parser('publish')
    live.add_argument('--manifest', required=True)
    live.add_argument('--credentials', required=True)
    live.add_argument('--origin', required=True)
    args = parser.parse_args()
    if args.command == 'plan':
        catalog = json.loads(Path(args.catalog).read_text())
        jobs = plan(catalog.get('items', catalog.get('records', [])), args.private)
        write_private(args.out, {'jobs': jobs})
        print(json.dumps({'images': len(jobs), 'records': len({r['id'] for j in jobs for r in j['records']})}))
    else:
        publish(args.manifest, args.credentials, args.origin)


if __name__ == '__main__':
    main()
