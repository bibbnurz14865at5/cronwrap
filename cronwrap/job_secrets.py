"""Manage per-job secret references (env-var names) without storing values."""
from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional


class SecretsError(Exception):
    pass


@dataclass
class JobSecrets:
    """Tracks which environment variables a job requires as secrets."""
    job_name: str
    required: List[str] = field(default_factory=list)
    optional: List[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "job_name": self.job_name,
            "required": list(self.required),
            "optional": list(self.optional),
        }

    @classmethod
    def from_dict(cls, data: dict) -> "JobSecrets":
        return cls(
            job_name=data["job_name"],
            required=list(data.get("required", [])),
            optional=list(data.get("optional", [])),
        )

    def missing_required(self) -> List[str]:
        """Return required secret names not present in the environment."""
        return [k for k in self.required if not os.environ.get(k)]

    def present_optional(self) -> List[str]:
        """Return optional secret names that ARE present in the environment."""
        return [k for k in self.optional if os.environ.get(k)]

    def check(self) -> "SecretsCheckResult":
        missing = self.missing_required()
        return SecretsCheckResult(ok=len(missing) == 0, missing=missing)


@dataclass
class SecretsCheckResult:
    ok: bool
    missing: List[str]

    def __repr__(self) -> str:
        return f"SecretsCheckResult(ok={self.ok}, missing={self.missing})"


class SecretsRegistry:
    """Persist job secret definitions to a JSON file."""

    def __init__(self, path: str) -> None:
        self._path = Path(path)

    def _load(self) -> Dict[str, dict]:
        if not self._path.exists():
            return {}
        return json.loads(self._path.read_text())

    def _save(self, data: Dict[str, dict]) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._path.write_text(json.dumps(data, indent=2))

    def register(self, secrets: JobSecrets) -> None:
        data = self._load()
        data[secrets.job_name] = secrets.to_dict()
        self._save(data)

    def get(self, job_name: str) -> Optional[JobSecrets]:
        data = self._load()
        if job_name not in data:
            return None
        return JobSecrets.from_dict(data[job_name])

    def all_jobs(self) -> List[str]:
        return sorted(self._load().keys())

    def remove(self, job_name: str) -> bool:
        data = self._load()
        if job_name not in data:
            return False
        del data[job_name]
        self._save(data)
        return True
