import os
from dataclasses import dataclass

@dataclass(frozen=True)
class StorageConfig:
    root: str = "./data"
    bucket: str | None = None
    public_objects: bool = False
    retention_days: int = 365
    grace_days: int = 30

    @classmethod
    def from_env(cls):
        # Missing credentials never enable a public or remote write path.
        return cls(root=os.getenv("SCREENSHOT_STORAGE_ROOT", "./data"), bucket=os.getenv("SCREENSHOT_STORAGE_BUCKET"),
                   public_objects=os.getenv("SCREENSHOT_STORAGE_PUBLIC", "false").lower() == "true",
                   retention_days=int(os.getenv("SCREENSHOT_RETENTION_DAYS", "365")),
                   grace_days=int(os.getenv("SCREENSHOT_RETENTION_GRACE_DAYS", "30")))
