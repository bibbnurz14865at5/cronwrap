"""Tests for cronwrap.job_retry and retry_cli."""
from __future__ import annotations

import pytest

from cronwrap.job_retry import RetryError, RetryPolicy
from cronwrap.retry_cli import build_parser, main


def _make_policy(tmp_path, max_retries=3, job_name="test-job") -> RetryPolicy:
    return RetryPolicy(
        job_name=job_name,
        max_retries=max_retries,
        state_dir=str(tmp_path),
    )


# --- RetryPolicy unit tests ---

def test_from_dict_defaults():
    p = RetryPolicy.from_dict({"job_name": "myjob"})
    assert p.max_retries == 3
    assert p.retry_delay == 0.0
    assert p.state_dir == "/tmp/cronwrap/retry"


def test_from_dict_custom():
    p = RetryPolicy.from_dict({
        "job_name": "myjob",
        "max_retries": 5,
        "retry_delay": 10.0,
        "state_dir": "/tmp/x",
    })
    assert p.max_retries == 5
    assert p.retry_delay == 10.0
    assert p.state_dir == "/tmp/x"


def test_to_dict_roundtrip():
    p = RetryPolicy.from_dict({"job_name": "myjob", "max_retries": 2})
    d = p.to_dict()
    p2 = RetryPolicy.from_dict(d)
    assert p2.max_retries == p.max_retries
    assert p2.job_name == p.job_name


def test_initial_attempts_zero(tmp_path):
    p = _make_policy(tmp_path)
    assert p.attempts() == 0


def test_not_exhausted_initially(tmp_path):
    p = _make_policy(tmp_path)
    assert not p.exhausted()


def test_record_attempt_increments(tmp_path):
    p = _make_policy(tmp_path)
    p.record_attempt()
    assert p.attempts() == 1


def test_exhausted_after_max_retries(tmp_path):
    p = _make_policy(tmp_path, max_retries=2)
    p.record_attempt()
    p.record_attempt()
    assert p.exhausted()


def test_check_raises_when_exhausted(tmp_path):
    p = _make_policy(tmp_path, max_retries=1)
    p.record_attempt()
    with pytest.raises(RetryError, match="exhausted"):
        p.check()


def test_check_passes_when_not_exhausted(tmp_path):
    p = _make_policy(tmp_path, max_retries=3)
    p.record_attempt()
    p.check()  # should not raise


def test_reset_clears_state(tmp_path):
    p = _make_policy(tmp_path)
    p.record_attempt()
    p.record_attempt()
    p.reset()
    assert p.attempts() == 0


def test_reset_noop_when_no_state(tmp_path):
    p = _make_policy(tmp_path)
    p.reset()  # should not raise


# --- retry_cli tests ---

def _run(args):
    return main(args)


def test_build_parser_returns_parser():
    p = build_parser()
    assert p is not None


def test_no_command_returns_1(tmp_path):
    assert _run(["--state-dir", str(tmp_path)]) == 1


def test_show_command(tmp_path):
    p = _make_policy(tmp_path)
    p.record_attempt()
    rc = _run(["--state-dir", str(tmp_path), "show", "test-job"])
    assert rc == 0


def test_reset_command(tmp_path):
    p = _make_policy(tmp_path)
    p.record_attempt()
    rc = _run(["--state-dir", str(tmp_path), "reset", "test-job"])
    assert rc == 0
    assert p.attempts() == 0
