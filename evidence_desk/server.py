"""Small, loopback-only demo server. No uploads, credentials, CORS or external actions."""
from __future__ import annotations
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from urllib.parse import urlsplit
from .core import ROOT, run_query, load_corpus
from .evaluation import evaluate

MAX_BODY = 4096
ASSETS = {'/': ('index.html','text/html; charset=utf-8'), '/app.js': ('app.js','text/javascript; charset=utf-8'), '/style.css': ('style.css','text/css; charset=utf-8')}


class Handler(BaseHTTPRequestHandler):
    server_version = 'EvidenceDesk/0.1'

    def _allowed(self) -> bool:
        port = self.server.server_address[1]
        hosts = {f'127.0.0.1:{port}', f'localhost:{port}'}
        if self.headers.get('Host') not in hosts:
            self._json(403, {'error':'Invalid local Host'})
            return False
        origin = self.headers.get('Origin')
        if origin is not None and origin not in {f'http://{h}' for h in hosts}:
            self._json(403, {'error':'Cross-origin requests are not supported'})
            return False
        return True

    def _send(self, status: int, body: bytes, content_type: str) -> None:
        self.send_response(status)
        self.send_header('Content-Type', content_type)
        self.send_header('Content-Length', str(len(body)))
        self.send_header('Cache-Control', 'no-store')
        self.send_header('X-Content-Type-Options','nosniff')
        self.send_header('Content-Security-Policy', "default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; connect-src 'self'; object-src 'none'; frame-ancestors 'none'; base-uri 'none'; form-action 'self'")
        self.end_headers()
        self.wfile.write(body)

    def _json(self, status: int, data: dict) -> None:
        self._send(status, json.dumps(data, allow_nan=False).encode(), 'application/json; charset=utf-8')

    def do_GET(self) -> None:
        if not self._allowed():
            return
        path = urlsplit(self.path).path
        if path in ASSETS:
            file, kind = ASSETS[path]
            self._send(200, (ROOT/'evidence_desk'/'web'/file).read_bytes(), kind)
        elif path == '/api/corpus':
            self._json(200, {'documents':[d.public() for d in load_corpus()]})
        elif path == '/api/evaluation':
            self._json(200, evaluate())
        elif path == '/api/health':
            self._json(200, {'status':'ok', 'mode':'offline-deterministic', 'version':'0.1.0'})
        else:
            self._json(404, {'error':'Not found'})

    def do_POST(self) -> None:
        if not self._allowed():
            return
        if urlsplit(self.path).path != '/api/ask':
            self._json(404, {'error':'Not found'})
            return
        if self.headers.get('Content-Type','').split(';')[0] != 'application/json':
            self._json(415, {'error':'Use application/json'})
            return
        try:
            length = int(self.headers.get('Content-Length','0'))
            if length <= 0 or length > MAX_BODY or self.headers.get('Transfer-Encoding'):
                self._json(413, {'error':'Request must be 1–4096 bytes without transfer encoding'})
                return
            self.connection.settimeout(5)
            raw = self.rfile.read(length)
            data = json.loads(raw)
            if not isinstance(data, dict) or set(data) - {'entity','question','as_of'}:
                raise ValueError('Expected entity, question and optional as_of')
            if 'as_of' in data and not isinstance(data['as_of'], str):
                raise ValueError('as_of must be an ISO date string')
            result = run_query(data.get('entity',''), data.get('question',''), as_of=data.get('as_of','2026-10-01'))
            self._json(200, result)
        except (ValueError, TypeError, UnicodeDecodeError, TimeoutError) as exc:
            self._json(400, {'error':str(exc)})

    def log_message(self, fmt: str, *args) -> None:
        pass  # Avoid logging source or request data in this demo.


def serve_local(port: int) -> None:
    if not 1 <= port <= 65535:
        raise ValueError('Port must be 1–65535')
    server = ThreadingHTTPServer(('127.0.0.1', port), Handler)
    print(f'Evidence Desk: http://127.0.0.1:{port}\nSynthetic offline prototype. Ctrl+C to stop.', flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
