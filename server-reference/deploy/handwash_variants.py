"""Source-confirmed, versioned media/price patch for the two handwash sizes.

This builds normal AdminStore bulk-save inputs; it never writes SQL or renumbers
products. The production runner backs up and checks versions before applying.
"""
from copy import deepcopy
from decimal import Decimal, InvalidOperation
import re

VARIANTS = (
    ('YZ-S01-R0012', 'YZ-BC-000009', 250, '1.35元'),
    ('YZ-S01-R0013', 'YZ-BC-000010', 500, '1.60元'),
)
UPLOAD = re.compile(r'uploads/[a-f0-9]{32}\.jpg\Z')
PREVIOUS_COVER = 'uploads/322d638682b9465ba78a880d857450b9.jpg'


def build_rows(records, images):
    """Reject stale identity/spec/quote evidence and pair-specific image reuse."""
    lookup = {r['id']: r for r in records}
    if len(lookup) != 2 or set(lookup) != {v[0] for v in VARIANTS}:
        raise ValueError('Expected precisely the two source records')
    if set(images) != {250, 500}:
        raise ValueError('Both confirmed sizes require a main image')
    paths = [images[size].get('path') for size in (250, 500)]
    if any(not isinstance(p, str) or not UPLOAD.fullmatch(p) for p in paths) or len(set(paths)) != 2:
        raise ValueError('Each size needs a different registered upload path')
    rows = []
    for rid, code, size, price in VARIANTS:
        record = lookup[rid]
        if record.get('productCode') != code or record.get('capacityMl') != size or record.get('archived'):
            raise ValueError('Product identity/specification changed; review again')
        if not re.fullmatch(str(size) + r'\s*ml', str(record.get('specificationRaw', '')), re.I):
            raise ValueError('Source specification changed; review again')
        try:
            matches = Decimal(str(record.get('quoteRaw', ''))) == Decimal(price[:-1])
        except InvalidOperation:
            matches = False
        if not matches or record.get('bareBottlePrice') not in (None, '', price):
            raise ValueError('Source quote or maintained bare price changed; review again')
        if type(record.get('version')) is not int or record['version'] < 1:
            raise ValueError('A current record version is required')
        original = deepcopy(record.get('images', []))
        if not any(i.get('path') == 'media/image30.jpeg' for i in original):
            raise ValueError('The confirmed left/right source image is absent')
        for image in original:
            image['clientVisible'] = False
            if image.get('path') == PREVIOUS_COVER:
                image.update(role='reference', caption='此前共用优化图，仅用于历史核对', imageScope='unresolved')
            elif image.get('path') == 'media/image30.jpeg':
                image['caption'] = '原始对照图：左侧250mL，右侧500mL'
            elif size == 500 and image.get('path') == 'media/image27.jpeg':
                image.update(role='reference', caption='原表关联图片，仅用于来源核对')
        main = {**deepcopy(images[size]), 'role': 'product', 'imageScope': 'single_product',
                'clientVisible': True, 'caption': f'{size}mL 主图 · AI优化展示，原始图片保留供核对'}
        rows.append({'id': rid, 'version': record['version'],
                     'record': {'bareBottlePrice': price, 'images': [main, *original]}})
    return rows
