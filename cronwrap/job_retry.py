"""Job retry policy — track and enforce per-job retry limits."""
from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional


class RetryError(Exception):
    """Raised when retry limit is exceeded."""


@dataclass
class RetryPolicy:
    job_name: str
    max_retries: int = 3
    retry_delay: float = 0.0  # seconds between retries
    state_dir: str = "/tmp/cronwrap/retry"

    @classmethod
    def from_dict(cls, data: dict) -> "RetryPolicy":
        return cls(
            job_name=data["job_name"],
            max_retries=int(data.get("max_retries", 3)),
            retry_delay=float(data.get("retry_delay", 0.0)),
            state_dir=data.get("state_dir", "/tmp/cronwrap/retry"),
        )

    def to_dict(self) -> dict:
        return {
            "job_name": self.job_name,
            "max_retries": self.max_retries,
            "retry_delay": self.retry_delay,
            "state_dir": self.state_dir,
        }

    def _state_path(self) -> Path:
        return Path(self.state_dir) / f"{self.job_name}.retry.json"

    def _load_state(self) -> dict:
        p = self._state_path()
        if p.exists():
            return json.loads(p.read_text())
        return {"attempts": 0, "last_attempt": None}

    def _save_state(self, state: dict) -> None:
        p = self._state_path()
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(state))

    def record_attempt(self) -> int:
        """Record a failed attempt. Returns current attempt count."""
        state = self._load_state()
        state["attempts"] += 1
        state["last_attempt"] = time.time()
        self._save_state(state)
        return state["attempts"]

    def attempts(self) -> int:
        return self._load_state()["attempts"]

    def exhausted(self) -> bool:
        return self.attempts() >= self.max_retries

    def reset(self) -> None:
        """Clear retry state after a successful run."""
        p = self._state_path()
        if p.exists():
            p.unlink()

    def check(self) -> None:
        """Raise RetryError if retries are exhausted."""
        if self.exhausted():
            raise RetryError(
                f"Job '{self.job_name}' has exhausted {self.max_retries} retries."
            )
