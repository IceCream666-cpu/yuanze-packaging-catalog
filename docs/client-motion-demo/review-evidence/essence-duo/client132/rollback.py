"""Guarded rollback of client1.32 only; default prints the retained rollback plan."""
from pathlib import Path
import argparse,hashlib,json,shlex,subprocess
HERE=Path(__file__).resolve().parent
before=json.loads((HERE/'server-before.json').read_text())
published=json.loads((HERE/'publication.json').read_text())
payload={key:before[key] for key in ['current','manifestHash','gatewayHash','service']}
payload.update(backup=published['backup'],newManifest=published['manifestSha256'],outsideHash=hashlib.sha256(json.dumps(before['outsideHashes'],sort_keys=True).encode()).hexdigest())
parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--rollback',action='store_true');args=parser.parse_args()
if not args.rollback:
 print(json.dumps({'localPlanOnly':True,'backup':payload['backup'],'requiresCurrentManifest':payload['newManifest'],'restoresManifest':payload['manifestHash']}));raise SystemExit(0)
script=r'''
import pathlib,json,hashlib,subprocess,ctypes,os
p=json.loads(PAYLOAD);root=pathlib.Path('/opt/yuanze-reference/current').resolve();live=root/'public/showroom';backup=pathlib.Path(p['backup'])
h=lambda f:hashlib.sha256(f.read_bytes()).hexdigest()
assert str(root)==p['current']
assert str(backup)=='/opt/yuanze-reference/backups/client1.32-essence-complete-droppers-20261030'
assert h(live/'bundle-manifest.json')==p['newManifest'],'Later deployment exists; do not overwrite it'
assert h(backup/'bundle-manifest.json')==p['manifestHash'],'Rollback baseline differs'
outside={str(f.relative_to(root)):h(f) for f in root.rglob('*') if f.is_file() and not f.is_symlink() and not f.is_relative_to(live) and '__pycache__' not in str(f)}
assert hashlib.sha256(json.dumps(outside,sort_keys=True).encode()).hexdigest()==p['outsideHash']
assert h(pathlib.Path('/etc/nginx/yuanze-bmt-public.conf'))==p['gatewayHash']
assert subprocess.check_output(['systemctl','show','yuanze-reference','--property=MainPID,ActiveState']).decode()==p['service']
for directory in [live,backup]:
 manifest=json.loads((directory/'bundle-manifest.json').read_text())
 assert not any(f.is_symlink() for f in directory.rglob('*'))
 assert {str(f.relative_to(directory)) for f in directory.rglob('*') if f.is_file()}==set(manifest['files'])|{'bundle-manifest.json'}
 for name,entry in manifest['files'].items():
  data=(directory/name).read_bytes();assert len(data)==entry['bytes'] and hashlib.sha256(data).hexdigest()==entry['sha256']
lib=ctypes.CDLL(None,use_errno=True)
if lib.renameat2(-100,os.fsencode(live),-100,os.fsencode(backup),2):raise OSError(ctypes.get_errno(),'Atomic rollback exchange failed')
assert h(live/'bundle-manifest.json')==p['manifestHash']
print(json.dumps({'rolledBack':True,'restoredManifest':p['manifestHash'],'retainedNewRelease':str(backup)}))
'''
command=['flock','-w','10','/opt/yuanze-reference/deploy.lock','python3','-c',script.replace('PAYLOAD',repr(json.dumps(payload)))]
r=subprocess.run(['ssh','-S','/tmp/yuanze-citrus-20261030.sock','-o','BatchMode=yes','root@47.79.233.3',shlex.join(command)],capture_output=True,timeout=60)
assert r.returncode==0,r.stderr.decode();(HERE/'rollback-result.json').write_bytes(r.stdout);print(r.stdout.decode())
