"""Tests for cronwrap.job_throttle and cronwrap.throttle_cli."""
from __future__ import annotations

import json
import time
from pathlib import Path

import pytest

from cronwrap.job_throttle import ThrottleError, ThrottlePolicy
from cronwrap.throttle_cli import build_parser, main


def _make_policy(tmp_path: Path, interval: int = 60) -> ThrottlePolicy:
    return ThrottlePolicy(
        job_name="test-job",
        min_interval_seconds=interval,
        state_dir=str(tmp_path),
    )


# ---------------------------------------------------------------------------
# ThrottlePolicy unit tests
# ---------------------------------------------------------------------------

def test_from_dict_required(tmp_path):
    p = ThrottlePolicy.from_dict({"job_name": "j", "min_interval_seconds": 120})
    assert p.job_name == "j"
    assert p.min_interval_seconds == 120


def test_from_dict_custom_state_dir(tmp_path):
    p = ThrottlePolicy.from_dict({
        "job_name": "j",
        "min_interval_seconds": 30,
        "state_dir": str(tmp_path),
    })
    assert p.state_dir == str(tmp_path)


def test_to_dict_roundtrip(tmp_path):
    p = _make_policy(tmp_path)
    assert ThrottlePolicy.from_dict(p.to_dict()).to_dict() == p.to_dict()


def test_check_allows_initially(tmp_path):
    p = _make_policy(tmp_path)
    assert p.check() == 0.0


def test_acquire_creates_state_file(tmp_path):
    p = _make_policy(tmp_path)
    p.acquire()
    state = tmp_path / "test-job.json"
    assert state.exists()
    data = json.loads(state.read_text())
    assert "last_run" in data


def test_acquire_raises_when_throttled(tmp_path):
    p = _make_policy(tmp_path, interval=9999)
    p.acquire()  # first call succeeds
    with pytest.raises(ThrottleError, match="throttled"):
        p.acquire()  # second call too soon


def test_check_returns_positive_when_throttled(tmp_path):
    p = _make_policy(tmp_path, interval=9999)
    p.acquire()
    remaining = p.check()
    assert remaining > 0


def test_reset_clears_state(tmp_path):
    p = _make_policy(tmp_path, interval=9999)
    p.acquire()
    p.reset()
    assert p.check() == 0.0


def test_reset_noop_when_no_state(tmp_path):
    p = _make_policy(tmp_path)
    p.reset()  # should not raise


def test_acquire_after_window_expires(tmp_path, monkeypatch):
    p = _make_policy(tmp_path, interval=1)
    p.acquire()
    monkeypatch.setattr(time, "time", lambda: time.time() + 2)
    p.acquire()  # should succeed after window


# ---------------------------------------------------------------------------
# CLI tests
# ---------------------------------------------------------------------------

def _run(argv):
    return main(argv)


def test_build_parser_returns_parser():
    parser = build_parser()
    assert parser is not None


def test_cli_check_ok(tmp_path):
    rc = _run(["--state-dir", str(tmp_path), "test-job", "check"])
    assert rc == 0


def test_cli_check_throttled(tmp_path):
    p = _make_policy(tmp_path, interval=9999)
    p.acquire()
    rc = _run(["--state-dir", str(tmp_path), "--min-interval", "9999", "test-job", "check"])
    assert rc == 1


def test_cli_reset(tmp_path):
    p = _make_policy(tmp_path, interval=9999)
    p.acquire()
    rc = _run(["--state-dir", str(tmp_path), "test-job", "reset"])
    assert rc == 0
    assert p.check() == 0.0
