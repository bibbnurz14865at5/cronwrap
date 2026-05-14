"""Execution window policy — restrict jobs to allowed time ranges."""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, time
from pathlib import Path
from typing import List, Optional


class WindowError(Exception):
    """Raised when a job is run outside its allowed window."""


@dataclass
class WindowPolicy:
    job_name: str
    # Each entry is a dict with keys: start, end (HH:MM), and optional weekdays (list of 0-6)
    windows: List[dict] = field(default_factory=list)
    timezone: str = "UTC"

    def to_dict(self) -> dict:
        return {
            "job_name": self.job_name,
            "windows": self.windows,
            "timezone": self.timezone,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "WindowPolicy":
        if "job_name" not in data:
            raise WindowError("'job_name' is required")
        return cls(
            job_name=data["job_name"],
            windows=data.get("windows", []),
            timezone=data.get("timezone", "UTC"),
        )

    @classmethod
    def from_json_file(cls, path: str) -> "WindowPolicy":
        p = Path(path)
        if not p.exists():
            raise WindowError(f"Config file not found: {path}")
        with p.open() as fh:
            return cls.from_dict(json.load(fh))

    def is_allowed(self, dt: Optional[datetime] = None) -> bool:
        """Return True if *dt* (default: now) falls within any configured window."""
        if not self.windows:
            return True
        now = dt or datetime.utcnow()
        current_time = now.time().replace(second=0, microsecond=0)
        current_weekday = now.weekday()  # 0=Monday … 6=Sunday
        for window in self.windows:
            try:
                start = time.fromisoformat(window["start"])
                end = time.fromisoformat(window["end"])
            except (KeyError, ValueError) as exc:
                raise WindowError(f"Invalid window entry: {exc}") from exc
            weekdays = window.get("weekdays")
            if weekdays is not None and current_weekday not in weekdays:
                continue
            if start <= end:
                if start <= current_time <= end:
                    return True
            else:  # window crosses midnight
                if current_time >= start or current_time <= end:
                    return True
        return False

    def assert_allowed(self, dt: Optional[datetime] = None) -> None:
        """Raise WindowError if the current time is outside all windows."""
        if not self.is_allowed(dt):
            raise WindowError(
                f"Job '{self.job_name}' is not allowed to run at this time."
            )
