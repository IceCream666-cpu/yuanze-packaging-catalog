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
MOTION_CLIENT = ROOT / 'docs/client-motion-demo'
CLIENT_ENTRYPOINTS = ('index.html', 'preview.js', 'preview.css')
CLIENT_EDITIONS = {'client1': 'client1.0', 'client12': 'client1.2', 'client13': 'client1.3', 'client14': 'client1.4', 'client15': 'client1.5', 'client16': 'client1.6'}
MOTION_EDITIONS = frozenset(('client12', 'client13', 'client14', 'client15', 'client16'))
REVIEWED_COUNTS = {'client12': (8, 38), 'client13': (8, 38), 'client14': (23, 53), 'client15': (23, 53), 'client16': (23, 53)}
FEATURED_APPROVAL_VERSIONS = {'client12': 'client1.2', 'client13': 'client1.2',
                             'client14': 'client1.4', 'client15': 'client1.4', 'client16': 'client1.4'}


def client_directory(edition):
    if edition not in CLIENT_EDITIONS:
        raise ValueError(f'Unsupported client edition: {edition}')
    return MOTION_CLIENT if edition in MOTION_EDITIONS else CLIENT


def client_source_hash(edition='client1'):
    client = client_directory(edition)
    sources = [*sorted((client / 'src').glob('*')), client / 'index.html',
               client / 'vite.config.js', client / 'package.json', client / 'assets-manifest.json']
    if edition in MOTION_EDITIONS:
        sources += [client / 'featured-manifest.json', client / 'prepare-assets.py',
                    client / 'display-derivatives.json', client / 'optimize-display-assets.py',
                    *sorted((client / 'optimized-assets').glob('*')),
                    *sorted((client / 'featured-assets').glob('*')),
                    *sorted((client / 'featured-optimized').glob('*'))]
    digest = hashlib.sha256()
    for path in sources:
        digest.update(path.relative_to(client).as_posix().encode() + b'\0' + path.read_bytes())
    return digest.hexdigest()


def stamp_client_release(edition='client1'):
    client = client_directory(edition)
    files = {name: hashlib.sha256(source_file(client / 'release', name).read_bytes()).hexdigest()
             for name in CLIENT_ENTRYPOINTS}
    (client / 'release/build.json').write_text(json.dumps({
        'version': CLIENT_EDITIONS[edition], 'sourceSha256': client_source_hash(edition), 'files': files,
    }, indent=2) + '\n')


def featured_files(files, client, edition='client16'):
    """Add the edition's complete approved set without replacing source posters."""
    manifest = json.loads(source_file(client, 'featured-manifest.json').read_text())
    approval_version = FEATURED_APPROVAL_VERSIONS[edition]
    if manifest.get('scope') != f'approved-{approval_version}-display-derivatives':
        raise ValueError(f'Featured media has not been approved for {approval_version}')
    featured = json.loads(source_file(client, 'src/featured.json').read_text())
    ids = [item['id'] for item in featured]
    entries = manifest['files']
    expected_count = REVIEWED_COUNTS[edition][0]
    if (len(ids) != expected_count or len(set(ids)) != expected_count
            or sorted(item['posterId'] for item in entries) != sorted(ids)):
        raise ValueError(f'Featured media must exactly match the {expected_count} reviewed products')
    displays = json.loads(source_file(client, 'src/featured-media.json').read_text())
    if set(displays) != set(ids):
        raise ValueError('Display derivatives must exactly match the approved featured products')
    for item in entries:
        poster_id = item['posterId']
        if not re.fullmatch(r'poster-\d{3}', poster_id):
            raise ValueError('Invalid featured poster identity')
        target = f'assets/featured/{poster_id}.png'
        if item.get('productionTarget') != target or item.get('file') != f'featured-assets/{poster_id}.png':
            raise ValueError('Invalid featured media route')
        original = f'assets/posters/{poster_id}.webp'
        if item.get('approvedPoster') != f'server-reference/public/showroom/{original}':
            raise ValueError('Invalid featured source poster')
        if hashlib.sha256(files.get(original, b'')).hexdigest() != item.get('approvedPosterSha256'):
            raise ValueError(f'Featured source poster checksum mismatch: {poster_id}')
        data = source_file(client, item['file']).read_bytes()
        if len(data) != item.get('bytes') or hashlib.sha256(data).hexdigest() != item.get('sha256'):
            raise ValueError(f'Featured media checksum mismatch: {poster_id}')
        if target in files:
            raise ValueError(f'Featured media cannot replace an existing file: {target}')
        files[target] = data
        display = displays[poster_id]
        if display['sourceSha256'] != item['sha256']:
            raise ValueError('Display derivatives no longer match approved cutout')
        if set(display['files']) != {'640', '1024'}:
            raise ValueError('Expected mobile and desktop display sizes')
        for size, entry in display['files'].items():
            name = f'{poster_id}-{size}.webp'
            if entry['file'] != f'featured-optimized/{name}':
                raise ValueError('Invalid optimized media path')
            data = source_file(client, entry['file']).read_bytes()
            if len(data) != entry['bytes'] or hashlib.sha256(data).hexdigest() != entry['sha256']:
                raise ValueError('Optimized media checksum mismatch')
            files[f'assets/featured/{name}'] = data


def optimized_display_files(files, client, edition='client16'):
    """Validate every display derivative against an existing approved original."""
    manifest = json.loads(source_file(client, 'display-derivatives.json').read_text())
    if manifest.get('schema') != 1 or manifest.get('scope') != 'approved-client-display-optimization':
        raise ValueError('Invalid display derivative approval')
    posters = files['product-posters.js'].decode()
    catalogue = json.loads(posters[posters.index('{'):].strip().rstrip(';'))
    ids = [item['id'] for item in catalogue['items']]
    expected_count = REVIEWED_COUNTS[edition][1]
    if (len(ids) != expected_count or len(set(ids)) != expected_count
            or any(not re.fullmatch(r'poster-\d{3}', value) for value in ids)):
        raise ValueError(f'Display derivatives require the {expected_count} approved posters for {CLIENT_EDITIONS[edition]}')
    expected = {f'{poster_id}-strip.webp': ('filmstrip', f'assets/posters/{poster_id}.webp', poster_id)
                for poster_id in ids}
    expected['yuanze-mark-compact.webp'] = ('visible-logo', 'assets/yuanze-mark.svg', None)
    entries = manifest.get('files', [])
    names = [entry.get('productionTarget', '').removeprefix('assets/optimized/') for entry in entries]
    if len(names) != len(expected) or set(names) != set(expected):
        raise ValueError('Display derivatives must exactly match approved logo and posters')
    for entry in entries:
        name = entry['productionTarget'].removeprefix('assets/optimized/')
        kind, original, poster_id = expected[name]
        if (entry.get('kind') != kind or entry.get('productionTarget') != f'assets/optimized/{name}'
                or entry.get('file') != f'optimized-assets/{name}' or entry.get('approvedSource') != original
                or entry.get('posterId') != poster_id):
            raise ValueError('Invalid display derivative identity or path')
        if hashlib.sha256(files.get(original, b'')).hexdigest() != entry.get('approvedSourceSha256'):
            raise ValueError('Display derivative source checksum mismatch')
        width, height = entry.get('width'), entry.get('height')
        if (type(width) is not int or type(height) is not int or width < 1 or height < 1
                or (kind == 'filmstrip' and max(width, height) != 192)
                or (kind == 'visible-logo' and ((width, height) != (152, 171) or entry.get('crop') != [1200, 264, 152, 171]))):
            raise ValueError('Invalid display derivative dimensions')
        data = source_file(client, entry['file']).read_bytes()
        if len(data) != entry.get('bytes') or hashlib.sha256(data).hexdigest() != entry.get('sha256'):
            raise ValueError('Display derivative checksum mismatch')
        target = entry['productionTarget']
        if target in files:
            raise ValueError('Display derivatives cannot replace existing showroom files')
        files[target] = data


def client_files(files, edition='client1'):
    """Overlay reviewed entrypoints; preserve original media and validate derivatives."""
    client = client_directory(edition)
    version = CLIENT_EDITIONS[edition]
    files = dict(files)
    stamp = json.loads(source_file(client / 'release', 'build.json').read_text())
    if stamp.get('version') != version or set(stamp.get('files', {})) != set(CLIENT_ENTRYPOINTS):
        raise ValueError(f'{version} release stamp has an invalid version or entrypoint set')
    if stamp['sourceSha256'] != client_source_hash(edition):
        raise ValueError(f'{version} source changed: rebuild and stamp the release first')
    for name in CLIENT_ENTRYPOINTS:
        data = source_file(client / 'release', name).read_bytes()
        if hashlib.sha256(data).hexdigest() != stamp['files'][name]:
            raise ValueError(f'{version} release checksum mismatch: {name}')
        files[name] = data
    paths = json.loads((client / 'src/asset-paths.json').read_text())
    approved = json.loads((client / 'assets-manifest.json').read_text())
    if edition in MOTION_EDITIONS:
        optimized_display_files(files, client, edition)
    for item in approved['files']:
        route = paths['/' + item['target']]
        if not route.startswith('/showroom/assets/') or '..' in route.split('/'):
            raise ValueError('Invalid client media route')
        data = files.get(route.removeprefix('/showroom/'), b'')
        if len(data) != item['bytes'] or hashlib.sha256(data).hexdigest() != item['sha256']:
            raise ValueError('Client media differs from reviewed showroom media')
    if edition in MOTION_EDITIONS:
        featured_files(files, client, edition)
    files.pop('bundle-manifest.json')
    bundle = {'schema': 1, 'source': client.relative_to(ROOT).as_posix(), 'version': version,
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
    if edition not in ('legacy', *CLIENT_EDITIONS):
        raise ValueError(f'Unsupported showroom edition: {edition}')
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
    return client_files(files, edition) if edition in CLIENT_EDITIONS else files


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
    parser.add_argument('--edition', choices=('client16', 'client15', 'client14', 'client13', 'client12', 'client1', 'legacy'), default='client16',
                        help='client16 is current; older editions require their matching source and release stamp')
    parser.add_argument('--stamp-client', action='store_true',
                        help='Record hashes after vite build --mode showroom')
    args = parser.parse_args()
    if args.stamp_client:
        stamp_client_release(args.edition)
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
