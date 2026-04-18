import json
from pathlib import Path

import pytest

from cronwrap.history import JobHistory, HistoryEntry
from cronwrap.timeout_policy import TimeoutPolicy
from cronwrap.job_timeout_tracker import (
    TimeoutViolation,
    find_violations,
    violations_to_json,
)


def _write_entry(history_dir: Path, job: str, duration: float, success: bool = True):
    h = JobHistory(history_dir / job)
    e = HistoryEntry(job_name=job, success=success, duration=duration, exit_code=0)
    h.record(e)


def test_violation_to_dict_keys():
    v = TimeoutViolation(job_name="backup", duration=90.0, limit=60.0, timestamp="2024-01-01T00:00:00")
    d = v.to_dict()
    assert set(d.keys()) == {"job_name", "duration", "limit", "timestamp"}


def test_violation_roundtrip():
    v = TimeoutViolation(job_name="sync", duration=200.0, limit=120.0, timestamp="2024-06-01T12:00:00")
    assert TimeoutViolation.from_dict(v.to_dict()) == v


def test_find_violations_none_when_under_limit(tmp_path):
    _write_entry(tmp_path, "fast_job", duration=10.0)
    policy = TimeoutPolicy(warn_after=60.0)
    assert find_violations(tmp_path, policy) == []


def test_find_violations_detects_exceeded(tmp_path):
    _write_entry(tmp_path, "slow_job", duration=90.0)
    policy = TimeoutPolicy(warn_after=60.0)
    violations = find_violations(tmp_path, policy)
    assert len(violations) == 1
    assert violations[0].job_name == "slow_job"
    assert violations[0].duration == 90.0


def test_find_violations_filter_by_job_name(tmp_path):
    _write_entry(tmp_path, "job_a", duration=90.0)
    _write_entry(tmp_path, "job_b", duration=90.0)
    policy = TimeoutPolicy(warn_after=60.0)
    violations = find_violations(tmp_path, policy, job_name="job_a")
    assert all(v.job_name == "job_a" for v in violations)
    assert len(violations) == 1


def test_find_violations_skips_none_duration(tmp_path):
    h = JobHistory(tmp_path / "nodur")
    e = HistoryEntry(job_name="nodur", success=True, duration=None, exit_code=0)
    h.record(e)
    policy = TimeoutPolicy(warn_after=1.0)
    assert find_violations(tmp_path, policy) == []


def test_violations_to_json_valid(tmp_path):
    _write_entry(tmp_path, "j", duration=200.0)
    policy = TimeoutPolicy(kill_after=100.0)
    violations = find_violations(tmp_path, policy)
    out = violations_to_json(violations)
    parsed = json.loads(out)
    assert isinstance(parsed, list)
    assert parsed[0]["job_name"] == "j"


def test_find_violations_multiple_entries(tmp_path):
    for d in [30.0, 70.0, 110.0]:
        _write_entry(tmp_path, "multi", duration=d)
    policy = TimeoutPolicy(warn_after=60.0)
    violations = find_violations(tmp_path, policy)
    assert len(violations) == 2
