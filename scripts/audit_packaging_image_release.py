"""Audit a published image batch against the live before/after catalogues."""
from packaging_image_batch import unchanged_product


def audit_release(edits, before, after, expected_count=50):
    if len(edits) != expected_count:
        raise ValueError('Incorrect completed image count')
    old = {r['id']: r for r in before}
    new = {r['id']: r for r in after}
    if old.keys() != new.keys():
        raise ValueError('Catalogue record membership changed')
    paths, hashes, outputs, touched = set(), set(), set(), set()
    links = 0
    for edit in edits:
        if edit['status'] != 'published' or not edit.get('publishedRecords'):
            raise ValueError('Image has not been linked to a live product')
        if edit['sourcePath'] in paths or edit['sourceSHA256'] in hashes:
            raise ValueError('Repeated original source')
        uploaded = edit['uploaded']['path']
        if uploaded in outputs:
            raise ValueError('Repeated edited image')
        paths.add(edit['sourcePath']); hashes.add(edit['sourceSHA256']); outputs.add(uploaded)
        for saved in edit['publishedRecords']:
            rid = saved['id']; a, b = old[rid], new[rid]
            if not unchanged_product(a, b):
                raise ValueError('Non-image product data changed')
            original = next((i for i in a['images'] if i['path'] == edit['sourcePath']), None)
            fresh = next((i for i in b['images'] if i['path'] == uploaded), None)
            if not original or not fresh or not {i['path'] for i in a['images']} <= {i['path'] for i in b['images']}:
                raise ValueError('Original gallery or edited association missing')
            if fresh.get('imageScope') != edit['scope'] or fresh.get('role') != 'product':
                raise ValueError('Edited image scope or role mismatched')
            allowed = bool(original.get('clientVisible') and edit['qa'].get('clientSafe')
                           and edit['scope'] in {'single_product', 'same_style_variants'})
            if bool(fresh.get('clientVisible')) != allowed:
                raise ValueError('Customer authorization changed')
            retained = next(i for i in b['images'] if i['path'] == edit['sourcePath'])
            if retained.get('clientVisible'):
                raise ValueError('Original supplier image remains customer visible')
            touched.add(rid); links += 1
    return {'editedImages': len(edits), 'updatedRecords': len(touched),
            'originalAssociationsKept': links, 'sourceDuplicates': 0,
            'nonImageFieldsUnchanged': True, 'customerPermissionsPreserved': True}
