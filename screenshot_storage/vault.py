"""Isolated, metadata-first evidence vault primitives.

The vault deliberately has no OCR/embedding implementation. Derivatives are
explicitly opt-in and require a human review token before they can be written.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
import hashlib
import json
from pathlib import Path
import secrets
import sqlite3
from typing import Any

from .storage import FileSystemStorage


@dataclass(frozen=True)
class VaultItem:
    vault_item_id: str
    sha256: str
    size: int
    mime: str
    classification: str
    status: str
    policy_version: str
    retention_expires_at: str


class EvidenceVault:
    """Filesystem MVP for an isolated evidence vault.

    Production deployments should provide encrypted/WORM storage and a KMS
    backed adapter. This class still enforces the application-level boundaries
    and audit gates locally, without claiming filesystem encryption.
    """

    def __init__(self, root: str | Path, *, retention_days: int = 365, policy_version: str = "vault-mvp-1"):
        self.root = Path(root)
        self.storage = FileSystemStorage(self.root / "objects")
        self.db = sqlite3.connect(self.root / "vault.sqlite3")
        self.db.row_factory = sqlite3.Row
        self.retention_days = retention_days
        self.policy_version = policy_version
        self.db.executescript("""
            CREATE TABLE IF NOT EXISTS items (
                vault_item_id TEXT PRIMARY KEY, sha256 TEXT UNIQUE NOT NULL,
                size INTEGER NOT NULL, mime TEXT NOT NULL, classification TEXT NOT NULL,
                status TEXT NOT NULL, policy_version TEXT NOT NULL,
                captured_at TEXT, ingested_at TEXT NOT NULL,
                retention_expires_at TEXT NOT NULL, deleted_at TEXT
            );
            CREATE TABLE IF NOT EXISTS audit (
                event_id TEXT PRIMARY KEY, event_at TEXT NOT NULL, actor TEXT NOT NULL,
                action TEXT NOT NULL, item_id TEXT, decision TEXT NOT NULL,
                reason TEXT, details TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS exports (
                export_id TEXT PRIMARY KEY, item_id TEXT NOT NULL,
                recipient TEXT NOT NULL, purpose TEXT NOT NULL,
                expires_at TEXT NOT NULL, status TEXT NOT NULL,
                token_hash TEXT NOT NULL
            );
        """)
        self.db.commit()

    def _audit(self, actor: str, action: str, decision: str, *, item_id: str | None = None,
               reason: str = "", **details: Any) -> None:
        self.db.execute(
            "INSERT INTO audit VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (secrets.token_hex(16), datetime.now(timezone.utc).isoformat(), actor,
             action, item_id, decision, reason, json.dumps(details, sort_keys=True)),
        )
        self.db.commit()

    def ingest(self, data: bytes, *, mime: str, classification: str = "denuncia",
               captured_at: str | None = None, actor: str = "system") -> VaultItem:
        """Persist bytes first, including uncertain classifications, without derivatives."""
        digest = hashlib.sha256(data).hexdigest()
        existing = self.db.execute("SELECT * FROM items WHERE sha256 = ? AND deleted_at IS NULL", (digest,)).fetchone()
        if existing:
            self._audit(actor, "ingest_duplicate", "allowed", item_id=existing["vault_item_id"], sha256=digest)
            return VaultItem(*(existing[key] for key in ("vault_item_id", "sha256", "size", "mime", "classification", "status", "policy_version", "retention_expires_at")))
        item_id = digest
        self.storage.put("originals", item_id, data, sha256=digest)
        now = datetime.now(timezone.utc)
        expires = now + timedelta(days=self.retention_days)
        status = "pending_review" if classification in {"uncertain", "sexism", "antisemitism", "denuncia"} else "committed"
        self.db.execute("INSERT INTO items VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, NULL)",
                        (item_id, digest, len(data), mime, classification, status, self.policy_version,
                         captured_at, now.isoformat(), expires.isoformat()))
        self.db.commit()
        self._audit(actor, "ingest_committed", "allowed", item_id=item_id, status=status, sha256=digest)
        return VaultItem(item_id, digest, len(data), mime, classification, status, self.policy_version, expires.isoformat())

    def search_metadata(self, *, actor: str, classification: str | None = None) -> list[dict[str, Any]]:
        """Search metadata only; content and derivatives are never returned."""
        if not actor:
            self._audit("anonymous", "metadata_search", "denied", reason="missing_actor")
            raise PermissionError("vault access denied")
        query = "SELECT vault_item_id, sha256, size, mime, classification, status, policy_version, retention_expires_at FROM items WHERE deleted_at IS NULL"
        args: list[str] = []
        if classification:
            query += " AND classification = ?"
            args.append(classification)
        rows = [dict(row) for row in self.db.execute(query, args)]
        self._audit(actor, "metadata_search", "allowed", count=len(rows))
        return rows

    def read_original(self, item_id: str, *, actor: str, role: str = "reader") -> bytes:
        if role not in {"reader", "reviewer", "exporter", "admin"}:
            self._audit(actor, "original_read", "denied", item_id=item_id, reason="role_denied")
            raise PermissionError("vault access denied")
        row = self.db.execute("SELECT sha256, deleted_at FROM items WHERE vault_item_id = ?", (item_id,)).fetchone()
        if not row or row["deleted_at"]:
            self._audit(actor, "original_read", "denied", item_id=item_id, reason="not_available")
            raise PermissionError("vault access denied")
        raw = self.storage.get("originals", item_id)
        if hashlib.sha256(raw).hexdigest() != row["sha256"]:
            self._audit(actor, "integrity_mismatch", "denied", item_id=item_id)
            raise IOError("original integrity check failed")
        self._audit(actor, "original_read", "allowed", item_id=item_id)
        return raw

    def approve_derivative(self, item_id: str, *, actor: str, review_token: str, kind: str, data: bytes) -> str:
        if not review_token or not kind or kind not in {"redaction", "ocr", "thumbnail", "embedding"}:
            self._audit(actor, "derivative_write", "denied", item_id=item_id, reason="explicit_review_required")
            raise PermissionError("explicit human review required")
        row = self.db.execute("SELECT deleted_at FROM items WHERE vault_item_id = ?", (item_id,)).fetchone()
        if not row or row["deleted_at"]:
            raise KeyError(item_id)
        key = f"{item_id}/{kind}-{hashlib.sha256(data).hexdigest()}"
        self.storage.put("derivatives", key, data)
        self._audit(actor, "derivative_write", "allowed", item_id=item_id, kind=kind, review_token=review_token)
        return key

    def correct_classification(self, item_id: str, classification: str, *, actor: str, reason: str) -> None:
        if not reason:
            raise ValueError("correction reason is required")
        cur = self.db.execute("UPDATE items SET classification = ?, status = 'reviewed' WHERE vault_item_id = ? AND deleted_at IS NULL", (classification, item_id))
        if cur.rowcount != 1:
            raise KeyError(item_id)
        self.db.commit()
        self._audit(actor, "classification_corrected", "allowed", item_id=item_id, reason=reason, classification=classification)

    def request_export(self, item_id: str, *, actor: str, recipient: str, purpose: str,
                       expires_at: str, confirmed: bool = False) -> tuple[str, str]:
        if not confirmed or not recipient or not purpose:
            self._audit(actor, "export_request", "denied", item_id=item_id, reason="explicit_confirmation_required")
            raise PermissionError("explicit export confirmation required")
        if not self.db.execute("SELECT 1 FROM items WHERE vault_item_id = ? AND deleted_at IS NULL", (item_id,)).fetchone():
            raise KeyError(item_id)
        export_id, token = secrets.token_hex(12), secrets.token_urlsafe(24)
        self.db.execute("INSERT INTO exports VALUES (?, ?, ?, ?, ?, 'active', ?)",
                        (export_id, item_id, recipient, purpose, expires_at, hashlib.sha256(token.encode()).hexdigest()))
        self.db.commit()
        self._audit(actor, "export_created", "allowed", item_id=item_id, export_id=export_id, recipient=recipient, expires_at=expires_at)
        return export_id, token

    def revoke_export(self, export_id: str, *, actor: str, reason: str) -> None:
        cur = self.db.execute("UPDATE exports SET status = 'revoked' WHERE export_id = ? AND status = 'active'", (export_id,))
        if cur.rowcount != 1:
            raise KeyError(export_id)
        self.db.commit()
        self._audit(actor, "export_revoked", "allowed", reason=reason, export_id=export_id)

    def delete(self, item_id: str, *, actor: str, confirmed: bool = False, reason: str = "") -> None:
        if not confirmed or not reason:
            self._audit(actor, "delete", "denied", item_id=item_id, reason="explicit_confirmation_required")
            raise PermissionError("explicit deletion confirmation required")
        now = datetime.now(timezone.utc).isoformat()
        cur = self.db.execute("UPDATE items SET deleted_at = ?, status = 'tombstoned' WHERE vault_item_id = ? AND deleted_at IS NULL", (now, item_id))
        if cur.rowcount != 1:
            raise KeyError(item_id)
        self.db.commit()
        self._audit(actor, "delete_tombstone", "allowed", item_id=item_id, reason=reason)

    def close(self) -> None:
        self.db.close()
