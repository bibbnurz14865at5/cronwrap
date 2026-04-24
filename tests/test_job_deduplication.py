"""Tests for cronwrap.job_deduplication."""

import json
import time
import pytest

from cronwrap.job_deduplication import DeduplicationPolicy, DeduplicationError


def _make_policy(tmp_path, window: int = 60) -> DeduplicationPolicy:
    return DeduplicationPolicy(
        job_name="test_job",
        window_seconds=window,
        state_dir=str(tmp_path),
    )


def test_from_dict_required(tmp_path):
    p = DeduplicationPolicy.from_dict(
        {"job_name": "j", "window_seconds": 30, "state_dir": str(tmp_path)}
    )
    assert p.job_name == "j"
    assert p.window_seconds == 30


def test_from_dict_default_state_dir():
    p = DeduplicationPolicy.from_dict({"job_name": "j", "window_seconds": 10})
    assert p.state_dir == "/tmp/cronwrap/dedup"


def test_from_dict_missing_raises():
    with pytest.raises(ValueError, match="Missing required keys"):
        DeduplicationPolicy.from_dict({"job_name": "j"})


def test_to_dict_roundtrip(tmp_path):
    p = _make_policy(tmp_path, window=45)
    d = p.to_dict()
    p2 = DeduplicationPolicy.from_dict(d)
    assert p2.job_name == p.job_name
    assert p2.window_seconds == p.window_seconds
    assert p2.state_dir == p.state_dir


def test_check_allows_first_run(tmp_path):
    p = _make_policy(tmp_path)
    p.check("run-001")  # should not raise
    state_file = tmp_path / "test_job.dedup.json"
    assert state_file.exists()


def test_check_state_file_contains_run_id(tmp_path):
    p = _make_policy(tmp_path)
    p.check("run-abc")
    state = json.loads((tmp_path / "test_job.dedup.json").read_text())
    assert state["run_id"] == "run-abc"
    assert "started_at" in state


def test_check_duplicate_raises(tmp_path):
    p = _make_policy(tmp_path, window=60)
    p.check("run-001")
    with pytest.raises(DeduplicationError, match="Duplicate run detected"):
        p.check("run-002")


def test_check_same_run_id_does_not_raise(tmp_path):
    p = _make_policy(tmp_path, window=60)
    p.check("run-001")
    p.check("run-001")  # same run_id, should not raise


def test_check_allows_after_window_expires(tmp_path):
    p = _make_policy(tmp_path, window=1)
    p.check("run-001")
    # Backdate the state file
    state_file = tmp_path / "test_job.dedup.json"
    state = json.loads(state_file.read_text())
    state["started_at"] = time.time() - 2
    state_file.write_text(json.dumps(state))
    p.check("run-002")  # window expired, should not raise


def test_release_removes_state(tmp_path):
    p = _make_policy(tmp_path)
    p.check("run-001")
    state_file = tmp_path / "test_job.dedup.json"
    assert state_file.exists()
    p.release()
    assert not state_file.exists()


def test_release_noop_when_no_state(tmp_path):
    p = _make_policy(tmp_path)
    p.release()  # should not raise


def test_error_message_includes_job_name(tmp_path):
    p = _make_policy(tmp_path, window=60)
    p.check("run-001")
    with pytest.raises(DeduplicationError, match="test_job"):
        p.check("run-002")
