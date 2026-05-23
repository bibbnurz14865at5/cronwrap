"""Job execution capping — limits the number of times a job may run
within a rolling time window."""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import List


class CappingError(Exception):
    """Raised when a capping operation fails."""


@dataclass
class CappingPolicy:
    job_name: str
    max_runs: int
    window_seconds: int
    state_dir: str = "/tmp/cronwrap/capping"

    @classmethod
    def from_dict(cls, data: dict) -> "CappingPolicy":
        required = ("job_name", "max_runs", "window_seconds")
        for key in required:
            if key not in data:
                raise CappingError(f"Missing required field: {key}")
        return cls(
            job_name=data["job_name"],
            max_runs=int(data["max_runs"]),
            window_seconds=int(data["window_seconds"]),
            state_dir=data.get("state_dir", "/tmp/cronwrap/capping"),
        )

    def to_dict(self) -> dict:
        return {
            "job_name": self.job_name,
            "max_runs": self.max_runs,
            "window_seconds": self.window_seconds,
            "state_dir": self.state_dir,
        }

    def _state_path(self) -> Path:
        return Path(self.state_dir) / f"{self.job_name}.json"

    def _load_timestamps(self) -> List[float]:
        p = self._state_path()
        if not p.exists():
            return []
        try:
            return json.loads(p.read_text())
        except (json.JSONDecodeError, OSError):
            return []

    def _save_timestamps(self, timestamps: List[float]) -> None:
        p = self._state_path()
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(timestamps))

    def _active_timestamps(self, now: float) -> List[float]:
        cutoff = now - self.window_seconds
        return [t for t in self._load_timestamps() if t >= cutoff]

    def check(self) -> bool:
        """Return True if the job is allowed to run, False if capped."""
        now = time.time()
        active = self._active_timestamps(now)
        return len(active) < self.max_runs

    def record_run(self) -> None:
        """Record a run timestamp, pruning stale entries."""
        now = time.time()
        active = self._active_timestamps(now)
        active.append(now)
        self._save_timestamps(active)

    def remaining(self) -> int:
        """Return how many runs are still allowed in the current window."""
        now = time.time()
        active = self._active_timestamps(now)
        return max(0, self.max_runs - len(active))

    def reset(self) -> None:
        """Clear all recorded runs."""
        p = self._state_path()
        if p.exists():
            p.unlink()
