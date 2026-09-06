from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

@dataclass(frozen=True)
class RetentionPolicy:
    retention_days: int = 365
    grace_days: int = 30

class RetentionManager:
    def __init__(self, storage, policy=RetentionPolicy()): self.storage, self.policy = storage, policy
    def purge(self, objects, *, now=None, legal_holds=frozenset(), dry_run=True):
        now = now or datetime.now(timezone.utc); cutoff = now - timedelta(days=self.policy.retention_days + self.policy.grace_days)
        results = []
        for obj in objects:
            key, captured = obj["key"], obj["captured_at"]
            when = captured if isinstance(captured, datetime) else datetime.fromisoformat(captured.replace("Z", "+00:00"))
            protected = key in legal_holds or obj.get("legal_hold", False)
            if when < cutoff and not protected:
                self.storage.delete(obj.get("zone", "originals"), key, dry_run=dry_run); results.append({"key": key, "purged": not dry_run, "dry_run": dry_run})
        return results
