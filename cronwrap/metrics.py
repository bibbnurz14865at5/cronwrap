"""Lightweight metrics aggregation for cron job runs."""

from __future__ import annotations

import statistics
from dataclasses import dataclass, field
from typing import List, Optional

from cronwrap.history import HistoryEntry, JobHistory


@dataclass
class JobMetrics:
    """Aggregated metrics for a single job derived from its history."""

    job_name: str
    total_runs: int = 0
    success_count: int = 0
    failure_count: int = 0
    timeout_count: int = 0
    durations: List[float] = field(default_factory=list)

    @property
    def success_rate(self) -> float:
        if self.total_runs == 0:
            return 0.0
        return self.success_count / self.total_runs

    @property
    def avg_duration(self) -> Optional[float]:
        if not self.durations:
            return None
        return statistics.mean(self.durations)

    @property
    def max_duration(self) -> Optional[float]:
        return max(self.durations) if self.durations else None

    @property
    def min_duration(self) -> Optional[float]:
        return min(self.durations) if self.durations else None

    def to_dict(self) -> dict:
        return {
            "job_name": self.job_name,
            "total_runs": self.total_runs,
            "success_count": self.success_count,
            "failure_count": self.failure_count,
            "timeout_count": self.timeout_count,
            "success_rate": round(self.success_rate, 4),
            "avg_duration": round(self.avg_duration, 3) if self.avg_duration is not None else None,
            "max_duration": round(self.max_duration, 3) if self.max_duration is not None else None,
            "min_duration": round(self.min_duration, 3) if self.min_duration is not None else None,
        }


def compute_metrics(job_name: str, history: JobHistory, limit: Optional[int] = None) -> JobMetrics:
    """Compute metrics for *job_name* from *history*.

    Parameters
    ----------
    job_name:
        Identifier used when entries were recorded.
    history:
        A :class:`JobHistory` instance to read entries from.
    limit:
        If given, only consider the most recent *limit* entries.
    """
    entries: List[HistoryEntry] = history.load(job_name)
    if limit is not None:
        entries = entries[-limit:]

    metrics = JobMetrics(job_name=job_name)
    for entry in entries:
        metrics.total_runs += 1
        if entry.timed_out:
            metrics.timeout_count += 1
            metrics.failure_count += 1
        elif entry.exit_code == 0:
            metrics.success_count += 1
        else:
            metrics.failure_count += 1
        if entry.duration is not None:
            metrics.durations.append(entry.duration)

    return metrics
