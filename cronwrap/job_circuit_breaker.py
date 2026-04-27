"""Circuit breaker for cron jobs: open the circuit after N consecutive failures."""
from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional


class CircuitBreakerError(Exception):
    """Raised when a job is blocked by an open circuit."""


@dataclass
class CircuitBreakerPolicy:
    job_name: str
    failure_threshold: int = 3          # consecutive failures to open
    recovery_timeout: int = 300         # seconds before half-open probe
    state_dir: str = "/tmp/cronwrap/circuit_breaker"

    # ------------------------------------------------------------------ #
    # serialisation
    # ------------------------------------------------------------------ #
    def to_dict(self) -> dict:
        return {
            "job_name": self.job_name,
            "failure_threshold": self.failure_threshold,
            "recovery_timeout": self.recovery_timeout,
            "state_dir": self.state_dir,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "CircuitBreakerPolicy":
        required = {"job_name"}
        missing = required - data.keys()
        if missing:
            raise ValueError(f"CircuitBreakerPolicy missing keys: {missing}")
        return cls(
            job_name=data["job_name"],
            failure_threshold=int(data.get("failure_threshold", 3)),
            recovery_timeout=int(data.get("recovery_timeout", 300)),
            state_dir=data.get("state_dir", "/tmp/cronwrap/circuit_breaker"),
        )

    # ------------------------------------------------------------------ #
    # state helpers
    # ------------------------------------------------------------------ #
    def _state_path(self) -> Path:
        p = Path(self.state_dir)
        p.mkdir(parents=True, exist_ok=True)
        return p / f"{self.job_name}.json"

    def _load_state(self) -> dict:
        path = self._state_path()
        if path.exists():
            return json.loads(path.read_text())
        return {"failures": 0, "opened_at": None, "state": "closed"}

    def _save_state(self, state: dict) -> None:
        self._state_path().write_text(json.dumps(state))

    # ------------------------------------------------------------------ #
    # public API
    # ------------------------------------------------------------------ #
    def record_success(self) -> None:
        """Reset failure count and close the circuit."""
        self._save_state({"failures": 0, "opened_at": None, "state": "closed"})

    def record_failure(self) -> None:
        """Increment failure count; open circuit when threshold is reached."""
        s = self._load_state()
        s["failures"] = s.get("failures", 0) + 1
        if s["failures"] >= self.failure_threshold:
            s["state"] = "open"
            s["opened_at"] = s.get("opened_at") or time.time()
        self._save_state(s)

    def check(self) -> None:
        """Raise CircuitBreakerError if the circuit is open and not yet recoverable."""
        s = self._load_state()
        if s["state"] != "open":
            return
        elapsed = time.time() - (s["opened_at"] or 0)
        if elapsed < self.recovery_timeout:
            raise CircuitBreakerError(
                f"Circuit open for job '{self.job_name}' "
                f"({int(elapsed)}s / {self.recovery_timeout}s recovery timeout)."
            )
        # half-open: allow one probe through (caller decides success/failure)

    def is_open(self) -> bool:
        """Return True if the circuit is currently open."""
        s = self._load_state()
        return s["state"] == "open"
