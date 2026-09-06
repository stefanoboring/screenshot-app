import hashlib
import pytest
from screenshot_storage import EvidenceVault


def test_ingest_preserves_original_and_starts_sensitive_items_in_review(tmp_path):
    vault = EvidenceVault(tmp_path)
    item = vault.ingest(b"sensitive", mime="image/png", classification="denuncia")
    assert item.status == "pending_review"
    assert vault.read_original(item.vault_item_id, actor="reviewer", role="reviewer") == b"sensitive"
    assert item.sha256 == hashlib.sha256(b"sensitive").hexdigest()
    vault.close()


def test_derivative_requires_review_and_correction_is_audited(tmp_path):
    vault = EvidenceVault(tmp_path)
    item = vault.ingest(b"x", mime="image/png", classification="uncertain")
    with pytest.raises(PermissionError):
        vault.approve_derivative(item.vault_item_id, actor="user", review_token="", kind="ocr", data=b"text")
    key = vault.approve_derivative(item.vault_item_id, actor="reviewer", review_token="human-review-1", kind="redaction", data=b"redacted")
    assert vault.storage.exists("derivatives", key)
    vault.correct_classification(item.vault_item_id, "ordinary", actor="reviewer", reason="human review corrected model")
    assert vault.search_metadata(actor="user")[0]["classification"] == "ordinary"
    vault.close()


def test_export_and_delete_need_explicit_confirmation_and_are_revocable(tmp_path):
    vault = EvidenceVault(tmp_path)
    item = vault.ingest(b"x", mime="image/png")
    with pytest.raises(PermissionError):
        vault.request_export(item.vault_item_id, actor="user", recipient="team", purpose="review", expires_at="2099-01-01", confirmed=False)
    export_id, token = vault.request_export(item.vault_item_id, actor="user", recipient="team", purpose="review", expires_at="2099-01-01", confirmed=True)
    assert token
    vault.revoke_export(export_id, actor="user", reason="no longer needed")
    vault.delete(item.vault_item_id, actor="user", confirmed=True, reason="user requested deletion")
    with pytest.raises(PermissionError):
        vault.read_original(item.vault_item_id, actor="user", role="reader")
    vault.close()
