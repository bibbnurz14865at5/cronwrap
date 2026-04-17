"""Exponential backoff policy for retry logic in notifications/webhooks."""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class BackoffPolicy:
    """Exponential backoff with optional jitter and max retries."""
    max_retries: int = 3
    base_delay: float = 1.0   # seconds
    multiplier: float = 2.0
    max_delay: float = 60.0
    jitter: bool = True

    @classmethod
    def from_dict(cls, data: dict) -> "BackoffPolicy":
        known = {"max_retries", "base_delay", "multiplier", "max_delay", "jitter"}
        filtered = {k: v for k, v in data.items() if k in known}
        return cls(**filtered)

    def to_dict(self) -> dict:
        return {
            "max_retries": self.max_retries,
            "base_delay": self.base_delay,
            "multiplier": self.multiplier,
            "max_delay": self.max_delay,
            "jitter": self.jitter,
        }

    def delay_for(self, attempt: int) -> float:
        """Return delay in seconds for the given attempt (0-indexed)."""
        delay = min(self.base_delay * (self.multiplier ** attempt), self.max_delay)
        if self.jitter:
            import random
            delay *= (0.5 + random.random() * 0.5)
        return delay

    def retry(self, fn, *args, **kwargs):
        """Call fn(*args, **kwargs) with retries. Raises last exception on exhaustion."""
        last_exc: Optional[Exception] = None
        for attempt in range(self.max_retries + 1):
            try:
                return fn(*args, **kwargs)
            except Exception as exc:  # noqa: BLE001
                last_exc = exc
                if attempt < self.max_retries:
                    time.sleep(self.delay_for(attempt))
        raise last_exc
