"""Simple file-backed registry mapping job names to their cron schedules and metadata."""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional


@dataclass
class JobEntry:
    name: str
    schedule: str
    command: str
    tags: List[str] = field(default_factory=list)
    description: str = ""
    enabled: bool = True

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "schedule": self.schedule,
            "command": self.command,
            "tags": self.tags,
            "description": self.description,
            "enabled": self.enabled,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "JobEntry":
        return cls(
            name=data["name"],
            schedule=data["schedule"],
            command=data["command"],
            tags=data.get("tags", []),
            description=data.get("description", ""),
            enabled=data.get("enabled", True),
        )


class RegistryError(Exception):
    pass


class JobRegistry:
    def __init__(self, path: Path) -> None:
        self.path = Path(path)
        self._jobs: Dict[str, JobEntry] = {}
        if self.path.exists():
            self._load()

    def _load(self) -> None:
        data = json.loads(self.path.read_text())
        self._jobs = {e["name"]: JobEntry.from_dict(e) for e in data.get("jobs", [])}

    def _save(self) -> None:
        self.path.write_text(json.dumps({"jobs": [e.to_dict() for e in self._jobs.values()]}, indent=2))

    def register(self, entry: JobEntry) -> None:
        self._jobs[entry.name] = entry
        self._save()

    def unregister(self, name: str) -> None:
        if name not in self._jobs:
            raise RegistryError(f"Job '{name}' not found")
        del self._jobs[name]
        self._save()

    def get(self, name: str) -> Optional[JobEntry]:
        return self._jobs.get(name)

    def all_jobs(self) -> List[JobEntry]:
        return list(self._jobs.values())

    def enabled_jobs(self) -> List[JobEntry]:
        return [j for j in self._jobs.values() if j.enabled]
