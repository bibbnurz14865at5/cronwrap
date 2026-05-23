"""Job execution jitter — adds randomised delay before running a job
to avoid thundering-herd problems when many cron jobs fire simultaneously."""

from __future__ import annotations

import random
import time
from dataclasses import dataclass, field
from typing import Optional


class JitterError(Exception):
    """Raised when jitter configuration is invalid."""


@dataclass
class JitterPolicy:
    job_name: str
    min_seconds: float = 0.0
    max_seconds: float = 30.0
    seed: Optional[int] = None  # for deterministic testing

    def __post_init__(self) -> None:
        if self.min_seconds < 0:
            raise JitterError("min_seconds must be >= 0")
        if self.max_seconds < self.min_seconds:
            raise JitterError("max_seconds must be >= min_seconds")

    # ------------------------------------------------------------------
    # Serialisation
    # ------------------------------------------------------------------

    def to_dict(self) -> dict:
        d: dict = {
            "job_name": self.job_name,
            "min_seconds": self.min_seconds,
            "max_seconds": self.max_seconds,
        }
        if self.seed is not None:
            d["seed"] = self.seed
        return d

    @classmethod
    def from_dict(cls, data: dict) -> "JitterPolicy":
        required = {"job_name"}
        missing = required - data.keys()
        if missing:
            raise JitterError(f"Missing required fields: {missing}")
        return cls(
            job_name=data["job_name"],
            min_seconds=float(data.get("min_seconds", 0.0)),
            max_seconds=float(data.get("max_seconds", 30.0)),
            seed=data.get("seed"),
        )

    # ------------------------------------------------------------------
    # Core behaviour
    # ------------------------------------------------------------------

    def sample(self) -> float:
        """Return a random delay in seconds within [min_seconds, max_seconds]."""
        rng = random.Random(self.seed)
        return rng.uniform(self.min_seconds, self.max_seconds)

    def apply(self, *, _sleep=time.sleep) -> float:
        """Sleep for the sampled delay and return the actual delay used."""
        delay = self.sample()
        _sleep(delay)
        return delay
