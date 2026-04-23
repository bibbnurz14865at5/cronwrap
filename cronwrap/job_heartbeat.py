"""Job heartbeat tracking — records periodic pings and detects missed heartbeats."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional


@dataclass
class HeartbeatRecord:
    job_name: str
    last_ping: datetime
    interval_seconds: int
    extra: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        d = {
            "job_name": self.job_name,
            "last_ping": self.last_ping.isoformat(),
            "interval_seconds": self.interval_seconds,
        }
        if self.extra:
            d["extra"] = self.extra
        return d

    @classmethod
    def from_dict(cls, data: dict) -> "HeartbeatRecord":
        return cls(
            job_name=data["job_name"],
            last_ping=datetime.fromisoformat(data["last_ping"]),
            interval_seconds=int(data["interval_seconds"]),
            extra=data.get("extra", {}),
        )


@dataclass
class MissedHeartbeat:
    job_name: str
    last_ping: datetime
    interval_seconds: int
    seconds_overdue: float

    def __repr__(self) -> str:
        return (
            f"MissedHeartbeat(job={self.job_name!r}, "
            f"overdue_by={self.seconds_overdue:.1f}s)"
        )


class JobHeartbeat:
    """Persist and query heartbeat pings for cron jobs."""

    def __init__(self, state_dir: str) -> None:
        self._dir = Path(state_dir)
        self._dir.mkdir(parents=True, exist_ok=True)

    def _path(self, job_name: str) -> Path:
        safe = job_name.replace(os.sep, "_").replace(" ", "_")
        return self._dir / f"{safe}.heartbeat.json"

    def ping(self, job_name: str, interval_seconds: int, extra: Optional[dict] = None) -> HeartbeatRecord:
        """Record a heartbeat ping for *job_name*."""
        record = HeartbeatRecord(
            job_name=job_name,
            last_ping=datetime.now(tz=timezone.utc),
            interval_seconds=interval_seconds,
            extra=extra or {},
        )
        self._path(job_name).write_text(json.dumps(record.to_dict(), indent=2))
        return record

    def last(self, job_name: str) -> Optional[HeartbeatRecord]:
        """Return the most recent heartbeat record, or *None* if absent."""
        p = self._path(job_name)
        if not p.exists():
            return None
        return HeartbeatRecord.from_dict(json.loads(p.read_text()))

    def check_missed(self, job_name: str, now: Optional[datetime] = None) -> Optional[MissedHeartbeat]:
        """Return a *MissedHeartbeat* if the job is overdue, else *None*."""
        record = self.last(job_name)
        if record is None:
            return None
        now = now or datetime.now(tz=timezone.utc)
        elapsed = (now - record.last_ping).total_seconds()
        if elapsed > record.interval_seconds:
            return MissedHeartbeat(
                job_name=job_name,
                last_ping=record.last_ping,
                interval_seconds=record.interval_seconds,
                seconds_overdue=elapsed - record.interval_seconds,
            )
        return None
