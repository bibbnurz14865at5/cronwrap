"""Structured event log for cron job lifecycle events.

Records discrete events (start, finish, error, skip, etc.) per job
to a newline-delimited JSON file, enabling audit trails and debugging
beyond what the run history alone provides.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Iterator, List, Optional

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

KNOWN_EVENTS = {
    "start",
    "finish",
    "error",
    "skip",
    "timeout",
    "retry",
    "paused",
    "resumed",
    "muted",
    "unmuted",
}


# ---------------------------------------------------------------------------
# Errors
# ---------------------------------------------------------------------------

class EventLogError(Exception):
    """Raised when an event log operation fails."""


# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------

@dataclass
class EventRecord:
    """A single structured event entry."""

    job_name: str
    event: str
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    message: Optional[str] = None
    extra: Dict[str, object] = field(default_factory=dict)

    def to_dict(self) -> dict:
        d: dict = {
            "job_name": self.job_name,
            "event": self.event,
            "timestamp": self.timestamp,
        }
        if self.message is not None:
            d["message"] = self.message
        if self.extra:
            d["extra"] = self.extra
        return d

    @classmethod
    def from_dict(cls, data: dict) -> "EventRecord":
        return cls(
            job_name=data["job_name"],
            event=data["event"],
            timestamp=data.get("timestamp", datetime.now(timezone.utc).isoformat()),
            message=data.get("message"),
            extra=data.get("extra", {}),
        )


# ---------------------------------------------------------------------------
# Event log store
# ---------------------------------------------------------------------------

class JobEventLog:
    """Append-only event log backed by a newline-delimited JSON file."""

    def __init__(self, log_dir: str) -> None:
        self._dir = Path(log_dir)
        self._dir.mkdir(parents=True, exist_ok=True)

    def _path(self, job_name: str) -> Path:
        safe = job_name.replace(os.sep, "_").replace(" ", "_")
        return self._dir / f"{safe}.jsonl"

    def append(self, record: EventRecord) -> None:
        """Append *record* to the job's event log file."""
        with self._path(record.job_name).open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(record.to_dict()) + "\n")

    def log(self, job_name: str, event: str, *,
            message: Optional[str] = None,
            extra: Optional[Dict[str, object]] = None) -> EventRecord:
        """Create and persist an event record, returning it."""
        rec = EventRecord(
            job_name=job_name,
            event=event,
            message=message,
            extra=extra or {},
        )
        self.append(rec)
        return rec

    def iter_events(self, job_name: str) -> Iterator[EventRecord]:
        """Yield all recorded events for *job_name* in chronological order."""
        path = self._path(job_name)
        if not path.exists():
            return
        with path.open("r", encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if line:
                    yield EventRecord.from_dict(json.loads(line))

    def read_events(self, job_name: str) -> List[EventRecord]:
        """Return all events for *job_name* as a list."""
        return list(self.iter_events(job_name))

    def clear(self, job_name: str) -> None:
        """Delete the event log for *job_name*."""
        path = self._path(job_name)
        if path.exists():
            path.unlink()
