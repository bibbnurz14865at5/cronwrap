"""Periodic digest report generation for cronwrap."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional

from cronwrap.history import JobHistory
from cronwrap.metrics import compute_metrics
from cronwrap.report import summarise_job


@dataclass
class DigestEntry:
    job_name: str
    success_rate: float
    avg_duration: float
    total_runs: int
    last_run: Optional[str]
    last_status: Optional[str]

    def to_dict(self) -> dict:
        return {
            "job_name": self.job_name,
            "success_rate": self.success_rate,
            "avg_duration": self.avg_duration,
            "total_runs": self.total_runs,
            "last_run": self.last_run,
            "last_status": self.last_status,
        }


@dataclass
class Digest:
    generated_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    entries: List[DigestEntry] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "generated_at": self.generated_at,
            "entries": [e.to_dict() for e in self.entries],
        }

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), indent=2)

    def to_text(self) -> str:
        lines = [f"Cronwrap Digest — {self.generated_at}", "=" * 50]
        if not self.entries:
            lines.append("No job history found.")
        for e in self.entries:
            lines.append(
                f"{e.job_name}: runs={e.total_runs}, "
                f"success={e.success_rate:.1f}%, "
                f"avg_dur={e.avg_duration:.2f}s, "
                f"last={e.last_run or 'n/a'} [{e.last_status or 'n/a'}]"
            )
        return "\n".join(lines)


def build_digest(history_dir: Path) -> Digest:
    """Scan *history_dir* for per-job history files and build a Digest."""
    digest = Digest()
    if not history_dir.exists():
        return digest

    for history_file in sorted(history_dir.glob("*.json")):
        job_name = history_file.stem
        jh = JobHistory(job_name, history_dir)
        entries = jh.load()
        if not entries:
            continue
        metrics = compute_metrics(entries)
        last = entries[-1]
        digest.entries.append(
            DigestEntry(
                job_name=job_name,
                success_rate=metrics.success_rate,
                avg_duration=metrics.avg_duration,
                total_runs=metrics.total_runs,
                last_run=last.timestamp,
                last_status="ok" if last.success else "fail",
            )
        )
    return digest
