"""Filter jobs from history/registry by tag, status, or schedule."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional

from cronwrap.history import HistoryEntry


@dataclass
class JobFilter:
    tags: List[str] = field(default_factory=list)
    statuses: List[str] = field(default_factory=list)  # 'ok', 'fail', 'timeout'
    job_names: List[str] = field(default_factory=list)
    since: Optional[float] = None  # unix timestamp
    until: Optional[float] = None  # unix timestamp

    @classmethod
    def from_dict(cls, data: dict) -> "JobFilter":
        return cls(
            tags=data.get("tags", []),
            statuses=data.get("statuses", []),
            job_names=data.get("job_names", []),
            since=data.get("since"),
            until=data.get("until"),
        )

    def to_dict(self) -> dict:
        return {
            "tags": self.tags,
            "statuses": self.statuses,
            "job_names": self.job_names,
            "since": self.since,
            "until": self.until,
        }

    def matches(self, entry: HistoryEntry, job_name: str, job_tags: List[str] | None = None) -> bool:
        if self.job_names and job_name not in self.job_names:
            return False
        if self.tags:
            entry_tags = job_tags or []
            if not any(t in entry_tags for t in self.tags):
                return False
        if self.statuses:
            status = "ok" if entry.exit_code == 0 else ("timeout" if entry.timed_out else "fail")
            if status not in self.statuses:
                return False
        ts = entry.timestamp
        if self.since is not None and ts < self.since:
            return False
        if self.until is not None and ts > self.until:
            return False
        return True


def apply_filter(
    entries: List[HistoryEntry],
    job_name: str,
    job_filter: JobFilter,
    job_tags: List[str] | None = None,
) -> List[HistoryEntry]:
    """Return only entries matching the filter."""
    return [e for e in entries if job_filter.matches(e, job_name, job_tags)]
