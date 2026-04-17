"""Append-only audit log for cron job events."""
from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional


@dataclass
class AuditEvent:
    event: str          # e.g. "run_start", "run_end", "alert_sent"
    job: str
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    detail: Optional[str] = None
    exit_code: Optional[int] = None

    def to_dict(self) -> dict:
        d = {"event": self.event, "job": self.job, "timestamp": self.timestamp}
        if self.detail is not None:
            d["detail"] = self.detail
        if self.exit_code is not None:
            d["exit_code"] = self.exit_code
        return d

    @classmethod
    def from_dict(cls, data: dict) -> "AuditEvent":
        return cls(
            event=data["event"],
            job=data["job"],
            timestamp=data.get("timestamp", datetime.now(timezone.utc).isoformat()),
            detail=data.get("detail"),
            exit_code=data.get("exit_code"),
        )


class AuditLog:
    def __init__(self, path: str) -> None:
        self.path = Path(path)

    def append(self, event: AuditEvent) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("a") as fh:
            fh.write(json.dumps(event.to_dict()) + "\n")

    def read(self, job: Optional[str] = None) -> List[AuditEvent]:
        if not self.path.exists():
            return []
        events = []
        with self.path.open() as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                ev = AuditEvent.from_dict(json.loads(line))
                if job is None or ev.job == job:
                    events.append(ev)
        return events

    def tail(self, n: int = 20, job: Optional[str] = None) -> List[AuditEvent]:
        return self.read(job=job)[-n:]
