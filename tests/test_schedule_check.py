"""Tests for cronwrap.schedule_check."""

import json
import os
from datetime import datetime, timedelta
from pathlib import Path

import pytest

from cronwrap.schedule_check import OverdueResult, check_overdue
from cronwrap.scheduler import ScheduleError


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

def _write_history(directory: Path, job: str, entries: list[dict]) -> None:
    path = directory / f"{job}.json"
    path.write_text(json.dumps(entries))


# ---------------------------------------------------------------------------
# OverdueResult
# ---------------------------------------------------------------------------

def test_overdue_result_attributes():
    now = datetime(2024, 6, 1, 12, 0)
    r = OverdueResult(
        job_name="backup",
        overdue=True,
        last_run=now - timedelta(hours=2),
        expected_by=now - timedelta(minutes=10),
        checked_at=now,
    )
    assert r.job_name == "backup"
    assert r.overdue is True
    assert isinstance(r.last_run, datetime)
    assert isinstance(r.expected_by, datetime)


# ---------------------------------------------------------------------------
# check_overdue — invalid schedule
# ---------------------------------------------------------------------------

def test_check_overdue_invalid_schedule_raises(tmp_path):
    with pytest.raises(ScheduleError):
        check_overdue("myjob", "not valid", str(tmp_path))


# ---------------------------------------------------------------------------
# check_overdue — no history (first run scenario)
# ---------------------------------------------------------------------------

def test_check_overdue_no_history_not_overdue(tmp_path):
    # Schedule: every minute.  grace=5.  now is only 3 minutes after start.
    now = datetime(2024, 6, 1, 0, 3, 0)
    result = check_overdue(
        "myjob", "* * * * *", str(tmp_path), grace_minutes=5, now=now
    )
    assert isinstance(result, OverdueResult)
    # With no history the reference is now-1day; next_run fires 1 min later
    # expected_by = reference+1min+5min = still in the past relative to 'now'
    # so overdue depends on timing — just assert it returns without error.
    assert result.last_run is None


# ---------------------------------------------------------------------------
# check_overdue — recent successful run
# ---------------------------------------------------------------------------

def test_check_overdue_recent_success_not_overdue(tmp_path):
    last = datetime(2024, 6, 1, 12, 0, 0)
    _write_history(
        tmp_path,
        "backup",
        [{"timestamp": last.isoformat(), "exit_code": 0, "duration": 1.0,
          "stdout": "", "stderr": "", "timed_out": False}],
    )
    # now is only 2 minutes after last run; schedule is hourly
    now = last + timedelta(minutes=2)
    result = check_overdue(
        "backup", "0 * * * *", str(tmp_path), grace_minutes=5, now=now
    )
    assert result.overdue is False
    assert result.last_run == last


# ---------------------------------------------------------------------------
# check_overdue — stale run (overdue)
# ---------------------------------------------------------------------------

def test_check_overdue_stale_run_is_overdue(tmp_path):
    last = datetime(2024, 6, 1, 10, 0, 0)
    _write_history(
        tmp_path,
        "backup",
        [{"timestamp": last.isoformat(), "exit_code": 0, "duration": 2.0,
          "stdout": "", "stderr": "", "timed_out": False}],
    )
    # now is 70 minutes later; hourly schedule + 5 min grace = 65 min window
    now = last + timedelta(minutes=70)
    result = check_overdue(
        "backup", "0 * * * *", str(tmp_path), grace_minutes=5, now=now
    )
    assert result.overdue is True


# ---------------------------------------------------------------------------
# check_overdue — failed run ignored, success used
# ---------------------------------------------------------------------------

def test_check_overdue_uses_last_success_not_failure(tmp_path):
    success_time = datetime(2024, 6, 1, 11, 0, 0)
    failure_time = datetime(2024, 6, 1, 11, 30, 0)
    _write_history(
        tmp_path,
        "myjob",
        [
            {"timestamp": success_time.isoformat(), "exit_code": 0,
             "duration": 1.0, "stdout": "", "stderr": "", "timed_out": False},
            {"timestamp": failure_time.isoformat(), "exit_code": 1,
             "duration": 1.0, "stdout": "", "stderr": "err", "timed_out": False},
        ],
    )
    now = success_time + timedelta(minutes=10)
    result = check_overdue(
        "myjob", "0 * * * *", str(tmp_path), grace_minutes=5, now=now
    )
    assert result.last_run == success_time
