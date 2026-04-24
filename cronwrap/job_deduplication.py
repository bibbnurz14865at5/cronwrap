"""Job deduplication: prevent duplicate runs of the same job within a time window."""

from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional


class DeduplicationError(Exception):
    """Raised when a duplicate job execution is detected."""


@dataclass
class DeduplicationPolicy:
    job_name: str
    window_seconds: int
    state_dir: str = "/tmp/cronwrap/dedup"

    @classmethod
    def from_dict(cls, data: dict) -> "DeduplicationPolicy":
        required = {"job_name", "window_seconds"}
        missing = required - data.keys()
        if missing:
            raise ValueError(f"Missing required keys: {missing}")
        return cls(
            job_name=data["job_name"],
            window_seconds=int(data["window_seconds"]),
            state_dir=data.get("state_dir", "/tmp/cronwrap/dedup"),
        )

    def to_dict(self) -> dict:
        return {
            "job_name": self.job_name,
            "window_seconds": self.window_seconds,
            "state_dir": self.state_dir,
        }

    def _state_path(self) -> Path:
        return Path(self.state_dir) / f"{self.job_name}.dedup.json"

    def _load_state(self) -> Optional[dict]:
        p = self._state_path()
        if not p.exists():
            return None
        with p.open() as fh:
            return json.load(fh)

    def _save_state(self, run_id: str) -> None:
        p = self._state_path()
        p.parent.mkdir(parents=True, exist_ok=True)
        with p.open("w") as fh:
            json.dump({"run_id": run_id, "started_at": time.time()}, fh)

    def _clear_state(self) -> None:
        p = self._state_path()
        if p.exists():
            p.unlink()

    def check(self, run_id: str) -> None:
        """Raise DeduplicationError if a duplicate run is detected within the window."""
        state = self._load_state()
        if state is None:
            self._save_state(run_id)
            return
        age = time.time() - state["started_at"]
        if age < self.window_seconds and state["run_id"] != run_id:
            raise DeduplicationError(
                f"Duplicate run detected for '{self.job_name}': "
                f"run '{state['run_id']}' started {age:.1f}s ago "
                f"(window={self.window_seconds}s)"
            )
        self._save_state(run_id)

    def release(self) -> None:
        """Clear deduplication state after a job completes."""
        self._clear_state()
