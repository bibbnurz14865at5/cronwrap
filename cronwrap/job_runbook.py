"""Job runbook: attach a runbook URL or markdown notes to a job for on-call reference."""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional


class RunbookError(Exception):
    """Raised on runbook storage or validation errors."""


@dataclass
class RunbookEntry:
    job_name: str
    url: Optional[str] = None
    notes: Optional[str] = None
    tags: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        d: dict = {"job_name": self.job_name}
        if self.url is not None:
            d["url"] = self.url
        if self.notes is not None:
            d["notes"] = self.notes
        if self.tags:
            d["tags"] = list(self.tags)
        return d

    @classmethod
    def from_dict(cls, data: dict) -> "RunbookEntry":
        return cls(
            job_name=data["job_name"],
            url=data.get("url"),
            notes=data.get("notes"),
            tags=list(data.get("tags", [])),
        )


class JobRunbook:
    """Persist and retrieve runbook entries keyed by job name."""

    def __init__(self, state_dir: str) -> None:
        self._path = Path(state_dir) / "runbooks.json"
        self._path.parent.mkdir(parents=True, exist_ok=True)

    def _load(self) -> dict:
        if not self._path.exists():
            return {}
        try:
            return json.loads(self._path.read_text())
        except (json.JSONDecodeError, OSError) as exc:
            raise RunbookError(f"Failed to read runbook store: {exc}") from exc

    def _save(self, data: dict) -> None:
        try:
            self._path.write_text(json.dumps(data, indent=2))
        except OSError as exc:
            raise RunbookError(f"Failed to write runbook store: {exc}") from exc

    def set(self, entry: RunbookEntry) -> None:
        """Insert or replace the runbook entry for a job."""
        data = self._load()
        data[entry.job_name] = entry.to_dict()
        self._save(data)

    def get(self, job_name: str) -> Optional[RunbookEntry]:
        """Return the runbook entry for *job_name*, or None if absent."""
        data = self._load()
        raw = data.get(job_name)
        if raw is None:
            return None
        return RunbookEntry.from_dict(raw)

    def remove(self, job_name: str) -> bool:
        """Delete the runbook entry. Returns True if it existed."""
        data = self._load()
        if job_name not in data:
            return False
        del data[job_name]
        self._save(data)
        return True

    def all_entries(self) -> list[RunbookEntry]:
        """Return all stored runbook entries sorted by job name."""
        data = self._load()
        return [RunbookEntry.from_dict(v) for v in sorted(data.values(), key=lambda x: x["job_name"])]
