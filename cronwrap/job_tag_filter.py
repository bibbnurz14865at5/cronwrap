"""Filter jobs by tag using the TagIndex, returning matching job names."""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional

from cronwrap.tags import TagIndex


class TagFilterError(Exception):
    """Raised when a tag filter operation fails."""


@dataclass
class TagFilterResult:
    tag: str
    matched: List[str] = field(default_factory=list)
    total: int = 0

    def to_dict(self) -> dict:
        return {
            "tag": self.tag,
            "matched": list(self.matched),
            "total": self.total,
        }

    def to_json(self, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), indent=indent)


def filter_by_tag(
    tag: str,
    tags_file: Path,
    *,
    allowed_jobs: Optional[List[str]] = None,
) -> TagFilterResult:
    """Return all jobs that carry *tag*.

    Parameters
    ----------
    tag:
        The tag to look up.
    tags_file:
        Path to the JSON file managed by :class:`~cronwrap.tags.TagIndex`.
    allowed_jobs:
        Optional allowlist.  When provided only jobs present in this list
        are included in the result.

    Raises
    ------
    TagFilterError
        If *tags_file* exists but cannot be parsed.
    """
    if tags_file.exists():
        try:
            index = TagIndex.load(tags_file)
        except (json.JSONDecodeError, KeyError) as exc:
            raise TagFilterError(f"Cannot read tags file {tags_file}: {exc}") from exc
    else:
        index = TagIndex(path=tags_file)

    jobs = index.jobs_for_tag(tag)

    if allowed_jobs is not None:
        allowed_set = set(allowed_jobs)
        jobs = [j for j in jobs if j in allowed_set]

    return TagFilterResult(tag=tag, matched=sorted(jobs), total=len(jobs))


def jobs_sharing_tags(
    job_name: str,
    tags_file: Path,
) -> List[str]:
    """Return jobs that share at least one tag with *job_name* (excluding itself)."""
    if not tags_file.exists():
        return []

    try:
        index = TagIndex.load(tags_file)
    except (json.JSONDecodeError, KeyError) as exc:
        raise TagFilterError(f"Cannot read tags file {tags_file}: {exc}") from exc

    own_tags = index.tags_for_job(job_name)
    related: set = set()
    for t in own_tags:
        for j in index.jobs_for_tag(t):
            if j != job_name:
                related.add(j)
    return sorted(related)
