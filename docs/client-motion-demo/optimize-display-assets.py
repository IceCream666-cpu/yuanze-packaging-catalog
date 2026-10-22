"""Derive a pixel-identical visible logo and small filmstrip images from approved assets."""
import base64
import hashlib
import io
import json
from pathlib import Path
import xml.etree.ElementTree as ET

from PIL import Image

BASE = Path(__file__).resolve().parent
ROOT = BASE.parents[1]
SHOWROOM = ROOT / 'server-reference/public/showroom'
OUTPUT = BASE / 'optimized-assets'
SCOPE = 'approved-client-display-optimization'


def digest(data):
    return hashlib.sha256(data).hexdigest()


def main():
    approved = {f"assets/{item['path']}": item for item in json.loads(
        (ROOT / 'docs/mobile-client-preview/assets/manifest.json').read_text())['files']}
    OUTPUT.mkdir(parents=True, exist_ok=True)
    entries = []

    def source_bytes(route):
        expected = approved[route]
        data = (SHOWROOM / route).read_bytes()
        if digest(data) != expected['sha256'] or len(data) != expected['bytes']:
            raise ValueError(f'Original no longer matches the approved source: {route}')
        return data

    def save(image, name, source, source_data, kind, **properties):
        target = OUTPUT / name
        image.save(target, 'WEBP', method=6, **({'lossless': True, 'exact': True} if kind == 'visible-logo' else {'quality': 76}))
        data = target.read_bytes()
        if kind == 'visible-logo':
            with Image.open(io.BytesIO(data)) as actual:
                if actual.convert('RGBA').tobytes() != image.convert('RGBA').tobytes():
                    raise ValueError('Visible logo pixels changed during lossless encoding')
        entries.append({'kind': kind, 'file': f'optimized-assets/{name}',
                        'productionTarget': f'assets/optimized/{name}', 'approvedSource': source,
                        'approvedSourceSha256': digest(source_data), 'sha256': digest(data),
                        'bytes': len(data), 'width': image.width, 'height': image.height, **properties})

    route = 'assets/yuanze-mark.svg'
    raw = source_bytes(route)
    svg = ET.fromstring(raw)
    images = list(svg.findall('{http://www.w3.org/2000/svg}image'))
    viewbox = [int(value) for value in svg.attrib['viewBox'].split()]
    if len(images) != 1 or viewbox != [1200, 264, 152, 171] or images[0].get('transform'):
        raise ValueError('Logo composition changed; review the visible crop before regenerating')
    embedded = images[0].attrib['href']
    if not embedded.startswith('data:image/png;base64,'):
        raise ValueError('Expected the approved embedded PNG logo')
    with Image.open(io.BytesIO(base64.b64decode(embedded.split(',', 1)[1], validate=True))) as original:
        if original.size != (1800, 1520):
            raise ValueError('Embedded logo dimensions changed')
        x, y, width, height = viewbox
        visible = original.crop((x, y, x + width, y + height))
        save(visible, 'yuanze-mark-compact.webp', route, raw, 'visible-logo', crop=viewbox)

    posters = json.loads((BASE / 'src/posters.json').read_text())
    ids = [item['id'] for item in posters]
    if len(ids) != 38 or len(set(ids)) != 38:
        raise ValueError('Expected the current 38 approved posters')
    for poster_id in sorted(ids):
        route = f'assets/posters/{poster_id}.webp'
        raw = source_bytes(route)
        with Image.open(io.BytesIO(raw)) as original:
            thumbnail = original.convert('RGB')
            thumbnail.thumbnail((192, 192), Image.Resampling.LANCZOS)
            save(thumbnail, f'{poster_id}-strip.webp', route, raw, 'filmstrip', posterId=poster_id)

    (BASE / 'display-derivatives.json').write_text(json.dumps(
        {'schema': 1, 'scope': SCOPE, 'files': entries}, ensure_ascii=False, indent=2) + '\n')
    print(f'Prepared {len(entries)} display derivatives: {sum(entry["bytes"] for entry in entries):,} bytes; approved originals unchanged.')


if __name__ == '__main__':
    main()
