import hashlib
import json
import sqlite3
import pytest
from screenshot_storage import EvidenceVault


HASH = hashlib.sha256(b"original").hexdigest()


def test_evidence_requires_human_review_before_derivatives_or_export():
    vault = EvidenceVault(sqlite3.connect(":memory:"))
    record = vault.request(HASH, "harassment", "user-1")
    with pytest.raises(PermissionError):
        vault.add_derivative(record.evidence_id, HASH, "ocr", "model:v1")
    with pytest.raises(PermissionError):
        vault.export_manifest([record.evidence_id], "user-1")
    approved = vault.review(record.evidence_id, "reviewer-1", True, "confirmed by human review")
    derivative = vault.add_derivative(record.evidence_id, HASH, "redacted", "reviewer-1")
    manifest = vault.export_manifest([approved.evidence_id], "user-1")
    assert derivative and manifest["items"][0]["original_is_immutable"]
    assert manifest["items"][0]["redactions_are_derivatives"]


def test_rejected_evidence_is_never_exportable_and_suggestions_exclude_vault():
    vault = EvidenceVault(sqlite3.connect(":memory:"))
    record = vault.request(HASH, "antisemitism", "user-1")
    vault.review(record.evidence_id, "reviewer-1", False, "insufficient context")
    with pytest.raises(PermissionError):
        vault.export_manifest([record.evidence_id], "user-1")
    candidates = vault.suggestion_candidates([{"sha256": HASH}, {"sha256": "other"}])
    assert candidates == [{"sha256": "other"}]


def test_audit_log_contains_no_original_content():
    vault = EvidenceVault(sqlite3.connect(":memory:"))
    record = vault.request(HASH, "sexism", "user-1")
    audit = vault.db.execute("SELECT action, details FROM evidence_audit WHERE evidence_id=?", (record.evidence_id,)).fetchall()
    assert audit and HASH not in json.dumps(audit)
