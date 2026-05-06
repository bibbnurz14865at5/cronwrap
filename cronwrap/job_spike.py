"""Detect duration spikes relative to a job's historical baseline."""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional

from cronwrap.history import JobHistory


class SpikeError(Exception):
    """Raised when spike detection configuration is invalid."""


@dataclass
class SpikeResult:
    job_name: str
    duration: float
    baseline_avg: float
    threshold_multiplier: float
    is_spike: bool
    extra: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        d = {
            "job_name": self.job_name,
            "duration": round(self.duration, 3),
            "baseline_avg": round(self.baseline_avg, 3),
            "threshold_multiplier": self.threshold_multiplier,
            "is_spike": self.is_spike,
        }
        if self.extra:
            d["extra"] = self.extra
        return d

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), indent=2)

    @classmethod
    def from_dict(cls, data: dict) -> "SpikeResult":
        return cls(
            job_name=data["job_name"],
            duration=data["duration"],
            baseline_avg=data["baseline_avg"],
            threshold_multiplier=data["threshold_multiplier"],
            is_spike=data["is_spike"],
            extra=data.get("extra", {}),
        )


def detect_spike(
    job_name: str,
    duration: float,
    history_dir: str,
    threshold_multiplier: float = 2.0,
    min_samples: int = 3,
    extra: Optional[dict] = None,
) -> SpikeResult:
    """Compare *duration* against the historical average for *job_name*.

    Returns a :class:`SpikeResult`.  If fewer than *min_samples* successful
    runs exist the result is never flagged as a spike.
    """
    if threshold_multiplier <= 0:
        raise SpikeError("threshold_multiplier must be positive")
    if min_samples < 1:
        raise SpikeError("min_samples must be >= 1")

    history = JobHistory(job_name, history_dir)
    entries = [e for e in history.load() if e.success and e.duration is not None]
    durations: List[float] = [e.duration for e in entries]

    if len(durations) < min_samples:
        baseline_avg = duration
        is_spike = False
    else:
        baseline_avg = sum(durations) / len(durations)
        is_spike = duration > baseline_avg * threshold_multiplier

    return SpikeResult(
        job_name=job_name,
        duration=duration,
        baseline_avg=baseline_avg,
        threshold_multiplier=threshold_multiplier,
        is_spike=is_spike,
        extra=extra or {},
    )
