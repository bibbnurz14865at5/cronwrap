"""Job roster: track which jobs are expected to run and flag missing ones."""
from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional


class RosterError(Exception):
    """Raised for roster-related errors."""


@dataclass
class RosterEntry:
    job_name: str
    expected_interval_seconds: int
    description: Optional[str] = None
    extra: Dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        d = {
            "job_name": self.job_name,
            "expected_interval_seconds": self.expected_interval_seconds,
        }
        if self.description is not None:
            d["description"] = self.description
        if self.extra:
            d["extra"] = self.extra
        return d

    @classmethod
    def from_dict(cls, data: dict) -> "RosterEntry":
        return cls(
            job_name=data["job_name"],
            expected_interval_seconds=int(data["expected_interval_seconds"]),
            description=data.get("description"),
            extra=data.get("extra", {}),
        )


@dataclass
class MissingJob:
    job_name: str
    last_seen: Optional[datetime]
    expected_interval_seconds: int
    seconds_overdue: float

    def __repr__(self) -> str:
        return (
            f"MissingJob(job_name={self.job_name!r}, "
            f"seconds_overdue={self.seconds_overdue:.1f})"
        )


class JobRoster:
    def __init__(self, roster_path: str, history_dir: str) -> None:
        self.roster_path = Path(roster_path)
        self.history_dir = Path(history_dir)

    def _load_roster(self) -> Dict[str, RosterEntry]:
        if not self.roster_path.exists():
            return {}
        with self.roster_path.open() as fh:
            raw = json.load(fh)
        return {e["job_name"]: RosterEntry.from_dict(e) for e in raw}

    def _save_roster(self, entries: Dict[str, RosterEntry]) -> None:
        self.roster_path.parent.mkdir(parents=True, exist_ok=True)
        with self.roster_path.open("w") as fh:
            json.dump([e.to_dict() for e in entries.values()], fh, indent=2)

    def register(self, entry: RosterEntry) -> None:
        entries = self._load_roster()
        entries[entry.job_name] = entry
        self._save_roster(entries)

    def unregister(self, job_name: str) -> None:
        entries = self._load_roster()
        if job_name not in entries:
            raise RosterError(f"Job not on roster: {job_name!r}")
        del entries[job_name]
        self._save_roster(entries)

    def _last_seen(self, job_name: str) -> Optional[datetime]:
        history_file = self.history_dir / f"{job_name}.json"
        if not history_file.exists():
            return None
        with history_file.open() as fh:
            records = json.load(fh)
        if not records:
            return None
        ts = records[-1].get("timestamp")
        if ts is None:
            return None
        return datetime.fromisoformat(ts).replace(tzinfo=timezone.utc)

    def check_missing(self, now: Optional[datetime] = None) -> List[MissingJob]:
        if now is None:
            now = datetime.now(timezone.utc)
        entries = self._load_roster()
        missing = []
        for job_name, entry in entries.items():
            last = self._last_seen(job_name)
            if last is None:
                overdue = float(entry.expected_interval_seconds)
            else:
                elapsed = (now - last).total_seconds()
                overdue = elapsed - entry.expected_interval_seconds
            if overdue > 0:
                missing.append(
                    MissingJob(
                        job_name=job_name,
                        last_seen=last,
                        expected_interval_seconds=entry.expected_interval_seconds,
                        seconds_overdue=overdue,
                    )
                )
        return missing

    def list_entries(self) -> List[RosterEntry]:
        return list(self._load_roster().values())
