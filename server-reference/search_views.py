"""Validated, reviewed product crops for visual search; no catalogue writes.

The browser manifests contain literal JSON, not executable configuration. Only
the two code-owned review bases below may add crop-to-record associations. File
resolution, actual image dimensions and delivered-file hashing remain the
responsibility of the search index, which already owns the private media root.
"""
from functools import lru_cache
import json
import math
from pathlib import Path, PurePosixPath
import re

MANIFESTS = (
    ('product-type-group-data.js', 'reviewedTypeGroups',
     'original-catalogue-photograph-and-size-table'),
    ('product-single-group-data.js', 'reviewedSingleTypeGroups',
     'visually-reviewed-single-physical-type-and-own-source-specifications'),
)
MAX_MANIFEST_BYTES = 8 * 1024 * 1024
MAX_PROVENANCE_BYTES = 2 * 1024 * 1024
MAX_GROUPS = 10_000
SHA256_RE = re.compile(r'[a-f0-9]{64}\Z')
DISPLAY_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.webp'}
# Extracted brochure originals are only hashed; the model receives the
# reviewed, browser-compatible display bitmap, never these original encodings.
NATIVE_EXTENSIONS = DISPLAY_EXTENSIONS | {'.jp2', '.jpf', '.jpx', '.tif', '.tiff'}
PROVENANCE_FILENAME = 'search-view-provenance.json'


@lru_cache(maxsize=8)
def _manifest(path, stamp, export_name):
    # The stamp keys the cache, including a same-length atomic replacement.
    del stamp
    source = Path(path).read_text(encoding='utf-8')
    declaration = re.search(r'\bexport\s+const\s+' + re.escape(export_name) + r'\s*=\s*', source)
    if declaration is None:
        return ()
    value, end = json.JSONDecoder().raw_decode(source, declaration.end())
    if source[end:].strip() != ';' or not isinstance(value, list) or len(value) > MAX_GROUPS:
        return ()
    return tuple(value)


def _read_manifest(public, filename, export_name):
    path = public / filename
    try:
        if path.is_symlink() or not path.resolve().is_relative_to(public):
            return ()
        stat = path.stat()
        if stat.st_size > MAX_MANIFEST_BYTES:
            return ()
        # Releases replace files atomically. Some server filesystems report
        # coarse timestamps, so a same-size replacement must also key on the
        # actual file identity rather than inheriting the previous JSON cache.
        return _manifest(str(path), (stat.st_dev, stat.st_ino, stat.st_size,
                                     stat.st_mtime_ns, stat.st_ctime_ns), export_name)
    except (OSError, UnicodeError, ValueError, json.JSONDecodeError):
        # A malformed optional crop manifest cannot break ordinary catalogue
        # searches; no guessed or partial associations are published.
        return ()


@lru_cache(maxsize=8)
def _provenance(path, stamp):
    del stamp
    document = json.loads(Path(path).read_text(encoding='utf-8'))
    if not isinstance(document, dict) or set(document) != {'version', 'entries'} or type(document['version']) is not int or document['version'] != 1:
        return ()
    entries = document['entries']
    if not isinstance(entries, list) or len(entries) > MAX_GROUPS:
        return ()
    bindings = {}
    for item in entries:
        if not isinstance(item, dict) or set(item) != {'path', 'sha256', 'native_path', 'native_sha256'}:
            return ()
        path, native_path = _media_path(item['path']), _media_path(item['native_path'])
        if (path is None or native_path is None
            or PurePosixPath(path).suffix.lower() not in DISPLAY_EXTENSIONS
            or PurePosixPath(native_path).suffix.lower() not in NATIVE_EXTENSIONS
            or PurePosixPath(path).parent != PurePosixPath(native_path).parent
            or any(not isinstance(item[key], str) or not SHA256_RE.fullmatch(item[key])
                   for key in ('sha256', 'native_sha256'))):
            return ()
        key = (path, native_path, item['native_sha256'])
        if key in bindings:
            return ()
        bindings[key] = item['sha256']
    return tuple(sorted(bindings.items()))


def _read_provenance(public):
    directory = public.parent
    path = directory / PROVENANCE_FILENAME
    try:
        if path.is_symlink() or not path.resolve().is_relative_to(directory):
            return {}
        stat = path.stat()
        if stat.st_size > MAX_PROVENANCE_BYTES:
            return {}
        return dict(_provenance(str(path), (stat.st_dev, stat.st_ino, stat.st_size,
                                           stat.st_mtime_ns, stat.st_ctime_ns)))
    except (OSError, UnicodeError, ValueError):
        return {}


def _crop(value):
    if not isinstance(value, dict):
        return None
    coordinates = [value.get(key) for key in ('x', 'y', 'width', 'height')]
    if any(isinstance(number, bool) or not isinstance(number, (int, float))
           or not 0 <= number <= 1 or not math.isfinite(number) for number in coordinates):
        return None
    x, y, width, height = map(float, coordinates)
    if min(x, y) < 0 or min(width, height) <= 0 or x + width > 1 + 1e-9 or y + height > 1 + 1e-9:
        return None
    dimensions = [value.get(key) for key in ('sourceWidth', 'sourceHeight')]
    if any(isinstance(number, bool) or not isinstance(number, int)
           or not 16 <= number <= 10_000 for number in dimensions):
        return None
    source_width, source_height = dimensions
    if source_width * source_height > 20_000_000 or width * source_width < 16 or height * source_height < 16:
        return None
    return (x, y, min(width, 1 - x), min(height, 1 - y), source_width, source_height)


def validated_crop(value):
    """Validate a serialized crop identity without trusting dynamic cache data."""
    if not isinstance(value, (list, tuple)) or len(value) != 6:
        return None
    return _crop(dict(zip(('x', 'y', 'width', 'height', 'sourceWidth', 'sourceHeight'), value)))


def _media_path(value):
    if not isinstance(value, str) or not value.startswith('media/') or any(char in value for char in ('\\', '\x00', '?', '#')):
        return None
    path = PurePosixPath(value)
    if path.is_absolute() or '..' in path.parts or path.as_posix() != value:
        return None
    return value


def reviewed_search_views(public, records):
    """Return only audited crops linked to currently active package records.

    Crop metadata retains the native source dimensions. ``review_sha256`` and
    ``review_native_path`` identify the review's original encoded photograph,
    which may differ from the WebP image delivered to the browser. Client
    approval is a separate, fresh permission filter and is never inferred here.
    """
    public = Path(public).resolve()
    records = records.get('records', []) if isinstance(records, dict) else records
    records = records if isinstance(records, (list, tuple)) else []
    active = {record['id'] for record in records if isinstance(record, dict)
              and isinstance(record.get('id'), str) and record['id']
              and record.get('kind') == 'package' and not record.get('archived')}
    provenance = _read_provenance(public)
    views = {}
    for filename, export_name, basis in MANIFESTS:
        for group in _read_manifest(public, filename, export_name):
            if not isinstance(group, dict) or group.get('imageMappingPending') is not False:
                continue
            review, image = group.get('review'), group.get('primaryImage')
            if not isinstance(review, dict) or review.get('basis') != basis or not isinstance(image, dict):
                continue
            digest = review.get('sourceImageSha256')
            if not isinstance(digest, str) or not SHA256_RE.fullmatch(digest):
                continue
            if image.get('role') != 'product' or image.get('imageScope') not in ('single_product', 'same_style_variants') or image.get('missing') or image.get('uncertain'):
                continue
            path, crop = _media_path(image.get('path')), _crop(image.get('displayCrop'))
            record_ids = group.get('recordIds')
            if path is None or PurePosixPath(path).suffix.lower() not in DISPLAY_EXTENSIONS or crop is None or not isinstance(record_ids, list):
                continue
            native_name = review.get('nativeSourceFile')
            if native_name is None:
                native_path = path
            elif (not isinstance(native_name, str) or not native_name
                  or PurePosixPath(native_name).name != native_name
                  or PurePosixPath(native_name).suffix.lower() not in NATIVE_EXTENSIONS):
                continue
            else:
                native_path = _media_path(str(PurePosixPath(path).parent / native_name))
                if native_path is None:
                    continue
            record_ids = {record_id for record_id in record_ids if isinstance(record_id, str) and record_id in active}
            if not record_ids:
                continue
            key = (path, crop, digest, native_path)
            views.setdefault(key, set()).update(record_ids)
    result = []
    for (path, crop, digest, native_path), record_ids in sorted(views.items()):
        view = {'path': path, 'record_ids': sorted(record_ids), 'crop': crop,
                'review_sha256': digest, 'review_native_path': native_path}
        delivered_hash = provenance.get((path, native_path, digest))
        if delivered_hash:
            view['display_sha256'] = delivered_hash
        result.append(view)
    return result
