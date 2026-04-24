"""SLA (Service Level Agreement) tracking for cron jobs.

Tracks whether jobs complete within a defined time window and
exposes SLA breach detection.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional


class SLAError(Exception):
    """Raised when an SLA operation fails."""


@dataclass
class SLAPolicy:
    job_name: str
    max_duration_seconds: Optional[float] = None  # wall-clock limit
    must_run_by: Optional[str] = None             # "HH:MM" daily deadline
    state_dir: str = "/tmp/cronwrap_sla"

    # --- serialisation ---

    def to_dict(self) -> dict:
        return {
            "job_name": self.job_name,
            "max_duration_seconds": self.max_duration_seconds,
            "must_run_by": self.must_run_by,
            "state_dir": self.state_dir,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "SLAPolicy":
        required = {"job_name"}
        missing = required - data.keys()
        if missing:
            raise SLAError(f"Missing required SLA keys: {missing}")
        return cls(
            job_name=data["job_name"],
            max_duration_seconds=data.get("max_duration_seconds"),
            must_run_by=data.get("must_run_by"),
            state_dir=data.get("state_dir", "/tmp/cronwrap_sla"),
        )

    @classmethod
    def from_json_file(cls, path: str) -> "SLAPolicy":
        p = Path(path)
        if not p.exists():
            raise SLAError(f"SLA config not found: {path}")
        return cls.from_dict(json.loads(p.read_text()))


@dataclass
class SLAResult:
    job_name: str
    breached: bool
    reason: Optional[str] = None

    def __repr__(self) -> str:  # pragma: no cover
        status = "BREACHED" if self.breached else "OK"
        return f"<SLAResult job={self.job_name!r} status={status}>"


def check_sla(policy: SLAPolicy, duration_seconds: float, run_time: Optional[str] = None) -> SLAResult:
    """Check whether a completed job run satisfies the given SLA.

    Args:
        policy: The SLA policy to evaluate.
        duration_seconds: How long the job actually ran.
        run_time: Optional "HH:MM" string representing when the job completed.

    Returns:
        SLAResult indicating whether the SLA was breached.
    """
    if policy.max_duration_seconds is not None:
        if duration_seconds > policy.max_duration_seconds:
            return SLAResult(
                job_name=policy.job_name,
                breached=True,
                reason=(
                    f"duration {duration_seconds:.1f}s exceeded limit "
                    f"{policy.max_duration_seconds:.1f}s"
                ),
            )

    if policy.must_run_by is not None and run_time is not None:
        # Simple lexicographic HH:MM comparison
        if run_time > policy.must_run_by:
            return SLAResult(
                job_name=policy.job_name,
                breached=True,
                reason=f"completed at {run_time}, deadline was {policy.must_run_by}",
            )

    return SLAResult(job_name=policy.job_name, breached=False)
