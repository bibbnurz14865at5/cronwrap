"""Human-readable report generation for cronwrap job history."""

from __future__ import annotations

from typing import List, Optional

from cronwrap.history import HistoryEntry, JobHistory
from cronwrap.metrics import JobMetrics, compute_metrics


def _pct(numerator: int, denominator: int) -> str:
    """Return a percentage string, or '—' when *denominator* is zero."""
    if denominator == 0:
        return "—"
    return f"{100 * numerator / denominator:.1f}%"


def summarise_job(job_name: str, history: JobHistory, limit: Optional[int] = None) -> str:
    """Return a multi-line summary string for a single job."""
    m: JobMetrics = compute_metrics(job_name, history, limit=limit)
    lines = [
        f"Job: {job_name}",
        f"  Runs      : {m.total_runs}",
        f"  Successes : {m.success_count} ({_pct(m.success_count, m.total_runs)})",
        f"  Failures  : {m.failure_count} ({_pct(m.failure_count, m.total_runs)})",
        f"  Timeouts  : {m.timeout_count}",
    ]
    if m.avg_duration is not None:
        lines += [
            f"  Avg dur.  : {m.avg_duration:.3f}s",
            f"  Min dur.  : {m.min_duration:.3f}s",
            f"  Max dur.  : {m.max_duration:.3f}s",
        ]
    return "\n".join(lines)


def summarise_all(history: JobHistory, limit: Optional[int] = None) -> str:
    """Return a combined summary for every job that has recorded history."""
    job_names = history.list_jobs()
    if not job_names:
        return "No job history found."
    sections = [summarise_job(name, history, limit=limit) for name in sorted(job_names)]
    return "\n\n".join(sections)


def tail(job_name: str, history: JobHistory, n: int = 10) -> str:
    """Return a table of the last *n* entries for *job_name*."""
    entries: List[HistoryEntry] = history.load(job_name)[-n:]
    if not entries:
        return f"No history for job '{job_name}'."
    header = f"{'Timestamp':<26} {'Exit':>4}  {'Dur(s)':>8}  {'Timeout':<7}  Stderr snippet"
    sep = "-" * len(header)
    rows = [header, sep]
    for e in entries:
        ts = e.timestamp or ""
        dur = f"{e.duration:.3f}" if e.duration is not None else "      —"
        timed = "yes" if e.timed_out else "no"
        snippet = (e.stderr or "").replace("\n", " ")[:40]
        rows.append(f"{ts:<26} {e.exit_code:>4}  {dur:>8}  {timed:<7}  {snippet}")
    return "\n".join(rows)
