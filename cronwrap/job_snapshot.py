"""Snapshot the current state of all jobs into a single JSON report."""
from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from cronwrap.history import JobHistory
from cronwrap.metrics import compute_metrics


@dataclass
class JobSnapshot:
    job_name: str
    last_run: Optional[str]
    last_status: Optional[str]
    success_rate: float
    avg_duration: float
    total_runs: int
    extra: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        d: Dict[str, Any] = {
            "job_name": self.job_name,
            "last_run": self.last_run,
            "last_status": self.last_status,
            "success_rate": self.success_rate,
            "avg_duration": self.avg_duration,
            "total_runs": self.total_runs,
        }
        if self.extra:
            d["extra"] = self.extra
        return d


@dataclass
class SnapshotReport:
    generated_at: str
    jobs: List[JobSnapshot] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "generated_at": self.generated_at,
            "jobs": [j.to_dict() for j in self.jobs],
        }

    def to_json(self, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), indent=indent)


def build_snapshot(history_dir: str) -> SnapshotReport:
    """Scan *history_dir* and build a SnapshotReport for every job found."""
    base = Path(history_dir)
    generated_at = datetime.now(timezone.utc).isoformat()
    report = SnapshotReport(generated_at=generated_at)

    if not base.exists():
        return report

    for entry in sorted(base.iterdir()):
        if not entry.is_file() or entry.suffix != ".json":
            continue
        job_name = entry.stem
        history = JobHistory(str(base), job_name)
        entries = history.load()
        metrics = compute_metrics(entries)
        last_run = entries[-1].timestamp if entries else None
        last_status = entries[-1].status if entries else None
        snap = JobSnapshot(
            job_name=job_name,
            last_run=last_run,
            last_status=last_status,
            success_rate=round(metrics.success_rate, 4),
            avg_duration=round(metrics.avg_duration, 3),
            total_runs=metrics.total_runs,
        )
        report.jobs.append(snap)

    return report


def save_snapshot(report: SnapshotReport, output_path: str) -> None:
    """Write *report* as JSON to *output_path*, creating parent dirs as needed."""
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(report.to_json(), encoding="utf-8")
