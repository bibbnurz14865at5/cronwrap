"""Per-job run quota enforcement (max runs per time window)."""
from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional


class QuotaExceeded(Exception):
    """Raised when a job has exceeded its allowed run quota."""


@dataclass
class QuotaPolicy:
    max_runs: int
    window_seconds: int
    state_dir: str = "/tmp/cronwrap/quota"

    @classmethod
    def from_dict(cls, data: dict) -> "QuotaPolicy":
        return cls(
            max_runs=int(data["max_runs"]),
            window_seconds=int(data["window_seconds"]),
            state_dir=data.get("state_dir", "/tmp/cronwrap/quota"),
        )

    def to_dict(self) -> dict:
        return {
            "max_runs": self.max_runs,
            "window_seconds": self.window_seconds,
            "state_dir": self.state_dir,
        }

    def _state_path(self, job_name: str) -> Path:
        p = Path(self.state_dir)
        p.mkdir(parents=True, exist_ok=True)
        return p / f"{job_name}.json"

    def _load_timestamps(self, job_name: str) -> List[float]:
        path = self._state_path(job_name)
        if not path.exists():
            return []
        try:
            return json.loads(path.read_text())
        except (json.JSONDecodeError, ValueError):
            return []

    def _save_timestamps(self, job_name: str, timestamps: List[float]) -> None:
        self._state_path(job_name).write_text(json.dumps(timestamps))

    def _prune(self, timestamps: List[float], now: float) -> List[float]:
        cutoff = now - self.window_seconds
        return [t for t in timestamps if t >= cutoff]

    def check(self, job_name: str, now: Optional[float] = None) -> int:
        """Return remaining runs allowed. Raises QuotaExceeded if limit hit."""
        now = now or time.time()
        timestamps = self._prune(self._load_timestamps(job_name), now)
        remaining = self.max_runs - len(timestamps)
        if remaining <= 0:
            raise QuotaExceeded(
                f"Job '{job_name}' has reached {self.max_runs} runs "
                f"within the last {self.window_seconds}s window."
            )
        return remaining

    def record(self, job_name: str, now: Optional[float] = None) -> None:
        """Record a run timestamp for the job."""
        now = now or time.time()
        timestamps = self._prune(self._load_timestamps(job_name), now)
        timestamps.append(now)
        self._save_timestamps(job_name, timestamps)

    def reset(self, job_name: str) -> None:
        """Clear all recorded timestamps for the job."""
        self._state_path(job_name).unlink(missing_ok=True)
