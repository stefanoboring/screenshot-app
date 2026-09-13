import json
import threading
from http.client import HTTPConnection
from http.server import ThreadingHTTPServer
from screenshot_storage.api import Handler, ImportService

def test_upload_hash_duplicate_and_get(tmp_path):
    Handler.service = ImportService(str(tmp_path)); server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True); thread.start(); host, port = server.server_address
    body = b'--x\r\nContent-Disposition: form-data; name="files"; filename="a.png"\r\nContent-Type: image/png\r\n\r\nbytes\r\n--x--\r\n'
    headers = {"Content-Type": "multipart/form-data; boundary=x", "Content-Length": str(len(body))}
    try:
        conn = HTTPConnection(host, port); conn.request("POST", "/imports", body, headers); response = conn.getresponse(); payload = json.loads(response.read()); assert response.status == 201
        item = payload["imports"][0]; assert item["status"] == "completed"; assert len(item["sha256"]) == 64
        conn.request("POST", "/imports", body, headers); duplicate = json.loads(conn.getresponse().read())["imports"][0]; assert duplicate["status"] == "duplicate"
        conn.request("GET", f"/imports/{item['id']}"); fetched = json.loads(conn.getresponse().read()); assert fetched["sha256"] == item["sha256"]
    finally: server.shutdown(); thread.join()
