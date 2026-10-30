"""Update only the approved AHA Body Mist complete sprayer model, preserving all 61 posters, 26 featured displays and the other 25 models.

Without --publish this is a LOCAL plan/hash check only: no SSH or remote writes.
"""
from pathlib import Path
import argparse
import hashlib
import io
import json
import sys
import tarfile

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
LOCAL = ROOT / 'server-reference/public/showroom'
BASELINE_HASH = '27ee9b3a01a72c46f126e2b706f4fd390e34f739631939d8a957ece24d72be1e'
AHA_HASH = 'a6f94ab8bd9a6af46b70a8f4471fb20fbc32e8271084c54dd53728afeb29768b'
ENTRYPOINTS = {'index.html', 'preview.js', 'preview.css'}
PRESERVED_PACKAGING = {
    'assets/packaging/liaose-pump.glb',
    'assets/packaging/poster-039.glb',
    'assets/packaging/poster-073.glb',
    'assets/packaging/poster-049.glb',
    'assets/packaging/poster-042.glb',
    'assets/packaging/poster-051.glb',
    'assets/packaging/poster-047.glb',
    'assets/packaging/poster-044.glb',
    'assets/packaging/poster-056.glb',
    'assets/packaging/poster-057.glb',
    'assets/packaging/gsap.min.js',
    'assets/packaging/ScrollTrigger.min.js',
}
STAGE = '/opt/yuanze-reference/staging/client1.33-aha-complete-sprayer-20261030.tar.gz'


def digest(data):
    return hashlib.sha256(data).hexdigest()


def plan():
    before = json.loads((HERE / 'server-before.json').read_text())
    new = json.loads((LOCAL / 'bundle-manifest.json').read_text())
    assert before['manifestHash'] == BASELINE_HASH, 'Unexpected concurrent-release baseline'
    assert before['manifest']['version'] == 'client1.32'
    assert 'ActiveState=active' in before['service']
    assert len(before['outsideHashes']) >= 6820
    assert new['version'] == 'client1.33', 'Build the isolated client1.33 first'
    old_files, new_files = before['manifest']['files'], new['files']
    assert len(old_files) == 458 and len(new_files) == 458
    modified = {n for n in old_files.keys() & new_files.keys() if old_files[n] != new_files[n]}
    added = new_files.keys() - old_files.keys()
    removed = old_files.keys() - new_files.keys()
    assert modified == {'index.html', 'preview.js', 'assets/packaging/poster-060.glb'}, sorted(modified)
    new_model = 'assets/packaging/poster-060.glb'
    assert new_files[new_model] == {'bytes': 1111452, 'sha256': AHA_HASH}
    assert sum(n.endswith('.glb') for n in new_files) == 26
    assert sum(n.endswith(('.webp','.png','.svg')) for n in new_files) == 418
    assert added == set(), sorted(added)
    assert removed == set(), sorted(removed)
    assert all(old_files[n]==new_files[n] for n in old_files if n.endswith(('.webp','.png','.svg','.glb')) and n != new_model)
    for number in (74,75,76,77,78):
        assert f'assets/packaging/poster-{number:03}.glb' not in new_files
    for number in range(74,79):
        for suffix in ('.png','-640.webp','-1024.webp'):
            assert f'assets/featured/poster-{number:03}{suffix}' not in new_files
    for name in PRESERVED_PACKAGING: assert old_files[name] == new_files[name]
    immutable = old_files.keys() - modified - removed
    assert all(old_files[n] == new_files.get(n) for n in immutable)
    packaging = sorted(n for n in old_files if (n.endswith('.glb') or n in PRESERVED_PACKAGING) and n != new_model)
    for name, entry in new_files.items():
        path = LOCAL / name
        assert not path.is_symlink() and path.is_file(), f'Invalid local resource: {name}'
        data = path.read_bytes()
        assert len(data) == entry['bytes'] and digest(data) == entry['sha256'], name
    actual = {str(f.relative_to(LOCAL)) for f in LOCAL.rglob('*') if f.is_file()}
    assert actual == set(new_files) | {'bundle-manifest.json'}, 'Unexpected file in local bundle'
    result = {
        'version': 'client1.33', 'baselineManifestSha256': BASELINE_HASH,
        'manifestSha256': digest((LOCAL / 'bundle-manifest.json').read_bytes()),
        'changed': sorted(modified | added), 'added': sorted(added), 'removed': sorted(removed),
        'preservedPackaging': packaging, 'resources': len(new_files),
    }
    return before, new, result


REMOTE_SCRIPT = r'''
import pathlib,json,hashlib,shutil,tarfile,ctypes,os,subprocess,datetime
p=json.loads(PAYLOAD)
root=pathlib.Path('/opt/yuanze-reference/current').resolve()
old=root/'public/showroom'
new=root/'public/showroom-aha-mist-stage'
backup=pathlib.Path('/opt/yuanze-reference/backups/client1.33-aha-complete-sprayer-20261030')
h=lambda f:hashlib.sha256(f.read_bytes()).hexdigest()
def outside():
    return {str(f.relative_to(root)):h(f) for f in root.rglob('*') if f.is_file() and not f.is_symlink() and not f.is_relative_to(old) and not f.is_relative_to(new) and '__pycache__' not in str(f)}
def outside_digest():
    return hashlib.sha256(json.dumps(outside(),sort_keys=True).encode()).hexdigest()
def service():
    return subprocess.check_output(['systemctl','show','yuanze-reference','--property=MainPID,ActiveState']).decode()
def guard():
    assert str(pathlib.Path('/opt/yuanze-reference/current').resolve())==p['current'],'Current release changed'
    assert h(old/'bundle-manifest.json')==p['manifestHash'],'Concurrent showroom changed'
    assert outside_digest()==p['outsideHash'],'Concurrent code changed: merge required'
    assert h(pathlib.Path('/etc/nginx/yuanze-bmt-public.conf'))==p['gatewayHash'],'Gateway changed'
    assert service()==p['service'],'Service identity or active state changed'
def verify(directory, manifest):
    actual={str(f.relative_to(directory)) for f in directory.rglob('*') if f.is_file()}
    assert actual==set(manifest['files'])|{'bundle-manifest.json'},'Unexpected bundle inventory'
    assert not any(f.is_symlink() for f in directory.rglob('*'))
    for name,entry in manifest['files'].items():
        data=(directory/name).read_bytes()
        assert len(data)==entry['bytes'] and hashlib.sha256(data).hexdigest()==entry['sha256'],name
guard()
assert not new.exists() and not backup.exists(),'Inspect previous publication before retry'
old_manifest=json.loads((old/'bundle-manifest.json').read_text())
verify(old,old_manifest)
assert h(pathlib.Path(p['stage']))==p['archiveHash'],'Upload checksum mismatch'
assert old_manifest['version']=='client1.32' and len(old_manifest['files'])==458
assert set(p['changed'])=={'index.html','preview.js','assets/packaging/poster-060.glb'}
assert set(p['added'])==set()
assert set(p['removed'])==set()
shutil.copytree(old,new)
for name in p['removed']:
    (new/name).unlink()
with tarfile.open(p['stage']) as tf:
    members=tf.getmembers()
    expected=set(p['changed'])|{'bundle-manifest.json'}
    assert len(members)==len(expected) and {m.name for m in members}==expected
    for member in members:
        assert member.isfile() and not pathlib.Path(member.name).is_absolute() and '..' not in pathlib.Path(member.name).parts
        target=new/member.name
        target.parent.mkdir(parents=True,exist_ok=True)
        target.write_bytes(tf.extractfile(member).read())
        os.chmod(target,(old/member.name).stat().st_mode&0o777 if (old/member.name).exists() else 0o644)
for target in [new,*new.rglob('*')]:
    previous=old if target==new else old/target.relative_to(new)
    stat=previous.stat() if previous.exists() else old.stat()
    os.chown(target,stat.st_uid,stat.st_gid)
    if target.is_dir():os.chmod(target,stat.st_mode&0o777)
manifest=json.loads((new/'bundle-manifest.json').read_text())
assert manifest['version']=='client1.33' and len(manifest['files'])==458 and h(new/'bundle-manifest.json')==p['newManifestHash']
assert manifest['files']['assets/packaging/poster-060.glb']['sha256']=='a6f94ab8bd9a6af46b70a8f4471fb20fbc32e8271084c54dd53728afeb29768b'
assert set(manifest['files'])==(set(old_manifest['files']) - set(p['removed'])) | set(p['added'])
verify(new,manifest)
assert all(old_manifest['files'][name]==manifest['files'][name] for name in p['preservedPackaging'])
for name,entry in old_manifest['files'].items():
    if name not in p['changed'] and name not in p['removed']:
        assert manifest['files'].get(name)==entry,'Unapproved resource change: '+name
subprocess.run(['runuser','-u','yuanze','--','python3','-c','import pathlib,sys,json;p=pathlib.Path(sys.argv[1]);assert all((p/n).read_bytes() for n in json.loads((p/"bundle-manifest.json").read_text())["files"])',str(new)],check=True)
guard()
lib=ctypes.CDLL(None,use_errno=True)
if lib.renameat2(-100,os.fsencode(old),-100,os.fsencode(new),2):
    raise OSError(ctypes.get_errno(),'Atomic exchange failed')
new.rename(backup)
assert outside_digest()==p['outsideHash']
assert service()==p['service']
assert h(pathlib.Path('/etc/nginx/yuanze-bmt-public.conf'))==p['gatewayHash']
print(json.dumps({
    'version':'client1.33','patch':'approved-aha-060-complete-sprayer-only',
    'publishedAt':datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=8))).isoformat(timespec='seconds'),
    'release':str(root),'manifestSha256':h(old/'bundle-manifest.json'),'backup':str(backup),
    'baselineManifestSha256':p['manifestHash'],'verifiedFiles':len(manifest['files']),
    'changed':p['changed']+['bundle-manifest.json'],'removedChunks':p['removed'],'added':p['added'],
    'preservedPackaging':p['preservedPackaging'],'outsideUnchanged':len(outside()),
    'service':service(),'serviceRestart':False,'businessDataWrites':0,
    'loginManifestSha256':h(root/'public/login-ui/bundle-manifest.json')
}))
'''


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--publish', action='store_true', help='Execute the reviewed guarded remote publication')
    args = parser.parse_args()
    before, new, result = plan()
    (HERE / 'publication-plan.json').write_text(json.dumps(result, indent=2) + '\n')
    if not args.publish:
        print(json.dumps({'localPlanOnly': True, **result}))
        return
    import subprocess, shlex
    def remote(args, **kwargs):
        return subprocess.run(['ssh','-S','/tmp/yuanze-citrus-20261030.sock','-o','BatchMode=yes','root@47.79.233.3', shlex.join(args)], capture_output=True, **kwargs)
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode='w:gz') as tf:
        for name in result['changed'] + ['bundle-manifest.json']:
            tf.add(LOCAL / name, arcname=name)
    archive = buf.getvalue()
    upload = remote(['python3', '-c', 'import sys,pathlib;p=pathlib.Path(sys.argv[1]);assert not p.exists();p.write_bytes(sys.stdin.buffer.read())', STAGE], input=archive, timeout=180)
    assert upload.returncode == 0, upload.stderr.decode()
    payload = {key: before[key] for key in ['current', 'manifestHash', 'gatewayHash', 'service']}
    payload.update(
        stage=STAGE, archiveHash=digest(archive), changed=result['changed'], added=result['added'], removed=result['removed'],
        preservedPackaging=result['preservedPackaging'], newManifestHash=result['manifestSha256'],
        outsideHash=digest(json.dumps(before['outsideHashes'], sort_keys=True).encode()),
    )
    response = remote(['flock', '-w', '10', '/opt/yuanze-reference/deploy.lock', 'python3', '-c',
                       REMOTE_SCRIPT.replace('PAYLOAD', repr(json.dumps(payload)))], timeout=90)
    assert response.returncode == 0, response.stderr.decode()
    (HERE / 'publication.json').write_bytes(response.stdout)
    print(response.stdout.decode())


if __name__ == '__main__':
    main()
