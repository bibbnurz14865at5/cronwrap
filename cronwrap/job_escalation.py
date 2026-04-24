"""Escalation policy: notify additional contacts after repeated failures."""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional


class EscalationError(Exception):
    """Raised when escalation configuration is invalid."""


@dataclass
class EscalationPolicy:
    job_name: str
    failure_threshold: int  # consecutive failures before escalating
    contacts: List[str]     # e.g. email addresses or Slack channels
    state_dir: str = "/tmp/cronwrap/escalation"
    _consecutive: int = field(default=0, init=False, repr=False)

    def __post_init__(self) -> None:
        if self.failure_threshold < 1:
            raise EscalationError("failure_threshold must be >= 1")
        if not self.contacts:
            raise EscalationError("contacts list must not be empty")

    # ------------------------------------------------------------------
    @classmethod
    def from_dict(cls, data: dict) -> "EscalationPolicy":
        if "job_name" not in data:
            raise EscalationError("'job_name' is required")
        if "failure_threshold" not in data:
            raise EscalationError("'failure_threshold' is required")
        if "contacts" not in data:
            raise EscalationError("'contacts' is required")
        return cls(
            job_name=data["job_name"],
            failure_threshold=int(data["failure_threshold"]),
            contacts=list(data["contacts"]),
            state_dir=data.get("state_dir", "/tmp/cronwrap/escalation"),
        )

    @classmethod
    def from_json_file(cls, path: str) -> "EscalationPolicy":
        p = Path(path)
        if not p.exists():
            raise EscalationError(f"Config file not found: {path}")
        return cls.from_dict(json.loads(p.read_text()))

    def to_dict(self) -> dict:
        return {
            "job_name": self.job_name,
            "failure_threshold": self.failure_threshold,
            "contacts": self.contacts,
            "state_dir": self.state_dir,
        }

    # ------------------------------------------------------------------
    def _state_path(self) -> Path:
        return Path(self.state_dir) / f"{self.job_name}.json"

    def _load_state(self) -> int:
        p = self._state_path()
        if not p.exists():
            return 0
        return int(json.loads(p.read_text()).get("consecutive_failures", 0))

    def _save_state(self, count: int) -> None:
        p = self._state_path()
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps({"consecutive_failures": count}))

    def record_failure(self) -> bool:
        """Record a failure; return True if escalation threshold is reached."""
        count = self._load_state() + 1
        self._save_state(count)
        return count >= self.failure_threshold

    def record_success(self) -> None:
        """Reset consecutive failure counter on success."""
        self._save_state(0)

    def consecutive_failures(self) -> int:
        """Return current consecutive failure count."""
        return self._load_state()

    def should_escalate(self) -> bool:
        """Return True if current state already meets the threshold."""
        return self._load_state() >= self.failure_threshold
