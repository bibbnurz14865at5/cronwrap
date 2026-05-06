"""Tests for cronwrap.job_summary."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from cronwrap.history import JobHistory
from cronwrap.job_summary import (
    JobSummaryEntry,
    build_summary,
    summary_to_json,
)


def _write_history(tmp_path: Path, job_name: str, entries):
    history = JobHistory(job_name, history_dir=str(tmp_path))
    for e in entries:
        history.record(e)


def _entry(exit_code=0, duration=1.0, timed_out=False):
    from cronwrap.history import HistoryEntry
    return HistoryEntry(exit_code=exit_code, duration=duration, timed_out=timed_out)


# ---------------------------------------------------------------------------
# JobSummaryEntry
# ---------------------------------------------------------------------------

def test_entry_to_dict_required_keys():
    e = JobSummaryEntry(
        job_name="myjob", total_runs=5,
        success_rate=0.8, avg_duration=2.5, last_status="ok"
    )
    d = e.to_dict()
    assert d["job_name"] == "myjob"
    assert d["total_runs"] == 5
    assert "success_rate" in d
    assert "avg_duration" in d
    assert d["last_status"] == "ok"


def test_entry_to_dict_omits_extra_when_empty():
    e = JobSummaryEntry(
        job_name="j", total_runs=1,
        success_rate=1.0, avg_duration=0.1, last_status="ok"
    )
    assert "extra" not in e.to_dict()


def test_entry_to_dict_includes_extra_when_set():
    e = JobSummaryEntry(
        job_name="j", total_runs=1,
        success_rate=1.0, avg_duration=0.1, last_status="ok",
        extra={"env": "prod"}
    )
    assert e.to_dict()["extra"] == {"env": "prod"}


def test_entry_to_json_valid():
    e = JobSummaryEntry(
        job_name="j", total_runs=3,
        success_rate=0.667, avg_duration=1.0, last_status="fail"
    )
    parsed = json.loads(e.to_json())
    assert parsed["job_name"] == "j"


# ---------------------------------------------------------------------------
# build_summary
# ---------------------------------------------------------------------------

def test_build_summary_empty_dir(tmp_path):
    assert build_summary(str(tmp_path)) == []


def test_build_summary_nonexistent_dir(tmp_path):
    result = build_summary(str(tmp_path / "missing"))
    assert result == []


def test_build_summary_single_job(tmp_path):
    _write_history(tmp_path, "backup", [
        _entry(exit_code=0, duration=10.0),
        _entry(exit_code=0, duration=12.0),
    ])
    results = build_summary(str(tmp_path))
    assert len(results) == 1
    r = results[0]
    assert r.job_name == "backup"
    assert r.total_runs == 2
    assert r.success_rate == 1.0
    assert r.last_status == "ok"


def test_build_summary_last_status_fail(tmp_path):
    _write_history(tmp_path, "report", [
        _entry(exit_code=0),
        _entry(exit_code=1),
    ])
    results = build_summary(str(tmp_path))
    assert results[0].last_status == "fail"


def test_build_summary_last_status_timeout(tmp_path):
    _write_history(tmp_path, "slow", [
        _entry(exit_code=1, timed_out=True),
    ])
    results = build_summary(str(tmp_path))
    assert results[0].last_status == "timeout"


def test_build_summary_multiple_jobs_sorted(tmp_path):
    for name in ["zzz", "aaa", "mmm"]:
        _write_history(tmp_path, name, [_entry()])
    names = [r.job_name for r in build_summary(str(tmp_path))]
    assert names == sorted(names)


def test_summary_to_json_returns_list(tmp_path):
    _write_history(tmp_path, "myjob", [_entry()])
    data = json.loads(summary_to_json(str(tmp_path)))
    assert isinstance(data, list)
    assert data[0]["job_name"] == "myjob"
