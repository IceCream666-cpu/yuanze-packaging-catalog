"""Copy only current approved showroom poster assets into the loopback demo."""
from pathlib import Path
import json, shutil, hashlib
from PIL import Image
BASE=Path(__file__).resolve().parent
ROOT=BASE.parents[1]
SHOWROOM=ROOT/'server-reference/public/showroom'
raw=(SHOWROOM/'product-posters.js').read_text()
data=json.loads(raw[raw.index('{'):].strip().rstrip(';'))
styles={51:'natural',47:'natural',52:'natural',54:'natural',42:'natural',43:'natural',45:'natural',49:'clear',44:'clear',55:'clear',53:'bold',46:'clear',9:'bold',36:'bold',12:'bold',13:'bold',11:'bold',39:'clear',4:'natural'}
first=[51,42,44,47,52,46,53,43,54,55]
items=sorted(data['items'],key=lambda x:first.index(int(x['id'].split('-')[-1])) if int(x['id'].split('-')[-1]) in first else 100+int(x['id'].split('-')[-1]))
records=[]; manifest=[]
derivatives=json.loads((BASE/'display-derivatives.json').read_text())
derivative_by_target={entry['productionTarget']:entry for entry in derivatives['files']}
def copy_asset(src,name):
 src=src.resolve(); src.relative_to(SHOWROOM.resolve())
 dst=BASE/'public/assets'/name; dst.parent.mkdir(parents=True,exist_ok=True)
 shutil.copyfile(src,dst)
 manifest.append({'source':str(src.relative_to(ROOT)),'target':'assets/'+name,'sha256':hashlib.sha256(src.read_bytes()).hexdigest(),'bytes':src.stat().st_size})
 return '/assets/'+name
def copy_derivative(target,name):
 entry=derivative_by_target[target]
 src=BASE/entry['file']
 data=src.read_bytes()
 if hashlib.sha256(data).hexdigest()!=entry['sha256'] or len(data)!=entry['bytes']:
  raise ValueError(f'Display derivative does not match reviewed manifest: {name}')
 dst=BASE/'public/assets'/name; dst.parent.mkdir(parents=True,exist_ok=True)
 shutil.copyfile(src,dst)
 manifest.append({'source':'server-reference/public/showroom/'+target,'target':'assets/'+name,'sha256':entry['sha256'],'bytes':entry['bytes']})
 return '/assets/'+name
def dimensions(path):
 with Image.open(path) as image:
  return image.size
for item in items:
 n=int(item['id'].split('-')[-1]); stem=item['id']
 original=SHOWROOM/item['src'].removeprefix('/showroom/')
 preview=SHOWROOM/f'assets/previews/posters/{stem}-1280.webp'
 if not preview.exists(): preview=original
 thumb=SHOWROOM/item['thumbnail'].removeprefix('/showroom/')
 small=SHOWROOM/f'assets/previews/posters/{stem}-512.webp'
 if not small.exists(): small=thumb
 image_width,image_height=dimensions(preview)
 small_width,small_height=dimensions(small)
 strip=derivative_by_target[f'assets/optimized/{stem}-strip.webp']
 records.append({'id':stem,'title':item['title'],'category':item['category'],'style':styles.get(n,'unclassified'),'image':copy_asset(preview,stem+'.webp'),'imageWidth':image_width,'imageHeight':image_height,'smallImage':copy_asset(small,stem+'-small.webp'),'smallWidth':small_width,'smallHeight':small_height,'thumb':copy_asset(thumb,stem+'-thumb.webp'),'stripThumb':copy_derivative(strip['productionTarget'],stem+'-strip.webp'),'stripWidth':strip['width'],'stripHeight':strip['height'],'original':copy_asset(original,stem+'-original.webp'),'width':item['width'],'height':item['height']})
copy_asset(SHOWROOM/'assets/yuanze-mark.svg','yuanze-mark.svg')
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
for item in json.loads((BASE/'src/featured.json').read_text()):
 src=BASE/'featured-assets'/f"{item['id']}.png"
 if not src.is_file():
  raise FileNotFoundError(f'Missing featured cutout: {src.name}')
 entry=next(record for record in featured_manifest['files'] if record['posterId']==item['id'])
 if hashlib.sha256(src.read_bytes()).hexdigest()!=entry['sha256']:
  raise ValueError(f'Featured cutout does not match reviewed derivative: {src.name}')
 shutil.copyfile(src,featured_dir/src.name)
print('Prepared 8 derived product cutouts for the design preview.')

for entry in json.loads((BASE/'src/featured-media.json').read_text()).values():
 for file in entry['files'].values():
  src=BASE/file['file']
  assert hashlib.sha256(src.read_bytes()).hexdigest()==file['sha256']
  shutil.copyfile(src,featured_dir/src.name)
