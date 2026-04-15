"""Alert policy: decide whether a notification should be sent for a job result."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from cronwrap.history import JobHistory


@dataclass
class AlertPolicy:
    """Controls when alerts are fired for a job.

    Attributes:
        notify_on_failure: Send an alert whenever the job fails.
        notify_on_recovery: Send an alert when the job succeeds after a failure.
        min_consecutive_failures: Only alert after this many consecutive failures.
        cooldown_seconds: Minimum seconds between repeated failure alerts.
    """

    notify_on_failure: bool = True
    notify_on_recovery: bool = True
    min_consecutive_failures: int = 1
    cooldown_seconds: int = 0

    @classmethod
    def from_dict(cls, data: dict) -> "AlertPolicy":
        return cls(
            notify_on_failure=bool(data.get("notify_on_failure", True)),
            notify_on_recovery=bool(data.get("notify_on_recovery", True)),
            min_consecutive_failures=int(data.get("min_consecutive_failures", 1)),
            cooldown_seconds=int(data.get("cooldown_seconds", 0)),
        )

    def to_dict(self) -> dict:
        return {
            "notify_on_failure": self.notify_on_failure,
            "notify_on_recovery": self.notify_on_recovery,
            "min_consecutive_failures": self.min_consecutive_failures,
            "cooldown_seconds": self.cooldown_seconds,
        }


def should_alert(policy: AlertPolicy, history: JobHistory, job_name: str) -> tuple[bool, str]:
    """Return (alert, reason) given the policy and recent job history.

    Parameters
    ----------
    policy:    The AlertPolicy for this job.
    history:   The JobHistory store (used to read past entries).
    job_name:  The name of the job to inspect.

    Returns
    -------
    A tuple of (should_send: bool, reason: str).
    """
    entries = history.load(job_name)
    if not entries:
        return False, "no history"

    latest = entries[-1]

    # --- recovery ---
    if latest.success and policy.notify_on_recovery and len(entries) >= 2:
        previous = entries[-2]
        if not previous.success:
            return True, "recovery after failure"

    if latest.success:
        return False, "job succeeded"

    # --- failure path ---
    if not policy.notify_on_failure:
        return False, "failure alerts disabled"

    consecutive = sum(1 for e in reversed(entries) if not e.success)
    if consecutive < policy.min_consecutive_failures:
        return False, f"only {consecutive} consecutive failure(s), threshold {policy.min_consecutive_failures}"

    if policy.cooldown_seconds > 0 and len(entries) >= 2:
        import time
        previous_failures = [e for e in entries[:-1] if not e.success]
        if previous_failures:
            last_alerted_ts = previous_failures[-1].timestamp
            elapsed = latest.timestamp - last_alerted_ts
            if elapsed < policy.cooldown_seconds:
                return False, f"cooldown active ({elapsed:.0f}s < {policy.cooldown_seconds}s)"

    return True, f"{consecutive} consecutive failure(s)"
