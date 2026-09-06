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

def test_storage_zones_are_separate(tmp_path):
    s = FileSystemStorage(tmp_path)
    for zone in ("originals", "derivatives", "sensitive", "manifests", "audit"):
        s.put(zone, "2026/item", zone.encode())
        assert s.get(zone, "2026/item") == zone.encode()
        assert (tmp_path / zone / "2026/item").is_file()
    assert sorted(p.name for p in tmp_path.iterdir()) == ["audit", "derivatives", "manifests", "originals", "sensitive"]

def test_retention_honors_grace_period_and_legal_hold(tmp_path):
    s = FileSystemStorage(tmp_path)
    s.put("originals", "within-grace", b"x")
    s.put("originals", "expired", b"x")
    s.put("originals", "held", b"x")
    now = datetime.now(timezone.utc)
    objects = [
        {"key": "within-grace", "captured_at": (now - timedelta(days=370)).isoformat()},
        {"key": "expired", "captured_at": (now - timedelta(days=400)).isoformat()},
        {"key": "held", "captured_at": (now - timedelta(days=400)).isoformat(), "legal_hold": True},
    ]
    manager = RetentionManager(s, RetentionPolicy(365, 30))
    result = manager.purge(objects, now=now, dry_run=True)
    assert [item["key"] for item in result] == ["expired"]
    assert s.exists("originals", "within-grace") and s.exists("originals", "held")
    manager.purge(objects, now=now, dry_run=False)
    assert not s.exists("originals", "expired")
def test_retention_dry_run_and_hold(tmp_path):
    s=FileSystemStorage(tmp_path); s.put("originals", "old", b"x"); s.put("originals", "held", b"x")
    old=(datetime.now(timezone.utc)-timedelta(days=400)).isoformat()
    r=RetentionManager(s, RetentionPolicy(365, 0)).purge([{"key":"old","captured_at":old},{"key":"held","captured_at":old,"legal_hold":True}], dry_run=True)
    assert len(r)==1 and s.exists("originals","old")
