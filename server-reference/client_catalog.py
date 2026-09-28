"""Explicitly approved customer catalogue; private records never cross this boundary."""
import hashlib
import hmac
import json
import math
import os
from pathlib import Path
import re
import secrets
import threading


class ClientMediaBusy(Exception):
    pass


def safe_capacity(record):
    """Never display an arbitrary original string as customer-facing capacity."""
    value = record.get('capacityMl')
    if type(value) in (int, float) and math.isfinite(value) and 0 < value <= 100000:
        return f'{value:g} mL'
    units = {'ml': 'mL', '毫升': 'mL', 'l': 'L', '升': 'L', 'g': 'g', '克': 'g', 'kg': 'kg', '千克': 'kg'}
    for detail in record.get('productDetails', []):
        if not isinstance(detail, dict) or detail.get('label') not in {'净含量', '标称容量', '容量'}:
            continue
        match = re.fullmatch(r'\s*(\d{1,6}(?:\.\d{1,3})?)\s*(mL|L|g|kg|毫升|升|克|千克)\s*', str(detail.get('value', '')), re.I)
        if match and 0 < float(match[1]) <= 100000:
            return f'{float(match[1]):g} {units[match[2].lower()]}'
    return ''


class ClientCatalog:
    PAGE_SIZE = 24
    TOKEN_RE = re.compile(r'^[a-f0-9]{64}\.jpg$')

    def __init__(self, store, state, private):
        self.store = store
        self.state, self.private = Path(state).resolve(), Path(private).resolve()
        self.cache = self.state / 'client-media'
        self.cache.mkdir(mode=0o700, parents=True, exist_ok=True)
        self.cache.chmod(0o700)
        keyfile = self.cache / 'key'
        try:
            descriptor = os.open(keyfile, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
            with os.fdopen(descriptor, 'wb') as output:
                output.write(secrets.token_bytes(32))
        except FileExistsError:
            pass
        self.key = keyfile.read_bytes()
        if len(self.key) != 32:
            raise ValueError('Invalid customer media key')
        self.gate = threading.Lock()
        # A first page may request many uncached images at once. Queue a small
        # number of conversions instead of failing the whole page immediately.
        self.waiters = threading.BoundedSemaphore(12)
        with self.store.connection(True) as conn:
            conn.execute('''CREATE TABLE IF NOT EXISTS client_media_map (
                token TEXT PRIMARY KEY, record_id TEXT NOT NULL, image_path TEXT NOT NULL
            )''')

    def opaque(self, namespace, *values):
        return hmac.new(self.key, json.dumps([namespace, *values], ensure_ascii=False).encode(), hashlib.sha256).hexdigest()

    def source(self, path):
        if not isinstance(path, str) or '\\' in path:
            return None
        if path.startswith('media/'):
            base = self.private / 'media'
            candidate = self.private / path
        elif path.startswith('uploads/'):
            base = self.state / 'uploads'
            candidate = self.state / path
        else:
            return None
        target = candidate.resolve()
        if not target.is_relative_to(base.resolve()) or not target.is_file():
            return None
        return target

    def approved_images(self, record):
        if record.get('kind') != 'package':
            return []
        result, seen = [], set()
        for image in record.get('images', []):
            if not isinstance(image, dict) or image.get('clientVisible') is not True or image.get('missing'):
                continue
            path = image.get('path')
            if not isinstance(path, str) or path in seen or self.source(path) is None:
                continue
            seen.add(path)
            result.append(path)
        return result

    def catalog(self, page=1, page_size=24):
        page = max(1, page)
        page_size = max(1, min(48, page_size))
        entries, mappings = [], []
        # json_each applies the opt-in filter in SQLite, avoiding a full parsed
        # copy of the employee catalogue for every customer request.
        with self.store.connection() as conn:
            rows = conn.execute('''SELECT id,content FROM admin_records
                WHERE archived=0 AND json_extract(content,'$.kind')='package'
                  AND EXISTS (SELECT 1 FROM json_each(content,'$.images') AS image
                              WHERE json_extract(image.value,'$.clientVisible')=1
                                AND json_type(image.value,'$.clientVisible')='true')
                ORDER BY id''')
            for row in rows:
                record = json.loads(row['content'])
                paths = self.approved_images(record)
                if not paths:
                    continue
                images = []
                for path in paths:
                    token = self.opaque('image', row['id'], path) + '.jpg'
                    mappings.append((token, row['id'], path))
                    images.append({'url': '/client-media/' + token})
                entries.append({'id': self.opaque('record', row['id']), 'capacity': safe_capacity(record), 'images': images})
        # The table only resolves opaque handles; every request below rechecks
        # current approval and archive state, including cache hits.
        if mappings:
            with self.store.connection(True) as conn:
                conn.executemany('INSERT OR IGNORE INTO client_media_map VALUES(?,?,?)', mappings)
        total = len(entries)
        pages = max(1, (total + page_size - 1) // page_size)
        page = min(page, pages)
        return {'items': entries[(page - 1) * page_size:page * page_size], 'page': page, 'pages': pages, 'total': total}

    def media(self, token):
        # Optional image dependencies must not prevent employee login/startup.
        try:
            from PIL import Image, ImageOps, UnidentifiedImageError
        except ImportError:
            return None
        if not self.TOKEN_RE.fullmatch(token):
            return None
        with self.store.connection() as conn:
            row = conn.execute('''SELECT m.image_path,r.content FROM client_media_map AS m
                JOIN admin_records AS r ON r.id=m.record_id
                WHERE m.token=? AND r.archived=0''', (token,)).fetchone()
        if not row or row['image_path'] not in self.approved_images(json.loads(row['content'])):
            return None
        source = self.source(row['image_path'])
        if source is None:
            return None
        stat = source.stat()
        fingerprint = hashlib.sha256(f'{stat.st_size}:{stat.st_mtime_ns}'.encode()).hexdigest()[:20]
        target = self.cache / (token[:-4] + '-' + fingerprint + '.jpg')
        if target.is_file():
            return target
        if not self.waiters.acquire(blocking=False):
            raise ClientMediaBusy()
        locked = False
        temporary = None
        try:
            locked = self.gate.acquire(timeout=45)
            if not locked:
                raise ClientMediaBusy()
            if target.is_file():
                return target
            with Image.open(source) as original:
                if original.width * original.height > 24_000_000 or original.width < 1 or original.height < 1:
                    return None
                original.draft('RGB', (1600, 1600))
                original.thumbnail((1600, 1600))
                rendered = ImageOps.exif_transpose(original).convert('RGB')
                # A fresh image has none of the original EXIF, comments, profiles
                # or PNG text chunks, regardless of the original file format.
                sanitized = Image.new('RGB', rendered.size, 'white')
                sanitized.paste(rendered)
                temporary = target.with_suffix('.' + secrets.token_hex(6) + '.tmp')
                sanitized.save(temporary, format='JPEG', quality=88, optimize=True)
                temporary.chmod(0o600)
                os.replace(temporary, target)
            return target
        except (OSError, ValueError, UnidentifiedImageError, Image.DecompressionBombError):
            return None
        finally:
            if temporary is not None:
                temporary.unlink(missing_ok=True)
            if locked:
                self.gate.release()
            self.waiters.release()
