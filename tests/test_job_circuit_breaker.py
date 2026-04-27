"""Tests for cronwrap.job_circuit_breaker."""
import time
import pytest
from cronwrap.job_circuit_breaker import CircuitBreakerPolicy, CircuitBreakerError


def _make(tmp_path, **kwargs):
    defaults = {
        "job_name": "test-job",
        "failure_threshold": 3,
        "recovery_timeout": 300,
        "state_dir": str(tmp_path),
    }
    defaults.update(kwargs)
    return CircuitBreakerPolicy.from_dict(defaults)


# ------------------------------------------------------------------ #
# from_dict / to_dict
# ------------------------------------------------------------------ #

def test_from_dict_required_only(tmp_path):
    p = CircuitBreakerPolicy.from_dict({"job_name": "j", "state_dir": str(tmp_path)})
    assert p.job_name == "j"
    assert p.failure_threshold == 3
    assert p.recovery_timeout == 300


def test_from_dict_custom(tmp_path):
    p = _make(tmp_path, failure_threshold=2, recovery_timeout=60)
    assert p.failure_threshold == 2
    assert p.recovery_timeout == 60


def test_from_dict_missing_job_name_raises():
    with pytest.raises(ValueError, match="job_name"):
        CircuitBreakerPolicy.from_dict({"failure_threshold": 2})


def test_to_dict_roundtrip(tmp_path):
    p = _make(tmp_path)
    d = p.to_dict()
    p2 = CircuitBreakerPolicy.from_dict(d)
    assert p2.job_name == p.job_name
    assert p2.failure_threshold == p.failure_threshold
    assert p2.recovery_timeout == p.recovery_timeout


# ------------------------------------------------------------------ #
# initial state
# ------------------------------------------------------------------ #

def test_circuit_closed_initially(tmp_path):
    p = _make(tmp_path)
    assert not p.is_open()


def test_check_passes_when_closed(tmp_path):
    p = _make(tmp_path)
    p.check()  # should not raise


# ------------------------------------------------------------------ #
# failure recording
# ------------------------------------------------------------------ #

def test_single_failure_does_not_open(tmp_path):
    p = _make(tmp_path, failure_threshold=3)
    p.record_failure()
    assert not p.is_open()


def test_failures_at_threshold_open_circuit(tmp_path):
    p = _make(tmp_path, failure_threshold=2)
    p.record_failure()
    p.record_failure()
    assert p.is_open()


def test_check_raises_when_open(tmp_path):
    p = _make(tmp_path, failure_threshold=1)
    p.record_failure()
    with pytest.raises(CircuitBreakerError):
        p.check()


# ------------------------------------------------------------------ #
# success resets circuit
# ------------------------------------------------------------------ #

def test_success_closes_circuit(tmp_path):
    p = _make(tmp_path, failure_threshold=1)
    p.record_failure()
    assert p.is_open()
    p.record_success()
    assert not p.is_open()


def test_success_allows_check(tmp_path):
    p = _make(tmp_path, failure_threshold=1)
    p.record_failure()
    p.record_success()
    p.check()  # should not raise


# ------------------------------------------------------------------ #
# recovery timeout (half-open)
# ------------------------------------------------------------------ #

def test_check_passes_after_recovery_timeout(tmp_path, monkeypatch):
    p = _make(tmp_path, failure_threshold=1, recovery_timeout=10)
    p.record_failure()
    # Simulate time passing beyond recovery window
    monkeypatch.setattr(time, "time", lambda: time.time.__wrapped__() + 20
                        if hasattr(time.time, "__wrapped__") else 9_999_999_999)
    # Direct state manipulation to simulate old opened_at
    s = p._load_state()
    s["opened_at"] = time.time() - 9999
    p._save_state(s)
    p.check()  # should not raise (half-open probe allowed)
