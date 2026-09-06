"""Explicit opt-in sensitive-evidence vault.

The vault stores metadata only in SQLite; binary originals and derivatives stay
in separate storage zones. A classification never grants access by itself.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import json
import sqlite3
import uuid


SENSITIVE_LABELS = frozenset(("sexism", "antisemitism", "harassment", "discrimination"))


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass(frozen=True)
class EvidenceRecord:
    evidence_id: str
    original_hash: str
    label: str
    status: str
    created_at: str
    reviewer_id: str | None


class EvidenceVault:
    """SQLite-backed policy boundary for restricted evidence workflows."""

    def __init__(self, db: sqlite3.Connection):
        self.db = db
        self.db.executescript("""
        CREATE TABLE IF NOT EXISTS evidence (
            evidence_id TEXT PRIMARY KEY, original_hash TEXT NOT NULL,
            label TEXT NOT NULL, status TEXT NOT NULL,
            created_at TEXT NOT NULL, reviewer_id TEXT, rationale TEXT
        );
        CREATE TABLE IF NOT EXISTS evidence_derivatives (
            derivative_id TEXT PRIMARY KEY, evidence_id TEXT NOT NULL,
            source_hash TEXT NOT NULL, kind TEXT NOT NULL, creator TEXT NOT NULL,
            created_at TEXT NOT NULL,
            FOREIGN KEY(evidence_id) REFERENCES evidence(evidence_id)
        );
        CREATE TABLE IF NOT EXISTS evidence_audit (
            event_id TEXT PRIMARY KEY, evidence_id TEXT, actor_id TEXT NOT NULL,
            action TEXT NOT NULL, details TEXT NOT NULL, created_at TEXT NOT NULL
        );
        """)
        self.db.commit()

    def _audit(self, evidence_id, actor_id, action, details=None):
        self.db.execute("INSERT INTO evidence_audit VALUES (?, ?, ?, ?, ?, ?)",
                        (str(uuid.uuid4()), evidence_id, actor_id, action,
                         json.dumps(details or {}, sort_keys=True), _now()))

    def request(self, original_hash: str, label: str, actor_id: str) -> EvidenceRecord:
        if label not in SENSITIVE_LABELS:
            raise ValueError("unsupported sensitive label")
        if not original_hash or len(original_hash) != 64:
            raise ValueError("original_hash must be a SHA-256 digest")
        evidence_id = str(uuid.uuid4())
        created = _now()
        self.db.execute("INSERT INTO evidence VALUES (?, ?, ?, 'pending_review', ?, NULL, NULL)",
                        (evidence_id, original_hash, label, created))
        self._audit(evidence_id, actor_id, "vault_requested", {"label": label})
        self.db.commit()
        return EvidenceRecord(evidence_id, original_hash, label, "pending_review", created, None)

    def review(self, evidence_id: str, reviewer_id: str, approved: bool, rationale: str) -> EvidenceRecord:
        row = self.db.execute("SELECT original_hash, label, created_at FROM evidence WHERE evidence_id = ?",
                              (evidence_id,)).fetchone()
        if not row:
            raise KeyError(evidence_id)
        status = "approved" if approved else "rejected"
        self.db.execute("UPDATE evidence SET status=?, reviewer_id=?, rationale=? WHERE evidence_id=?",
                        (status, reviewer_id, rationale, evidence_id))
        self._audit(evidence_id, reviewer_id, "human_review", {"approved": approved, "rationale": rationale})
        self.db.commit()
        return EvidenceRecord(evidence_id, row[0], row[1], status, row[2], reviewer_id)

    def add_derivative(self, evidence_id: str, source_hash: str, kind: str, creator: str) -> str:
        status = self.db.execute("SELECT status FROM evidence WHERE evidence_id=?", (evidence_id,)).fetchone()
        if not status or status[0] != "approved":
            raise PermissionError("derivatives require approved evidence")
        derivative_id = str(uuid.uuid4())
        self.db.execute("INSERT INTO evidence_derivatives VALUES (?, ?, ?, ?, ?, ?)",
                        (derivative_id, evidence_id, source_hash, kind, creator, _now()))
        self._audit(evidence_id, creator, "derivative_added", {"derivative_id": derivative_id, "kind": kind})
        self.db.commit()
        return derivative_id

    def export_manifest(self, evidence_ids: list[str], actor_id: str) -> dict:
        if not evidence_ids:
            raise ValueError("at least one evidence id is required")
        placeholders = ",".join("?" for _ in evidence_ids)
        rows = self.db.execute(f"SELECT evidence_id, original_hash, label, status FROM evidence WHERE evidence_id IN ({placeholders})", evidence_ids).fetchall()
        if len(rows) != len(set(evidence_ids)) or any(r[3] != "approved" for r in rows):
            raise PermissionError("only approved evidence can be exported")
        manifest = {"manifest_version": 1, "export_id": str(uuid.uuid4()), "created_at": _now(),
                    "requested_by": actor_id, "items": [{"evidence_id": r[0], "original_sha256": r[1],
                    "label": r[2], "original_is_immutable": True, "redactions_are_derivatives": True} for r in rows]}
        for evidence_id in evidence_ids:
            self._audit(evidence_id, actor_id, "export_manifest_created", {"export_id": manifest["export_id"]})
        self.db.commit()
        return manifest

    def suggestion_candidates(self, records):
        """Exclude every vault item from ordinary suggestions by stable hash/id."""
        hashes = {row[0] for row in self.db.execute("SELECT original_hash FROM evidence")}
        return [record for record in records if record.get("sha256") not in hashes and not record.get("evidence_id")]
