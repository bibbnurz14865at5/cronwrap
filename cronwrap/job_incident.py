"""Track and manage incidents associated with cron job failures."""
from __future__ import annotations

import json
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional


class IncidentError(Exception):
    """Raised when an incident operation fails."""


@dataclass
class IncidentRecord:
    job_name: str
    incident_id: str
    opened_at: str
    status: str  # open | resolved | suppressed
    reason: Optional[str] = None
    resolved_at: Optional[str] = None
    extra: Dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        d = {
            "job_name": self.job_name,
            "incident_id": self.incident_id,
            "opened_at": self.opened_at,
            "status": self.status,
        }
        if self.reason is not None:
            d["reason"] = self.reason
        if self.resolved_at is not None:
            d["resolved_at"] = self.resolved_at
        if self.extra:
            d["extra"] = self.extra
        return d

    @classmethod
    def from_dict(cls, data: dict) -> "IncidentRecord":
        return cls(
            job_name=data["job_name"],
            incident_id=data["incident_id"],
            opened_at=data["opened_at"],
            status=data["status"],
            reason=data.get("reason"),
            resolved_at=data.get("resolved_at"),
            extra=data.get("extra", {}),
        )


class JobIncident:
    _VALID_STATUSES = {"open", "resolved", "suppressed"}

    def __init__(self, state_dir: str) -> None:
        self._dir = Path(state_dir)
        self._dir.mkdir(parents=True, exist_ok=True)

    def _path(self, job_name: str) -> Path:
        return self._dir / f"{job_name}.incidents.json"

    def _load(self, job_name: str) -> List[dict]:
        p = self._path(job_name)
        if not p.exists():
            return []
        return json.loads(p.read_text())

    def _save(self, job_name: str, records: List[dict]) -> None:
        self._path(job_name).write_text(json.dumps(records, indent=2))

    def open(self, job_name: str, reason: Optional[str] = None, extra: Optional[dict] = None) -> IncidentRecord:
        now = datetime.now(timezone.utc).isoformat()
        rec = IncidentRecord(
            job_name=job_name,
            incident_id=str(uuid.uuid4()),
            opened_at=now,
            status="open",
            reason=reason,
            extra=extra or {},
        )
        records = self._load(job_name)
        records.append(rec.to_dict())
        self._save(job_name, records)
        return rec

    def resolve(self, job_name: str, incident_id: str) -> IncidentRecord:
        records = self._load(job_name)
        for r in records:
            if r["incident_id"] == incident_id:
                if r["status"] != "open":
                    raise IncidentError(f"Incident {incident_id} is not open")
                r["status"] = "resolved"
                r["resolved_at"] = datetime.now(timezone.utc).isoformat()
                self._save(job_name, records)
                return IncidentRecord.from_dict(r)
        raise IncidentError(f"Incident {incident_id} not found for job {job_name!r}")

    def list_open(self, job_name: str) -> List[IncidentRecord]:
        return [
            IncidentRecord.from_dict(r)
            for r in self._load(job_name)
            if r["status"] == "open"
        ]

    def list_all(self, job_name: str) -> List[IncidentRecord]:
        return [IncidentRecord.from_dict(r) for r in self._load(job_name)]
