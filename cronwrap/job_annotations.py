"""Persistent key-value annotations for cron jobs."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, Iterator, Optional


class AnnotationError(Exception):
    """Raised when annotation operations fail."""


class JobAnnotations:
    """Store and retrieve free-form annotations for a job."""

    def __init__(self, storage_dir: str, job_name: str) -> None:
        self._path = Path(storage_dir) / f"{job_name}.annotations.json"
        self._job = job_name

    def _load(self) -> Dict[str, str]:
        if not self._path.exists():
            return {}
        try:
            return json.loads(self._path.read_text())
        except json.JSONDecodeError as exc:
            raise AnnotationError(f"Corrupt annotations file: {self._path}") from exc

    def _save(self, data: Dict[str, str]) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._path.write_text(json.dumps(data, indent=2))

    def set(self, key: str, value: str) -> None:
        """Set an annotation key."""
        data = self._load()
        data[key] = value
        self._save(data)

    def get(self, key: str) -> Optional[str]:
        """Return annotation value or None."""
        return self._load().get(key)

    def remove(self, key: str) -> bool:
        """Remove a key; return True if it existed."""
        data = self._load()
        if key not in data:
            return False
        del data[key]
        self._save(data)
        return True

    def all(self) -> Dict[str, str]:
        """Return all annotations as a dict."""
        return self._load()

    def keys(self) -> Iterator[str]:
        yield from self._load()

    def clear(self) -> None:
        """Remove all annotations."""
        self._save({})

    def to_dict(self) -> Dict[str, object]:
        return {"job": self._job, "annotations": self._load()}
