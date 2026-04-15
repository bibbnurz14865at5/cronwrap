"""Human-readable reporting utilities built on top of JobHistory."""

from __future__ import annotations

from typing import List

from cronwrap.history import HistoryEntry, JobHistory


def _pct(part: int, total: int) -> str:
    if total == 0:
        return "n/a"
    return f"{part / total * 100:.1f}%"


def summarise_job(history: JobHistory, job_name: str, last_n: int = 10) -> str:
    """Return a plain-text summary of the last *last_n* runs for *job_name*."""
    entries: List[HistoryEntry] = history.load_for_job(job_name)[-last_n:]
    if not entries:
        return f"No history found for job '{job_name}'."

    total = len(entries)
    failures = sum(1 for e in entries if e.exit_code != 0 or e.timed_out)
    successes = total - failures
    avg_duration = sum(e.duration for e in entries) / total
    last = entries[-1]

    lines = [
        f"Job: {job_name}",
        f"Runs analysed : {total} (last {last_n} max)",
        f"Successes     : {successes} ({_pct(successes, total)})",
        f"Failures      : {failures} ({_pct(failures, total)})",
        f"Avg duration  : {avg_duration:.2f}s",
        f"Last run      : {last.timestamp}  exit={last.exit_code}"
        + ("  [TIMEOUT]" if last.timed_out else ""),
    ]
    return "\n".join(lines)


def summarise_all(history: JobHistory) -> str:
    """Return a plain-text summary table for every distinct job in history."""
    entries = history.load_all()
    if not entries:
        return "No history recorded yet."

    job_names = list(dict.fromkeys(e.job_name for e in entries))  # preserve order
    sections = [summarise_job(history, name) for name in job_names]
    divider = "-" * 40
    return ("\n" + divider + "\n").join(sections)


def tail(history: JobHistory, job_name: str, n: int = 5) -> List[HistoryEntry]:
    """Return the *n* most recent entries for *job_name*."""
    return history.load_for_job(job_name)[-n:]
