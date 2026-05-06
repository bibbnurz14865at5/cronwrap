"""Job summary report: aggregate per-job stats into a concise human-readable block."""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional

from cronwrap.history import JobHistory
from cronwrap.metrics import compute_metrics


class SummaryError(Exception):
    """Raised when summary generation fails."""


@dataclass
class JobSummaryEntry:
    job_name: str
    total_runs: int
    success_rate: float  # 0.0 – 1.0
    avg_duration: float  # seconds
    last_status: str  # "ok" | "fail" | "timeout" | "unknown"
    extra: Dict[str, object] = field(default_factory=dict)

    def to_dict(self) -> dict:
        d: dict = {
            "job_name": self.job_name,
            "total_runs": self.total_runs,
            "success_rate": round(self.success_rate, 4),
            "avg_duration": round(self.avg_duration, 3),
            "last_status": self.last_status,
        }
        if self.extra:
            d["extra"] = self.extra
        return d

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), indent=2)


def _last_status(history: JobHistory) -> str:
    entries = history.load()
    if not entries:
        return "unknown"
    last = entries[-1]
    if last.timed_out:
        return "timeout"
    return "ok" if last.exit_code == 0 else "fail"


def build_summary(history_dir: str) -> List[JobSummaryEntry]:
    """Build a summary entry for every job found in *history_dir*."""
    base = Path(history_dir)
    if not base.exists():
        return []

    results: List[JobSummaryEntry] = []
    for path in sorted(base.glob("*.json")):
        job_name = path.stem
        history = JobHistory(job_name, history_dir=history_dir)
        metrics = compute_metrics(history)
        last = _last_status(history)
        results.append(
            JobSummaryEntry(
                job_name=job_name,
                total_runs=metrics.total_runs,
                success_rate=metrics.success_rate,
                avg_duration=metrics.avg_duration,
                last_status=last,
            )
        )
    return results


def summary_to_json(history_dir: str) -> str:
    entries = build_summary(history_dir)
    return json.dumps([e.to_dict() for e in entries], indent=2)
