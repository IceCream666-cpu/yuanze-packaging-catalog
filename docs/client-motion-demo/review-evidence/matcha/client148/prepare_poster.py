"""Append only approved poster-083 and its five normal display resources."""
from pathlib import Path
import hashlib
import json
from PIL import Image

ROOT = Path(__file__).resolve().parents[5]
CLIENT = ROOT / 'docs/client-motion-demo'
MOBILE = ROOT / 'docs/mobile-client-preview'
SOURCE = CLIENT / 'model-source/collection/poster-083/matcha-shampoo-poster-v1.png'
POSTER = 'poster-083'


def sha(data):
    return hashlib.sha256(data).hexdigest()


def main():
    original = SOURCE.read_bytes()
    assert sha(original) == "53afd0b0caca47d4a6b5f9818a0179d1badb6861510775103212e606145eaafd", "Approved source changed"
    image = Image.open(SOURCE).convert('RGB')
    assert image.size == (2048, 3072)
    manifest_path = MOBILE / 'assets/manifest.json'
    manifest = json.loads(manifest_path.read_text())
    assert not any(POSTER in e['path'] for e in manifest['files']), 'Already imported; inspect before repeating'
    entries = []

    def save(img, path, **kwargs):
        target = MOBILE / 'assets' / path
        target.parent.mkdir(parents=True, exist_ok=True)
        img.save(target, 'WEBP', method=6, **kwargs)
        data = target.read_bytes()
        return {'path': path, 'width': img.width, 'height': img.height,
                'bytes': len(data), 'sha256': sha(data)}

    full = save(image, f'posters/{POSTER}.webp', lossless=True, exact=True)
    with Image.open(MOBILE / 'assets' / full['path']) as decoded:
        assert decoded.convert('RGB').tobytes() == image.tobytes(), 'Lossless source pixels changed'
    entries.append({**full, 'kind': 'poster-lossless', 'posterId': POSTER,
                    'originalSha256': sha(original), 'originalPixelsSha256': sha(image.tobytes())})
    thumb = image.copy()
    thumb.thumbnail((640, 640), Image.Resampling.LANCZOS)
    entries.append({**save(thumb, f'posters/{POSTER}-thumb.webp', quality=84),
                    'kind': 'poster-thumbnail', 'posterId': POSTER,
                    'sourceImage': full['path'], 'originalSha256': sha(original)})
    for edge in (512, 1280):
        small = image.copy()
        small.thumbnail((edge, edge), Image.Resampling.LANCZOS)
        entries.append({**save(small, f'previews/posters/{POSTER}-{edge}.webp', quality=80 if edge == 1280 else 76),
                        'kind': 'showroom-preview', 'source': full['path'],
                        'sourceSha256': full['sha256'], 'maxEdge': edge})
    manifest['files'] += entries
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + '\n')
    strip = image.copy()
    strip.thumbnail((192, 192), Image.Resampling.LANCZOS)
    strip_path = CLIENT / 'optimized-assets' / f'{POSTER}-strip.webp'
    strip.save(strip_path, 'WEBP', method=6, quality=76)
    strip_data = strip_path.read_bytes()
    path = CLIENT / 'display-derivatives.json'
    derivatives = json.loads(path.read_text())
    derivatives['files'].append({'kind': 'filmstrip', 'file': f'optimized-assets/{strip_path.name}',
        'productionTarget': f'assets/optimized/{strip_path.name}', 'approvedSource': f'assets/{full["path"]}',
        'approvedSourceSha256': full['sha256'], 'sha256': sha(strip_data), 'bytes': len(strip_data),
        'width': strip.width, 'height': strip.height, 'posterId': POSTER})
    path.write_text(json.dumps(derivatives, ensure_ascii=False, indent=2) + '\n')
    path = MOBILE / 'product-posters.js'
    raw = path.read_text()
    catalogue = json.loads(raw[raw.index('{'):].strip().rstrip(';'))
    assert not any(p['id'] == POSTER for p in catalogue['items'])
    catalogue['items'].append({'id': POSTER, 'category': 'hair',
        'title': {'zh': 'liaose 抹茶洗发水', 'en': 'liaose Matcha Shampoo'},
        'src': f'assets/{full["path"]}', 'thumbnail': f'assets/posters/{POSTER}-thumb.webp',
        'width': 2048, 'height': 3072})
    path.write_text(raw[:raw.index('{')] + json.dumps(catalogue, ensure_ascii=False, indent=2) + ';\n')
    print(json.dumps({'poster': POSTER, 'approvedSourceSha256': sha(original), 'resources': 5,
                     'losslessPixelsVerified': True, 'posterCount': len(catalogue['items'])}))


if __name__ == '__main__':
    main()
