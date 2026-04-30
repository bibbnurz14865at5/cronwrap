"""Tests for cronwrap.job_suppression."""
from __future__ import annotations

import json
from datetime import datetime, timezone, timedelta

import pytest

from cronwrap.job_suppression import JobSuppression, SuppressionState


def _make(tmp_path):
    return JobSuppression(state_dir=str(tmp_path / "suppression"))


def _future(minutes=60):
    return datetime.now(timezone.utc) + timedelta(minutes=minutes)


def _past(minutes=60):
    return datetime.now(timezone.utc) - timedelta(minutes=minutes)


def test_suppress_creates_state(tmp_path):
    js = _make(tmp_path)
    until = _future()
    state = js.suppress("myjob", until=until)
    assert state.job_name == "myjob"
    assert state.suppressed_until == until


def test_suppress_persists_to_disk(tmp_path):
    js = _make(tmp_path)
    until = _future()
    js.suppress("myjob", until=until, reason="maintenance")
    state = js.get("myjob")
    assert state is not None
    assert state.reason == "maintenance"


def test_is_suppressed_true_when_active(tmp_path):
    js = _make(tmp_path)
    js.suppress("myjob", until=_future())
    assert js.is_suppressed("myjob") is True


def test_is_suppressed_false_when_expired(tmp_path):
    js = _make(tmp_path)
    js.suppress("myjob", until=_past())
    assert js.is_suppressed("myjob") is False


def test_is_suppressed_false_when_no_state(tmp_path):
    js = _make(tmp_path)
    assert js.is_suppressed("unknown") is False


def test_resume_removes_state(tmp_path):
    js = _make(tmp_path)
    js.suppress("myjob", until=_future())
    js.resume("myjob")
    assert js.get("myjob") is None


def test_resume_noop_when_not_suppressed(tmp_path):
    js = _make(tmp_path)
    js.resume("notexist")  # should not raise


def test_list_suppressed_returns_active_only(tmp_path):
    js = _make(tmp_path)
    js.suppress("job_a", until=_future(30))
    js.suppress("job_b", until=_past(10))
    js.suppress("job_c", until=_future(90))
    active = js.list_suppressed()
    names = [s.job_name for s in active]
    assert "job_a" in names
    assert "job_c" in names
    assert "job_b" not in names


def test_suppression_state_to_dict_keys(tmp_path):
    until = _future()
    state = SuppressionState(job_name="x", suppressed_until=until, reason="test")
    d = state.to_dict()
    assert "job_name" in d
    assert "suppressed_until" in d
    assert "reason" in d


def test_suppression_state_to_dict_omits_reason_when_none():
    until = _future()
    state = SuppressionState(job_name="x", suppressed_until=until)
    d = state.to_dict()
    assert "reason" not in d


def test_suppression_state_roundtrip():
    until = _future()
    state = SuppressionState(job_name="x", suppressed_until=until, reason="planned")
    restored = SuppressionState.from_dict(state.to_dict())
    assert restored.job_name == state.job_name
    assert restored.suppressed_until == state.suppressed_until
    assert restored.reason == state.reason
