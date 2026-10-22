"""Copy only current approved showroom poster assets into the loopback demo."""
from pathlib import Path
import json, shutil, hashlib
import re
from PIL import Image
BASE=Path(__file__).resolve().parent
ROOT=BASE.parents[1]
SOURCE=ROOT/'docs/mobile-client-preview'
raw=(SOURCE/'product-posters.js').read_text()
data=json.loads(raw[raw.index('{'):].strip().rstrip(';'))
ids=[item['id'] for item in data['items']]
if not ids or len(set(ids))!=len(ids) or any(not re.fullmatch(r'poster-\d{3}',value) for value in ids):
 raise ValueError('Expected unique canonical poster identities')
approved={f"assets/{entry['path']}":entry for entry in json.loads((SOURCE/'assets/manifest.json').read_text())['files']}
styles={51:'natural',47:'natural',52:'natural',54:'natural',42:'natural',43:'natural',45:'natural',49:'clear',44:'clear',55:'clear',53:'bold',46:'clear',9:'bold',36:'bold',12:'bold',13:'bold',11:'bold',39:'clear',4:'natural'}
styles.update({56:'natural',57:'clear',58:'natural',59:'natural',60:'clear',61:'natural',62:'clear',63:'natural',64:'natural',65:'natural',66:'natural',67:'natural',68:'clear',69:'natural',70:'natural'})
first=[51,42,44,47,52,46,53,43,54,55]
items=sorted(data['items'],key=lambda x:first.index(int(x['id'].split('-')[-1])) if int(x['id'].split('-')[-1]) in first else 100+int(x['id'].split('-')[-1]))
records=[]; manifest=[]
derivatives=json.loads((BASE/'display-derivatives.json').read_text())
derivative_by_target={entry['productionTarget']:entry for entry in derivatives['files']}
def copy_asset(src,name):
 src=src.resolve(); route=src.relative_to(SOURCE.resolve()).as_posix()
 raw=src.read_bytes(); entry=approved[route]
 if hashlib.sha256(raw).hexdigest()!=entry['sha256'] or len(raw)!=entry['bytes']:
  raise ValueError(f'Original no longer matches the approved source: {route}')
 dst=BASE/'public/assets'/name; dst.parent.mkdir(parents=True,exist_ok=True)
 shutil.copyfile(src,dst)
 manifest.append({'source':'server-reference/public/showroom/'+route,'target':'assets/'+name,'sha256':entry['sha256'],'bytes':entry['bytes']})
 return '/assets/'+name
def copy_derivative(target,name):
 entry=derivative_by_target[target]
 src=BASE/entry['file']
 data=src.read_bytes()
 if hashlib.sha256(data).hexdigest()!=entry['sha256'] or len(data)!=entry['bytes']:
  raise ValueError(f'Display derivative does not match reviewed manifest: {name}')
 if entry['approvedSourceSha256']!=approved[entry['approvedSource']]['sha256']:
  raise ValueError(f'Display derivative no longer matches approved original: {name}')
 dst=BASE/'public/assets'/name; dst.parent.mkdir(parents=True,exist_ok=True)
 shutil.copyfile(src,dst)
 manifest.append({'source':'server-reference/public/showroom/'+target,'target':'assets/'+name,'sha256':entry['sha256'],'bytes':entry['bytes']})
 return '/assets/'+name
def dimensions(path):
 with Image.open(path) as image:
  return image.size
for item in items:
 n=int(item['id'].split('-')[-1]); stem=item['id']
 original=SOURCE/item['src'].removeprefix('/showroom/')
 preview=SOURCE/f'assets/previews/posters/{stem}-1280.webp'
 if not preview.exists(): preview=original
 thumb=SOURCE/item['thumbnail'].removeprefix('/showroom/')
 small=SOURCE/f'assets/previews/posters/{stem}-512.webp'
 if not small.exists(): small=thumb
 image_width,image_height=dimensions(preview)
 small_width,small_height=dimensions(small)
 strip=derivative_by_target[f'assets/optimized/{stem}-strip.webp']
 records.append({'id':stem,'title':item['title'],'category':item['category'],'style':styles.get(n,'unclassified'),'image':copy_asset(preview,stem+'.webp'),'imageWidth':image_width,'imageHeight':image_height,'smallImage':copy_asset(small,stem+'-small.webp'),'smallWidth':small_width,'smallHeight':small_height,'thumb':copy_asset(thumb,stem+'-thumb.webp'),'stripThumb':copy_derivative(strip['productionTarget'],stem+'-strip.webp'),'stripWidth':strip['width'],'stripHeight':strip['height'],'original':copy_asset(original,stem+'-original.webp'),'width':item['width'],'height':item['height']})
copy_asset(SOURCE/'assets/yuanze-mark.svg','yuanze-mark.svg')
copy_derivative('assets/optimized/yuanze-mark-compact.webp','yuanze-mark-compact.webp')
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
featured=json.loads((BASE/'src/featured.json').read_text())
featured_ids=[item['id'] for item in featured]
if (len(set(featured_ids))!=len(featured_ids) or not set(featured_ids)<=set(ids)
    or sorted(entry['posterId'] for entry in featured_manifest['files'])!=sorted(featured_ids)):
 raise ValueError('Featured approval must exactly match unique current catalogue products')
for item in featured:
 src=BASE/'featured-assets'/f"{item['id']}.png"
 if not src.is_file():
  raise FileNotFoundError(f'Missing featured cutout: {src.name}')
 entry=next(record for record in featured_manifest['files'] if record['posterId']==item['id'])
 if hashlib.sha256(src.read_bytes()).hexdigest()!=entry['sha256'] or src.stat().st_size!=entry['bytes']:
  raise ValueError(f'Featured cutout does not match reviewed derivative: {src.name}')
 shutil.copyfile(src,featured_dir/src.name)
print(f'Prepared {len(featured)} derived product cutouts for the design preview.')

featured_media=json.loads((BASE/'src/featured-media.json').read_text())
if set(featured_media)!=set(featured_ids):
 raise ValueError('Optimized featured media must exactly match current featured products')
for entry in featured_media.values():
 for file in entry['files'].values():
  src=BASE/file['file']
  if hashlib.sha256(src.read_bytes()).hexdigest()!=file['sha256'] or src.stat().st_size!=file['bytes']:
   raise ValueError(f'Optimized featured media checksum mismatch: {src.name}')
  shutil.copyfile(src,featured_dir/src.name)
