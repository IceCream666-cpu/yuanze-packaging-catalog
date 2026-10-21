"""Copy only current approved showroom poster assets into the loopback demo."""
from pathlib import Path
import json, shutil, hashlib
BASE=Path(__file__).resolve().parent
ROOT=BASE.parents[1]
SHOWROOM=ROOT/'server-reference/public/showroom'
raw=(SHOWROOM/'product-posters.js').read_text()
data=json.loads(raw[raw.index('{'):].strip().rstrip(';'))
styles={51:'natural',47:'natural',52:'natural',54:'natural',42:'natural',43:'natural',45:'natural',49:'clear',44:'clear',55:'clear',53:'bold',46:'clear',9:'bold',36:'bold',12:'bold',13:'bold',11:'bold',39:'clear',4:'natural'}
first=[51,42,44,47,52,46,53,43,54,55]
items=sorted(data['items'],key=lambda x:first.index(int(x['id'].split('-')[-1])) if int(x['id'].split('-')[-1]) in first else 100+int(x['id'].split('-')[-1]))
records=[]; manifest=[]
def copy_asset(src,name):
 src=src.resolve(); src.relative_to(SHOWROOM.resolve())
 dst=BASE/'public/assets'/name; dst.parent.mkdir(parents=True,exist_ok=True)
 shutil.copyfile(src,dst)
 manifest.append({'source':str(src.relative_to(ROOT)),'target':'assets/'+name,'sha256':hashlib.sha256(src.read_bytes()).hexdigest(),'bytes':src.stat().st_size})
 return '/assets/'+name
for item in items:
 n=int(item['id'].split('-')[-1]); stem=item['id']
 original=SHOWROOM/item['src'].removeprefix('/showroom/')
 preview=SHOWROOM/f'assets/previews/posters/{stem}-1280.webp'
 if not preview.exists(): preview=original
 thumb=SHOWROOM/item['thumbnail'].removeprefix('/showroom/')
 records.append({'id':stem,'title':item['title'],'category':item['category'],'style':styles.get(n,'unclassified'),'image':copy_asset(preview,stem+'.webp'),'thumb':copy_asset(thumb,stem+'-thumb.webp'),'original':copy_asset(original,stem+'-original.webp'),'width':item['width'],'height':item['height']})
copy_asset(SHOWROOM/'assets/yuanze-mark.svg','yuanze-mark.svg')
(BASE/'src/posters.json').write_text(json.dumps(records,ensure_ascii=False,indent=2)+'\n')
(BASE/'assets-manifest.json').write_text(json.dumps({'scope':'local-demo-only','styleTags':'editorial proposal, not product properties','count':len(records),'files':manifest},ensure_ascii=False,indent=2)+'\n')
(BASE/'src/asset-paths.json').write_text(json.dumps({
 '/'+item['target']:'/showroom/'+item['source'].split('public/showroom/')[1]
 for item in manifest
},indent=2)+'\n')
print(f'Prepared {len(records)} approved posters and original logo; source pixels unchanged.')
featured_dir=BASE/'public/featured'
featured_dir.mkdir(parents=True,exist_ok=True)
featured_manifest=json.loads((BASE/'featured-manifest.json').read_text())
for item in json.loads((BASE/'src/featured.json').read_text()):
 src=BASE/'featured-assets'/f"{item['id']}.png"
 if not src.is_file():
  raise FileNotFoundError(f'Missing featured cutout: {src.name}')
 entry=next(record for record in featured_manifest['files'] if record['posterId']==item['id'])
 if hashlib.sha256(src.read_bytes()).hexdigest()!=entry['sha256']:
  raise ValueError(f'Featured cutout does not match reviewed derivative: {src.name}')
 shutil.copyfile(src,featured_dir/src.name)
print('Prepared 8 derived product cutouts for the design preview.')
