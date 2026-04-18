"""Simple key/value label system for annotating cron jobs."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, List, Optional


class LabelError(Exception):
    """Raised when label operations fail."""


class JobLabels:
    """Stores arbitrary string key/value labels per job name."""

    def __init__(self, path: str | Path) -> None:
        self._path = Path(path)
        self._data: Dict[str, Dict[str, str]] = {}
        if self._path.exists():
            self._data = json.loads(self._path.read_text())

    # ------------------------------------------------------------------
    def set(self, job: str, key: str, value: str) -> None:
        """Set a label on a job, persisting immediately."""
        if not job or not key:
            raise LabelError("job and key must be non-empty strings")
        self._data.setdefault(job, {})[key] = value
        self._save()

    def get(self, job: str, key: str) -> Optional[str]:
        """Return label value or None."""
        return self._data.get(job, {}).get(key)

    def remove(self, job: str, key: str) -> bool:
        """Remove a label; return True if it existed."""
        labels = self._data.get(job, {})
        if key in labels:
            del labels[key]
            if not labels:
                del self._data[job]
            self._save()
            return True
        return False

    def labels_for(self, job: str) -> Dict[str, str]:
        """Return all labels for a job (copy)."""
        return dict(self._data.get(job, {}))

    def jobs_with_label(self, key: str, value: Optional[str] = None) -> List[str]:
        """Return job names that have *key*, optionally filtered by *value*."""
        result = []
        for job, labels in self._data.items():
            if key in labels:
                if value is None or labels[key] == value:
                    result.append(job)
        return sorted(result)

    def to_dict(self) -> Dict[str, Dict[str, str]]:
        return {job: dict(lbls) for job, lbls in self._data.items()}

    # ------------------------------------------------------------------
    def _save(self) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._path.write_text(json.dumps(self._data, indent=2))
