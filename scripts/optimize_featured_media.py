#!/usr/bin/env python3
"""Encode approved cutouts for display; retain original PNGs and poster downloads."""
from pathlib import Path
import hashlib, io, json
from PIL import Image
ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / 'docs/client-motion-demo'
manifest = json.loads((BASE / 'featured-manifest.json').read_text())
output = BASE / 'featured-optimized'
output.mkdir(exist_ok=True)
records = {}
for entry in manifest['files']:
    source = (BASE / entry['file']).read_bytes()
    assert hashlib.sha256(source).hexdigest() == entry['sha256']
    original = Image.open(io.BytesIO(source)).convert('RGBA')
    record = {'sourceSha256': entry['sha256'], 'width': original.width, 'height': original.height, 'files': {}}
    for size in [640, 1024]:
        image = original.copy()
        image.thumbnail((size, size), Image.Resampling.LANCZOS)
        path = output / f"{entry['posterId']}-{size}.webp"
        # Preserve 640/1024 resolution and lossless alpha. Reviewed q82 encoding
        # reduces first-screen transfer without changing approved PNG originals.
        image.save(path, 'WEBP', quality=82, method=6)
        record['files'][str(size)] = {'file': str(path.relative_to(BASE)), 'bytes': path.stat().st_size,
            'sha256': hashlib.sha256(path.read_bytes()).hexdigest(), 'width': image.width, 'height': image.height}
    records[entry['posterId']] = record
(BASE / 'src/featured-media.json').write_text(json.dumps(records, indent=2) + '\n')
print(json.dumps({'originalBytes':sum(e['bytes'] for e in manifest['files']),
    'mobileBytes':sum(r['files']['640']['bytes'] for r in records.values()),
    'desktopBytes':sum(r['files']['1024']['bytes'] for r in records.values())}))
