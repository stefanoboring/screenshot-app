"""Byte-preserving, idempotent screenshot batch ingestion."""
from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import shutil
import sqlite3

@dataclass(frozen=True)
class ImportResult:
    stable_id: str
    source: str
    status: str
    sha256: str
    original_path: str

class ScreenshotImporter:
    """Stores originals separately from metadata/derivatives; never overwrites bytes."""
    def __init__(self, root: str | Path):
        self.root = Path(root)
        self.originals = self.root / "originals"
        self.derivatives = self.root / "derivatives"
        self.originals.mkdir(parents=True, exist_ok=True)
        self.derivatives.mkdir(parents=True, exist_ok=True)
        self.db = sqlite3.connect(self.root / "manifest.sqlite3")
        self.db.execute("""CREATE TABLE IF NOT EXISTS screenshots (
            stable_id TEXT PRIMARY KEY, sha256 TEXT UNIQUE NOT NULL, source TEXT NOT NULL,
            source_mtime REAL, captured_at TEXT, imported_at TEXT NOT NULL,
            original_path TEXT NOT NULL, size INTEGER NOT NULL)""")
        self.db.commit()

    def import_file(self, path: str | Path, captured_at: str | None = None) -> ImportResult:
        source = Path(path)
        if not source.is_file():
            raise FileNotFoundError(source)
        digest = hashlib.sha256(source.read_bytes()).hexdigest()
        existing = self.db.execute("SELECT stable_id, original_path, source FROM screenshots WHERE sha256 = ?", (digest,)).fetchone()
        if existing:
            return ImportResult(existing[0], existing[2], "duplicate", digest, existing[1])
        stable_id = digest  # content-addressed: stable across retries and machines
        target = self.originals / f"{stable_id}{source.suffix.lower()}"
        shutil.copyfile(source, target)  # copyfile preserves bytes, not metadata
        now = datetime.now(timezone.utc).isoformat()
        self.db.execute("INSERT INTO screenshots VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (stable_id, digest, str(source), source.stat().st_mtime, captured_at, now, str(target), target.stat().st_size))
        self.db.commit()
        return ImportResult(stable_id, str(source), "imported", digest, str(target))

    def import_batch(self, paths: list[str | Path], captured_at: str | None = None) -> list[ImportResult]:
        return [self.import_file(path, captured_at) for path in paths]

    def close(self):
        self.db.close()
