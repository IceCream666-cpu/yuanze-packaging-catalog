"""Build an explicitly authorized, image-only client visibility plan.

This pure function performs no I/O and never changes the supplied objects. The
caller must verify uploaded bytes against its publication evidence, then submit
each patch through the administrator API using the returned current version.
API version conflicts require a fresh snapshot and a new plan, not a retry with
the old gallery. Gallery order, historical QA and image scope are preserved.
"""
from collections.abc import Mapping
from copy import deepcopy
import re


SCOPES = {'single_product', 'same_style_variants', 'source_page', 'unresolved'}
PRODUCT_SCOPES = {'single_product', 'same_style_variants'}
QA_FIELDS = ('identity', 'count', 'watermarks', 'clientSafe')
REVIEW_FIELDS = ('visualReviewed', 'noSensitiveText', 'approvedForClientDisplay')
UPLOAD = re.compile(r'uploads/[0-9a-f]{32}\.jpg\Z')
SHA256 = re.compile(r'[0-9a-f]{64}\Z')
PRODUCT_CODE = re.compile(r'YZ-BC-[0-9]{6,}\Z')


def _require(condition, message):
    if not condition:
        raise ValueError(message)


def _list(value, name):
    _require(isinstance(value, (list, tuple)), name + ' must be a list')
    return value


def _id(value, name):
    _require(isinstance(value, str) and bool(value.strip()) and value == value.strip(),
             name + ' must be a nonempty identifier')
    return value


def _hash(value, name):
    _require(isinstance(value, str) and SHA256.fullmatch(value) is not None,
             name + ' must be a lowercase SHA256')


def _upload(value):
    _require(isinstance(value, str) and UPLOAD.fullmatch(value) is not None,
             'Invalid uploaded image path')
    return value


def _source(value):
    _require(isinstance(value, str) and value.startswith(('media/', 'uploads/'))
             and '\\' not in value and not any(c in value for c in ('?', '#', '%'))
             and not any(ord(c) < 32 for c in value)
             and all(part not in ('', '.', '..') for part in value.split('/')),
             'Invalid sourcePath')


def _version(value, name):
    _require(type(value) is int and value > 0, name + ' must be a positive integer')


def _image(record, path, target=False, scope=None):
    images = _list(record.get('images'), 'record.images')
    _require(all(isinstance(image, Mapping) for image in images),
             'Invalid gallery entry: ' + record['id'])
    matches = [image for image in images if image.get('path') == path]
    if target:
        _require(len(matches) == 1, 'Expected one gallery image: ' + record['id'] + ' / ' + path)
    else:
        # A source file can retain separate supplier/inquiry associations.
        # They are evidence, not duplicate uploads to merge or discard.
        _require(bool(matches), 'Expected source gallery image: ' + record['id'] + ' / ' + path)
    _require(all(image.get('missing') is None or image.get('missing') is False
                 for image in matches),
             'Missing gallery image: ' + record['id'] + ' / ' + path)
    image = matches[0]
    if target:
        _require(isinstance(image.get('role'), str) and image['role'] in {'product', 'reference'},
                 'Unexpected target image role: ' + record['id'])
        _require(image.get('imageScope') == scope,
                 'Target image scope differs from publication: ' + record['id'])
        _require('clientVisible' not in image or type(image['clientVisible']) is bool,
                 'Invalid target clientVisible: ' + record['id'])
    return image


def build_plan(records, edits, approvals, supersessions):
    """Return validated ``patches`` and ``excluded`` without performing writes.

    ``records`` is a current administrator snapshot. ``edits`` is a list of
    published manifest entries (including superseded entries). ``approvals``
    maps an uploaded path to outputSHA256, scope, and three strictly true review
    flags: visualReviewed, noSensitiveText and approvedForClientDisplay.
    ``supersessions`` contains explicit {oldPath, newPath} pairs.

    A published ref's version is a historical lower bound; patches use the
    current record version. Non-package and archived refs are reported before
    code/version checks. Missing records and all ambiguous evidence fail the
    entire plan. Reference approvals do not certify individual capacities.
    """
    _require(isinstance(approvals, Mapping), 'approvals must be keyed by upload path')
    record_index = {}
    for record in _list(records, 'records'):
        _require(isinstance(record, Mapping), 'Invalid record')
        rid = _id(record.get('id'), 'record.id')
        _require(rid not in record_index, 'Duplicate record id: ' + rid)
        record_index[rid] = record

    edit_index, refs_by_path = {}, {}
    for edit in _list(edits, 'edits'):
        _require(isinstance(edit, Mapping) and edit.get('status') == 'published',
                 'Every edit must be published')
        _require(isinstance(edit.get('uploaded'), Mapping), 'Missing uploaded metadata')
        path = _upload(edit['uploaded'].get('path'))
        _require(path not in edit_index, 'Duplicate uploaded path: ' + path)
        _source(edit.get('sourcePath'))
        _require(path != edit['sourcePath'], 'An upload cannot replace itself as its source')
        _hash(edit.get('sourceSHA256'), 'sourceSHA256')
        _hash(edit.get('outputSHA256'), 'outputSHA256')
        _require(isinstance(edit.get('scope'), str) and edit['scope'] in SCOPES,
                 'Invalid published image scope')
        _require(isinstance(edit.get('qa'), Mapping), 'Missing historical QA')
        refs = _list(edit.get('publishedRecords'), 'publishedRecords')
        _require(bool(refs), 'publishedRecords cannot be empty')
        ref_index = {}
        for ref in refs:
            _require(isinstance(ref, Mapping), 'Invalid published ref')
            rid = _id(ref.get('id'), 'published ref id')
            _require(rid not in ref_index, 'Duplicate published ref: ' + rid)
            _require(rid in record_index, 'Published record is missing: ' + rid)
            ref_index[rid] = ref
        edit_index[path], refs_by_path[path] = edit, ref_index

    replaced = {}
    for relation in _list(supersessions, 'supersessions'):
        _require(isinstance(relation, Mapping), 'Invalid supersession')
        old, new = _upload(relation.get('oldPath')), _upload(relation.get('newPath'))
        _require(old != new and old not in replaced, 'Duplicate or self supersession')
        _require(old in edit_index and new in edit_index, 'Supersession edit is missing')
        _require(all(edit_index[old][key] == edit_index[new][key]
                     for key in ('sourcePath', 'sourceSHA256')),
                 'Supersession must have the same sourcePath and sourceSHA256')
        replaced[old] = new
    _require(not set(replaced.values()).intersection(replaced),
             'Supersession newPath must be selected, not itself superseded')

    # Supplied approval evidence must be internally consistent even when an
    # ordinary product image would also pass its original QA.
    for path, approval in approvals.items():
        _require(path in edit_index, 'Approval has no published edit')
        _require(isinstance(approval, Mapping), 'Invalid approval')
        _hash(approval.get('outputSHA256'), 'approval.outputSHA256')
        _require(approval['outputSHA256'] == edit_index[path]['outputSHA256'],
                 'Approval checksum differs from publication: ' + path)
        _require(approval.get('scope') == edit_index[path]['scope'],
                 'Approval scope differs from publication: ' + path)
        _require(all(approval.get(key) is True for key in REVIEW_FIELDS),
                 'Explicit visual and client approval required: ' + path)
    for path, edit in edit_index.items():
        if path in replaced:
            continue
        ordinary = (edit['scope'] in PRODUCT_SCOPES
                    and all(edit['qa'].get(key) is True for key in QA_FIELDS))
        _require(ordinary or path in approvals,
                 'Reference or incomplete QA requires explicit approval: ' + path)

    excluded, active_refs, code_owners = [], {}, {}
    for path, edit in edit_index.items():
        active_refs[path] = set()
        for rid, ref in refs_by_path[path].items():
            record = record_index[rid]
            _require('archived' not in record or type(record['archived']) is bool,
                     'Invalid archived state: ' + rid)
            reason = ('not_package' if record.get('kind') != 'package'
                      else 'archived' if record.get('archived') else None)
            if reason:
                excluded.append({'id': rid, 'uploadPath': path, 'reason': reason,
                                 'kind': record.get('kind')})
                continue
            code = record.get('productCode')
            _require(isinstance(code, str) and PRODUCT_CODE.fullmatch(code) is not None
                     and ref.get('code') == code, 'Product code differs from publication: ' + rid)
            _require(code not in code_owners or code_owners[code] == rid,
                     'Product code belongs to multiple selected records: ' + code)
            code_owners[code] = rid
            _version(record.get('version'), 'record.version')
            _version(ref.get('version'), 'published ref version')
            _require(record['version'] >= ref['version'], 'Record snapshot predates publication: ' + rid)
            _image(record, edit['sourcePath'])
            _image(record, path, target=True, scope=edit['scope'])
            active_refs[path].add(rid)
    for old, new in replaced.items():
        _require(active_refs[old].issubset(active_refs[new]),
                 'Supersession does not cover every active package association: ' + old)
        for rid in sorted(active_refs[old]):
            excluded.append({'id': rid, 'uploadPath': old, 'newPath': new,
                             'reason': 'superseded'})

    # All evidence has passed before constructing even the first patch.
    changes = {}
    for path in edit_index:
        for rid in active_refs[path]:
            changes.setdefault(rid, {})[path] = path not in replaced
    patches = []
    for rid in sorted(changes):
        record = record_index[rid]
        gallery = deepcopy(record['images'])
        changed = False
        for image in gallery:
            path = image.get('path')
            if path not in changes[rid]:
                continue
            visible = changes[rid][path]
            if (image.get('clientVisible') is True) != visible:
                image['clientVisible'] = visible
                changed = True
        if changed:
            patches.append({'action': 'images', 'id': rid, 'version': record['version'],
                            'images': gallery})
    return {'patches': patches, 'excluded': excluded}
