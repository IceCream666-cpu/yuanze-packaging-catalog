#!/usr/bin/env python3
"""Rebuild reviewed browser assets from original PDFs, without changing product data.

The manifest retains exact source-image hashes and separate CSS display rectangles.
No bitmap cropping, generative enhancement, or inference of missing parameters occurs.
"""
import argparse
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]


def digest(data):
    return hashlib.sha256(data).hexdigest()


def manifest_groups(path):
    source = Path(path).read_text(encoding='utf-8')
    return json.loads(source[source.index('[{'):source.rindex(']') + 1])


def deliver_photo(native, expected, display, preview):
    """Preserve native bytes; convert unsupported formats losslessly for browsers."""
    from PIL import Image
    if digest(native.read_bytes()) != expected:
        raise ValueError('Original photo changed; review it before rebuilding')
    with Image.open(native) as original:
        if not 0 < original.width * original.height <= 24_000_000:
            raise ValueError('Original photo dimensions exceed the delivery limit')
        if native != display:
            original.convert('RGB').save(display, format='WEBP', lossless=True)
        im = original.convert('RGB')
        im.thumbnail((1536, 1536))
        im.save(preview, format='WEBP', quality=80, method=4)
        return original.size


def rebuild(pdf_root, output, groups):
    from pypdf import PdfReader
    output.mkdir(parents=True, exist_ok=True)
    readers, completed = {}, set()
    for group in groups:
        review, image = group['review'], group['primaryImage']
        page = int(review.get('imagePage') or review['page'])
        filename = review['catalogue']
        if Path(filename).name != filename:
            raise ValueError('Unsafe source filename')
        native_name = review['nativeSourceFile']
        names = [native_name, Path(image['path']).name, Path(image['previewPath']).name]
        if any(Path(name).name != name for name in names):
            raise ValueError('Unsafe asset filename')
        expected = review['sourceImageSha256']
        # Identical source photographs may have different source-specific names.
        # Rebuilding must deliver every referenced name, not just the first hash.
        delivery_key = (expected, *names)
        if delivery_key in completed:
            continue
        native, display, preview = [output / name for name in names]
        if not native.is_file():
            pdf = pdf_root / filename
            if filename not in readers:
                readers[filename] = PdfReader(pdf)
            candidates = readers[filename].pages[page - 1].images
            key = review.get('sourceImageKey')
            if key:
                chosen = candidates[key]
                if digest(chosen.data) != expected:
                    raise ValueError('Original PDF image changed')
            else:
                chosen = next((value for value in candidates if digest(value.data) == expected), None)
                if chosen is None:
                    raise ValueError('Reviewed photo not found in the original PDF')
            native.write_bytes(chosen.data)
        size = deliver_photo(native, expected, display, preview)
        crop = image['displayCrop']
        if size != (crop['sourceWidth'], crop['sourceHeight']):
            raise ValueError('Reviewed viewport dimensions no longer match its source')
        completed.add(delivery_key)
    return len(completed)


def main():
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument('--pdf-root', type=Path, required=True)
    cli.add_argument('--output', type=Path, default=ROOT/'server-reference/private/media/type-views')
    cli.add_argument('--manifest', type=Path, default=ROOT/'server-reference/public/product-type-group-data.js')
    options = cli.parse_args()
    count = rebuild(options.pdf_root, options.output, manifest_groups(options.manifest))
    print(json.dumps({'rebuiltSourcePhotos': count, 'businessRecordsChanged': False}))


if __name__ == '__main__':
    main()
