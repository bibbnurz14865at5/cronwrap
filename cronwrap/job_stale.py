"""Detect stale jobs that have not run within an expected interval."""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from cronwrap.history import JobHistory


class StaleError(Exception):
    """Raised for invalid stale-detection configuration."""


@dataclass
class StalePolicy:
    """Policy that flags a job as stale when it hasn't run in *max_age_seconds*."""

    job_name: str
    max_age_seconds: int
    history_dir: str = "/var/lib/cronwrap/history"

    def to_dict(self) -> dict:
        return {
            "job_name": self.job_name,
            "max_age_seconds": self.max_age_seconds,
            "history_dir": self.history_dir,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "StalePolicy":
        if "job_name" not in data:
            raise StaleError("'job_name' is required")
        if "max_age_seconds" not in data:
            raise StaleError("'max_age_seconds' is required")
        return cls(
            job_name=data["job_name"],
            max_age_seconds=int(data["max_age_seconds"]),
            history_dir=data.get("history_dir", "/var/lib/cronwrap/history"),
        )

    @classmethod
    def from_json_file(cls, path: str) -> "StalePolicy":
        p = Path(path)
        if not p.exists():
            raise StaleError(f"Config file not found: {path}")
        return cls.from_dict(json.loads(p.read_text()))


@dataclass
class StaleResult:
    job_name: str
    is_stale: bool
    last_run: Optional[datetime]
    age_seconds: Optional[float]
    max_age_seconds: int
    reason: str = ""

    def __repr__(self) -> str:  # pragma: no cover
        return (
            f"StaleResult(job={self.job_name!r}, stale={self.is_stale}, "
            f"age={self.age_seconds}s, max={self.max_age_seconds}s)"
        )


def check_stale(policy: StalePolicy, now: Optional[datetime] = None) -> StaleResult:
    """Return a :class:`StaleResult` indicating whether the job is stale."""
    if now is None:
        now = datetime.now(timezone.utc)

    history = JobHistory(policy.history_dir, policy.job_name)
    entries = history.load()

    if not entries:
        return StaleResult(
            job_name=policy.job_name,
            is_stale=False,
            last_run=None,
            age_seconds=None,
            max_age_seconds=policy.max_age_seconds,
            reason="no history available",
        )

    last_entry = entries[-1]
    last_run = last_entry.timestamp
    if last_run.tzinfo is None:
        last_run = last_run.replace(tzinfo=timezone.utc)

    age = (now - last_run).total_seconds()
    is_stale = age > policy.max_age_seconds
    reason = (
        f"last run {age:.0f}s ago, limit {policy.max_age_seconds}s"
        if is_stale
        else "within acceptable age"
    )
    return StaleResult(
        job_name=policy.job_name,
        is_stale=is_stale,
        last_run=last_run,
        age_seconds=age,
        max_age_seconds=policy.max_age_seconds,
        reason=reason,
    )
