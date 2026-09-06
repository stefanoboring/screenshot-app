import hashlib, json, os
from pathlib import Path
from typing import BinaryIO

ZONES = frozenset(("originals", "derivatives", "sensitive", "manifests", "audit"))
def sha256_bytes(data: bytes) -> str: return hashlib.sha256(data).hexdigest()

class FileSystemStorage:
    """Local adapter. Originals are write-once; paths cannot escape root."""
    def __init__(self, root: str): self.root = Path(root).resolve()
    def _path(self, zone, key):
        if zone not in ZONES or not key or Path(key).is_absolute() or ".." in Path(key).parts: raise ValueError("invalid storage key")
        return self.root / zone / key
    def put(self, zone: str, key: str, data: bytes | BinaryIO, *, sha256: str | None = None, overwrite=False) -> str:
        path = self._path(zone, key)
        if zone == "originals" and path.exists() and not overwrite: raise FileExistsError(key)
        raw = data.read() if hasattr(data, "read") else data
        digest = sha256_bytes(raw)
        if sha256 and digest != sha256: raise ValueError("sha256 mismatch")
        path.parent.mkdir(parents=True, exist_ok=True)
        if path.exists() and not overwrite: raise FileExistsError(key)
        path.write_bytes(raw)
        return digest
    def get(self, zone, key) -> bytes: return self._path(zone, key).read_bytes()
    def exists(self, zone, key) -> bool: return self._path(zone, key).exists()
    def delete(self, zone, key, *, dry_run=True) -> bool:
        path = self._path(zone, key)
        if path.exists() and not dry_run: path.unlink()
        return path.exists()

class S3Storage:
    """S3-compatible adapter; inject a boto-style client for production."""
    def __init__(self, client, bucket: str, prefix=""): self.client, self.bucket, self.prefix = client, bucket, prefix.strip("/")
    def put(self, zone, key, data, *, sha256=None, overwrite=False):
        raw = data.read() if hasattr(data, "read") else data
        digest = sha256_bytes(raw)
        if sha256 and digest != sha256: raise ValueError("sha256 mismatch")
        name = "/".join(x for x in (self.prefix, zone, key) if x)
        if zone == "originals" and not overwrite:
            try: self.client.head_object(Bucket=self.bucket, Key=name); raise FileExistsError(key)
            except Exception as exc:
                if isinstance(exc, FileExistsError): raise
        self.client.put_object(Bucket=self.bucket, Key=name, Body=raw, Metadata={"sha256": digest}, ACL="private")
        return digest
