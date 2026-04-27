"""Quota reset scheduling for cronwrap jobs.

Allows quota windows to be reset on a schedule (daily, weekly, monthly)
or manually via CLI.
"""
from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional


class QuotaResetError(Exception):
    """Raised when a quota reset operation fails."""


VALID_PERIODS = ("hourly", "daily", "weekly", "monthly")


@dataclass
class QuotaResetPolicy:
    job_name: str
    period: str  # hourly | daily | weekly | monthly
    state_dir: str = "/tmp/cronwrap/quota_reset"
    last_reset: Optional[str] = field(default=None)

    def __post_init__(self) -> None:
        if self.period not in VALID_PERIODS:
            raise QuotaResetError(
                f"Invalid period {self.period!r}. Must be one of {VALID_PERIODS}."
            )

    # ------------------------------------------------------------------
    @classmethod
    def from_dict(cls, data: dict) -> "QuotaResetPolicy":
        required = {"job_name", "period"}
        missing = required - data.keys()
        if missing:
            raise QuotaResetError(f"Missing required keys: {missing}")
        return cls(
            job_name=data["job_name"],
            period=data["period"],
            state_dir=data.get("state_dir", "/tmp/cronwrap/quota_reset"),
            last_reset=data.get("last_reset"),
        )

    def to_dict(self) -> dict:
        return {
            "job_name": self.job_name,
            "period": self.period,
            "state_dir": self.state_dir,
            "last_reset": self.last_reset,
        }

    # ------------------------------------------------------------------
    def _state_path(self) -> Path:
        return Path(self.state_dir) / f"{self.job_name}.reset.json"

    def _load_state(self) -> dict:
        p = self._state_path()
        if p.exists():
            return json.loads(p.read_text())
        return {}

    def _save_state(self, state: dict) -> None:
        p = self._state_path()
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(state))

    def needs_reset(self, now: Optional[datetime] = None) -> bool:
        """Return True if the quota window has expired and a reset is due."""
        state = self._load_state()
        last = state.get("last_reset")
        if last is None:
            return True
        now = now or datetime.now(timezone.utc)
        last_dt = datetime.fromisoformat(last)
        if last_dt.tzinfo is None:
            last_dt = last_dt.replace(tzinfo=timezone.utc)
        delta = (now - last_dt).total_seconds()
        thresholds = {
            "hourly": 3600,
            "daily": 86400,
            "weekly": 604800,
            "monthly": 2592000,
        }
        return delta >= thresholds[self.period]

    def reset(self, now: Optional[datetime] = None) -> str:
        """Record a reset and return the ISO timestamp."""
        now = now or datetime.now(timezone.utc)
        ts = now.isoformat()
        self._save_state({"last_reset": ts, "job_name": self.job_name})
        return ts

    def last_reset_time(self) -> Optional[str]:
        return self._load_state().get("last_reset")
