"""Job throttle: limit how often a job can run within a time window."""
from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional


class ThrottleError(Exception):
    """Raised when a job is throttled."""


@dataclass
class ThrottlePolicy:
    job_name: str
    min_interval_seconds: int
    state_dir: str = "/tmp/cronwrap/throttle"

    @classmethod
    def from_dict(cls, data: dict) -> "ThrottlePolicy":
        return cls(
            job_name=data["job_name"],
            min_interval_seconds=int(data["min_interval_seconds"]),
            state_dir=data.get("state_dir", "/tmp/cronwrap/throttle"),
        )

    def to_dict(self) -> dict:
        return {
            "job_name": self.job_name,
            "min_interval_seconds": self.min_interval_seconds,
            "state_dir": self.state_dir,
        }

    def _state_path(self) -> Path:
        return Path(self.state_dir) / f"{self.job_name}.json"

    def _load_last_run(self) -> Optional[float]:
        path = self._state_path()
        if not path.exists():
            return None
        try:
            data = json.loads(path.read_text())
            return float(data.get("last_run", 0))
        except (json.JSONDecodeError, ValueError):
            return None

    def _save_last_run(self, ts: float) -> None:
        path = self._state_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps({"last_run": ts}))

    def check(self) -> float:
        """Return seconds remaining in throttle window (0 if allowed)."""
        last = self._load_last_run()
        if last is None:
            return 0.0
        elapsed = time.time() - last
        remaining = self.min_interval_seconds - elapsed
        return max(0.0, remaining)

    def acquire(self) -> None:
        """Record that the job is running now, or raise ThrottleError."""
        remaining = self.check()
        if remaining > 0:
            raise ThrottleError(
                f"Job '{self.job_name}' is throttled; "
                f"{remaining:.1f}s remaining in window."
            )
        self._save_last_run(time.time())

    def reset(self) -> None:
        """Clear throttle state for this job."""
        path = self._state_path()
        if path.exists():
            path.unlink()
