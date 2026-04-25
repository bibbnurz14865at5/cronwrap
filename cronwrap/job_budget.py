"""Job execution budget tracking — enforce max allowed runs per time window."""
from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional


class BudgetError(Exception):
    """Raised when a job exceeds its execution budget."""


@dataclass
class BudgetPolicy:
    job_name: str
    max_runs: int
    window_seconds: int
    state_dir: str = "/tmp/cronwrap/budget"

    @classmethod
    def from_dict(cls, data: dict) -> "BudgetPolicy":
        required = {"job_name", "max_runs", "window_seconds"}
        missing = required - data.keys()
        if missing:
            raise ValueError(f"BudgetPolicy missing keys: {missing}")
        return cls(
            job_name=data["job_name"],
            max_runs=int(data["max_runs"]),
            window_seconds=int(data["window_seconds"]),
            state_dir=data.get("state_dir", "/tmp/cronwrap/budget"),
        )

    def to_dict(self) -> dict:
        return {
            "job_name": self.job_name,
            "max_runs": self.max_runs,
            "window_seconds": self.window_seconds,
            "state_dir": self.state_dir,
        }

    def _state_path(self) -> Path:
        p = Path(self.state_dir)
        p.mkdir(parents=True, exist_ok=True)
        return p / f"{self.job_name}.json"

    def _load_timestamps(self) -> List[float]:
        path = self._state_path()
        if not path.exists():
            return []
        try:
            return json.loads(path.read_text())
        except (json.JSONDecodeError, ValueError):
            return []

    def _save_timestamps(self, timestamps: List[float]) -> None:
        self._state_path().write_text(json.dumps(timestamps))

    def _prune(self, timestamps: List[float], now: float) -> List[float]:
        cutoff = now - self.window_seconds
        return [t for t in timestamps if t >= cutoff]

    def check(self, now: Optional[float] = None) -> int:
        """Return remaining runs in the current window.

        Raises BudgetError if the budget is exhausted.
        """
        now = now if now is not None else time.time()
        timestamps = self._prune(self._load_timestamps(), now)
        remaining = self.max_runs - len(timestamps)
        if remaining <= 0:
            raise BudgetError(
                f"Job '{self.job_name}' has exhausted its budget of "
                f"{self.max_runs} runs per {self.window_seconds}s window."
            )
        return remaining

    def record(self, now: Optional[float] = None) -> None:
        """Record a run timestamp (call after check succeeds)."""
        now = now if now is not None else time.time()
        timestamps = self._prune(self._load_timestamps(), now)
        timestamps.append(now)
        self._save_timestamps(timestamps)

    def reset(self) -> None:
        """Clear all recorded run timestamps."""
        self._save_timestamps([])

    def current_count(self, now: Optional[float] = None) -> int:
        """Return the number of runs recorded in the current window."""
        now = now if now is not None else time.time()
        return len(self._prune(self._load_timestamps(), now))
