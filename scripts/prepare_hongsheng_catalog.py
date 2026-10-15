#!/usr/bin/env python3
"""Source-specific, auditable brochure import. Never infer prices or convert g to mL."""
import argparse
import hashlib
import json
import re
import shutil
from pathlib import Path

MODEL = re.compile(r'HSX?\d{3,4}\b', re.I)
PAIRS = {44:43, 63:62, 74:73, 93:92, 102:101, 120:121, 139:140, 145:146}
SKIP = {1,2,178,*PAIRS.values()}
JARS = {6,9,18,26,27,51,154,160,164,173}
TUBES = {30,31,57}
OVERRIDES = {9:['HS0116'], 82:['HS0215','HS0216'], 177:['HSX001','HSX002']}

def block(lines, start, end):
    for i,line in enumerate(lines):
        if re.search(start,line,re.I):
            tail=[]
            for value in lines[i:]:
                if tail and re.search(end,value,re.I): break
                tail.append(value)
            return ' '.join(tail)
    return ''

def extract(page, companion=None):
    n=page['page']
    lines=[x['text'] for x in page['lines']]
    model_lines=page['lines'] + (companion['lines'] if companion else [])
    models=list(dict.fromkeys(m.upper() for row in model_lines for m in MODEL.findall(row['text'])))
    models=OVERRIDES.get(n,models)
    material=block(lines,r'材质|Material',r'容量|Capacity|Specifications|规格')
    capacity=block(lines,r'容量|Capacity',r'规格|Specifications|PLASTIC|^HS')
    # Two OCR slash/l confusions verified on the source pages.
    capacity=capacity.replace('750m/','750ml/').replace('150m/','150ml/')
    caps=re.findall(r'(\d+(?:\.\d+)?)\s*(ml|g)\b',capacity,re.I)
    mats=re.findall(r'HDPE|PETG|PETE|PET|PP|PE',material.upper())
    if len(caps)==1: caps*=len(models)
    if len(mats)==1: mats*=len(models)
    if not models or len(models)!=len(caps) or len(models)!=len(mats):
        raise ValueError(f'Page {n}: ambiguous mapping models={models}, caps={caps}, materials={mats}')
    spec=block(lines,r'规格|Specif',r'PLASTIC|^HS|^\d{1,3}$')
    spec=re.sub(r'^.*?[:：]','',spec).strip()
    specs=re.findall(r'\d+(?:\.\d+)?牙(?:\s*/?\s*\d+(?:\.\d+)?克)?',spec)
    rows=[]
    for i,(model,(amount,unit),mat) in enumerate(zip(models,caps,mats)):
        category='罐' if n in JARS or model=='HS0212' else '软管' if n in TUBES else '瓶'
        unit='mL' if unit.lower()=='ml' else 'g'
        row={'model':model,'material':mat,'specification':amount+unit,
             'capacityMl':float(amount) if unit=='mL' else None,'category':category,
             'pages':sorted([n]+([companion['page']] if companion else [])),
             'evidence':'\n'.join([material,capacity,spec]),
             'neckWeight':specs[i] if len(specs)==len(models) else '',
             'uncertainties':['图册识别参数，采购前请与供应商复核；图片为原页参考，尚未逐款裁切。']}
        if n==9: row['uncertainties'].append('按图册容量栏200g录入；场景瓶贴350ml与容量栏不一致，待供应商确认。')
        if n==122: row['uncertainties'].append('原页4款仅列出3组重量，未擅自分配重量。')
        rows.append(row)
    return rows

def prepare(directory, source):
    directory=Path(directory); source=Path(source)
    digest=hashlib.sha256(source.read_bytes()).hexdigest()
    pages={p:json.loads((directory/'pages'/f'{p:04}.json').read_text()) for p in range(1,179)}
    indexed={}
    for n,page in pages.items():
        if n in SKIP: continue
        for row in extract(page,pages.get(PAIRS.get(n))):
            key=(row['model'],row['material'],row['specification'])
            if key in indexed:
                old=indexed[key]
                old['pages']=sorted(set(old['pages']+row['pages']))
                old['evidence']+='\n补充页：'+row['evidence']
                if row['neckWeight']: old['neckWeight']=row['neckWeight']
            else: indexed[key]=row
    records=[]
    for row in indexed.values():
        note=f"{source.name}；PDF第{','.join(map(str,row['pages']))}页；SHA256:{digest}"
        details=[]
        if row['neckWeight']:
            details=[{'label':'口径／克重（图册原文）','value':row['neckWeight'],'evidence':note}]
        record={'kind':'package','name':f"鸿昇 {row['model']} {row['category']} {row['specification']}",
                'model':row['model'],'category':row['category'],'materials':[row['material']],
                'materialRaw':row['material'],'specificationRaw':row['specification'],
                'capacityMl':row['capacityMl'],'supplierRaw':'广州市鸿昇包材',
                'sourceNote':note,'remarksRaw':row['evidence'],'productDetails':details,
                'uses':[],'referenceUses':[],'unitPrice':None,'bareBottlePrice':'',
                'quoteRaw':'','moqRaw':'','leadTimeRaw':'','uncertainties':row['uncertainties']}
        records.append({'id':f"HS2608-{row['model']}-{row['specification']}",'pages':row['pages'],'record':record})
    covered=sorted({p for r in records for p in r['pages']})
    assert covered==list(range(3,178)), 'Product page coverage incomplete'
    archive=directory/source.name
    if source.resolve()!=archive.resolve(): shutil.copy2(source,archive)
    result={'source':source.name,'sha256':digest,'pageCount':178,'productPages':covered,
            'records':records,'imagePolicy':'Original brochure pages; clientVisible=false; source_page'}
    (directory/'manifest.json').write_text(json.dumps(result,ensure_ascii=False,indent=2))
    return result

if __name__=='__main__':
    parser=argparse.ArgumentParser(); parser.add_argument('directory'); parser.add_argument('source')
    args=parser.parse_args(); result=prepare(args.directory,args.source)
    print(json.dumps({'records':len(result['records']),'productPages':len(result['productPages']),
                     'models':len({r['record']['model'] for r in result['records']})}))
