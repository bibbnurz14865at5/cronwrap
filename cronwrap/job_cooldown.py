"""Job cooldown policy — enforces a minimum gap between successive runs."""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional


class CooldownError(Exception):
    """Raised when a job is invoked before its cooldown period has elapsed."""


@dataclass
class CooldownPolicy:
    job_name: str
    min_gap_seconds: int
    state_dir: str = "/tmp/cronwrap/cooldown"

    @classmethod
    def from_dict(cls, data: dict) -> "CooldownPolicy":
        return cls(
            job_name=data["job_name"],
            min_gap_seconds=int(data["min_gap_seconds"]),
            state_dir=data.get("state_dir", "/tmp/cronwrap/cooldown"),
        )

    def to_dict(self) -> dict:
        return {
            "job_name": self.job_name,
            "min_gap_seconds": self.min_gap_seconds,
            "state_dir": self.state_dir,
        }

    def _state_path(self) -> Path:
        return Path(self.state_dir) / f"{self.job_name}.json"

    def _load_last_run(self) -> Optional[float]:
        p = self._state_path()
        if not p.exists():
            return None
        try:
            return float(json.loads(p.read_text()).get("last_run", 0))
        except (ValueError, KeyError, json.JSONDecodeError):
            return None

    def _save_last_run(self, ts: float) -> None:
        p = self._state_path()
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps({"last_run": ts}))

    def seconds_remaining(self) -> float:
        """Return how many seconds remain in the cooldown (0 if ready)."""
        last = self._load_last_run()
        if last is None:
            return 0.0
        elapsed = time.time() - last
        remaining = self.min_gap_seconds - elapsed
        return max(0.0, remaining)

    def check(self) -> None:
        """Raise CooldownError if the cooldown period has not yet elapsed."""
        remaining = self.seconds_remaining()
        if remaining > 0:
            raise CooldownError(
                f"Job '{self.job_name}' is in cooldown for another "
                f"{remaining:.1f}s (min_gap={self.min_gap_seconds}s)."
            )

    def record(self) -> None:
        """Record the current time as the last run timestamp."""
        self._save_last_run(time.time())

    def check_and_record(self) -> None:
        """Convenience: check then immediately record the run."""
        self.check()
        self.record()

    def reset(self) -> None:
        """Clear the cooldown state for this job."""
        p = self._state_path()
        if p.exists():
            p.unlink()
