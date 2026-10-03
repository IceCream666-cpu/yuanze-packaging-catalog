#!/usr/bin/env python3
"""Loopback-only customer design preview using an explicitly public snapshot.

No production credentials, account database, employee catalogue or source images
are loaded. Query images stay in memory. Start from the project virtualenv:
    .venv/bin/python scripts/preview_customer_showroom.py --port 4319
"""
import argparse
import hashlib
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import math
import mimetypes
from pathlib import Path
import re
import secrets
import sys
import threading
from urllib.parse import parse_qs, unquote, urlsplit

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'server-reference'))
from client_catalog import (BOTTLE_TYPES, CATEGORIES, DIMENSIONS, FACETS, MATERIALS,
                            SECTIONS, USES, canonical, canonical_list, facet_values,
                            matches_search, safe_measurement)
from image_search import (Embedder, MAX_REQUEST_BYTES, SearchBusy, SearchUnavailable,
                          decode_image, decode_upload, model_manifest, rank_matches)

TOKEN = re.compile(r'[a-f0-9]{64}')
MEDIA = re.compile(r'/client-media/([a-f0-9]{64}\.jpg)')
PUBLIC = {'/client': 'client.html', '/client.html': 'client.html', '/client/products': 'client.html',
          '/client.js': 'client.js', '/client.css': 'client.css',
          '/api-client.js': 'api-client.js', '/i18n.js': 'i18n.js',
          '/i18n.css': 'i18n.css', '/brand/yuanze-mark.svg': 'brand/yuanze-mark.svg'}
DRAFT = {'/': 'index.html', '/index.html': 'index.html', '/preview.css': 'preview.css',
         '/preview.js': 'preview.js', '/company-content.js': 'company-content.js',
         '/product-posters.js': 'product-posters.js'}


def within(base, path):
    resolved = (base / path).resolve()
    return resolved if resolved.is_relative_to(base.resolve()) and resolved.is_file() else None


def public_item(raw, media_dir):
    """Rebuild every output field; never trust names, raw text or extra keys."""
    if not isinstance(raw, dict) or not isinstance(raw.get('id'), str) or not TOKEN.fullmatch(raw['id']):
        return None
    capacity = safe_measurement(raw.get('capacity'), 'capacity')
    capacity_label, capacity_ml = '', None
    if capacity:
        capacity_label, amount, unit = capacity
        capacity_ml = amount if unit in {'mL', 'L'} else None
    category = canonical(raw.get('category'), CATEGORIES)
    bottle = canonical(raw.get('bottleType'), BOTTLE_TYPES)
    specs = []
    for entry in raw.get('specifications', []) if isinstance(raw.get('specifications'), list) else []:
        if not isinstance(entry, dict) or not isinstance(entry.get('label'), str) or entry['label'] not in DIMENSIONS:
            continue
        measured = safe_measurement(entry.get('value'), DIMENSIONS[entry['label']][0])
        if measured:
            value = {'label': entry['label'], 'value': measured[0]}
            if value not in specs:
                specs.append(value)
    images = []
    for image in raw.get('images', []) if isinstance(raw.get('images'), list) else []:
        url = image.get('url') if isinstance(image, dict) else None
        match = MEDIA.fullmatch(url) if isinstance(url, str) else None
        if match and within(media_dir, match[1]) and {'url': url} not in images:
            images.append({'url': url})
    if not images:
        return None
    code = raw.get('productCode', '')
    return {'id': raw['id'], 'productCode': code if isinstance(code, str) and re.fullmatch(r'YZ-BC-\d{6,}', code) else '',
            'name': ' · '.join(filter(None, (bottle or category or '包材', capacity_label))),
            'capacity': capacity_label, 'capacityMl': capacity_ml, 'category': category,
            'bottleType': bottle, 'materials': canonical_list(raw.get('materials'), MATERIALS),
            'uses': canonical_list(raw.get('uses'), USES), 'sections': canonical_list(raw.get('sections'), SECTIONS),
            'specifications': specs, 'images': images}


class PublicSnapshot:
    def __init__(self, directory):
        self.directory = Path(directory)
        self.media = self.directory / 'client-media'
        raw = json.loads((self.directory / 'catalog.json').read_text(encoding='utf-8'))
        self.items, seen = [], set()
        for source in raw.get('items', []):
            item = public_item(source, self.media)
            if item and item['id'] not in seen:
                seen.add(item['id'])
                self.items.append(item)
        self.images = {image['url']: within(self.media, image['url'].split('/')[-1])
                       for item in self.items for image in item['images']}
        self.facets = {key: sorted({value for item in self.items for value in facet_values(item, field)})
                       for key, field in FACETS.values()}

    def catalog(self, params=None, ranking=None):
        params = params or {}
        def number(key, default, maximum):
            try:
                return max(1, min(maximum, int(params.get(key, [default])[0])))
            except (ValueError, TypeError, IndexError):
                return default
        page_size = number('pageSize', 24, 48)
        query = str(params.get('q', [''])[0])[:200]
        items = [item for item in self.items if matches_search(item, query) and
                 all(not params.get(key) or set(params[key]).intersection(facet_values(item, field))
                     for key, (_, field) in FACETS.items())]
        if ranking is not None:
            ordered = {item['record_id']: n for n, item in enumerate(ranking)}
            items = sorted((item for item in items if item['id'] in ordered), key=lambda item: ordered[item['id']])
        total = len(items)
        pages = max(1, math.ceil(total / page_size))
        page = number('page', 1, pages)
        return {'items': items[(page-1)*page_size:page*page_size], 'page': page,
                'pages': pages, 'total': total, 'facets': self.facets}


class PublicImageSearch:
    """Build an independent index exclusively from approved customer media."""
    def __init__(self, snapshot, model_dir):
        self.snapshot, self.model_dir = snapshot, Path(model_dir)
        self.lock = threading.Lock()
        self.embedder = None

    def initialize(self):
        if self.embedder is not None:
            return
        try:
            embedder = Embedder(self.model_dir)
            manifest = model_manifest(self.model_dir)
            np = embedder.np
            entries, gray, rgb = [], [], []
            by_image = {}
            for item in self.snapshot.items:
                for image in item['images']:
                    by_image.setdefault(image['url'], []).append(item['id'])
            image_hashes = {}
            for url, ids in by_image.items():
                data = self.snapshot.images[url].read_bytes()
                image = decode_image(data)
                try:
                    shape, color = embedder.pair(image)
                finally:
                    image.close()
                entries.append({'path': url, 'record_ids': ids})
                gray.append(shape); rgb.append(color)
                image_hashes[url] = hashlib.sha256(data).hexdigest()
            if not entries:
                raise ValueError('No approved customer images')
            self.entries, self.gray, self.rgb = entries, np.asarray(gray), np.asarray(rgb)
            index = self.snapshot.directory / 'image-search'
            index.mkdir(parents=True, exist_ok=True)
            np.savez_compressed(index / 'approved-vectors.npz', gray=self.gray, rgb=self.rgb)
            (index / 'manifest.json').write_text(json.dumps({'model': manifest, 'images': image_hashes,
                'entries': entries}, ensure_ascii=False), encoding='utf-8')
            self.embedder = embedder
        except Exception as error:
            self.embedder = None
            raise SearchUnavailable('本地客户搜图模型暂不可用，请检查本机模型和运行依赖；仍可使用文字及分类检索。') from error

    def search(self, image):
        if not self.lock.acquire(blocking=False):
            raise SearchBusy('客户图片检索正在处理中，请稍后重试。')
        decoded = None
        try:
            decoded = decode_upload(image)
            self.initialize()
            shape, color = self.embedder.pair(decoded)
            return rank_matches(self.embedder.np, self.entries, self.gray, self.rgb, shape, color)
        finally:
            if decoded is not None:
                decoded.close()
            self.lock.release()


class PreviewServer(ThreadingHTTPServer):
    daemon_threads = True
    allow_reuse_address = True

    def __init__(self, root=ROOT, port=4319, model_dir=None):
        self.root = Path(root).resolve()
        self.snapshot = PublicSnapshot(self.root / 'outputs/mobile-preview')
        self.csrf = secrets.token_urlsafe(32)
        self.visual = PublicImageSearch(self.snapshot, model_dir or self.root / 'server-reference/private/image-search/model')
        self.assets = set()
        manifest = self.root / 'docs/mobile-client-preview/assets/manifest.json'
        if manifest.is_file():
            self.assets = {f"/assets/{item['path']}" for item in json.loads(manifest.read_text())['files']}
        super().__init__(('127.0.0.1', port), PreviewHandler)


class PreviewHandler(BaseHTTPRequestHandler):
    server_version = 'YuanzePreview'
    sys_version = ''

    def log_message(self, fmt, *args):
        # Do not record image bodies, search strings or file-system paths.
        pass

    def allowed_origin(self):
        hosts = {f'127.0.0.1:{self.server.server_port}', f'localhost:{self.server.server_port}'}
        if self.headers.get('Host', '') not in hosts:
            return False
        origin = self.headers.get('Origin')
        if origin and origin not in {f'http://{host}' for host in hosts}:
            return False
        return self.headers.get('Sec-Fetch-Site', '') != 'cross-site'

    def respond(self, status, body, content_type='application/json; charset=utf-8'):
        if not isinstance(body, bytes):
            body = json.dumps(body, ensure_ascii=False).encode()
        self.send_response(status)
        self.send_header('Content-Type', content_type)
        self.send_header('Content-Length', str(len(body)))
        self.send_header('Cache-Control', 'no-store')
        self.send_header('X-Content-Type-Options', 'nosniff')
        self.send_header('X-Frame-Options', 'SAMEORIGIN')
        self.send_header('Referrer-Policy', 'no-referrer')
        self.send_header('Cross-Origin-Resource-Policy', 'same-origin')
        self.send_header('Content-Security-Policy', "default-src 'self'; img-src 'self' data: blob:; style-src 'self' 'unsafe-inline'; script-src 'self'; connect-src 'self'; frame-ancestors 'self'; base-uri 'self'; form-action 'self'")
        self.end_headers()
        if self.command != 'HEAD':
            self.wfile.write(body)

    def do_GET(self):
        if not self.allowed_origin():
            return self.respond(403, {'error': 'Local preview requests only'})
        split = urlsplit(self.path)
        path = unquote(split.path)
        if '\\' in path or '..' in path.split('/') or '\x00' in path:
            return self.respond(404, {'error': 'Not found'})
        if path == '/api/session':
            return self.respond(200, {'username': 'local-preview', 'role': 'client', 'csrf': self.server.csrf, 'preview': True})
        if path == '/api/client/catalog':
            if len(split.query) > 8192:
                return self.respond(400, {'error': 'Too many filters'})
            return self.respond(200, self.server.snapshot.catalog(parse_qs(split.query)))
        target = None
        if path in PUBLIC:
            target = within(self.server.root / 'server-reference/public', PUBLIC[path])
        elif path in DRAFT:
            target = within(self.server.root / 'docs/mobile-client-preview', DRAFT[path])
        elif path in self.server.assets:
            target = within(self.server.root / 'docs/mobile-client-preview', path.lstrip('/'))
        elif path in self.server.snapshot.images:
            target = within(self.server.snapshot.media, path.split('/')[-1])
        elif path == '/login':
            # Preview has no user database. Exit returns to the clearly labelled draft.
            self.send_response(303); self.send_header('Location', '/'); self.end_headers(); return
        if target and target.is_file():
            mime = 'image/webp' if target.suffix.lower() == '.webp' else mimetypes.guess_type(target.name)[0] or 'application/octet-stream'
            return self.respond(200, target.read_bytes(), mime)
        return self.respond(404, {'error': 'Not found'})

    def do_POST(self):
        if not self.allowed_origin() or not secrets.compare_digest(self.headers.get('X-CSRF-Token', ''), self.server.csrf):
            return self.respond(403, {'error': 'Local preview verification required'})
        path = urlsplit(self.path).path
        if path not in {'/api/client/image-search', '/api/logout'}:
            return self.respond(403, {'error': 'Preview does not support changes'})
        if self.headers.get('Transfer-Encoding') or self.headers.get('Content-Type', '').split(';')[0] != 'application/json':
            return self.respond(400, {'error': 'JSON request required'})
        try:
            size = int(self.headers.get('Content-Length', '0'))
            if not 0 < size <= MAX_REQUEST_BYTES + 4096:
                return self.respond(413, {'error': 'Image request is too large or empty'})
            self.connection.settimeout(15)
            payload = json.loads(self.rfile.read(size))
            if not isinstance(payload, dict):
                raise ValueError('Invalid request')
            if path == '/api/logout':
                self.server.csrf = secrets.token_urlsafe(32)
                return self.respond(200, {'ok': True, 'preview': True})
            if set(payload) != {'image'}:
                raise ValueError('Only a query image is accepted')
            ranking = self.server.visual.search(payload.get('image'))
            result = self.server.snapshot.catalog({'pageSize': ['48']}, ranking=ranking[:48])
            result['imageSearch'] = True
            return self.respond(200, result)
        except SearchBusy as error:
            return self.respond(429, {'error': str(error)})
        except SearchUnavailable as error:
            return self.respond(503, {'error': str(error), 'code': 'CLIENT_SEARCH_UNAVAILABLE'})
        except (ValueError, TypeError, TimeoutError):
            return self.respond(400, {'error': '图片格式无法识别，请使用 JPG、PNG 或 WebP 图片。'})
        except Exception:
            return self.respond(503, {'error': '本地客户搜图暂不可用，请稍后重试。'})

    def do_HEAD(self):
        self.do_GET()

    def do_PUT(self):
        self.respond(405, {'error': 'Preview does not support changes'})

    do_PATCH = do_DELETE = do_PUT


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--port', type=int, default=4319)
    parser.add_argument('--model-dir', type=Path)
    args = parser.parse_args()
    server = PreviewServer(port=args.port, model_dir=args.model_dir)
    print(f'Local customer draft: http://127.0.0.1:{server.server_port}/ ({len(server.snapshot.items)} approved records)', flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == '__main__':
    main()
