"""Job history archiver: move old history entries to a compressed archive."""

from __future__ import annotations

import gzip
import json
import os
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional


class ArchiveError(Exception):
    """Raised when archiving fails."""


@dataclass
class ArchivePolicy:
    job_name: str
    history_dir: str
    archive_dir: str
    older_than_days: int = 30
    compress: bool = True

    @classmethod
    def from_dict(cls, data: dict) -> "ArchivePolicy":
        required = {"job_name", "history_dir", "archive_dir"}
        missing = required - data.keys()
        if missing:
            raise ArchiveError(f"Missing required keys: {missing}")
        return cls(
            job_name=data["job_name"],
            history_dir=data["history_dir"],
            archive_dir=data["archive_dir"],
            older_than_days=int(data.get("older_than_days", 30)),
            compress=bool(data.get("compress", True)),
        )

    def to_dict(self) -> dict:
        return {
            "job_name": self.job_name,
            "history_dir": self.history_dir,
            "archive_dir": self.archive_dir,
            "older_than_days": self.older_than_days,
            "compress": self.compress,
        }


@dataclass
class ArchiveResult:
    archived: int = 0
    skipped: int = 0
    archive_path: Optional[str] = None

    def __repr__(self) -> str:
        return (
            f"ArchiveResult(archived={self.archived}, "
            f"skipped={self.skipped}, archive_path={self.archive_path!r})"
        )


def archive_history(policy: ArchivePolicy) -> ArchiveResult:
    """Move history entries older than policy.older_than_days to an archive file."""
    history_path = Path(policy.history_dir) / f"{policy.job_name}.json"
    if not history_path.exists():
        return ArchiveResult()

    with history_path.open() as fh:
        try:
            entries: List[dict] = json.load(fh)
        except json.JSONDecodeError as exc:
            raise ArchiveError(f"Corrupt history file: {exc}") from exc

    now = datetime.now(timezone.utc)
    cutoff_ts = now.timestamp() - policy.older_than_days * 86400

    to_keep: List[dict] = []
    to_archive: List[dict] = []
    for entry in entries:
        ts = entry.get("timestamp", 0)
        if isinstance(ts, str):
            try:
                ts = datetime.fromisoformat(ts).timestamp()
            except ValueError:
                ts = 0
        if ts < cutoff_ts:
            to_archive.append(entry)
        else:
            to_keep.append(entry)

    if not to_archive:
        return ArchiveResult(skipped=len(to_keep))

    os.makedirs(policy.archive_dir, exist_ok=True)
    label = now.strftime("%Y%m%dT%H%M%S")
    if policy.compress:
        archive_path = (
            Path(policy.archive_dir) / f"{policy.job_name}_{label}.json.gz"
        )
        with gzip.open(archive_path, "wt", encoding="utf-8") as gz:
            json.dump(to_archive, gz)
    else:
        archive_path = (
            Path(policy.archive_dir) / f"{policy.job_name}_{label}.json"
        )
        with archive_path.open("w") as fh:
            json.dump(to_archive, fh)

    with history_path.open("w") as fh:
        json.dump(to_keep, fh)

    return ArchiveResult(
        archived=len(to_archive),
        skipped=len(to_keep),
        archive_path=str(archive_path),
    )
