"""Transactional administrative content and account store.

Original catalog evidence is retained separately from editable content. No schema
changes are made to the legacy samples/plans tables. Password material is never
returned by the read, audit, or export APIs.
"""
from contextlib import contextmanager
from copy import deepcopy
from datetime import datetime, timezone
from decimal import Decimal
import hashlib
import hmac
import json
import math
from pathlib import Path
import re
import secrets
import sqlite3
import unicodedata


class AdminError(ValueError):
    def __init__(self, message, status=400):
        super().__init__(message)
        self.status = status


class ConflictError(AdminError):
    def __init__(self, message='资料已被其他人修改，请刷新后重试'):
        super().__init__(message, 409)


DEFAULT_PROCESS_STANDARDS = [
    {'id': key, 'name': name, 'englishName': en, 'price': None, 'unit': unit, 'moq': '', 'leadTime': ''}
    for key,name,en,unit in [
        ('silk','丝印','Screen printing','colour'), ('foil','烫金 / 烫银','Gold / silver foil','colour'),
        ('injection','注塑色','Moulded colour','unit'), ('spray','喷涂','Spray coating','colour'),
        ('frost','蒙砂','Frosting','unit'), ('bodyPlate','电镀瓶身','Body plating','unit'),
        ('capPlate','电镀盖子','Cap plating','unit'), ('other','其他工艺','Other finish','unit')]]

DEFAULT_SETTINGS = {
    'brandName': '源泽', 'englishName': 'YUANZE PACKAGING',
    'companyName': '广州源泽药业有限公司', 'siteTitle': '源泽包材库 · 内部选型',
    'catalogTitle': '包材选型库',
    'catalogSubtitle': '从原始询价资料中查找包材，保留图片、报价条件与来源。',
    'footerNote': '资料来自公司提供的询价记录表', 'announcement': '',
    'processReference': '', 'processStandards': DEFAULT_PROCESS_STANDARDS, 'showBusinessDemo': True,
}
DEFAULT_TAXONOMY = {
    'categories': ['瓶', '罐', '软管', '泵头', '盖子', '滴管', '彩盒', '套装', '其他'],
    'materials': ['玻璃', 'PET', 'PETG', 'PE', 'HDPE', 'PP', 'PMMA', 'AS', '铝', '纸'],
    'bottleTypes': ['圆瓶', '方瓶', '异形瓶', '广口瓶', '真空瓶', '泡沫瓶', '喷雾瓶', '滴管瓶', '膏霜罐'],
    'uses': ['水剂', '乳液', '膏霜', '油剂', '凝胶', '粉体', '洗护'],
}
IMMUTABLE_RECORD_FIELDS = {'source', 'rawCells', 'provenance', 'formulaCachedValues'}
RAW_FIELDS = {
    'addressRaw', 'contactRaw', 'customLeadTimeRaw', 'customMoqRaw', 'customQuoteRaw',
    'customerRaw', 'dateOrNotesRaw', 'extra2Raw', 'extraRaw', 'leadTimeRaw', 'materialRaw',
    'moldFeeRaw', 'moqRaw', 'processRaw', 'quoteRaw', 'remarksRaw', 'requirementsRaw',
    'sampleFeeRaw', 'specificationRaw', 'supplierRaw', 'testPlanRaw',
}
TEXT_FIELDS = RAW_FIELDS | {
    'name', 'kind', 'category', 'bottleType', 'series', 'model', 'description',
    'quoteHeader', 'sourceNote', 'bareBottlePrice', 'stockStatus',
}
RECORD_FIELDS = TEXT_FIELDS | {'materials', 'uses', 'referenceUses', 'capacityMl', 'unitPrice', 'currency',
                              'validUntil', 'images', 'uncertainties', 'productDetails', 'bodyAreas'}
KINDS = {'package', 'uncertain', 'semi_finished', 'service', 'requirement',
         'source_page', 'process_rule'}
ROLES = {'admin', 'employee', 'client'}
SAMPLE_STATUSES = {'available', 'lent', 'consumed', 'sent'}
USERNAME_RE = re.compile(r'^[A-Za-z0-9][A-Za-z0-9_.@-]{2,79}$')
ID_RE = re.compile(r'^[A-Za-z0-9\u4e00-\u9fff][A-Za-z0-9\u4e00-\u9fff_. -]{0,119}$')
# Legacy identifiers that already exist may contain a slash. New records must
# still use ID_RE, so nothing new can be created with an unaddressable id.
LEGACY_ID_RE = re.compile(r'^[A-Za-z0-9\u4e00-\u9fff][A-Za-z0-9\u4e00-\u9fff_. /-]{0,119}$')
UPLOAD_RE = re.compile(r'^uploads/[a-f0-9]{16,64}\.(?:jpg|jpeg|png|webp)$')
RECORD_SELECT = '''SELECT r.*, pc.product_code AS product_code
                   FROM admin_records r
                   LEFT JOIN admin_product_codes pc ON pc.record_id=r.id'''


def now():
    return datetime.now(timezone.utc).isoformat(timespec='seconds')


def dumps(value):
    return json.dumps(value, ensure_ascii=False, separators=(',', ':'), allow_nan=False)


def text(value, limit=5000, required=False):
    if not isinstance(value, str):
        raise AdminError('文字字段格式不正确')
    value = value.strip()
    if len(value) > limit:
        raise AdminError(f'文字长度不能超过 {limit} 字')
    if '\x00' in value:
        raise AdminError('文字包含无效字符')
    if required and not value:
        raise AdminError('必填项不能为空')
    return value


def text_list(value, max_items=100):
    if not isinstance(value, list) or len(value) > max_items:
        raise AdminError('分类或标签必须为列表，且不能超过 100 项')
    return list(dict.fromkeys(text(x, 200, True) for x in value))


def process_standards(value):
    if not isinstance(value, list) or len(value) > 50:
        raise AdminError('工艺标准必须为列表，且不能超过 50 项')
    result, seen = [], set()
    for item in value:
        if not isinstance(item, dict) or set(item) - {'id','name','englishName','price','unit','moq','leadTime'}:
            raise AdminError('工艺标准格式不正确')
        rid = text(item.get('id',''), 80, True)
        if not re.fullmatch(r'[A-Za-z0-9_-]+', rid) or rid in seen:
            raise AdminError('工艺编号必须唯一且只含字母、数字、下划线或横线')
        seen.add(rid)
        unit = item.get('unit', 'unit')
        if unit not in ('unit','colour'):
            raise AdminError('费用单位须为每个或每色')
        result.append({'id':rid,'name':text(item.get('name',''),80,True),
                       'englishName':text(item.get('englishName',''),120),
                       'price':number(item.get('price'), '工艺价格'), 'unit':unit,
                       'moq':text(item.get('moq',''),200), 'leadTime':text(item.get('leadTime',''),200)})
    return result


def product_details(value):
    """Editable, ordered plain-text details; repeated labels retain tier quotes."""
    if not isinstance(value, list) or len(value) > 60:
        raise AdminError('产品细则必须为列表，且不能超过 60 项')
    result = []
    for index, item in enumerate(value, 1):
        if not isinstance(item, dict) or set(item) - {'label', 'value', 'sourceField', 'evidence'}:
            raise AdminError(f'第 {index} 项产品细则格式不正确')
        row = {
            'label': text(item.get('label', ''), 80, True),
            'value': text(item.get('value', ''), 2000),
            'sourceField': text(item.get('sourceField', ''), 80),
            'evidence': text(item.get('evidence', ''), 2000),
        }
        if row['sourceField'] and row['sourceField'] not in TEXT_FIELDS:
            raise AdminError(f'第 {index} 项产品细则的资料来源无效')
        if any(re.search(r'<\s*/?\s*[a-zA-Z][^>]*>|<!--|<!DOCTYPE|<\?', row[k], re.I)
               for k in ('label', 'value', 'evidence')):
            raise AdminError(f'第 {index} 项产品细则请填写纯文字，不可包含网页标签')
        result.append(row)
    return result


def number(value, label):
    if value in (None, ''):
        return None
    if isinstance(value, bool) or not isinstance(value, (float, int)) or not math.isfinite(value) or value < 0 or value > 1e12:
        raise AdminError(label + '必须是有效的非负数，未知时请留空')
    return value


def specification_override(previous, current):
    """A future explicit field edit may replace a reviewed SKU label, never its OCR."""
    if not previous:
        return None
    capacity_changed = previous.get('capacityMl') != current.get('capacityMl')
    raw_changed = (previous.get('specificationRaw') or '') != (current.get('specificationRaw') or '')
    if not capacity_changed and not raw_changed:
        return previous.get('specificationOverride')
    raw = (current.get('specificationRaw') or '').strip()
    capacity = current.get('capacityMl')
    if capacity_changed and raw_changed and raw and capacity is not None and capacity > 0:
        normalized = unicodedata.normalize('NFKC', raw)
        compound = re.search(r'\d\s*(?:ml|毫升|l|升)?\s*[-~～至–—/+×x]\s*\d', normalized, re.I)
        values = {float(value) * (1000 if unit.lower() in {'l', '升'} else 1)
                  for value, unit in re.findall(r'(\d+(?:\.\d+)?)\s*(ml|毫升|l(?![a-z])|升)', normalized, re.I)}
        if compound or len(values) != 1:
            raise AdminError('规格说明无法与容量（mL）直接核对；克重、复合或未确认规格请将容量留空')
        if not math.isclose(next(iter(values)), capacity, rel_tol=1e-9, abs_tol=1e-9):
            raise AdminError('规格说明与容量（mL）不一致，请核对后保存')
    # A raw-only edit must not inherit an old numeric value, and vice versa.
    if raw_changed and (raw or not capacity_changed):
        return {'label': raw or '规格待补充', 'sourceField': 'specificationRaw'}
    if capacity is not None and capacity > 0:
        value = format(Decimal(str(capacity)), 'f')
        label = (value.rstrip('0').rstrip('.') if '.' in value else value) + ' mL'
    else:
        label = '规格待补充'
    return {'label': label, 'sourceField': 'capacityMl'}


def checked_id(value):
    value = text(value, 120, True)
    if not ID_RE.fullmatch(value):
        raise AdminError('编号只能含文字、数字、空格、点、下划线和连字符')
    return value


def writable_id(c, value):
    """Allow the strict pattern for new records; existing rows keep their id."""
    value = text(value, 120, True)
    if ID_RE.fullmatch(value):
        return value
    if LEGACY_ID_RE.fullmatch(value) and c.execute('SELECT 1 FROM admin_records WHERE id=?', (value,)).fetchone():
        return value
    raise AdminError('编号只能含文字、数字、空格、点、下划线和连字符')


def expected_version(data, actual):
    supplied = data.get('version')
    if isinstance(supplied, bool) or not isinstance(supplied, int) or supplied != actual:
        raise ConflictError()


def public_user(row):
    if row is None:
        return None
    return {k: (bool(row[k]) if k == 'active' else row[k]) for k in
            ('username', 'name', 'role', 'active', 'version', 'auth_version', 'created', 'updated')}


class AdminStore:
    def __init__(self, state, private, legacy_auth, base_catalog):
        self.state = Path(state)
        self.private = Path(private)
        self.state.mkdir(parents=True, exist_ok=True)
        self.path = self.state / 'catalog.sqlite'
        self.base = deepcopy(base_catalog or {'meta': {}, 'records': []})
        self.trusted_images = {}
        self.image_scopes = {}
        for record in self.base.get('records', []):
            for image in record.get('images', []):
                path = image.get('path', '')
                if isinstance(path, str) and path.startswith('media/'):
                    resolved = (self.private / path).resolve()
                    if resolved.is_relative_to((self.private / 'media').resolve()):
                        self.trusted_images.setdefault(path, []).append(deepcopy(image))
        materials_images = self.private / 'materials-images-20260924.json'
        if materials_images.is_file():
            for image in json.loads(materials_images.read_text()):
                path = image.get('path', '')
                if isinstance(path, str) and path.startswith('media/'):
                    resolved = (self.private / path).resolve()
                    if resolved.is_relative_to((self.private / 'media').resolve()):
                        self.trusted_images.setdefault(path, []).append(deepcopy(image))
        # Curated image evidence is server-owned. A browser edit may change a
        # caption or role, but cannot promote a catalogue sheet into a product.
        image_manifest = self.private / 'product-image-manifest.json'
        if image_manifest.is_file():
            manifest = json.loads(image_manifest.read_text())
            for path, scope in manifest.get('scopes', {}).items():
                if scope in {'single_product', 'same_style_variants', 'source_page', 'unresolved'}:
                    self.image_scopes[path] = scope
            for image in manifest.get('images', []):
                path = image.get('path', '')
                if isinstance(path, str) and path.startswith('media/'):
                    resolved = (self.private / path).resolve()
                    if resolved.is_relative_to((self.private / 'media').resolve()):
                        self.trusted_images.setdefault(path, []).append(deepcopy(image))
        self._initialize(legacy_auth or {})

    @contextmanager
    def connection(self, write=False):
        c = sqlite3.connect(self.path, timeout=20)
        c.row_factory = sqlite3.Row
        c.execute('PRAGMA foreign_keys=ON')
        try:
            if write:
                c.execute('BEGIN IMMEDIATE')
            yield c
            c.commit()
        except Exception:
            c.rollback()
            raise
        finally:
            c.close()

    def _initialize(self, legacy):
        with self.connection() as c:
            c.executescript('''
                PRAGMA journal_mode=WAL;
                CREATE TABLE IF NOT EXISTS admin_records (
                    id TEXT PRIMARY KEY, content TEXT NOT NULL, original TEXT NOT NULL,
                    version INTEGER NOT NULL, archived INTEGER NOT NULL DEFAULT 0,
                    created TEXT NOT NULL, updated TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS admin_product_codes (
                    record_id TEXT PRIMARY KEY REFERENCES admin_records(id),
                    number INTEGER NOT NULL UNIQUE CHECK(number BETWEEN 1 AND 999999),
                    product_code TEXT NOT NULL UNIQUE
                        CHECK(product_code=printf('YZ-BC-%06d',number)),
                    created TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS admin_product_code_sequence (
                    id INTEGER PRIMARY KEY CHECK(id=1),
                    next_number INTEGER NOT NULL CHECK(next_number BETWEEN 1 AND 1000000));
                CREATE TRIGGER IF NOT EXISTS admin_product_codes_immutable
                    BEFORE UPDATE OF record_id,number,product_code ON admin_product_codes
                    WHEN NEW.record_id != OLD.record_id OR NEW.number != OLD.number
                         OR NEW.product_code != OLD.product_code
                    BEGIN SELECT RAISE(ABORT,'Product codes are immutable'); END;
                CREATE TRIGGER IF NOT EXISTS admin_product_codes_no_delete
                    BEFORE DELETE ON admin_product_codes
                    BEGIN SELECT RAISE(ABORT,'Product codes cannot be deleted'); END;
                CREATE TABLE IF NOT EXISTS admin_users (
                    username TEXT PRIMARY KEY, name TEXT NOT NULL, role TEXT NOT NULL,
                    active INTEGER NOT NULL, salt TEXT NOT NULL, hash TEXT NOT NULL,
                    iterations INTEGER NOT NULL, version INTEGER NOT NULL,
                    auth_version INTEGER NOT NULL, created TEXT NOT NULL, updated TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS admin_config (
                    resource TEXT PRIMARY KEY, content TEXT NOT NULL, version INTEGER NOT NULL);
                CREATE TABLE IF NOT EXISTS admin_audit (
                    id INTEGER PRIMARY KEY AUTOINCREMENT, resource TEXT NOT NULL,
                    entity_id TEXT NOT NULL, action TEXT NOT NULL, actor TEXT NOT NULL,
                    before_json TEXT, after_json TEXT, created TEXT NOT NULL);
                CREATE INDEX IF NOT EXISTS admin_audit_entity ON admin_audit(resource,entity_id,id);
                CREATE TABLE IF NOT EXISTS admin_entity_meta (
                    resource TEXT NOT NULL, entity_id TEXT NOT NULL,
                    version INTEGER NOT NULL DEFAULT 1, archived INTEGER NOT NULL DEFAULT 0,
                    PRIMARY KEY(resource,entity_id));
                CREATE TABLE IF NOT EXISTS admin_uploads (
                    path TEXT PRIMARY KEY, actor TEXT NOT NULL, created TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS admin_migrations (name TEXT PRIMARY KEY, created TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS preferences (username TEXT PRIMARY KEY, content TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS plans (id TEXT PRIMARY KEY, username TEXT NOT NULL, title TEXT NOT NULL, note TEXT NOT NULL, snapshot TEXT NOT NULL, created TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS samples (id TEXT PRIMARY KEY, record_id TEXT NOT NULL, location TEXT NOT NULL, status TEXT NOT NULL, borrower TEXT NOT NULL DEFAULT '', due TEXT NOT NULL DEFAULT '', condition TEXT NOT NULL, updated TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS movements (id INTEGER PRIMARY KEY, sample_id TEXT NOT NULL REFERENCES samples(id), action TEXT NOT NULL, actor TEXT NOT NULL, details TEXT NOT NULL, created TEXT NOT NULL);
            ''')
        with self.connection(True) as c:
            if not c.execute('SELECT 1 FROM admin_migrations WHERE name=?', ('catalog-v1',)).fetchone():
                for r in self.base.get('records', []):
                    original = dumps(r)
                    c.execute('INSERT INTO admin_records VALUES(?,?,?,?,?,?,?)',
                              (r['id'], original, original, 1, 0, now(), now()))
                c.execute('INSERT INTO admin_migrations VALUES(?,?)', ('catalog-v1', now()))
            self.product_code_migration = self._backfill_product_codes(c)
            if legacy and not c.execute('SELECT 1 FROM admin_migrations WHERE name=?', ('legacy-account-v1',)).fetchone():
                self._seed_user(c, legacy, 'employee')
                c.execute('INSERT INTO admin_migrations VALUES(?,?)', ('legacy-account-v1', now()))
            bootstrap = self.state / 'admin-bootstrap.json'
            if bootstrap.exists() and not c.execute('SELECT 1 FROM admin_migrations WHERE name=?', ('admin-bootstrap-v1',)).fetchone():
                value = json.loads(bootstrap.read_text())
                if value.get('username') == legacy.get('username'):
                    raise AdminError('管理员必须使用独立账号')
                self._seed_user(c, value, 'admin')
                c.execute('INSERT INTO admin_migrations VALUES(?,?)', ('admin-bootstrap-v1', now()))
            for resource, value in [('settings', DEFAULT_SETTINGS), ('taxonomy', DEFAULT_TAXONOMY)]:
                c.execute('INSERT OR IGNORE INTO admin_config VALUES(?,?,?)', (resource, dumps(value), 1))

    def _allocate_product_codes(self, c, record_ids):
        """Called only under BEGIN IMMEDIATE; numbering rolls back with the write."""
        if not record_ids:
            return
        start = c.execute('SELECT next_number FROM admin_product_code_sequence WHERE id=1').fetchone()[0]
        if start + len(record_ids) > 1000000:
            raise AdminError('六位产品编号已用完，请联系管理员扩展编号范围')
        timestamp = now()
        c.executemany('INSERT INTO admin_product_codes(record_id,number,product_code,created) VALUES(?,?,?,?)',
                      ((rid, start + offset, f'YZ-BC-{start + offset:06d}', timestamp)
                       for offset, rid in enumerate(record_ids)))
        c.execute('UPDATE admin_product_code_sequence SET next_number=? WHERE id=1',
                  (start + len(record_ids),))

    def _backfill_product_codes(self, c):
        # An independent mapping leaves content, original evidence, business
        # versions, timestamps, snapshots and audit history byte-for-byte intact.
        c.execute('''INSERT OR IGNORE INTO admin_product_code_sequence(id,next_number)
                     SELECT 1,COALESCE(MAX(number),0)+1 FROM admin_product_codes''')
        missing = []
        for row in c.execute('''SELECT r.id,r.content FROM admin_records r
                                LEFT JOIN admin_product_codes pc ON pc.record_id=r.id
                                WHERE pc.record_id IS NULL ORDER BY r.rowid'''):
            if json.loads(row['content']).get('kind') == 'package':
                missing.append(row['id'])
        self._allocate_product_codes(c, missing)
        return {'assigned': len(missing),
                'total': c.execute('SELECT COUNT(*) FROM admin_product_codes').fetchone()[0],
                'nextNumber': c.execute('SELECT next_number FROM admin_product_code_sequence WHERE id=1').fetchone()[0]}

    def _ensure_product_code(self, c, record_id, kind):
        if kind == 'package' and not c.execute('SELECT 1 FROM admin_product_codes WHERE record_id=?', (record_id,)).fetchone():
            self._allocate_product_codes(c, [record_id])

    def _check_product_code(self, data, previous):
        current = (previous or {}).get('productCode')
        # Nested record and outer transport fields are checked independently so
        # a conflicting outer value cannot be silently discarded.
        for values in (data, data.get('record', {})):
            if not isinstance(values, dict) or 'productCode' not in values:
                continue
            value = values['productCode']
            if value != current and not (current is None and value == ''):
                raise AdminError('产品编号由系统分配且不能修改；更新时请保留原编号或省略该列')

    def _seed_user(self, c, value, role):
        username = text(value.get('username', ''), 80, True)
        if not USERNAME_RE.fullmatch(username):
            raise AdminError('账号格式不正确')
        salt, digest, iterations = value.get('salt'), value.get('hash'), value.get('iterations', 600000)
        if (not isinstance(salt, str) or not re.fullmatch(r'[0-9a-fA-F]{16,128}', salt)
                or len(salt) % 2 or not isinstance(digest, str) or not re.fullmatch(r'[0-9a-fA-F]{64}', digest)
                or type(iterations) is not int or not 100000 <= iterations <= 2000000):
            raise AdminError('账号初始化资料无效')
        if c.execute('SELECT 1 FROM admin_users WHERE username=?', (username,)).fetchone():
            raise ConflictError('初始化账号已存在，未覆盖原账号')
        timestamp = now()
        c.execute('INSERT INTO admin_users VALUES(?,?,?,?,?,?,?,?,?,?,?)',
                  (username, text(value.get('name', '管理员' if role == 'admin' else '员工'), 100),
                   role, 1, salt, digest.lower(), iterations, 1, 1, timestamp, timestamp))

    def get_user(self, username):
        with self.connection() as c:
            return public_user(c.execute('SELECT * FROM admin_users WHERE username=?', (username,)).fetchone())

    def users(self):
        with self.connection() as c:
            return [public_user(r) for r in c.execute('SELECT * FROM admin_users ORDER BY username')]

    def authenticate(self, username, password):
        if not isinstance(username, str) or not isinstance(password, str) or len(password) > 300:
            return None
        with self.connection() as c:
            r = c.execute('SELECT * FROM admin_users WHERE username=?', (username,)).fetchone()
        # Perform password derivation for unknown accounts too.
        salt, iterations = (r['salt'], r['iterations']) if r else ('0' * 32, 600000)
        result = hashlib.pbkdf2_hmac('sha256', password.encode(), bytes.fromhex(salt), iterations).hex()
        if not r or not hmac.compare_digest(result, r['hash']) or not r['active'] or r['role'] not in ROLES:
            return None
        return public_user(r)

    def _actor(self, c, actor):
        row = c.execute('SELECT role,active FROM admin_users WHERE username=?', (actor,)).fetchone()
        if not row or not row['active'] or row['role'] != 'admin':
            raise AdminError('仅管理员可以修改资料', 403)

    def _record(self, row):
        if not row:
            return None
        content = json.loads(row['content'])
        return {**content, 'productCode': row['product_code'],
                'version': row['version'], 'archived': bool(row['archived']),
                'created': row['created'], 'updated': row['updated']}

    def catalog(self, include_archived=False):
        with self.connection() as c:
            where = '' if include_archived else ' WHERE r.archived=0'
            records = [self._record(r) for r in c.execute(RECORD_SELECT + where + ' ORDER BY r.rowid')]
            settings = self._config(c, 'settings')
            taxonomy = self._config(c, 'taxonomy')
        meta = deepcopy(self.base.get('meta', {}))
        meta['recordCount'] = len(records)
        meta['kindCounts'] = {k: sum(r.get('kind') == k for r in records) for k in KINDS}
        return {'meta': meta, 'records': records, 'settings': settings, 'taxonomy': taxonomy}

    def _config(self, c, resource):
        r = c.execute('SELECT * FROM admin_config WHERE resource=?', (resource,)).fetchone()
        value = json.loads(r['content'])
        if resource == 'settings':
            value.setdefault('processStandards', deepcopy(DEFAULT_PROCESS_STANDARDS))
        return {**value, 'version': r['version']}

    def _entity(self, c, resource, row):
        if not row:
            return None
        value = dict(row)
        meta = c.execute('SELECT version,archived FROM admin_entity_meta WHERE resource=? AND entity_id=?',
                         (resource, value['id'])).fetchone()
        value['version'], value['archived'] = (meta['version'], bool(meta['archived'])) if meta else (1, False)
        if resource == 'plans':
            value['snapshot'] = json.loads(value['snapshot'])
        return value

    def read_admin(self, resource, id=None, limit=1000):
        with self.connection() as c:
            if resource == 'records':
                if id is not None:
                    row = self._record(c.execute(RECORD_SELECT + ' WHERE r.id=?', (id,)).fetchone())
                    if not row:
                        raise AdminError('记录不存在', 404)
                    return row
                return [self._record(r) for r in c.execute(RECORD_SELECT + ' ORDER BY r.rowid DESC')]
            if resource == 'users':
                return [public_user(r) for r in c.execute('SELECT * FROM admin_users ORDER BY username')]
            if resource in ('settings', 'taxonomy'):
                return self._config(c, resource)
            if resource in ('samples', 'plans'):
                return [self._entity(c, resource, r) for r in c.execute('SELECT * FROM ' + resource + ' ORDER BY rowid DESC')]
            if resource == 'audit':
                sql = 'SELECT * FROM admin_audit'
                args = ()
                if id is not None:
                    sql += ' WHERE entity_id=?'
                    args = (id,)
                tail = ' ORDER BY id DESC'
                if limit is not None:
                    tail += ' LIMIT ?'
                    args = (*args, min(1000, max(1, int(limit))))
                rows = [dict(r) for r in c.execute(sql + tail, args)]
                for r in rows:
                    r['before'] = json.loads(r.pop('before_json'))
                    r['after'] = json.loads(r.pop('after_json'))
                return rows
        raise AdminError('管理项目不存在', 404)

    def export(self):
        with self.connection() as c:
            originals = {r['id']: json.loads(r['original']) for r in c.execute('SELECT id,original FROM admin_records')}
            movements = [dict(r) for r in c.execute('SELECT * FROM movements ORDER BY id')]
        return {'exportedAt': now(), 'schemaVersion': 1,
                **{r: self.read_admin(r, limit=None) for r in ('records', 'users', 'settings', 'taxonomy', 'samples', 'plans', 'audit')},
                'originalRecords': originals, 'movements': movements}

    def write_export(self, stream):
        """Write a complete, consistent export one record at a time.

        Full before/after image history must not be materialized alongside the
        entire catalogue and a second, encoded JSON copy on the small server.
        """
        def emit(value):
            stream.write(dumps(value).encode('utf-8'))

        def array(values):
            stream.write(b'[')
            for n, value in enumerate(values):
                if n:
                    stream.write(b',')
                emit(value)
            stream.write(b']')

        with self.connection() as c:
            c.execute('BEGIN')
            stream.write(b'{"exportedAt":')
            emit(now())
            stream.write(b',"schemaVersion":1,"records":')
            array(self._record(r) for r in c.execute(RECORD_SELECT + ' ORDER BY r.rowid DESC'))
            stream.write(b',"users":')
            array(public_user(r) for r in c.execute('SELECT * FROM admin_users ORDER BY username'))
            for resource in ('settings', 'taxonomy'):
                stream.write(b','); emit(resource); stream.write(b':')
                emit(self._config(c, resource))
            for resource in ('samples', 'plans'):
                stream.write(b','); emit(resource); stream.write(b':')
                array(self._entity(c, resource, row) for row in c.execute('SELECT * FROM ' + resource + ' ORDER BY rowid DESC'))
            stream.write(b',"audit":')

            def audit():
                for row in c.execute('SELECT * FROM admin_audit ORDER BY id DESC'):
                    item = dict(row)
                    item['before'] = json.loads(item.pop('before_json'))
                    item['after'] = json.loads(item.pop('after_json'))
                    yield item

            array(audit())
            stream.write(b',"originalRecords":{')
            for n, row in enumerate(c.execute('SELECT id,original FROM admin_records')):
                if n:
                    stream.write(b',')
                emit(row['id']); stream.write(b':')
                stream.write(row['original'].encode('utf-8'))
            stream.write(b'},"movements":')
            array(dict(row) for row in c.execute('SELECT * FROM movements ORDER BY id'))
            stream.write(b'}')

    def _audit(self, c, resource, entity_id, action, actor, before, after):
        c.execute('INSERT INTO admin_audit(resource,entity_id,action,actor,before_json,after_json,created) VALUES(?,?,?,?,?,?,?)',
                  (resource, entity_id, action, actor, dumps(before), dumps(after), now()))

    def register_upload(self, path, actor):
        if not isinstance(path, str) or not UPLOAD_RE.fullmatch(path):
            raise AdminError('图片路径无效')
        target = (self.state / path).resolve()
        if not target.is_relative_to((self.state / 'uploads').resolve()) or not target.is_file():
            raise AdminError('图片尚未上传完成')
        with self.connection(True) as c:
            self._actor(c, actor)
            c.execute('INSERT OR IGNORE INTO admin_uploads VALUES(?,?,?)', (path, actor, now()))
            self._audit(c, 'uploads', path, 'upload', actor, None, {'path': path})
        return {'path': path, 'role': 'product', 'mapping': 'admin-upload', 'missing': False,
                'imageScope': 'single_product'}

    def _images(self, c, images):
        if not isinstance(images, list) or len(images) > 30:
            raise AdminError('每个产品最多添加 30 张图片')
        result = []
        for item in images:
            if not isinstance(item, dict):
                raise AdminError('图片资料格式不正确')
            path = item.get('path')
            if not isinstance(path, str):
                raise AdminError('图片路径无效')
            originals = self.trusted_images.get(path)
            if originals is not None:
                # A source can legitimately use the same bitmap in inquiry and
                # supplier columns; retain each distinct provenance association.
                original = next((v for v in originals if all(v.get(k) == item.get(k)
                                for k in ('cell', 'sourceCell', 'imageId', 'mapping'))), originals[0])
                image = deepcopy(original)
            elif UPLOAD_RE.fullmatch(path) and c.execute('SELECT 1 FROM admin_uploads WHERE path=?', (path,)).fetchone():
                scope = item.get('imageScope', 'single_product')
                if scope not in {'single_product', 'same_style_variants', 'source_page', 'unresolved'}:
                    raise AdminError('图片范围无效')
                image = {'path': path, 'mapping': 'admin-upload', 'missing': False,
                         'imageScope': scope}
            else:
                raise AdminError('图片必须来自原始资料或已上传的图片')
            role = item.get('role', image.get('role', 'product'))
            # Preserve legacy image roles, but do not allow callers to alter evidence flags.
            if role not in {'supplier', 'inquiry', 'product', 'reference', 'uncertain', 'customer',
                            'floating-reference', 'other', 'test-plan'}:
                raise AdminError('图片用途无效')
            image['role'] = role
            image['caption'] = text(item.get('caption', ''), 500)
            if 'clientVisible' in item and type(item['clientVisible']) is not bool:
                raise AdminError('客户展示设置必须为布尔值')
            image['clientVisible'] = item.get('clientVisible', False)
            if path in self.image_scopes:
                image['imageScope'] = self.image_scopes[path]
            result.append(image)
        return result

    def _normalized_record(self, c, data, previous=None):
        candidate = data.get('record', data)
        if not isinstance(candidate, dict):
            raise AdminError('产品资料格式不正确')
        old = deepcopy(previous or {})
        self._check_product_code(data, previous)
        out = {k: v for k, v in old.items() if k not in {'productCode', 'version', 'archived', 'created', 'updated'}}
        for field in IMMUTABLE_RECORD_FIELDS:
            original = old.get(field)
            if not previous and field == 'source':
                original = {'workbook': '管理员录入', 'sheet': '', 'row': ''}
            if field in candidate and candidate[field] != original:
                raise AdminError('原始来源资料不可覆盖，请使用来源补充说明')
        if 'specificationOverride' in candidate and candidate['specificationOverride'] != old.get('specificationOverride'):
            raise AdminError('规格覆盖标记由服务器维护，请修改规格说明或容量')
        ignored = {'id', 'productCode', 'version', 'archived', 'created', 'updated', 'searchText', 'action', 'record', 'specificationOverride'} | IMMUTABLE_RECORD_FIELDS
        if set(candidate) - RECORD_FIELDS - ignored:
            raise AdminError('包含不支持的产品字段：' + ','.join(sorted(set(candidate) - RECORD_FIELDS - ignored)))
        for key in TEXT_FIELDS:
            if key in candidate:
                value = candidate[key]
                if value is None and key not in ('name', 'kind'):
                    value = ''
                out[key] = text(value, 10000 if key.endswith('Raw') or key == 'description' else 1000)
        if 'stockStatus' in candidate and out['stockStatus'] not in ('','yes','no','unknown'):
            raise AdminError('现货状态须为 yes、no 或 unknown')
        if not out.get('name'):
            raise AdminError('请填写产品名称')
        if out.setdefault('kind', 'package') not in KINDS:
            raise AdminError('记录类型无效')
        for key in ('materials', 'uses', 'uncertainties'):
            if key in candidate:
                out[key] = text_list(candidate[key])
        if 'referenceUses' in candidate:
            # Only this new field uses null as a reset-to-automatic operation.
            # Missing fields preserve the previous override; [] disables it.
            if candidate['referenceUses'] is None:
                out.pop('referenceUses', None)
            else:
                out['referenceUses'] = text_list(candidate['referenceUses'])
        if 'bodyAreas' in candidate:
            areas = candidate['bodyAreas']
            if not isinstance(areas, list) or len(areas) > 3 or any(
                    not isinstance(area, str) or area not in {'face', 'body', 'head'} for area in areas):
                raise AdminError('护理部位必须为面部、身体、头部的列表，且不能超过 3 项')
            out['bodyAreas'] = list(dict.fromkeys(areas))
        if 'productDetails' in candidate:
            out['productDetails'] = product_details(candidate['productDetails'])
        out.setdefault('productDetails', [])
        if previous and out['productDetails'] == old.get('productDetails', []):
            changed_patterns = [pattern for field,pattern in [
                ('materials',r'材质|材料'),('specificationRaw',r'规格|容量|净含量'),
                ('moqRaw',r'MOQ|起订|最小订购'),('leadTimeRaw',r'货期|交期|周期'),('uses',r'用途|通常用于')]
                if field in candidate and out.get(field) != old.get(field)]
            if changed_patterns:
                out['productDetails'] = [row for row in out['productDetails']
                    if not any(re.search(pattern,row.get('label',''),re.I) for pattern in changed_patterns)]
        for key in ('capacityMl', 'unitPrice'):
            if key in candidate:
                out[key] = number(candidate[key], '容量' if key == 'capacityMl' else '单价')
        if 'currency' in candidate:
            out['currency'] = None if candidate['currency'] in (None, '') else text(candidate['currency'], 20)
        if 'validUntil' in candidate:
            value = candidate['validUntil']
            if value not in (None, ''):
                try:
                    datetime.strptime(value, '%Y-%m-%d')
                except (TypeError, ValueError):
                    raise AdminError('报价有效期请使用 YYYY-MM-DD 格式')
            out['validUntil'] = value or None
        if 'images' in candidate:
            out['images'] = self._images(c, candidate['images'])
        out.setdefault('images', [])
        out.setdefault('source', {'workbook': '管理员录入', 'sheet': '', 'row': ''})
        for field in RAW_FIELDS:
            out.setdefault(field, '')
        out.setdefault('quoteHeader', '')
        out.setdefault('currency', None)
        out.setdefault('unitPrice', None)
        out.setdefault('validUntil', None)
        out.setdefault('uncertainties', [])
        out['searchText'] = ' '.join(str(out.get(key) or '') if not isinstance(out.get(key), list)
                                     else ' '.join(map(str, out[key])) for key in sorted(RECORD_FIELDS - {'images', 'productDetails', 'bodyAreas'}))
        out['searchText'] += ' ' + ' '.join(' '.join(item.get(key, '') for key in ('label', 'value', 'evidence'))
                                          for item in out['productDetails'])
        return out

    def _save_record(self, c, action, data, actor):
        candidate = data.get('record', data)
        if not isinstance(candidate, dict):
            raise AdminError('产品资料格式不正确')
        raw_id = data.get('id') or candidate.get('id')
        rid = writable_id(c, raw_id) if raw_id else ('YZ-NEW-' + secrets.token_hex(6).upper())
        row = c.execute(RECORD_SELECT + ' WHERE r.id=?', (rid,)).fetchone()
        before = self._record(row)
        expected_version(data, row['version'] if row else 0)
        self._check_product_code(data, before)
        if action != 'save' and not row:
            raise AdminError('记录不存在', 404)
        timestamp = now()
        if action == 'save':
            out = self._normalized_record(c, data, before)
            override = specification_override(before, out)
            if override is not None:
                out['specificationOverride'] = override
            out['id'] = rid
            archived = row['archived'] if row else 0
        elif action == 'images':
            if set(data) - {'id', 'version', 'images'} or 'images' not in data:
                raise AdminError('图片更新只能包含记录 ID、版本和图片')
            out = json.loads(row['content'])
            out['images'] = self._images(c, data['images'])
            archived = row['archived']
        elif action in ('archive', 'unarchive'):
            out = json.loads(row['content'])
            archived = int(action == 'archive')
        elif action == 'restore':
            revision = data.get('revision')
            if type(revision) is not int:
                raise AdminError('请选择有效的历史版本')
            old = c.execute('SELECT after_json FROM admin_audit WHERE id=? AND resource=? AND entity_id=?',
                            (revision, 'records', rid)).fetchone()
            if not old or not json.loads(old[0]):
                raise AdminError('历史版本不存在', 404)
            preserved = {k: v for k, v in before.items() if k in IMMUTABLE_RECORD_FIELDS or k == 'productCode'}
            historical = json.loads(old[0])
            # Only the trusted audit snapshot can restore this server-owned field.
            if 'specificationOverride' in historical:
                preserved['specificationOverride'] = deepcopy(historical['specificationOverride'])
            # Older history can predate numbering (or predate the record first
            # becoming a package). Its projected code never changes the mapping.
            historical.pop('productCode', None)
            out = self._normalized_record(c, {'record': historical}, preserved)
            out['id'] = rid
            archived = row['archived']
        else:
            raise AdminError('不支持的产品操作')
        version = (row['version'] if row else 0) + 1
        if row:
            c.execute('UPDATE admin_records SET content=?,version=?,archived=?,updated=? WHERE id=?',
                      (dumps(out), version, archived, timestamp, rid))
        else:
            c.execute('INSERT INTO admin_records VALUES(?,?,?,?,?,?,?)',
                      (rid, dumps(out), dumps(out), version, archived, timestamp, timestamp))
        self._ensure_product_code(c, rid, out.get('kind'))
        after = self._record(c.execute(RECORD_SELECT + ' WHERE r.id=?', (rid,)).fetchone())
        # Preserve the initial imported version as a selectable audit revision.
        if row and not c.execute('SELECT 1 FROM admin_audit WHERE resource=? AND entity_id=?', ('records', rid)).fetchone():
            self._audit(c, 'records', rid, 'initial', actor, None, before)
        self._audit(c, 'records', rid, action, actor, before, after)
        return after

    def _save_user(self, c, action, data, actor):
        if action != 'save':
            raise AdminError('账号请通过启用或停用操作管理')
        username = text(data.get('id') or data.get('username', ''), 80, True)
        if not USERNAME_RE.fullmatch(username):
            raise AdminError('账号需为 3–80 位英文字母、数字、点、下划线、@ 或连字符')
        row = c.execute('SELECT * FROM admin_users WHERE username=?', (username,)).fetchone()
        expected_version(data, row['version'] if row else 0)
        before = public_user(row)
        name = text(data.get('name', row['name'] if row else username), 100, True)
        role = data.get('role', row['role'] if row else 'employee')
        active = data.get('active', bool(row['active']) if row else True)
        if role not in ROLES or type(active) is not bool:
            raise AdminError('账号角色或启用状态无效')
        if row and row['role'] == 'admin' and row['active'] and (role != 'admin' or not active):
            if c.execute("SELECT count(*) FROM admin_users WHERE role='admin' AND active=1").fetchone()[0] <= 1:
                raise AdminError('至少保留一个启用的管理员账号')
        password = data.get('password', '')
        if not isinstance(password, str):
            raise AdminError('密码格式不正确')
        if password or not row:
            if not 12 <= len(password) <= 300 or password != password.strip():
                raise AdminError('新密码需要 12–300 位且首尾不能有空格')
            salt, iterations = secrets.token_hex(16), 600000
            digest = hashlib.pbkdf2_hmac('sha256', password.encode(), bytes.fromhex(salt), iterations).hex()
        else:
            salt, iterations, digest = row['salt'], row['iterations'], row['hash']
        version = (row['version'] if row else 0) + 1
        auth_version = (row['auth_version'] if row else 0) + int(not row or bool(password) or role != row['role'] or active != bool(row['active']))
        timestamp = now()
        c.execute('INSERT INTO admin_users VALUES(?,?,?,?,?,?,?,?,?,?,?) ON CONFLICT(username) DO UPDATE SET name=excluded.name,role=excluded.role,active=excluded.active,salt=excluded.salt,hash=excluded.hash,iterations=excluded.iterations,version=excluded.version,auth_version=excluded.auth_version,updated=excluded.updated',
                  (username, name, role, int(active), salt, digest, iterations, version, auth_version,
                   row['created'] if row else timestamp, timestamp))
        after = public_user(c.execute('SELECT * FROM admin_users WHERE username=?', (username,)).fetchone())
        self._audit(c, 'users', username, 'password_reset' if row and password else 'save', actor, before, after)
        return after

    def _save_config(self, c, resource, action, data, actor):
        if action != 'save':
            raise AdminError('不支持此设置操作')
        before = self._config(c, resource)
        expected_version(data, before['version'])
        value = data.get('value')
        if not isinstance(value, dict):
            raise AdminError('设置资料格式不正确')
        allowed = DEFAULT_SETTINGS if resource == 'settings' else DEFAULT_TAXONOMY
        if set(value) - set(allowed) - {'version'}:
            raise AdminError('设置包含不支持的字段')
        out = {k: v for k, v in before.items() if k != 'version'}
        for key, val in value.items():
            if key == 'version':
                continue
            if resource == 'taxonomy':
                out[key] = text_list(val)
            elif key == 'processStandards':
                out[key] = process_standards(val)
            elif key == 'showBusinessDemo':
                if type(val) is not bool:
                    raise AdminError('显示状态必须为是或否')
                out[key] = val
            else:
                out[key] = text(val, 20000 if key == 'processReference' else 2000)
                if key in ('companyName', 'siteTitle', 'catalogTitle') and not out[key]:
                    raise AdminError('公司名称、站点名称和展厅名称不能为空')
        version = before['version'] + 1
        c.execute('UPDATE admin_config SET content=?,version=? WHERE resource=?', (dumps(out), version, resource))
        after = {**out, 'version': version}
        self._audit(c, resource, resource, action, actor, before, after)
        return after

    def _save_entity(self, c, resource, action, data, actor):
        rid = text(data.get('id', ''), 300, True)
        row = c.execute('SELECT * FROM ' + resource + ' WHERE id=?', (rid,)).fetchone()
        if not row:
            rid = checked_id(rid)
        before = self._entity(c, resource, row)
        expected_version(data, before['version'] if row else 0)
        if not row and (resource == 'plans' or action != 'save'):
            raise AdminError('记录不存在', 404)
        archived = before['archived'] if row else False
        if action in ('archive', 'unarchive'):
            archived = action == 'archive'
        elif action == 'save' and resource == 'plans':
            for key in ('snapshot', 'username', 'created'):
                if key in data and data[key] != before[key]:
                    raise AdminError('选型方案保留原始产品快照，仅可修改标题和备注')
            c.execute('UPDATE plans SET title=?,note=? WHERE id=?',
                      (text(data.get('title', row['title']), 300, True), text(data.get('note', row['note']), 10000), rid))
        elif action == 'save' and resource == 'samples':
            out = {key: data.get(key, before.get(key, '') if before else '') for key in
                   ('record_id', 'location', 'status', 'borrower', 'due', 'condition')}
            if not out['status']:
                out['status'] = 'available'
            if not isinstance(out['record_id'], str) or not c.execute('SELECT 1 FROM admin_records WHERE id=?', (out['record_id'],)).fetchone():
                raise AdminError('关联产品不存在')
            for key in ('location', 'condition'):
                out[key] = text(out[key], 1000, True)
            if out['status'] not in SAMPLE_STATUSES:
                raise AdminError('样品状态无效')
            out['borrower'] = text(out['borrower'], 300)
            out['due'] = text(out['due'], 10)
            if out['status'] == 'lent':
                if not out['borrower']:
                    raise AdminError('借出样品需要填写借用人')
                try:
                    datetime.strptime(out['due'], '%Y-%m-%d')
                except ValueError:
                    raise AdminError('借出样品需要填写有效的预计归还日期')
            elif out['borrower'] or out['due']:
                raise AdminError('未借出样品不能保留借用人或归还日期')
            c.execute('INSERT INTO samples VALUES(?,?,?,?,?,?,?,?) ON CONFLICT(id) DO UPDATE SET record_id=excluded.record_id,location=excluded.location,status=excluded.status,borrower=excluded.borrower,due=excluded.due,condition=excluded.condition,updated=excluded.updated',
                      (rid, out['record_id'], out['location'], out['status'], out['borrower'], out['due'], out['condition'], now()))
        else:
            raise AdminError('不支持的管理操作')
        version = (before['version'] if before else 0) + 1
        c.execute('INSERT INTO admin_entity_meta VALUES(?,?,?,?) ON CONFLICT(resource,entity_id) DO UPDATE SET version=excluded.version,archived=excluded.archived',
                  (resource, rid, version, int(archived)))
        after = self._entity(c, resource, c.execute('SELECT * FROM ' + resource + ' WHERE id=?', (rid,)).fetchone())
        if resource == 'samples':
            c.execute('INSERT INTO movements(sample_id,action,actor,details,created) VALUES(?,?,?,?,?)',
                      (rid, 'admin_' + action, actor, dumps({'before': before, 'after': after}), now()))
        self._audit(c, resource, rid, action, actor, before, after)
        return after

    def mutate(self, resource, action, data, actor):
        if not isinstance(data, dict):
            raise AdminError('提交资料格式不正确')
        with self.connection(True) as c:
            self._actor(c, actor)
            if resource == 'records':
                if action == 'bulk':
                    return self._bulk_change(c, data, actor)
                return self._save_record(c, action, data, actor)
            if resource == 'users':
                return self._save_user(c, action, data, actor)
            if resource in ('settings', 'taxonomy'):
                return self._save_config(c, resource, action, data, actor)
            if resource in ('samples', 'plans'):
                return self._save_entity(c, resource, action, data, actor)
            raise AdminError('管理项目不存在', 404)

    def _bulk_change(self, c, data, actor):
        items, operation = data.get('items'), data.get('operation')
        if not isinstance(items, list) or not 1 <= len(items) <= 500:
            raise AdminError('每次批量操作需要 1–500 条记录')
        if operation not in ('save','archive','unarchive'):
            raise AdminError('批量操作无效')
        patch = data.get('patch', {})
        allowed = {'bareBottlePrice','materials','materialRaw','specificationRaw','capacityMl','moqRaw','leadTimeRaw','uses','referenceUses','stockStatus'}
        if not isinstance(patch, dict) or set(patch) - allowed or (operation == 'save' and not patch):
            raise AdminError('请选择需要修改的产品字段')
        seen, output = set(), []
        # All saves and their audit entries share one transaction. Any stale
        # version, absent record or invalid value rolls back the entire batch.
        for item in items:
            if not isinstance(item, dict) or set(item) != {'id','version'} or not isinstance(item['id'], str) or item['id'] in seen:
                raise AdminError('批量记录编号或版本无效')
            seen.add(item['id'])
            rid = writable_id(c, item['id'])
            row = c.execute(RECORD_SELECT + ' WHERE r.id=?', (rid,)).fetchone()
            if not row:
                raise AdminError('批量操作包含不存在的产品',404)
            before = self._record(row)
            change = deepcopy(patch)
            if operation == 'save':
                # Remove superseded extracted copies, while retaining immutable
                # rawCells, source evidence and the previous audit revision.
                patterns = []
                for field, pattern in [('materials',r'材质|材料'),('specificationRaw',r'规格|容量|净含量'),
                                       ('moqRaw',r'MOQ|起订|最小订购'),('leadTimeRaw',r'货期|交期|周期'),('uses',r'用途|通常用于')]:
                    if field in change:
                        patterns.append(pattern)
                if patterns:
                    change['productDetails'] = [d for d in before.get('productDetails',[])
                        if not any(re.search(p,d.get('label',''),re.I) for p in patterns)]
            output.append(self._save_record(c, operation, {'id':rid,'version':item['version'],'record':change}, actor))
        return {'items': output, 'count': len(output)}

    def _bulk_rows(self, rows):
        if not isinstance(rows, list) or not 1 <= len(rows) <= 5000:
            raise AdminError('每次导入需要 1–5000 条记录')
        if any(not isinstance(r, dict) for r in rows):
            raise AdminError('导入记录必须为对象列表')

    def bulk_preview(self, rows):
        self._bulk_rows(rows)
        clean_rows, errors, seen = [], [], set()
        with self.connection() as c:
            for index, data in enumerate(rows):
                try:
                    item = deepcopy(data)
                    candidate = item.get('record', item)
                    if not isinstance(candidate, dict):
                        raise AdminError('产品资料格式不正确')
                    rid = item.get('id') or candidate.get('id')
                    if rid:
                        rid = writable_id(c, rid)
                        if rid in seen:
                            raise AdminError('导入文件中编号重复')
                        seen.add(rid)
                    row = c.execute(RECORD_SELECT + ' WHERE r.id=?', (rid,)).fetchone() if rid else None
                    if 'version' not in item:
                        if 'version' in candidate:
                            item['version'] = candidate['version']
                        elif row:
                            # An update without the exported version cannot tell
                            # whether the file was produced before a later edit,
                            # so it is rejected instead of silently replacing
                            # newer content with an older row.
                            raise AdminError('更新已有记录必须填写版本号；请使用导出的文件或模板中的“版本”列')
                        else:
                            item['version'] = 0
                    expected_version(item, row['version'] if row else 0)
                    normalized = self._normalized_record(c, item, self._record(row))
                    # Validate the same specification constraints before import
                    # confirmation. Only the eventual save persists the marker.
                    specification_override(self._record(row), normalized)
                    # IDs and versions are frozen by the preview, so commit cannot
                    # silently turn a conflicting existing record into a new record.
                    rid = rid or ('YZ-NEW-' + secrets.token_hex(6).upper())
                    normalized['id'] = rid
                    normalized['productCode'] = row['product_code'] if row else None
                    # Preview normalizes full records. Preserve reset intent so
                    # the later save removes an existing override as requested.
                    if 'referenceUses' in candidate and candidate['referenceUses'] is None:
                        normalized['referenceUses'] = None
                    clean_rows.append({'id': rid, 'version': item['version'], 'record': normalized})
                except (AdminError, ValueError, TypeError) as exc:
                    errors.append({'row': index + 1, 'error': str(exc)})
        return {'rows': clean_rows, 'errors': errors, 'valid': not errors, 'count': len(rows),
                'createCount': sum(r['version'] == 0 for r in clean_rows),
                'updateCount': sum(r['version'] > 0 for r in clean_rows)}

    def bulk_save(self, rows, actor):
        self._bulk_rows(rows)
        with self.connection(True) as c:
            self._actor(c, actor)
            result, seen = [], set()
            for data in rows:
                candidate = data.get('record', data)
                if not isinstance(candidate, dict):
                    raise AdminError('产品资料格式不正确')
                rid = data.get('id') or candidate.get('id')
                if rid in seen and rid is not None:
                    raise AdminError('导入文件中编号重复')
                seen.add(rid)
                result.append(self._save_record(c, 'save', data, actor))
        return {'count': len(result), 'records': result}
