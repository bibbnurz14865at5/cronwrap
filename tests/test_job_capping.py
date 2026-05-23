"""Tests for cronwrap.job_capping."""

from __future__ import annotations

import time
import pytest

from cronwrap.job_capping import CappingError, CappingPolicy


def _make(tmp_path, max_runs=3, window_seconds=60) -> CappingPolicy:
    return CappingPolicy(
        job_name="test_job",
        max_runs=max_runs,
        window_seconds=window_seconds,
        state_dir=str(tmp_path),
    )


def test_from_dict_required(tmp_path):
    p = CappingPolicy.from_dict(
        {"job_name": "j", "max_runs": 5, "window_seconds": 120, "state_dir": str(tmp_path)}
    )
    assert p.job_name == "j"
    assert p.max_runs == 5
    assert p.window_seconds == 120


def test_from_dict_default_state_dir():
    p = CappingPolicy.from_dict({"job_name": "j", "max_runs": 2, "window_seconds": 30})
    assert p.state_dir == "/tmp/cronwrap/capping"


def test_from_dict_missing_raises():
    with pytest.raises(CappingError, match="job_name"):
        CappingPolicy.from_dict({"max_runs": 1, "window_seconds": 60})


def test_to_dict_roundtrip(tmp_path):
    p = _make(tmp_path)
    d = p.to_dict()
    p2 = CappingPolicy.from_dict(d)
    assert p2.job_name == p.job_name
    assert p2.max_runs == p.max_runs
    assert p2.window_seconds == p.window_seconds


def test_check_allows_initially(tmp_path):
    p = _make(tmp_path, max_runs=3)
    assert p.check() is True


def test_remaining_full_initially(tmp_path):
    p = _make(tmp_path, max_runs=3)
    assert p.remaining() == 3


def test_record_run_decrements_remaining(tmp_path):
    p = _make(tmp_path, max_runs=3)
    p.record_run()
    assert p.remaining() == 2


def test_check_blocks_when_capped(tmp_path):
    p = _make(tmp_path, max_runs=2)
    p.record_run()
    p.record_run()
    assert p.check() is False


def test_remaining_zero_when_capped(tmp_path):
    p = _make(tmp_path, max_runs=2)
    p.record_run()
    p.record_run()
    assert p.remaining() == 0


def test_reset_clears_runs(tmp_path):
    p = _make(tmp_path, max_runs=2)
    p.record_run()
    p.record_run()
    p.reset()
    assert p.check() is True
    assert p.remaining() == 2


def test_stale_runs_pruned(tmp_path):
    p = _make(tmp_path, max_runs=2, window_seconds=1)
    p.record_run()
    p.record_run()
    assert p.check() is False
    time.sleep(1.1)
    assert p.check() is True
    assert p.remaining() == 2


def test_state_file_created(tmp_path):
    p = _make(tmp_path)
    p.record_run()
    state_file = tmp_path / "test_job.json"
    assert state_file.exists()


def test_reset_noop_when_no_state(tmp_path):
    p = _make(tmp_path)
    p.reset()  # should not raise
    assert p.remaining() == 3
