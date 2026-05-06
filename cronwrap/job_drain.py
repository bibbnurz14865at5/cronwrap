"""job_drain.py – graceful drain support for cron jobs.

A 'drain' marks a job as draining so that new runs are skipped while
existing runs are allowed to finish.  State is persisted to a JSON file.
"""
from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional


class DrainError(Exception):
    """Raised on invalid drain operations."""


@dataclass
class DrainState:
    job_name: str
    drained_at: str
    reason: Optional[str] = None

    def is_active(self) -> bool:
        return True  # presence of the file means draining

    def to_dict(self) -> dict:
        d: dict = {"job_name": self.job_name, "drained_at": self.drained_at}
        if self.reason is not None:
            d["reason"] = self.reason
        return d

    @classmethod
    def from_dict(cls, data: dict) -> "DrainState":
        return cls(
            job_name=data["job_name"],
            drained_at=data["drained_at"],
            reason=data.get("reason"),
        )


class JobDrain:
    def __init__(self, state_dir: str) -> None:
        self._dir = Path(state_dir)

    def _path(self, job_name: str) -> Path:
        return self._dir / f"{job_name}.drain.json"

    def drain(self, job_name: str, reason: Optional[str] = None) -> DrainState:
        """Mark *job_name* as draining."""
        if not job_name:
            raise DrainError("job_name must not be empty")
        self._dir.mkdir(parents=True, exist_ok=True)
        now = datetime.now(timezone.utc).isoformat()
        state = DrainState(job_name=job_name, drained_at=now, reason=reason)
        self._path(job_name).write_text(json.dumps(state.to_dict(), indent=2))
        return state

    def undrain(self, job_name: str) -> None:
        """Remove the drain marker for *job_name*."""
        p = self._path(job_name)
        if p.exists():
            p.unlink()

    def is_draining(self, job_name: str) -> bool:
        """Return True if *job_name* is currently marked as draining."""
        return self._path(job_name).exists()

    def get(self, job_name: str) -> Optional[DrainState]:
        """Return the DrainState for *job_name*, or None if not draining."""
        p = self._path(job_name)
        if not p.exists():
            return None
        return DrainState.from_dict(json.loads(p.read_text()))

    def list_draining(self) -> list[str]:
        """Return sorted list of job names currently draining."""
        if not self._dir.exists():
            return []
        return sorted(
            p.stem.replace(".drain", "")
            for p in self._dir.glob("*.drain.json")
        )
