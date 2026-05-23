"""Tests for cronwrap.job_jitter."""

from __future__ import annotations

import pytest

from cronwrap.job_jitter import JitterError, JitterPolicy


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make(**kwargs) -> JitterPolicy:
    defaults = {"job_name": "my_job", "min_seconds": 0.0, "max_seconds": 10.0}
    defaults.update(kwargs)
    return JitterPolicy(**defaults)


# ---------------------------------------------------------------------------
# from_dict / to_dict
# ---------------------------------------------------------------------------

def test_from_dict_required_only():
    p = JitterPolicy.from_dict({"job_name": "j"})
    assert p.job_name == "j"
    assert p.min_seconds == 0.0
    assert p.max_seconds == 30.0
    assert p.seed is None


def test_from_dict_custom():
    p = JitterPolicy.from_dict({"job_name": "j", "min_seconds": 2.0, "max_seconds": 5.0, "seed": 42})
    assert p.min_seconds == 2.0
    assert p.max_seconds == 5.0
    assert p.seed == 42


def test_from_dict_missing_job_name_raises():
    with pytest.raises(JitterError, match="job_name"):
        JitterPolicy.from_dict({"max_seconds": 10})


def test_to_dict_roundtrip():
    p = _make(seed=7)
    assert JitterPolicy.from_dict(p.to_dict()).to_dict() == p.to_dict()


def test_to_dict_omits_seed_when_none():
    p = _make()
    assert "seed" not in p.to_dict()


def test_to_dict_includes_seed_when_set():
    p = _make(seed=99)
    assert p.to_dict()["seed"] == 99


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------

def test_negative_min_raises():
    with pytest.raises(JitterError, match="min_seconds"):
        _make(min_seconds=-1.0)


def test_max_less_than_min_raises():
    with pytest.raises(JitterError, match="max_seconds"):
        _make(min_seconds=5.0, max_seconds=2.0)


def test_equal_min_max_ok():
    p = _make(min_seconds=3.0, max_seconds=3.0)
    assert p.sample() == pytest.approx(3.0)


# ---------------------------------------------------------------------------
# sample / apply
# ---------------------------------------------------------------------------

def test_sample_within_range():
    p = _make(min_seconds=1.0, max_seconds=5.0)
    for _ in range(20):
        d = p.sample()
        assert 1.0 <= d <= 5.0


def test_sample_deterministic_with_seed():
    p = _make(seed=123)
    assert p.sample() == p.sample()


def test_apply_calls_sleep_with_delay():
    slept: list[float] = []
    p = _make(min_seconds=2.0, max_seconds=2.0)
    returned = p.apply(_sleep=slept.append)
    assert slept == [pytest.approx(2.0)]
    assert returned == pytest.approx(2.0)
