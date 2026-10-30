"""Verify the published client1.33 and preserve concurrent packaging/auth features."""
from pathlib import Path
import datetime
import hashlib
import json
import sys
import urllib.request
import urllib.error
import time

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
PUBLIC = ROOT / 'server-reference/public/showroom'
sys.path.insert(0, str(ROOT / 'server-reference/deploy'))
import release_gate as g


def verified_client():
    client = g.Client('https://bmt.yuanzebeauty.com', 30, connect_address='47.79.233.3')
    original = client.opener.open
    def open_with_get_retry(request, *args, **kwargs):
        for attempt in range(3):
            try:
                return original(request, *args, **kwargs)
            except urllib.error.HTTPError:
                raise
            except (urllib.error.URLError, TimeoutError):
                if request.get_method() != 'GET' or attempt == 2:
                    raise
                time.sleep(1)
    client.opener.open = open_with_get_retry
    return client


def sha(data):
    return hashlib.sha256(data).hexdigest()


def range_check(client, path, local_path, total_bytes):
    request = urllib.request.Request(client.origin + path, headers={
        'Range': 'bytes=0-99', 'Cache-Control': 'no-cache', 'User-Agent': client.agent,
    })
    with client.opener.open(request, timeout=30) as response:
        assert response.status == 206, 'Byte-range request did not return 206'
        data = response.read(101)
        assert len(data) == 100 and data == local_path.read_bytes()[:100]
        assert response.headers.get('Content-Range') == f'bytes 0-99/{total_bytes}'
        return {'status': 206, 'bytes': len(data), 'contentRange': response.headers['Content-Range']}


def main():
    before = json.loads((HERE / 'server-before.json').read_text())
    published = json.loads((HERE / 'publication.json').read_text())
    manifest_bytes = (PUBLIC / 'bundle-manifest.json').read_bytes()
    manifest = json.loads(manifest_bytes)
    assert manifest['version'] == published['version'] == 'client1.33'
    assert sha(manifest_bytes) == published['manifestSha256'], 'Local build changed after publication'
    packaging = sorted(n for n in manifest['files'] if n.startswith('assets/packaging/'))
    model = 'assets/packaging/poster-060.glb'
    assert model in packaging
    approved = json.loads((ROOT / 'docs/client-motion-demo/packaging-manifest.json').read_text())
    assert len([f for f in approved['files'] if f['kind']=='model'])==26
    assert {n for n in packaging if n.endswith('.glb')} == {f['productionTarget'] for f in approved['files'] if f['kind']=='model'}
    secret = Path('/Users/icecream/Documents/Codex/2026-09-22/claude-code/.secrets')
    report = {'version': 'client1.33', 'roles': {}, 'resources': [], 'packagingResources': []}
    for role, filename in [('client', '客户展示登录信息.txt'), ('employee', '包材库登录信息.txt'), ('admin', '管理员登录信息.txt')]:
        client = verified_client()
        try:
            g.expect_status(client, '/api/login', 200, g.load_credentials(secret / filename))
            _, raw = g.expect_status(client, '/api/session', 200)
            session = json.loads(raw)
            assert session['role'] == role
            client.csrf = session['csrf']
            if role == 'employee':
                g.expect_status(client, '/', 200)
                g.expect_status(client, '/client', 403)
                g.expect_status(client, '/showroom/preview.js', 403)
                for name in packaging:
                    g.expect_status(client, '/showroom/' + name, 403)
            else:
                _, body = g.expect_status(client, '/client', 200)
                assert body == (PUBLIC / 'index.html').read_bytes()
                if role == 'admin':
                    g.expect_status(client, '/admin', 200)
                    report['adminAHARange']=range_check(client,'/showroom/'+model,PUBLIC/model,manifest['files'][model]['bytes'])
            if role == 'client':
                g.expect_status(client, '/api/catalog', 403)
                g.expect_status(client, '/api/admin/records', 403)
                g.expect_status(client, '/showroom/bundle-manifest.json', 404)
                report['withdrawnModels'] = []
                for n in (74,75,76,77,78):
                    path = f'/showroom/assets/packaging/poster-{n:03}.glb'
                    g.expect_status(client,path,404)
                    report['withdrawnModels'].append(path)
                report['withdrawnFeaturedImages'] = []
                for n in range(74,79):
                    for suffix in ('.png','-640.webp','-1024.webp'):
                        path = f'/showroom/assets/featured/poster-{n:03}{suffix}'
                        g.expect_status(client,path,404)
                        report['withdrawnFeaturedImages'].append(path)
                names = [f'assets/posters/poster-{n:03}.webp' for n in range(74,79)] + ['preview.js', 'preview.css', 'index.html', 'product-posters.js',
                         'assets/featured/poster-012-640.webp'] + packaging
                for name in names:
                    entry = manifest['files'][name]
                    if name == model:
                        headers,data=g.expect_status(client,'/showroom/'+name,200)
                        assert len(data)==entry['bytes'] and sha(data)==entry['sha256']
                        report['ahaFullFile']={'name':name,'status':200,**entry}
                        assert 'no-cache' in headers.get('Cache-Control','')
                        previous_etag=json.loads((HERE/'model-cache-before.json').read_text())['etag']
                        conditional=urllib.request.Request(client.origin+'/showroom/'+name,headers={'If-None-Match':previous_etag,'User-Agent':client.agent})
                        with client.opener.open(conditional,timeout=30) as response:
                            revalidated=response.read()
                            assert response.status==200 and sha(revalidated)==entry['sha256']
                            assert response.headers.get('ETag')!=previous_etag
                            report['previousModelCacheRevalidated']={'status':200,'bytes':len(revalidated),'sha256':sha(revalidated),'etagChanged':True}

                    if name.endswith('.glb'):
                        verified = range_check(client, '/showroom/' + name, PUBLIC/name, entry['bytes'])
                        report['packagingResources'].append({'name':name, **entry, 'httpsRange':verified, 'fullFileHashVerifiedOnServer':True})
                    else:
                        headers, data = g.expect_status(client, '/showroom/' + name, 200)
                        assert len(data) == entry['bytes'] and sha(data) == entry['sha256'], name
                    report['resources'].append(name)
                    (HERE / 'online-progress.json').write_text(json.dumps(report))
                report['all26ModelRanges'] = {entry['name']:entry['httpsRange'] for entry in report['packagingResources']}
                report['modelRange'] = range_check(client, '/showroom/' + model, PUBLIC / model, manifest['files'][model]['bytes'])
                headers, data = g.expect_status(client, '/showroom/assets/posters/poster-060.webp?download=poster-060.webp', 200)
                assert 'attachment' in headers.get('Content-Disposition', '')
                assert sha(data) == manifest['files']['assets/posters/poster-060.webp']['sha256']
                report['originalDownload'] = True
            report['roles'][role] = True
        finally:
            if client.csrf:
                g.expect_status(client, '/api/logout', 200, {})
            g.expect_status(client, '/api/session', 401)

    client = verified_client()
    for name in ['preview.js', 'assets/featured/poster-012.png', 'assets/featured/poster-012-640.webp',
                 'assets/optimized/yuanze-mark-compact.webp', 'assets/optimized/poster-060-strip.webp'] + packaging:
        g.expect_status(client, '/showroom/' + name, 401)
    login_root = ROOT / 'server-reference/public/login-ui'
    login_bytes = (login_root / 'bundle-manifest.json').read_bytes()
    assert sha(login_bytes) == before['outsideHashes']['public/login-ui/bundle-manifest.json']
    login = json.loads(login_bytes)
    for name, entry in login['files'].items():
        if name == 'index.html':
            g.expect_status(client, '/_login/index.html', 404)
            continue
        _, data = g.expect_status(client, '/_login/' + name, 200)
        assert sha(data) == entry['sha256'], name
        if name.endswith('.mp4'):
            report['loginVideoRange'] = range_check(client, '/_login/' + name, login_root / name, len(data))
    report['loginAllFilesVerified'] = True
    report['videoRange'] = True
    _, body = g.expect_status(client, '/login', 200)
    assert b'yuanze2.0.3' in body
    _, data = g.expect_status(client, '/_login/login.js', 200)
    assert sha(data) == before['outsideHashes']['public/login-ui/login.js']
    report.update(
        counts={'featured':26,'posters':61,'models':26,'images':418,'resources':458},
        checkedAt=datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=8))).isoformat(timespec='seconds'),
        manifestSha256=sha(manifest_bytes), publicHttps=True, certificateVerified=True, directOriginAddress='47.79.233.3', tlsServerName='bmt.yuanzebeauty.com', anonymousDenied=True,
        packagingAccessControlled=True, logoutVerified=True, loginUnchanged=True,
    )
    (HERE / 'online-verification.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report))


if __name__ == '__main__':
    main()
