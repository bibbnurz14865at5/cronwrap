"""Tag-based filtering and grouping for cron jobs."""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional
import json


@dataclass
class TagIndex:
    """Maps tags to lists of job names."""
    index: Dict[str, List[str]] = field(default_factory=dict)

    def add(self, job: str, tags: List[str]) -> None:
        """Register a job under each of its tags."""
        for tag in tags:
            self.index.setdefault(tag, [])
            if job not in self.index[tag]:
                self.index[tag].append(job)

    def jobs_for_tag(self, tag: str) -> List[str]:
        """Return all jobs associated with *tag*."""
        return list(self.index.get(tag, []))

    def tags_for_job(self, job: str) -> List[str]:
        """Return all tags associated with *job*."""
        return [tag for tag, jobs in self.index.items() if job in jobs]

    def all_tags(self) -> List[str]:
        return sorted(self.index.keys())

    def to_dict(self) -> Dict[str, List[str]]:
        return {tag: list(jobs) for tag, jobs in self.index.items()}

    @classmethod
    def from_dict(cls, data: Dict[str, List[str]]) -> "TagIndex":
        obj = cls()
        obj.index = {tag: list(jobs) for tag, jobs in data.items()}
        return obj

    def save(self, path: Path) -> None:
        path.write_text(json.dumps(self.to_dict(), indent=2))

    @classmethod
    def load(cls, path: Path) -> "TagIndex":
        if not path.exists():
            return cls()
        return cls.from_dict(json.loads(path.read_text()))


def filter_jobs_by_tags(
    all_jobs: List[str],
    index: TagIndex,
    include_tags: Optional[List[str]] = None,
    exclude_tags: Optional[List[str]] = None,
) -> List[str]:
    """Return jobs matching *include_tags* and not matching *exclude_tags*."""
    result = list(all_jobs)
    if include_tags:
        included: set = set()
        for tag in include_tags:
            included.update(index.jobs_for_tag(tag))
        result = [j for j in result if j in included]
    if exclude_tags:
        excluded: set = set()
        for tag in exclude_tags:
            excluded.update(index.jobs_for_tag(tag))
        result = [j for j in result if j not in excluded]
    return result
