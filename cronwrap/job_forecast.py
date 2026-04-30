"""Job run-time forecasting based on historical durations."""
from __future__ import annotations

import json
import statistics
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional

from cronwrap.history import JobHistory


class ForecastError(Exception):
    """Raised when forecasting cannot be performed."""


@dataclass
class ForecastResult:
    job_name: str
    sample_size: int
    predicted_duration: float  # seconds
    lower_bound: float
    upper_bound: float
    confidence: str  # 'low' | 'medium' | 'high'

    def to_dict(self) -> dict:
        return {
            "job_name": self.job_name,
            "sample_size": self.sample_size,
            "predicted_duration": round(self.predicted_duration, 3),
            "lower_bound": round(self.lower_bound, 3),
            "upper_bound": round(self.upper_bound, 3),
            "confidence": self.confidence,
        }

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), indent=2)

    @classmethod
    def from_dict(cls, d: dict) -> "ForecastResult":
        return cls(
            job_name=d["job_name"],
            sample_size=d["sample_size"],
            predicted_duration=d["predicted_duration"],
            lower_bound=d["lower_bound"],
            upper_bound=d["upper_bound"],
            confidence=d["confidence"],
        )


def _confidence_level(n: int) -> str:
    if n >= 20:
        return "high"
    if n >= 5:
        return "medium"
    return "low"


def forecast_job(
    job_name: str,
    history_dir: str,
    stddev_multiplier: float = 1.5,
) -> ForecastResult:
    """Forecast next run duration from successful history entries."""
    hist = JobHistory(job_name, history_dir)
    entries = [e for e in hist.load() if e.success and e.duration is not None]

    if not entries:
        raise ForecastError(
            f"No successful history entries found for job '{job_name}'"
        )

    durations = [e.duration for e in entries]
    predicted = statistics.mean(durations)
    n = len(durations)

    if n >= 2:
        sd = statistics.stdev(durations)
    else:
        sd = predicted * 0.1  # 10% fallback

    margin = stddev_multiplier * sd
    lower = max(0.0, predicted - margin)
    upper = predicted + margin

    return ForecastResult(
        job_name=job_name,
        sample_size=n,
        predicted_duration=predicted,
        lower_bound=lower,
        upper_bound=upper,
        confidence=_confidence_level(n),
    )
