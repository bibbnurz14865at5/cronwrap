"""Track job dependencies — ensure a job only runs after its dependencies succeeded."""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional


class DependencyError(Exception):
    """Raised when a dependency check fails."""


@dataclass
class DependencyConfig:
    job_name: str
    depends_on: List[str] = field(default_factory=list)
    require_success_within_seconds: Optional[int] = None

    def to_dict(self) -> dict:
        return {
            "job_name": self.job_name,
            "depends_on": self.depends_on,
            "require_success_within_seconds": self.require_success_within_seconds,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "DependencyConfig":
        return cls(
            job_name=data["job_name"],
            depends_on=data.get("depends_on", []),
            require_success_within_seconds=data.get("require_success_within_seconds"),
        )

    @classmethod
    def from_json_file(cls, path: str) -> "DependencyConfig":
        p = Path(path)
        if not p.exists():
            raise FileNotFoundError(f"Dependency config not found: {path}")
        return cls.from_dict(json.loads(p.read_text()))


def check_dependencies(config: DependencyConfig, history_dir: str) -> List[str]:
    """Return list of unmet dependency names. Empty list means all deps satisfied."""
    import time
    from cronwrap.history import JobHistory

    unmet: List[str] = []
    now = time.time()

    for dep in config.depends_on:
        dep_dir = Path(history_dir) / dep
        if not dep_dir.exists():
            unmet.append(dep)
            continue
        history = JobHistory(str(dep_dir))
        entries = history.load()
        successes = [e for e in entries if e.success]
        if not successes:
            unmet.append(dep)
            continue
        latest = max(successes, key=lambda e: e.timestamp)
        if config.require_success_within_seconds is not None:
            age = now - latest.timestamp
            if age > config.require_success_within_seconds:
                unmet.append(dep)
    return unmet


def assert_dependencies(config: DependencyConfig, history_dir: str) -> None:
    """Raise DependencyError if any dependency is unmet."""
    unmet = check_dependencies(config, history_dir)
    if unmet:
        raise DependencyError(f"Unmet dependencies for '{config.job_name}': {unmet}")
