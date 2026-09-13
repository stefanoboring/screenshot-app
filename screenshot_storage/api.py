"""Small dependency-free HTTP API for the MVP ingestion contract."""
import json
import os
import re
import uuid
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

from .storage import FileSystemStorage, sha256_bytes

MAX_FILE_BYTES = 25 * 1024 * 1024

class ImportService:
    def __init__(self, root: str):
        self.storage = FileSystemStorage(root)
        self.manifests = Path(root).resolve() / "manifests"

    def upload(self, files):
        results = []
        for name, content, content_type in files:
            if not name or not content or len(content) > MAX_FILE_BYTES:
                results.append({"name": name or "", "status": "failed", "error": "invalid file"})
                continue
            digest = sha256_bytes(content)
            import_id = str(uuid.uuid4())
            key = f"{digest[:2]}/{digest}"
            now = datetime.now(timezone.utc).isoformat()
            duplicate = self.storage.exists("originals", key)
            status = "duplicate" if duplicate else "processing"
            if not duplicate:
                try:
                    self.storage.put("originals", key, content, sha256=digest)
                    status = "completed"
                except FileExistsError:
                    status = "duplicate"
            item = {"id": import_id, "name": name, "type": content_type or "application/octet-stream", "size": len(content), "sha256": digest, "timestamp": now, "status": status, "original_key": key}
            self.manifests.mkdir(parents=True, exist_ok=True)
            (self.manifests / f"{import_id}.json").write_text(json.dumps(item), encoding="utf-8")
            results.append(item)
        return results

    def get(self, import_id):
        path = self.manifests / f"{import_id}.json"
        if not path.is_file(): return None
        return json.loads(path.read_text(encoding="utf-8"))

class Handler(BaseHTTPRequestHandler):
    service = None
    def _json(self, status, payload):
        raw = json.dumps(payload).encode(); self.send_response(status); self.send_header("Content-Type", "application/json"); self.send_header("Content-Length", str(len(raw))); self.end_headers(); self.wfile.write(raw)
    def do_POST(self):
        if urlparse(self.path).path != "/imports": return self._json(404, {"error": "not found"})
        try:
            content_type = self.headers.get("Content-Type", "")
            match = re.search(r"boundary=(?:\"([^\"]+)\"|([^;]+))", content_type)
            if not match: return self._json(400, {"error": "multipart/form-data boundary is required"})
            raw = self.rfile.read(int(self.headers.get("Content-Length", "0"))); boundary = (match.group(1) or match.group(2)).encode()
            files = []
            for part in raw.split(b"--" + boundary):
                if b"filename=" not in part: continue
                header, separator, content = part.partition(b"\r\n\r\n")
                if not separator: continue
                filename_match = re.search(rb'filename="([^"]*)"', header); type_match = re.search(rb"Content-Type:\s*([^\r\n]+)", header, re.I)
                if filename_match: files.append((filename_match.group(1).decode("utf-8", "replace"), content.rstrip(b"\r\n-"), (type_match.group(1).decode() if type_match else "application/octet-stream")))
            if not files: return self._json(400, {"error": "multipart field 'files' is required"})
            return self._json(201, {"imports": self.service.upload(files)})
        except (ValueError, OSError) as exc: return self._json(400, {"error": str(exc)})
    def do_GET(self):
        parts = urlparse(self.path).path.strip("/").split("/")
        if len(parts) == 2 and parts[0] == "imports":
            item = self.service.get(parts[1]); return self._json(200, item) if item else self._json(404, {"error": "import not found"})
        return self._json(404, {"error": "not found"})
    def log_message(self, *_): pass

def serve(host="127.0.0.1", port=8080, root=None):
    Handler.service = ImportService(root or os.getenv("SCREENSHOT_STORAGE_ROOT", "./data"))
    server = ThreadingHTTPServer((host, port), Handler)
    print(f"Screenshot API listening on http://{host}:{port}")
    server.serve_forever()
