#!/usr/bin/env python3
"""Build the authenticated customer company pages from the reviewed preview.

Only the reviewed frontend entrypoints and checksum-verified company assets are
included. Catalogue snapshots, local credentials and preview servers are never
copied. Run --check in verification to detect a stale deployment bundle.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / 'docs/mobile-client-preview'
DESTINATION = ROOT / 'server-reference/public/showroom'
ENTRYPOINTS = ('index.html', 'preview.css', 'preview.js', 'company-content.js', 'product-posters.js')
ASSET_PATH = re.compile(r'[A-Za-z0-9_./-]+\.(?:png|jpg|jpeg|webp|svg|pdf)')
CLIENT = ROOT / 'docs/client-apple-demo'
CLIENT_ENTRYPOINTS = ('index.html', 'preview.js', 'preview.css')


def client_source_hash():
    sources = [*sorted((CLIENT / 'src').glob('*')), CLIENT / 'index.html',
               CLIENT / 'vite.config.js', CLIENT / 'package.json', CLIENT / 'assets-manifest.json']
    digest = hashlib.sha256()
    for path in sources:
        digest.update(path.relative_to(CLIENT).as_posix().encode() + b'\0' + path.read_bytes())
    return digest.hexdigest()


def stamp_client_release():
    files = {name: hashlib.sha256((CLIENT / 'release' / name).read_bytes()).hexdigest()
             for name in CLIENT_ENTRYPOINTS}
    (CLIENT / 'release/build.json').write_text(json.dumps({
        'version': 'client1.0', 'sourceSha256': client_source_hash(), 'files': files,
    }, indent=2) + '\n')


def client_files(files):
    """Overlay only the client entrypoints; preserve all reviewed media."""
    files = dict(files)
    stamp = json.loads((CLIENT / 'release/build.json').read_text())
    if stamp['sourceSha256'] != client_source_hash():
        raise ValueError('client1.0 source changed: rebuild and stamp the release first')
    for name in CLIENT_ENTRYPOINTS:
        data = source_file(CLIENT / 'release', name).read_bytes()
        if hashlib.sha256(data).hexdigest() != stamp['files'][name]:
            raise ValueError(f'client1.0 release checksum mismatch: {name}')
        files[name] = data
    paths = json.loads((CLIENT / 'src/asset-paths.json').read_text())
    approved = json.loads((CLIENT / 'assets-manifest.json').read_text())
    for item in approved['files']:
        route = paths['/' + item['target']]
        if not route.startswith('/showroom/assets/') or '..' in route.split('/'):
            raise ValueError('Invalid client media route')
        data = files.get(route.removeprefix('/showroom/'), b'')
        if len(data) != item['bytes'] or hashlib.sha256(data).hexdigest() != item['sha256']:
            raise ValueError('Client media differs from reviewed showroom media')
    files.pop('bundle-manifest.json')
    bundle = {'schema': 1, 'source': 'docs/client-apple-demo', 'version': 'client1.0',
              'files': {name: {'sha256': hashlib.sha256(data).hexdigest(), 'bytes': len(data)}
                        for name, data in sorted(files.items())}}
    files['bundle-manifest.json'] = (json.dumps(bundle, ensure_ascii=False, sort_keys=True, indent=2) + '\n').encode()
    return files


def source_file(source, name):
    path = (source / name).resolve()
    if not path.is_relative_to(source.resolve()) or not path.is_file():
        raise ValueError(f'Invalid showroom source: {name}')
    return path


def expected_files(source=SOURCE, edition='legacy'):
    source = Path(source)
    files = {}
    for name in ENTRYPOINTS:
        text = source_file(source, name).read_text(encoding='utf-8')
        if name == 'index.html':
            def production_tag(match):
                attributes = re.sub(r'\sdata-mode=[\"\'][^\"\']*[\"\']', '', match[2])
                return match[1] + ' data-mode="production"' + attributes
            text, count = re.subn(r'(<html\b)([^>]*>)', production_tag, text, count=1)
            if count != 1:
                raise ValueError('Showroom HTML entrypoint is missing its html element')
            for entry in ENTRYPOINTS[1:]:
                text = text.replace(f'="{entry}"', f'="/showroom/{entry}"')
                text = text.replace(f"='{entry}'", f"='/showroom/{entry}'")
            text = text.replace('="assets/', '="/showroom/assets/').replace("='assets/", "='/showroom/assets/")
            # This stable route is the original safe customer catalogue, embedded
            # as the separate Products page instead of recursively loading Home.
            text = text.replace('/client?showroom=1', '/client/products?showroom=1')
        elif name in {'company-content.js', 'product-posters.js'}:
            # Preserve the reviewed content and translations byte-for-byte
            # apart from relocatable media references.
            text = text.replace("'assets/", "'/showroom/assets/").replace('"assets/', '"/showroom/assets/')
        files[name] = text.encode('utf-8')
    # The login-protected HTML can paint without a second render-blocking CSS
    # request. One deferred script preserves data-before-controller execution
    # without waiting for three separate responses on mobile networks.
    html = files['index.html'].decode('utf-8')
    html = html.replace('<link rel="stylesheet" href="/showroom/preview.css">',
                        '<style data-showroom-styles>' + files['preview.css'].decode('utf-8') + '</style>')
    for entry in ('company-content.js', 'product-posters.js'):
        html = html.replace(f'  <script defer src="/showroom/{entry}"></script>\n', '')
    files['index.html'] = html.encode('utf-8')
    files['preview.js'] = b'\n'.join(files[name] for name in
                                   ('company-content.js', 'product-posters.js', 'preview.js'))
    manifest = json.loads(source_file(source, 'assets/manifest.json').read_text(encoding='utf-8'))
    for item in manifest['files']:
        name = item.get('path')
        if not isinstance(name, str) or not ASSET_PATH.fullmatch(name) or '..' in name.split('/') or name.startswith('/'):
            raise ValueError('Company asset manifest contains an invalid path')
        path = 'assets/' + name
        if path in files:
            raise ValueError(f'Duplicate company asset: {name}')
        data = source_file(source, path).read_bytes()
        if hashlib.sha256(data).hexdigest() != item.get('sha256') or len(data) != item.get('bytes'):
            raise ValueError(f'Company asset checksum mismatch: {name}')
        files[path] = data
    bundle = {'schema': 1, 'source': 'docs/mobile-client-preview',
              'files': {name: {'sha256': hashlib.sha256(data).hexdigest(), 'bytes': len(data)}
                        for name, data in sorted(files.items())}}
    files['bundle-manifest.json'] = (json.dumps(bundle, ensure_ascii=False, sort_keys=True, indent=2) + '\n').encode()
    return client_files(files) if edition == 'client1' else files


def check(source=SOURCE, destination=DESTINATION, edition='legacy'):
    destination = Path(destination)
    expected = expected_files(source, edition)
    actual = {path.relative_to(destination).as_posix() for path in destination.rglob('*') if path.is_file() or path.is_symlink()}
    stale = sorted(actual.symmetric_difference(expected))
    for name, data in expected.items():
        path = destination / name
        if not path.is_file() or path.is_symlink() or path.read_bytes() != data:
            stale.append(name)
    return sorted(set(stale))


def build(source=SOURCE, destination=DESTINATION, edition='legacy'):
    destination = Path(destination)
    if destination.name != 'showroom' or destination.is_symlink():
        raise ValueError('Destination must be a dedicated showroom directory')
    files = expected_files(source, edition)
    destination.mkdir(parents=True, exist_ok=True)
    for path in destination.rglob('*'):
        if path.is_symlink():
            raise ValueError('Showroom output may not contain symlinks')
    for name, data in files.items():
        path = destination / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
    for path in list(destination.rglob('*')):
        if path.is_file() and path.relative_to(destination).as_posix() not in files:
            path.unlink()
    for path in sorted(destination.rglob('*'), key=lambda p: len(p.parts), reverse=True):
        if path.is_dir() and not any(path.iterdir()):
            path.rmdir()
    return len(files) - 1


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true')
    parser.add_argument('--output', type=Path, default=DESTINATION)
    parser.add_argument('--edition', choices=('client1', 'legacy'), default='client1',
                        help='client1 is the current release; legacy is for historical regression only')
    parser.add_argument('--stamp-client', action='store_true',
                        help='Record hashes after vite build --mode showroom')
    args = parser.parse_args()
    if args.stamp_client:
        stamp_client_release()
        return 0
    if args.check:
        stale = check(destination=args.output, edition=args.edition)
        if stale:
            print('Customer showroom bundle is stale: ' + ', '.join(stale), file=sys.stderr)
            return 1
        print('Customer showroom bundle matches the reviewed source.')
    else:
        count = build(destination=args.output, edition=args.edition)
        print(f'Built {count} authenticated showroom files in {args.output}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
