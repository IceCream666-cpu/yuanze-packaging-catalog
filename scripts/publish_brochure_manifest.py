#!/usr/bin/env python3
"""Resume-safe, create-only administrator API publication of reviewed manifests."""
import argparse
import base64
import json
import io
import os
import sys
import time
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, wait, FIRST_COMPLETED

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'server-reference/deploy'))
sys.path.insert(0,str(ROOT/'scripts'))
import release_gate as gate

def upload_image(client,image):
    # UploadManager owns the resource gate. Honor explicit 429 responses,
    # without a separate status request for every image or retrying ambiguous IO.
    for attempt in range(30):
        status,headers,body=client.request('/api/admin/uploads',{'image':image})
        if status==201:return json.loads(body)['image']
        if status!=429:raise RuntimeError(f'Upload returned {status}; inspect before resuming')
        delay=min(30,max(2,float(headers.get('Retry-After',2))))
        time.sleep(delay)
    raise TimeoutError('Image service busy; resume later')

def upload_bytes(path):
    # Match the server's 1600px limit before transmission. Original page renders
    # and the PDF remain untouched on disk; this only reduces upload bandwidth.
    from PIL import Image
    with Image.open(path) as image:
        image=image.convert('RGB')
        image.thumbnail((1600,1600),Image.Resampling.LANCZOS)
        buffer=io.BytesIO();image.save(buffer,'JPEG',quality=90,optimize=True)
        return buffer.getvalue()

def save(path,value):
    temp=path.with_suffix('.tmp')
    temp.write_text(json.dumps(value,ensure_ascii=False,indent=2)); temp.chmod(0o600)
    os.replace(temp,path)

def check_existing(existing, entry, digest):
    if digest not in existing.get('sourceNote',''):
        raise ValueError('Existing record ID has another source; refusing overwrite')
    for key in ('model','specificationRaw','materials','category'):
        if existing.get(key)!=entry['record'].get(key):
            raise ValueError('Existing record differs; manual reconciliation required: '+key)
    if not existing.get('images') or any(i.get('clientVisible') for i in existing['images']):
        raise ValueError('Existing image policy differs; manual reconciliation required')

def create_record(client,entry,uploads):
    # Each request has its own HTTP handlers; authentication stays in memory.
    worker=gate.Client(client.origin,180)
    for cookie in client.jar:worker.jar.set_cookie(cookie)
    worker.csrf=client.csrf
    record=dict(entry['record'])
    record['images']=[{'path':uploads[str(p)]['path'],'imageScope':'source_page',
                      'role':'reference','clientVisible':False,
                      'caption':f"鸿昇2608图册 · PDF第{p}页 · 原页参考，可能含其他规格／型号"} for p in entry['pages']]
    status,_,body=worker.request('/api/admin/records',{'action':'save','id':entry['id'],'version':0,'record':record})
    if status!=200: raise RuntimeError(f"Create {entry['id']} returned {status}: "+body.decode()[:300])
    value=json.loads(body)
    return value.get('item',value)

def publish(directory, credentials, origin):
    directory=Path(directory)
    manifest=json.loads((directory/'manifest.json').read_text())
    state_path=directory/'publication.json'
    state=json.loads(state_path.read_text()) if state_path.exists() else {'sha256':manifest['sha256'],'uploads':{},'records':{}}
    assert state['sha256']==manifest['sha256']
    client=gate.Client(origin,90)
    gate.expect_status(client,'/api/login',200,gate.load_credentials(credentials))
    _,body=gate.expect_status(client,'/api/session',200)
    session=json.loads(body); assert session['role']=='admin'; client.csrf=session['csrf']
    try:
        _,body=gate.expect_status(client,'/api/admin/records',200)
        before=json.loads(body); existing={r['id']:r for r in before['items']}
        if not (directory/'publication-before.json').exists(): save(directory/'publication-before.json',before)
        for entry in manifest['records']:
            if entry['id'] in existing: check_existing(existing[entry['id']],entry,manifest['sha256'])
        for i,page in enumerate(manifest['productPages'],1):
            key=str(page)
            if key not in state['uploads']:
                raw=upload_bytes(directory/'pages'/f'{page:04}.jpg')
                state['uploads'][key]=upload_image(client,'data:image/jpeg;base64,'+base64.b64encode(raw).decode())
                save(state_path,state)
            if i%10==0 or i==len(manifest['productPages']): print(f'images {i}/{len(manifest["productPages"])}',flush=True)
        remaining=iter(e for e in manifest['records'] if e['id'] not in existing)
        for entry in manifest['records']:
            if entry['id'] in existing:
                r=existing[entry['id']];state['records'][entry['id']]={'productCode':r.get('productCode'),'version':r.get('version')}
        # At most two in flight. Never queue the whole batch: on failure, only
        # the other in-flight create may finish; resume reads it back first.
        with ThreadPoolExecutor(max_workers=2) as pool:
            pending={}
            def schedule():
                entry=next(remaining,None)
                if entry is not None:pending[pool.submit(create_record,client,entry,state['uploads'])]=entry
            schedule();schedule()
            while pending:
                done,_=wait(pending,return_when=FIRST_COMPLETED)
                results=[(future,pending[future],future.result()) for future in done]
                for future,entry,value in results:
                    pending.pop(future);rid=entry['id'];existing[rid]=value
                    state['records'][rid]={'productCode':value.get('productCode'),'version':value.get('version')}
                    save(state_path,state)
                    n=len(state['records'])
                    if n%10==0 or n==len(manifest['records']):print(f'records {n}/{len(manifest["records"])}',flush=True)
                for _ in results:schedule()
        _,body=gate.expect_status(client,'/api/admin/records',200)
        after=json.loads(body); save(directory/'publication-after.json',after)
        final={r['id']:r for r in after['items']}
        for entry in manifest['records']:
            check_existing(final[entry['id']],entry,manifest['sha256'])
            assert final[entry['id']]['unitPrice'] is None and not final[entry['id']].get('bareBottlePrice')
        baseline=json.loads((directory/'publication-before.json').read_text())['items']
        changed=[r['id'] for r in baseline if final.get(r['id'])!=r]
        state['verification']={'records':len(manifest['records']),'images':len(state['uploads']),
                               'preexistingChanged':changed,'catalogCount':len(final)}
        save(state_path,state)
        if changed: raise RuntimeError('Concurrent existing-record changes detected; preserved, inspect report')
        print(json.dumps(state['verification'],ensure_ascii=False),flush=True)
    finally:
        gate.expect_status(client,'/api/logout',200,{})

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('directory');p.add_argument('--credentials',type=Path,required=True)
    p.add_argument('--origin',default='https://bmt.yuanzebeauty.com');p.add_argument('--publish',action='store_true',required=True)
    args=p.parse_args();publish(args.directory,args.credentials,args.origin)
