"""Track and query the current status of known cron jobs."""
from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional


STATUS_UNKNOWN = "unknown"
STATUS_RUNNING = "running"
STATUS_SUCCESS = "success"
STATUS_FAILURE = "failure"

VALID_STATUSES = {STATUS_UNKNOWN, STATUS_RUNNING, STATUS_SUCCESS, STATUS_FAILURE}


class StatusError(Exception):
    """Raised when an invalid status operation is attempted."""


@dataclass
class StatusEntry:
    job_name: str
    status: str
    updated_at: float = field(default_factory=time.time)
    message: Optional[str] = None

    def to_dict(self) -> Dict:
        d = {
            "job_name": self.job_name,
            "status": self.status,
            "updated_at": self.updated_at,
        }
        if self.message is not None:
            d["message"] = self.message
        return d

    @classmethod
    def from_dict(cls, data: Dict) -> "StatusEntry":
        return cls(
            job_name=data["job_name"],
            status=data["status"],
            updated_at=data.get("updated_at", time.time()),
            message=data.get("message"),
        )


class JobStatusStore:
    """Persist and retrieve per-job status entries on disk."""

    def __init__(self, state_dir: str) -> None:
        self._dir = Path(state_dir)
        self._dir.mkdir(parents=True, exist_ok=True)

    def _path(self, job_name: str) -> Path:
        safe = job_name.replace("/", "_").replace(" ", "_")
        return self._dir / f"{safe}.status.json"

    def set(self, job_name: str, status: str, message: Optional[str] = None) -> StatusEntry:
        if status not in VALID_STATUSES:
            raise StatusError(f"Invalid status {status!r}; choose from {sorted(VALID_STATUSES)}")
        entry = StatusEntry(job_name=job_name, status=status, message=message)
        self._path(job_name).write_text(json.dumps(entry.to_dict()), encoding="utf-8")
        return entry

    def get(self, job_name: str) -> StatusEntry:
        p = self._path(job_name)
        if not p.exists():
            return StatusEntry(job_name=job_name, status=STATUS_UNKNOWN)
        data = json.loads(p.read_text(encoding="utf-8"))
        return StatusEntry.from_dict(data)

    def all(self) -> List[StatusEntry]:
        entries = []
        for p in sorted(self._dir.glob("*.status.json")):
            data = json.loads(p.read_text(encoding="utf-8"))
            entries.append(StatusEntry.from_dict(data))
        return entries

    def delete(self, job_name: str) -> bool:
        p = self._path(job_name)
        if p.exists():
            p.unlink()
            return True
        return False
