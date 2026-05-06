"""Job duration and success-rate trend analysis over sliding windows."""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional

from cronwrap.history import JobHistory


class TrendError(Exception):
    """Raised when trend analysis cannot be completed."""


@dataclass
class TrendResult:
    job_name: str
    window: int  # number of recent runs examined
    success_rate_pct: float
    avg_duration_s: float
    trend_direction: str  # 'improving', 'degrading', 'stable', 'unknown'
    sample_count: int
    extra: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        d = {
            "job_name": self.job_name,
            "window": self.window,
            "success_rate_pct": round(self.success_rate_pct, 2),
            "avg_duration_s": round(self.avg_duration_s, 3),
            "trend_direction": self.trend_direction,
            "sample_count": self.sample_count,
        }
        if self.extra:
            d["extra"] = self.extra
        return d

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), indent=2)


def _direction(early_avg: float, late_avg: float, threshold: float = 0.05) -> str:
    if early_avg == 0:
        return "unknown"
    delta = (late_avg - early_avg) / early_avg
    if delta < -threshold:
        return "improving"
    if delta > threshold:
        return "degrading"
    return "stable"


def analyse_trend(
    job_name: str,
    history_dir: str,
    window: int = 20,
) -> TrendResult:
    """Compute trend for *job_name* using the last *window* history entries."""
    if window < 2:
        raise TrendError("window must be >= 2")

    hist = JobHistory(job_name, history_dir)
    entries = hist.load()
    recent = entries[-window:] if len(entries) >= window else entries
    sample_count = len(recent)

    if sample_count == 0:
        return TrendResult(
            job_name=job_name,
            window=window,
            success_rate_pct=0.0,
            avg_duration_s=0.0,
            trend_direction="unknown",
            sample_count=0,
        )

    successes = sum(1 for e in recent if e.success)
    success_rate = (successes / sample_count) * 100.0
    durations = [e.duration for e in recent if e.duration is not None]
    avg_dur = sum(durations) / len(durations) if durations else 0.0

    # Compare first half vs second half for direction
    mid = sample_count // 2
    early = [e.duration for e in recent[:mid] if e.duration is not None]
    late = [e.duration for e in recent[mid:] if e.duration is not None]
    early_avg = sum(early) / len(early) if early else 0.0
    late_avg = sum(late) / len(late) if late else 0.0
    direction = _direction(early_avg, late_avg)

    return TrendResult(
        job_name=job_name,
        window=window,
        success_rate_pct=success_rate,
        avg_duration_s=avg_dur,
        trend_direction=direction,
        sample_count=sample_count,
    )
