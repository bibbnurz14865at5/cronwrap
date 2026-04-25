"""Job versioning — track and compare deployed versions of cron jobs."""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional


class VersioningError(Exception):
    """Raised for version store errors."""


@dataclass
class VersionRecord:
    job_name: str
    version: str
    deployed_at: str
    deployed_by: Optional[str] = None
    notes: Optional[str] = None

    def to_dict(self) -> dict:
        d = {
            "job_name": self.job_name,
            "version": self.version,
            "deployed_at": self.deployed_at,
        }
        if self.deployed_by is not None:
            d["deployed_by"] = self.deployed_by
        if self.notes is not None:
            d["notes"] = self.notes
        return d

    @classmethod
    def from_dict(cls, data: dict) -> "VersionRecord":
        return cls(
            job_name=data["job_name"],
            version=data["version"],
            deployed_at=data["deployed_at"],
            deployed_by=data.get("deployed_by"),
            notes=data.get("notes"),
        )


class JobVersioning:
    """Persist and query version history for cron jobs."""

    def __init__(self, state_dir: str) -> None:
        self._dir = Path(state_dir)
        self._dir.mkdir(parents=True, exist_ok=True)

    def _path(self, job_name: str) -> Path:
        safe = job_name.replace("/", "_")
        return self._dir / f"{safe}.versions.json"

    def _load(self, job_name: str) -> list:
        p = self._path(job_name)
        if not p.exists():
            return []
        return json.loads(p.read_text())

    def _save(self, job_name: str, records: list) -> None:
        self._path(job_name).write_text(json.dumps(records, indent=2))

    def record(self, record: VersionRecord) -> None:
        """Append a new version record for a job."""
        records = self._load(record.job_name)
        records.append(record.to_dict())
        self._save(record.job_name, records)

    def current(self, job_name: str) -> Optional[VersionRecord]:
        """Return the most recently recorded version, or None."""
        records = self._load(job_name)
        if not records:
            return None
        return VersionRecord.from_dict(records[-1])

    def history(self, job_name: str) -> list:
        """Return all version records for a job, oldest first."""
        return [VersionRecord.from_dict(r) for r in self._load(job_name)]

    def rollback_target(self, job_name: str) -> Optional[VersionRecord]:
        """Return the second-to-last version (rollback candidate), or None."""
        records = self._load(job_name)
        if len(records) < 2:
            return None
        return VersionRecord.from_dict(records[-2])
