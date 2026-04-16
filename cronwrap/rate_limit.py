"""Rate limiting: suppress repeated alerts within a cooldown window."""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Optional


@dataclass
class RateLimitPolicy:
    cooldown_seconds: int = 3600  # default 1 hour
    state_file: Path = Path("/tmp/cronwrap_ratelimit.json")

    @classmethod
    def from_dict(cls, data: dict) -> "RateLimitPolicy":
        return cls(
            cooldown_seconds=int(data.get("cooldown_seconds", 3600)),
            state_file=Path(data.get("state_file", "/tmp/cronwrap_ratelimit.json")),
        )

    def to_dict(self) -> dict:
        return {
            "cooldown_seconds": self.cooldown_seconds,
            "state_file": str(self.state_file),
        }

    def _load_state(self) -> Dict[str, float]:
        if not self.state_file.exists():
            return {}
        try:
            return json.loads(self.state_file.read_text())
        except (json.JSONDecodeError, OSError):
            return {}

    def _save_state(self, state: Dict[str, float]) -> None:
        self.state_file.write_text(json.dumps(state))

    def is_suppressed(self, job_name: str) -> bool:
        """Return True if an alert for job_name is within the cooldown window."""
        state = self._load_state()
        last = state.get(job_name)
        if last is None:
            return False
        return (time.time() - last) < self.cooldown_seconds

    def record_alert(self, job_name: str) -> None:
        """Record that an alert was sent for job_name right now."""
        state = self._load_state()
        state[job_name] = time.time()
        self._save_state(state)

    def reset(self, job_name: str) -> None:
        """Clear rate-limit state for a specific job."""
        state = self._load_state()
        state.pop(job_name, None)
        self._save_state(state)
