#!/usr/bin/env python3
"""Prepare small showroom images before publishing; preserve every original."""
import hashlib
import io
import json
from pathlib import Path

from PIL import Image, ImageOps

ASSETS = Path(__file__).resolve().parents[1] / 'docs/mobile-client-preview/assets'


def build(assets=ASSETS):
    assets = Path(assets)
    manifest_path = assets / 'manifest.json'
    manifest = json.loads(manifest_path.read_text())
    originals = [item for item in manifest['files'] if item['kind'] != 'showroom-preview']
    previews = []
    for item in originals:
        name = item['path']
        if Path(name).suffix not in {'.png', '.webp'} or name.endswith('-thumb.webp'):
            continue
        data = (assets / name).read_bytes()
        if hashlib.sha256(data).hexdigest() != item['sha256']:
            raise ValueError('Source checksum mismatch: ' + name)
        for edge in (512, 1280):
            with Image.open(io.BytesIO(data)) as source:
                image = ImageOps.exif_transpose(source).convert('RGB')
                image.thumbnail((edge, edge), Image.Resampling.LANCZOS)
                clean = Image.new('RGB', image.size, 'white')
                clean.paste(image)
                output = io.BytesIO()
                clean.save(output, 'WEBP', quality=80 if edge == 1280 else 76, method=6)
                content = output.getvalue()
            relative = 'previews/' + name.rsplit('.', 1)[0] + f'-{edge}.webp'
            target = assets / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(content)
            previews.append({'path': relative, 'kind': 'showroom-preview',
                             'source': name, 'sourceSha256': item['sha256'],
                             'sha256': hashlib.sha256(content).hexdigest(),
                             'bytes': len(content), 'width': image.width, 'height': image.height,
                             'maxEdge': edge})
    manifest['files'] = originals + previews
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + '\n')
    return previews


if __name__ == '__main__':
    previews = build()
    print(f'Prepared {len(previews)} showroom previews, {sum(x["bytes"] for x in previews):,} bytes; originals preserved.')
