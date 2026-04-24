"""Baseline duration tracking for cron jobs.

Records a rolling baseline (median duration) for a job and exposes
helpers to detect anomalous runtimes.
"""
from __future__ import annotations

import json
import statistics
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional


class BaselineError(Exception):
    """Raised when baseline operations fail."""


@dataclass
class BaselineRecord:
    job_name: str
    durations: List[float] = field(default_factory=list)
    window: int = 20  # keep last N samples

    # ------------------------------------------------------------------
    # Persistence helpers
    # ------------------------------------------------------------------

    def to_dict(self) -> dict:
        return {
            "job_name": self.job_name,
            "durations": self.durations,
            "window": self.window,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "BaselineRecord":
        return cls(
            job_name=data["job_name"],
            durations=list(data.get("durations", [])),
            window=int(data.get("window", 20)),
        )

    # ------------------------------------------------------------------
    # Statistics
    # ------------------------------------------------------------------

    @property
    def median(self) -> Optional[float]:
        if not self.durations:
            return None
        return statistics.median(self.durations)

    def is_anomalous(self, duration: float, factor: float = 2.0) -> bool:
        """Return True if *duration* exceeds *factor* × median baseline."""
        med = self.median
        if med is None or med == 0:
            return False
        return duration > med * factor

    def record(self, duration: float) -> None:
        """Append *duration* and trim to the rolling window."""
        self.durations.append(duration)
        if len(self.durations) > self.window:
            self.durations = self.durations[-self.window :]


class JobBaseline:
    """Persist and retrieve baseline records from a directory."""

    def __init__(self, state_dir: str) -> None:
        self._dir = Path(state_dir)
        self._dir.mkdir(parents=True, exist_ok=True)

    def _path(self, job_name: str) -> Path:
        safe = job_name.replace("/", "_").replace(" ", "_")
        return self._dir / f"{safe}.baseline.json"

    def load(self, job_name: str, window: int = 20) -> BaselineRecord:
        p = self._path(job_name)
        if not p.exists():
            return BaselineRecord(job_name=job_name, window=window)
        try:
            data = json.loads(p.read_text())
            return BaselineRecord.from_dict(data)
        except (json.JSONDecodeError, KeyError) as exc:
            raise BaselineError(f"Corrupt baseline file {p}: {exc}") from exc

    def save(self, record: BaselineRecord) -> None:
        p = self._path(record.job_name)
        p.write_text(json.dumps(record.to_dict(), indent=2))

    def update(self, job_name: str, duration: float, window: int = 20) -> BaselineRecord:
        """Load, append *duration*, persist, and return the updated record."""
        rec = self.load(job_name, window=window)
        rec.window = window
        rec.record(duration)
        self.save(rec)
        return rec
