"""Detect overlapping image work before independent batches are published."""


def conflicts(edits, other_edits, records):
    """Check source identity and live product associations, regardless of status."""
    other_paths = {e['sourcePath'] for e in other_edits}
    other_shas = {e.get('sourceSHA256') for e in other_edits} - {None, ''}
    other_ids = {r['id'] for e in other_edits for r in e.get('publishedRecords', [])}
    live = [r for r in records if not r.get('archived')
            and r.get('kind') in {'package', 'source_page'}]
    for record in live:
        if any(i.get('path') in other_paths for i in record.get('images', [])):
            other_ids.add(record['id'])
    issues = []
    seen_paths, seen_shas = set(), set()
    for edit in edits:
        path, checksum = edit['sourcePath'], edit.get('sourceSHA256')
        matches = [r for r in live if any(i.get('path') == path for i in r.get('images', []))]
        reasons = []
        if path in other_paths or checksum and checksum in other_shas:
            reasons.append('source reserved by another batch')
        if path in seen_paths or checksum and checksum in seen_shas:
            reasons.append('duplicate source in this batch')
        if not matches:
            reasons.append('no active live product references source')
        if any(r['id'] in other_ids for r in matches):
            reasons.append('live product shared with another batch')
        if reasons:
            issues.append({'sourcePath': path, 'reasons': reasons})
        seen_paths.add(path)
        if checksum:
            seen_shas.add(checksum)
    return issues
