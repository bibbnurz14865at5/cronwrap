"""Track and analyse per-job latency (time between scheduled and actual start)."""
from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from statistics import mean, median
from typing import List, Optional


class LatencyError(Exception):
    """Raised for latency tracking errors."""


@dataclass
class LatencyRecord:
    job_name: str
    scheduled_at: str          # ISO-8601
    started_at: str            # ISO-8601
    latency_seconds: float
    extra: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        d = {
            "job_name": self.job_name,
            "scheduled_at": self.scheduled_at,
            "started_at": self.started_at,
            "latency_seconds": round(self.latency_seconds, 3),
        }
        if self.extra:
            d["extra"] = self.extra
        return d

    @classmethod
    def from_dict(cls, data: dict) -> "LatencyRecord":
        return cls(
            job_name=data["job_name"],
            scheduled_at=data["scheduled_at"],
            started_at=data["started_at"],
            latency_seconds=float(data["latency_seconds"]),
            extra=data.get("extra", {}),
        )

    @classmethod
    def measure(cls, job_name: str, scheduled_at: datetime, started_at: Optional[datetime] = None, **extra) -> "LatencyRecord":
        if started_at is None:
            started_at = datetime.utcnow()
        delta = (started_at - scheduled_at).total_seconds()
        return cls(
            job_name=job_name,
            scheduled_at=scheduled_at.isoformat(),
            started_at=started_at.isoformat(),
            latency_seconds=max(0.0, delta),
            extra=extra or {},
        )


class JobLatency:
    def __init__(self, state_dir: str):
        self.state_dir = Path(state_dir)
        self.state_dir.mkdir(parents=True, exist_ok=True)

    def _path(self, job_name: str) -> Path:
        return self.state_dir / f"{job_name}.latency.json"

    def record(self, rec: LatencyRecord) -> None:
        path = self._path(rec.job_name)
        records = self._load(rec.job_name)
        records.append(rec.to_dict())
        path.write_text(json.dumps(records, indent=2))

    def _load(self, job_name: str) -> list:
        path = self._path(job_name)
        if not path.exists():
            return []
        return json.loads(path.read_text())

    def get_records(self, job_name: str) -> List[LatencyRecord]:
        return [LatencyRecord.from_dict(d) for d in self._load(job_name)]

    def stats(self, job_name: str) -> dict:
        records = self.get_records(job_name)
        if not records:
            return {"count": 0, "mean": None, "median": None, "max": None, "min": None}
        values = [r.latency_seconds for r in records]
        return {
            "count": len(values),
            "mean": round(mean(values), 3),
            "median": round(median(values), 3),
            "max": round(max(values), 3),
            "min": round(min(values), 3),
        }
