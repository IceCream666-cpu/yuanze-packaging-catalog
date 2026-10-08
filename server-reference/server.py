#!/usr/bin/env python3
"""Private reference catalog. Python 3 standard library; sits behind HTTPS proxy."""
import html
import io
import tempfile
import argparse, base64, hashlib, hmac, http.cookies, json, mimetypes, os, re, secrets, sqlite3, threading, time
from contextlib import contextmanager
from datetime import datetime, timezone
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
from pathlib import Path
from urllib.parse import urlsplit, unquote, parse_qs, quote
from image_search import ImageSearchService, SearchBusy, SearchUnavailable, MAX_REQUEST_BYTES
from admin_store import AdminStore, AdminError
from admin_images import ManagedImageSearch, UploadManager
from admin_imports import parse_import, template_csv, MAX_BODY_BYTES
from auth_sessions import SessionStore, SessionLimit
from client_catalog import ClientCatalog, ClientMediaBusy
from media_derivatives import ThumbnailCache, ThumbnailBusy
from catalog_pages import CatalogPages, CatalogBusy, search_options, internal_csv

SUPPORTED_ROLES = {'employee', 'admin', 'client'}
ROOT = Path(__file__).resolve().parent
STATE = Path(os.environ.get('YZ_STATE', str(ROOT / 'state')))
PRIVATE = ROOT / 'private'
PUBLIC = ROOT / 'public'
SESSION_STORE = None
CLIENT_CATALOG = None
ATTEMPTS = {}
ATTEMPT_WINDOW = 600
ATTEMPT_LIMIT = 10
SESSION_SECONDS = 28800
LOCK = threading.Lock()
CATALOG = {'meta': {}, 'records': []}
AUTH = {}
LOCAL = False
IMAGE_SEARCH = None
STORE = None
CLIENT_CATALOG = None
UPLOADS = None
THUMBNAILS = None
CATALOG_PAGES = None
IMPORTS = {}
IMPORT_GATE = threading.Lock()
CATALOG_RESPONSE_GATE = threading.Lock()
DEFAULT_CSP = "default-src 'self'; img-src 'self' data:; style-src 'self' 'unsafe-inline'; script-src 'self'; connect-src 'self'; frame-ancestors 'none'; base-uri 'self'; form-action 'self'"

def showroom_asset(relative):
    """Only deterministic build outputs may be served as customer company files."""
    if not isinstance(relative,str) or '\\' in relative or '..' in relative.split('/'):
        return None
    entrypoints={'index.html','preview.js','preview.css','company-content.js','product-posters.js'}
    if relative not in entrypoints and not re.fullmatch(r'assets/[A-Za-z0-9_./-]+\.(?:png|jpg|jpeg|webp|svg|pdf)',relative):
        return None
    directory=PUBLIC/'showroom'
    try:
        manifest=json.loads((directory/'bundle-manifest.json').read_text())
        if not isinstance(manifest,dict) or manifest.get('schema')!=1 or not isinstance(manifest.get('files'),dict) or relative not in manifest['files']:
            return None
    except (OSError,ValueError,TypeError):
        return None
    target=(directory/relative).resolve()
    return target if target.is_relative_to(directory.resolve()) and target.is_file() else None

class AuthStorageUnavailable(Exception):
    pass

def now(): return datetime.now(timezone.utc).isoformat(timespec='seconds')

@contextmanager
def db():
    # sqlite3's own context manager only commits or rolls back; the connection
    # must be closed explicitly, otherwise every request leaks a file handle.
    c = sqlite3.connect(STATE/'catalog.sqlite', timeout=15)
    c.row_factory=sqlite3.Row
    c.execute('PRAGMA foreign_keys=ON')
    try:
        with c:
            yield c
    finally:
        c.close()

def attempt_times(key):
    # Caller holds LOCK. Reads and prunes the rolling failure window.
    cutoff=time.time()-ATTEMPT_WINDOW
    return [stamp for stamp in ATTEMPTS.get(key,[]) if stamp>cutoff]

def register_failure(*keys):
    # Caller holds LOCK. A successful login only clears its own account key, so
    # one valid account cannot reset the failure count of another account or of
    # the source address it is attacking from.
    stamp=time.time()
    for key in keys:
        if not key[1]: continue
        items=attempt_times(key); items.append(stamp); ATTEMPTS[key]=items
    if len(ATTEMPTS)>4096:
        for key in [k for k in list(ATTEMPTS) if not attempt_times(k)]: ATTEMPTS.pop(key,None)

def login_retry_after(*keys):
    # Caller holds LOCK. Keep the existing abuse limits, expose their actual
    # remaining duration rather than presenting a lockout as a bad password.
    waits=[items[0]+ATTEMPT_WINDOW-time.time() for key in keys
           if len(items:=attempt_times(key))>=ATTEMPT_LIMIT]
    return max(1,int(max(waits))+1) if waits else 0

def active_ids(values):
    # Only the submitted identifiers are checked; the catalog is never scanned
    # in full just to validate a favorite, a plan or a sample link.
    wanted=list(dict.fromkeys(v for v in values if isinstance(v,str)))
    found=set()
    if not wanted: return found
    with db() as c:
        for start in range(0,len(wanted),400):
            chunk=wanted[start:start+400]
            marks=','.join('?'*len(chunk))
            found.update(row[0] for row in c.execute('SELECT id FROM admin_records WHERE archived=0 AND id IN ('+marks+')',chunk))
    return found

def initialize():
    global CATALOG, AUTH, IMAGE_SEARCH, STORE, UPLOADS, SESSION_STORE, CLIENT_CATALOG, THUMBNAILS, CATALOG_PAGES
    STATE.mkdir(parents=True, exist_ok=True)
    if (PRIVATE/'catalog.json').exists(): CATALOG=json.loads((PRIVATE/'catalog.json').read_text())
    AUTH=json.loads((STATE/'auth.json').read_text()) if (STATE/'auth.json').exists() else {}
    if not AUTH and not LOCAL: raise RuntimeError('Missing state/auth.json; refusing unauthenticated remote deployment')
    with db() as c:
        c.executescript('''PRAGMA journal_mode=WAL;
        CREATE TABLE IF NOT EXISTS preferences (username TEXT PRIMARY KEY, content TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS plans (id TEXT PRIMARY KEY, username TEXT NOT NULL, title TEXT NOT NULL, note TEXT NOT NULL, snapshot TEXT NOT NULL, created TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS samples (id TEXT PRIMARY KEY, record_id TEXT NOT NULL, location TEXT NOT NULL, status TEXT NOT NULL, borrower TEXT NOT NULL DEFAULT '', due TEXT NOT NULL DEFAULT '', condition TEXT NOT NULL, updated TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS movements (id INTEGER PRIMARY KEY, sample_id TEXT NOT NULL REFERENCES samples(id), action TEXT NOT NULL, actor TEXT NOT NULL, details TEXT NOT NULL, created TEXT NOT NULL);
        ''')
    if IMAGE_SEARCH is not None and hasattr(IMAGE_SEARCH,'close'):
        IMAGE_SEARCH.close()
    STORE = AdminStore(STATE, PRIVATE, AUTH, CATALOG)
    if CATALOG_PAGES is not None:CATALOG_PAGES.close()
    CATALOG_PAGES = CatalogPages(STORE, ROOT)
    CLIENT_CATALOG = ClientCatalog(STORE, STATE, PRIVATE)
    THUMBNAILS = ThumbnailCache(STATE)
    SESSION_STORE = SessionStore(STATE,
        employee_limit=int(os.environ.get('YZ_EMPLOYEE_SESSION_LIMIT','0')),
        admin_limit=int(os.environ.get('YZ_ADMIN_SESSION_LIMIT','20')))
    if LOCAL and not STORE.get_user('local-preview-admin'):
        salt=secrets.token_hex(16)
        with STORE.connection(True) as c:
            STORE._seed_user(c,{'username':'local-preview-admin','salt':salt,'hash':hashlib.pbkdf2_hmac('sha256',secrets.token_bytes(32),bytes.fromhex(salt),100000).hex(),'iterations':100000},'admin')
    # CATALOG is only the small immutable import seed. Keeping an additional
    # parsed snapshot of every database record here duplicates the live catalog.
    base = ImageSearchService(PRIVATE)
    UPLOADS = UploadManager(STATE, base.gate)
    IMAGE_SEARCH = ManagedImageSearch(base, STATE, PRIVATE, STORE.catalog, upload_manager=UPLOADS)

def clean(v, maxlen=300):
    if not isinstance(v, str): raise ValueError('请填写有效文字')
    return v.strip()[:maxlen]
def required(v, message):
    v=clean(v)
    if not v: raise ValueError(message)
    return v

def change_sample(sid, action, data, actor):
    with db() as c:
        c.execute('BEGIN IMMEDIATE')
        s=c.execute('SELECT * FROM samples WHERE id=?',(sid,)).fetchone()
        if not s: raise ValueError('样品不存在')
        if c.execute("SELECT 1 FROM admin_entity_meta WHERE resource='samples' AND entity_id=? AND archived=1",(sid,)).fetchone():raise ValueError('样品已归档，请先在后台恢复')
        location, status, borrower, due, condition=s['location'],s['status'],s['borrower'],s['due'],s['condition']
        if action=='lend':
            if status!='available': raise ValueError('该样品当前不可借出')
            borrower=required(data.get('borrower'), '请填写借用人')
            due=required(data.get('due'),'请填写预计归还日期')
            try: datetime.strptime(due,'%Y-%m-%d')
            except ValueError: raise ValueError('日期格式不正确')
            location='借用人保管';status='lent'
        elif action=='return':
            if status!='lent': raise ValueError('仅借出样品可以登记归还')
            location=required(data.get('location'),'请填写归还位置')
            condition=required(data.get('condition'),'请填写归还状态')
            status='available';borrower='';due=''
        elif action in ['consumed','sent']:
            if status not in ['available','lent']: raise ValueError('该样品已结束流转')
            required(data.get('note'),'请填写用途或去向')
            status=action;borrower='';due='';location='已耗用' if action=='consumed' else '已寄给客户'
        else: raise ValueError('未知操作')
        c.execute('UPDATE samples SET location=?,status=?,borrower=?,due=?,condition=?,updated=? WHERE id=?',(location,status,borrower,due,condition,now(),sid))
        c.execute('INSERT INTO movements(sample_id,action,actor,details,created) VALUES(?,?,?,?,?)',(sid,action,actor,json.dumps(data,ensure_ascii=False),now()))
        c.execute("INSERT INTO admin_entity_meta(resource,entity_id,version,archived) VALUES('samples',?,2,0) ON CONFLICT(resource,entity_id) DO UPDATE SET version=version+1",(sid,))

class Handler(BaseHTTPRequestHandler):
    server_version='YuanzeReference'
    protocol_version='HTTP/1.1'
    def setup(self):
        super().setup()
        self.connection.settimeout(30)
    def handle_one_request(self):
        self.request_id=secrets.token_hex(8)
        self.request_started=time.monotonic()
        self.auth_reason=None
        try:
            return super().handle_one_request()
        except AuthStorageUnavailable:
            return self.auth_storage_unavailable()
        except (BrokenPipeError,ConnectionResetError,TimeoutError):
            self.log_message('client_disconnected')
            self.close_connection=True
    def auth_storage_unavailable(self):
        self.auth_reason='storage_unavailable'
        return self.respond(503,{'error':'登录服务暂时繁忙，请稍后重试',
            'code':'AUTH_STORAGE_UNAVAILABLE'},extra={'Retry-After':'2'})
    def log_request(self,code='-',size='-'):
        # Server-generated IDs correlate frontend errors and service logs. Never
        # include query strings, headers, credentials, csrf or request bodies.
        event={'event':'http_request','request_id':self.request_id,
               'method':self.command,'path':urlsplit(self.path).path,'status':code,
               'elapsed_ms':round((time.monotonic()-self.request_started)*1000)}
        if self.auth_reason:event['auth_reason']=self.auth_reason
        print(json.dumps(event,ensure_ascii=False),flush=True)
    def log_message(self, fmt, *args):
        # BaseHTTPRequestHandler may pass untrusted request lines in fmt/args.
        # Log only a fixed diagnostic name, without interpolating those inputs.
        event='client_disconnected' if fmt=='client_disconnected' else 'http_protocol_error'
        print(json.dumps({'event':event,'request_id':getattr(self,'request_id','')}),flush=True)
    def respond(self, code, value, ctype='application/json; charset=utf-8', extra=None):
        body=json.dumps(value,ensure_ascii=False).encode() if ctype.startswith('application/json') else value
        self.response_headers(code,len(body),ctype,extra)
        if self.command!='HEAD': self.wfile.write(body)
    def response_headers(self,code,length,ctype,extra=None):
        self.send_response(code)
        # POST rejections can occur before the body is read. Never reuse that
        # upstream connection with unread credentials/body bytes on the socket.
        if self.command not in {'GET','HEAD'}:
            self.close_connection=True
            self.send_header('Connection','close')
        for k,v in {'Content-Type':ctype,'Content-Length':str(length),'Cache-Control':'no-store','X-Request-ID':self.request_id,'X-Content-Type-Options':'nosniff','X-Frame-Options':'DENY','Referrer-Policy':'no-referrer','Content-Security-Policy':DEFAULT_CSP,**(extra or {})}.items(): self.send_header(k,v)
        self.end_headers()
    def respond_export(self):
        if not CATALOG_RESPONSE_GATE.acquire(blocking=False):
            return self.respond(429,{'error':'目录资料正在加载，请稍后重试'},extra={'Retry-After':'2'})
        try:
            output=tempfile.TemporaryFile()
            try:
                STORE.write_export(output)
            except BaseException:
                output.close()
                raise
        finally:
            CATALOG_RESPONSE_GATE.release()
        # Release the catalogue gate before network output: a slow download
        # must not block employees' catalogue requests. The temporary file is
        # private and removed automatically on success or disconnect.
        with output:
            length=output.tell();output.seek(0)
            self.response_headers(200,length,'application/json; charset=utf-8',
                {'Content-Disposition':'attachment; filename="yuanze-admin-export.json"'})
            if self.command!='HEAD':
                while chunk:=output.read(65536):self.wfile.write(chunk)
    def respond_catalog(self, loader, extra=None):
        # Serialize one catalogue at a time to bound memory. Once serialized,
        # each slow download uses its own private spool, not the global gate.
        if not CATALOG_RESPONSE_GATE.acquire(blocking=False):
            return self.respond(429,{'error':'目录资料正在加载，请稍后重试'},extra={'Retry-After':'2'})
        try:
            output=tempfile.TemporaryFile()
            try:
                writer=io.TextIOWrapper(output,encoding='utf-8',write_through=True)
                try:json.dump(loader(),writer,ensure_ascii=False)
                finally:writer.detach()
            except BaseException:
                output.close()
                raise
        finally:
            CATALOG_RESPONSE_GATE.release()
        with output:
            length=output.tell();output.seek(0)
            self.response_headers(200,length,'application/json; charset=utf-8',extra)
            if self.command!='HEAD':
                while chunk:=output.read(65536):self.wfile.write(chunk)
    def session(self):
        try:
            return self.checked_session()
        except sqlite3.Error:
            # A locked/unavailable session or account DB is not a bad password
            # and must never clear the browser's still-valid session cookie.
            raise AuthStorageUnavailable() from None
    def checked_session(self):
        if LOCAL and self.client_address[0] in ['127.0.0.1','::1']: return {'username':'local-preview-admin','csrf':'local-preview','role':'admin','auth_version':1}
        try:
            cookie=http.cookies.SimpleCookie(self.headers.get('Cookie',''))
            token=cookie['yz_session'].value
        except (KeyError, http.cookies.CookieError):
            self.auth_reason='missing_session'
            return None
        snapshot,self.auth_reason=SESSION_STORE.get(token)
        if not snapshot:return None
        # Always recheck the current account version; password changes, account
        # removal and deactivation revoke persisted sessions immediately.
        user=STORE.get_user(snapshot['username'])
        if not user or not user.get('active') or user.get('auth_version')!=snapshot.get('auth_version') or user.get('role') not in SUPPORTED_ROLES:
            SESSION_STORE.delete(token)
            self.auth_reason='revoked_session'
            return None
        self.session_token=token
        return {**snapshot,'role':user['role']}
    def body(self, max_size=100000):
        size=int(self.headers.get('Content-Length','0'))
        if self.headers.get('Transfer-Encoding') or size<0 or size>max_size: raise ValueError('提交内容过大或格式不支持')
        value=json.loads(self.rfile.read(size) or b'{}')
        if not isinstance(value,dict): raise ValueError('提交格式错误')
        return value
    def valid_host(self):
        host=self.headers.get('Host','').split(':')[0]
        return not LOCAL or host in ['127.0.0.1','localhost']
    def valid_origin(self):
        origin=self.headers.get('Origin')
        if not origin: return False
        return urlsplit(origin).netloc==self.headers.get('Host')
    def do_HEAD(self): self.do_GET()
    def do_GET(self):
        if not self.valid_host(): return self.respond(403,{'error':'访问地址无效'})
        path=unquote(urlsplit(self.path).path)
        # Reject alternate spellings before route/role selection. Otherwise a
        # staff request such as /./admin.html or /x/../showroom/file could reach generic static
        # serving instead of the customer-only showroom boundary.
        if any(part in {'.','..'} for part in path.split('/')) or '//' in path or '\\' in path or '\x00' in path:
            return self.respond(404,{'error':'页面或文件不存在'})
        if path=='/healthz': return self.respond(200,{'status':'ok'})
        if path in ['/login','/login.html']:
            s=self.session()
            if s:
                code=parse_qs(urlsplit(self.path).query).get('code',[''])[0].upper()
                destination='/client' if s['role']=='client' else '/?code='+quote(code) if re.fullmatch(r'YZ-BC-[0-9]{6,}',code) else ('/admin' if s['role']=='admin' else '/')
                return self.respond(303,b'','text/plain',{'Location':destination})
            settings=STORE.read_admin('settings')
            page=(PUBLIC/'login.html').read_text().replace('登录 · 源泽包材库',html.escape('登录 · '+settings['siteTitle'])).replace('YUANZE · 源泽',html.escape(settings['englishName']+' · '+settings['brandName'])).replace('包材选型工作空间',html.escape(settings['catalogTitle']))
            return self.respond(200,page.encode(),'text/html; charset=utf-8')
        if path in ['/login.js','/api-client.js','/style.css','/i18n.js','/i18n.css']:
            return self.file(PUBLIC/('login.html' if path in ['/login','/login.html'] else path[1:]), PUBLIC)
        if path in ['/brand/yuanze-brand-guide.png', '/brand/yuanze-mark.svg']:
            return self.file(PUBLIC/path.lstrip('/'), PUBLIC)
        s=self.session()
        if not s:
            if path.startswith(('/api/','/media/','/uploads/','/client-media/','/showroom/')): return self.respond(401,{'error':'请先登录'})
            # Only a validated internal product code may survive the login step.
            code=parse_qs(urlsplit(self.path).query).get('code',[''])[0].upper()
            destination='/login?code='+quote(code) if path in ['/','/index.html','/catalog'] and re.fullmatch(r'YZ-BC-[0-9]{6,}',code) else '/login'
            return self.respond(303,b'','text/plain',{'Location':destination})
        customer_route=path in ['/client','/client.html','/client/products','/client.js','/client.css','/api/client/catalog'] or path.startswith(('/client-media/','/showroom/'))
        if s['role']=='client' or (s['role']=='admin' and customer_route):
            return self.client_get(path,s)
        if customer_route:return self.respond(403,{'error':'此页面仅供客户账号及管理员预览'})
        if path in ['/','/index.html'] and s['role']=='admin':
            # The shared company link opens each account's workspace. Explicit
            # product links and /catalog remain available for staff-view browsing.
            code=parse_qs(urlsplit(self.path).query).get('code',[''])[0].upper()
            if not re.fullmatch(r'YZ-BC-[0-9]{6,}',code):
                return self.respond(303,b'','text/plain',{'Location':'/admin'})
        if path=='/api/session': return self.respond(200,{'username':s['username'],'csrf':s['csrf'],'local':LOCAL,'role':s['role'],'catalogPaging':bool(CATALOG_PAGES and CATALOG_PAGES.enabled)})
        if path.startswith('/api/admin/'):
            if s['role']!='admin': return self.respond(403,{'error':'仅管理员可以维护资料'})
            return self.admin_get(path)
        if path in ['/admin','/admin.html','/admin/tools','/admin.js','/admin.css']:
            if s['role']!='admin': return self.respond(403,{'error':'仅管理员可以进入后台'})
            filename='index.html' if path in ['/admin','/admin.html'] else 'admin.html' if path=='/admin/tools' else path[1:]
            return self.file(PUBLIC/filename,PUBLIC)
        if path=='/api/catalog': return self.respond_catalog(STORE.catalog)
        if path in ['/api/catalog/page','/api/catalog/records','/api/catalog/export']:
            try:
                if path=='/api/catalog/records':
                    ids=parse_qs(urlsplit(self.path).query,max_num_fields=128).get('id',[])
                    if not ids or len(ids)>128 or any(len(value)>200 for value in ids):raise ValueError()
                    data=CATALOG_PAGES.request('records',ids=ids)
                else:
                    options=search_options(urlsplit(self.path).query,STORE,s['username'])
                    data=CATALOG_PAGES.request('export' if path.endswith('/export') else 'query',options=options)
                if path.endswith('/export'):
                    return self.respond(200,internal_csv(data['records']),'text/csv; charset=utf-8',{'Content-Disposition':'attachment; filename="yuanze-packaging.csv"'})
                return self.respond(200,data)
            except (ValueError,TypeError):return self.respond(400,{'error':'检索参数格式不正确'})
            except CatalogBusy:return self.respond(503,{'error':'目录索引正在准备，请稍后重试'},extra={'Retry-After':'2'})
        if path=='/api/image-search/status': return self.respond(200,IMAGE_SEARCH.status())
        if path=='/api/preferences':
            with db() as c: row=c.execute('SELECT content FROM preferences WHERE username=?',(s['username'],)).fetchone()
            return self.respond(200,json.loads(row[0]) if row else {'favorites':[]})
        if path=='/api/plans':
            rows=[x for x in STORE.read_admin('plans') if x['username']==s['username'] and not x.get('archived')]
            return self.respond(200,rows)
        if path=='/api/samples':
            with db() as c:
                rows=[x for x in STORE.read_admin('samples') if not x.get('archived')]
                events=[dict(x) for x in c.execute('SELECT * FROM movements ORDER BY id DESC LIMIT 300')]
            return self.respond(200,{'samples':rows,'events':events})
        history=re.fullmatch(r'/api/samples/([^/]+)/history',urlsplit(self.path).path)
        if history:
            sid=unquote(history[1])
            with db() as c:
                if not c.execute('SELECT 1 FROM samples WHERE id=?',(sid,)).fetchone(): return self.respond(404,{'error':'样品不存在'})
                events=[dict(x) for x in c.execute('SELECT * FROM movements WHERE sample_id=? ORDER BY id DESC',(sid,))]
            return self.respond(200,events)
        if path.startswith('/uploads/'):
            asset=UPLOADS.resolve(path.lstrip('/'))
            if asset is None:return self.respond(404,{'error':'图片不存在'})
            return self.file(asset,STATE/'uploads')
        if path.startswith('/media/'):
            return self.file(PRIVATE/'media'/path[len('/media/'):],PRIVATE/'media')
        return self.file(PUBLIC/('index.html' if path in ['/','/catalog'] else path.lstrip('/')),PUBLIC)
    def client_get(self,path,session):
        # Deny-by-default: customer credentials can never select employee APIs,
        # private original images, internal scripts, exports or business pages.
        if path in ['/','/index.html','/catalog']:
            return self.respond(303,b'','text/plain',{'Location':'/client'})
        if path=='/api/session':
            return self.respond(200,{'username':session['username'],'csrf':session['csrf'],'role':'client'})
        if path in ['/client','/client.html'] or path.startswith('/showroom/'):
            relative='index.html' if path in ['/client','/client.html'] else path[len('/showroom/'):]
            asset=showroom_asset(relative)
            if asset is None:return self.respond(404,{'error':'客户展示资料暂不可用'})
            extra={'Content-Security-Policy':DEFAULT_CSP+"; frame-src 'self'"} if relative=='index.html' else None
            return self.file(asset,PUBLIC/'showroom',extra)
        if path=='/client/products':
            return self.file(PUBLIC/'client.html',PUBLIC,{'X-Frame-Options':'SAMEORIGIN',
                'Content-Security-Policy':DEFAULT_CSP.replace("frame-ancestors 'none'","frame-ancestors 'self'")})
        if path in ['/client.js','/client.css']:
            return self.file(PUBLIC/path[1:],PUBLIC)
        if path=='/api/client/catalog':
            try:
                query=parse_qs(urlsplit(self.path).query,max_num_fields=256)
                page=int(query.get('page',['1'])[0]);size=int(query.get('pageSize',['24'])[0])
                if page<1 or size<1:raise ValueError()
                search=query.get('q',[''])[0]
                filters={key:query.get(key,[]) for key in ('category','material','capacity','bottle','use','section')}
                if len(search)>200 or any(len(values)>32 or any(len(value)>100 for value in values) for values in filters.values()):
                    raise ValueError()
            except ValueError:
                return self.respond(400,{'error':'检索参数格式不正确'})
            return self.respond_catalog(lambda:CLIENT_CATALOG.catalog(page,size,q=search,filters=filters))
        if path.startswith('/client-media/'):
            try:asset=CLIENT_CATALOG.media(path[len('/client-media/'):], thumbnail=self.wants_thumbnail())
            except ClientMediaBusy:return self.respond(429,{'error':'图片正在准备，请稍后重试'},extra={'Retry-After':'2'})
            if asset is None:return self.respond(404,{'error':'图片不存在'})
            return self.file(asset,CLIENT_CATALOG.cache,thumbnail=False)
        return self.respond(403,{'error':'此账号仅可访问客户展示页'})

    def unsupported_method(self):
        session=self.session()
        if session and session['role']=='client':
            return self.respond(403,{'error':'此账号仅可浏览客户展示页'})
        return self.respond(405,{'error':'请求方法不支持'})
    do_PUT=unsupported_method
    do_PATCH=unsupported_method
    do_DELETE=unsupported_method
    do_OPTIONS=unsupported_method
    do_TRACE=unsupported_method
    do_CONNECT=unsupported_method

    def admin_get(self,path):
        resource=path[len('/api/admin/'):]
        try:
            query=parse_qs(urlsplit(self.path).query,keep_blank_values=True,max_num_fields=256)
            if resource=='search-status':return self.respond(200,IMAGE_SEARCH.status())
            if resource=='import/template':return self.respond(200,template_csv(),'text/csv; charset=utf-8',{'Content-Disposition':'attachment; filename="packaging-import-template.csv"'})
            if resource=='export':
                return self.respond_export()
            if resource=='records':
                if 'id' in query:
                    ids=query['id']
                    if len(ids)!=1 or not ids[0].strip():raise ValueError('请选择一条记录')
                    return self.respond(200,{'item':STORE.read_admin('records',id=ids[0])})
                return self.respond_catalog(lambda:{'items':STORE.read_admin('records')})
            value=STORE.read_admin(resource,id=query.get('id',[None])[0] if resource=='audit' else None)
            if resource in ['settings','taxonomy']:
                version=value.pop('version')
                return self.respond(200,{'value':value,'version':version})
            if isinstance(value,list):
                if resource=='audit':
                    if query.get('id'):value=[x for x in value if str(x.get('entity_id',x.get('target_id','')))==query['id'][0]]
                    if query.get('resource'):value=[x for x in value if x.get('resource',x.get('entity'))==query['resource'][0]]
                return self.respond(200,{'items':value})
            return self.respond(200,value)
        except AdminError as error:return self.respond(error.status,{'error':str(error)})
        except (ValueError,KeyError,TypeError):return self.respond(400,{'error':'请求参数无效'})
    def admin_post(self,path,session):
        resource=path[len('/api/admin/'):]
        actor=session['username']
        if resource=='uploads':
            image=UPLOADS.save_request(lambda:self.body(MAX_REQUEST_BYTES))
            STORE.register_upload(image['path'],actor)
            return self.respond(201,{'image':image})
        if resource=='import/preview':
            if not IMPORT_GATE.acquire(blocking=False):raise SearchBusy('正在读取另一份导入文件，请稍后重试')
            try:
                data=parse_import(self.body(MAX_BODY_BYTES))
                preview=STORE.bulk_preview(data['rows']) if data['rows'] else {'rows':[],'errors':[]}
                # Store validation indexes the successfully parsed rows, which
                # excludes the header, blank rows and parse failures. Report
                # the source file's row numbers so staff can find the cells.
                source_rows=data.get('sourceRows',[])
                store_errors=[]
                for error in preview.get('errors',[]):
                    index=error.get('row',0)-1
                    source_row=source_rows[index] if 0<=index<len(source_rows) else error.get('row')
                    store_errors.append({**error,'row':source_row})
                errors=data['errors']+store_errors
                token=secrets.token_urlsafe(24) if not errors else None
                if token:
                    with LOCK:
                        expired=[key for key,item in IMPORTS.items() if item['expires']<time.time() or item['actor']==actor]
                        for key in expired:IMPORTS.pop(key,None)
                        if len(IMPORTS)>=4:raise SearchBusy('待确认导入过多，请先完成已有导入')
                        IMPORTS[token]={'actor':actor,'expires':time.time()+1800,'rows':preview['rows']}
                return self.respond(200,{'token':token,'count':len(preview['rows']),'valid':not errors,'rows':preview['rows'],'errors':errors,'warnings':data['warnings']})
            finally:IMPORT_GATE.release()
        data=self.body(3*1024*1024 if resource=='records' else 150000)
        if resource=='import/commit':
            token=data.get('token')
            if not isinstance(token,str):raise ValueError('请先预览导入文件')
            with LOCK:
                item=IMPORTS.get(token)
                if not item or item['actor']!=actor or item['expires']<time.time():
                    IMPORTS.pop(token,None);raise ValueError('导入预览已失效，请重新上传预览')
                if item.get('state')=='committing':raise SearchBusy('该批次正在导入，请稍后查看结果')
                # Claim the preview under the lock, then leave the global
                # session lock before touching the database: a large import
                # must not block other employees' logins or session checks.
                item['state']='committing';rows=item['rows']
            try:
                if not IMPORT_GATE.acquire(blocking=False):raise SearchBusy('正在处理其他导入，请稍后重试')
                try:
                    result=STORE.bulk_save(rows,actor)
                finally:
                    IMPORT_GATE.release()
            except Exception:
                with LOCK:
                    current=IMPORTS.get(token)
                    if current and current['actor']==actor and current.get('state')=='committing':current['state']='preview'
                raise
            with LOCK:IMPORTS.pop(token,None)
            IMAGE_SEARCH.refresh()
            return self.respond(200,result)
        if resource=='reindex':
            IMAGE_SEARCH.refresh()
            return self.respond(200,IMAGE_SEARCH.status())
        action=data.get('action','save')
        payload={key:value for key,value in data.items() if key not in ['action','record','value']}
        if resource=='records' and isinstance(data.get('record'),dict):payload={**data['record'],**payload}
        if resource in ['settings','taxonomy'] and isinstance(data.get('value'),dict):payload['value']=data['value']
        result=STORE.mutate(resource,action,payload,actor)
        if resource=='records':IMAGE_SEARCH.refresh()
        return self.respond(200,result)
    def image_download_headers(self,content_type):
        if not content_type.startswith('image/'):
            return {}
        values=parse_qs(urlsplit(self.path).query).get('download',[])
        if not values:
            return {}
        filename=values[0]
        extensions={'image/jpeg':'jpg','image/png':'png','image/webp':'webp','image/gif':'gif','image/svg+xml':'svg'}
        if len(filename)>100 or not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9._-]*\.(?:jpg|jpeg|png|webp|gif|svg)',filename):
            filename='yuanze-image.'+extensions.get(content_type,'jpg')
        return {'Content-Disposition':'attachment; filename="'+filename+'"'}
    def wants_thumbnail(self):
        return parse_qs(urlsplit(self.path).query).get('thumb') == ['1']
    def file(self,path,base,extra=None,thumbnail=True):
        path=path.resolve();base=base.resolve()
        if not path.is_relative_to(base) or not path.is_file(): return self.respond(404,{'error':'页面或文件不存在'})
        ctype=mimetypes.guess_type(path.name)[0] or 'application/octet-stream'
        if path.suffix in ['.js','.mjs']: ctype='text/javascript'
        # Minimal Linux installations may omit WebP from their system MIME map.
        if path.suffix.lower()=='.webp': ctype='image/webp'
        if thumbnail and self.wants_thumbnail() and path.suffix.lower() in {'.png','.jpg','.jpeg','.webp','.gif'}:
            try:asset=THUMBNAILS.get(path)
            except ThumbnailBusy:return self.respond(429,{'error':'图片正在准备，请稍后重试'},extra={'Retry-After':'2'})
            if asset is None:return self.respond(404,{'error':'图片不存在'})
            return self.file(asset,THUMBNAILS.root,extra,thumbnail=False)
        # Authentication, role selection and customer approval have already run.
        # Revalidate on every reuse: revoked media must never get a cached 304.
        cacheable=ctype.startswith('image/') or path.suffix.lower() in {'.css','.js','.mjs','.pdf','.woff','.woff2'}
        with path.open('rb') as source:
            stat=os.fstat(source.fileno())
            headers={**(extra or {}),**self.image_download_headers(ctype)}
            if cacheable:
                etag='"'+hashlib.sha256(f'{path}:{stat.st_size}:{stat.st_mtime_ns}:{stat.st_ino}'.encode()).hexdigest()[:32]+'"'
                headers.update({'Cache-Control':'private, no-cache','ETag':etag})
                tags=self.headers.get('If-None-Match','').split(',')
                if 'Content-Disposition' not in headers and any(tag.strip().removeprefix('W/') in {etag,'*'} for tag in tags):
                    return self.respond(304,b'',ctype,headers)
            self.response_headers(200,stat.st_size,ctype,headers)
            if self.command!='HEAD':
                while chunk:=source.read(65536):self.wfile.write(chunk)
    def do_POST(self):
        if not self.valid_host(): return self.respond(403,{'error':'访问地址无效'})
        path=urlsplit(self.path).path
        try:
            if not self.valid_origin(): return self.respond(403,{'error':'请从本站页面操作'})
            if path=='/api/login':
                data=self.body()
                # Reverse proxy must replace, not append, X-Forwarded-For.
                peer=self.headers.get('X-Forwarded-For',self.client_address[0]).split(',')[0].strip()
                source_key=('source',peer)
                raw_user=data.get('username','')
                user=raw_user.strip()[:80] if isinstance(raw_user,str) else ''
                account_key=('account',user.casefold())
                with LOCK:
                    # Failures are counted separately for the source address and
                    # for the account name, so an attacker cannot hide a slow
                    # password guess behind a single valid login.
                    retry_after=login_retry_after(source_key,account_key)
                if retry_after:
                    self.auth_reason='login_rate_limited'
                    return self.respond(429,{'error':'登录尝试过于频繁，请等待后重试',
                        'code':'LOGIN_RATE_LIMITED','retryAfter':retry_after},extra={'Retry-After':str(retry_after)})
                if not isinstance(raw_user,str) or not user:
                    with LOCK: register_failure(source_key)
                    raise ValueError('请填写账号')
                password=data.get('password','')
                if not isinstance(password,str) or not password or len(password)>300:
                    with LOCK: register_failure(source_key,account_key)
                    raise ValueError('密码格式无效')
                try:account=STORE.authenticate(user,password)
                except sqlite3.Error:raise AuthStorageUnavailable() from None
                if not account or account.get('role') not in SUPPORTED_ROLES:
                    with LOCK: register_failure(source_key,account_key)
                    self.auth_reason='invalid_credentials'
                    return self.respond(401,{'error':'账号或密码不正确','code':'INVALID_CREDENTIALS'})
                token=secrets.token_urlsafe(32);csrf=secrets.token_urlsafe(24)
                try:
                    SESSION_STORE.create(token,{'username':user,'csrf':csrf,'expires':time.time()+SESSION_SECONDS,
                        'auth_version':account['auth_version'],'role':account['role']})
                except SessionLimit:
                    self.auth_reason='session_capacity_reached'
                    return self.respond(429,{'error':'此账号的在线会话已达上限，请先在不用的设备退出登录',
                        'code':'SESSION_CAPACITY_REACHED'})
                except sqlite3.Error:raise AuthStorageUnavailable() from None
                with LOCK:
                    # Only this account's own counter is cleared; the source
                    # counter and other accounts' counters remain intact.
                    ATTEMPTS.pop(account_key,None)
                self.auth_reason='login_success'
                cookie=f'yz_session={token}; HttpOnly; SameSite=Strict; Path=/; Max-Age={SESSION_SECONDS}'
                if os.environ.get('YZ_SECURE_COOKIE','1')=='1': cookie+='; Secure'
                return self.respond(200,{'ok':True,'role':account['role']},extra={'Set-Cookie':cookie})
            s=self.session()
            if not s: return self.respond(401,{'error':'请先登录'})
            if not hmac.compare_digest(self.headers.get('X-CSRF-Token',''),s['csrf']): return self.respond(403,{'error':'页面已失效，请刷新重试'})
            if s['role']=='client' and path not in ['/api/logout','/api/client/image-search']:
                return self.respond(403,{'error':'此账号仅可浏览客户展示页'})
            if path=='/api/client/image-search':
                if s['role'] not in ['client','admin']:
                    return self.respond(403,{'error':'此功能仅供客户展示页使用'})
                result=IMAGE_SEARCH.search_request(lambda: self.body(MAX_REQUEST_BYTES))
                return self.respond(200,CLIENT_CATALOG.image_search_results(result.get('matches',[])))
            if path=='/api/image-search':
                return self.respond(200,IMAGE_SEARCH.search_request(lambda: self.body(MAX_REQUEST_BYTES)))
            if path.startswith('/api/admin/'):
                if s['role']!='admin':return self.respond(403,{'error':'仅管理员可以维护资料'})
                return self.admin_post(path,s)
            if path.startswith('/api/samples') and s['role']!='admin':return self.respond(403,{'error':'样品资料由管理员维护'})
            data=self.body()
            if path=='/api/logout':
                if not LOCAL:SESSION_STORE.delete(self.session_token)
                self.auth_reason='logged_out'
                return self.respond(200,{'ok':True},extra={'Set-Cookie':'yz_session=; Max-Age=0; Path=/; HttpOnly; SameSite=Strict; Secure'})
            if path=='/api/preferences':
                fav=data.get('favorites',[])
                if not isinstance(fav,list) or len(fav)>1000 or any(not isinstance(x,str) for x in fav): raise ValueError('收藏条目无效')
                fav=list(dict.fromkeys(fav))
                valid=active_ids(fav)
                if any(x not in valid for x in fav): raise ValueError('收藏条目无效')
                content=json.dumps({'favorites':fav})
                with db() as c:c.execute('INSERT INTO preferences VALUES(?,?) ON CONFLICT(username) DO UPDATE SET content=excluded.content',(s['username'],content))
                return self.respond(200,{'ok':True})
            if path=='/api/plans':
                ids=data.get('ids',[])
                if not isinstance(ids,list) or not 1<=len(ids)<=30 or any(not isinstance(x,str) for x in ids): raise ValueError('请选择1至30条有效记录')
                ids=list(dict.fromkeys(ids))
                valid=active_ids(ids)
                if any(x not in valid for x in ids): raise ValueError('请选择1至30条有效记录')
                title=required(data.get('title'),'请填写选型方案名称');note=clean(data.get('note',''),3000)
                snapshot=[STORE.read_admin('records',id=x) for x in ids];pid='PLAN-'+secrets.token_hex(6).upper()
                with db() as c:c.execute('INSERT INTO plans VALUES(?,?,?,?,?,?)',(pid,s['username'],title,note,json.dumps(snapshot,ensure_ascii=False),now()))
                return self.respond(201,{'id':pid})
            if path=='/api/samples':
                rid=data.get('record_id');sid=required(data.get('id'),'请填写实物样品编号')
                if rid not in active_ids([rid]): raise ValueError('关联记录不存在')
                location=required(data.get('location'),'请填写存放位置');condition=required(data.get('condition'),'请填写样品状况')
                with db() as c:
                    c.execute('INSERT INTO samples VALUES(?,?,?,?,?,?,?,?)',(sid,rid,location,'available','','',condition,now()))
                    c.execute('INSERT INTO movements(sample_id,action,actor,details,created) VALUES(?,?,?,?,?)',(sid,'register',s['username'],json.dumps(data,ensure_ascii=False),now()))
                return self.respond(201,{'ok':True})
            match=re.fullmatch(r'/api/samples/([^/]+)/(lend|return|consumed|sent)',path)
            if match:
                change_sample(unquote(match[1]),match[2],data,s['username']);return self.respond(200,{'ok':True})
            return self.respond(404,{'error':'功能不存在'})
        except AuthStorageUnavailable:return self.auth_storage_unavailable()
        except (BrokenPipeError,ConnectionResetError,TimeoutError):
            self.log_message('client_disconnected')
            self.close_connection=True
        except AdminError as e:return self.respond(e.status,{'error':str(e)})
        except SearchBusy as e: return self.respond(429,{'error':str(e)},extra={'Retry-After':'2'})
        except SearchUnavailable as e: return self.respond(503,{'error':str(e)})
        except sqlite3.IntegrityError: return self.respond(409,{'error':'编号已存在，请核对后重试'})
        except (ValueError,TypeError,KeyError,json.JSONDecodeError) as e: return self.respond(400,{'error':str(e) or '提交内容有误'})
        except Exception:
            return self.respond(500,{'error':'操作未完成，请重试；原记录已保留'})

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--host',default='127.0.0.1');p.add_argument('--port',type=int,default=4180);p.add_argument('--local-preview',action='store_true');args=p.parse_args()
    LOCAL=args.local_preview
    if LOCAL and args.host not in ['127.0.0.1','::1']: raise SystemExit('Local preview must bind to loopback')
    initialize()
    if CATALOG_PAGES.enabled:
        try:CATALOG_PAGES.warm()
        except CatalogBusy:print('Catalogue warming deferred; authentication remains available',flush=True)
    CLIENT_CATALOG.catalog(page_size=1)
    print(f'Yuanze reference listening on {args.host}:{args.port}',flush=True)
    ThreadingHTTPServer((args.host,args.port),Handler).serve_forever()
