"""Job manifest: a registry of all known jobs with metadata snapshots."""
from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from typing import Dict, List, Optional


class ManifestError(Exception):
    """Raised on manifest operation failures."""


@dataclass
class ManifestEntry:
    job_name: str
    command: str
    schedule: Optional[str] = None
    owner: Optional[str] = None
    tags: List[str] = field(default_factory=list)
    description: Optional[str] = None

    def to_dict(self) -> dict:
        d: dict = {"job_name": self.job_name, "command": self.command}
        if self.schedule is not None:
            d["schedule"] = self.schedule
        if self.owner is not None:
            d["owner"] = self.owner
        if self.tags:
            d["tags"] = list(self.tags)
        if self.description is not None:
            d["description"] = self.description
        return d

    @classmethod
    def from_dict(cls, data: dict) -> "ManifestEntry":
        if "job_name" not in data:
            raise ManifestError("ManifestEntry requires 'job_name'")
        if "command" not in data:
            raise ManifestError("ManifestEntry requires 'command'")
        return cls(
            job_name=data["job_name"],
            command=data["command"],
            schedule=data.get("schedule"),
            owner=data.get("owner"),
            tags=list(data.get("tags", [])),
            description=data.get("description"),
        )


class JobManifest:
    """Persistent store of job manifest entries."""

    def __init__(self, path: str) -> None:
        self._path = path
        self._entries: Dict[str, ManifestEntry] = {}
        if os.path.exists(path):
            self._load()

    def _load(self) -> None:
        with open(self._path, "r", encoding="utf-8") as fh:
            raw = json.load(fh)
        self._entries = {
            k: ManifestEntry.from_dict(v) for k, v in raw.items()
        }

    def _save(self) -> None:
        with open(self._path, "w", encoding="utf-8") as fh:
            json.dump(
                {k: v.to_dict() for k, v in self._entries.items()},
                fh,
                indent=2,
            )

    def register(self, entry: ManifestEntry) -> None:
        self._entries[entry.job_name] = entry
        self._save()

    def get(self, job_name: str) -> Optional[ManifestEntry]:
        return self._entries.get(job_name)

    def remove(self, job_name: str) -> None:
        if job_name not in self._entries:
            raise ManifestError(f"Job not found in manifest: {job_name}")
        del self._entries[job_name]
        self._save()

    def all_entries(self) -> List[ManifestEntry]:
        return sorted(self._entries.values(), key=lambda e: e.job_name)

    def to_dict(self) -> dict:
        return {k: v.to_dict() for k, v in self._entries.items()}
