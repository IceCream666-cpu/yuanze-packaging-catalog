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
CLIENT_EDITIONS = {'client1': 'client1.0', 'client12': 'client1.2', 'client13': 'client1.3', 'client14': 'client1.4', 'client15': 'client1.5', 'client16': 'client1.6', 'client17': 'client1.7', 'client18': 'client1.8', 'client19': 'client1.9', 'client110': 'client1.10', 'client111': 'client1.11', 'client112': 'client1.12', 'client113': 'client1.13', 'client114': 'client1.14', 'client115': 'client1.15', 'client116': 'client1.16', 'client117': 'client1.17', 'client118': 'client1.18', 'client119': 'client1.19', 'client120': 'client1.20', 'client121': 'client1.21', 'client122': 'client1.22', 'client123': 'client1.23', 'client124': 'client1.24', 'client125': 'client1.25', 'client126': 'client1.26', 'client127': 'client1.27', 'client128': 'client1.28', 'client129': 'client1.29', 'client130': 'client1.30', 'client132': 'client1.32', 'client133': 'client1.33', 'client134': 'client1.34', 'client135': 'client1.35', 'client136': 'client1.36', 'client137': 'client1.37', 'client138': 'client1.38', 'client139': 'client1.39', 'client140': 'client1.40', 'client141':'client1.41', 'client143':'client1.43', 'client144':'client1.44', 'client145':'client1.45', 'client146':'client1.46', 'client147':'client1.47', 'client148':'client1.48', 'client149':'client1.49', 'client150':'client1.50', 'client151':'client1.51', 'client152':'client1.52', 'client153':'client1.53', 'client154':'client1.54', 'client155':'client1.55', 'client156':'client1.56'}
MOTION_EDITIONS = frozenset(('client12', 'client13', 'client14', 'client15', 'client16', 'client17', 'client18', 'client19', 'client110', 'client111', 'client112', 'client113', 'client114', 'client115', 'client116', 'client117', 'client118', 'client119', 'client120', 'client121', 'client122', 'client123', 'client124', 'client125', 'client126', 'client127', 'client128', 'client129', 'client130', 'client132', 'client133', 'client134', 'client135', 'client136', 'client137', 'client138', 'client139', 'client140','client141','client143','client144','client145','client146','client147','client148','client149','client150','client151','client152','client153','client154','client155','client156'))
REVIEWED_COUNTS = {'client12': (8, 38), 'client13': (8, 38), 'client14': (23, 53), 'client15': (23, 53), 'client16': (23, 53), 'client17': (23, 53), 'client18': (24, 54), 'client19': (24, 54), 'client110': (24, 54), 'client111': (24, 54), 'client112': (24, 54), 'client113': (24, 54), 'client114': (24, 54), 'client115': (24, 54), 'client116': (24, 54), 'client117': (31, 61), 'client118': (31, 61), 'client119': (24, 61), 'client120': (24, 61), 'client121': (24, 61), 'client122': (24, 61), 'client123': (24, 61), 'client124': (24, 61), 'client125': (24, 61), 'client126': (24, 61), 'client127': (24, 61), 'client128': (24, 61), 'client129': (24, 61), 'client130': (26, 61), 'client132': (26, 61), 'client133': (26, 61), 'client134': (26, 61), 'client135': (26, 61), 'client136': (26, 61), 'client137': (26, 61), 'client138': (26, 61), 'client139': (26, 61), 'client140': (26, 61),'client141':(27,62), 'client143':(27,62), 'client144':(28,64), 'client145':(29,64), 'client146':(29,65), 'client147':(29,65), 'client148':(29,66), 'client149':(29,67), 'client150':(30,67), 'client151':(31,68), 'client152':(31,69), 'client153':(31,68), 'client154':(31,68), 'client155':(31,68), 'client156':(31,68)}
FEATURED_APPROVAL_VERSIONS = {'client12': 'client1.2', 'client13': 'client1.2',
                             'client14': 'client1.4', 'client15': 'client1.4', 'client16': 'client1.4', 'client17': 'client1.4', 'client18': 'client1.8', 'client19': 'client1.8', 'client110': 'client1.8', 'client111': 'client1.8', 'client112': 'client1.8', 'client113': 'client1.8', 'client114': 'client1.8', 'client115': 'client1.8', 'client116': 'client1.8', 'client117': 'client1.17', 'client118': 'client1.17', 'client119': 'client1.19', 'client120': 'client1.19', 'client121': 'client1.19', 'client122': 'client1.19', 'client123': 'client1.19', 'client124': 'client1.19', 'client125': 'client1.19', 'client126': 'client1.19', 'client127': 'client1.19', 'client128': 'client1.19', 'client129': 'client1.19', 'client130': 'client1.30', 'client132': 'client1.30', 'client133': 'client1.30', 'client134': 'client1.34', 'client135': 'client1.34', 'client136': 'client1.34', 'client137': 'client1.34', 'client138': 'client1.34', 'client139': 'client1.34', 'client140': 'client1.34','client141':'client1.41', 'client143':'client1.43', 'client144':'client1.44', 'client145':'client1.45', 'client146':'client1.45', 'client147':'client1.47', 'client148':'client1.47', 'client149':'client1.47', 'client150':'client1.50', 'client151':'client1.51', 'client152':'client1.51', 'client153':'client1.51', 'client154':'client1.51', 'client155':'client1.51', 'client156':'client1.51'}
PACKAGING_EDITIONS = frozenset(('client16', 'client17', 'client18', 'client19', 'client110', 'client111', 'client112', 'client113', 'client114', 'client115', 'client116', 'client117', 'client118', 'client119', 'client120', 'client121', 'client122', 'client123', 'client124', 'client125', 'client126', 'client127', 'client128', 'client129', 'client130', 'client132', 'client133', 'client134', 'client135', 'client136', 'client137', 'client138', 'client139', 'client140','client141','client143','client144','client145','client146','client147','client148','client149','client150','client151','client152','client153','client154','client155','client156'))
COLLECTION_MODELS = json.loads((MOTION_CLIENT / 'src/structure/collection-products.json').read_text())
assert all(re.fullmatch(r'poster-\d{3}', key) and re.fullmatch(re.escape(key) + r'(?:-v[1-9]\d*)?\.glb', value['file']) for key, value in COLLECTION_MODELS.items())
PACKAGING_ASSETS = {'beach-magic-packaging.glb': 'model', 'gsap.min.js': 'animation',
                    'ScrollTrigger.min.js': 'scroll-animation', **{value['file']: 'model' for value in COLLECTION_MODELS.values()}}
PACKAGING_CHUNK = re.compile(r'assets/packaging/[A-Za-z0-9_-]+-[A-Za-z0-9_-]{8,}\.(?:js|css)')


def client_directory(edition):
    if edition not in CLIENT_EDITIONS:
        raise ValueError(f'Unsupported client edition: {edition}')
    return MOTION_CLIENT if edition in MOTION_EDITIONS else CLIENT


def client_source_hash(edition='client1'):
    client = client_directory(edition)
    sources = [*sorted(path for path in (client / 'src').rglob('*') if path.is_file() or path.is_symlink()), client / 'index.html',
               client / 'vite.config.js', client / 'package.json', client / 'assets-manifest.json']
    if edition in MOTION_EDITIONS:
        sources += [client / 'featured-manifest.json', client / 'prepare-assets.py',
                    client / 'display-derivatives.json', client / 'optimize-display-assets.py',
                    *sorted((client / 'optimized-assets').glob('*')),
                    *sorted((client / 'featured-assets').glob('*')),
                    *sorted((client / 'featured-optimized').glob('*'))]
    if edition in PACKAGING_EDITIONS:
        sources += [client / 'packaging-manifest.json',
                    *(client / 'packaging-assets' / name for name in sorted(PACKAGING_ASSETS))]
    digest = hashlib.sha256()
    for path in sources:
        name = path.relative_to(client).as_posix()
        digest.update(name.encode() + b'\0' + source_file(client, name).read_bytes())
    return digest.hexdigest()


def release_file_names(client, edition):
    """Permit only reachable Vite outputs, never an arbitrary release directory."""
    if edition not in PACKAGING_EDITIONS:
        return set(CLIENT_ENTRYPOINTS)
    release = client / 'release'
    graph = json.loads(source_file(release, '.vite/manifest.json').read_text())
    if not isinstance(graph, dict) or not graph or 'index.html' not in graph:
        raise ValueError('Invalid packaging build graph')
    if not isinstance(graph['index.html'], dict) or graph['index.html'].get('file') != 'preview.js' or graph['index.html'].get('isEntry') is not True:
        raise ValueError('Invalid packaging build entrypoint')
    names, seen, pending = {'index.html'}, set(), ['index.html']
    while pending:
        key = pending.pop()
        if key in seen:
            continue
        node = graph.get(key)
        if not isinstance(node, dict):
            raise ValueError('Invalid packaging build dependency')
        seen.add(key)
        if node.get('isEntry') and key != 'index.html':
            raise ValueError('Unexpected packaging build entrypoint')
        output = node.get('file')
        if (output != 'preview.js' and (not isinstance(output, str) or not PACKAGING_CHUNK.fullmatch(output))
                or not isinstance(output, str) or not output.endswith('.js')):
            raise ValueError('Invalid packaging build module path')
        names.add(output)
        css = node.get('css', [])
        if not isinstance(css, list) or node.get('assets', []):
            raise ValueError('Unexpected packaging build assets')
        for name in css:
            if not isinstance(name, str) or (name != 'preview.css' and not PACKAGING_CHUNK.fullmatch(name)) or not name.endswith('.css'):
                raise ValueError('Invalid packaging build stylesheet path')
            names.add(name)
        for field in ('imports', 'dynamicImports'):
            edges = node.get(field, [])
            if not isinstance(edges, list) or any(not isinstance(key, str) for key in edges):
                raise ValueError('Invalid packaging build dependencies')
            pending.extend(edges)
    if seen != set(graph) or not set(CLIENT_ENTRYPOINTS).issubset(names):
        raise ValueError('Packaging build has unreachable modules or missing entrypoints')
    actual = set()
    for path in release.rglob('*'):
        if path.is_symlink():
            raise ValueError('Packaging release may not contain symlinks')
        if path.is_file():
            actual.add(path.relative_to(release).as_posix())
    if actual - {'build.json', '.vite/manifest.json'} != names:
        raise ValueError('Packaging release differs from its build graph')
    return names


def stamp_client_release(edition='client1'):
    client = client_directory(edition)
    files = {name: hashlib.sha256(source_file(client / 'release', name).read_bytes()).hexdigest()
             for name in sorted(release_file_names(client, edition))}
    stamp = {
        'version': CLIENT_EDITIONS[edition], 'sourceSha256': client_source_hash(edition), 'files': files,
    }
    if edition in PACKAGING_EDITIONS:
        packaging_files({}, client)
        stamp['viteManifestSha256'] = hashlib.sha256(source_file(client / 'release', '.vite/manifest.json').read_bytes()).hexdigest()
    (client / 'release/build.json').write_text(json.dumps(stamp, indent=2) + '\n')


def packaging_files(files, client):
    """Add all current approved models and two animation scripts, with fixed routes."""
    manifest = json.loads(source_file(client, 'packaging-manifest.json').read_text())
    if (manifest.get('schema') != 1 or manifest.get('scope') != 'approved-client1.56-collection-packaging' or manifest.get('publicationApproved') is not True
            or manifest.get('posterId') != 'poster-012'
            or manifest.get('components') != ['Jar', 'OuterCap', 'InnerLid', 'LogoPrint']
            or manifest.get('additionalProducts') != ([{'posterId':key,'file':value['file'],'components':[part['node'] for part in value['parts']]} for key,value in COLLECTION_MODELS.items()])
            or manifest.get('containsFormula') is not False):
        raise ValueError('Invalid packaging approval')
    entries = manifest.get('files', [])
    if (not isinstance(entries, list) or len(entries) != len(PACKAGING_ASSETS)
            or any(not isinstance(entry, dict) for entry in entries)
            or {entry.get('name') for entry in entries} != set(PACKAGING_ASSETS)):
        raise ValueError('Packaging approval must exactly match the reviewed assets')
    for entry in entries:
        name = entry['name']
        target = f'assets/packaging/{name}'
        if (entry.get('kind') != PACKAGING_ASSETS[name] or entry.get('file') != f'packaging-assets/{name}'
                or entry.get('productionTarget') != target):
            raise ValueError('Invalid packaging asset identity or path')
        data = source_file(client, entry['file']).read_bytes()
        if len(data) != entry.get('bytes') or hashlib.sha256(data).hexdigest() != entry.get('sha256'):
            raise ValueError(f'Packaging asset checksum mismatch: {name}')
        if target in files:
            raise ValueError(f'Packaging asset cannot replace an existing file: {target}')
        files[target] = data


def prepare_packaging_assets(client):
    """Use the production approval checks for the loopback preview as well."""
    files = {}
    packaging_files(files, client)
    public = client / 'public'
    for name in files:
        parts = name.split('/')
        if public.is_symlink() or any(public.joinpath(*parts[:index]).is_symlink()
                                      for index in range(1, len(parts) + 1)):
            raise ValueError('Packaging preview output may not contain symlinks')
    for name, data in files.items():
        destination = public / name
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(data)
    return len(files)


def featured_files(files, client, edition='client150'):
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


def optimized_display_files(files, client, edition='client150'):
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
    if stamp.get('version') != version:
        raise ValueError(f'{version} release stamp has an invalid version or entrypoint set')
    release_names = release_file_names(client, edition)
    if set(stamp.get('files', {})) != release_names:
        raise ValueError(f'{version} release stamp has an invalid version or entrypoint set')
    if edition in PACKAGING_EDITIONS and stamp.get('viteManifestSha256') != hashlib.sha256(source_file(client / 'release', '.vite/manifest.json').read_bytes()).hexdigest():
        raise ValueError(f'{version} build graph checksum mismatch')
    if stamp['sourceSha256'] != client_source_hash(edition):
        raise ValueError(f'{version} source changed: rebuild and stamp the release first')
    for name in sorted(release_names):
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
    if edition in PACKAGING_EDITIONS:
        packaging_files(files, client)
    files.pop('bundle-manifest.json')
    bundle = {'schema': 1, 'source': client.relative_to(ROOT).as_posix(), 'version': version,
              'files': {name: {'sha256': hashlib.sha256(data).hexdigest(), 'bytes': len(data)}
                        for name, data in sorted(files.items())}}
    files['bundle-manifest.json'] = (json.dumps(bundle, ensure_ascii=False, sort_keys=True, indent=2) + '\n').encode()
    return files


def source_file(source, name):
    if (not isinstance(name, str) or '\\' in name or name.startswith('/')
            or any(part in {'.', '..', ''} for part in name.split('/'))):
        raise ValueError(f'Invalid showroom source: {name}')
    candidate = source / name
    parts = name.split('/')
    if any(source.joinpath(*parts[:index]).is_symlink() for index in range(1, len(parts) + 1)):
        raise ValueError(f'Invalid showroom source symlink: {name}')
    path = candidate.resolve()
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
    parser.add_argument('--edition', choices=('client156', 'client155', 'client154', 'client153', 'client152', 'client151', 'client150', 'client149', 'client148', 'client147', 'client146', 'client145', 'client144', 'client143', 'client141','client140', 'client139', 'client138', 'client137', 'client136', 'client135', 'client134', 'client133', 'client132', 'client130', 'client129', 'client128', 'client127', 'client126', 'client125', 'client124', 'client123', 'client122', 'client121', 'client120', 'client119', 'client118', 'client117', 'client116', 'client115', 'client114', 'client113', 'client112', 'client111', 'client110', 'client19', 'client18', 'client17', 'client16', 'client15', 'client14', 'client13', 'client12', 'client1', 'legacy'), default='client156',
                        help='client156 is current; older editions require their matching source and release stamp')
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
