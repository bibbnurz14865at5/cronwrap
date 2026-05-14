"""Quota usage forecasting: project when a job will exhaust its quota."""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional


class QuotaForecastError(Exception):
    """Raised when quota forecasting fails."""


@dataclass
class QuotaForecastResult:
    job_name: str
    quota_limit: int
    current_usage: int
    avg_usage_per_period: float
    periods_remaining: Optional[float]  # None when avg is 0
    will_exhaust: bool
    extra: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        d = {
            "job_name": self.job_name,
            "quota_limit": self.quota_limit,
            "current_usage": self.current_usage,
            "avg_usage_per_period": round(self.avg_usage_per_period, 4),
            "periods_remaining": self.periods_remaining,
            "will_exhaust": self.will_exhaust,
        }
        if self.extra:
            d["extra"] = self.extra
        return d

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), indent=2)

    @classmethod
    def from_dict(cls, d: dict) -> "QuotaForecastResult":
        return cls(
            job_name=d["job_name"],
            quota_limit=d["quota_limit"],
            current_usage=d["current_usage"],
            avg_usage_per_period=d["avg_usage_per_period"],
            periods_remaining=d.get("periods_remaining"),
            will_exhaust=d["will_exhaust"],
            extra=d.get("extra", {}),
        )


def forecast_quota(
    job_name: str,
    quota_limit: int,
    usage_history: List[int],
    current_usage: int,
    extra: Optional[dict] = None,
) -> QuotaForecastResult:
    """Forecast remaining periods before quota exhaustion.

    Args:
        job_name: Identifier for the job.
        quota_limit: Maximum allowed usage.
        usage_history: List of per-period usage counts (most recent last).
        current_usage: Usage consumed so far in the current period.
        extra: Optional metadata to attach.
    """
    if quota_limit <= 0:
        raise QuotaForecastError("quota_limit must be positive")

    avg = sum(usage_history) / len(usage_history) if usage_history else 0.0
    remaining_capacity = max(0, quota_limit - current_usage)

    if avg == 0.0:
        periods_remaining = None
        will_exhaust = False
    else:
        periods_remaining = round(remaining_capacity / avg, 4)
        will_exhaust = periods_remaining < 1.0

    return QuotaForecastResult(
        job_name=job_name,
        quota_limit=quota_limit,
        current_usage=current_usage,
        avg_usage_per_period=avg,
        periods_remaining=periods_remaining,
        will_exhaust=will_exhaust,
        extra=extra or {},
    )
