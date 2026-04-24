"""Job ownership tracking — assign owners/teams to jobs and look them up."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional


class OwnershipError(Exception):
    """Raised when an ownership operation fails."""


@dataclass
class OwnerRecord:
    job_name: str
    owner: str
    team: Optional[str] = None
    email: Optional[str] = None

    def to_dict(self) -> dict:
        d: dict = {"job_name": self.job_name, "owner": self.owner}
        if self.team is not None:
            d["team"] = self.team
        if self.email is not None:
            d["email"] = self.email
        return d

    @classmethod
    def from_dict(cls, data: dict) -> "OwnerRecord":
        return cls(
            job_name=data["job_name"],
            owner=data["owner"],
            team=data.get("team"),
            email=data.get("email"),
        )


class JobOwnership:
    """Persist and query job ownership records."""

    def __init__(self, path: Path) -> None:
        self._path = Path(path)
        self._records: Dict[str, OwnerRecord] = {}
        self._load()

    def _load(self) -> None:
        if self._path.exists():
            raw = json.loads(self._path.read_text())
            self._records = {
                k: OwnerRecord.from_dict(v) for k, v in raw.items()
            }

    def _save(self) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._path.write_text(
            json.dumps({k: v.to_dict() for k, v in self._records.items()}, indent=2)
        )

    def set(self, record: OwnerRecord) -> None:
        """Register or update ownership for a job."""
        self._records[record.job_name] = record
        self._save()

    def get(self, job_name: str) -> Optional[OwnerRecord]:
        """Return the ownership record for *job_name*, or None."""
        return self._records.get(job_name)

    def remove(self, job_name: str) -> None:
        """Remove ownership record; raises OwnershipError if not found."""
        if job_name not in self._records:
            raise OwnershipError(f"No ownership record for job '{job_name}'")
        del self._records[job_name]
        self._save()

    def jobs_for_team(self, team: str) -> List[str]:
        """Return sorted list of job names belonging to *team*."""
        return sorted(
            name for name, r in self._records.items() if r.team == team
        )

    def all_records(self) -> List[OwnerRecord]:
        """Return all ownership records sorted by job name."""
        return [self._records[k] for k in sorted(self._records)]
