"""Track and analyse job execution velocity (runs per time window)."""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional


class VelocityError(Exception):
    """Raised when velocity operations fail."""


@dataclass
class VelocityResult:
    job_name: str
    window_seconds: int
    run_count: int
    success_count: int
    failure_count: int
    runs_per_minute: float
    extra: Dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        d = {
            "job_name": self.job_name,
            "window_seconds": self.window_seconds,
            "run_count": self.run_count,
            "success_count": self.success_count,
            "failure_count": self.failure_count,
            "runs_per_minute": round(self.runs_per_minute, 4),
        }
        if self.extra:
            d["extra"] = self.extra
        return d

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), indent=2)

    @classmethod
    def from_dict(cls, data: dict) -> "VelocityResult":
        return cls(
            job_name=data["job_name"],
            window_seconds=data["window_seconds"],
            run_count=data["run_count"],
            success_count=data["success_count"],
            failure_count=data["failure_count"],
            runs_per_minute=data["runs_per_minute"],
            extra=data.get("extra", {}),
        )


def compute_velocity(
    job_name: str,
    history_dir: str,
    window_seconds: int = 3600,
    extra: Optional[Dict] = None,
) -> VelocityResult:
    """Compute run velocity for *job_name* over the last *window_seconds*."""
    if window_seconds <= 0:
        raise VelocityError("window_seconds must be positive")

    history_path = Path(history_dir) / f"{job_name}.json"
    if not history_path.exists():
        return VelocityResult(
            job_name=job_name,
            window_seconds=window_seconds,
            run_count=0,
            success_count=0,
            failure_count=0,
            runs_per_minute=0.0,
            extra=extra or {},
        )

    entries: List[dict] = json.loads(history_path.read_text())
    now = datetime.now(tz=timezone.utc).timestamp()
    cutoff = now - window_seconds

    recent = [e for e in entries if e.get("timestamp", 0) >= cutoff]
    run_count = len(recent)
    success_count = sum(1 for e in recent if e.get("success", False))
    failure_count = run_count - success_count
    runs_per_minute = (run_count / window_seconds) * 60 if run_count else 0.0

    return VelocityResult(
        job_name=job_name,
        window_seconds=window_seconds,
        run_count=run_count,
        success_count=success_count,
        failure_count=failure_count,
        runs_per_minute=runs_per_minute,
        extra=extra or {},
    )
