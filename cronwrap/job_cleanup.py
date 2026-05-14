"""Job cleanup policy: remove stale lock files and temp artifacts."""
from __future__ import annotations

import os
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import List


class CleanupError(Exception):
    """Raised when a cleanup operation fails."""


@dataclass
class CleanupResult:
    removed: List[str] = field(default_factory=list)
    skipped: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.errors

    def to_dict(self) -> dict:
        return {
            "removed": self.removed,
            "skipped": self.skipped,
            "errors": self.errors,
            "ok": self.ok,
        }


@dataclass
class CleanupPolicy:
    state_dir: str
    max_age_seconds: int = 3600
    extensions: List[str] = field(default_factory=lambda: [".lock", ".tmp"])

    @classmethod
    def from_dict(cls, data: dict) -> "CleanupPolicy":
        if "state_dir" not in data:
            raise CleanupError("'state_dir' is required")
        return cls(
            state_dir=data["state_dir"],
            max_age_seconds=int(data.get("max_age_seconds", 3600)),
            extensions=list(data.get("extensions", [".lock", ".tmp"])),
        )

    def to_dict(self) -> dict:
        return {
            "state_dir": self.state_dir,
            "max_age_seconds": self.max_age_seconds,
            "extensions": self.extensions,
        }

    def run(self) -> CleanupResult:
        result = CleanupResult()
        directory = Path(self.state_dir)
        if not directory.exists():
            return result
        now = time.time()
        for entry in directory.iterdir():
            if not entry.is_file():
                continue
            if entry.suffix not in self.extensions:
                result.skipped.append(str(entry))
                continue
            try:
                age = now - entry.stat().st_mtime
                if age >= self.max_age_seconds:
                    entry.unlink()
                    result.removed.append(str(entry))
                else:
                    result.skipped.append(str(entry))
            except OSError as exc:
                result.errors.append(f"{entry}: {exc}")
        return result
