"""Tests for cronwrap.job_cooldown."""

import json
import time
from pathlib import Path

import pytest

from cronwrap.job_cooldown import CooldownError, CooldownPolicy


def _make_policy(tmp_path, min_gap: int = 60) -> CooldownPolicy:
    return CooldownPolicy(
        job_name="test-job",
        min_gap_seconds=min_gap,
        state_dir=str(tmp_path),
    )


def test_from_dict_required(tmp_path):
    p = CooldownPolicy.from_dict(
        {"job_name": "j", "min_gap_seconds": 120, "state_dir": str(tmp_path)}
    )
    assert p.job_name == "j"
    assert p.min_gap_seconds == 120


def test_from_dict_default_state_dir():
    p = CooldownPolicy.from_dict({"job_name": "j", "min_gap_seconds": 30})
    assert p.state_dir == "/tmp/cronwrap/cooldown"


def test_to_dict_roundtrip(tmp_path):
    policy = _make_policy(tmp_path, min_gap=90)
    d = policy.to_dict()
    restored = CooldownPolicy.from_dict(d)
    assert restored.job_name == policy.job_name
    assert restored.min_gap_seconds == policy.min_gap_seconds


def test_check_allows_initially(tmp_path):
    policy = _make_policy(tmp_path)
    # No state file — should not raise
    policy.check()


def test_seconds_remaining_zero_when_no_state(tmp_path):
    policy = _make_policy(tmp_path)
    assert policy.seconds_remaining() == 0.0


def test_record_creates_state_file(tmp_path):
    policy = _make_policy(tmp_path)
    policy.record()
    state_file = tmp_path / "test-job.json"
    assert state_file.exists()
    data = json.loads(state_file.read_text())
    assert "last_run" in data
    assert data["last_run"] == pytest.approx(time.time(), abs=2)


def test_check_raises_during_cooldown(tmp_path):
    policy = _make_policy(tmp_path, min_gap=3600)
    policy.record()
    with pytest.raises(CooldownError, match="test-job"):
        policy.check()


def test_seconds_remaining_positive_after_record(tmp_path):
    policy = _make_policy(tmp_path, min_gap=3600)
    policy.record()
    remaining = policy.seconds_remaining()
    assert remaining > 3590  # nearly full gap left


def test_check_allows_after_gap_elapsed(tmp_path):
    policy = _make_policy(tmp_path, min_gap=1)
    # Write a last_run far in the past
    state_file = tmp_path / "test-job.json"
    state_file.write_text(json.dumps({"last_run": time.time() - 10}))
    policy.check()  # should not raise


def test_check_and_record_updates_state(tmp_path):
    policy = _make_policy(tmp_path, min_gap=0)
    policy.check_and_record()
    state_file = tmp_path / "test-job.json"
    assert state_file.exists()


def test_reset_removes_state_file(tmp_path):
    policy = _make_policy(tmp_path)
    policy.record()
    assert (tmp_path / "test-job.json").exists()
    policy.reset()
    assert not (tmp_path / "test-job.json").exists()


def test_reset_noop_when_no_state(tmp_path):
    policy = _make_policy(tmp_path)
    policy.reset()  # should not raise


def test_corrupted_state_treated_as_no_state(tmp_path):
    state_file = tmp_path / "test-job.json"
    state_file.write_text("not-json")
    policy = _make_policy(tmp_path, min_gap=3600)
    assert policy.seconds_remaining() == 0.0
    policy.check()  # should not raise
