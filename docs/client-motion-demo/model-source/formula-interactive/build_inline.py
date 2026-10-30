"""Package each 3D preview into a self-contained sandbox fragment below 1 MB."""
from pathlib import Path
import base64,gzip,json,re,sys
here=Path(__file__).resolve().parent
out=Path(sys.argv[1]);dest=Path(sys.argv[2]);dest.mkdir(parents=True,exist_ok=True)
standalone=(out/'交互式料体3D.html').read_text()
script=re.search(r'<script type="module">(.*?)</script>',standalone,re.S).group(1)
compressed=base64.b64encode(gzip.compress(script.encode())).decode()
for key,id,title in [('oil','body-oil-collection','身体油 02'),('daily','daily-emulsion','日常乳液')]:
 raw=(out/(id+'-filled-demo.glb')).read_bytes();data=base64.b64encode(gzip.compress(raw)).decode();assert gzip.decompress(base64.b64decode(data))==raw
 html=(here/'inline-template.html').read_text().replace('__NAME__',title).replace('__MODELS__',json.dumps({key:data})).replace('__SCRIPT__',compressed)
 assert len(html.encode())<1_000_000,(id,len(html.encode()))
 assert '<!doctype' not in html and '<body' not in html and '__SCRIPT__' not in html
 (dest/('liaose-'+key+'-interactive.html')).write_text(html)
 print(id,len(html.encode()),'bytes; embedded original GLB validated')
