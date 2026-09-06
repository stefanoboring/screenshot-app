import hashlib
from datetime import datetime, timezone, timedelta
import pytest
from screenshot_storage import FileSystemStorage, RetentionManager, RetentionPolicy

def test_hash_and_no_overwrite(tmp_path):
    s=FileSystemStorage(tmp_path); digest=s.put("originals", "2026/a.png", b"x")
    assert digest == hashlib.sha256(b"x").hexdigest()
    with pytest.raises(FileExistsError): s.put("originals", "2026/a.png", b"y")
def test_hash_mismatch(tmp_path):
    with pytest.raises(ValueError): FileSystemStorage(tmp_path).put("originals", "a", b"x", sha256="bad")
def test_retention_dry_run_and_hold(tmp_path):
    s=FileSystemStorage(tmp_path); s.put("originals", "old", b"x"); s.put("originals", "held", b"x")
    old=(datetime.now(timezone.utc)-timedelta(days=400)).isoformat()
    r=RetentionManager(s, RetentionPolicy(365, 0)).purge([{"key":"old","captured_at":old},{"key":"held","captured_at":old,"legal_hold":True}], dry_run=True)
    assert len(r)==1 and s.exists("originals","old")
