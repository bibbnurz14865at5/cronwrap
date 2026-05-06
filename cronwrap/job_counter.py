"""Simple per-job execution counter with persistence."""
from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Optional


class CounterError(Exception):
    """Raised when the counter store encounters an error."""


@dataclass
class CounterRecord:
    job_name: str
    total: int = 0
    successes: int = 0
    failures: int = 0
    extra: Dict[str, object] = field(default_factory=dict)

    def to_dict(self) -> dict:
        d = {
            "job_name": self.job_name,
            "total": self.total,
            "successes": self.successes,
            "failures": self.failures,
        }
        if self.extra:
            d["extra"] = self.extra
        return d

    @classmethod
    def from_dict(cls, data: dict) -> "CounterRecord":
        return cls(
            job_name=data["job_name"],
            total=data.get("total", 0),
            successes=data.get("successes", 0),
            failures=data.get("failures", 0),
            extra=data.get("extra", {}),
        )

    @property
    def success_rate(self) -> Optional[float]:
        if self.total == 0:
            return None
        return round(self.successes / self.total, 4)


class JobCounter:
    def __init__(self, state_dir: str) -> None:
        self.state_dir = Path(state_dir)
        self.state_dir.mkdir(parents=True, exist_ok=True)

    def _path(self, job_name: str) -> Path:
        safe = job_name.replace(os.sep, "_")
        return self.state_dir / f"{safe}.counter.json"

    def _load(self, job_name: str) -> CounterRecord:
        p = self._path(job_name)
        if not p.exists():
            return CounterRecord(job_name=job_name)
        try:
            return CounterRecord.from_dict(json.loads(p.read_text()))
        except (json.JSONDecodeError, KeyError) as exc:
            raise CounterError(f"Corrupt counter file for {job_name!r}: {exc}") from exc

    def _save(self, record: CounterRecord) -> None:
        self._path(record.job_name).write_text(json.dumps(record.to_dict(), indent=2))

    def increment(self, job_name: str, *, success: bool) -> CounterRecord:
        rec = self._load(job_name)
        rec.total += 1
        if success:
            rec.successes += 1
        else:
            rec.failures += 1
        self._save(rec)
        return rec

    def get(self, job_name: str) -> CounterRecord:
        return self._load(job_name)

    def reset(self, job_name: str) -> CounterRecord:
        rec = CounterRecord(job_name=job_name)
        self._save(rec)
        return rec
