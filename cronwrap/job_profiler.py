"""Job profiling: track per-job timing percentiles and detect regressions."""
from __future__ import annotations

import json
import statistics
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional


class ProfilerError(Exception):
    """Raised when profiler operations fail."""


@dataclass
class ProfileSnapshot:
    job_name: str
    durations: List[float] = field(default_factory=list)

    def p50(self) -> Optional[float]:
        if not self.durations:
            return None
        return statistics.median(self.durations)

    def p95(self) -> Optional[float]:
        if len(self.durations) < 2:
            return None
        sorted_d = sorted(self.durations)
        idx = max(0, int(len(sorted_d) * 0.95) - 1)
        return sorted_d[idx]

    def p99(self) -> Optional[float]:
        if len(self.durations) < 2:
            return None
        sorted_d = sorted(self.durations)
        idx = max(0, int(len(sorted_d) * 0.99) - 1)
        return sorted_d[idx]

    def is_regression(self, duration: float, threshold: float = 2.0) -> bool:
        """Return True if duration exceeds threshold * p95."""
        p = self.p95()
        if p is None or p == 0:
            return False
        return duration > threshold * p

    def to_dict(self) -> dict:
        return {
            "job_name": self.job_name,
            "durations": self.durations,
            "p50": self.p50(),
            "p95": self.p95(),
            "p99": self.p99(),
        }

    @classmethod
    def from_dict(cls, data: dict) -> "ProfileSnapshot":
        return cls(
            job_name=data["job_name"],
            durations=list(data.get("durations", [])),
        )


class JobProfiler:
    """Persist and query per-job duration profiles."""

    def __init__(self, state_dir: str, max_samples: int = 100) -> None:
        self._dir = Path(state_dir)
        self._dir.mkdir(parents=True, exist_ok=True)
        self.max_samples = max_samples

    def _path(self, job_name: str) -> Path:
        safe = job_name.replace("/", "_").replace(" ", "_")
        return self._dir / f"{safe}.profile.json"

    def load(self, job_name: str) -> ProfileSnapshot:
        p = self._path(job_name)
        if not p.exists():
            return ProfileSnapshot(job_name=job_name)
        try:
            data = json.loads(p.read_text())
            return ProfileSnapshot.from_dict(data)
        except Exception as exc:
            raise ProfilerError(f"Failed to load profile for {job_name!r}: {exc}") from exc

    def record(self, job_name: str, duration: float) -> ProfileSnapshot:
        snap = self.load(job_name)
        snap.durations.append(duration)
        if len(snap.durations) > self.max_samples:
            snap.durations = snap.durations[-self.max_samples:]
        self._path(job_name).write_text(json.dumps(snap.to_dict(), indent=2))
        return snap

    def all_snapshots(self) -> Dict[str, ProfileSnapshot]:
        result: Dict[str, ProfileSnapshot] = {}
        for fp in sorted(self._dir.glob("*.profile.json")):
            try:
                data = json.loads(fp.read_text())
                snap = ProfileSnapshot.from_dict(data)
                result[snap.job_name] = snap
            except Exception:
                continue
        return result
