"""Loopback-only build comparison. Uses showroom assets, no accounts or business data."""
from pathlib import Path
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlsplit, unquote
import argparse, gzip, hashlib

ROOT=Path(__file__).resolve().parents[4]
PUBLIC=ROOT/'server-reference/public/showroom'

class Handler(SimpleHTTPRequestHandler):
    def log_message(self,*args): pass
    def do_GET(self):
        path=unquote(urlsplit(self.path).path)
        if path=='/api/session':
            return self.reply(b'{"role":"client","username":"local-preview","csrf":"local-only"}', 'application/json', cache=False)
        if path in ('/','/client'): path='/showroom/index.html'
        if not path.startswith('/showroom/') or '..' in path.split('/') or '\\' in path:
            return self.send_error(404)
        name=path.removeprefix('/showroom/')
        target=PUBLIC/name
        # Reuse identical HTML/media. Only built JS/CSS may differ between trials.
        if self.server.candidate and name!='index.html' and (self.server.candidate/name).is_file():
            target=self.server.candidate/name
        if not target.is_file() or target.suffix not in {'.html','.js','.css','.webp','.png','.svg','.glb'}: return self.send_error(404)
        self.reply(target.read_bytes(),self.guess_type(str(target)))
    def reply(self,data,mime,cache=True):
        etag='"'+hashlib.sha256(data).hexdigest()+'"'
        status=304 if cache and self.headers.get('If-None-Match')==etag else 200
        encoded=False
        if status==200 and ('gzip' in self.headers.get('Accept-Encoding','')) and (mime.startswith(('text/','application/javascript','model/')) or mime=='application/octet-stream'):
            data=gzip.compress(data,compresslevel=6,mtime=0);encoded=True
        self.send_response(status); self.send_header('Content-Type',mime)
        self.send_header('Cache-Control','private, no-cache' if cache else 'no-store')
        self.send_header('ETag',etag);self.send_header('Vary','Accept-Encoding')
        if encoded:self.send_header('Content-Encoding','gzip')
        self.send_header('Content-Length',str(len(data) if status==200 else 0));self.end_headers()
        if status==200:
            try:self.wfile.write(data)
            except (BrokenPipeError,ConnectionResetError):pass

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--port',type=int,required=True);p.add_argument('--candidate',type=Path);args=p.parse_args()
    assert (PUBLIC/'bundle-manifest.json').is_file()
    server=ThreadingHTTPServer(('127.0.0.1',args.port),Handler);server.candidate=args.candidate
    print(f'Local comparison: http://127.0.0.1:{args.port}/client',flush=True);server.serve_forever()
