"""Track and audit quota usage events for cron jobs."""
from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional


class QuotaAuditError(Exception):
    """Raised when a quota audit operation fails."""


@dataclass
class QuotaAuditEvent:
    job_name: str
    action: str          # "allowed" | "denied" | "reset"
    quota_used: int
    quota_limit: int
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    reason: Optional[str] = None

    def to_dict(self) -> dict:
        d = {
            "job_name": self.job_name,
            "action": self.action,
            "quota_used": self.quota_used,
            "quota_limit": self.quota_limit,
            "timestamp": self.timestamp,
        }
        if self.reason is not None:
            d["reason"] = self.reason
        return d

    @classmethod
    def from_dict(cls, data: dict) -> "QuotaAuditEvent":
        return cls(
            job_name=data["job_name"],
            action=data["action"],
            quota_used=data["quota_used"],
            quota_limit=data["quota_limit"],
            timestamp=data.get("timestamp", datetime.now(timezone.utc).isoformat()),
            reason=data.get("reason"),
        )


class QuotaAuditLog:
    def __init__(self, log_dir: str) -> None:
        self._dir = Path(log_dir)
        self._dir.mkdir(parents=True, exist_ok=True)

    def _path(self, job_name: str) -> Path:
        return self._dir / f"{job_name}.quota_audit.json"

    def record(self, event: QuotaAuditEvent) -> None:
        path = self._path(event.job_name)
        events = self._load(event.job_name)
        events.append(event.to_dict())
        path.write_text(json.dumps(events, indent=2))

    def _load(self, job_name: str) -> list:
        path = self._path(job_name)
        if not path.exists():
            return []
        return json.loads(path.read_text())

    def events(self, job_name: str) -> List[QuotaAuditEvent]:
        return [QuotaAuditEvent.from_dict(d) for d in self._load(job_name)]

    def clear(self, job_name: str) -> None:
        path = self._path(job_name)
        if path.exists():
            path.unlink()
