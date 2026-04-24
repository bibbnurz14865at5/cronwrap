"""Blackout window support — suppress job execution during defined time ranges."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, time
from pathlib import Path
from typing import List, Optional


class BlackoutError(Exception):
    """Raised for invalid blackout configuration."""


@dataclass
class BlackoutWindow:
    """A single blackout window defined by start/end times (HH:MM) and optional weekdays."""

    start: str  # "HH:MM"
    end: str    # "HH:MM"
    weekdays: List[int] = field(default_factory=list)  # 0=Mon … 6=Sun; empty = every day
    label: Optional[str] = None

    def __post_init__(self) -> None:
        for attr in ("start", "end"):
            val = getattr(self, attr)
            try:
                datetime.strptime(val, "%H:%M")
            except ValueError:
                raise BlackoutError(f"Invalid time '{val}' for '{attr}'; expected HH:MM")
        for d in self.weekdays:
            if d not in range(7):
                raise BlackoutError(f"Invalid weekday {d}; must be 0–6")

    def is_active(self, dt: Optional[datetime] = None) -> bool:
        """Return True if *dt* (default: now) falls within this blackout window."""
        dt = dt or datetime.now()
        if self.weekdays and dt.weekday() not in self.weekdays:
            return False
        t = dt.time().replace(second=0, microsecond=0)
        t_start = time(*map(int, self.start.split(":")))
        t_end = time(*map(int, self.end.split(":")))
        if t_start <= t_end:
            return t_start <= t <= t_end
        # overnight window e.g. 22:00 – 06:00
        return t >= t_start or t <= t_end

    def to_dict(self) -> dict:
        d: dict = {"start": self.start, "end": self.end}
        if self.weekdays:
            d["weekdays"] = self.weekdays
        if self.label is not None:
            d["label"] = self.label
        return d

    @classmethod
    def from_dict(cls, data: dict) -> "BlackoutWindow":
        return cls(
            start=data["start"],
            end=data["end"],
            weekdays=data.get("weekdays", []),
            label=data.get("label"),
        )


@dataclass
class BlackoutPolicy:
    """Collection of blackout windows for a job."""

    job_name: str
    windows: List[BlackoutWindow] = field(default_factory=list)

    def is_blacked_out(self, dt: Optional[datetime] = None) -> bool:
        return any(w.is_active(dt) for w in self.windows)

    def to_dict(self) -> dict:
        return {"job_name": self.job_name, "windows": [w.to_dict() for w in self.windows]}

    @classmethod
    def from_dict(cls, data: dict) -> "BlackoutPolicy":
        if "job_name" not in data:
            raise BlackoutError("'job_name' is required")
        windows = [BlackoutWindow.from_dict(w) for w in data.get("windows", [])]
        return cls(job_name=data["job_name"], windows=windows)

    @classmethod
    def from_json_file(cls, path: str) -> "BlackoutPolicy":
        p = Path(path)
        if not p.exists():
            raise BlackoutError(f"Config file not found: {path}")
        return cls.from_dict(json.loads(p.read_text()))
