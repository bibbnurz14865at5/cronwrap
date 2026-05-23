"""Grace period policy: suppress alerts for a job during an initial window after registration."""
from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional


class GracePeriodError(Exception):
    """Raised on invalid grace period configuration."""


@dataclass
class GracePeriodPolicy:
    job_name: str
    duration_seconds: int
    state_dir: str = "/tmp/cronwrap/grace"
    reason: Optional[str] = None

    @classmethod
    def from_dict(cls, data: dict) -> "GracePeriodPolicy":
        if "job_name" not in data:
            raise GracePeriodError("'job_name' is required")
        if "duration_seconds" not in data:
            raise GracePeriodError("'duration_seconds' is required")
        duration = int(data["duration_seconds"])
        if duration <= 0:
            raise GracePeriodError("'duration_seconds' must be positive")
        return cls(
            job_name=data["job_name"],
            duration_seconds=duration,
            state_dir=data.get("state_dir", "/tmp/cronwrap/grace"),
            reason=data.get("reason"),
        )

    def to_dict(self) -> dict:
        d: dict = {
            "job_name": self.job_name,
            "duration_seconds": self.duration_seconds,
            "state_dir": self.state_dir,
        }
        if self.reason is not None:
            d["reason"] = self.reason
        return d

    def _state_path(self) -> Path:
        return Path(self.state_dir) / f"{self.job_name}.grace.json"

    def activate(self, now: Optional[datetime] = None) -> None:
        """Record the grace period start time on disk."""
        now = now or datetime.now(timezone.utc)
        Path(self.state_dir).mkdir(parents=True, exist_ok=True)
        state = {
            "job_name": self.job_name,
            "started_at": now.isoformat(),
            "duration_seconds": self.duration_seconds,
        }
        self._state_path().write_text(json.dumps(state))

    def is_active(self, now: Optional[datetime] = None) -> bool:
        """Return True if the job is still within its grace period."""
        path = self._state_path()
        if not path.exists():
            return False
        now = now or datetime.now(timezone.utc)
        state = json.loads(path.read_text())
        started_at = datetime.fromisoformat(state["started_at"])
        if started_at.tzinfo is None:
            started_at = started_at.replace(tzinfo=timezone.utc)
        elapsed = (now - started_at).total_seconds()
        return elapsed < state["duration_seconds"]

    def deactivate(self) -> None:
        """Remove the grace period state file."""
        path = self._state_path()
        if path.exists():
            path.unlink()
