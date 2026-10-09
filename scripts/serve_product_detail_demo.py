#!/usr/bin/env python3
"""Serve the isolated product-detail design on loopback, without live APIs."""
import argparse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[1]
DEMO = ROOT / 'docs/product-detail-demo'
SAMPLE = ROOT / 'work/packaging-batch-20261006/round4/images/image19.png'
ROUTES = {
    '/': (DEMO / 'index.html', 'text/html; charset=utf-8'),
    '/index.html': (DEMO / 'index.html', 'text/html; charset=utf-8'),
    '/demo.css': (DEMO / 'demo.css', 'text/css; charset=utf-8'),
    '/demo.js': (DEMO / 'demo.js', 'text/javascript; charset=utf-8'),
    '/brand.svg': (ROOT / 'server-reference/public/brand/yuanze-mark.svg', 'image/svg+xml'),
    '/sample.png': (SAMPLE, 'image/png'),
}


class DemoHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.respond(body=True)

    def do_HEAD(self):
        self.respond(body=False)

    def respond(self, body):
        route = ROUTES.get(urlsplit(self.path).path)
        if route is None or not route[0].is_file():
            self.send_error(404)
            return
        path, content_type = route
        data = path.read_bytes()
        self.send_response(200)
        self.send_header('Content-Type', content_type)
        self.send_header('Content-Length', str(len(data)))
        self.send_header('Cache-Control', 'no-store')
        self.send_header('X-Content-Type-Options', 'nosniff')
        self.send_header('Referrer-Policy', 'no-referrer')
        self.send_header('Content-Security-Policy', "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self'; connect-src 'none'; object-src 'none'; base-uri 'none'; frame-ancestors 'none'")
        self.end_headers()
        if body:
            self.wfile.write(data)

    def log_message(self, format, *args):
        pass


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--port', type=int, default=8901)
    args = parser.parse_args()
    if not SAMPLE.is_file():
        raise SystemExit('Local demo image is missing; restore the approved image19.png sample first.')
    server = ThreadingHTTPServer(('127.0.0.1', args.port), DemoHandler)
    print(f'Product detail demo: http://127.0.0.1:{args.port}/', flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == '__main__':
    main()
