import hashlib
from pathlib import Path
from screenshot_app import ScreenshotImporter

def test_import_preserves_bytes_and_metadata(tmp_path: Path):
    source = tmp_path / "capture.PNG"
    payload = b"not altered\x00binary"
    source.write_bytes(payload)
    importer = ScreenshotImporter(tmp_path / "store")
    result = importer.import_file(source, "2026-09-06T10:00:00+00:00")
    assert result.status == "imported"
    assert result.stable_id == hashlib.sha256(payload).hexdigest()
    assert Path(result.original_path).read_bytes() == payload
    row = importer.db.execute("SELECT captured_at, source FROM screenshots").fetchone()
    assert row == ("2026-09-06T10:00:00+00:00", str(source))
    importer.close()

def test_duplicate_is_idempotent_and_does_not_overwrite(tmp_path: Path):
    source = tmp_path / "a.png"
    source.write_bytes(b"same")
    importer = ScreenshotImporter(tmp_path / "store")
    first = importer.import_file(source)
    source.rename(tmp_path / "renamed.png")
    second = importer.import_file(tmp_path / "renamed.png")
    assert second.status == "duplicate"
    assert second.stable_id == first.stable_id
    assert len(list((tmp_path / "store" / "originals").iterdir())) == 1
    importer.close()
