"""Job suppression: temporarily suppress notifications for a job."""
from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional


class SuppressionError(Exception):
    """Raised when a suppression operation fails."""


@dataclass
class SuppressionState:
    job_name: str
    suppressed_until: datetime
    reason: Optional[str] = None

    def is_active(self, now: Optional[datetime] = None) -> bool:
        now = now or datetime.now(timezone.utc)
        return now < self.suppressed_until

    def to_dict(self) -> dict:
        d: dict = {
            "job_name": self.job_name,
            "suppressed_until": self.suppressed_until.isoformat(),
        }
        if self.reason is not None:
            d["reason"] = self.reason
        return d

    @classmethod
    def from_dict(cls, data: dict) -> "SuppressionState":
        return cls(
            job_name=data["job_name"],
            suppressed_until=datetime.fromisoformat(data["suppressed_until"]),
            reason=data.get("reason"),
        )


class JobSuppression:
    def __init__(self, state_dir: str = "/tmp/cronwrap/suppression") -> None:
        self.state_dir = Path(state_dir)
        self.state_dir.mkdir(parents=True, exist_ok=True)

    def _path(self, job_name: str) -> Path:
        return self.state_dir / f"{job_name}.json"

    def suppress(self, job_name: str, until: datetime, reason: Optional[str] = None) -> SuppressionState:
        state = SuppressionState(job_name=job_name, suppressed_until=until, reason=reason)
        self._path(job_name).write_text(json.dumps(state.to_dict()))
        return state

    def resume(self, job_name: str) -> None:
        p = self._path(job_name)
        if p.exists():
            p.unlink()

    def get(self, job_name: str) -> Optional[SuppressionState]:
        p = self._path(job_name)
        if not p.exists():
            return None
        return SuppressionState.from_dict(json.loads(p.read_text()))

    def is_suppressed(self, job_name: str, now: Optional[datetime] = None) -> bool:
        state = self.get(job_name)
        if state is None:
            return False
        return state.is_active(now=now)

    def list_suppressed(self, now: Optional[datetime] = None) -> list:
        results = []
        for p in sorted(self.state_dir.glob("*.json")):
            try:
                state = SuppressionState.from_dict(json.loads(p.read_text()))
                if state.is_active(now=now):
                    results.append(state)
            except Exception:
                continue
        return results
