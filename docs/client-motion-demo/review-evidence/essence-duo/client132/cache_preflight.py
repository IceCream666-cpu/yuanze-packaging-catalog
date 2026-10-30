from pathlib import Path
import json,subprocess
HERE=Path(__file__).resolve().parent
script=r"""import pathlib,json,hashlib
root=pathlib.Path('/opt/yuanze-reference/current').resolve();model=root/'public/showroom/assets/packaging/poster-059.glb'
b=model.read_bytes();stat=model.stat();h=hashlib.sha256(b).hexdigest()
assert h=='fd0ad9a323a5aad51982236bba6be5c80a868af50f773d1518d671f2c16fdcf5'
etag='"'+hashlib.sha256(f'{model}:{stat.st_size}:{stat.st_mtime_ns}:{stat.st_ino}'.encode()).hexdigest()[:32]+'"'
print(json.dumps({'path':str(model),'etag':etag,'bytes':len(b),'sha256':h}))
"""
r=subprocess.run(['ssh','-S','/tmp/yuanze-citrus-20261030.sock','-o','BatchMode=yes','root@47.79.233.3','python3 -'],input=script.encode(),capture_output=True,timeout=30)
assert r.returncode==0,r.stderr.decode();(HERE/'model-cache-before.json').write_bytes(r.stdout)
print('Captured approved old059 ETag for post-publication revalidation.')
