"""Common-use suggestions from explicit container structure, never source prose.

Missing referenceUses enables these suggestions. A maintained list overrides
them, including an empty list that disables suggestions for that record.
"""
import re
import unicodedata


def normalized(value):
    return unicodedata.normalize('NFKC', value).strip().casefold() if isinstance(value, str) else ''


CATEGORY_FAMILIES = {
    **dict.fromkeys(('', '待细分', '瓶', '瓶类', 'bottle', 'bottles'), 'bottle'),
    **dict.fromkeys(('软管', 'tube', 'tubes'), 'tube'),
    **dict.fromkeys(('罐', '罐类', '罐与广口盒', 'jar', 'jars'), 'jar'),
    **dict.fromkeys(('滴管与滴管瓶', '滴管', 'dropper', 'droppers'), 'dropper'),
}

STRUCTURE_RULES = (
    (('软管', 'tube', 'tubes'), 'tube', ('洁面', '护手霜', '身体乳')),
    (('滴管瓶', '精油滴管瓶', '精华滴管瓶', 'dropper bottle'), 'dropper', ('精华液', '精油')),
    (('真空瓶', '可替换真空瓶', 'airless bottle', 'airless'), 'bottle', ('精华液', '乳液', '面霜')),
    (('乳液瓶', 'lotion bottle'), 'bottle', ('乳液', '身体乳')),
    (('泡沫瓶', '慕斯瓶', 'foam bottle', 'foaming bottle', 'foam'), 'bottle', ('洁面', '洗手液')),
    (('喷雾瓶', 'spray bottle', 'spray'), 'bottle', ('爽肤水', '身体香氛')),
    (('膏霜罐', '广口膏霜罐', '广口罐', 'cream jar'), 'jar', ('面霜', '身体霜')),
    (('滚珠瓶', 'roll-on bottle', 'roller bottle', '香水瓶', 'perfume bottle'), 'bottle', ('香水',)),
)
BOTTLE_RULES = {alias: (family, values) for aliases, family, values in STRUCTURE_RULES for alias in aliases}
CATEGORY_RULES = {'tube': ('洁面', '护手霜', '身体乳'), 'jar': ('面霜', '身体霜')}
SPECIAL_TUBE_USES = frozenset(('唇彩', '唇部护理', '眼霜', '眼部精华', '口腔护理', '眉妆',
                               '睫毛产品', '美甲', '染发', '脱毛', '家居清洁', '洗衣液'))
SPECIAL_TUBE_PATTERNS = tuple(re.compile(pattern, re.I) for pattern in (
    r'口红|唇釉|唇泥|唇彩|\blip(?:stick|\s+gloss|\s+tint)\b',
    r'唇部护理|润唇|唇膏|唇油|\blip\s+(?:care|balm|oil|mask)\b',
    r'眼霜|\beye\s+cream\b', r'眼(?:部)?精华|\beye\s+serum\b',
    r'漱口水|牙膏|口腔护理|\b(?:mouthwash|toothpaste|oral\s+care)\b',
    r'眉粉|眉笔|染眉|眉胶|\b(?:eyebrow|brow)\s+(?:powder|pencil|gel)\b',
    r'睫毛|\b(?:mascara|eyelash)\b', r'指甲油|美甲|甲油胶|\bnail\s+(?:polish|gel|care)\b',
    r'染发|\bhair\s+(?:dye|color|colour)\b',
    r'脱毛|\bdepilatory\b|\bhair\s+removal\b',
    r'洗洁精|家居清洁|厨房清洁|\b(?:dishwashing\s+liquid|household\s+cleaner)\b',
    r'洗衣液|\blaundry\s+detergent\b',
))
USAGE_COLUMN = re.compile(r'^(?:用途|产品用途|适用用途|适用产品|应用产品|usage|purpose|application|uses|使用部位|适用部位|应用部位|bodyarea|applicationarea)$', re.I)
SHARED_MARKER = re.compile(r'图册整页|整页(?:参考|共用)|共用参考|共享参考|原页(?:共用|参考)|source[ -]page\s+reference', re.I)
NEGATIVE_BEFORE = re.compile(r'(?:不(?:适用|适合|用于|供|可(?:以)?(?:用|装|盛|灌)|能(?:用|装)|推荐|支持|建议)|避免用于|禁(?:止)?(?:用|装)|不得(?:用|装)|\bnot\s+(?:suitable\s+|intended\s+)?for\b|\bnot\s+(?:suitable|applicable)\b|\bdo\s+not\s+use\b)', re.I)
NEGATIVE_IMMEDIATE = re.compile(r'(?:而非|并非|非|不是|无用途为|\bnot\s+)\s*$', re.I)


def scoped_usage_sources(record):
    """Mirror the browser's product-only evidence boundary for the tube guard."""
    def source_text(value):
        return unicodedata.normalize('NFKC', value).strip() if isinstance(value, str) else ''

    values = []
    name = source_text(record.get('name'))
    if name and not SHARED_MARKER.search(name):
        values.append(name)
    uses = record.get('uses', [])
    values.extend(uses if isinstance(uses, list) else [uses])
    raw_cells = record.get('rawCells')
    for cells in (raw_cells, raw_cells.get('original') if isinstance(raw_cells, dict) else None):
        if not isinstance(cells, dict):
            continue
        for key, value in cells.items():
            if not USAGE_COLUMN.fullmatch(re.sub(r'[\s:_-]', '', normalized(key))):
                continue
            if isinstance(value, dict):
                if value.get('shared') or value.get('sharedPage') or value.get('scope') in ('page', 'source_page', 'catalog'):
                    continue
                value = value.get('value')
            value = source_text(value)
            if value and len(value) <= 500 and not SHARED_MARKER.search(value):
                values.append(value)
    for detail in record.get('productDetails', []) if isinstance(record.get('productDetails'), list) else []:
        if not isinstance(detail, dict) or (detail.get('sourceField') or '') not in ('', 'name', 'uses'):
            continue
        value = source_text(detail.get('value'))
        if (USAGE_COLUMN.fullmatch(re.sub(r'[\s:_-]', '', normalized(detail.get('label'))))
                and value and len(value) <= 500 and not SHARED_MARKER.search(value)):
            values.append(value)
    return [source_text(value) for value in values if source_text(value)]


def has_special_tube_use(record):
    # Positive, product-scoped eye/lip/etc. evidence prevents broad tube
    # suggestions. This guard never supplies or changes a container structure.
    for source in scoped_usage_sources(record):
        source = re.sub(r'(?:不仅(?:限于)?|不只(?:是)?|不限于|\bnot\s+only\b)', ' ', source, flags=re.I)
        for sentence in re.split(r'[；;。\n\r]+|但是|但|而是|\bbut\b', source, flags=re.I):
            negative_list = False
            for clause in re.split(r'[，,]+', sentence):
                clause = clause.strip()
                if not clause:
                    continue
                if re.match(r'^(?:不是|并非|非(?!标))', clause):
                    clause = '不适用于' + clause
                negative = bool(NEGATIVE_BEFORE.search(clause))
                positive = not negative and bool(re.search(r'(?:可以|可用|可装|适用|适合|用于|使用|专用|仅供|\bfor\b|\bonly\b)', clause, re.I))
                checked = '不适用于' + clause if negative_list and not positive else clause
                for pattern in SPECIAL_TUBE_PATTERNS:
                    for match in pattern.finditer(checked):
                        before, after = checked[:match.start()], checked[match.end():]
                        if (not NEGATIVE_BEFORE.search(before) and not NEGATIVE_IMMEDIATE.search(before)
                                and not re.match(r'^\s*[（(]?\s*(?:不适用|不适合|禁用|不可用)', after)):
                            return True
                if negative:
                    negative_list = True
                elif positive:
                    negative_list = False
    return False


def reference_uses(record):
    """Return separate suggestions; leave confirmed uses and body areas intact."""
    if not isinstance(record, dict) or record.get('kind', 'package') != 'package':
        return []
    maintained = record.get('uses', [])
    maintained = maintained if isinstance(maintained, list) else [maintained]
    confirmed = {value.strip() for value in maintained if isinstance(value, str)}
    def separate(values):
        return list(dict.fromkeys(value.strip() for value in values
                                 if isinstance(value, str) and value.strip() and value.strip() not in confirmed))
    if 'referenceUses' in record:
        values = record['referenceUses']
        if not isinstance(values, list):
            return []
        return separate(values)
    category, bottle_type = normalized(record.get('category')), normalized(record.get('bottleType'))
    family = CATEGORY_FAMILIES.get(category)
    if family is None:
        return []
    if bottle_type:
        rule = BOTTLE_RULES.get(bottle_type)
        if rule is None:
            return []
        rule_family, uses = rule
        # An absent category permits the explicit type to decide. A generic
        # bottle can contain a dropper assembly, but cannot become a jar/tube.
        if category not in ('', '待细分') and family != rule_family and not (family == 'bottle' and rule_family == 'dropper'):
            return []
        family = rule_family
    else:
        uses = CATEGORY_RULES.get(family, ())
    if family == 'tube' and (SPECIAL_TUBE_USES.intersection(confirmed) or has_special_tube_use(record)):
        return []
    return separate(uses)
