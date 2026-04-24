"""Job correlation ID tracking — attach and retrieve correlation IDs for job runs."""
from __future__ import annotations

import json
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional


class CorrelationError(Exception):
    """Raised when a correlation operation fails."""


@dataclass
class CorrelationRecord:
    job_name: str
    correlation_id: str
    parent_id: Optional[str] = None
    extra: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        d = {
            "job_name": self.job_name,
            "correlation_id": self.correlation_id,
        }
        if self.parent_id is not None:
            d["parent_id"] = self.parent_id
        if self.extra:
            d["extra"] = self.extra
        return d

    @classmethod
    def from_dict(cls, data: dict) -> "CorrelationRecord":
        return cls(
            job_name=data["job_name"],
            correlation_id=data["correlation_id"],
            parent_id=data.get("parent_id"),
            extra=data.get("extra", {}),
        )


class JobCorrelation:
    """Persist and retrieve correlation IDs for cron job runs."""

    def __init__(self, state_dir: str) -> None:
        self._dir = Path(state_dir)
        self._dir.mkdir(parents=True, exist_ok=True)

    def _path(self, job_name: str) -> Path:
        safe = job_name.replace("/", "_").replace(" ", "_")
        return self._dir / f"{safe}.correlation.json"

    def generate(self, job_name: str, parent_id: Optional[str] = None, extra: Optional[dict] = None) -> CorrelationRecord:
        """Generate and persist a new correlation ID for *job_name*."""
        record = CorrelationRecord(
            job_name=job_name,
            correlation_id=str(uuid.uuid4()),
            parent_id=parent_id,
            extra=extra or {},
        )
        self._path(job_name).write_text(json.dumps(record.to_dict(), indent=2))
        return record

    def get(self, job_name: str) -> Optional[CorrelationRecord]:
        """Return the current correlation record for *job_name*, or None."""
        p = self._path(job_name)
        if not p.exists():
            return None
        return CorrelationRecord.from_dict(json.loads(p.read_text()))

    def clear(self, job_name: str) -> None:
        """Remove the stored correlation record for *job_name*."""
        p = self._path(job_name)
        if p.exists():
            p.unlink()

    def all_records(self) -> list[CorrelationRecord]:
        """Return all stored correlation records sorted by job name."""
        records = []
        for p in sorted(self._dir.glob("*.correlation.json")):
            try:
                records.append(CorrelationRecord.from_dict(json.loads(p.read_text())))
            except (KeyError, json.JSONDecodeError):
                continue
        return records
