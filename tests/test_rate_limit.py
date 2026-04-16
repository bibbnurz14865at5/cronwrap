"""Tests for cronwrap.rate_limit."""

import json
import time
from pathlib import Path

import pytest

from cronwrap.rate_limit import RateLimitPolicy


def _make_policy(tmp_path: Path, cooldown: int = 60) -> RateLimitPolicy:
    return RateLimitPolicy(
        cooldown_seconds=cooldown,
        state_file=tmp_path / "rl.json",
    )


def test_from_dict_defaults():
    p = RateLimitPolicy.from_dict({})
    assert p.cooldown_seconds == 3600
    assert str(p.state_file) == "/tmp/cronwrap_ratelimit.json"


def test_from_dict_custom():
    p = RateLimitPolicy.from_dict({"cooldown_seconds": 300, "state_file": "/tmp/x.json"})
    assert p.cooldown_seconds == 300
    assert str(p.state_file) == "/tmp/x.json"


def test_to_dict_roundtrip():
    p = RateLimitPolicy(cooldown_seconds=900)
    d = p.to_dict()
    p2 = RateLimitPolicy.from_dict(d)
    assert p2.cooldown_seconds == 900


def test_not_suppressed_initially(tmp_path):
    p = _make_policy(tmp_path)
    assert p.is_suppressed("myjob") is False


def test_suppressed_after_record(tmp_path):
    p = _make_policy(tmp_path, cooldown=3600)
    p.record_alert("myjob")
    assert p.is_suppressed("myjob") is True


def test_not_suppressed_after_cooldown_expires(tmp_path):
    p = _make_policy(tmp_path, cooldown=1)
    p.record_alert("myjob")
    time.sleep(1.1)
    assert p.is_suppressed("myjob") is False


def test_reset_clears_state(tmp_path):
    p = _make_policy(tmp_path)
    p.record_alert("myjob")
    assert p.is_suppressed("myjob") is True
    p.reset("myjob")
    assert p.is_suppressed("myjob") is False


def test_multiple_jobs_independent(tmp_path):
    p = _make_policy(tmp_path)
    p.record_alert("job_a")
    assert p.is_suppressed("job_a") is True
    assert p.is_suppressed("job_b") is False


def test_state_persists_across_instances(tmp_path):
    sf = tmp_path / "rl.json"
    p1 = RateLimitPolicy(cooldown_seconds=3600, state_file=sf)
    p1.record_alert("myjob")
    p2 = RateLimitPolicy(cooldown_seconds=3600, state_file=sf)
    assert p2.is_suppressed("myjob") is True


def test_corrupt_state_file_handled(tmp_path):
    sf = tmp_path / "rl.json"
    sf.write_text("not-json")
    p = RateLimitPolicy(cooldown_seconds=60, state_file=sf)
    assert p.is_suppressed("myjob") is False
