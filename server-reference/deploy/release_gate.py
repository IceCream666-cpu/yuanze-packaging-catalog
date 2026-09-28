#!/usr/bin/env python3
"""Fail-closed deployment gates. Reports never contain credentials or cookies.

The config gate must run beside Caddy/certificate files on the target server.
The routes gate runs after switching the release, before declaring success;
its nonzero exit status must trigger the deployer's rollback procedure.
"""
import argparse
import datetime
import html.parser
import http.client
import http.cookiejar
import ipaddress
import json
import os
import re
import socket
import ssl
import stat
import subprocess
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

DEFAULT_HOSTS = ('bmt.yuanzebeauty.com', '8.134.220.216')
CODE = 'YZ-BC-000014'
REDIRECTS = {301, 302, 303, 307, 308}
MAX_BODY = 128 * 1024 * 1024


class GateFailure(Exception):
    """Messages must use fixed descriptions, never untrusted response bodies."""


def require(condition, message):
    if not condition:
        raise GateFailure(message)


def load_credentials(path):
    source = Path(path)
    require(source.is_file(), 'credential file is missing')
    require(not stat.S_IMODE(source.stat().st_mode) & 0o077,
            'credential file must have owner-only permissions (chmod 600)')
    raw = source.read_text(encoding='utf-8')
    if raw.lstrip().startswith('{'):
        value = json.loads(raw)
    else:
        value = {}
        for key, label in [('username', '账号'), ('password', '密码')]:
            match = re.search(r'(?m)^' + label + r'[：:]\s*([^\r\n]+)', raw)
            require(match is not None, 'credential file is missing username/password')
            value[key] = match.group(1)
    require(isinstance(value, dict) and all(isinstance(value.get(k), str) and value[k]
            for k in ('username', 'password')), 'credential file has invalid fields')
    return {k: value[k] for k in ('username', 'password')}


def walk_dicts(value):
    if isinstance(value, dict):
        yield value
        for child in value.values():
            yield from walk_dicts(child)
    elif isinstance(value, list):
        for child in value:
            yield from walk_dicts(child)


def check_auth_headers(headers, host):
    for scope, forbidden in (
        ('response', {'location', 'set-cookie'}),
        ('request', {'cookie', 'origin', 'authorization', 'x-csrf-token'}),
    ):
        for node in walk_dicts(headers.get(scope, {})):
            require(not forbidden.intersection(key.lower() for key in node),
                    f'{host}: gateway must not replace authentication headers')
            for action in ('delete', 'drop'):
                removed = node.get(action, [])
                if isinstance(removed, list):
                    require(not forbidden.intersection(str(key).lower() for key in removed),
                            f'{host}: gateway must not delete authentication headers')
    request = headers.get('request', {})
    for action in ('set', 'add', 'replace'):
        values = request.get(action, {})
        if isinstance(values, dict):
            for key, value in values.items():
                if key.lower() == 'host':
                    require(action == 'set' and value in (["{http.request.hostport}"], ["{hostport}"]),
                            f'{host}: proxy must preserve the original Host')
    require('host' not in {str(key).lower() for key in request.get('delete', [])},
            f'{host}: proxy must preserve the original Host')


def check_proxy_contract(adapted, hosts, upstream='127.0.0.1:4180'):
    """Auth routing belongs exclusively to the app, not to Caddy.

    This deliberately small allowlist is stronger than a regex for today's bug:
    even a syntactically valid rewrite/redirect/file-server alternative is blocked.
    A future intentional gateway feature needs an explicit contract/test update.
    """
    servers = adapted.get('apps', {}).get('http', {}).get('servers', {})
    require(isinstance(servers, dict) and servers, 'no HTTP servers in adapted configuration')
    found = {host: [] for host in hosts}
    for server in servers.values():
        for route in server.get('routes', []):
            matchers = route.get('match', [])
            require(matchers and all(isinstance(m, dict) and m.get('host') for m in matchers),
                    'unscoped HTTP route could intercept protected site routing')
            for matcher in matchers:
                require(all('*' not in host for host in matcher['host']),
                        'wildcard host route requires explicit review of protected sites')
                for host in matcher.get('host', []):
                    if host in found:
                        found[host].append(route)
    for host, routes in found.items():
        require(len(routes) == 1, f'{host}: expected exactly one explicit site route')
        route = routes[0]
        require(route.get('terminal') is True, f'{host}: site route must be terminal')
        proxies = []
        for node in walk_dicts(route):
            if 'match' in node:
                require(all(isinstance(m, dict) and set(m) <= {'host'}
                            for m in node['match']),
                        f'{host}: path/method auth routing must stay in the application')
            handler = node.get('handler')
            if handler:
                require(handler in {'subroute', 'headers', 'encode', 'reverse_proxy'},
                        f'{host}: gateway handler outside transparent proxy contract')
                if handler == 'reverse_proxy':
                    require('rewrite' not in node,
                            f'{host}: proxy must preserve the application request URI')
                    check_auth_headers(node.get('headers', {}), host)
                    proxies.append(node)
                elif handler == 'headers':
                    check_auth_headers(node, host)
        require(len(proxies) == 1, f'{host}: expected exactly one reverse proxy')
        require(proxies[0].get('upstreams') == [{'dial': upstream}],
                f'{host}: unexpected application upstream')
    return {'hosts': list(hosts), 'transparentProxyContract': True}


def config_gate(args):
    commands = [
        [args.caddy_bin, 'validate', '--config', str(args.caddyfile), '--adapter', 'caddyfile'],
        [args.caddy_bin, 'adapt', '--config', str(args.caddyfile), '--adapter', 'caddyfile'],
    ]
    outputs = []
    for command in commands:
        result = subprocess.run(command, capture_output=True, text=True, timeout=60)
        require(result.returncode == 0, f'Caddy {command[1]} failed; inspect locally without publishing secrets')
        outputs.append(result.stdout)
    report = check_proxy_contract(json.loads(outputs[1]), args.host or DEFAULT_HOSTS, args.upstream)
    report['caddyValidate'] = True
    report['caddyAdapt'] = True
    return report


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, request, fp, code, msg, headers, newurl):
        return None


class TargetHTTPSConnection(http.client.HTTPSConnection):
    def __init__(self, host, connect_address=None, **kwargs):
        super().__init__(host, **kwargs)
        if connect_address:
            # HTTPSConnection still wraps TLS with self.host as server_hostname;
            # only the TCP destination is overridden, not Host or certificate identity.
            self._create_connection = lambda address, timeout=socket._GLOBAL_DEFAULT_TIMEOUT, source_address=None: socket.create_connection(
                (connect_address, address[1]), timeout, source_address)


class TargetHTTPSHandler(urllib.request.HTTPSHandler):
    def __init__(self, connect_address):
        super().__init__(context=ssl.create_default_context())
        self.connect_address = connect_address

    def https_open(self, request):
        return self.do_open(lambda host, **kwargs: TargetHTTPSConnection(
            host, connect_address=self.connect_address, **kwargs), request,
            context=self._context)


class Client:
    def __init__(self, origin, timeout=20, allow_local_http=False, connect_address=None):
        parts = urllib.parse.urlsplit(origin)
        require(parts.scheme == 'https' or (allow_local_http and parts.scheme == 'http'
                and parts.hostname in {'localhost', '127.0.0.1', '::1'}),
                'origin must use verified HTTPS (HTTP allowed only for local tests)')
        require(parts.hostname and not parts.username and not parts.password
                and parts.path in {'', '/'} and not parts.query and not parts.fragment,
                'origin must be a bare site origin without credentials or path')
        self.origin = urllib.parse.urlunsplit((parts.scheme, parts.netloc, '', '', ''))
        if connect_address:
            ipaddress.ip_address(connect_address)
        self.connect_address = connect_address
        self.timeout = timeout
        self.jar = http.cookiejar.CookieJar()
        self.opener = urllib.request.build_opener(
            urllib.request.ProxyHandler({}), NoRedirect(),
            urllib.request.HTTPCookieProcessor(self.jar),
            TargetHTTPSHandler(connect_address))
        self.csrf = ''
        self.agent = 'Yuanze-Release-Gate/1.0'

    def request(self, path, data=None, csrf=True):
        require(path.startswith('/') and not path.startswith('//'), 'request must stay on this origin')
        headers = {'User-Agent': self.agent, 'Accept': 'application/json, text/html',
                   'Cache-Control': 'no-cache'}
        body = None
        if data is not None:
            body = json.dumps(data).encode()
            headers.update({'Content-Type': 'application/json', 'Origin': self.origin})
            if csrf:
                headers['X-CSRF-Token'] = self.csrf
        request = urllib.request.Request(self.origin + path, data=body, headers=headers)
        try:
            response = self.opener.open(request, timeout=self.timeout)
        except urllib.error.HTTPError as error:
            response = error
        with response:
            content = response.read(MAX_BODY + 1)
            require(len(content) <= MAX_BODY, 'response exceeds gate size limit')
            return response.status, response.headers, content

    def document(self, path, marker, expected_path, max_redirects=4):
        visited = set()
        for _ in range(max_redirects + 1):
            require(path not in visited, 'redirect loop detected')
            visited.add(path)
            status, headers, body = self.request(path)
            if status not in REDIRECTS:
                require(status == 200, f'document returned HTTP {status}, expected 200')
                require(path == expected_path, 'document reached the wrong route')
                require(marker in body, 'document does not contain the expected application entrypoint')
                return len(visited) - 1
            location = headers.get('Location', '')
            require(bool(location), 'redirect is missing Location')
            absolute = urllib.parse.urljoin(self.origin + path, location)
            target = urllib.parse.urlsplit(absolute)
            require(urllib.parse.urlunsplit((target.scheme, target.netloc, '', '', '')) == self.origin,
                    'cross-origin redirect blocked (session credentials are never forwarded)')
            require(not target.fragment, 'unexpected redirect fragment')
            path = urllib.parse.urlunsplit(('', '', target.path or '/', target.query, ''))
        raise GateFailure('redirect limit exceeded')


class LoginScripts(html.parser.HTMLParser):
    def __init__(self):
        super().__init__()
        self.scripts = []

    def handle_starttag(self, tag, attrs):
        if tag == 'script':
            src = dict(attrs).get('src')
            if src:
                self.scripts.append(src)


def local_asset_path(client, base, reference):
    target = urllib.parse.urlsplit(urllib.parse.urljoin(client.origin + base, reference))
    require(urllib.parse.urlunsplit((target.scheme, target.netloc, '', '', '')) == client.origin,
            'login script dependency leaves the site origin')
    require(not target.fragment, 'login script dependency has an unexpected fragment')
    return urllib.parse.urlunsplit(('', '', target.path, target.query, ''))


def login_assets_gate(client):
    _, page = expect_status(client, '/login', 200)
    parsed = LoginScripts()
    parsed.feed(page.decode('utf-8'))
    require(parsed.scripts, 'login page is missing its script entrypoint')
    todo = [local_asset_path(client, '/login', src) for src in parsed.scripts]
    seen = set()
    # Covers static imports, re-exports and literal dynamic imports used here.
    imports = re.compile(r'''(?:\b(?:import|export)\s+(?:[^;'"\n]+?\s+from\s*)?|\bimport\s*\(\s*)["']([^"']+)["']''')
    while todo:
        path = todo.pop()
        if path in seen:
            continue
        require(len(seen) < 30, 'login script dependency limit exceeded')
        seen.add(path)
        headers, source = expect_status(client, path, 200)
        require(headers.get_content_type() in {'text/javascript', 'application/javascript'},
                'login script returned a non-JavaScript MIME type')
        text = source.decode('utf-8')
        require('<html' not in text[:100].lower() and '<!doctype' not in text[:100].lower(),
                'login script returned an HTML document')
        for dependency in imports.findall(text):
            require(dependency.startswith(('/', './', '../')), 'unsupported login module dependency')
            todo.append(local_asset_path(client, path, dependency))
    return len(seen)


def certificate_report(client):
    parts = urllib.parse.urlsplit(client.origin)
    if parts.scheme != 'https':
        return {'verified': False, 'localTestOnly': True}
    with socket.create_connection((client.connect_address or parts.hostname, parts.port or 443),
                                  timeout=client.timeout) as tcp:
        with ssl.create_default_context().wrap_socket(tcp, server_hostname=parts.hostname) as secure:
            certificate = secure.getpeercert()
    expiry = datetime.datetime.fromtimestamp(ssl.cert_time_to_seconds(certificate['notAfter']),
                                             datetime.timezone.utc)
    remaining = expiry - datetime.datetime.now(datetime.timezone.utc)
    return {'verified': True, 'expiresAt': expiry.isoformat(),
            'daysRemaining': round(remaining.total_seconds() / 86400, 2)}


def expect_status(client, path, expected, data=None, csrf=True):
    status, headers, body = client.request(path, data, csrf)
    require(status == expected, f'{path.split("?")[0]} returned HTTP {status}, expected {expected}')
    return headers, body


def role_gate(origin, role, credentials, timeout=20, allow_local_http=False, connect_address=None):
    client = Client(origin, timeout, allow_local_http, connect_address)
    checks = []
    authenticated = False
    error = None
    try:
        client.document('/', b'login.js', '/login')
        client.document('/admin', b'login.js', '/login')
        client.document('/?code=' + CODE, b'login.js', '/login?code=' + CODE)
        expect_status(client, '/api/session', 401)
        expect_status(client, '/api/catalog', 401)
        checks.append('anonymous_routes_and_api_protection')
        asset_count = login_assets_gate(client)
        checks.append('anonymous_login_script_dependencies_and_mime')
        headers, body = expect_status(client, '/api/login', 200, credentials)
        require(json.loads(body).get('role') == role, 'login returned an unexpected role')
        authenticated = True
        cookie = headers.get('Set-Cookie', '')
        require('HttpOnly' in cookie and 'SameSite=Strict' in cookie
                and (client.origin.startswith('http://') or 'Secure' in cookie),
                'login cookie protection is missing')
        _, body = expect_status(client, '/api/session', 200)
        session = json.loads(body)
        require(session.get('role') == role and session.get('username') == credentials['username'],
                'session identity does not match authenticated account')
        client.csrf = session.get('csrf', '')
        require(isinstance(client.csrf, str) and client.csrf, 'session is missing CSRF token')
        checks.append('login_and_session')
        destination = '/' if role == 'employee' else '/admin'
        marker = b'app.js' if role == 'employee' else b'admin.js'
        client.document('/', marker, destination)
        client.document('/login', marker, destination)
        # Request the destination again, with a mobile browser identity, like refresh.
        client.agent = 'Mozilla/5.0 (iPhone; CPU iPhone OS 18_0 like Mac OS X) Version/18.0 Mobile/15E148 Safari/604.1'
        client.document(destination, marker, destination)
        checks.append('workspace_login_redirect_and_mobile_refresh')
        if role == 'employee':
            _, body = expect_status(client, '/api/catalog', 200)
            records = json.loads(body).get('records')
            require(isinstance(records, list) and len(records) > 0, 'catalogue is empty or invalid')
            expect_status(client, '/admin', 403)
            expect_status(client, '/api/admin/settings', 403)
            checks.append('catalogue_and_employee_role_boundary')
        else:
            _, body = expect_status(client, '/api/admin/settings', 200)
            require(isinstance(json.loads(body).get('value'), dict), 'admin API response is invalid')
            checks.append('admin_workspace_and_api')
        client.document('/login?code=' + CODE, b'app.js', '/?code=' + CODE)
        checks.append('authenticated_product_deep_link')
        expect_status(client, '/api/logout', 403, {}, csrf=False)
        checks.append('csrf_protection')
    except Exception as exc:
        error = exc
    finally:
        if authenticated and client.csrf:
            try:
                expect_status(client, '/api/logout', 200, {})
                expect_status(client, '/api/session', 401)
                client.document('/', b'login.js', '/login')
                checks.append('logout_invalidates_session')
            except Exception as exc:
                if error is None:
                    error = exc
        # Closing the cookie jar removes local credentials; no cookies are persisted.
        client.jar.clear()
    if error:
        if isinstance(error, GateFailure):
            raise GateFailure(f'{role}: {error}') from None
        raise GateFailure(f'{role}: request/response failure ({type(error).__name__}); no secrets logged') from None
    return {'role': role, 'checks': checks, 'loginScriptCount': asset_count, 'passed': True}


def routes_gate(args):
    if args.credentials_stdin:
        require(not args.employee_credentials and not args.admin_credentials,
                'use credentials stdin or credential file paths, not both')
        credentials = json.load(sys.stdin)
        require(isinstance(credentials, dict) and all(
            isinstance(credentials.get(role), dict) and all(
                isinstance(credentials[role].get(key), str) and credentials[role][key]
                for key in ('username', 'password')) for role in ('employee', 'admin')),
            'stdin credentials must contain employee/admin username and password objects')
    else:
        require(args.employee_credentials and args.admin_credentials,
                'both private credential file paths are required')
        credentials = {'employee': load_credentials(args.employee_credentials),
                       'admin': load_credentials(args.admin_credentials)}
    sites = []
    for origin in args.origin:
        client = Client(origin, args.timeout, args.allow_local_http, args.connect_address)
        tls = certificate_report(client)
        roles = [role_gate(origin, role, credentials[role], args.timeout, args.allow_local_http, args.connect_address)
                 for role in ('employee', 'admin')]
        sites.append({'origin': client.origin, 'tls': tls, 'roles': roles})
    return {'sites': sites, 'tlsVerification': all(site['tls']['verified'] for site in sites),
            'networkPath': ('direct_tcp_override_not_public_dns_test' if args.connect_address else 'public_dns_from_this_machine'),
            'connectAddress': args.connect_address,
            'persistentCookies': False}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--report', type=Path, help='write the redacted JSON result atomically')
    sub = parser.add_subparsers(dest='gate', required=True)
    config = sub.add_parser('config', help='validate Caddy and enforce transparent auth routing')
    config.add_argument('--caddyfile', type=Path, required=True)
    config.add_argument('--caddy-bin', default='/usr/local/bin/yuanze-caddy')
    config.add_argument('--host', action='append')
    config.add_argument('--upstream', default='127.0.0.1:4180')
    routes = sub.add_parser('routes', help='one bounded login test per account per origin; never poll')
    routes.add_argument('--origin', action='append', required=True)
    routes.add_argument('--employee-credentials', type=Path)
    routes.add_argument('--admin-credentials', type=Path)
    routes.add_argument('--credentials-stdin', action='store_true',
                        help='read employee/admin JSON from stdin; useful over SSH without writing server credential files')
    routes.add_argument('--timeout', type=float, default=20)
    routes.add_argument('--connect-address', help='TCP destination IP only; preserve URL Host/SNI and strict TLS verification')
    routes.add_argument('--allow-local-http', action='store_true', help='local test servers only, never disables TLS verification')
    args = parser.parse_args(argv)
    report = {'gate': args.gate, 'checkedAt': datetime.datetime.now(datetime.timezone.utc).isoformat()}
    if args.gate == 'routes':
        report['networkPath'] = ('direct_tcp_override_not_public_dns_test' if args.connect_address else 'public_dns_from_this_machine')
    try:
        report.update(config_gate(args) if args.gate == 'config' else routes_gate(args))
        report['passed'] = True
    except Exception as exc:
        report['passed'] = False
        report['error'] = str(exc) if isinstance(exc, GateFailure) else type(exc).__name__ + ' (details suppressed)'
    encoded = json.dumps(report, ensure_ascii=False, indent=2) + '\n'
    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        temporary = args.report.with_name(args.report.name + '.tmp')
        temporary.write_text(encoded, encoding='utf-8')
        os.replace(temporary, args.report)
    print(encoded, end='')
    return 0 if report['passed'] else 1


if __name__ == '__main__':
    sys.exit(main())
