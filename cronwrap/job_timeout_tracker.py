"""Track and report jobs that have exceeded their expected duration."""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional

from cronwrap.history import JobHistory
from cronwrap.timeout_policy import TimeoutPolicy


@dataclass
class TimeoutViolation:
    job_name: str
    duration: float
    limit: float
    timestamp: str

    def to_dict(self) -> dict:
        return {
            "job_name": self.job_name,
            "duration": self.duration,
            "limit": self.limit,
            "timestamp": self.timestamp,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "TimeoutViolation":
        return cls(
            job_name=d["job_name"],
            duration=float(d["duration"]),
            limit=float(d["limit"]),
            timestamp=d["timestamp"],
        )


def find_violations(
    history_dir: Path,
    policy: TimeoutPolicy,
    job_name: Optional[str] = None,
) -> List[TimeoutViolation]:
    """Scan history entries and return violations for jobs exceeding the policy limit."""
    violations: List[TimeoutViolation] = []
    dirs = [history_dir / job_name] if job_name else [p for p in history_dir.iterdir() if p.is_dir()]
    for job_dir in dirs:
        name = job_dir.name
        history = JobHistory(job_dir)
        for entry in history.load():
            if entry.duration is None:
                continue
            if policy.is_timed_out(entry.duration):
                violations.append(
                    TimeoutViolation(
                        job_name=name,
                        duration=entry.duration,
                        limit=policy.warn_after or policy.kill_after,
                        timestamp=entry.timestamp,
                    )
                )
    return violations


def violations_to_json(violations: List[TimeoutViolation]) -> str:
    return json.dumps([v.to_dict() for v in violations], indent=2)
