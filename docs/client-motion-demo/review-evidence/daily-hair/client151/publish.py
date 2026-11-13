"""Publish the approved Daily Hair Ritual model and poster and homepage entry.

Default invocation validates the local plan; --publish explicitly writes remotely.
No credentials are stored here. Approved clear-glass model and homepage integration.
"""
from pathlib import Path
import argparse
import hashlib
import importlib.util
import inspect
import io
import json
import re
import shlex
import tarfile

HERE = Path(__file__).resolve().parent
ROOT = Path(__file__).resolve().parents[5]
LOCAL = ROOT / 'server-reference/public/showroom'
BASELINE_HASH = '9488dc44fca4a8d2d023ab339969a3ad1a1f759002a17a8689417d2eeae23b49'
MODEL_HASH = '8dc698ef18f767cd369a6a7c9de670d6058e78c66ec0428dab217c63df1b5132'
STAGE = '/opt/yuanze-reference/staging/client1.51-daily-hair-model-20261113.tar.gz'
ADDED_ASSETS = ['assets/featured/poster-085-1024.webp', 'assets/featured/poster-085-640.webp', 'assets/featured/poster-085.png', 'assets/optimized/poster-085-strip.webp', 'assets/packaging/PackagingDetail-OsDFhrw0.js', 'assets/packaging/packaging-scene-BGnCwcnB.js', 'assets/packaging/poster-085-v2.glb', 'assets/posters/poster-085-thumb.webp', 'assets/posters/poster-085.webp', 'assets/previews/posters/poster-085-1280.webp', 'assets/previews/posters/poster-085-512.webp']
REMOVED = ['assets/packaging/PackagingDetail-B_3DPi1e.js', 'assets/packaging/packaging-scene-Cahxbiuj.js']
APPROVED_MODEL_HASH = 'a5335c7148c715720b1a81b6d181faae07d2e7f1d7e6af648846a1ec28aaea8d'


def digest(data):
    return hashlib.sha256(data).hexdigest()


def plan():
    assert (ROOT / 'AGENTS.md').is_file(), 'Invalid worktree root'
    before = json.loads((HERE / 'server-before.json').read_text())
    new = json.loads((LOCAL / 'bundle-manifest.json').read_text())
    assert before['manifestHash'] == BASELINE_HASH, 'Unexpected baseline'
    assert before['manifest']['version'] == 'client1.50'
    assert 'ActiveState=active' in before['service']
    assert len(before['outsideHashes']) >= 6820
    assert new['version'] == 'client1.51', 'Build and stamp client1.51 first'
    old_files, new_files = before['manifest']['files'], new['files']
    assert len(old_files) == 505 and len(new_files) == 514
    modified = {n for n in old_files.keys() & new_files.keys() if old_files[n] != new_files[n]}
    added, removed = new_files.keys() - old_files.keys(), old_files.keys() - new_files.keys()
    assert modified == {'index.html', 'product-posters.js', 'preview.js'}, sorted(modified)
    assert added == set(ADDED_ASSETS), sorted(added)
    assert removed == set(REMOVED), sorted(removed)
    assert new_files['assets/packaging/poster-081-v1.glb'] == {'bytes': 4527020, 'sha256': MODEL_HASH}
    assert sum(n.endswith('.glb') for n in new_files) == 32
    assert all(old_files[n] == new_files.get(n) for n in old_files if n.endswith(('.glb','.png','.webp','.svg')))
    assert new_files['assets/packaging/poster-085-v2.glb']['sha256'] == APPROVED_MODEL_HASH
    for number in range(74, 79):
        assert not any(f'poster-{number:03}' in n for n in new_files if n.startswith(('assets/packaging/','assets/featured/')))
    featured = json.loads((ROOT/'docs/client-motion-demo/src/featured.json').read_text())
    posters = json.loads((ROOT/'docs/client-motion-demo/src/posters.json').read_text())
    assert len(featured) == 31 and len(posters) == 68
    assert featured[-1]['id'] == 'poster-085'
    assert featured[:-1] == json.loads((HERE/'featured-before.json').read_text())
    for name, entry in new_files.items():
        path = LOCAL / name
        assert not path.is_symlink() and path.is_file(), name
        data = path.read_bytes()
        assert len(data) == entry['bytes'] and digest(data) == entry['sha256'], name
    assert not any(p.is_symlink() for p in LOCAL.rglob('*'))
    assert {str(p.relative_to(LOCAL)) for p in LOCAL.rglob('*') if p.is_file()} == set(new_files) | {'bundle-manifest.json'}
    result = {
        'version':'client1.51', 'baselineManifestSha256':BASELINE_HASH,
        'manifestSha256':digest((LOCAL/'bundle-manifest.json').read_bytes()),
        'changed':sorted(modified | added), 'added':sorted(added), 'removed':sorted(removed),
        'preservedPackaging':sorted(n for n in old_files if n.endswith('.glb')),
        'resources':len(new_files), 'counts':{'posters':68,'featured':31,'models':32},
        'publishedModel':'poster-085', 'featuredAdded':'poster-085',
    }
    return before, new, result


def require_disk_headroom(available_bytes, candidate_bytes):
    """Reserve a complete staging copy and 256 MiB for live session writes."""
    required = candidate_bytes + 256 * 1024 * 1024
    if available_bytes < required:
        raise RuntimeError(f'Insufficient service-user disk space: {available_bytes} available; {required} required')
    return required


REMOTE_SCRIPT = inspect.getsource(require_disk_headroom) + r'''

import pathlib,json,hashlib,shutil,tarfile,ctypes,os,subprocess,datetime
p=json.loads(PAYLOAD)
root=pathlib.Path('/opt/yuanze-reference/current').resolve()
old=root/'public/showroom'
new=root/'public/showroom-daily-hair-client151-stage'
backup=pathlib.Path('/opt/yuanze-reference/backups/client1.51-daily-hair-model-20261113')
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
space=os.statvfs(root)
require_disk_headroom(space.f_bavail*space.f_frsize,p['candidateBytes'])
verify(old,old_manifest)
assert h(pathlib.Path(p['stage']))==p['archiveHash'],'Upload checksum mismatch'
assert old_manifest['version']=='client1.50' and len(old_manifest['files'])==505
assert p['added']==['assets/featured/poster-085-1024.webp', 'assets/featured/poster-085-640.webp', 'assets/featured/poster-085.png', 'assets/optimized/poster-085-strip.webp', 'assets/packaging/PackagingDetail-OsDFhrw0.js', 'assets/packaging/packaging-scene-BGnCwcnB.js', 'assets/packaging/poster-085-v2.glb', 'assets/posters/poster-085-thumb.webp', 'assets/posters/poster-085.webp', 'assets/previews/posters/poster-085-1280.webp', 'assets/previews/posters/poster-085-512.webp']
assert p['removed']==['assets/packaging/PackagingDetail-B_3DPi1e.js', 'assets/packaging/packaging-scene-Cahxbiuj.js']
assert set(p['changed'])-set(p['added'])=={'index.html','product-posters.js','preview.js'}
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
assert manifest['version']=='client1.51' and len(manifest['files'])==514 and h(new/'bundle-manifest.json')==p['newManifestHash']
assert manifest['files']['assets/packaging/poster-081-v1.glb']['sha256']=='8dc698ef18f767cd369a6a7c9de670d6058e78c66ec0428dab217c63df1b5132'
assert sum(n.endswith('.glb') for n in manifest['files'])==32
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
verify(old,manifest)
verify(backup,old_manifest)
assert outside_digest()==p['outsideHash']
assert service()==p['service']
assert h(pathlib.Path('/etc/nginx/yuanze-bmt-public.conf'))==p['gatewayHash']
print(json.dumps({
    'version':'client1.51','patch':'approved-085-poster-model-and-home',
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
    parser.add_argument('--publish', action='store_true')
    args = parser.parse_args()
    before, new, result = plan()
    (HERE/'publication-plan.json').write_text(json.dumps(result, indent=2)+'\n')
    if not args.publish:
        print(json.dumps({'localPlanOnly':True, **result}))
        return
    helper = Path('/private/tmp/yuanze-handgel-ssh.py')
    assert helper.is_file(), 'Restore the authorized local SSH helper before publication'
    spec = importlib.util.spec_from_file_location('authorized_ssh', helper)
    ssh = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(ssh)
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode='w:gz') as tf:
        for name in result['changed'] + ['bundle-manifest.json']:
            tf.add(LOCAL/name, arcname=name)
    archive = buf.getvalue()
    disk_check = inspect.getsource(require_disk_headroom) + '\nimport os;v=os.statvfs("/opt/yuanze-reference");require_disk_headroom(v.f_bavail*v.f_frsize,' + str(len(archive) + sum(e['bytes'] for e in new['files'].values()) + (LOCAL/'bundle-manifest.json').stat().st_size) + ')'
    capacity = ssh.remote(shlex.join(['python3','-c',disk_check]), timeout=30)
    assert capacity.returncode == 0, capacity.stderr.decode()
    upload_code = 'import sys,pathlib;p=pathlib.Path(sys.argv[1]);assert p.parent.is_dir() and not p.exists();p.write_bytes(sys.stdin.buffer.read())'
    upload = ssh.remote(shlex.join(['python3','-c',upload_code,STAGE]), input=archive, timeout=180)
    assert upload.returncode == 0, 'Upload failed; inspect local stderr without sharing secrets'
    payload = {key: before[key] for key in ['current','manifestHash','gatewayHash','service']}
    payload.update(candidateBytes=sum(e['bytes'] for e in new['files'].values()) + (LOCAL/'bundle-manifest.json').stat().st_size, stage=STAGE, archiveHash=digest(archive), changed=result['changed'], added=result['added'], removed=result['removed'], preservedPackaging=result['preservedPackaging'], newManifestHash=result['manifestSha256'], outsideHash=digest(json.dumps(before['outsideHashes'], sort_keys=True).encode()))
    response = ssh.remote(shlex.join(['flock','-w','10','/opt/yuanze-reference/deploy.lock','python3','-c',REMOTE_SCRIPT.replace('PAYLOAD',repr(json.dumps(payload)))]), timeout=180)
    assert response.returncode == 0, response.stderr.decode()
    (HERE/'publication.json').write_bytes(response.stdout)
    print(response.stdout.decode())


if __name__ == '__main__':
    main()
