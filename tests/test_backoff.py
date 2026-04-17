"""Tests for cronwrap.backoff."""
import pytest
from unittest.mock import patch, call
from cronwrap.backoff import BackoffPolicy


def test_from_dict_defaults():
    p = BackoffPolicy.from_dict({})
    assert p.max_retries == 3
    assert p.base_delay == 1.0
    assert p.multiplier == 2.0
    assert p.max_delay == 60.0
    assert p.jitter is True


def test_from_dict_custom():
    p = BackoffPolicy.from_dict({"max_retries": 5, "base_delay": 0.5, "jitter": False})
    assert p.max_retries == 5
    assert p.base_delay == 0.5
    assert p.jitter is False


def test_from_dict_ignores_unknown():
    p = BackoffPolicy.from_dict({"unknown_key": 99, "max_retries": 1})
    assert p.max_retries == 1
    assert not hasattr(p, "unknown_key")


def test_to_dict_roundtrip():
    p = BackoffPolicy(max_retries=2, base_delay=3.0, multiplier=1.5, max_delay=20.0, jitter=False)
    d = p.to_dict()
    p2 = BackoffPolicy.from_dict(d)
    assert p2.max_retries == 2
    assert p2.base_delay == 3.0
    assert p2.jitter is False


def test_delay_for_no_jitter():
    p = BackoffPolicy(base_delay=1.0, multiplier=2.0, max_delay=100.0, jitter=False)
    assert p.delay_for(0) == 1.0
    assert p.delay_for(1) == 2.0
    assert p.delay_for(2) == 4.0


def test_delay_for_respects_max():
    p = BackoffPolicy(base_delay=10.0, multiplier=10.0, max_delay=15.0, jitter=False)
    assert p.delay_for(3) == 15.0


def test_retry_succeeds_first_attempt():
    p = BackoffPolicy(max_retries=3, jitter=False)
    calls = []
    def fn():
        calls.append(1)
        return "ok"
    result = p.retry(fn)
    assert result == "ok"
    assert len(calls) == 1


def test_retry_succeeds_after_failures():
    p = BackoffPolicy(max_retries=3, base_delay=0.0, jitter=False)
    attempts = []
    def fn():
        attempts.append(1)
        if len(attempts) < 3:
            raise ValueError("fail")
        return "done"
    with patch.object(p, "delay_for", return_value=0.0):
        result = p.retry(fn)
    assert result == "done"
    assert len(attempts) == 3


def test_retry_raises_after_exhaustion():
    p = BackoffPolicy(max_retries=2, base_delay=0.0, jitter=False)
    def fn():
        raise RuntimeError("always fails")
    with patch.object(p, "delay_for", return_value=0.0):
        with pytest.raises(RuntimeError, match="always fails"):
            p.retry(fn)


def test_delay_for_jitter_within_range():
    p = BackoffPolicy(base_delay=2.0, multiplier=2.0, max_delay=100.0, jitter=True)
    for _ in range(20):
        d = p.delay_for(1)  # base = 4.0
        assert 2.0 <= d <= 4.0
