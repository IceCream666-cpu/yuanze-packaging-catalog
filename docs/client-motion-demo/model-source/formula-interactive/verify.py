"""Validate the packaged preview, embedded models and executable module syntax."""
import base64,gzip,json,re,struct,subprocess,sys
from pathlib import Path
out,fragments=map(Path,sys.argv[1:3]);node='/Users/icecream/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/bin/node'
for key,id in [('oil','body-oil-collection'),('daily','daily-emulsion')]:
 html=(fragments/f'liaose-{key}-interactive.html').read_text();assert len(html.encode())<1_000_000
 data=json.loads(re.search(r'<script id="models" type="application/json">(.*?)</script>',html,re.S).group(1));assert set(data)=={key}
 raw=gzip.decompress(base64.b64decode(data[key]));assert raw==(out/f'{id}-filled-demo.glb').read_bytes()
 size=struct.unpack_from('<I',raw,12)[0];doc=json.loads(raw[20:20+size]);assert 'Formula' in {n.get('name') for n in doc['nodes']};assert all('uri' not in image for image in doc['images'])
 js=gzip.decompress(base64.b64decode(re.search(r"atob\('([^']+)'\)",html).group(1))).decode()
 subprocess.run([node,'--input-type=module','--check'],input=js,text=True,check=True)
 assert not re.search(r'<(?:script|img)[^>]+src=["\']https?://',html)
 print(key,'PASS: original embedded model, standalone scripts, module syntax, <1 MB')
