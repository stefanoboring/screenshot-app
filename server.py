"""Local HTTP API for the browser MVP; originals are stored by ScreenshotImporter."""
import argparse, json, tempfile
from email.parser import BytesParser
from email.policy import default
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from screenshot_app.ingest import ScreenshotImporter

class Handler(BaseHTTPRequestHandler):
    importer = None
    def do_POST(self):
        if self.path != '/api/ingest': self.send_error(404); return
        try:
            body = self.rfile.read(int(self.headers.get('Content-Length', 0)))
            msg = BytesParser(policy=default).parsebytes(
                f'Content-Type: {self.headers.get("Content-Type")}\r\n\r\n'.encode() + body)
            records = []
            with tempfile.TemporaryDirectory() as tmp:
                for part in msg.iter_attachments():
                    name = Path(part.get_filename() or 'upload.bin').name
                    path = Path(tmp) / name
                    path.write_bytes(part.get_payload(decode=True) or b'')
                    result = self.importer.import_file(path)
                    records.append({'name': name, 'size': path.stat().st_size,
                        'type': part.get_content_type(), 'id': result.stable_id,
                        'hash': f'sha256:{result.sha256}',
                        'provenance': result.source, 'preservation': 'Original locked',
                        'status': 'duplicate' if result.status == 'duplicate' else 'completed'})
            self._json({'records': records})
        except Exception as exc: self._json({'error': str(exc)}, 400)
    def _json(self, value, status=200):
        raw = json.dumps(value).encode(); self.send_response(status)
        self.send_header('Content-Type', 'application/json'); self.send_header('Content-Length', str(len(raw)))
        self.end_headers(); self.wfile.write(raw)
    def log_message(self, *_): pass

if __name__ == '__main__':
    parser = argparse.ArgumentParser(); parser.add_argument('--store', type=Path, default=Path('.screenshot-data')); parser.add_argument('--port', type=int, default=4173)
    args = parser.parse_args(); Handler.importer = ScreenshotImporter(args.store)
    try: ThreadingHTTPServer(('127.0.0.1', args.port), Handler).serve_forever()
    finally: Handler.importer.close()
