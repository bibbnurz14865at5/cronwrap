"""Track incremental progress for long-running cron jobs."""
from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional


class ProgressError(Exception):
    """Raised when a progress operation fails."""


@dataclass
class ProgressRecord:
    job_name: str
    step: int
    total: int
    message: str
    updated_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    extra: Dict[str, Any] = field(default_factory=dict)

    @property
    def pct(self) -> float:
        if self.total <= 0:
            return 0.0
        return round(100.0 * self.step / self.total, 2)

    def to_dict(self) -> Dict[str, Any]:
        d: Dict[str, Any] = {
            "job_name": self.job_name,
            "step": self.step,
            "total": self.total,
            "pct": self.pct,
            "message": self.message,
            "updated_at": self.updated_at,
        }
        if self.extra:
            d["extra"] = self.extra
        return d

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ProgressRecord":
        return cls(
            job_name=data["job_name"],
            step=int(data["step"]),
            total=int(data["total"]),
            message=data["message"],
            updated_at=data.get("updated_at", datetime.now(timezone.utc).isoformat()),
            extra=data.get("extra", {}),
        )


class JobProgress:
    def __init__(self, state_dir: str = "/tmp/cronwrap/progress") -> None:
        self.state_dir = Path(state_dir)
        self.state_dir.mkdir(parents=True, exist_ok=True)

    def _path(self, job_name: str) -> Path:
        safe = job_name.replace("/", "_").replace(" ", "_")
        return self.state_dir / f"{safe}.json"

    def update(self, job_name: str, step: int, total: int, message: str = "",
               extra: Optional[Dict[str, Any]] = None) -> ProgressRecord:
        if step < 0 or total < 0:
            raise ProgressError("step and total must be non-negative")
        record = ProgressRecord(
            job_name=job_name,
            step=step,
            total=total,
            message=message,
            extra=extra or {},
        )
        self._path(job_name).write_text(json.dumps(record.to_dict(), indent=2))
        return record

    def get(self, job_name: str) -> Optional[ProgressRecord]:
        p = self._path(job_name)
        if not p.exists():
            return None
        return ProgressRecord.from_dict(json.loads(p.read_text()))

    def clear(self, job_name: str) -> None:
        p = self._path(job_name)
        if p.exists():
            p.unlink()
