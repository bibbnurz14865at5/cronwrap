"""Tests for cronwrap.job_quota_audit."""
import json
import pytest
from cronwrap.job_quota_audit import QuotaAuditEvent, QuotaAuditLog, QuotaAuditError


def _make_log(tmp_path):
    return QuotaAuditLog(str(tmp_path / "audit"))


def _event(**kwargs):
    defaults = dict(
        job_name="myjob",
        action="allowed",
        quota_used=3,
        quota_limit=10,
    )
    defaults.update(kwargs)
    return QuotaAuditEvent(**defaults)


def test_event_to_dict_required_keys():
    e = _event()
    d = e.to_dict()
    assert "job_name" in d
    assert "action" in d
    assert "quota_used" in d
    assert "quota_limit" in d
    assert "timestamp" in d


def test_event_to_dict_omits_reason_when_none():
    e = _event()
    assert "reason" not in e.to_dict()


def test_event_to_dict_includes_reason_when_set():
    e = _event(reason="daily cap hit")
    assert e.to_dict()["reason"] == "daily cap hit"


def test_event_roundtrip():
    e = _event(action="denied", reason="over limit")
    e2 = QuotaAuditEvent.from_dict(e.to_dict())
    assert e2.job_name == e.job_name
    assert e2.action == e.action
    assert e2.quota_used == e.quota_used
    assert e2.quota_limit == e.quota_limit
    assert e2.reason == e.reason


def test_record_creates_file(tmp_path):
    log = _make_log(tmp_path)
    log.record(_event())
    files = list((tmp_path / "audit").iterdir())
    assert len(files) == 1
    assert files[0].name == "myjob.quota_audit.json"


def test_events_empty_when_no_file(tmp_path):
    log = _make_log(tmp_path)
    assert log.events("nonexistent") == []


def test_events_returns_all_recorded(tmp_path):
    log = _make_log(tmp_path)
    log.record(_event(action="allowed", quota_used=1))
    log.record(_event(action="denied", quota_used=10))
    events = log.events("myjob")
    assert len(events) == 2
    assert events[0].action == "allowed"
    assert events[1].action == "denied"


def test_clear_removes_file(tmp_path):
    log = _make_log(tmp_path)
    log.record(_event())
    log.clear("myjob")
    assert log.events("myjob") == []


def test_clear_noop_when_no_file(tmp_path):
    log = _make_log(tmp_path)
    log.clear("ghost")  # should not raise


def test_multiple_jobs_isolated(tmp_path):
    log = _make_log(tmp_path)
    log.record(_event(job_name="job_a", action="allowed"))
    log.record(_event(job_name="job_b", action="denied"))
    assert len(log.events("job_a")) == 1
    assert len(log.events("job_b")) == 1
    assert log.events("job_a")[0].action == "allowed"
    assert log.events("job_b")[0].action == "denied"


def test_timestamp_auto_set():
    e = _event()
    assert e.timestamp  # non-empty string
    assert "T" in e.timestamp  # ISO format
