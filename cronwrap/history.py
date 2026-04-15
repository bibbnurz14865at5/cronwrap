"""Job run history tracking — stores results to a local JSON log file."""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional

DEFAULT_HISTORY_FILE = os.path.expanduser("~/.cronwrap_history.json")
MAX_ENTRIES = 500


class HistoryEntry:
    """A single recorded job run."""

    def __init__(
        self,
        job_name: str,
        command: str,
        exit_code: int,
        duration: float,
        timed_out: bool,
        timestamp: Optional[str] = None,
    ) -> None:
        self.job_name = job_name
        self.command = command
        self.exit_code = exit_code
        self.duration = duration
        self.timed_out = timed_out
        self.timestamp = timestamp or datetime.now(timezone.utc).isoformat()

    def to_dict(self) -> dict:
        return {
            "job_name": self.job_name,
            "command": self.command,
            "exit_code": self.exit_code,
            "duration": self.duration,
            "timed_out": self.timed_out,
            "timestamp": self.timestamp,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "HistoryEntry":
        return cls(
            job_name=data["job_name"],
            command=data["command"],
            exit_code=data["exit_code"],
            duration=data["duration"],
            timed_out=data["timed_out"],
            timestamp=data.get("timestamp"),
        )


class JobHistory:
    """Append-only history log backed by a JSON file."""

    def __init__(self, path: str = DEFAULT_HISTORY_FILE, max_entries: int = MAX_ENTRIES) -> None:
        self.path = Path(path)
        self.max_entries = max_entries

    def _load(self) -> List[dict]:
        if not self.path.exists():
            return []
        try:
            return json.loads(self.path.read_text())
        except (json.JSONDecodeError, OSError):
            return []

    def record(self, entry: HistoryEntry) -> None:
        """Append *entry* to the log, pruning oldest records beyond max_entries."""
        entries = self._load()
        entries.append(entry.to_dict())
        if len(entries) > self.max_entries:
            entries = entries[-self.max_entries :]
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(entries, indent=2))

    def load_all(self) -> List[HistoryEntry]:
        """Return all stored entries, oldest first."""
        return [HistoryEntry.from_dict(d) for d in self._load()]

    def load_for_job(self, job_name: str) -> List[HistoryEntry]:
        """Return entries filtered to *job_name*."""
        return [e for e in self.load_all() if e.job_name == job_name]
