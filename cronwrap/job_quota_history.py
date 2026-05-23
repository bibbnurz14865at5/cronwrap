"""Track historical quota usage snapshots for a job."""
from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import List, Optional


class QuotaHistoryError(Exception):
    """Raised when quota history operations fail."""


@dataclass
class QuotaUsageSnapshot:
    job_name: str
    used: int
    limit: int
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    extra: dict = field(default_factory=dict)

    @property
    def pct_used(self) -> float:
        if self.limit == 0:
            return 0.0
        return round(self.used / self.limit * 100, 2)

    def to_dict(self) -> dict:
        d = {
            "job_name": self.job_name,
            "used": self.used,
            "limit": self.limit,
            "pct_used": self.pct_used,
            "timestamp": self.timestamp,
        }
        if self.extra:
            d["extra"] = self.extra
        return d

    @classmethod
    def from_dict(cls, data: dict) -> "QuotaUsageSnapshot":
        return cls(
            job_name=data["job_name"],
            used=data["used"],
            limit=data["limit"],
            timestamp=data.get("timestamp", datetime.now(timezone.utc).isoformat()),
            extra=data.get("extra", {}),
        )


@dataclass
class QuotaHistory:
    job_name: str
    state_dir: str

    def _path(self) -> str:
        return os.path.join(self.state_dir, f"{self.job_name}.quota_history.json")

    def _load(self) -> List[dict]:
        p = self._path()
        if not os.path.exists(p):
            return []
        with open(p) as f:
            return json.load(f)

    def record(self, used: int, limit: int, extra: Optional[dict] = None) -> QuotaUsageSnapshot:
        snap = QuotaUsageSnapshot(
            job_name=self.job_name,
            used=used,
            limit=limit,
            extra=extra or {},
        )
        entries = self._load()
        entries.append(snap.to_dict())
        os.makedirs(self.state_dir, exist_ok=True)
        with open(self._path(), "w") as f:
            json.dump(entries, f, indent=2)
        return snap

    def snapshots(self) -> List[QuotaUsageSnapshot]:
        return [QuotaUsageSnapshot.from_dict(e) for e in self._load()]

    def clear(self) -> None:
        p = self._path()
        if os.path.exists(p):
            os.remove(p)
