"""Job execution heatmap: tracks run counts bucketed by hour-of-day."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional


class HeatmapError(Exception):
    """Raised on heatmap operation failures."""


@dataclass
class HeatmapRecord:
    job_name: str
    # 24 buckets, one per hour (0-23)
    buckets: List[int] = field(default_factory=lambda: [0] * 24)

    def to_dict(self) -> dict:
        return {"job_name": self.job_name, "buckets": list(self.buckets)}

    @classmethod
    def from_dict(cls, data: dict) -> "HeatmapRecord":
        buckets = data.get("buckets", [0] * 24)
        if len(buckets) != 24:
            raise HeatmapError("buckets must have exactly 24 entries")
        return cls(job_name=data["job_name"], buckets=list(buckets))

    def peak_hour(self) -> Optional[int]:
        """Return the hour (0-23) with the most runs, or None if all zero."""
        if max(self.buckets) == 0:
            return None
        return self.buckets.index(max(self.buckets))

    def total_runs(self) -> int:
        return sum(self.buckets)


class JobHeatmap:
    def __init__(self, state_dir: str) -> None:
        self._dir = Path(state_dir)
        self._dir.mkdir(parents=True, exist_ok=True)

    def _path(self, job_name: str) -> Path:
        return self._dir / f"{job_name}.heatmap.json"

    def _load(self, job_name: str) -> HeatmapRecord:
        p = self._path(job_name)
        if p.exists():
            return HeatmapRecord.from_dict(json.loads(p.read_text()))
        return HeatmapRecord(job_name=job_name)

    def _save(self, record: HeatmapRecord) -> None:
        self._path(record.job_name).write_text(json.dumps(record.to_dict(), indent=2))

    def record(self, job_name: str, hour: int) -> HeatmapRecord:
        """Increment the bucket for *hour* (0-23) and persist."""
        if not 0 <= hour <= 23:
            raise HeatmapError(f"hour must be 0-23, got {hour}")
        rec = self._load(job_name)
        rec.buckets[hour] += 1
        self._save(rec)
        return rec

    def get(self, job_name: str) -> HeatmapRecord:
        return self._load(job_name)

    def reset(self, job_name: str) -> None:
        p = self._path(job_name)
        if p.exists():
            p.unlink()

    def all_jobs(self) -> List[str]:
        return sorted(p.name.replace(".heatmap.json", "") for p in self._dir.glob("*.heatmap.json"))
