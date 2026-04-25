"""Tests for cronwrap.job_budget."""
from __future__ import annotations

import json
import time

import pytest

from cronwrap.job_budget import BudgetError, BudgetPolicy


def _make_policy(tmp_path, max_runs=3, window_seconds=60) -> BudgetPolicy:
    return BudgetPolicy(
        job_name="test_job",
        max_runs=max_runs,
        window_seconds=window_seconds,
        state_dir=str(tmp_path),
    )


def test_from_dict_required(tmp_path):
    policy = BudgetPolicy.from_dict(
        {"job_name": "j", "max_runs": 5, "window_seconds": 3600}
    )
    assert policy.job_name == "j"
    assert policy.max_runs == 5
    assert policy.window_seconds == 3600


def test_from_dict_default_state_dir():
    policy = BudgetPolicy.from_dict(
        {"job_name": "j", "max_runs": 2, "window_seconds": 60}
    )
    assert policy.state_dir == "/tmp/cronwrap/budget"


def test_from_dict_missing_raises():
    with pytest.raises(ValueError, match="missing keys"):
        BudgetPolicy.from_dict({"job_name": "j", "max_runs": 2})


def test_to_dict_roundtrip(tmp_path):
    policy = _make_policy(tmp_path)
    d = policy.to_dict()
    restored = BudgetPolicy.from_dict(d)
    assert restored.job_name == policy.job_name
    assert restored.max_runs == policy.max_runs
    assert restored.window_seconds == policy.window_seconds


def test_check_allows_initially(tmp_path):
    policy = _make_policy(tmp_path, max_runs=3)
    remaining = policy.check()
    assert remaining == 3


def test_record_increments_count(tmp_path):
    policy = _make_policy(tmp_path, max_runs=5)
    now = time.time()
    policy.record(now=now)
    policy.record(now=now + 1)
    assert policy.current_count(now=now + 2) == 2


def test_check_raises_when_exhausted(tmp_path):
    policy = _make_policy(tmp_path, max_runs=2)
    now = time.time()
    policy.record(now=now)
    policy.record(now=now + 1)
    with pytest.raises(BudgetError, match="exhausted"):
        policy.check(now=now + 2)


def test_check_remaining_decrements(tmp_path):
    policy = _make_policy(tmp_path, max_runs=3)
    now = time.time()
    policy.record(now=now)
    remaining = policy.check(now=now + 1)
    assert remaining == 2


def test_old_timestamps_pruned(tmp_path):
    policy = _make_policy(tmp_path, max_runs=2, window_seconds=10)
    old = time.time() - 100
    policy.record(now=old)
    policy.record(now=old)
    # Both are outside the window — budget should be available
    assert policy.current_count() == 0
    assert policy.check() == 2


def test_reset_clears_state(tmp_path):
    policy = _make_policy(tmp_path, max_runs=2)
    now = time.time()
    policy.record(now=now)
    policy.record(now=now + 1)
    policy.reset()
    assert policy.current_count() == 0


def test_state_file_created(tmp_path):
    policy = _make_policy(tmp_path)
    policy.record()
    state_file = tmp_path / "test_job.json"
    assert state_file.exists()
    data = json.loads(state_file.read_text())
    assert isinstance(data, list)
    assert len(data) == 1


def test_corrupted_state_treated_as_empty(tmp_path):
    policy = _make_policy(tmp_path, max_runs=3)
    state_file = tmp_path / "test_job.json"
    state_file.write_text("not-json")
    assert policy.current_count() == 0
