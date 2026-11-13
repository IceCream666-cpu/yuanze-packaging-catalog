"""Verify the deployed client1.56 assets through authenticated, verified HTTPS.

Read-only application checks except dedicated test-account login/logout.
No credentials, CSRF tokens or cookies enter the report.
"""
from pathlib import Path
import datetime
import hashlib
import json
import sys
import time
import urllib.error
import urllib.request

HERE = Path(__file__).resolve().parent
ROOT = Path(__file__).resolve().parents[5]
PUBLIC = ROOT / 'server-reference/public/showroom'
sys.path.insert(0, str(ROOT / 'server-reference/deploy'))
import release_gate as g


def sha(data):
    return hashlib.sha256(data).hexdigest()


def verified_client():
    client = g.Client('https://bmt.yuanzebeauty.com', 30, connect_address='47.79.233.3')
    original = client.opener.open
    def retry_get(request, *args, **kwargs):
        for attempt in range(3):
            try:
                return original(request, *args, **kwargs)
            except urllib.error.HTTPError:
                raise
            except (urllib.error.URLError, TimeoutError):
                if request.get_method() != 'GET' or attempt == 2:
                    raise
                time.sleep(1)
    client.opener.open = retry_get
    return client


def range_check(client, name, entry):
    request = urllib.request.Request(client.origin + '/showroom/' + name, headers={
        'Range':'bytes=0-99', 'Cache-Control':'no-cache', 'User-Agent':client.agent,
    })
    with client.opener.open(request, timeout=30) as response:
        assert response.status == 206, name
        data = response.read(101)
        assert len(data) == 100 and data == (PUBLIC/name).read_bytes()[:100], name
        expected = f"bytes 0-99/{entry['bytes']}"
        assert response.headers.get('Content-Range') == expected, name
        return {'status':206, 'bytes':100, 'contentRange':expected}


def save_progress(report):
    (HERE/'online-progress.json').write_text(json.dumps(report, indent=2)+'\n')


def main():
    published = json.loads((HERE/'publication.json').read_text())
    plan = json.loads((HERE/'publication-plan.json').read_text())
    before = json.loads((HERE/'server-before.json').read_text())
    raw_manifest = (PUBLIC/'bundle-manifest.json').read_bytes()
    manifest = json.loads(raw_manifest)
    assert published['version'] == manifest['version'] == plan['version'] == 'client1.56'
    assert sha(raw_manifest) == published['manifestSha256'] == plan['manifestSha256']
    models = sorted(n for n in manifest['files'] if n.endswith('.glb'))
    assert len(models) == 32 and len(manifest['files']) == 514
    approved = json.loads((ROOT/'docs/client-motion-demo/packaging-manifest.json').read_text())
    assert set(models) == {x['productionTarget'] for x in approved['files'] if x['kind']=='model'}
    assert 'assets/packaging/poster-081-v1.glb' in models
    assert 'assets/packaging/poster-085-v2.glb' in models
    assert len(plan['added']) == 1 and len(plan['changed']) == 3 and len(plan['removed']) == 1
    secret = Path('/Users/icecream/Documents/Codex/2026-09-22/claude-code/.secrets')
    report = {'version':'client1.56', 'roles':{}, 'fullResources':[], 'modelRanges':{}, 'excludedResources':[]}
    for role,filename in [('client','客户展示登录信息.txt'),('employee','包材库登录信息.txt'),('admin','管理员登录信息.txt')]:
        client = verified_client()
        logged_in = False
        try:
            g.expect_status(client,'/api/login',200,g.load_credentials(secret/filename))
            logged_in = True
            _, body = g.expect_status(client,'/api/session',200)
            session = json.loads(body)
            assert session['role'] == role
            client.csrf = session['csrf']
            if role == 'employee':
                g.expect_status(client,'/',200)
                for path in ['/client','/showroom/preview.js','/showroom/assets/packaging/poster-081-v1.glb','/showroom/assets/posters/poster-086.webp']:
                    g.expect_status(client,path,403)
            else:
                _,body = g.expect_status(client,'/client',200)
                assert body == (PUBLIC/'index.html').read_bytes()
                if role == 'admin':
                    g.expect_status(client,'/admin',200)
                    report['adminModelRange'] = range_check(client,'assets/packaging/poster-081-v1.glb',manifest['files']['assets/packaging/poster-081-v1.glb'])
            if role == 'client':
                for path in ['/api/catalog','/api/admin/records']:
                    g.expect_status(client,path,403)
                g.expect_status(client,'/showroom/bundle-manifest.json',404)
                for name in plan['changed']:
                    headers,data = g.expect_status(client,'/showroom/'+name,200)
                    entry = manifest['files'][name]
                    assert len(data) == entry['bytes'] and sha(data) == entry['sha256'], name
                    report['fullResources'].append({'name':name,'status':200,**entry})
                    save_progress(report)
                catalogue_raw=(PUBLIC/'product-posters.js').read_text()
                catalogue=json.loads(catalogue_raw[catalogue_raw.index('{'):].strip().rstrip(';'))['items']
                assert len(catalogue)==68 and all(p['id']!='poster-086' for p in catalogue)
                report['posterThumbnails']=[]
                for poster in [p for p in catalogue if p['id'] in ['poster-071','poster-085']]:
                    name=poster['thumbnail'].removeprefix('/showroom/')
                    _,data=g.expect_status(client,'/showroom/'+name,200)
                    assert sha(data)==manifest['files'][name]['sha256'],name
                    report['posterThumbnails'].append(poster['id'])
                report['featuredPreviews']=[]
                for product in [p for p in json.loads((ROOT/'docs/client-motion-demo/src/featured.json').read_text()) if p['id'] in ['poster-071','poster-085']]:
                    name=f"assets/featured/{product['id']}-640.webp"
                    _,data=g.expect_status(client,'/showroom/'+name,200)
                    assert sha(data)==manifest['files'][name]['sha256'],name
                    report['featuredPreviews'].append(product['id'])
                for name in models:
                    report['modelRanges'][name] = range_check(client,name,manifest['files'][name])
                    save_progress(report)
                for number in [74,75,76,77,78,83,86]:
                    names = [f'assets/packaging/poster-{number:03}.glb',f'assets/packaging/poster-{number:03}-v1.glb']
                    names += [f'assets/featured/poster-{number:03}{suffix}' for suffix in ['.png','-640.webp','-1024.webp']]
                    for name in names:
                        g.expect_status(client,'/showroom/'+name,404)
                        report['excludedResources'].append(name)
                for name in plan['removed']:
                    g.expect_status(client,'/showroom/'+name,404)
                    report['excludedResources'].append(name)
                for number in [71]:
                    name=f'assets/posters/poster-{number:03}.webp'
                    headers,data=g.expect_status(client,f'/showroom/{name}?download=poster-{number:03}.webp',200)
                    assert 'attachment' in headers.get('Content-Disposition','')
                    assert sha(data)==manifest['files'][name]['sha256']
                report['originalDownloads']=[71]
            report['roles'][role]=True
        finally:
            if logged_in and client.csrf:
                g.expect_status(client,'/api/logout',200,{})
                g.expect_status(client,'/api/session',401)
        save_progress(report)
    anonymous=verified_client()
    for path in ['/api/session','/showroom/preview.js','/showroom/assets/packaging/poster-081-v1.glb','/showroom/assets/posters/poster-086.webp']:
        g.expect_status(anonymous,path,401)
    _,body=g.expect_status(anonymous,'/_login/login.js',200)
    assert sha(body)==before['outsideHashes']['public/login-ui/login.js']
    report.update(
        counts=plan['counts'], resources=514, checkedAt=datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=8))).isoformat(timespec='seconds'),
        manifestSha256=sha(raw_manifest), publicHttps=True, certificateVerified=True,
        directOriginAddress='47.79.233.3', tlsServerName='bmt.yuanzebeauty.com',
        anonymousDenied=True, logoutVerified=True, loginScriptUnchanged=True,
        all32ModelRanges=True, oldModelFullHashesVerifiedOnServer=31,
        withdrawnPoster='poster-086', publishedModel='poster-071', featuredAdded=None, browserInteractionVerified=False,
    )
    (HERE/'online-verification.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({'version':report['version'],'counts':report['counts'],'verifiedFullResources':len(report['fullResources']),'modelRanges':len(report['modelRanges']),'roles':report['roles'],'checkedAt':report['checkedAt'],'manifestSha256':report['manifestSha256']}))


if __name__=='__main__':
    main()
