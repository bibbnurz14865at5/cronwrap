"""Track high-water-mark (maximum observed duration) for cron jobs."""
from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from typing import Optional


class WatermarkError(Exception):
    """Raised when watermark operations fail."""


@dataclass
class WatermarkRecord:
    job_name: str
    max_duration: float
    recorded_at: str
    extra: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        d = {
            "job_name": self.job_name,
            "max_duration": self.max_duration,
            "recorded_at": self.recorded_at,
        }
        if self.extra:
            d["extra"] = self.extra
        return d

    @classmethod
    def from_dict(cls, data: dict) -> "WatermarkRecord":
        return cls(
            job_name=data["job_name"],
            max_duration=float(data["max_duration"]),
            recorded_at=data["recorded_at"],
            extra=data.get("extra", {}),
        )


class JobWatermark:
    """Persist and query the high-water-mark duration for a job."""

    def __init__(self, state_dir: str) -> None:
        self.state_dir = state_dir
        os.makedirs(state_dir, exist_ok=True)

    def _path(self, job_name: str) -> str:
        safe = job_name.replace(os.sep, "_")
        return os.path.join(self.state_dir, f"{safe}.watermark.json")

    def get(self, job_name: str) -> Optional[WatermarkRecord]:
        """Return the current watermark record, or None if not set."""
        p = self._path(job_name)
        if not os.path.exists(p):
            return None
        with open(p) as fh:
            return WatermarkRecord.from_dict(json.load(fh))

    def update(self, job_name: str, duration: float, recorded_at: str,
               extra: Optional[dict] = None) -> WatermarkRecord:
        """Update the watermark if *duration* exceeds the current maximum."""
        current = self.get(job_name)
        if current is not None and current.max_duration >= duration:
            return current
        record = WatermarkRecord(
            job_name=job_name,
            max_duration=duration,
            recorded_at=recorded_at,
            extra=extra or {},
        )
        with open(self._path(job_name), "w") as fh:
            json.dump(record.to_dict(), fh)
        return record

    def reset(self, job_name: str) -> None:
        """Remove the stored watermark for *job_name*."""
        p = self._path(job_name)
        if os.path.exists(p):
            os.remove(p)
        else:
            raise WatermarkError(f"No watermark found for job '{job_name}'")
