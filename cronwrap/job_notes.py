"""Persistent free-text notes attached to a cron job."""
from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional


class NotesError(Exception):
    """Raised when a notes operation fails."""


@dataclass
class NoteEntry:
    job_name: str
    text: str
    author: Optional[str] = None
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> dict:
        d = {"job_name": self.job_name, "text": self.text, "timestamp": self.timestamp}
        if self.author is not None:
            d["author"] = self.author
        return d

    @classmethod
    def from_dict(cls, data: dict) -> "NoteEntry":
        return cls(
            job_name=data["job_name"],
            text=data["text"],
            author=data.get("author"),
            timestamp=data.get("timestamp", datetime.now(timezone.utc).isoformat()),
        )


class JobNotes:
    def __init__(self, notes_dir: str) -> None:
        self._dir = Path(notes_dir)
        self._dir.mkdir(parents=True, exist_ok=True)

    def _path(self, job_name: str) -> Path:
        return self._dir / f"{job_name}.notes.json"

    def _load(self, job_name: str) -> List[dict]:
        p = self._path(job_name)
        if not p.exists():
            return []
        with p.open() as fh:
            return json.load(fh)

    def _save(self, job_name: str, entries: List[dict]) -> None:
        with self._path(job_name).open("w") as fh:
            json.dump(entries, fh, indent=2)

    def add(self, entry: NoteEntry) -> None:
        entries = self._load(entry.job_name)
        entries.append(entry.to_dict())
        self._save(entry.job_name, entries)

    def list_notes(self, job_name: str) -> List[NoteEntry]:
        return [NoteEntry.from_dict(d) for d in self._load(job_name)]

    def clear(self, job_name: str) -> int:
        """Remove all notes for *job_name*. Returns the number removed."""
        entries = self._load(job_name)
        count = len(entries)
        self._save(job_name, [])
        return count

    def remove_by_index(self, job_name: str, index: int) -> NoteEntry:
        entries = self._load(job_name)
        if index < 0 or index >= len(entries):
            raise NotesError(f"Index {index} out of range for job '{job_name}'")
        removed = NoteEntry.from_dict(entries.pop(index))
        self._save(job_name, entries)
        return removed
