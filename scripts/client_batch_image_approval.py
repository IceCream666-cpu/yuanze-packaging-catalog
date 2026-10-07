"""Build image-only client approvals for an explicitly selected published batch.

This module performs no I/O. Callers supply a current catalog snapshot and the
published edits, then submit the returned patches with their version checks.
"""

from copy import deepcopy
import re


SAFE_SCOPES = {'single_product', 'same_style_variants'}
SOURCE_SCOPES = SAFE_SCOPES | {'source_page', 'unresolved'}
SOURCE_ROLES = {'supplier', 'inquiry', 'product', 'reference', 'customer',
                'floating-reference', 'other', 'test-plan'}
UPLOAD_PATH = re.compile(r'uploads/[0-9a-f]{32}\.jpg')
QA_FIELDS = ('identity', 'count', 'watermarks', 'clientSafe')


def _text(value, label):
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f'{label} must be a nonempty string')
    return value


def _source_path(value):
    value = _text(value, 'sourcePath')
    parts = value.split('/')
    if (parts[0] != 'media' or len(parts) < 2
            or any(part in {'', '.', '..'} for part in parts)
            or any(char in value for char in ('\\', '\x00', '?', '#', '%'))):
        raise ValueError('sourcePath must be a canonical media path')
    return value


def _image_evidence(image, *, target_scope=None):
    if image.get('missing') or image.get('uncertain'):
        raise ValueError('Missing or uncertain image cannot support approval')
    if target_scope is None:
        role, scope = image.get('role'), image.get('imageScope')
        if (not isinstance(role, str) or role not in SOURCE_ROLES
                or not isinstance(scope, str) or scope not in SOURCE_SCOPES):
            raise ValueError('Original image role or scope is invalid')
    elif image.get('role') != 'product' or image.get('imageScope') != target_scope:
        raise ValueError('Uploaded image role or scope does not match the reviewed edit')
    if 'clientVisible' in image and type(image['clientVisible']) is not bool:
        raise ValueError('Image clientVisible must be a boolean')


def build_plan(records, edits):
    """Return one patch per changed record, after validating the entire batch.

    Only existing uploads named in each edit's publishedRecords are approved.
    The input order of records and each gallery is retained, and inputs are never
    mutated. Already approved images produce no patch. A source shared by many
    products is approved only for the explicitly listed product IDs and codes.
    Invalid or incomplete evidence raises ValueError, including on repeat runs.
    """
    if not isinstance(records, list) or not isinstance(edits, list):
        raise ValueError('records and edits must be lists')
    by_id = {}
    for record in records:
        if not isinstance(record, dict):
            raise ValueError('Record must be an object')
        record_id = _text(record.get('id'), 'Record id')
        if record_id in by_id:
            raise ValueError(f'Duplicate record id: {record_id}')
        by_id[record_id] = record

    selected = {}
    upload_sources = {}
    # No patch is built until all edits and every published association pass.
    for edit in edits:
        if not isinstance(edit, dict) or edit.get('status') != 'published':
            raise ValueError('Every edit must be published')
        qa = edit.get('qa')
        if not isinstance(qa, dict) or not all(qa.get(field) is True for field in QA_FIELDS):
            raise ValueError('Every visual review and client safety check must pass')
        scope = edit.get('scope')
        if not isinstance(scope, str) or scope not in SAFE_SCOPES:
            raise ValueError('Edit scope is not client safe')
        source = _source_path(edit.get('sourcePath'))
        uploaded = edit.get('uploaded')
        path = uploaded.get('path') if isinstance(uploaded, dict) else None
        if not isinstance(path, str) or not UPLOAD_PATH.fullmatch(path):
            raise ValueError('Uploaded path must be uploads/<32 lowercase hex>.jpg')
        evidence = (source, scope)
        if path in upload_sources and upload_sources[path] != evidence:
            raise ValueError('Conflicting source or scope for the same upload')
        upload_sources[path] = evidence
        refs = edit.get('publishedRecords')
        if not isinstance(refs, list) or not refs:
            raise ValueError('Published record provenance is required')
        for ref in refs:
            if not isinstance(ref, dict):
                raise ValueError('Published record reference must be an object')
            record_id = _text(ref.get('id'), 'Published record id')
            code = _text(ref.get('code'), 'Published product code')
            record = by_id.get(record_id)
            if record is None:
                raise ValueError(f'Published record is missing: {record_id}')
            if record.get('productCode') != code:
                raise ValueError(f'Product code does not match: {record_id}')
            if record.get('archived') or record.get('kind') != 'package':
                raise ValueError(f'Record is archived or is not a package: {record_id}')
            version = record.get('version')
            if type(version) is not int or version < 1:
                raise ValueError(f'Current record version is invalid: {record_id}')
            images = record.get('images')
            if not isinstance(images, list) or not all(isinstance(image, dict) for image in images):
                raise ValueError(f'Gallery is invalid: {record_id}')
            originals = [image for image in images if image.get('path') == source]
            targets = [image for image in images if image.get('path') == path]
            if not originals or len(targets) != 1:
                raise ValueError(f'Original or unique uploaded image is missing: {record_id}')
            for original in originals:
                _image_evidence(original)
            _image_evidence(targets[0], target_scope=scope)
            selected.setdefault(record_id, set()).add(path)

    plan = []
    for record in records:
        paths = selected.get(record['id'], set())
        if not paths:
            continue
        if not any(image.get('path') in paths and image.get('clientVisible') is not True
                   for image in record.get('images', []) if isinstance(image, dict)):
            continue
        images = deepcopy(record['images'])
        for image in images:
            if image.get('path') in paths:
                image['clientVisible'] = True
        plan.append({'action': 'images', 'id': record['id'],
                     'version': record['version'], 'images': images})
    return plan
