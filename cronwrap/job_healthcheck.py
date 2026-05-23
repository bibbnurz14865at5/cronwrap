"""Job health check module for cronwrap.

Provides a simple health-check status store that records whether a job
is considered healthy, degraded, or unhealthy based on recent history.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional


HEALTH_OK = "ok"
HEALTH_DEGRADED = "degraded"
HEALTH_UNHEALTHY = "unhealthy"

VALID_STATUSES = {HEALTH_OK, HEALTH_DEGRADED, HEALTH_UNHEALTHY}


class HealthCheckError(Exception):
    """Raised when a health-check operation fails."""


@dataclass
class HealthStatus:
    job_name: str
    status: str
    checked_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    message: Optional[str] = None
    extra: dict = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.status not in VALID_STATUSES:
            raise HealthCheckError(
                f"Invalid status {self.status!r}. Must be one of {sorted(VALID_STATUSES)}."
            )

    def to_dict(self) -> dict:
        d: dict = {
            "job_name": self.job_name,
            "status": self.status,
            "checked_at": self.checked_at,
        }
        if self.message is not None:
            d["message"] = self.message
        if self.extra:
            d["extra"] = self.extra
        return d

    @classmethod
    def from_dict(cls, data: dict) -> "HealthStatus":
        return cls(
            job_name=data["job_name"],
            status=data["status"],
            checked_at=data.get("checked_at", datetime.now(timezone.utc).isoformat()),
            message=data.get("message"),
            extra=data.get("extra", {}),
        )


class JobHealthCheck:
    """Persist and retrieve health-check status for jobs."""

    def __init__(self, state_dir: str) -> None:
        self.state_dir = Path(state_dir)
        self.state_dir.mkdir(parents=True, exist_ok=True)

    def _path(self, job_name: str) -> Path:
        safe = job_name.replace(os.sep, "_")
        return self.state_dir / f"{safe}.health.json"

    def record(self, status: HealthStatus) -> None:
        """Persist a health status to disk."""
        self._path(status.job_name).write_text(
            json.dumps(status.to_dict(), indent=2), encoding="utf-8"
        )

    def get(self, job_name: str) -> Optional[HealthStatus]:
        """Return the last recorded health status, or None if not found."""
        p = self._path(job_name)
        if not p.exists():
            return None
        data = json.loads(p.read_text(encoding="utf-8"))
        return HealthStatus.from_dict(data)

    def is_healthy(self, job_name: str) -> bool:
        """Return True only if the last recorded status is 'ok'."""
        status = self.get(job_name)
        return status is not None and status.status == HEALTH_OK
