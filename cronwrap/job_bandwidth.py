"""Track and enforce data throughput limits for cron jobs."""
from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional


class BandwidthError(Exception):
    """Raised when a bandwidth policy is violated."""


@dataclass
class BandwidthPolicy:
    job_name: str
    max_bytes_per_run: int
    state_dir: str = "/tmp/cronwrap/bandwidth"
    warn_pct: float = 80.0

    @classmethod
    def from_dict(cls, data: dict) -> "BandwidthPolicy":
        required = {"job_name", "max_bytes_per_run"}
        missing = required - data.keys()
        if missing:
            raise BandwidthError(f"Missing required fields: {missing}")
        return cls(
            job_name=data["job_name"],
            max_bytes_per_run=int(data["max_bytes_per_run"]),
            state_dir=data.get("state_dir", "/tmp/cronwrap/bandwidth"),
            warn_pct=float(data.get("warn_pct", 80.0)),
        )

    def to_dict(self) -> dict:
        return {
            "job_name": self.job_name,
            "max_bytes_per_run": self.max_bytes_per_run,
            "state_dir": self.state_dir,
            "warn_pct": self.warn_pct,
        }

    def _state_path(self) -> Path:
        p = Path(self.state_dir)
        p.mkdir(parents=True, exist_ok=True)
        return p / f"{self.job_name}.json"

    def record(self, bytes_used: int) -> dict:
        """Record bytes used for the current run and return status dict."""
        if bytes_used < 0:
            raise BandwidthError("bytes_used must be non-negative")
        entry = {
            "job_name": self.job_name,
            "bytes_used": bytes_used,
            "max_bytes_per_run": self.max_bytes_per_run,
            "timestamp": time.time(),
            "exceeded": bytes_used > self.max_bytes_per_run,
            "warn": bytes_used >= (self.max_bytes_per_run * self.warn_pct / 100),
        }
        self._state_path().write_text(json.dumps(entry))
        if entry["exceeded"]:
            raise BandwidthError(
                f"{self.job_name} used {bytes_used} bytes, limit is {self.max_bytes_per_run}"
            )
        return entry

    def last_record(self) -> Optional[dict]:
        """Return the last recorded bandwidth entry, or None."""
        p = self._state_path()
        if not p.exists():
            return None
        return json.loads(p.read_text())
