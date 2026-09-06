import argparse, json
from pathlib import Path
from .ingest import ScreenshotImporter

def main() -> None:
    parser = argparse.ArgumentParser(description="Import screenshots without altering originals")
    parser.add_argument("source", type=Path)
    parser.add_argument("--store", type=Path, default=Path(".screenshot-data"))
    parser.add_argument("--captured-at")
    args = parser.parse_args()
    files = sorted(p for p in args.source.rglob("*") if p.is_file()) if args.source.is_dir() else [args.source]
    importer = ScreenshotImporter(args.store)
    try:
        for result in importer.import_batch(files, args.captured_at):
            print(json.dumps(result.__dict__, sort_keys=True))
    finally:
        importer.close()
