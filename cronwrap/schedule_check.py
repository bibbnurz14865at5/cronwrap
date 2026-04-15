"""CLI-facing helpers: check whether a job is overdue given its cron schedule."""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Optional

from cronwrap.history import JobHistory
from cronwrap.scheduler import next_run, validate_cron, ScheduleError


class OverdueResult:
    """Result of an overdue check."""

    def __init__(
        self,
        job_name: str,
        overdue: bool,
        last_run: Optional[datetime],
        expected_by: Optional[datetime],
        checked_at: datetime,
    ) -> None:
        self.job_name = job_name
        self.overdue = overdue
        self.last_run = last_run
        self.expected_by = expected_by
        self.checked_at = checked_at

    def __repr__(self) -> str:  # pragma: no cover
        return (
            f"OverdueResult(job={self.job_name!r}, overdue={self.overdue}, "
            f"expected_by={self.expected_by})"
        )


def check_overdue(
    job_name: str,
    schedule: str,
    history_dir: str,
    grace_minutes: int = 5,
    now: Optional[datetime] = None,
) -> OverdueResult:
    """Return an :class:`OverdueResult` for *job_name*.

    A job is considered overdue when the wall-clock time has passed
    ``next_run(schedule, last_run) + grace_minutes`` and no newer
    successful run is recorded in the history.

    Parameters
    ----------
    job_name:
        Identifier used in the history store.
    schedule:
        Standard 5-field cron expression.
    history_dir:
        Directory passed to :class:`~cronwrap.history.JobHistory`.
    grace_minutes:
        Extra minutes to wait before flagging as overdue.
    now:
        Override the current time (useful in tests).
    """
    if not validate_cron(schedule):
        raise ScheduleError(f"Invalid schedule for job {job_name!r}: {schedule!r}")

    now = now or datetime.utcnow()
    history = JobHistory(job_name, history_dir)
    entries = history.load()

    last_success = next(
        (e for e in reversed(entries) if e.exit_code == 0), None
    )
    last_run_dt: Optional[datetime] = (
        datetime.fromisoformat(last_success.timestamp) if last_success else None
    )

    reference = last_run_dt or (now - timedelta(days=1))
    expected_by = next_run(schedule, after=reference) + timedelta(minutes=grace_minutes)

    overdue = now > expected_by
    return OverdueResult(
        job_name=job_name,
        overdue=overdue,
        last_run=last_run_dt,
        expected_by=expected_by,
        checked_at=now,
    )
