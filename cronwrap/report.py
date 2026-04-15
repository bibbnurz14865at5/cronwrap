"""Human-readable reporting helpers for job history."""
from __future__ import annotations

from typing import List

from cronwrap.history import HistoryEntry, JobHistory


def _pct(numerator: int, denominator: int) -> str:
    if denominator == 0:
        return "n/a"
    return f"{100 * numerator / denominator:.1f}%"


def summarise_job(job_name: str, history_dir: str, last_n: int = 50) -> dict:
    """Return a summary dict for a single job."""
    jh = JobHistory(history_dir)
    entries: List[HistoryEntry] = jh.load(job_name)[-last_n:]

    if not entries:
        return {"job": job_name, "runs": 0, "success_rate": "n/a", "last_status": None,
                "avg_duration_s": None, "last_ran": None}

    successes = sum(1 for e in entries if e.success)
    durations = [e.duration_s for e in entries if e.duration_s is not None]
    avg_dur = round(sum(durations) / len(durations), 2) if durations else None
    last = entries[-1]

    return {
        "job": job_name,
        "runs": len(entries),
        "success_rate": _pct(successes, len(entries)),
        "last_status": "ok" if last.success else "fail",
        "avg_duration_s": avg_dur,
        "last_ran": last.timestamp,
    }


def summarise_all(history_dir: str, last_n: int = 50) -> List[dict]:
    """Return summary dicts for every job found in *history_dir*."""
    import os

    if not os.path.isdir(history_dir):
        return []

    job_names = [
        fname[:-len(".jsonl")]
        for fname in os.listdir(history_dir)
        if fname.endswith(".jsonl")
    ]
    return [summarise_job(name, history_dir, last_n) for name in sorted(job_names)]


def tail(job_name: str, history_dir: str, n: int = 10) -> List[HistoryEntry]:
    """Return the last *n* history entries for *job_name*."""
    jh = JobHistory(history_dir)
    return jh.load(job_name)[-n:]
