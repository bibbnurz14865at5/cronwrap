"""Tests for cronwrap.job_quota."""
import time
import pytest
from cronwrap.job_quota import QuotaPolicy, QuotaExceeded


def _make_policy(tmp_path, max_runs=3, window_seconds=60):
    return QuotaPolicy(
        max_runs=max_runs,
        window_seconds=window_seconds,
        state_dir=str(tmp_path / "quota"),
    )


def test_from_dict_required(tmp_path):
    p = QuotaPolicy.from_dict({"max_runs": 5, "window_seconds": 3600, "state_dir": str(tmp_path)})
    assert p.max_runs == 5
    assert p.window_seconds == 3600


def test_from_dict_default_state_dir():
    p = QuotaPolicy.from_dict({"max_runs": 2, "window_seconds": 120})
    assert p.state_dir == "/tmp/cronwrap/quota"


def test_to_dict_roundtrip(tmp_path):
    p = _make_policy(tmp_path)
    d = p.to_dict()
    p2 = QuotaPolicy.from_dict(d)
    assert p2.max_runs == p.max_runs
    assert p2.window_seconds == p.window_seconds


def test_check_allows_initially(tmp_path):
    p = _make_policy(tmp_path, max_runs=3)
    remaining = p.check("myjob", now=1000.0)
    assert remaining == 3


def test_record_and_check_decrements(tmp_path):
    p = _make_policy(tmp_path, max_runs=3)
    now = 1000.0
    p.record("myjob", now=now)
    p.record("myjob", now=now + 1)
    remaining = p.check("myjob", now=now + 2)
    assert remaining == 1


def test_check_raises_when_quota_exceeded(tmp_path):
    p = _make_policy(tmp_path, max_runs=2)
    now = 1000.0
    p.record("myjob", now=now)
    p.record("myjob", now=now + 1)
    with pytest.raises(QuotaExceeded, match="myjob"):
        p.check("myjob", now=now + 2)


def test_old_timestamps_pruned(tmp_path):
    p = _make_policy(tmp_path, max_runs=2, window_seconds=60)
    old = 1000.0
    p.record("myjob", now=old)
    p.record("myjob", now=old + 1)
    # advance past window
    remaining = p.check("myjob", now=old + 120)
    assert remaining == 2


def test_reset_clears_state(tmp_path):
    p = _make_policy(tmp_path, max_runs=1)
    now = 1000.0
    p.record("myjob", now=now)
    with pytest.raises(QuotaExceeded):
        p.check("myjob", now=now + 1)
    p.reset("myjob")
    assert p.check("myjob", now=now + 2) == 1


def test_independent_jobs(tmp_path):
    p = _make_policy(tmp_path, max_runs=1)
    now = 1000.0
    p.record("job_a", now=now)
    # job_b unaffected
    assert p.check("job_b", now=now) == 1


def test_state_dir_created(tmp_path):
    state_dir = tmp_path / "new" / "quota"
    p = QuotaPolicy(max_runs=3, window_seconds=60, state_dir=str(state_dir))
    p.record("myjob", now=1000.0)
    assert state_dir.exists()
