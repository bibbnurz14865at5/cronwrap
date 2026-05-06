"""Job health scoring based on recent history metrics."""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from cronwrap.history import JobHistory


class ScoringError(Exception):
    """Raised when scoring cannot be computed."""


@dataclass
class ScoreResult:
    job_name: str
    score: float          # 0.0 – 100.0
    success_rate: float
    avg_duration: float
    sample_size: int
    grade: str = field(init=False)
    extra: dict = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.score >= 90:
            self.grade = "A"
        elif self.score >= 75:
            self.grade = "B"
        elif self.score >= 60:
            self.grade = "C"
        elif self.score >= 40:
            self.grade = "D"
        else:
            self.grade = "F"

    def to_dict(self) -> dict:
        d = {
            "job_name": self.job_name,
            "score": round(self.score, 2),
            "grade": self.grade,
            "success_rate": round(self.success_rate, 4),
            "avg_duration": round(self.avg_duration, 3),
            "sample_size": self.sample_size,
        }
        if self.extra:
            d["extra"] = self.extra
        return d

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), indent=2)


def compute_score(
    job_name: str,
    history_dir: str,
    window: int = 30,
    duration_penalty_threshold: float = 60.0,
) -> ScoreResult:
    """Compute a health score (0-100) for *job_name* from its recent history.

    The score is weighted: 70 % success rate + 30 % duration efficiency.
    A duration penalty is applied when avg_duration exceeds
    *duration_penalty_threshold* seconds.
    """
    hist = JobHistory(job_name=job_name, history_dir=history_dir)
    entries = hist.load()
    if not entries:
        raise ScoringError(f"No history found for job '{job_name}'")

    recent = entries[-window:]
    sample_size = len(recent)
    successes = sum(1 for e in recent if e.success)
    sr = successes / sample_size

    durations = [e.duration for e in recent if e.duration is not None]
    avg_dur = sum(durations) / len(durations) if durations else 0.0

    # Duration component: full marks if under threshold, linear decay above.
    if avg_dur <= duration_penalty_threshold:
        dur_score = 1.0
    else:
        excess = avg_dur - duration_penalty_threshold
        dur_score = max(0.0, 1.0 - excess / duration_penalty_threshold)

    score = (sr * 70.0) + (dur_score * 30.0)
    return ScoreResult(
        job_name=job_name,
        score=score,
        success_rate=sr,
        avg_duration=avg_dur,
        sample_size=sample_size,
    )
