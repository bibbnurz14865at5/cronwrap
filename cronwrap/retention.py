"""History retention policy: prune old entries from job history files."""

from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone
from typing import Optional

from cronwrap.history import JobHistory


class RetentionPolicy:
    """Defines how long history entries should be kept."""

    def __init__(self, max_entries: Optional[int] = None, max_days: Optional[int] = None):
        if max_entries is None and max_days is None:
            raise ValueError("At least one of max_entries or max_days must be specified")
        self.max_entries = max_entries
        self.max_days = max_days

    @classmethod
    def from_dict(cls, data: dict) -> "RetentionPolicy":
        return cls(
            max_entries=data.get("max_entries"),
            max_days=data.get("max_days"),
        )

    def to_dict(self) -> dict:
        return {
            "max_entries": self.max_entries,
            "max_days": self.max_days,
        }


def prune_history(job_name: str, history_dir: str, policy: RetentionPolicy) -> int:
    """Remove entries that violate the retention policy.

    Returns the number of entries removed.
    """
    history = JobHistory(job_name, history_dir)
    entries = history.load()
    original_count = len(entries)

    if policy.max_days is not None:
        cutoff = datetime.now(tz=timezone.utc) - timedelta(days=policy.max_days)
        entries = [
            e for e in entries
            if datetime.fromisoformat(e.timestamp).replace(tzinfo=timezone.utc) >= cutoff
        ]

    if policy.max_entries is not None and len(entries) > policy.max_entries:
        entries = entries[-policy.max_entries:]

    removed = original_count - len(entries)
    if removed > 0:
        history_file = os.path.join(history_dir, f"{job_name}.json")
        import json
        with open(history_file, "w") as fh:
            json.dump([e.to_dict() for e in entries], fh, indent=2)

    return removed


def prune_all(history_dir: str, policy: RetentionPolicy) -> dict:
    """Prune all job history files in history_dir.

    Returns a dict mapping job_name -> number of entries removed.
    """
    results = {}
    if not os.path.isdir(history_dir):
        return results
    for filename in os.listdir(history_dir):
        if filename.endswith(".json"):
            job_name = filename[:-5]
            results[job_name] = prune_history(job_name, history_dir, policy)
    return results
