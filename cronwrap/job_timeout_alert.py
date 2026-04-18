"""Alert policy for jobs that exceed a duration threshold."""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional


@dataclass
class TimeoutAlertPolicy:
    job_name: str
    warn_seconds: Optional[float] = None
    critical_seconds: Optional[float] = None
    notify_slack: bool = False
    notify_email: bool = False

    def to_dict(self) -> dict:
        return {
            "job_name": self.job_name,
            "warn_seconds": self.warn_seconds,
            "critical_seconds": self.critical_seconds,
            "notify_slack": self.notify_slack,
            "notify_email": self.notify_email,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "TimeoutAlertPolicy":
        return cls(
            job_name=data["job_name"],
            warn_seconds=data.get("warn_seconds"),
            critical_seconds=data.get("critical_seconds"),
            notify_slack=bool(data.get("notify_slack", False)),
            notify_email=bool(data.get("notify_email", False)),
        )

    @classmethod
    def from_json_file(cls, path: str) -> "TimeoutAlertPolicy":
        p = Path(path)
        if not p.exists():
            raise FileNotFoundError(f"Config not found: {path}")
        return cls.from_dict(json.loads(p.read_text()))


@dataclass
class TimeoutAlertResult:
    job_name: str
    duration: float
    level: str  # "ok", "warn", "critical"
    warn_seconds: Optional[float]
    critical_seconds: Optional[float]

    @property
    def triggered(self) -> bool:
        return self.level != "ok"

    def __repr__(self) -> str:
        return (
            f"TimeoutAlertResult(job={self.job_name!r}, "
            f"duration={self.duration:.2f}s, level={self.level!r})"
        )


def evaluate(policy: TimeoutAlertPolicy, duration_seconds: float) -> TimeoutAlertResult:
    """Evaluate a duration against the policy thresholds."""
    level = "ok"
    if policy.critical_seconds is not None and duration_seconds >= policy.critical_seconds:
        level = "critical"
    elif policy.warn_seconds is not None and duration_seconds >= policy.warn_seconds:
        level = "warn"
    return TimeoutAlertResult(
        job_name=policy.job_name,
        duration=duration_seconds,
        level=level,
        warn_seconds=policy.warn_seconds,
        critical_seconds=policy.critical_seconds,
    )
