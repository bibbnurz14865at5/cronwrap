"""Timeout policy: define and evaluate per-job timeout settings."""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional


@dataclass
class TimeoutPolicy:
    """Holds timeout configuration for a cron job."""

    # Hard timeout in seconds; None means no limit.
    timeout_seconds: Optional[int] = None
    # Warn (but don't kill) if job exceeds this duration.
    warn_seconds: Optional[int] = None
    # Whether to send an alert when the warn threshold is crossed.
    alert_on_warn: bool = False

    # ------------------------------------------------------------------
    # Factories
    # ------------------------------------------------------------------

    @classmethod
    def from_dict(cls, data: dict) -> "TimeoutPolicy":
        allowed = {"timeout_seconds", "warn_seconds", "alert_on_warn"}
        filtered = {k: v for k, v in data.items() if k in allowed}
        return cls(**filtered)

    @classmethod
    def from_json_file(cls, path: str) -> "TimeoutPolicy":
        p = Path(path)
        if not p.exists():
            raise FileNotFoundError(f"Timeout policy file not found: {path}")
        with p.open() as fh:
            return cls.from_dict(json.load(fh))

    # ------------------------------------------------------------------
    # Serialisation
    # ------------------------------------------------------------------

    def to_dict(self) -> dict:
        return {
            "timeout_seconds": self.timeout_seconds,
            "warn_seconds": self.warn_seconds,
            "alert_on_warn": self.alert_on_warn,
        }

    # ------------------------------------------------------------------
    # Evaluation
    # ------------------------------------------------------------------

    def is_timed_out(self, duration: float) -> bool:
        """Return True if *duration* (seconds) exceeds the hard timeout."""
        if self.timeout_seconds is None:
            return False
        return duration >= self.timeout_seconds

    def is_warned(self, duration: float) -> bool:
        """Return True if *duration* exceeds the warn threshold."""
        if self.warn_seconds is None:
            return False
        return duration >= self.warn_seconds

    def evaluate(self, duration: float) -> dict:
        """Return a status dict for *duration*."""
        return {
            "duration": duration,
            "timed_out": self.is_timed_out(duration),
            "warned": self.is_warned(duration),
            "alert": self.alert_on_warn and self.is_warned(duration),
        }
