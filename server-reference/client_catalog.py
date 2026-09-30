"""Explicitly approved customer catalogue; private records never cross this boundary."""
import hashlib
import hmac
import json
import math
import os
from pathlib import Path
import re
import secrets
import threading
import unicodedata


class ClientMediaBusy(Exception):
    pass


def normalized(value):
    return unicodedata.normalize('NFKC', value).strip().casefold() if isinstance(value, str) else ''


# Public labels are code-owned constants, never the editable administrator
# taxonomy or substrings extracted from product names, OCR, vendors or quotes.
CATEGORIES = {
    '瓶类': ('瓶', 'bottle', 'bottles'),
    '罐与广口盒': ('罐', '罐类', '膏霜盒', 'jar', 'jars'),
    '软管': ('tube', 'tubes'),
    '泵头与喷头': ('泵头', '喷头', 'pump', 'pumps', 'sprayer'),
    '盖与其他配件': ('盖子', '瓶盖', '配件', 'cap', 'caps', 'closure', 'accessories'),
    '滴管与滴管瓶': ('滴管', 'dropper', 'droppers'),
    '袋类': ('袋', '膜袋', '袋子', 'pouch', 'pouches', 'bag', 'bags'),
    '外包装': ('彩盒', '纸盒', '包装盒', '礼盒', '内托', 'box', 'boxes', 'outer packaging'),
    '标签辅材': ('标签', '标贴', 'label', 'labels'),
    '套装': ('set', 'sets'),
    '其他': ('other',),
}
BOTTLE_TYPES = {
    '圆瓶': ('round bottle', 'round'), '方瓶': ('square bottle', 'square'),
    '异形瓶': ('shaped bottle', 'shaped'), '广口瓶': ('wide mouth bottle', 'wide-mouth bottle'),
    '真空瓶': ('airless bottle', 'airless'), '泡沫瓶': ('foam bottle', 'foaming bottle', 'foam'),
    '喷雾瓶': ('spray bottle', 'spray'), '滴管瓶': ('dropper bottle',),
    '膏霜罐': ('cream jar',), '乳液瓶': ('lotion bottle',),
    '香水瓶': ('perfume bottle',), '滚珠瓶': ('roll-on bottle', 'roller bottle'),
    '安瓿瓶': ('ampoule', 'ampoule bottle'),
}
MATERIALS = {
    **{value: () for value in ('PET', 'PETG', 'PE', 'HDPE', 'LDPE', 'PP', 'PMMA', 'AS', 'ABS', 'PS', 'PVC')},
    '玻璃': ('glass',), '铝': ('aluminum', 'aluminium'), '纸': ('paper',),
    '塑料（待细分）': ('塑料', '塑胶', 'plastic'), '硅胶': ('silicone',),
    '橡胶': ('rubber',), '不锈钢': ('stainless steel',),
    '无纺布': ('nonwoven', 'non-woven'), '铝塑复合': ('aluminum plastic laminate',),
}
USES = {
    '水剂': ('water-based', 'aqueous'), '乳液': ('lotion',), '膏霜': ('cream',),
    '油剂': ('oil-based',), '凝胶': ('gel',), '粉体': ('powder',), '洗护': ('wash and care',),
    '洁面': ('洗面奶', '洗颜', 'face cleanser', 'facial cleanser', 'face wash'),
    '卸妆': ('makeup remover', 'make-up remover', 'cleansing oil', 'cleansing balm'),
    '精华液': ('精华', '精华露', '精华素', 'serum'),
    '爽肤水': ('toner', 'facial toner'), '化妆水': ('skin toner',),
    '面霜': ('face cream', 'facial cream'), '眼霜': ('eye cream',),
    '眼部精华': ('眼精华', 'eye serum'), '面膜': ('眼膜', 'face mask', 'facial mask', 'sheet mask'),
    '唇部护理': ('润唇', '唇膏', '唇油', 'lip care', 'lip balm', 'lip oil'),
    '防晒': ('sunscreen', 'sunblock', 'sun care'), '粉底液': ('liquid foundation',),
    '底妆': ('粉底', '隔离霜', '妆前', '遮瑕', '气垫', 'foundation', 'concealer', 'makeup primer'),
    '唇彩': ('口红', '唇釉', '唇泥', 'lipstick', 'lip gloss', 'lip tint'),
    '眉妆': ('眉粉', '眉笔', '眉胶', 'brow pencil', 'brow gel', 'eyebrow powder'),
    '睫毛产品': ('睫毛', 'mascara', 'eyelash'),
    '洗手液': ('洗手慕斯', 'hand wash', 'hand soap'),
    '洗发水': ('洗发露', '洗发液', '洗发乳', 'shampoo'), '护发素': ('hair conditioner',),
    '发膜': ('hair mask',), '头皮护理': ('scalp care',),
    '头发造型': ('发胶', '发蜡', '发泥', '定型喷雾', 'hair spray', 'hair gel', 'hair wax', 'hair styling'),
    '染发': ('hair dye', 'hair color', 'hair colour'),
    '沐浴露': ('沐浴乳', '沐浴液', '沐浴油', 'body wash', 'shower gel', 'shower cream'),
    '身体乳': ('body lotion',), '身体霜': ('身体润肤霜', 'body cream', 'body butter'),
    '身体油': ('body oil',), '身体磨砂': ('body scrub',),
    '护手霜': ('手霜', 'hand cream'), '手足护理': ('手部护理', '足部护理', 'hand and foot care'),
    '护足霜': ('脚霜', 'foot cream'), '脱毛': ('depilatory', 'hair removal'),
    '止汗除臭': ('体香剂', 'deodorant', 'antiperspirant'),
    '香水': ('perfume', 'eau de parfum', 'eau de toilette'),
    '身体香氛': ('身体喷雾', 'body mist', 'body fragrance'), '香氛': ('fragrance',),
    '美甲': ('指甲油', '甲油胶', 'nail polish', 'nail gel', 'nail care'),
    '口腔护理': ('漱口水', '牙膏', 'mouthwash', 'toothpaste', 'oral care'),
    '精油': ('essential oil',), '洗衣液': ('laundry detergent',),
    '家居清洁': ('洗洁精', '厨房清洁', 'dishwashing liquid', 'household cleaner'),
}
SECTIONS = {'face': ('面部', '脸部', '眼部', '唇部', 'facial'),
            'body-head': ('身体/头部', '身体', '头部', '头皮', '头发', 'body', 'hair', 'scalp')}
SECTION_USES = {
    'face': {'洁面', '卸妆', '爽肤水', '化妆水', '面霜', '眼霜', '眼部精华', '面膜', '唇部护理', '粉底液', '底妆', '唇彩', '眉妆', '睫毛产品'},
    'body-head': {'洗手液', '洗发水', '护发素', '发膜', '头皮护理', '头发造型', '染发', '沐浴露', '身体乳', '身体霜', '身体油', '身体磨砂', '护手霜', '手足护理', '护足霜', '脱毛', '止汗除臭', '香水', '身体香氛', '美甲'},
}
VOCABULARIES = (CATEGORIES, BOTTLE_TYPES, MATERIALS, USES, SECTIONS)
ALIASES = {id(vocabulary): {normalized(alias): label for label, aliases in vocabulary.items()
                          for alias in (label, *aliases)} for vocabulary in VOCABULARIES}


def canonical(value, vocabulary):
    return ALIASES[id(vocabulary)].get(normalized(value), '')


def canonical_list(values, vocabulary):
    values = values if isinstance(values, list) else [values]
    return list(dict.fromkeys(label for value in values if (label := canonical(value, vocabulary))))


def details(record):
    values = record.get('productDetails')
    return [value for value in values if isinstance(value, dict)] if isinstance(values, list) else []


def trusted_source(detail, allowed):
    source = detail.get('sourceField', '')
    return isinstance(source, str) and source in allowed


def safe_measurement(value, family, implicit_unit=''):
    """Accept a complete numeric measurement only; never carry original text."""
    units = {'ml': ('mL', 1), '毫升': ('mL', 1), 'l': ('L', 1000), '升': ('L', 1000),
             'g': ('g', 1), '克': ('g', 1), 'kg': ('kg', 1000), '千克': ('kg', 1000),
             'mm': ('mm', 1), '毫米': ('mm', 1), 'cm': ('cm', 10), '厘米': ('cm', 10)}
    match = re.fullmatch(r'(\d{1,6}(?:\.\d{1,3})?)\s*([a-z]+|毫升|千克|毫米|厘米|升|克)?', normalized(value))
    if not match:
        return None
    unit = match[2] or implicit_unit
    allowed = {'capacity': {'ml', '毫升', 'l', '升', 'g', '克', 'kg', '千克'},
               'volume': {'ml', '毫升', 'l', '升'}, 'mass': {'g', '克', 'kg', '千克'},
               'length': {'mm', '毫米', 'cm', '厘米'}}[family]
    if unit not in allowed:
        return None
    amount = float(match[1]); unit_name, scale = units[unit]
    maximum = 10000 if family == 'length' else 100000
    if not 0 < amount * scale <= maximum:
        return None
    return f'{amount:g} {unit_name}', amount * scale, unit_name


def capacity_info(record):
    value = record.get('capacityMl')
    if type(value) in (int, float) and math.isfinite(value) and 0 < value <= 100000:
        return f'{value:g} mL', value
    for detail in details(record):
        if normalized(detail.get('label')) not in {'净含量', '标称容量', '容量'} or not trusted_source(detail, {'', 'capacityMl', 'specificationRaw'}):
            continue
        measured = safe_measurement(detail.get('value'), 'capacity')
        if measured:
            display, amount, unit = measured
            return display, amount if unit in {'mL', 'L'} else None
    return '', None


def safe_capacity(record):
    return capacity_info(record)[0]


DIMENSIONS = {
    '口径': ('length', ('瓶口直径', 'neck diameter')),
    '瓶高': ('length', ('bottle height',)), '高度': ('length', ('高', 'height')),
    '直径': ('length', ('瓶身直径', 'diameter')), '底径': ('length', ('瓶底直径', 'base diameter')),
    '长度': ('length', ('长', 'length')), '宽度': ('length', ('宽', 'width')),
    '厚度': ('length', ('厚', 'thickness')), '重量': ('mass', ('净重', 'weight')),
    '满口容量': ('volume', ('满容量', 'overflow capacity', 'brimful capacity')),
}


def safe_specifications(record):
    specifications, seen = [], set()
    for detail in details(record):
        if not trusted_source(detail, {'', 'specificationRaw'}):
            continue
        label = normalized(detail.get('label'))
        for name, (family, aliases) in DIMENSIONS.items():
            implicit = ''
            if label not in {normalized(name), *(normalized(alias) for alias in aliases)}:
                # A unit in the trusted label permits a bare numeric cell.
                found = re.fullmatch(r'(.+?)\s*\((mm|cm|g|kg|ml|l)\)', label)
                if not found or found[1].strip() not in {normalized(name), *(normalized(alias) for alias in aliases)}:
                    continue
                implicit = found[2]
            measured = safe_measurement(detail.get('value'), family, implicit)
            if measured and (name, measured[0]) not in seen:
                seen.add((name, measured[0]))
                specifications.append({'label': name, 'value': measured[0]})
            break
    return specifications


def project_record(record, product_code):
    """The only customer data boundary: build every field from safe primitives."""
    category = canonical(record.get('category'), CATEGORIES)
    bottle_type = canonical(record.get('bottleType'), BOTTLE_TYPES)
    materials = canonical_list(record.get('materials'), MATERIALS)
    uses = canonical_list(record.get('uses'), USES)
    sections = canonical_list(record.get('sections'), SECTIONS)
    for detail in details(record):
        label = normalized(detail.get('label'))
        if label in {'用途', '产品用途', '适用用途', '适用产品', '应用产品', 'usage', 'purpose', 'application', 'uses'} and trusted_source(detail, {'', 'uses'}):
            uses.extend(canonical_list(detail.get('value'), USES))
        if label in {'使用部位', '适用部位', '应用部位', 'body area', 'application area'} and trusted_source(detail, {'', 'uses'}):
            sections.extend(canonical_list(detail.get('value'), SECTIONS))
    uses = list(dict.fromkeys(uses))
    sections = [section for section in SECTIONS if section in sections or SECTION_USES[section].intersection(uses)]
    capacity, capacity_ml = capacity_info(record)
    code = product_code if isinstance(product_code, str) and re.fullmatch(r'YZ-BC-[0-9]{6,}', product_code) else ''
    return {'productCode': code, 'name': ' · '.join(value for value in (bottle_type or category or '包材', capacity) if value),
            'capacity': capacity, 'capacityMl': capacity_ml, 'category': category, 'bottleType': bottle_type,
            'materials': materials, 'uses': uses, 'sections': sections, 'specifications': safe_specifications(record)}


def search_text(item):
    # Even search matching is based only on the public projection: private
    # supplier, price and source probes cannot reveal whether a record exists.
    values = [item['productCode'], item['name'], item['capacity']]
    for fields, vocabulary in (([item['category']], CATEGORIES), ([item['bottleType']], BOTTLE_TYPES),
                              (item['materials'], MATERIALS), (item['uses'], USES), (item['sections'], SECTIONS)):
        for field in fields:
            values.extend((field, *vocabulary.get(field, ())))
    for specification in item['specifications']:
        values.extend((specification['label'], specification['value'], *DIMENSIONS[specification['label']][1]))
    return normalize_search(' '.join(values))


def normalize_search(value):
    return re.sub(r'(\d+(?:\.\d+)?)\s*(?:毫升|ml)', r'\1ml', normalized(value))


def matches_search(item, query):
    haystack = search_text(item)
    for term in re.findall(r'[\w]+(?:[.-][\w]+)*', normalize_search(query)):
        if re.fullmatch(r'[a-z0-9_.-]+', term):
            if not re.search(r'(?<![a-z0-9])' + re.escape(term) + r'(?![a-z0-9])', haystack):
                return False
        elif term not in haystack:
            return False
    return True


FACETS = {'category': ('categories', 'category'), 'material': ('materials', 'materials'),
          'capacity': ('capacities', 'capacity'), 'bottle': ('bottleTypes', 'bottleType'),
          'use': ('uses', 'uses'), 'section': ('sections', 'sections')}


def facet_values(item, field):
    value = item[field]
    return value if isinstance(value, list) else ([value] if value else [])


class ClientCatalog:
    PAGE_SIZE = 24
    TOKEN_RE = re.compile(r'^[a-f0-9]{64}\.jpg$')

    def __init__(self, store, state, private):
        self.store = store
        self.state, self.private = Path(state).resolve(), Path(private).resolve()
        self.cache = self.state / 'client-media'
        self.cache.mkdir(mode=0o700, parents=True, exist_ok=True)
        self.cache.chmod(0o700)
        keyfile = self.cache / 'key'
        try:
            descriptor = os.open(keyfile, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
            with os.fdopen(descriptor, 'wb') as output:
                output.write(secrets.token_bytes(32))
        except FileExistsError:
            pass
        self.key = keyfile.read_bytes()
        if len(self.key) != 32:
            raise ValueError('Invalid customer media key')
        self.gate = threading.Lock()
        # A first page may request many uncached images at once. Queue a small
        # number of conversions instead of failing the whole page immediately.
        self.waiters = threading.BoundedSemaphore(12)
        with self.store.connection(True) as conn:
            conn.execute('''CREATE TABLE IF NOT EXISTS client_media_map (
                token TEXT PRIMARY KEY, record_id TEXT NOT NULL, image_path TEXT NOT NULL
            )''')

    def opaque(self, namespace, *values):
        return hmac.new(self.key, json.dumps([namespace, *values], ensure_ascii=False).encode(), hashlib.sha256).hexdigest()

    def source(self, path):
        if not isinstance(path, str) or '\\' in path:
            return None
        if path.startswith('media/'):
            base = self.private / 'media'
            candidate = self.private / path
        elif path.startswith('uploads/'):
            base = self.state / 'uploads'
            candidate = self.state / path
        else:
            return None
        target = candidate.resolve()
        if not target.is_relative_to(base.resolve()) or not target.is_file():
            return None
        return target

    def approved_images(self, record):
        if record.get('kind') != 'package':
            return []
        result, seen = [], set()
        for image in record.get('images', []):
            if not isinstance(image, dict) or image.get('clientVisible') is not True or image.get('missing'):
                continue
            path = image.get('path')
            if not isinstance(path, str) or path in seen or self.source(path) is None:
                continue
            seen.add(path)
            result.append(path)
        return result

    def catalog(self, page=1, page_size=24, q='', filters=None):
        page = max(1, page)
        page_size = max(1, min(48, page_size))
        entries, mappings = [], []
        # json_each applies the opt-in filter in SQLite, avoiding a full parsed
        # copy of the employee catalogue for every customer request.
        with self.store.connection() as conn:
            rows = conn.execute('''SELECT r.id,r.content,pc.product_code FROM admin_records AS r
                LEFT JOIN admin_product_codes AS pc ON pc.record_id=r.id
                WHERE r.archived=0 AND json_extract(r.content,'$.kind')='package'
                  AND EXISTS (SELECT 1 FROM json_each(r.content,'$.images') AS image
                              WHERE json_extract(image.value,'$.clientVisible')=1
                                AND json_type(image.value,'$.clientVisible')='true')
                ORDER BY r.id''')
            for row in rows:
                record = json.loads(row['content'])
                paths = self.approved_images(record)
                if not paths:
                    continue
                images = []
                for path in paths:
                    token = self.opaque('image', row['id'], path) + '.jpg'
                    mappings.append((token, row['id'], path))
                    images.append({'url': '/client-media/' + token})
                entries.append({'id': self.opaque('record', row['id']),
                                **project_record(record, row['product_code']), 'images': images})
        # The table only resolves opaque handles; every request below rechecks
        # current approval and archive state, including cache hits.
        if mappings:
            with self.store.connection(True) as conn:
                conn.executemany('INSERT OR IGNORE INTO client_media_map VALUES(?,?,?)', mappings)
        # Stable facet choices cover only currently approved packages, even if
        # the selected combination has zero matches. Never inspect raw fields.
        facets = {key: sorted({value for item in entries for value in facet_values(item, field)})
                  for key, field in FACETS.values()}
        filters = filters or {}
        entries = [item for item in entries if matches_search(item, q) and
                   all(not filters.get(key) or set(filters[key]).intersection(facet_values(item, field))
                       for key, (_, field) in FACETS.items())]
        total = len(entries)
        pages = max(1, (total + page_size - 1) // page_size)
        page = min(page, pages)
        return {'items': entries[(page - 1) * page_size:page * page_size], 'page': page,
                'pages': pages, 'total': total, 'facets': facets}

    def image_search_results(self, matches, limit=48):
        """Project ranked matches only after rechecking each matched image.

        Search indices contain private images and may outlive an approval edit.
        A public image elsewhere on the same record does not authorize the
        matched image. Never return index counts, scores, paths or raw IDs.
        """
        matches = matches if isinstance(matches, list) else []
        candidates = [(match.get('record_id'), match.get('image_path')) for match in matches
                      if isinstance(match, dict) and isinstance(match.get('record_id'), str)
                      and isinstance(match.get('image_path'), str)]
        requested = {record_id for record_id, _ in candidates}
        records = {}
        with self.store.connection() as conn:
            # The approval predicate bounds parsing to customer-visible records.
            # Re-read after the slower inference, not from an index snapshot.
            rows = conn.execute('''SELECT r.id,r.content,pc.product_code FROM admin_records AS r
                LEFT JOIN admin_product_codes AS pc ON pc.record_id=r.id
                WHERE r.archived=0 AND json_extract(r.content,'$.kind')='package'
                  AND EXISTS (SELECT 1 FROM json_each(r.content,'$.images') AS image
                              WHERE json_extract(image.value,'$.clientVisible')=1
                                AND json_type(image.value,'$.clientVisible')='true')''')
            for row in rows:
                if row['id'] in requested:
                    record = json.loads(row['content'])
                    paths = self.approved_images(record)
                    if paths:
                        records[row['id']] = (record, row['product_code'], paths)
        entries, mappings, seen = [], [], set()
        for record_id, matched_path in candidates:
            if record_id in seen or record_id not in records:
                continue
            record, product_code, paths = records[record_id]
            if matched_path not in paths:
                continue
            seen.add(record_id)
            ordered_paths = [matched_path, *(path for path in paths if path != matched_path)]
            images = []
            for path in ordered_paths:
                token = self.opaque('image', record_id, path) + '.jpg'
                mappings.append((token, record_id, path))
                images.append({'url': '/client-media/' + token})
            entries.append({'id': self.opaque('record', record_id),
                            **project_record(record, product_code), 'images': images})
            if len(entries) >= max(1, min(48, limit)):
                break
        if mappings:
            with self.store.connection(True) as conn:
                conn.executemany('INSERT OR IGNORE INTO client_media_map VALUES(?,?,?)', mappings)
        facets = {key: sorted({value for item in entries for value in facet_values(item, field)})
                  for key, field in FACETS.values()}
        return {'items': entries, 'page': 1, 'pages': 1, 'total': len(entries), 'facets': facets}

    def media(self, token):
        # Optional image dependencies must not prevent employee login/startup.
        try:
            from PIL import Image, ImageOps, UnidentifiedImageError
        except ImportError:
            return None
        if not self.TOKEN_RE.fullmatch(token):
            return None
        with self.store.connection() as conn:
            row = conn.execute('''SELECT m.image_path,r.content FROM client_media_map AS m
                JOIN admin_records AS r ON r.id=m.record_id
                WHERE m.token=? AND r.archived=0''', (token,)).fetchone()
        if not row or row['image_path'] not in self.approved_images(json.loads(row['content'])):
            return None
        source = self.source(row['image_path'])
        if source is None:
            return None
        stat = source.stat()
        fingerprint = hashlib.sha256(f'{stat.st_size}:{stat.st_mtime_ns}'.encode()).hexdigest()[:20]
        target = self.cache / (token[:-4] + '-' + fingerprint + '.jpg')
        if target.is_file():
            return target
        if not self.waiters.acquire(blocking=False):
            raise ClientMediaBusy()
        locked = False
        temporary = None
        try:
            locked = self.gate.acquire(timeout=45)
            if not locked:
                raise ClientMediaBusy()
            if target.is_file():
                return target
            with Image.open(source) as original:
                if original.width * original.height > 24_000_000 or original.width < 1 or original.height < 1:
                    return None
                original.draft('RGB', (1600, 1600))
                original.thumbnail((1600, 1600))
                rendered = ImageOps.exif_transpose(original).convert('RGB')
                # A fresh image has none of the original EXIF, comments, profiles
                # or PNG text chunks, regardless of the original file format.
                sanitized = Image.new('RGB', rendered.size, 'white')
                sanitized.paste(rendered)
                temporary = target.with_suffix('.' + secrets.token_hex(6) + '.tmp')
                sanitized.save(temporary, format='JPEG', quality=88, optimize=True)
                temporary.chmod(0o600)
                os.replace(temporary, target)
            return target
        except (OSError, ValueError, UnidentifiedImageError, Image.DecompressionBombError):
            return None
        finally:
            if temporary is not None:
                temporary.unlink(missing_ok=True)
            if locked:
                self.gate.release()
            self.waiters.release()
