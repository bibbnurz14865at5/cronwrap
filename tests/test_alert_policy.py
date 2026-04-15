"""Tests for cronwrap.alert_policy."""

import time
import pytest

from cronwrap.alert_policy import AlertPolicy, should_alert
from cronwrap.history import HistoryEntry, JobHistory


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _entry(success: bool, ts: float | None = None) -> HistoryEntry:
    e = HistoryEntry(success=success, exit_code=0 if success else 1,
                     duration=1.0, command="echo hi")
    if ts is not None:
        e.timestamp = ts
    return e


def _make_history(tmp_path, job_name: str, entries: list) -> JobHistory:
    h = JobHistory(str(tmp_path))
    for e in entries:
        h.record(job_name, e)
    return h


# ---------------------------------------------------------------------------
# AlertPolicy.from_dict / to_dict
# ---------------------------------------------------------------------------

def test_from_dict_defaults():
    p = AlertPolicy.from_dict({})
    assert p.notify_on_failure is True
    assert p.notify_on_recovery is True
    assert p.min_consecutive_failures == 1
    assert p.cooldown_seconds == 0


def test_from_dict_custom():
    p = AlertPolicy.from_dict({"notify_on_failure": False, "min_consecutive_failures": 3})
    assert p.notify_on_failure is False
    assert p.min_consecutive_failures == 3


def test_to_dict_roundtrip():
    p = AlertPolicy(notify_on_failure=True, notify_on_recovery=False,
                    min_consecutive_failures=2, cooldown_seconds=60)
    assert AlertPolicy.from_dict(p.to_dict()) == p


# ---------------------------------------------------------------------------
# should_alert
# ---------------------------------------------------------------------------

def test_no_history_no_alert(tmp_path):
    h = JobHistory(str(tmp_path))
    ok, reason = should_alert(AlertPolicy(), h, "myjob")
    assert ok is False
    assert "no history" in reason


def test_single_failure_alerts(tmp_path):
    h = _make_history(tmp_path, "job", [_entry(False)])
    ok, reason = should_alert(AlertPolicy(), h, "job")
    assert ok is True


def test_success_no_alert(tmp_path):
    h = _make_history(tmp_path, "job", [_entry(True)])
    ok, _ = should_alert(AlertPolicy(), h, "job")
    assert ok is False


def test_recovery_alert(tmp_path):
    h = _make_history(tmp_path, "job", [_entry(False), _entry(True)])
    ok, reason = should_alert(AlertPolicy(), h, "job")
    assert ok is True
    assert "recovery" in reason


def test_recovery_disabled(tmp_path):
    policy = AlertPolicy(notify_on_recovery=False)
    h = _make_history(tmp_path, "job", [_entry(False), _entry(True)])
    ok, _ = should_alert(policy, h, "job")
    assert ok is False


def test_min_consecutive_failures_not_met(tmp_path):
    policy = AlertPolicy(min_consecutive_failures=3)
    h = _make_history(tmp_path, "job", [_entry(False), _entry(False)])
    ok, reason = should_alert(policy, h, "job")
    assert ok is False
    assert "threshold" in reason


def test_min_consecutive_failures_met(tmp_path):
    policy = AlertPolicy(min_consecutive_failures=2)
    h = _make_history(tmp_path, "job", [_entry(False), _entry(False)])
    ok, _ = should_alert(policy, h, "job")
    assert ok is True


def test_failure_alerts_disabled(tmp_path):
    policy = AlertPolicy(notify_on_failure=False)
    h = _make_history(tmp_path, "job", [_entry(False)])
    ok, _ = should_alert(policy, h, "job")
    assert ok is False


def test_cooldown_suppresses_repeat_alert(tmp_path):
    now = time.time()
    e1 = _entry(False, ts=now - 10)
    e2 = _entry(False, ts=now - 5)
    policy = AlertPolicy(cooldown_seconds=60)
    h = _make_history(tmp_path, "job", [e1, e2])
    ok, reason = should_alert(policy, h, "job")
    assert ok is False
    assert "cooldown" in reason


def test_cooldown_expired_allows_alert(tmp_path):
    now = time.time()
    e1 = _entry(False, ts=now - 120)
    e2 = _entry(False, ts=now)
    policy = AlertPolicy(cooldown_seconds=60)
    h = _make_history(tmp_path, "job", [e1, e2])
    ok, _ = should_alert(policy, h, "job")
    assert ok is True
