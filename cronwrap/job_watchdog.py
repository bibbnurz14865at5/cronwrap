"""Job watchdog: detect jobs that started but never completed."""
from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional


class WatchdogError(Exception):
    """Raised when watchdog operations fail."""


@dataclass
class WatchdogEntry:
    job_name: str
    pid: int
    started_at: float  # Unix timestamp
    extra: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        d = {
            "job_name": self.job_name,
            "pid": self.pid,
            "started_at": self.started_at,
        }
        if self.extra:
            d["extra"] = self.extra
        return d

    @classmethod
    def from_dict(cls, data: dict) -> "WatchdogEntry":
        return cls(
            job_name=data["job_name"],
            pid=data["pid"],
            started_at=data["started_at"],
            extra=data.get("extra", {}),
        )


@dataclass
class StuckJob:
    entry: WatchdogEntry
    elapsed: float  # seconds since started_at

    def __repr__(self) -> str:
        return (
            f"StuckJob(job={self.entry.job_name!r}, "
            f"pid={self.entry.pid}, elapsed={self.elapsed:.1f}s)"
        )


class JobWatchdog:
    """Register job starts and detect stuck/hung jobs."""

    def __init__(self, state_dir: str) -> None:
        self.state_dir = Path(state_dir)
        self.state_dir.mkdir(parents=True, exist_ok=True)

    def _path(self, job_name: str) -> Path:
        safe = job_name.replace("/", "_").replace(" ", "_")
        return self.state_dir / f"{safe}.watchdog.json"

    def register(self, job_name: str, pid: Optional[int] = None, extra: Optional[dict] = None) -> WatchdogEntry:
        """Record that a job has started."""
        entry = WatchdogEntry(
            job_name=job_name,
            pid=pid if pid is not None else os.getpid(),
            started_at=time.time(),
            extra=extra or {},
        )
        self._path(job_name).write_text(json.dumps(entry.to_dict()))
        return entry

    def clear(self, job_name: str) -> None:
        """Remove watchdog entry after a job completes successfully."""
        p = self._path(job_name)
        if p.exists():
            p.unlink()

    def get(self, job_name: str) -> Optional[WatchdogEntry]:
        """Return the current watchdog entry for a job, or None."""
        p = self._path(job_name)
        if not p.exists():
            return None
        return WatchdogEntry.from_dict(json.loads(p.read_text()))

    def find_stuck(self, threshold_seconds: float) -> List[StuckJob]:
        """Return all jobs that have been running longer than *threshold_seconds*."""
        now = time.time()
        stuck: List[StuckJob] = []
        for p in sorted(self.state_dir.glob("*.watchdog.json")):
            try:
                entry = WatchdogEntry.from_dict(json.loads(p.read_text()))
            except (json.JSONDecodeError, KeyError):
                continue
            elapsed = now - entry.started_at
            if elapsed >= threshold_seconds:
                stuck.append(StuckJob(entry=entry, elapsed=elapsed))
        return stuck
