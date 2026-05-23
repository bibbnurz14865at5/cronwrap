"""job_flux.py — tracks run-to-run duration variability (flux) for a job."""
from __future__ import annotations

import json
import math
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional

from cronwrap.history import JobHistory


class FluxError(Exception):
    """Raised when flux analysis cannot be performed."""


@dataclass
class FluxResult:
    job_name: str
    sample_count: int
    mean: float
    stddev: float
    cv: float          # coefficient of variation (stddev / mean)
    is_volatile: bool  # True when cv exceeds threshold
    threshold: float
    extra: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        d = {
            "job_name": self.job_name,
            "sample_count": self.sample_count,
            "mean": round(self.mean, 4),
            "stddev": round(self.stddev, 4),
            "cv": round(self.cv, 4),
            "is_volatile": self.is_volatile,
            "threshold": self.threshold,
        }
        if self.extra:
            d["extra"] = self.extra
        return d

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), indent=2)

    @classmethod
    def from_dict(cls, data: dict) -> "FluxResult":
        return cls(
            job_name=data["job_name"],
            sample_count=data["sample_count"],
            mean=data["mean"],
            stddev=data["stddev"],
            cv=data["cv"],
            is_volatile=data["is_volatile"],
            threshold=data["threshold"],
            extra=data.get("extra", {}),
        )


def analyse_flux(
    job_name: str,
    history_dir: str,
    *,
    threshold: float = 0.5,
    min_samples: int = 3,
) -> FluxResult:
    """Compute duration flux for *job_name* from its history.

    Raises FluxError when fewer than *min_samples* successful runs exist.
    """
    history_path = Path(history_dir) / f"{job_name}.json"
    if not history_path.exists():
        raise FluxError(f"No history file found for job '{job_name}'")

    jh = JobHistory(history_path)
    entries = [e for e in jh.load() if e.success and e.duration is not None]

    if len(entries) < min_samples:
        raise FluxError(
            f"Need at least {min_samples} successful runs; found {len(entries)}"
        )

    durations: List[float] = [e.duration for e in entries]  # type: ignore[misc]
    n = len(durations)
    mean = sum(durations) / n
    variance = sum((d - mean) ** 2 for d in durations) / n
    stddev = math.sqrt(variance)
    cv = stddev / mean if mean > 0 else 0.0

    return FluxResult(
        job_name=job_name,
        sample_count=n,
        mean=mean,
        stddev=stddev,
        cv=cv,
        is_volatile=cv > threshold,
        threshold=threshold,
    )
