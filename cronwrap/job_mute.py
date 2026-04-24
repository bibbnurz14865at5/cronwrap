"""Mute (silence) alerting for a specific job for a given duration."""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional


class MuteError(Exception):
    """Raised when a mute operation fails."""


@dataclass
class MuteState:
    job_name: str
    muted_until: float  # Unix timestamp
    reason: Optional[str] = None

    def is_active(self, now: Optional[float] = None) -> bool:
        """Return True if the mute window is currently active."""
        return (now or time.time()) < self.muted_until

    def to_dict(self) -> dict:
        d: dict = {
            "job_name": self.job_name,
            "muted_until": self.muted_until,
        }
        if self.reason is not None:
            d["reason"] = self.reason
        return d

    @classmethod
    def from_dict(cls, data: dict) -> "MuteState":
        return cls(
            job_name=data["job_name"],
            muted_until=float(data["muted_until"]),
            reason=data.get("reason"),
        )


class JobMute:
    """Persist and query mute state for cron jobs."""

    def __init__(self, state_dir: str = "/tmp/cronwrap/mute") -> None:
        self._dir = Path(state_dir)
        self._dir.mkdir(parents=True, exist_ok=True)

    def _path(self, job_name: str) -> Path:
        safe = job_name.replace("/", "_").replace(" ", "_")
        return self._dir / f"{safe}.json"

    def mute(self, job_name: str, duration_seconds: int, reason: Optional[str] = None) -> MuteState:
        """Mute alerts for *job_name* for *duration_seconds* seconds."""
        if duration_seconds <= 0:
            raise MuteError("duration_seconds must be positive")
        state = MuteState(
            job_name=job_name,
            muted_until=time.time() + duration_seconds,
            reason=reason,
        )
        self._path(job_name).write_text(json.dumps(state.to_dict()))
        return state

    def unmute(self, job_name: str) -> None:
        """Remove an active mute for *job_name* (no-op if not muted)."""
        p = self._path(job_name)
        if p.exists():
            p.unlink()

    def get(self, job_name: str) -> Optional[MuteState]:
        """Return the MuteState for *job_name*, or None if absent."""
        p = self._path(job_name)
        if not p.exists():
            return None
        return MuteState.from_dict(json.loads(p.read_text()))

    def is_muted(self, job_name: str, now: Optional[float] = None) -> bool:
        """Return True if *job_name* currently has an active mute."""
        state = self.get(job_name)
        return state is not None and state.is_active(now)
