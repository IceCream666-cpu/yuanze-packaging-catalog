from pathlib import Path
import subprocess,json,hashlib
here=Path(__file__).resolve().parent
ssh=['ssh','-S','/tmp/yuanze-citrus-20261030.sock','-o','BatchMode=yes','root@47.79.233.3']
script='''import pathlib,hashlib,json,subprocess
root=pathlib.Path('/opt/yuanze-reference/current').resolve();s=root/'public/showroom';h=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
outside={str(f.relative_to(root)):h(f) for f in root.rglob('*') if f.is_file() and not f.is_symlink() and not f.is_relative_to(s) and '__pycache__' not in str(f)}
assert subprocess.run(['nginx','-t'],capture_output=True).returncode==0
print(json.dumps({'current':str(root),'manifest':json.loads((s/'bundle-manifest.json').read_text()),'manifestHash':h(s/'bundle-manifest.json'),'outsideHashes':outside,'owner':[s.stat().st_uid,s.stat().st_gid],'gatewayHash':h(pathlib.Path('/etc/nginx/yuanze-bmt-public.conf')),'service':subprocess.check_output(['systemctl','show','yuanze-reference','--property=MainPID,ActiveState']).decode()}))'''
r=subprocess.run(ssh+['python3 -'],input=script.encode(),capture_output=True,timeout=60);assert r.returncode==0,r.stderr.decode();(here/'server-before.json').write_bytes(r.stdout)
b=json.loads(r.stdout)
print({k:b[k] for k in ('current','manifestHash','service')});print('version',b['manifest']['version'],'files',len(b['manifest']['files']))
assert b['manifest']['version']=='client1.32'
assert b['manifestHash']=='27ee9b3a01a72c46f126e2b706f4fd390e34f739631939d8a957ece24d72be1e'
assert len(b['manifest']['files'])==458
assert 'ActiveState=active' in b['service']
