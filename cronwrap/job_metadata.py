"""Attach and retrieve arbitrary metadata key/value pairs for a job."""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Optional


class MetadataError(Exception):
    """Raised when a metadata operation fails."""


@dataclass
class JobMetadata:
    job_name: str
    state_dir: str = ".cronwrap/metadata"
    _data: Dict[str, Any] = field(default_factory=dict, init=False, repr=False)

    def __post_init__(self) -> None:
        self._path = Path(self.state_dir) / f"{self.job_name}.json"
        self._data = self._load()

    def _load(self) -> Dict[str, Any]:
        if self._path.exists():
            try:
                return json.loads(self._path.read_text())
            except (json.JSONDecodeError, OSError):
                return {}
        return {}

    def _save(self) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._path.write_text(json.dumps(self._data, indent=2))

    def set(self, key: str, value: Any) -> None:
        """Set a metadata key."""
        if not key:
            raise MetadataError("key must be a non-empty string")
        self._data[key] = value
        self._save()

    def get(self, key: str, default: Any = None) -> Any:
        """Return the value for *key*, or *default* if absent."""
        return self._data.get(key, default)

    def remove(self, key: str) -> None:
        """Remove *key* if present; silently ignore if absent."""
        if key in self._data:
            del self._data[key]
            self._save()

    def all(self) -> Dict[str, Any]:
        """Return a shallow copy of all metadata."""
        return dict(self._data)

    def clear(self) -> None:
        """Remove all metadata for this job."""
        self._data = {}
        self._save()

    def to_dict(self) -> Dict[str, Any]:
        return {"job_name": self.job_name, "metadata": self.all()}

    @classmethod
    def from_dict(cls, data: Dict[str, Any], state_dir: str = ".cronwrap/metadata") -> "JobMetadata":
        job_name = data.get("job_name")
        if not job_name:
            raise MetadataError("job_name is required")
        obj = cls(job_name=job_name, state_dir=state_dir)
        for k, v in data.get("metadata", {}).items():
            obj._data[k] = v
        obj._save()
        return obj
