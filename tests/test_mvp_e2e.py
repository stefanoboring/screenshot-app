"""End-to-end regression coverage for the currently delivered MVP workflow.

These tests deliberately exercise the public ingestion/storage APIs together:
source bytes -> immutable original -> manifest/provenance -> isolated zones.
"""
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from screenshot_app import ScreenshotImporter
from screenshot_storage import FileSystemStorage


def test_batch_import_is_byte_preserving_and_provenance_stable(tmp_path: Path):
    source_dir = tmp_path / "captures"
    source_dir.mkdir()
    payloads = {"event.png": b"png\x00bytes", "book.jpg": b"jpeg\xffbytes"}
    for name, payload in payloads.items():
        (source_dir / name).write_bytes(payload)

    importer = ScreenshotImporter(tmp_path / "store")
    results = importer.import_batch(sorted(source_dir.iterdir()), "2026-09-06T10:00:00+00:00")

    assert [result.status for result in results] == ["imported", "imported"]
    for result in results:
        assert Path(result.original_path).read_bytes() == payloads[Path(result.source).name]
        row = importer.db.execute(
            "SELECT stable_id, sha256, source, captured_at, original_path "
            "FROM screenshots WHERE stable_id = ?", (result.stable_id,)
        ).fetchone()
        assert row == (result.stable_id, result.sha256, result.source,
                       "2026-09-06T10:00:00+00:00", result.original_path)
    importer.close()


def test_duplicate_retry_keeps_first_original_and_manifest_row(tmp_path: Path):
    source = tmp_path / "capture.png"
    source.write_bytes(b"same content")
    importer = ScreenshotImporter(tmp_path / "store")

    first = importer.import_file(source)
    source.write_bytes(b"same content")
    retry = importer.import_file(source)

    assert retry.status == "duplicate"
    assert retry.stable_id == first.stable_id
    assert retry.original_path == first.original_path
    assert len(list((tmp_path / "store" / "originals").iterdir())) == 1
    assert importer.db.execute("SELECT COUNT(*) FROM screenshots").fetchone()[0] == 1
    importer.close()


def test_missing_partial_input_fails_without_creating_manifest_or_original(tmp_path: Path):
    importer = ScreenshotImporter(tmp_path / "store")

    with pytest.raises(FileNotFoundError):
        importer.import_file(tmp_path / "missing.png")

    assert importer.db.execute("SELECT COUNT(*) FROM screenshots").fetchone()[0] == 0
    assert not list((tmp_path / "store" / "originals").iterdir())
    importer.close()


def test_sensitive_zone_is_not_an_ordinary_original_zone(tmp_path: Path):
    storage = FileSystemStorage(tmp_path / "store")
    storage.put("sensitive", "evidence.bin", b"private")

    assert storage.get("sensitive", "evidence.bin") == b"private"
    assert not storage.exists("originals", "evidence.bin")
    with pytest.raises(FileNotFoundError):
        storage.get("originals", "evidence.bin")


def test_expired_original_can_be_reported_but_legal_hold_is_preserved(tmp_path: Path):
    storage = FileSystemStorage(tmp_path / "store")
    storage.put("originals", "expired.bin", b"old")
    storage.put("originals", "held.bin", b"old")
    old = (datetime.now(timezone.utc) - timedelta(days=400)).isoformat()

    # The retention policy is intentionally dry-run by default; this verifies
    # that a hold is excluded before any destructive operation is requested.
    from screenshot_storage import RetentionManager, RetentionPolicy
    report = RetentionManager(storage, RetentionPolicy(365, 0)).purge(
        [{"key": "expired.bin", "captured_at": old},
         {"key": "held.bin", "captured_at": old, "legal_hold": True}],
        dry_run=True,
    )

    assert report == [{"key": "expired.bin", "purged": False, "dry_run": True}]
    assert storage.exists("originals", "expired.bin")
    assert storage.exists("originals", "held.bin")
